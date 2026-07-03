"""
Connection pool for managing multiple connections per peer.
"""

import asyncio
from datetime import datetime
from typing import Any, Optional

from .types import SocketConfig, PeerId, ConnectionState
from .client import SocketClient
from .exceptions import PoolError


class ConnectionPool:
    """
    Manages a pool of SocketClient connections per peer.
    
    Each peer can have multiple active connections (for load balancing
    or multiplexing).
    """
    
    def __init__(
        self,
        max_per_peer: int = 5,
        idle_timeout: float = 300.0,
        cleanup_interval: float = 60.0,
        logger: Any = None,
    ):
        self._max_per_peer = max_per_peer
        self._idle_timeout = idle_timeout
        self._cleanup_interval = cleanup_interval
        self._logger = logger
        
        # Pool: peer_id -> list of clients
        self._pool: dict[PeerId, list[SocketClient]] = {}
        
        # Round-robin index per peer
        self._rr_index: dict[PeerId, int] = {}
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    # =========================================================================
    # Pool Management
    # =========================================================================
    
    async def start(self):
        """Start the pool and cleanup task."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        if self._logger:
            self._logger.log(
                f"ConnectionPool started "
                f"(max_per_peer={self._max_per_peer}, "
                f"idle_timeout={self._idle_timeout}s)",
                tag="socket"
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
        
        # Disconnect all clients
        for peer_id, clients in list(self._pool.items()):
            for client in clients:
                try:
                    await client.disconnect()
                except Exception:
                    pass
        
        self._pool.clear()
        self._rr_index.clear()
        
        if self._logger:
            self._logger.log("ConnectionPool stopped", tag="socket")
    
    # =========================================================================
    # Client Management
    # =========================================================================
    
    async def add_client(
        self,
        peer_id: PeerId,
        client: SocketClient,
        connect: bool = True,
    ):
        """
        Add a client to the pool for a peer.
        
        Args:
            peer_id: The peer identifier
            client: The SocketClient instance
            connect: Whether to connect immediately
        
        Raises:
            PoolError: If max connections reached for peer
            
        Note:
            If connect=True and connection fails, the client is NOT removed
            from the pool. The auto-reconnect mechanism will keep trying
            to establish the connection in the background.
        """
        if peer_id not in self._pool:
            self._pool[peer_id] = []
            self._rr_index[peer_id] = 0
        
        if len(self._pool[peer_id]) >= self._max_per_peer:
            raise PoolError(
                f"Max connections ({self._max_per_peer}) reached "
                f"for peer '{peer_id}'"
            )
        
        # Set peer_id on client
        client.peer_id = peer_id
        
        # Enable auto-reconnect BEFORE adding to pool
        # This ensures reconnect is active even if initial connect fails
        await client.enable_auto_reconnect()
        
        # Add to pool FIRST so reconnect can find it
        self._pool[peer_id].append(client)
        
        if connect:
            try:
                await client.connect()
            except Exception as e:
                # Don't remove from pool - let reconnect handle it
                # The client remains in the pool and will keep trying
                # to reconnect in the background via _schedule_reconnect()
                if self._logger:
                    self._logger.log(
                        f"Initial connection to peer '{peer_id}' failed, "
                        f"auto-reconnect is active: {e}",
                        level="WARNING",
                        tag="socket"
                    )
                # Don't raise - let reconnect work in background
                # The caller can check client.is_connected later
        
        if self._logger:
            self._logger.log(
                f"Added client for peer '{peer_id}' "
                f"(total: {len(self._pool[peer_id])})",
                tag="socket"
            )
    
    async def remove_client(
        self,
        peer_id: PeerId,
        client: Optional[SocketClient] = None,
    ):
        """
        Remove a client from the pool.
        
        Args:
            peer_id: The peer identifier
            client: Specific client to remove (None = all for peer)
        """
        if peer_id not in self._pool:
            return
        
        if client is None:
            # Remove all
            clients = list(self._pool[peer_id])
            for c in clients:
                await c.disconnect()
            self._pool[peer_id].clear()
        else:
            if client in self._pool[peer_id]:
                await client.disconnect()
                self._pool[peer_id].remove(client)
        
        # Cleanup empty peer entry
        if not self._pool[peer_id]:
            del self._pool[peer_id]
            if peer_id in self._rr_index:
                del self._rr_index[peer_id]
    
    def get_client(self, peer_id: PeerId) -> Optional[SocketClient]:
        """
        Get a connected client for a peer using round-robin.
        
        Returns None if no connected clients available.
        Note: A client may be in the pool but not connected yet
        (e.g., during reconnection). This method only returns
        actually connected clients.
        """
        if peer_id not in self._pool:
            return None
        
        clients = self._pool[peer_id]
        if not clients:
            return None
        
        # Filter to connected clients
        connected = [c for c in clients if c.is_connected]
        if not connected:
            return None
        
        # Round-robin selection
        idx = self._rr_index.get(peer_id, 0) % len(connected)
        self._rr_index[peer_id] = idx + 1
        
        return connected[idx]
    
    def get_any_client(self, peer_id: PeerId) -> Optional[SocketClient]:
        """
        Get any client for a peer (connected or not).
        
        Useful for checking if a client exists for a peer,
        even if it's currently reconnecting.
        """
        if peer_id not in self._pool:
            return None
        
        clients = self._pool[peer_id]
        return clients[0] if clients else None
    
    def get_all_clients(self, peer_id: PeerId) -> list[SocketClient]:
        """Get all clients for a peer."""
        return list(self._pool.get(peer_id, []))
    
    def get_all_peers(self) -> list[PeerId]:
        """Get all peer IDs in the pool."""
        return list(self._pool.keys())
    
    # =========================================================================
    # Stats
    # =========================================================================
    
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
    
    # =========================================================================
    # Internal
    # =========================================================================
    
    async def _cleanup_loop(self):
        """Periodically cleanup idle connections."""
        try:
            while self._running:
                await asyncio.sleep(self._cleanup_interval)
                
                if not self._running:
                    break
                
                await self._cleanup_idle()
        except asyncio.CancelledError:
            pass
    
    async def _cleanup_idle(self):
        """Remove idle connections."""
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
                
                # Only cleanup if we have more than 1 connection for this peer
                if (
                    idle_seconds > self._idle_timeout
                    and len(clients) > 1
                ):
                    to_remove.append(client)
            
            for client in to_remove:
                await self.remove_client(peer_id, client)
                removed += 1
        
        if removed > 0 and self._logger:
            self._logger.log(
                f"Cleaned up {removed} idle connection(s)",
                tag="socket"
            )