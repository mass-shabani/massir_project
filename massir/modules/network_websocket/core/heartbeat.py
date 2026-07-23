"""
WebSocket heartbeat monitor using native ping/pong frames.

Uses WebSocket protocol-level ping/pong for more reliable liveness
detection than application-level messages.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Awaitable, Optional

from .connection import WebSocketConnection
from .types import PeerId

PeerDeadCallback = Callable[[PeerId, WebSocketConnection], Awaitable[None] | None]


class WebSocketHeartbeatMonitor:
    """
    Heartbeat monitor using native WebSocket ping/pong frames.
    
    Unlike raw TCP sockets which require custom ping/pong messages,
    WebSocket has built-in ping/pong control frames that are handled
    at the protocol level by the WebSocket library.
    """
    
    def __init__(
        self,
        interval: float = 20.0,
        timeout: float = 60.0,
        logger: Any = None,
    ):
        if interval <= 0:
            raise ValueError("interval must be positive")
        if timeout <= interval:
            raise ValueError("timeout must be greater than interval")
        
        self._interval = interval
        self._timeout = timeout
        self._logger = logger
        
        self._connections: dict[PeerId, WebSocketConnection] = {}
        self._last_activity: dict[PeerId, datetime] = {}
        
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        self._on_peer_dead: Optional[PeerDeadCallback] = None
        self._on_peer_alive: Optional[PeerDeadCallback] = None
    
    def on_peer_dead(self, callback: PeerDeadCallback):
        """Register callback for when a peer is declared dead."""
        self._on_peer_dead = callback
    
    def on_peer_alive(self, callback: PeerDeadCallback):
        """Register callback for when a dead peer recovers."""
        self._on_peer_alive = callback
    
    async def start(self):
        """Start the heartbeat monitor."""
        if self._running:
            return
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        if self._logger:
            self._logger.log(
                f"WebSocketHeartbeatMonitor started "
                f"(interval={self._interval}s, timeout={self._timeout}s)",
                tag="websocket"
            )
    
    async def stop(self):
        """Stop the heartbeat monitor."""
        self._running = False
        
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        self._connections.clear()
        self._last_activity.clear()
        
        if self._logger:
            self._logger.log("WebSocketHeartbeatMonitor stopped", tag="websocket")
    
    def add_connection(self, peer_id: PeerId, connection: WebSocketConnection):
        """Register a connection for monitoring."""
        self._connections[peer_id] = connection
        self._last_activity[peer_id] = datetime.now()
        
        # Wrap callbacks to track activity on any received data
        original_on_bytes = getattr(connection, "_on_bytes", None)
        original_on_message = getattr(connection, "_on_message", None)
        
        async def activity_tracker_bytes(data, conn):
            self._record_activity(peer_id)
            if original_on_bytes:
                result = original_on_bytes(data, conn)
                if asyncio.iscoroutine(result):
                    await result
        
        async def activity_tracker_message(msg, conn):
            self._record_activity(peer_id)
            if original_on_message:
                result = original_on_message(msg, conn)
                if asyncio.iscoroutine(result):
                    await result
        
        connection.on_bytes(activity_tracker_bytes)
        connection.on_message(activity_tracker_message)
    
    def remove_connection(self, peer_id: PeerId):
        """Remove a connection from monitoring."""
        self._connections.pop(peer_id, None)
        self._last_activity.pop(peer_id, None)
    
    def get_tracked_peers(self) -> list[PeerId]:
        """Get list of tracked peer IDs."""
        return list(self._connections.keys())
    
    def get_peer_status(self, peer_id: PeerId) -> dict[str, Any]:
        """Get status information for a peer."""
        if peer_id not in self._connections:
            return {"tracked": False}
        
        last_activity = self._last_activity.get(peer_id)
        seconds_since = (
            (datetime.now() - last_activity).total_seconds()
            if last_activity else None
        )
        
        return {
            "tracked": True,
            "last_activity": last_activity.isoformat() if last_activity else None,
            "seconds_since_activity": seconds_since,
            "is_alive": (
                seconds_since is not None and seconds_since < self._timeout
            ),
        }
    
    def _record_activity(self, peer_id: PeerId):
        """Record activity for a peer."""
        if peer_id not in self._connections:
            return
        
        was_inactive = self._is_peer_inactive(peer_id)
        self._last_activity[peer_id] = datetime.now()
        
        if was_inactive and self._on_peer_alive:
            conn = self._connections[peer_id]
            try:
                result = self._on_peer_alive(peer_id, conn)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass
    
    def _is_peer_inactive(self, peer_id: PeerId) -> bool:
        """Check if a peer is currently inactive."""
        last_activity = self._last_activity.get(peer_id)
        if last_activity is None:
            return True
        seconds_since = (datetime.now() - last_activity).total_seconds()
        return seconds_since > self._timeout
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self._running:
                await asyncio.sleep(self._interval)
                if not self._running:
                    break
                await self._send_pings()
                await self._check_timeouts()
        except asyncio.CancelledError:
            pass
    
    async def _send_pings(self):
        """Send native WebSocket pings to all tracked connections."""
        for peer_id, connection in list(self._connections.items()):
            if connection.is_closed:
                continue
            
            try:
                await connection.send_ping()
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to ping peer '{peer_id}': {e}",
                        level="WARNING",
                        tag="websocket"
                    )
    
    async def _check_timeouts(self):
        """Check for timed-out peers."""
        for peer_id in list(self._connections.keys()):
            if self._is_peer_inactive(peer_id):
                conn = self._connections[peer_id]
                last_activity = self._last_activity.get(peer_id)
                seconds_since = (
                    (datetime.now() - last_activity).total_seconds()
                    if last_activity else 0
                )
                
                if self._logger:
                    self._logger.log(
                        f"WebSocket peer '{peer_id}' declared dead "
                        f"(no activity for {seconds_since:.1f}s)",
                        level="WARNING",
                        tag="websocket"
                    )
                
                if self._on_peer_dead:
                    try:
                        result = self._on_peer_dead(peer_id, conn)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        if self._logger:
                            self._logger.log(
                                f"Error in on_peer_dead callback: {e}",
                                level="ERROR",
                                tag="websocket"
                            )