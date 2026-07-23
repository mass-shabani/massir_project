"""
WebSocket server with multi-path support.

Hosts WebSocket services on specific URL paths, allowing multiple
WebSocket services to coexist on the same port (e.g., /ws, /ws/v2, /admin).
"""

import asyncio
import ssl
import websockets
from typing import Any, Callable, Optional, Awaitable

from .types import (
    WebSocketConfig,
    WebSocketCloseCode,
    PeerId,
)
from .connection import WebSocketConnection

# Callback types
ConnectionCallback = Callable[[WebSocketConnection], Awaitable[None] | None]
ProcessRequestCallback = Callable[
    [Any, str], Awaitable[Optional[tuple[int, str, list[tuple[str, str]]]]]
]


class WebSocketServer:
    """
    WebSocket server supporting path-based routing and TLS.
    
    Unlike raw TCP servers, WebSocket servers operate on top of HTTP and
    can distinguish connections by URL path, allowing multiple logical
    services on a single port.
    
    Features:
    - Path-based routing (/ws, /ws/v2, etc.)
    - Origin validation (CORS-like)
    - Custom request processing (authentication, rate limiting)
    - Subprotocol negotiation
    - Compression (permessage-deflate)
    """
    
    def __init__(
        self,
        config: WebSocketConfig,
        logger: Any = None,
        ssl_context: Optional[ssl.SSLContext] = None,
    ):
        self._config = config
        self._logger = logger
        self._ssl_context = ssl_context
        self._server: Optional[websockets.WebSocketServer] = None
        
        # Active connections
        self._connections: dict[PeerId | tuple[str, int], WebSocketConnection] = {}
        
        # Callbacks
        self._on_connection: Optional[ConnectionCallback] = None
        self._on_disconnection: Optional[ConnectionCallback] = None
        self._process_request: Optional[ProcessRequestCallback] = None
        
        # Allowed origins for security
        self._allowed_origins: list[str] = ["*"]
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def set_ssl_context(self, ssl_context: ssl.SSLContext):
        """Set the TLS context for WSS."""
        self._ssl_context = ssl_context
    
    def set_allowed_origins(self, origins: list[str]):
        """
        Set allowed origins for WebSocket connections.
        
        Args:
            origins: List of allowed origin strings, or ["*"] for any
        """
        self._allowed_origins = origins
    
    def on_connection(self, callback: ConnectionCallback):
        """Register callback for new connections."""
        self._on_connection = callback
    
    def on_disconnection(self, callback: ConnectionCallback):
        """Register callback for closed connections."""
        self._on_disconnection = callback
    
    def set_process_request(self, callback: ProcessRequestCallback):
        """
        Register custom request processing callback.
        
        Called during HTTP upgrade handshake. Can be used for:
        - Authentication (check Authorization header)
        - Rate limiting
        - Custom subprotocol selection
        
        Return None to accept, or (status_code, reason, headers) to reject.
        """
        self._process_request = callback
    
    def get_connections(self) -> list[WebSocketConnection]:
        """Get all active connections."""
        return list(self._connections.values())
    
    def get_connection(self, peer_id: PeerId) -> Optional[WebSocketConnection]:
        """Get a specific connection by peer_id."""
        return self._connections.get(peer_id)
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self):
        """Start the WebSocket server."""
        if self._server is not None:
            return
        
        # Build server kwargs
        server_kwargs = {
            "handler": self._handle_client,
            "host": self._config.host,
            "port": self._config.port,
            "ssl": self._ssl_context,
            "max_size": self._config.max_size_bytes,
            "ping_interval": self._config.ping_interval,
            "ping_timeout": self._config.ping_timeout,
        }
        
        # Compression
        if self._config.compression_enabled:
            server_kwargs["compression"] = "deflate"
        else:
            server_kwargs["compression"] = None
        
        # Subprotocol negotiation (server offers list)
        if self._config.subprotocol:
            server_kwargs["subprotocols"] = [self._config.subprotocol]
        
        # Custom request processing
        if self._process_request:
            server_kwargs["process_request"] = self._process_request
        
        # Origin validation
        if self._allowed_origins and self._allowed_origins != ["*"]:
            server_kwargs["origins"] = self._allowed_origins
        
        try:
            self._server = await websockets.serve(**server_kwargs)
            
            if self._logger:
                tls_str = "WSS" if self._ssl_context else "WS"
                subprotocol_str = (
                    f", subprotocol={self._config.subprotocol}"
                    if self._config.subprotocol else ""
                )
                self._logger.log(
                    f"WebSocketServer started on "
                    f"{self._config.host}:{self._config.port}{self._config.path} "
                    f"({tls_str}{subprotocol_str})",
                    tag="websocket"
                )
        
        except Exception as e:
            from .exceptions import WebSocketConfigError
            raise WebSocketConfigError(
                f"Failed to start WebSocket server on "
                f"{self._config.host}:{self._config.port}: {e}"
            ) from e
    
    async def stop(self):
        """Stop the server and close all connections."""
        if self._server is None:
            return
        
        # Gracefully close all active connections
        connections = list(self._connections.values())
        for conn in connections:
            try:
                await conn.close(
                    code=WebSocketCloseCode.GOING_AWAY,
                    reason="Server shutting down",
                )
            except Exception:
                pass
        
        self._connections.clear()
        
        # Close the server
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        
        if self._logger:
            self._logger.log(
                f"WebSocketServer stopped on "
                f"{self._config.host}:{self._config.port}",
                tag="websocket"
            )
    
    # =========================================================================
    # Connection Handling
    # =========================================================================
    
    async def _handle_client(self, ws: websockets.WebSocketClientProtocol):
        """Handle a new WebSocket client connection."""
        # Path validation
        request_path = getattr(ws, 'path', '/') or '/'
        expected_path = self._config.path
        if not expected_path.startswith('/'):
            expected_path = f"/{expected_path}"
        
        if request_path != expected_path:
            if self._logger:
                self._logger.log(
                    f"Rejected connection: path '{request_path}' != expected '{expected_path}'",
                    level="WARNING",
                    tag="websocket"
                )
            await ws.close(
                code=WebSocketCloseCode.POLICY_VIOLATION,
                reason="Invalid path",
            )
            return
        
        # Get remote address
        try:
            remote = ws.remote_address
            remote_str = f"{remote[0]}:{remote[1]}" if remote else "unknown"
        except Exception:
            remote_str = "unknown"
            remote = None
        
        if self._logger:
            subprotocol = getattr(ws, 'subprotocol', None)
            self._logger.log(
                f"New WebSocket connection from {remote_str}"
                f"{f' (subprotocol: {subprotocol})' if subprotocol else ''}",
                tag="websocket"
            )
        
        # Build connection config
        conn_config = WebSocketConfig(
            host=remote[0] if remote else "",
            port=remote[1] if remote else 0,
            path=request_path,
            use_tls=self._ssl_context is not None,
            max_size_bytes=self._config.max_size_bytes,
            compression_enabled=self._config.compression_enabled,
            ping_interval=self._config.ping_interval,
            ping_timeout=self._config.ping_timeout,
        )
        
        # Create connection wrapper
        connection = WebSocketConnection(
            config=conn_config,
            ws=ws,
            is_server_side=True,
            logger=self._logger,
        )
        
        # Register close handler
        async def on_close(conn: WebSocketConnection, code: int, reason: str):
            key = conn.peer_id if conn.peer_id else conn.remote_address
            if key in self._connections and self._connections[key] is conn:
                del self._connections[key]
            
            if self._on_disconnection:
                try:
                    result = self._on_disconnection(conn)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    pass
        
        connection.on_close(on_close)
        
        # Store connection by remote address (until peer_id is set)
        key = connection.remote_address
        self._connections[key] = connection
        
        # Invoke connection callback
        if self._on_connection:
            try:
                result = self._on_connection(connection)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in on_connection callback: {e}",
                        level="ERROR",
                        tag="websocket"
                    )
        
        # Start receiving (blocks until connection closes)
        await connection.start_receiving()
        
        # Wait for receive task to complete
        if connection._receive_task:
            try:
                await connection._receive_task
            except Exception:
                pass
    
    # =========================================================================
    # Utility
    # =========================================================================
    
    def register_peer(self, connection: WebSocketConnection, peer_id: PeerId):
        """Re-key a connection by peer_id."""
        old_key = connection.remote_address
        if old_key in self._connections and self._connections[old_key] is connection:
            del self._connections[old_key]
        
        connection.peer_id = peer_id
        self._connections[peer_id] = connection
    
    def __repr__(self):
        return (
            f"WebSocketServer(host={self._config.host}, "
            f"port={self._config.port}, path={self._config.path}, "
            f"connections={len(self._connections)})"
        )