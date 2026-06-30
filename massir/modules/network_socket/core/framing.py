"""
Message framing and codec abstraction.

Supports:
- Length-prefix framing for Message Mode
- Raw byte passthrough for Stream Mode
- Pluggable codecs (JSON, MessagePack, etc.)
"""

import json
import struct
from abc import ABC, abstractmethod
from typing import Any, Optional

from .types import SocketMessage, MessageType
from .exceptions import (
    FramingError,
    MessageTooLargeError,
    CodecError,
)


class MessageCodec(ABC):
    """Abstract base class for message codecs."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Codec identifier name."""
        pass
    
    @abstractmethod
    def encode(self, message: SocketMessage) -> bytes:
        """
        Encode a SocketMessage to bytes.
        
        Args:
            message: The message to encode
        
        Returns:
            Encoded bytes (without length prefix)
        """
        pass
    
    @abstractmethod
    def decode(self, data: bytes) -> SocketMessage:
        """
        Decode bytes to a SocketMessage.
        
        Args:
            data: Bytes to decode
        
        Returns:
            Decoded SocketMessage
        """
        pass


class JsonCodec(MessageCodec):
    """JSON-based message codec."""
    
    @property
    def name(self) -> str:
        return "json"
    
    def encode(self, message: SocketMessage) -> bytes:
        """Encode message to JSON bytes."""
        try:
            data = message.to_dict()
            return json.dumps(data, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as e:
            raise CodecError(f"Failed to encode message as JSON: {e}") from e
    
    def decode(self, data: bytes) -> SocketMessage:
        """Decode JSON bytes to message."""
        try:
            json_str = data.decode("utf-8")
            parsed = json.loads(json_str)
            return SocketMessage.from_dict(parsed)
        except UnicodeDecodeError as e:
            raise CodecError(f"Invalid UTF-8 in message: {e}") from e
        except json.JSONDecodeError as e:
            raise CodecError(f"Invalid JSON in message: {e}") from e
        except Exception as e:
            raise CodecError(f"Failed to decode message: {e}") from e


class MsgPackCodec(MessageCodec):
    """
    MessagePack-based message codec.
    
    Requires msgpack library (optional dependency).
    """
    
    def __init__(self):
        try:
            import msgpack  # type: ignore
            self._msgpack = msgpack
        except ImportError:
            self._msgpack = None
    
    @property
    def name(self) -> str:
        return "msgpack"
    
    def encode(self, message: SocketMessage) -> bytes:
        """Encode message to MessagePack bytes."""
        if self._msgpack is None:
            raise CodecError(
                "msgpack library not installed. "
                "Install with: pip install msgpack"
            )
        try:
            data = message.to_dict()
            return self._msgpack.packb(data, use_bin_type=True)
        except Exception as e:
            raise CodecError(f"Failed to encode message as MessagePack: {e}") from e
    
    def decode(self, data: bytes) -> SocketMessage:
        """Decode MessagePack bytes to message."""
        if self._msgpack is None:
            raise CodecError(
                "msgpack library not installed. "
                "Install with: pip install msgpack"
            )
        try:
            parsed = self._msgpack.unpackb(data, raw=False)
            return SocketMessage.from_dict(parsed)
        except Exception as e:
            raise CodecError(f"Failed to decode MessagePack message: {e}") from e


# Registry of available codecs
_CODEC_REGISTRY: dict[str, type[MessageCodec]] = {
    "json": JsonCodec,
    "msgpack": MsgPackCodec,
}


def get_codec(name: str) -> MessageCodec:
    """
    Get a codec instance by name.
    
    Args:
        name: Codec name ("json", "msgpack", etc.)
    
    Returns:
        Codec instance
    
    Raises:
        CodecError: If codec is not registered
    """
    codec_class = _CODEC_REGISTRY.get(name.lower())
    if codec_class is None:
        available = ", ".join(_CODEC_REGISTRY.keys())
        raise CodecError(
            f"Unknown codec: '{name}'. Available: {available}"
        )
    return codec_class()


def register_codec(name: str, codec_class: type[MessageCodec]) -> None:
    """
    Register a custom codec.
    
    Args:
        name: Codec name
        codec_class: Codec class (must inherit from MessageCodec)
    """
    if not issubclass(codec_class, MessageCodec):
        raise TypeError(f"Codec must inherit from MessageCodec")
    _CODEC_REGISTRY[name.lower()] = codec_class


class LengthPrefixProtocol:
    """
    Length-prefix framing protocol for Message Mode.
    
    Format: [length (N bytes, big-endian)] [payload (length bytes)]
    
    Where N is configurable (2, 4, or 8 bytes).
    """
    
    # Map length_prefix_bytes to struct format
    _FORMAT_MAP = {
        2: ">H",   # unsigned short (max 65535)
        4: ">I",   # unsigned int (max 4GB)
        8: ">Q",   # unsigned long long
    }
    
    def __init__(
        self,
        codec: MessageCodec,
        length_prefix_bytes: int = 4,
        max_message_size: int = 16 * 1024 * 1024,
    ):
        """
        Initialize the protocol.
        
        Args:
            codec: Message codec to use
            length_prefix_bytes: Size of length prefix (2, 4, or 8)
            max_message_size: Maximum allowed message size in bytes
        """
        if length_prefix_bytes not in self._FORMAT_MAP:
            raise ValueError(
                f"length_prefix_bytes must be 2, 4, or 8, got {length_prefix_bytes}"
            )
        
        self._codec = codec
        self._length_prefix_bytes = length_prefix_bytes
        self._max_message_size = max_message_size
        self._format = self._FORMAT_MAP[length_prefix_bytes]
        
        # Calculate max based on prefix size
        max_by_prefix = (1 << (8 * length_prefix_bytes)) - 1
        if max_message_size > max_by_prefix:
            raise ValueError(
                f"max_message_size ({max_message_size}) exceeds "
                f"max for {length_prefix_bytes}-byte prefix ({max_by_prefix})"
            )
    
    @property
    def codec(self) -> MessageCodec:
        """Get the codec."""
        return self._codec
    
    @property
    def length_prefix_bytes(self) -> int:
        """Get the length prefix size."""
        return self._length_prefix_bytes
    
    @property
    def max_message_size(self) -> int:
        """Get the max message size."""
        return self._max_message_size
    
    def encode_message(self, message: SocketMessage) -> bytes:
        """
        Encode a message with length prefix.
        
        Args:
            message: The message to encode
        
        Returns:
            Bytes containing length prefix + encoded payload
        
        Raises:
            MessageTooLargeError: If encoded message exceeds max size
        """
        payload = self._codec.encode(message)
        payload_len = len(payload)
        
        if payload_len > self._max_message_size:
            raise MessageTooLargeError(
                f"Message size {payload_len} exceeds max {self._max_message_size}"
            )
        
        header = struct.pack(self._format, payload_len)
        return header + payload
    
    def decode_message(self, data: bytes) -> SocketMessage:
        """
        Decode a complete message (without length prefix).
        
        Args:
            data: The payload bytes (length prefix already stripped)
        
        Returns:
            Decoded SocketMessage
        """
        return self._codec.decode(data)
    
    async def read_message(self, reader) -> SocketMessage:
        """
        Read a complete framed message from an asyncio StreamReader.
        
        Args:
            reader: asyncio.StreamReader
        
        Returns:
            Decoded SocketMessage
        
        Raises:
            FramingError: If reading fails
            ConnectionClosedError: If connection is closed
        """
        from .exceptions import ConnectionClosedError
        
        # Read length prefix
        header_bytes = await reader.readexactly(self._length_prefix_bytes)
        if not header_bytes:
            raise ConnectionClosedError("Connection closed while reading header")
        
        payload_len = struct.unpack(self._format, header_bytes)[0]
        
        if payload_len > self._max_message_size:
            raise MessageTooLargeError(
                f"Received message size {payload_len} exceeds max {self._max_message_size}"
            )
        
        if payload_len == 0:
            # Empty payload - return a PING-like message
            return SocketMessage(type=MessageType.PING)
        
        # Read payload
        try:
            payload = await reader.readexactly(payload_len)
        except Exception as e:
            raise FramingError(f"Failed to read message payload: {e}") from e
        
        return self.decode_message(payload)
    
    async def write_message(
        self,
        writer,
        message: SocketMessage,
    ) -> int:
        """
        Write a framed message to an asyncio StreamWriter.
        
        Args:
            writer: asyncio.StreamWriter
            message: The message to write
        
        Returns:
            Number of bytes written
        
        Raises:
            ConnectionClosedError: If connection is closed
        """
        from .exceptions import ConnectionClosedError
        
        try:
            data = self.encode_message(message)
            writer.write(data)
            await writer.drain()
            return len(data)
        except ConnectionError as e:
            raise ConnectionClosedError(f"Connection closed: {e}") from e
        except Exception as e:
            raise FramingError(f"Failed to write message: {e}") from e