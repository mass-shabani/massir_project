"""
WebSocket client with URL-based connections and auto-reconnect.
"""

import asyncio
import ssl
import websockets
from typing import Any, Optional

from .types import (
    WebSocketConfig,
    WebSocketCloseCode,
    ConnectionState,
    PeerId,
)
from .connection import WebSocketConnection
from .exceptions import (
    WebSocketConnectionError,
    WebSocketConnectionTimeoutError,
    WebSocketHandshakeError,
)


class WebSocketClient:
    """
    WebSocket client with automatic reconnection and exponential backoff.
    
    Features:
    - URL-based or host/port/path connections
    - Subprotocol negotiation
    - Custom HTTP headers (for Bearer tokens, cookies)
    - Compression support
    - Auto-reconnect with exponential backoff
    - Send queue for backpressure
    """
    
    def __init__(self, config: WebSocketConfig, logger: Any = None):
        self._config = config
        self._logger = logger
        self._connection: Optional[WebSocketConnection] = None
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
        
        # Callbacks
        self._on_connect = None
        self._on_disconnect = None
        self._on_reconnect_attempt = None
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def connection(self) -> Optional[WebSocketConnection]:
        """Get the underlying WebSocketConnection."""
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
        """Get the peer identifier."""
        return self._config.peer_id
    
    @peer_id.setter
    def peer_id(self, value: PeerId):
        """Set the peer identifier."""
        self._config.peer_id = value
    
    @property
    def url(self) -> str:
        """Get the target URL."""
        return self._config.build_url()
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def set_ssl_context(self, ssl_context: ssl.SSLContext):
        """Set the TLS context for WSS connections."""
        self._ssl_context = ssl_context
    
    def on_connect(self, callback):
        """Register callback for successful connections."""
        self._on_connect = callback
    
    def on_disconnect(self, callback):
        """Register callback for disconnections."""
        self._on_disconnect = callback
    
    def on_reconnect_attempt(self, callback):
        """Register callback for reconnect attempts."""
        self._on_reconnect_attempt = callback
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def connect(self):
        """Connect to the remote WebSocket server."""
        if self.is_connected:
            return
        
        url = self._config.build_url()
        
        if self._logger:
            tls_str = "WSS" if self._ssl_context else "WS"
            subprotocol_str = (
                f", subprotocol={self._config.subprotocol}"
                if self._config.subprotocol else ""
            )
            self._logger.log(
                f"Connecting to {url} ({tls_str}{subprotocol_str})",
                tag="websocket"
            )
        
        # Build connection kwargs
        connect_kwargs = {
            "uri": url,
            "ssl": self._ssl_context,
            "max_size": self._config.max_size_bytes,
            "ping_interval": self._config.ping_interval,
            "ping_timeout": self._config.ping_timeout,
            "open_timeout": self._config.connect_timeout,
        }
        
        # Compression
        if self._config.compression_enabled:
            connect_kwargs["compression"] = "deflate"
        else:
            connect_kwargs["compression"] = None
        
        # Subprotocol negotiation
        if self._config.subprotocol:
            connect_kwargs["subprotocols"] = [self._config.subprotocol]
        
        # Custom headers (auth, cookies, etc.)
        if self._config.additional_headers:
            connect_kwargs["additional_headers"] = self._config.additional_headers
        
        try:
            ws = await asyncio.wait_for(
                websockets.connect(**connect_kwargs),
                timeout=self._config.connect_timeout,
            )
        except asyncio.TimeoutError as e:
            if self._should_reconnect:
                await self._schedule_reconnect()
            raise WebSocketConnectionTimeoutError(
                f"Connection to {url} timed out after {self._config.connect_timeout}s"
            ) from e
        except websockets.InvalidStatusCode as e:
            if self._should_reconnect:
                await self._schedule_reconnect()
            raise WebSocketHandshakeError(
                f"WebSocket handshake failed for {url}: HTTP {e.status_code}",
                http_status=e.status_code,
            ) from e
        except Exception as e:
            if self._should_reconnect:
                await self._schedule_reconnect()
            raise WebSocketConnectionError(
                f"Failed to connect to {url}: {e}"
            ) from e
        
        # Create connection wrapper
        self._connection = WebSocketConnection(
            config=self._config,
            ws=ws,
            is_server_side=False,
            logger=self._logger,
        )
        self._connection.increment_reconnect_count()
        
        # Set close handler
        async def on_close(conn: WebSocketConnection, code: int, reason: str):
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
        
        # Reset reconnect state on successful connection
        self._current_delay = self._config.reconnect_initial_delay
        self._reconnect_attempts = 0
        
        # Start receiving
        await self._connection.start_receiving()
        
        # Start send queue worker
        self._send_task = asyncio.create_task(self._send_queue_worker())
        
        if self._logger:
            subprotocol = self._connection.subprotocol
            self._logger.log(
                f"Connected to {url}"
                f"{f' (subprotocol: {subprotocol})' if subprotocol else ''}",
                tag="websocket"
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
                        tag="websocket"
                    )
    
    async def disconnect(self, code: int = WebSocketCloseCode.NORMAL, reason: str = ""):
        """Disconnect from the server with a close code."""
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
        
        # Close connection with code
        if self._connection:
            await self._connection.close(code=code, reason=reason)
            self._connection = None
        
        # Clear queue
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        if self._logger:
            self._logger.log(
                f"Disconnected from {self._config.build_url()} "
                f"(code={code}, reason='{reason}')",
                tag="websocket"
            )
    
    async def enable_auto_reconnect(self):
        """Enable automatic reconnection on failure."""
        self._should_reconnect = True
    
    async def disable_auto_reconnect(self):
        """Disable automatic reconnection."""
        self._should_reconnect = False
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    async def send_message(self, message: dict) -> int:
        """Send a JSON-serializable dict via the send queue."""
        if not self.is_connected:
            from .exceptions import WebSocketConnectionClosedError
            raise WebSocketConnectionClosedError("Not connected")
        
        try:
            self._send_queue.put_nowait(message)
            return 0
        except asyncio.QueueFull:
            raise WebSocketConnectionError(
                f"Send queue full ({self._config.send_queue_size} items)"
            )
    
    async def send_bytes(self, data: bytes) -> int:
        """Send raw bytes directly (bypasses queue)."""
        if not self.is_connected:
            from .exceptions import WebSocketConnectionClosedError
            raise WebSocketConnectionClosedError("Not connected")
        return await self._connection.send_bytes(data)
    
    async def send_bytes_queued(self, data: bytes):
        """Send raw bytes via the send queue."""
        if not self.is_connected:
            from .exceptions import WebSocketConnectionClosedError
            raise WebSocketConnectionClosedError("Not connected")
        try:
            self._send_queue.put_nowait(data)
        except asyncio.QueueFull:
            raise WebSocketConnectionError("Send queue full")
    
    # =========================================================================
    # Internal
    # =========================================================================
    
    async def _send_queue_worker(self):
        """Process the send queue."""
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
                    if isinstance(item, dict):
                        await self._connection.send_message(item)
                    elif isinstance(item, bytes):
                        await self._connection.send_bytes(item)
                    else:
                        if self._logger:
                            self._logger.log(
                                f"Unknown item type in send queue: {type(item)}",
                                level="WARNING",
                                tag="websocket"
                            )
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Error sending queued item: {e}",
                            level="ERROR",
                            tag="websocket"
                        )
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
        if not self._config.reconnect_enabled or not self._should_reconnect:
            return
        
        if (
            self._config.reconnect_max_attempts > 0
            and self._reconnect_attempts >= self._config.reconnect_max_attempts
        ):
            if self._logger:
                self._logger.log(
                    f"Max reconnect attempts ({self._config.reconnect_max_attempts}) "
                    f"reached for {self._config.build_url()}",
                    level="WARNING",
                    tag="websocket"
                )
            return
        
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
        
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())
    
    async def _reconnect_loop(self):
        """Reconnect with exponential backoff."""
        try:
            while self._should_reconnect and not self.is_connected:
                if (
                    self._config.reconnect_max_attempts > 0
                    and self._reconnect_attempts >= self._config.reconnect_max_attempts
                ):
                    break
                
                self._reconnect_attempts += 1
                
                if self._logger:
                    self._logger.log(
                        f"WebSocket reconnect attempt {self._reconnect_attempts} to "
                        f"{self._config.build_url()} in {self._current_delay:.1f}s",
                        tag="websocket"
                    )
                
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
                
                await asyncio.sleep(self._current_delay)
                
                try:
                    await self.connect()
                    return
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"WebSocket reconnect failed: {e}",
                            level="WARNING",
                            tag="websocket"
                        )
                    
                    self._current_delay = min(
                        self._current_delay * self._config.reconnect_backoff_multiplier,
                        self._config.reconnect_max_delay,
                    )
        except asyncio.CancelledError:
            pass
    
    def __repr__(self):
        return (
            f"WebSocketClient(url={self._config.build_url()}, "
            f"connected={self.is_connected})"
        )