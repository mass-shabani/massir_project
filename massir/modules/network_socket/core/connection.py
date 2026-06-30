"""
Single connection management.
"""

import asyncio
from datetime import datetime
from typing import Any, Callable, Optional, Awaitable

from .types import (
    SocketConfig,
    SocketMessage,
    ConnectionInfo,
    ConnectionState,
    SocketMode,
    MessageType,
    PeerId,
)
from .framing import LengthPrefixProtocol
from .exceptions import (
    ConnectionError,
    ConnectionClosedError,
)

# Callback types
MessageCallback = Callable[[SocketMessage, "Connection"], Awaitable[None] | None]
BytesCallback = Callable[[bytes, "Connection"], Awaitable[None] | None]
StateCallback = Callable[[ConnectionState, "Connection"], Awaitable[None] | None]


class Connection:
    """
    Represents a single TCP connection.
    
    Supports both Message Mode (framed messages) and Stream Mode (raw bytes).
    """
    
    def __init__(
        self,
        config: SocketConfig,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        protocol: Optional[LengthPrefixProtocol] = None,
        is_server_side: bool = False,
    ):
        self._config = config
        self._reader = reader
        self._writer = writer
        self._protocol = protocol
        self._is_server_side = is_server_side
        
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
        
        # Callbacks
        self._on_message: Optional[MessageCallback] = None
        self._on_bytes: Optional[BytesCallback] = None
        self._on_state_change: Optional[StateCallback] = None
        self._on_close: Optional[Callable[["Connection"], Awaitable[None] | None]] = None
        
        # Tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._closed = False
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def peer_id(self) -> Optional[PeerId]:
        """Get the peer ID."""
        return self._peer_id
    
    @peer_id.setter
    def peer_id(self, value: PeerId):
        """Set the peer ID."""
        self._peer_id = value
    
    @property
    def state(self) -> ConnectionState:
        """Get the connection state."""
        return self._state
    
    @property
    def mode(self) -> SocketMode:
        """Get the socket mode."""
        return self._config.mode
    
    @property
    def is_closed(self) -> bool:
        """Check if connection is closed."""
        return self._closed
    
    @property
    def is_message_mode(self) -> bool:
        """Check if in message mode."""
        return self._config.mode == SocketMode.MESSAGE
    
    @property
    def is_stream_mode(self) -> bool:
        """Check if in stream mode."""
        return self._config.mode == SocketMode.STREAM
    
    @property
    def remote_address(self) -> tuple[str, int]:
        """Get remote address."""
        try:
            peername = self._writer.get_extra_info("peername")
            if peername:
                return (peername[0], peername[1])
        except Exception:
            pass
        return (self._config.host, self._config.port)
    
    @property
    def local_address(self) -> tuple[str, int]:
        """Get local address."""
        try:
            sockname = self._writer.get_extra_info("sockname")
            if sockname:
                return (sockname[0], sockname[1])
        except Exception:
            pass
        return ("", 0)
    
    def get_info(self) -> ConnectionInfo:
        """Get connection information."""
        host, port = self.remote_address
        return ConnectionInfo(
            peer_id=self._peer_id,
            host=host,
            port=port,
            state=self._state,
            mode=self._config.mode,
            is_tls=self._config.use_tls,
            established_at=self._established_at,
            last_activity_at=self._last_activity_at,
            bytes_sent=self._bytes_sent,
            bytes_received=self._bytes_received,
            messages_sent=self._messages_sent,
            messages_received=self._messages_received,
        )
    
    # =========================================================================
    # Callback Registration
    # =========================================================================
    
    def on_message(self, callback: MessageCallback):
        """Register message callback (Message Mode only)."""
        self._on_message = callback
    
    def on_bytes(self, callback: BytesCallback):
        """Register bytes callback (Stream Mode only)."""
        self._on_bytes = callback
    
    def on_state_change(self, callback: StateCallback):
        """Register state change callback."""
        self._on_state_change = callback
    
    def on_close(self, callback: Callable[["Connection"], Awaitable[None] | None]):
        """Register close callback."""
        self._on_close = callback
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start_receiving(self):
        """Start the receive loop as a background task."""
        if self._receive_task is not None:
            return
        
        if self._config.mode == SocketMode.MESSAGE:
            coro = self._message_receive_loop()
        else:
            coro = self._stream_receive_loop()
        
        self._receive_task = asyncio.create_task(coro)
    
    async def close(self):
        """Close the connection gracefully."""
        if self._closed:
            return
        
        self._closed = True
        self._set_state(ConnectionState.DISCONNECTING)
        
        # Cancel receive task
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except (asyncio.CancelledError, Exception):
                pass
            self._receive_task = None
        
        # Close writer
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except Exception:
            pass
        
        self._set_state(ConnectionState.DISCONNECTED)
        
        # Invoke close callback
        if self._on_close:
            try:
                result = self._on_close(self)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
    
    def _set_state(self, new_state: ConnectionState):
        """Update connection state and invoke callback."""
        if self._state == new_state:
            return
        
        old_state = self._state
        self._state = new_state
        
        if self._on_state_change:
            try:
                result = self._on_state_change(new_state, self)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception:
                pass
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    async def send_message(self, message: SocketMessage) -> int:
        """
        Send a framed message (Message Mode only).
        
        Args:
            message: The message to send
        
        Returns:
            Number of bytes written
        
        Raises:
            ConnectionError: If not in message mode or connection closed
        """
        if self._closed:
            raise ConnectionClosedError("Cannot send on closed connection")
        
        if self._config.mode != SocketMode.MESSAGE:
            raise ConnectionError(
                "send_message() only works in MESSAGE mode. "
                "Use send_bytes() for STREAM mode."
            )
        
        if self._protocol is None:
            raise ConnectionError("No protocol configured for message mode")
        
        bytes_written = await self._protocol.write_message(self._writer, message)
        self._bytes_sent += bytes_written
        self._messages_sent += 1
        self._last_activity_at = datetime.now()
        
        return bytes_written
    
    async def send_bytes(self, data: bytes) -> int:
        """
        Send raw bytes (works in any mode).
        
        Args:
            data: Bytes to send
        
        Returns:
            Number of bytes written
        """
        if self._closed:
            raise ConnectionClosedError("Cannot send on closed connection")
        
        try:
            self._writer.write(data)
            await self._writer.drain()
            self._bytes_sent += len(data)
            self._last_activity_at = datetime.now()
            return len(data)
        except Exception as e:
            raise ConnectionClosedError(f"Failed to send bytes: {e}") from e
    
    async def send_ping(self) -> int:
        """Send a PING message (Message Mode only)."""
        return await self.send_message(SocketMessage(type=MessageType.PING))
    
    async def send_pong(self, correlation_id: Optional[str] = None) -> int:
        """Send a PONG message (Message Mode only)."""
        return await self.send_message(
            SocketMessage(
                type=MessageType.PONG,
                correlation_id=correlation_id,
            )
        )
    
    # =========================================================================
    # Receive Loops
    # =========================================================================
    
    async def _message_receive_loop(self):
        """Receive loop for Message Mode."""
        try:
            while not self._closed:
                try:
                    message = await self._protocol.read_message(self._reader)
                    self._messages_received += 1
                    self._last_activity_at = datetime.now()
                    
                    # Handle PING automatically
                    if message.type == MessageType.PING:
                        await self.send_pong(correlation_id=message.message_id)
                        continue
                    
                    # Invoke callback
                    if self._on_message:
                        try:
                            result = self._on_message(message, self)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception:
                            pass
                
                except asyncio.IncompleteReadError:
                    # Connection closed by peer
                    break
                except asyncio.CancelledError:
                    raise
                except ConnectionClosedError:
                    break
                except Exception:
                    # Log and continue for non-fatal errors
                    continue
        
        except asyncio.CancelledError:
            pass
        finally:
            if not self._closed:
                await self.close()
    
    async def _stream_receive_loop(self):
        """Receive loop for Stream Mode."""
        try:
            while not self._closed:
                try:
                    # Read in chunks for efficiency
                    data = await self._reader.read(65536)  # 64KB chunks
                    if not data:
                        # Connection closed by peer
                        break
                    
                    self._bytes_received += len(data)
                    self._last_activity_at = datetime.now()
                    
                    # Invoke callback
                    if self._on_bytes:
                        try:
                            result = self._on_bytes(data, self)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception:
                            pass
                
                except asyncio.CancelledError:
                    raise
                except Exception:
                    break
        
        except asyncio.CancelledError:
            pass
        finally:
            if not self._closed:
                await self.close()
    
    # =========================================================================
    # Utility
    # =========================================================================
    
    def update_activity(self):
        """Manually update last activity timestamp."""
        self._last_activity_at = datetime.now()
    
    def add_stats(self, bytes_sent: int = 0, bytes_received: int = 0):
        """Manually add to byte counters."""
        self._bytes_sent += bytes_sent
        self._bytes_received += bytes_received
    
    def __repr__(self):
        host, port = self.remote_address
        return (
            f"Connection(peer_id={self._peer_id}, "
            f"remote={host}:{port}, "
            f"state={self._state.value}, "
            f"mode={self._config.mode.value})"
        )