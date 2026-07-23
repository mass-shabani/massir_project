"""
Connection pool for WebSocket clients.

Manages multiple WebSocketClient connections per peer with round-robin
selection and idle connection cleanup.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from .types import PeerId, WebSocketCloseCode
from .client import WebSocketClient
from .exceptions import PoolError


class WebSocketConnectionPool:
    """
    Manages a pool of WebSocketClient connections per peer.
    """
    
    def __init__(
        self,
        max_per_peer: int = 3,
        idle_timeout: float = 300.0,
        cleanup_interval: float = 60.0,
        logger: Any = None,
    ):
        self._max_per_peer = max_per_peer
        self._idle_timeout = idle_timeout
        self._cleanup_interval = cleanup_interval
        self._logger = logger
        
        self._pool: dict[PeerId, list[WebSocketClient]] = {}
        self._rr_index: dict[PeerId, int] = {}
        
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the pool and cleanup task."""
        if self._running:
            return
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self._logger:
            self._logger.log(
                f"WebSocketConnectionPool started "
                f"(max_per_peer={self._max_per_peer}, "
                f"idle_timeout={self._idle_timeout}s)",
                tag="websocket"
            )
    
    async def stop(self):
        """Stop the pool and disconnect all clients."""
        self._running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        for peer_id, clients in list(self._pool.items()):
            for client in clients:
                try:
                    await client.disconnect(
                        code=WebSocketCloseCode.GOING_AWAY,
                        reason="Pool shutting down",
                    )
                except Exception:
                    pass
        
        self._pool.clear()
        self._rr_index.clear()
        
        if self._logger:
            self._logger.log("WebSocketConnectionPool stopped", tag="websocket")
    
    async def add_client(
        self,
        peer_id: PeerId,
        client: WebSocketClient,
        connect: bool = True,
    ):
        """
        Add a client to the pool for a peer.
        
        If connect=True and initial connection fails, the client remains
        in the pool and auto-reconnect will continue in the background.
        """
        if peer_id not in self._pool:
            self._pool[peer_id] = []
            self._rr_index[peer_id] = 0
        
        if len(self._pool[peer_id]) >= self._max_per_peer:
            raise PoolError(
                f"Max connections ({self._max_per_peer}) reached for peer '{peer_id}'"
            )
        
        client.peer_id = peer_id
        await client.enable_auto_reconnect()
        
        self._pool[peer_id].append(client)
        
        if connect:
            try:
                await client.connect()
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Initial WebSocket connection to peer '{peer_id}' failed, "
                        f"auto-reconnect active: {e}",
                        level="WARNING",
                        tag="websocket"
                    )
        
        if self._logger:
            self._logger.log(
                f"Added WebSocket client for peer '{peer_id}' "
                f"(total: {len(self._pool[peer_id])})",
                tag="websocket"
            )
    
    async def remove_client(
        self,
        peer_id: PeerId,
        client: Optional[WebSocketClient] = None,
    ):
        """Remove a client (or all clients) for a peer."""
        if peer_id not in self._pool:
            return
        
        if client is None:
            for c in list(self._pool[peer_id]):
                await c.disconnect()
            self._pool[peer_id].clear()
        else:
            if client in self._pool[peer_id]:
                await client.disconnect()
                self._pool[peer_id].remove(client)
        
        if not self._pool[peer_id]:
            del self._pool[peer_id]
            if peer_id in self._rr_index:
                del self._rr_index[peer_id]
    
    def get_client(self, peer_id: PeerId) -> Optional[WebSocketClient]:
        """Get a connected client for a peer using round-robin."""
        if peer_id not in self._pool:
            return None
        
        clients = self._pool[peer_id]
        if not clients:
            return None
        
        connected = [c for c in clients if c.is_connected]
        if not connected:
            return None
        
        idx = self._rr_index.get(peer_id, 0) % len(connected)
        self._rr_index[peer_id] = idx + 1
        return connected[idx]
    
    def get_all_clients(self, peer_id: PeerId) -> list[WebSocketClient]:
        """Get all clients for a peer."""
        return list(self._pool.get(peer_id, []))
    
    def get_all_peers(self) -> list[PeerId]:
        """Get all peer IDs in the pool."""
        return list(self._pool.keys())
    
    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        total_clients = sum(len(clients) for clients in self._pool.values())
        connected_clients = sum(
            sum(1 for c in clients if c.is_connected)
            for clients in self._pool.values()
        )
        
        return {
            "total_peers": len(self._pool),
            "total_clients": total_clients,
            "connected_clients": connected_clients,
            "max_per_peer": self._max_per_peer,
            "peers": {
                peer_id: {
                    "total": len(clients),
                    "connected": sum(1 for c in clients if c.is_connected),
                }
                for peer_id, clients in self._pool.items()
            },
        }
    
    async def _cleanup_loop(self):
        """Periodically cleanup idle connections."""
        try:
            while self._running:
                await asyncio.sleep(self._cleanup_interval)
                if self._running:
                    await self._cleanup_idle()
        except asyncio.CancelledError:
            pass
    
    async def _cleanup_idle(self):
        """Remove idle connections (keep at least 1 per peer)."""
        now = datetime.now()
        removed = 0
        
        for peer_id in list(self._pool.keys()):
            clients = self._pool[peer_id]
            to_remove = []
            
            for client in clients:
                if not client.connection:
                    continue
                info = client.connection.get_info()
                idle_seconds = (now - info.last_activity_at).total_seconds()
                if idle_seconds > self._idle_timeout and len(clients) > 1:
                    to_remove.append(client)
            
            for client in to_remove:
                await self.remove_client(peer_id, client)
                removed += 1
        
        if removed > 0 and self._logger:
            self._logger.log(
                f"Cleaned up {removed} idle WebSocket connection(s)",
                tag="websocket"
            )