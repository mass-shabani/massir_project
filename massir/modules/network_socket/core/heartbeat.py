"""
Heartbeat monitoring for connections.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Awaitable, Optional

from .connection import Connection
from .types import SocketMessage, MessageType, PeerId
from .exceptions import HeartbeatTimeoutError

# Callback types
PeerDeadCallback = Callable[[PeerId, Connection], Awaitable[None] | None]


class HeartbeatMonitor:
    """
    Monitors connection health via ping/pong heartbeats.
    
    Responsibilities:
    - Send periodic pings to all monitored connections
    - Track pong responses
    - Detect dead peers (no pong within timeout)
    - Notify via callbacks
    """
    
    def __init__(
        self,
        interval: float = 30.0,
        timeout: float = 90.0,
        missed_threshold: int = 3,
        logger: Any = None,
    ):
        """
        Initialize the heartbeat monitor.
        
        Args:
            interval: Seconds between ping attempts
            timeout: Seconds before considering peer dead
            missed_threshold: Number of missed pongs before declaring dead
            logger: Logger instance
        """
        if interval <= 0:
            raise ValueError("interval must be positive")
        if timeout <= interval:
            raise ValueError("timeout must be greater than interval")
        
        self._interval = interval
        self._timeout = timeout
        self._missed_threshold = missed_threshold
        self._logger = logger
        
        # Tracked connections: peer_id -> Connection
        self._connections: dict[PeerId, Connection] = {}
        
        # Last pong time per peer
        self._last_pong: dict[PeerId, datetime] = {}
        
        # Missed ping count per peer
        self._missed_count: dict[PeerId, int] = {}
        
        # Tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks
        self._on_peer_dead: Optional[PeerDeadCallback] = None
        self._on_peer_alive: Optional[PeerDeadCallback] = None
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def on_peer_dead(self, callback: PeerDeadCallback):
        """Register callback for when peer is declared dead."""
        self._on_peer_dead = callback
    
    def on_peer_alive(self, callback: PeerDeadCallback):
        """Register callback for when peer recovers."""
        self._on_peer_alive = callback
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self):
        """Start the heartbeat monitor."""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        if self._logger:
            self._logger.log(
                f"HeartbeatMonitor started "
                f"(interval={self._interval}s, timeout={self._timeout}s)",
                tag="socket"
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
        self._last_pong.clear()
        self._missed_count.clear()
        
        if self._logger:
            self._logger.log("HeartbeatMonitor stopped", tag="socket")
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    def add_connection(self, peer_id: PeerId, connection: Connection):
        """
        Add a connection to be monitored.
        
        Automatically handles incoming PONG messages.
        """
        self._connections[peer_id] = connection
        self._last_pong[peer_id] = datetime.now()
        self._missed_count[peer_id] = 0
        
        # Register PONG handler if in message mode
        if connection.is_message_mode:
            original_handler = getattr(connection, "_on_message", None)
            
            async def pong_handler(message: SocketMessage, conn: Connection):
                if message.type == MessageType.PONG:
                    self._handle_pong(peer_id)
                if original_handler:
                    result = original_handler(message, conn)
                    if asyncio.iscoroutine(result):
                        await result
            
            connection.on_message(pong_handler)
    
    def remove_connection(self, peer_id: PeerId):
        """Remove a connection from monitoring."""
        self._connections.pop(peer_id, None)
        self._last_pong.pop(peer_id, None)
        self._missed_count.pop(peer_id, None)
    
    def get_tracked_peers(self) -> list[PeerId]:
        """Get list of tracked peer IDs."""
        return list(self._connections.keys())
    
    def get_peer_status(self, peer_id: PeerId) -> dict[str, Any]:
        """Get status information for a peer."""
        if peer_id not in self._connections:
            return {"tracked": False}
        
        last_pong = self._last_pong.get(peer_id)
        seconds_since_pong = (
            (datetime.now() - last_pong).total_seconds()
            if last_pong else None
        )
        
        return {
            "tracked": True,
            "last_pong": last_pong.isoformat() if last_pong else None,
            "seconds_since_pong": seconds_since_pong,
            "missed_count": self._missed_count.get(peer_id, 0),
            "is_alive": (
                seconds_since_pong is not None
                and seconds_since_pong < self._timeout
            ),
        }
    
    # =========================================================================
    # Internal
    # =========================================================================
    
    def _handle_pong(self, peer_id: PeerId):
        """Handle a received PONG."""
        if peer_id not in self._connections:
            return
        
        was_dead = self._missed_count.get(peer_id, 0) >= self._missed_threshold
        self._last_pong[peer_id] = datetime.now()
        self._missed_count[peer_id] = 0
        
        # Notify recovery
        if was_dead and self._on_peer_alive:
            conn = self._connections[peer_id]
            try:
                result = self._on_peer_alive(peer_id, conn)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass
    
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
        """Send PING to all tracked connections."""
        for peer_id, connection in list(self._connections.items()):
            if connection.is_closed:
                continue
            
            if not connection.is_message_mode:
                # Stream mode doesn't support ping/pong
                continue
            
            try:
                await connection.send_ping()
                self._missed_count[peer_id] = (
                    self._missed_count.get(peer_id, 0) + 1
                )
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to send ping to {peer_id}: {e}",
                        level="WARNING",
                        tag="socket"
                    )
    
    async def _check_timeouts(self):
        """Check for timed-out peers."""
        now = datetime.now()
        
        for peer_id in list(self._connections.keys()):
            last_pong = self._last_pong.get(peer_id)
            if last_pong is None:
                continue
            
            seconds_since = (now - last_pong).total_seconds()
            missed = self._missed_count.get(peer_id, 0)
            
            if seconds_since > self._timeout or missed >= self._missed_threshold:
                conn = self._connections[peer_id]
                
                if self._logger:
                    self._logger.log(
                        f"Peer '{peer_id}' declared dead "
                        f"(last_pong: {seconds_since:.1f}s ago, "
                        f"missed: {missed})",
                        level="WARNING",
                        tag="socket"
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
                                tag="socket"
                            )