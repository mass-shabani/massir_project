"""
Type definitions for network_socket module.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, NewType, Optional
from datetime import datetime

# Type aliases
PeerId = NewType("PeerId", str)


class MessageType(str, Enum):
    """Types of messages in the socket protocol."""
    
    DATA = "data"           # Application data
    PING = "ping"           # Heartbeat ping
    PONG = "pong"           # Heartbeat pong response
    HANDSHAKE = "handshake" # Initial connection handshake
    HANDSHAKE_ACK = "handshake_ack"
    CLOSE = "close"         # Graceful close request
    ERROR = "error"         # Error notification
    
    # Control messages
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


class ConnectionState(str, Enum):
    """State of a socket connection."""
    
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


class SocketMode(str, Enum):
    """Operating mode for a socket."""
    
    MESSAGE = "message"     # Framed messages with codec
    STREAM = "stream"       # Raw byte passthrough


@dataclass
class SocketConfig:
    """Configuration for a socket connection."""
    
    host: str
    port: int
    mode: SocketMode = SocketMode.MESSAGE
    use_tls: bool = True
    peer_id: Optional[PeerId] = None
    
    # Timeouts (seconds)
    connect_timeout: float = 10.0
    read_timeout: Optional[float] = None
    write_timeout: Optional[float] = None
    
    # Reconnect settings
    reconnect_enabled: bool = True
    reconnect_initial_delay: float = 1.0
    reconnect_max_delay: float = 60.0
    reconnect_backoff_multiplier: float = 2.0
    reconnect_max_attempts: int = 0  # 0 = unlimited
    
    # Framing
    max_message_size: int = 16 * 1024 * 1024  # 16 MB
    length_prefix_bytes: int = 4
    
    # Send queue
    send_queue_size: int = 1000
    
    def __post_init__(self):
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {self.port}")
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be positive")
        if self.max_message_size < 1:
            raise ValueError("max_message_size must be at least 1")
        if self.length_prefix_bytes not in (2, 4, 8):
            raise ValueError("length_prefix_bytes must be 2, 4, or 8")


@dataclass
class SocketMessage:
    """A framed message with header and payload."""
    
    type: MessageType
    payload: Any = None
    message_id: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "payload": self.payload,
            "message_id": self.message_id,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SocketMessage":
        """Create from dictionary."""
        msg_type = data.get("type")
        if isinstance(msg_type, str):
            try:
                msg_type = MessageType(msg_type)
            except ValueError:
                msg_type = MessageType.DATA
        
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        else:
            timestamp = datetime.now()
        
        return cls(
            type=msg_type,
            payload=data.get("payload"),
            message_id=data.get("message_id"),
            correlation_id=data.get("correlation_id"),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )


@dataclass
class NodeInfo:
    """Information about a network node."""
    
    node_id: PeerId
    host: str
    port: int
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.node_id)
    
    def __eq__(self, other):
        if not isinstance(other, NodeInfo):
            return False
        return self.node_id == other.node_id


@dataclass
class ConnectionInfo:
    """Information about an active connection."""
    
    peer_id: Optional[PeerId]
    host: str
    port: int
    state: ConnectionState
    mode: SocketMode
    is_tls: bool
    established_at: datetime = field(default_factory=lambda: datetime.now())
    last_activity_at: datetime = field(default_factory=lambda: datetime.now())
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    reconnect_count: int = 0
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "state": self.state.value,
            "mode": self.mode.value,
            "is_tls": self.is_tls,
            "established_at": self.established_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "reconnect_count": self.reconnect_count,
            "latency_ms": self.latency_ms,
        }