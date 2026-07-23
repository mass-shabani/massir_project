"""
Exception hierarchy for network_websocket module.

WebSocket-specific exceptions with close codes where applicable.
"""


class WebSocketError(Exception):
    """Base exception for all WebSocket-related errors."""
    pass


class WebSocketConfigError(WebSocketError):
    """Raised when WebSocket configuration is invalid."""
    pass


class WebSocketConnectionError(WebSocketError):
    """Raised when a WebSocket connection operation fails."""
    
    def __init__(self, message: str, close_code: int | None = None):
        super().__init__(message)
        self.close_code = close_code


class WebSocketConnectionTimeoutError(WebSocketConnectionError):
    """Raised when a connection attempt times out."""
    pass


class WebSocketConnectionClosedError(WebSocketConnectionError):
    """Raised when operating on a closed WebSocket connection."""
    
    def __init__(
        self,
        message: str = "Connection closed",
        close_code: int | None = None,
        close_reason: str | None = None,
    ):
        super().__init__(message, close_code)
        self.close_reason = close_reason


class WebSocketHandshakeError(WebSocketConnectionError):
    """Raised when WebSocket HTTP upgrade handshake fails."""
    
    def __init__(self, message: str, http_status: int | None = None):
        super().__init__(message)
        self.http_status = http_status


class WebSocketProtocolError(WebSocketError):
    """Raised when WebSocket protocol violations occur."""
    pass


class PoolError(WebSocketError):
    """Raised when connection pool operations fail."""
    pass