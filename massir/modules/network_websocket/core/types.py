"""
Type definitions for network_websocket module.

Defines WebSocket-specific types. Message types (SocketMessage, MessageType)
are intentionally NOT defined here - they belong to application-level modules
or a future shared transport-types module.

This module focuses purely on WebSocket transport concerns:
- Connection configuration (URLs, paths, subprotocols)
- Close codes (RFC 6455)
- Frame types
- Connection state information
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum, IntEnum


class WebSocketCloseCode(IntEnum):
    """
    Standard WebSocket close codes (RFC 6455 Section 7.4.1).
    
    These codes indicate the reason for connection closure and are
    exchanged during the WebSocket close handshake.
    """
    
    # Standard codes (1000-2999)
    NORMAL = 1000                    # Normal closure
    GOING_AWAY = 1001                # Endpoint is going away (server shutdown, browser navigation)
    PROTOCOL_ERROR = 1002            # Protocol error
    UNSUPPORTED_DATA = 1003          # Received unsupported data type
    RESERVED = 1004                  # Reserved
    NO_STATUS = 1005                 # No status code present (reserved, not sent)
    ABNORMAL_CLOSURE = 1006          # Abnormal closure (reserved, not sent)
    INVALID_PAYLOAD = 1007           # Inconsistent data (e.g., non-UTF8 in text frame)
    POLICY_VIOLATION = 1008          # Generic policy violation
    MESSAGE_TOO_BIG = 1009           # Message too big to process
    MANDATORY_EXTENSION = 1010       # Client expected server to negotiate extensions
    INTERNAL_ERROR = 1011            # Server encountered unexpected condition
    SERVICE_RESTART = 1012           # Service is restarting
    TRY_AGAIN_LATER = 1013           # Temporary condition, try again later
    BAD_GATEWAY = 1014               # Bad gateway (upstream server issue)
    TLS_HANDSHAKE = 1015             # TLS handshake failure (reserved, not sent)
    
    # Application-specific codes (4000-4999) for Massir
    APP_HEARTBEAT_TIMEOUT = 4001     # Peer failed heartbeat checks
    APP_PEER_SHUTDOWN = 4002         # Peer is shutting down gracefully
    APP_AUTH_FAILED = 4003           # Authentication failed
    APP_PROTOCOL_MISMATCH = 4004     # Subprotocol negotiation failed
    APP_RATE_LIMITED = 4005          # Rate limit exceeded
    APP_NODE_REJECTED = 4006         # Node rejected by policy
    APP_VERSION_MISMATCH = 4007      # Protocol version mismatch


class WebSocketFrameType(str, Enum):
    """Types of WebSocket frames as defined in RFC 6455."""
    
    TEXT = "text"           # UTF-8 encoded text (used for JSON messages)
    BINARY = "binary"       # Raw binary data (used for streams)
    PING = "ping"           # Protocol-level ping (auto-responded with pong)
    PONG = "pong"           # Protocol-level pong response
    CLOSE = "close"         # Connection close frame


class ConnectionState(str, Enum):
    """State of a WebSocket connection."""
    
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


@dataclass
class WebSocketConfig:
    """
    Configuration for a WebSocket connection.
    
    WebSocket-specific configuration including URLs, paths, subprotocols,
    HTTP headers, and compression settings.
    """
    
    # Target (for client mode)
    host: Optional[str] = None
    port: Optional[int] = None
    path: str = "/ws"
    use_tls: bool = True
    
    # Full URL alternative (overrides host/port/path)
    url: Optional[str] = None
    
    # WebSocket protocol features
    subprotocol: Optional[str] = None
    additional_headers: dict[str, str] = field(default_factory=dict)
    compression_enabled: bool = True
    
    # Framing limits
    max_size_bytes: int = 16 * 1024 * 1024  # 16 MB
    
    # Protocol-level ping/pong (WebSocket native heartbeat)
    ping_interval: Optional[float] = 20.0
    ping_timeout: Optional[float] = 60.0
    
    # Connection timeouts
    connect_timeout: float = 10.0
    
    # Reconnection behavior
    reconnect_enabled: bool = True
    reconnect_initial_delay: float = 2.0
    reconnect_max_delay: float = 60.0
    reconnect_backoff_multiplier: float = 2.0
    reconnect_max_attempts: int = 0  # 0 = unlimited
    
    # Peer identification (for pool management)
    peer_id: Optional[str] = None
    
    # Backpressure
    send_queue_size: int = 1000
    
    def build_url(self) -> str:
        """
        Build the WebSocket URL from configuration.
        
        Returns the full wss:// or ws:// URL with path.
        If 'url' field is set, returns it directly.
        """
        if self.url:
            return self.url
        
        scheme = "wss" if self.use_tls else "ws"
        path = self.path if self.path.startswith("/") else f"/{self.path}"
        return f"{scheme}://{self.host}:{self.port}{path}"
    
    def __post_init__(self):
        if not self.url:
            if self.host is None:
                raise ValueError("Either 'url' or 'host' must be provided")
            if self.port is None:
                self.port = 443 if self.use_tls else 80
            if self.port < 1 or self.port > 65535:
                raise ValueError(f"Port must be 1-65535, got {self.port}")
        
        if self.max_size_bytes < 1:
            raise ValueError("max_size_bytes must be positive")


@dataclass
class WebSocketConnectionInfo:
    """
    Information about an active WebSocket connection.
    
    Captures all relevant metadata about the connection including
    WebSocket-specific details like negotiated subprotocol and close codes.
    """
    
    # Basic connection info
    peer_id: Optional[str]
    host: str
    port: int
    state: ConnectionState
    is_tls: bool
    
    # Timestamps
    established_at: datetime = field(default_factory=lambda: datetime.now())
    last_activity_at: datetime = field(default_factory=lambda: datetime.now())
    
    # Statistics
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    reconnect_count: int = 0
    
    # Latency tracking
    latency_ms: Optional[float] = None
    
    # WebSocket-specific
    url: str = ""
    path: str = "/ws"
    subprotocol: Optional[str] = None
    compression_enabled: bool = False
    close_code: Optional[int] = None
    close_reason: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "state": self.state.value,
            "is_tls": self.is_tls,
            "established_at": self.established_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "reconnect_count": self.reconnect_count,
            "latency_ms": self.latency_ms,
            "url": self.url,
            "path": self.path,
            "subprotocol": self.subprotocol,
            "compression_enabled": self.compression_enabled,
            "close_code": self.close_code,
            "close_reason": self.close_reason,
        }


# Type alias for peer identifiers
PeerId = str