"""
Exception hierarchy for network_socket module.
"""


class SocketError(Exception):
    """Base exception for all socket-related errors."""
    pass


class SocketConfigError(SocketError):
    """Raised when socket configuration is invalid."""
    pass


class ConnectionError(SocketError):
    """Raised when a connection operation fails."""
    pass


class ConnectionTimeoutError(ConnectionError):
    """Raised when a connection attempt times out."""
    pass


class ConnectionClosedError(ConnectionError):
    """Raised when operating on a closed connection."""
    pass


class ConnectionRefusedError(ConnectionError):
    """Raised when a connection is refused by the peer."""
    pass


class FramingError(SocketError):
    """Raised when message framing fails."""
    pass


class MessageTooLargeError(FramingError):
    """Raised when a message exceeds the maximum allowed size."""
    pass


class CodecError(FramingError):
    """Raised when message encoding/decoding fails."""
    pass


class PoolError(SocketError):
    """Raised when connection pool operations fail."""
    pass


class HeartbeatTimeoutError(SocketError):
    """Raised when a peer fails to respond to heartbeats."""
    pass