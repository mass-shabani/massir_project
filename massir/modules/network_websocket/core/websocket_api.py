"""
Unified WebSocket API.

Provides a WebSocket-specific API optimized for cloud-friendly deployments.
Unlike network_socket's API, this exposes WebSocket-specific features:

- URL-based connections (wss://example.com/ws)
- Path-based routing (multiple services on one port)
- Subprotocol negotiation (massir.v1, etc.)
- Custom HTTP headers (Authorization, cookies)
- Close codes with reasons (RFC 6455)
- Built-in compression (permessage-deflate)
- Native ping/pong heartbeat

For unified transport management across multiple protocols, use the
system_network module which adapts both socket_api and websocket_api
to a common interface.
"""

import asyncio
import ssl
from typing import Any, Optional

from .types import (
    WebSocketConfig,
    WebSocketCloseCode,
    PeerId,
)
from .connection import WebSocketConnection
from .server import WebSocketServer
from .client import WebSocketClient
from .pool import WebSocketConnectionPool
from .heartbeat import WebSocketHeartbeatMonitor


class WebSocketAPI:
    """
    WebSocket transport API.
    
    Provides WebSocket-specific operations optimized for cloud environments.
    Message structure is not enforced here - higher layers (system_network,
    application modules) define message formats.
    """
    
    # Expose close codes for application use
    CloseCode = WebSocketCloseCode
    
    def __init__(self, config: dict, logger: Any = None):
        self._config = config
        self._logger = logger
        self._ssl_api = None
        self._encryption_api = None
        
        # Active servers (keyed by host:port:path)
        self._servers: dict[tuple[str, int, str], WebSocketServer] = {}
        
        # Connection pool
        pool_config = config.get("pool", {})
        self._pool = WebSocketConnectionPool(
            max_per_peer=pool_config.get("max_connections_per_peer", 3),
            idle_timeout=pool_config.get("idle_timeout_seconds", 300.0),
            cleanup_interval=pool_config.get("cleanup_interval_seconds", 60.0),
            logger=logger,
        )
        
        # Heartbeat monitor
        hb_config = config.get("heartbeat", {})
        self._heartbeat = WebSocketHeartbeatMonitor(
            interval=hb_config.get("interval_seconds", 20.0),
            timeout=hb_config.get("timeout_seconds", 60.0),
            logger=logger,
        )
        
        # Global callbacks
        self._on_inbound_connection = None
        self._on_inbound_disconnection = None
        self._on_inbound_message = None
        self._on_inbound_bytes = None
    
    # =========================================================================
    # Service Integration
    # =========================================================================
    
    def set_ssl_api(self, ssl_api: Any):
        """Link with ssl_api for WSS support."""
        self._ssl_api = ssl_api
    
    def set_encryption_api(self, encryption_api: Any):
        """Link with encryption_api for application-level encryption."""
        self._encryption_api = encryption_api
    
    # =========================================================================
    # Global Callbacks
    # =========================================================================
    
    def on_inbound_connection(self, callback):
        """Register callback for inbound connections."""
        self._on_inbound_connection = callback
    
    def on_inbound_disconnection(self, callback):
        """Register callback for inbound disconnections."""
        self._on_inbound_disconnection = callback
    
    def on_inbound_message(self, callback):
        """Register callback for inbound messages (JSON dicts)."""
        self._on_inbound_message = callback
    
    def on_inbound_bytes(self, callback):
        """Register callback for inbound binary frames."""
        self._on_inbound_bytes = callback
    
    # =========================================================================
    # Server Management - WebSocket-Specific
    # =========================================================================
    
    async def create_server(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        use_tls: bool = True,
        compression: bool = True,
        subprotocol: Optional[str] = None,
        allowed_origins: Optional[list[str]] = None,
    ) -> WebSocketServer:
        """
        Create and start a WebSocket server on a specific path.
        
        Multiple servers can run on the same port with different paths:
            create_server(path="/ws/v1", ...)
            create_server(path="/ws/v2", ...)
            create_server(path="/admin", ...)
        
        Args:
            host: Bind host (default from config)
            port: Bind port (default from config, typically 443)
            path: URL path to serve on (default "/ws")
            use_tls: Use WSS (TLS) instead of WS
            compression: Enable permessage-deflate
            subprotocol: Subprotocol to offer (e.g., "massir.v1")
            allowed_origins: List of allowed origins (None = from config)
        
        Returns:
            WebSocketServer instance
        """
        server_config = self._config.get("server", {})
        hb_config = self._config.get("heartbeat", {})
        
        host = host or server_config.get("default_host", "0.0.0.0")
        port = port or server_config.get("default_port", 443)
        path = path or server_config.get("default_path", "/ws")
        subprotocol = subprotocol or server_config.get("subprotocol")
        
        config = WebSocketConfig(
            host=host,
            port=port,
            path=path,
            use_tls=use_tls,
            subprotocol=subprotocol,
            max_size_bytes=server_config.get("max_size_bytes", 16 * 1024 * 1024),
            compression_enabled=(
                compression and server_config.get("compression_enabled", True)
            ),
            ping_interval=hb_config.get("interval_seconds", 20.0),
            ping_timeout=hb_config.get("timeout_seconds", 60.0),
        )
        
        # Setup TLS
        ssl_context = None
        if use_tls and self._ssl_api:
            try:
                ssl_context = self._ssl_api.get_server_context("default")
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to setup TLS for WebSocket server: {e}. "
                        f"Falling back to plain WS.",
                        level="WARNING",
                        tag="websocket"
                    )
                config.use_tls = False
        
        server = WebSocketServer(config, self._logger, ssl_context)
        
        # Configure allowed origins
        if allowed_origins:
            server.set_allowed_origins(allowed_origins)
        elif "allowed_origins" in server_config:
            server.set_allowed_origins(server_config["allowed_origins"])
        
        # Wire up callbacks
        async def on_conn_with_handlers(conn: WebSocketConnection):
            # Message handler (JSON dicts)
            async def msg_handler(msg, c):
                if self._on_inbound_message:
                    result = self._on_inbound_message(msg, c)
                    if asyncio.iscoroutine(result):
                        await result
            
            # Bytes handler (binary frames)
            async def bytes_handler(data, c):
                if self._on_inbound_bytes:
                    result = self._on_inbound_bytes(data, c)
                    if asyncio.iscoroutine(result):
                        await result
            
            conn.on_message(msg_handler)
            conn.on_bytes(bytes_handler)
            
            if self._on_inbound_connection:
                result = self._on_inbound_connection(conn)
                if asyncio.iscoroutine(result):
                    await result
        
        async def on_disconn(conn: WebSocketConnection):
            if conn.peer_id:
                self._heartbeat.remove_connection(conn.peer_id)
            
            if self._on_inbound_disconnection:
                result = self._on_inbound_disconnection(conn)
                if asyncio.iscoroutine(result):
                    await result
        
        server.on_connection(on_conn_with_handlers)
        server.on_disconnection(on_disconn)
        
        await server.start()
        
        key = (host, port, path)
        self._servers[key] = server
        
        return server
    
    async def stop_server(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
    ):
        """Stop a specific server (by host/port/path) or all servers."""
        if host is not None and port is not None:
            path = path or "/ws"
            key = (host, port, path)
            server = self._servers.get(key)
            if server:
                await server.stop()
                del self._servers[key]
        else:
            for server in list(self._servers.values()):
                await server.stop()
            self._servers.clear()
    
    def get_server(
        self,
        host: str,
        port: int,
        path: str = "/ws",
    ) -> Optional[WebSocketServer]:
        """Get a running server by host/port/path."""
        return self._servers.get((host, port, path))
    
    # =========================================================================
    # Client Management - WebSocket-Specific
    # =========================================================================
    
    async def connect_to_peer(
        self,
        peer_id: PeerId,
        url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        use_tls: Optional[bool] = None,
        subprotocol: Optional[str] = None,
        additional_headers: Optional[dict] = None,
        compression: Optional[bool] = None,
    ) -> WebSocketClient:
        """
        Connect to a peer via WebSocket.
        
        Two ways to specify target:
        1. URL-based: connect_to_peer(peer_id, url="wss://example.com/ws")
        2. Component-based: connect_to_peer(peer_id, host="...", port=443, path="/ws")
        
        Args:
            peer_id: Peer identifier
            url: Full WebSocket URL (overrides host/port/path)
            host: Remote host
            port: Remote port
            path: URL path (default from config)
            use_tls: Use WSS (TLS) - auto-detected from URL if not specified
            subprotocol: Subprotocol to negotiate
            additional_headers: Extra HTTP headers (Authorization, cookies)
            compression: Enable compression
        
        Returns:
            Connected WebSocketClient
        """
        client_config = self._config.get("client", {})
        hb_config = self._config.get("heartbeat", {})
        
        # Determine TLS from URL if provided
        if url and use_tls is None:
            use_tls = url.startswith("wss://")
        
        # Build config
        config = WebSocketConfig(
            url=url,
            host=host if not url else None,
            port=port if not url else None,
            path=path or client_config.get("default_path", "/ws"),
            use_tls=use_tls if use_tls is not None else True,
            peer_id=peer_id,
            subprotocol=subprotocol or client_config.get("subprotocol"),
            additional_headers=(
                additional_headers or client_config.get("additional_headers", {})
            ),
            compression_enabled=(
                compression if compression is not None
                else client_config.get("compression_enabled", True)
            ),
            max_size_bytes=client_config.get("max_size_bytes", 16 * 1024 * 1024),
            connect_timeout=client_config.get("connect_timeout_seconds", 10.0),
            reconnect_enabled=client_config.get("reconnect_enabled", True),
            reconnect_initial_delay=client_config.get("reconnect_initial_delay_seconds", 2.0),
            reconnect_max_delay=client_config.get("reconnect_max_delay_seconds", 60.0),
            reconnect_backoff_multiplier=client_config.get("reconnect_backoff_multiplier", 2.0),
            reconnect_max_attempts=client_config.get("reconnect_max_attempts", 0),
            send_queue_size=client_config.get("send_queue_size", 1000),
            ping_interval=hb_config.get("interval_seconds", 20.0),
            ping_timeout=hb_config.get("timeout_seconds", 60.0),
        )
        
        client = WebSocketClient(config, self._logger)
        
        # Setup TLS
        if config.use_tls and self._ssl_api:
            try:
                ssl_ctx = self._ssl_api.get_client_context(peer_id)
                client.set_ssl_context(ssl_ctx)
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to setup TLS for peer '{peer_id}': {e}. "
                        f"Falling back to plain WS.",
                        level="WARNING",
                        tag="websocket"
                    )
        
        # Add to pool
        await self._pool.add_client(peer_id, client, connect=True)
        
        # Register with heartbeat
        if client.connection:
            self._heartbeat.add_connection(peer_id, client.connection)
        
        return client
    
    async def disconnect_from_peer(
        self,
        peer_id: PeerId,
        code: int = WebSocketCloseCode.NORMAL,
        reason: str = "",
    ):
        """Disconnect from a peer with a specific close code."""
        self._heartbeat.remove_connection(peer_id)
        
        # Close all clients for this peer with code
        for client in self._pool.get_all_clients(peer_id):
            try:
                await client.disconnect(code=code, reason=reason)
            except Exception:
                pass
        
        await self._pool.remove_client(peer_id)
    
    def get_client(self, peer_id: PeerId) -> Optional[WebSocketClient]:
        """Get an active client for a peer."""
        return self._pool.get_client(peer_id)
    
    def get_all_peers(self) -> list[PeerId]:
        """Get all peer IDs in the pool."""
        return self._pool.get_all_peers()
    
    # =========================================================================
    # WebSocket-Specific Operations
    # =========================================================================
    
    def get_subprotocol(self, peer_id: PeerId) -> Optional[str]:
        """Get the negotiated subprotocol for a peer."""
        client = self._pool.get_client(peer_id)
        if client and client.connection:
            return client.connection.subprotocol
        return None
    
    def get_close_info(self, peer_id: PeerId) -> Optional[dict]:
        """
        Get close code and reason for a disconnected peer.
        
        Returns None if peer is still connected or was never connected.
        """
        clients = self._pool.get_all_clients(peer_id)
        for client in clients:
            if client.connection and client.connection.is_closed:
                return {
                    "code": client.connection.close_code,
                    "reason": client.connection.close_reason,
                }
        return None
    
    async def close_peer(
        self,
        peer_id: PeerId,
        code: int = WebSocketCloseCode.NORMAL,
        reason: str = "",
    ):
        """
        Close connection to a peer with a specific code and reason.
        
        Unlike disconnect_from_peer, this does NOT remove the client
        from the pool - useful for graceful shutdown with specific codes.
        """
        client = self._pool.get_client(peer_id)
        if client and client.is_connected:
            await client.disconnect(code=code, reason=reason)
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    async def send_message(self, peer_id: PeerId, message: dict) -> bool:
        """
        Send a JSON-serializable dict to a peer.
        
        The message structure is not enforced - higher layers define format.
        """
        client = self._pool.get_client(peer_id)
        if not client or not client.is_connected:
            if self._logger:
                self._logger.log(
                    f"Cannot send to peer '{peer_id}': not connected",
                    level="WARNING",
                    tag="websocket"
                )
            return False
        
        try:
            await client.send_message(message)
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to send WebSocket message to '{peer_id}': {e}",
                    level="ERROR",
                    tag="websocket"
                )
            return False
    
    async def send_bytes(
        self,
        peer_id: PeerId,
        data: bytes,
        use_queue: bool = False,
    ) -> bool:
        """Send raw bytes to a peer."""
        client = self._pool.get_client(peer_id)
        if not client or not client.is_connected:
            if self._logger:
                self._logger.log(
                    f"Cannot send bytes to peer '{peer_id}': not connected",
                    level="WARNING",
                    tag="websocket"
                )
            return False
        
        try:
            if use_queue:
                await client.send_bytes_queued(data)
            else:
                await client.send_bytes(data)
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to send WebSocket bytes to '{peer_id}': {e}",
                    level="ERROR",
                    tag="websocket"
                )
            return False
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self):
        """Start all background services."""
        await self._pool.start()
        
        hb_config = self._config.get("heartbeat", {})
        if hb_config.get("enabled", True):
            await self._heartbeat.start()
    
    async def stop(self):
        """Stop all services and connections."""
        await self._heartbeat.stop()
        await self._pool.stop()
        await self.stop_server()
        
        if self._logger:
            self._logger.log("WebSocketAPI stopped", tag="websocket")
    
    # =========================================================================
    # Utility
    # =========================================================================
    
    def get_info(self) -> dict[str, Any]:
        """Get API information and statistics."""
        return {
            "module": "network_websocket",
            "version": "1.0.0",
            "protocol": "WebSocket (RFC 6455)",
            "servers": {
                f"{h}:{p}{pa}": {
                    "connections": len(s.get_connections()),
                    "tls": s._ssl_context is not None,
                }
                for (h, p, pa), s in self._servers.items()
            },
            "pool": self._pool.get_stats(),
            "tracked_peers": self._heartbeat.get_tracked_peers(),
        }
    
    def get_all_connection_info(self) -> list[dict[str, Any]]:
        """Get information about all active connections."""
        info = []
        
        for server in self._servers.values():
            for conn in server.get_connections():
                info.append(conn.get_info().to_dict())
        
        for peer_id in self._pool.get_all_peers():
            for client in self._pool.get_all_clients(peer_id):
                if client.connection:
                    info.append(client.connection.get_info().to_dict())
        
        return info