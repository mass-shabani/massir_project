"""
Network Socket Core Module

Provides async TCP/UDP socket programming for the Massir framework:
- Message Mode: length-prefix framing with pluggable codecs
- Stream Mode: zero-copy byte passthrough
- Connection pooling per peer
- Auto-reconnect with exponential backoff
- Heartbeat monitoring
- Optional TLS (via ssl_api) and encryption (via encryption_api)
"""

from .types import (
    SocketConfig,
    SocketMessage,
    ConnectionInfo,
    MessageType,
    ConnectionState,
    NodeInfo,
    PeerId,
)
from .framing import (
    MessageCodec,
    JsonCodec,
    MsgPackCodec,
    LengthPrefixProtocol,
)
from .connection import Connection
from .server import SocketServer
from .client import SocketClient
from .pool import ConnectionPool
from .heartbeat import HeartbeatMonitor
from .socket_api import SocketAPI
from .exceptions import (
    SocketError,
    SocketConfigError,
    ConnectionError,
    ConnectionTimeoutError,
    ConnectionClosedError,
    FramingError,
    MessageTooLargeError,
    CodecError,
    PoolError,
    HeartbeatTimeoutError,
)

__all__ = [
    # Types
    "SocketConfig",
    "SocketMessage",
    "ConnectionInfo",
    "MessageType",
    "ConnectionState",
    "NodeInfo",
    "PeerId",
    # Framing
    "MessageCodec",
    "JsonCodec",
    "MsgPackCodec",
    "LengthPrefixProtocol",
    # Connection management
    "Connection",
    "SocketServer",
    "SocketClient",
    "ConnectionPool",
    "HeartbeatMonitor",
    # API
    "SocketAPI",
    # Exceptions
    "SocketError",
    "SocketConfigError",
    "ConnectionError",
    "ConnectionTimeoutError",
    "ConnectionClosedError",
    "FramingError",
    "MessageTooLargeError",
    "CodecError",
    "PoolError",
    "HeartbeatTimeoutError",
]