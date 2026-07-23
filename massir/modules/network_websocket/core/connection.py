"""
WebSocket connection wrapper.

Wraps a websockets connection and provides a WebSocket-optimized interface
with support for text frames (JSON), binary frames (streams), and
WebSocket-specific features like subprotocols and close codes.
"""

import asyncio
import json
import websockets
from datetime import datetime
from typing import Any, Callable, Optional, Awaitable

from .types import (
    WebSocketConfig,
    WebSocketConnectionInfo,
    WebSocketCloseCode,
    ConnectionState,
    WebSocketFrameType,
    PeerId,
)

# Callback types
MessageCallback = Callable[[dict, "WebSocketConnection"], Awaitable[None] | None]
BytesCallback = Callable[[bytes, "WebSocketConnection"], Awaitable[None] | None]
StateCallback = Callable[[ConnectionState, "WebSocketConnection"], Awaitable[None] | None]
CloseCallback = Callable[["WebSocketConnection", int, str], Awaitable[None] | None]


class WebSocketConnection:
    """
    Wraps a websockets connection with a WebSocket-optimized interface.
    
    Unlike raw TCP sockets, WebSocket connections are already message-oriented:
    - Text frames carry UTF-8 encoded JSON (for structured messages)
    - Binary frames carry raw bytes (for streams)
    - Control frames (ping/pong/close) are handled at the protocol level
    
    This class does NOT dictate message format - it passes JSON dicts and
    bytes as-is. Message framing is the responsibility of higher layers
    (e.g., system_network or application modules).
    """
    
    def __init__(
        self,
        config: WebSocketConfig,
        ws: websockets.WebSocketClientProtocol,
        is_server_side: bool = False,
        logger: Any = None,
    ):
        self._config = config
        self._ws = ws
        self._is_server_side = is_server_side
        self._logger = logger
        
        # State
        self._state = ConnectionState.CONNECTED
        self._peer_id: Optional[PeerId] = config.peer_id
        self._established_at = datetime.now()
        self._last_activity_at = datetime.now()
        
        # Stats
        self._bytes_sent = 0
        self._bytes_received = 0
        self._messages_sent = 0
        self._messages_received = 0
        self._reconnect_count = 0
        
        # Close info
        self._close_code: Optional[int] = None
        self._close_reason: Optional[str] = None
        
        # Callbacks
        self._on_message: Optional[MessageCallback] = None
        self._on_bytes: Optional[BytesCallback] = None
        self._on_state_change: Optional[StateCallback] = None
        self._on_close: Optional[CloseCallback] = None
        
        # Background tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._closed = False
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def peer_id(self) -> Optional[PeerId]:
        """Get the peer identifier."""
        return self._peer_id
    
    @peer_id.setter
    def peer_id(self, value: PeerId):
        """Set the peer identifier."""
        self._peer_id = value
    
    @property
    def state(self) -> ConnectionState:
        """Get the current connection state."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if the connection is closed."""
        return self._closed
    
    @property
    def subprotocol(self) -> Optional[str]:
        """Get the negotiated subprotocol (if any)."""
        try:
            return getattr(self._ws, 'subprotocol', None)
        except Exception:
            return None
    
    @property
    def close_code(self) -> Optional[int]:
        """Get the WebSocket close code (if connection was closed)."""
        return self._close_code
    
    @property
    def close_reason(self) -> Optional[str]:
        """Get the WebSocket close reason (if connection was closed)."""
        return self._close_reason
    
    @property
    def remote_address(self) -> tuple[str, int]:
        """Get remote address (host, port)."""
        try:
            if hasattr(self._ws, 'remote_address'):
                addr = self._ws.remote_address
                if addr:
                    return (addr[0], addr[1])
        except Exception:
            pass
        return (self._config.host or "", self._config.port or 0)
    
    @property
    def url(self) -> str:
        """Get the connection URL."""
        return self._config.build_url()
    
    def get_info(self) -> WebSocketConnectionInfo:
        """Get comprehensive connection information."""
        host, port = self.remote_address
        return WebSocketConnectionInfo(
            peer_id=self._peer_id,
            host=host,
            port=port,
            state=self._state,
            is_tls=self._config.use_tls,
            established_at=self._established_at,
            last_activity_at=self._last_activity_at,
            bytes_sent=self._bytes_sent,
            bytes_received=self._bytes_received,
            messages_sent=self._messages_sent,
            messages_received=self._messages_received,
            reconnect_count=self._reconnect_count,
            url=self.url,
            path=self._config.path,
            subprotocol=self.subprotocol,
            compression_enabled=self._config.compression_enabled,
            close_code=self._close_code,
            close_reason=self._close_reason,
        )
    
    # =========================================================================
    # Callback Registration
    # =========================================================================
    
    def on_message(self, callback: MessageCallback):
        """
        Register callback for incoming text messages (JSON dicts).
        
        The callback receives (message_dict, connection).
        """
        self._on_message = callback
    
    def on_bytes(self, callback: BytesCallback):
        """
        Register callback for incoming binary frames.
        
        The callback receives (bytes, connection).
        """
        self._on_bytes = callback
    
    def on_state_change(self, callback: StateCallback):
        """Register callback for connection state changes."""
        self._on_state_change = callback
    
    def on_close(self, callback: CloseCallback):
        """
        Register callback for connection closure.
        
        The callback receives (connection, close_code, close_reason).
        This is more informative than the socket-level on_close because
        it includes WebSocket close codes and reasons.
        """
        self._on_close = callback
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start_receiving(self):
        """Start the receive loop as a background task."""
        if self._receive_task is not None:
            return
        self._receive_task = asyncio.create_task(self._receive_loop())
    
    async def close(
        self,
        code: int = WebSocketCloseCode.NORMAL,
        reason: str = "",
    ):
        """
        Close the WebSocket connection gracefully.
        
        Args:
            code: WebSocket close code (RFC 6455)
            reason: Human-readable close reason (max 123 bytes UTF-8)
        """
        if self._closed:
            return
        
        self._closed = True
        self._close_code = code
        self._close_reason = reason
        self._set_state(ConnectionState.DISCONNECTING)
        
        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except (asyncio.CancelledError, Exception):
                pass
            self._receive_task = None
        
        # Close the WebSocket with code and reason
        try:
            await self._ws.close(code=code, reason=reason)
        except Exception:
            pass
        
        self._set_state(ConnectionState.DISCONNECTED)
        
        # Invoke close callback with close code info
        if self._on_close:
            try:
                result = self._on_close(self, code, reason)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in on_close callback: {e}",
                        level="ERROR",
                        tag="websocket"
                    )
    
    def _set_state(self, new_state: ConnectionState):
        """Update connection state and invoke callback."""
        if self._state == new_state:
            return
        self._state = new_state
        if self._on_state_change:
            try:
                result = self._on_state_change(new_state, self)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass
    
    def increment_reconnect_count(self):
        """Increment the reconnect counter (called by client on reconnect)."""
        self._reconnect_count += 1
    
    # =========================================================================
    # Sending - WebSocket-Optimized
    # =========================================================================
    
    async def send_message(self, message: dict) -> int:
        """
        Send a JSON-serializable dict as a WebSocket text frame.
        
        Unlike network_socket which requires SocketMessage objects, this
        method accepts any JSON-serializable dict. The higher layers
        (system_network, application modules) are responsible for message
        structure and framing.
        
        Args:
            message: JSON-serializable dict
        
        Returns:
            Number of bytes sent
        """
        if self._closed:
            from .exceptions import WebSocketConnectionClosedError
            raise WebSocketConnectionClosedError(
                "Cannot send on closed connection",
                close_code=self._close_code,
                close_reason=self._close_reason,
            )
        
        try:
            payload = json.dumps(message, separators=(",", ":"))
            await self._ws.send(payload)
            bytes_written = len(payload.encode("utf-8"))
            self._bytes_sent += bytes_written
            self._messages_sent += 1
            self._last_activity_at = datetime.now()
            return bytes_written
        except websockets.ConnectionClosed as e:
            from .exceptions import WebSocketConnectionClosedError
            self._close_code = e.code
            self._close_reason = e.reason
            raise WebSocketConnectionClosedError(
                f"Connection closed: {e}",
                close_code=e.code,
                close_reason=e.reason,
            ) from e
        except Exception as e:
            from .exceptions import WebSocketConnectionError
            raise WebSocketConnectionError(f"Failed to send message: {e}") from e
    
    async def send_bytes(self, data: bytes) -> int:
        """
        Send raw bytes as a WebSocket binary frame.
        
        Ideal for streaming, file transfer, and binary protocols.
        
        Args:
            data: Raw bytes to send
        
        Returns:
            Number of bytes sent
        """
        if self._closed:
            from .exceptions import WebSocketConnectionClosedError
            raise WebSocketConnectionClosedError(
                "Cannot send on closed connection",
                close_code=self._close_code,
                close_reason=self._close_reason,
            )
        
        try:
            await self._ws.send(data)
            self._bytes_sent += len(data)
            self._last_activity_at = datetime.now()
            return len(data)
        except websockets.ConnectionClosed as e:
            from .exceptions import WebSocketConnectionClosedError
            self._close_code = e.code
            self._close_reason = e.reason
            raise WebSocketConnectionClosedError(
                f"Connection closed: {e}",
                close_code=e.code,
                close_reason=e.reason,
            ) from e
        except Exception as e:
            from .exceptions import WebSocketConnectionError
            raise WebSocketConnectionError(f"Failed to send bytes: {e}") from e
    
    async def send_ping(self, data: bytes = b"") -> None:
        """
        Send a WebSocket protocol-level ping.
        
        This is different from application-level ping messages. The peer's
        WebSocket library automatically responds with a pong frame.
        
        Args:
            data: Optional ping payload (max 125 bytes)
        """
        if self._closed:
            from .exceptions import WebSocketConnectionClosedError
            raise WebSocketConnectionClosedError("Cannot ping on closed connection")
        try:
            await self._ws.ping(data)
        except Exception as e:
            from .exceptions import WebSocketConnectionError
            raise WebSocketConnectionError(f"Failed to send ping: {e}") from e
    
    # =========================================================================
    # Receive Loop
    # =========================================================================
    
    async def _receive_loop(self):
        """Receive loop handling text (JSON) and binary frames."""
        try:
            async for frame in self._ws:
                self._last_activity_at = datetime.now()
                
                if isinstance(frame, str):
                    # Text frame -> JSON dict
                    try:
                        data = json.loads(frame)
                        self._messages_received += 1
                        self._bytes_received += len(frame.encode("utf-8"))
                        
                        if self._on_message:
                            try:
                                result = self._on_message(data, self)
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception as e:
                                if self._logger:
                                    self._logger.log(
                                        f"Error in message callback: {e}",
                                        level="ERROR",
                                        tag="websocket"
                                    )
                    except json.JSONDecodeError:
                        if self._logger:
                            self._logger.log(
                                "Received invalid JSON in text frame",
                                level="WARNING",
                                tag="websocket"
                            )
                
                elif isinstance(frame, bytes):
                    # Binary frame -> raw bytes
                    self._bytes_received += len(frame)
                    if self._on_bytes:
                        try:
                            result = self._on_bytes(frame, self)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            if self._logger:
                                self._logger.log(
                                    f"Error in bytes callback: {e}",
                                    level="ERROR",
                                    tag="websocket"
                                )
        
        except websockets.ConnectionClosed as e:
            self._close_code = e.code
            self._close_reason = e.reason
            if self._logger:
                self._logger.log(
                    f"WebSocket closed: code={e.code} "
                    f"({self._code_name(e.code)}), reason='{e.reason}'",
                    level="INFO",
                    tag="websocket"
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"WebSocket receive error: {e}",
                    level="ERROR",
                    tag="websocket"
                )
        finally:
            if not self._closed:
                await self.close(
                    code=WebSocketCloseCode.ABNORMAL_CLOSURE,
                    reason="Receive loop terminated",
                )
    
    @staticmethod
    def _code_name(code: int) -> str:
        """Get human-readable name for a close code."""
        try:
            return WebSocketCloseCode(code).name
        except ValueError:
            if 4000 <= code <= 4999:
                return f"APP_{code}"
            return f"UNKNOWN_{code}"
    
    def __repr__(self):
        host, port = self.remote_address
        return (
            f"WebSocketConnection(peer_id={self._peer_id}, "
            f"remote={host}:{port}, state={self._state.value}, "
            f"subprotocol={self.subprotocol})"
        )