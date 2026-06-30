"""
Async TCP client with reconnect logic.
"""

import asyncio
import ssl
from typing import Any, Optional

from .types import (
    SocketConfig,
    ConnectionState,
    SocketMode,
    SocketMessage,
    MessageType,
    PeerId,
)
from .connection import Connection
from .framing import LengthPrefixProtocol, get_codec
from .exceptions import (
    ConnectionError,
    ConnectionTimeoutError,
    ConnectionClosedError,
    ConnectionRefusedError,
)


class SocketClient:
    """
    Async TCP client with auto-reconnect and exponential backoff.
    """
    
    def __init__(self, config: SocketConfig, logger: Any = None):
        self._config = config
        self._logger = logger
        self._connection: Optional[Connection] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
        
        # Reconnect state
        self._current_delay = config.reconnect_initial_delay
        self._reconnect_attempts = 0
        self._reconnect_task: Optional[asyncio.Task] = None
        self._should_reconnect = False
        
        # Send queue for backpressure
        self._send_queue: asyncio.Queue = asyncio.Queue(
            maxsize=config.send_queue_size
        )
        self._send_task: Optional[asyncio.Task] = None
        
        # Protocol (only for Message Mode)
        self._protocol: Optional[LengthPrefixProtocol] = None
        if config.mode == SocketMode.MESSAGE:
            codec = get_codec("json")
            self._protocol = LengthPrefixProtocol(
                codec=codec,
                length_prefix_bytes=config.length_prefix_bytes,
                max_message_size=config.max_message_size,
            )
        
        # Callbacks
        self._on_connect = None
        self._on_disconnect = None
        self._on_reconnect_attempt = None
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def connection(self) -> Optional[Connection]:
        """Get the current connection."""
        return self._connection
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected."""
        return (
            self._connection is not None
            and self._connection.state == ConnectionState.CONNECTED
            and not self._connection.is_closed
        )
    
    @property
    def peer_id(self) -> Optional[PeerId]:
        """Get the peer ID."""
        return self._config.peer_id
    
    @peer_id.setter
    def peer_id(self, value: PeerId):
        """Set the peer ID."""
        self._config.peer_id = value
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def set_ssl_context(self, ssl_context: ssl.SSLContext):
        """Set SSL context for TLS."""
        self._ssl_context = ssl_context
    
    def on_connect(self, callback):
        """Register connect callback."""
        self._on_connect = callback
    
    def on_disconnect(self, callback):
        """Register disconnect callback."""
        self._on_disconnect = callback
    
    def on_reconnect_attempt(self, callback):
        """Register reconnect attempt callback."""
        self._on_reconnect_attempt = callback
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def connect(self):
        """Connect to the remote peer."""
        if self.is_connected:
            return
        
        if self._logger:
            tls_str = "TLS" if self._ssl_context else "plain"
            self._logger.log(
                f"Connecting to {self._config.host}:{self._config.port} "
                f"({tls_str}, {self._config.mode.value} mode)",
                tag="socket"
            )
        
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=self._config.host,
                    port=self._config.port,
                    ssl=self._ssl_context,
                    server_hostname=(
                        self._config.host if self._ssl_context else None
                    ),
                ),
                timeout=self._config.connect_timeout,
            )
        except asyncio.TimeoutError as e:
            raise ConnectionTimeoutError(
                f"Connection to {self._config.host}:{self._config.port} "
                f"timed out after {self._config.connect_timeout}s"
            ) from e
        except ConnectionRefusedError as e:
            raise ConnectionRefusedError(
                f"Connection refused by {self._config.host}:{self._config.port}"
            ) from e
        except OSError as e:
            raise ConnectionError(
                f"Failed to connect to {self._config.host}:{self._config.port}: {e}"
            ) from e
        
        # Create connection
        self._connection = Connection(
            config=self._config,
            reader=reader,
            writer=writer,
            protocol=self._protocol,
            is_server_side=False,
        )
        
        # Set close handler
        async def on_close(conn: Connection):
            if self._on_disconnect:
                try:
                    result = self._on_disconnect(conn)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass
            
            if self._should_reconnect:
                await self._schedule_reconnect()
        
        self._connection.on_close(on_close)
        
        # Reset reconnect state
        self._current_delay = self._config.reconnect_initial_delay
        self._reconnect_attempts = 0
        
        # Start receiving
        await self._connection.start_receiving()
        
        # Start send queue worker
        self._send_task = asyncio.create_task(self._send_queue_worker())
        
        if self._logger:
            self._logger.log(
                f"Connected to {self._config.host}:{self._config.port}",
                tag="socket"
            )
        
        # Invoke connect callback
        if self._on_connect:
            try:
                result = self._on_connect(self._connection)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in on_connect callback: {e}",
                        level="ERROR",
                        tag="socket"
                    )
    
    async def disconnect(self):
        """Disconnect from the remote peer."""
        self._should_reconnect = False
        
        # Cancel reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None
        
        # Cancel send task
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass
            self._send_task = None
        
        # Close connection
        if self._connection:
            await self._connection.close()
            self._connection = None
        
        # Clear send queue
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        if self._logger:
            self._logger.log(
                f"Disconnected from {self._config.host}:{self._config.port}",
                tag="socket"
            )
    
    async def enable_auto_reconnect(self):
        """Enable automatic reconnection."""
        self._should_reconnect = True
    
    async def disable_auto_reconnect(self):
        """Disable automatic reconnection."""
        self._should_reconnect = False
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    async def send_message(self, message: SocketMessage):
        """
        Send a framed message (Message Mode).
        
        Uses the send queue for backpressure handling.
        """
        if self._config.mode != SocketMode.MESSAGE:
            raise ConnectionError(
                "send_message() only works in MESSAGE mode"
            )
        
        if not self.is_connected:
            raise ConnectionClosedError("Not connected")
        
        try:
            self._send_queue.put_nowait(message)
        except asyncio.QueueFull:
            raise ConnectionError(
                f"Send queue is full ({self._config.send_queue_size} items)"
            )
    
    async def send_bytes(self, data: bytes):
        """Send raw bytes directly (bypasses queue)."""
        if not self.is_connected:
            raise ConnectionClosedError("Not connected")
        
        await self._connection.send_bytes(data)
    
    async def send_bytes_queued(self, data: bytes):
        """Send raw bytes via the send queue."""
        if not self.is_connected:
            raise ConnectionClosedError("Not connected")
        
        try:
            self._send_queue.put_nowait(data)
        except asyncio.QueueFull:
            raise ConnectionError("Send queue is full")
    
    # =========================================================================
    # Internal
    # =========================================================================
    
    async def _send_queue_worker(self):
        """Worker that processes the send queue."""
        try:
            while self._connection and not self._connection.is_closed:
                try:
                    item = await asyncio.wait_for(
                        self._send_queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    raise
                
                if not self._connection or self._connection.is_closed:
                    break
                
                try:
                    if self._config.mode == SocketMode.MESSAGE:
                        if isinstance(item, SocketMessage):
                            await self._connection.send_message(item)
                        elif isinstance(item, bytes):
                            await self._connection.send_bytes(item)
                    else:
                        if isinstance(item, bytes):
                            await self._connection.send_bytes(item)
                        elif isinstance(item, SocketMessage):
                            raise ConnectionError(
                                "Cannot send SocketMessage in STREAM mode"
                            )
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Error sending queued item: {e}",
                            level="ERROR",
                            tag="socket"
                        )
                    # Put back in queue if connection still alive
                    if self.is_connected:
                        try:
                            self._send_queue.put_nowait(item)
                        except asyncio.QueueFull:
                            pass
                    break
        except asyncio.CancelledError:
            pass
    
    async def _schedule_reconnect(self):
        """Schedule a reconnect attempt."""
        if not self._config.reconnect_enabled:
            return
        
        if not self._should_reconnect:
            return
        
        # Check max attempts
        if (
            self._config.reconnect_max_attempts > 0
            and self._reconnect_attempts >= self._config.reconnect_max_attempts
        ):
            if self._logger:
                self._logger.log(
                    f"Max reconnect attempts ({self._config.reconnect_max_attempts}) "
                    f"reached for {self._config.host}:{self._config.port}",
                    level="WARNING",
                    tag="socket"
                )
            return
        
        # Cancel existing reconnect task
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())
    
    async def _reconnect_loop(self):
        """Reconnect loop with exponential backoff."""
        try:
            while self._should_reconnect and not self.is_connected:
                # Check max attempts
                if (
                    self._config.reconnect_max_attempts > 0
                    and self._reconnect_attempts >= self._config.reconnect_max_attempts
                ):
                    break
                
                self._reconnect_attempts += 1
                
                if self._logger:
                    self._logger.log(
                        f"Reconnect attempt {self._reconnect_attempts} to "
                        f"{self._config.host}:{self._config.port} "
                        f"in {self._current_delay:.1f}s",
                        tag="socket"
                    )
                
                # Invoke callback
                if self._on_reconnect_attempt:
                    try:
                        result = self._on_reconnect_attempt(
                            self._reconnect_attempts,
                            self._current_delay,
                        )
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception:
                        pass
                
                # Wait before reconnecting
                await asyncio.sleep(self._current_delay)
                
                # Try to reconnect
                try:
                    await self.connect()
                    return  # Success
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Reconnect failed: {e}",
                            level="WARNING",
                            tag="socket"
                        )
                    
                    # Exponential backoff
                    self._current_delay = min(
                        self._current_delay * self._config.reconnect_backoff_multiplier,
                        self._config.reconnect_max_delay,
                    )
        except asyncio.CancelledError:
            pass
    
    def __repr__(self):
        return (
            f"SocketClient(host={self._config.host}, "
            f"port={self._config.port}, "
            f"connected={self.is_connected})"
        )