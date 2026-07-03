"""
Unified Socket API.

Provides a high-level interface for all socket operations.
"""

from __future__ import annotations

import asyncio
import ssl
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
from .connection import Connection
from .server import SocketServer
from .client import SocketClient
from .pool import ConnectionPool
from .heartbeat import HeartbeatMonitor
from .framing import get_codec, LengthPrefixProtocol
from .exceptions import (
    SocketError,
    SocketConfigError,
    ConnectionError,
    PoolError,
)

# Callback types
MessageCallback = Callable[[SocketMessage, Connection], Awaitable[None] | None]
BytesCallback = Callable[[bytes, Connection], Awaitable[None] | None]
ConnectionCallback = Callable[[Connection], Awaitable[None] | None]


class SocketAPI:
    """
    Unified API for socket operations.
    
    Provides methods to:
    - Create and manage TCP servers
    - Connect to peers with auto-reconnect
    - Manage connection pools
    - Monitor connection health via heartbeats
    - Send messages (Message Mode) or bytes (Stream Mode)
    - Factory methods for creating messages (no direct imports needed)
    
    Access message types via instance attributes:
        socket_api.MessageType.DATA
        socket_api.SocketMessage(type=..., payload=...)
    """
    
    # Expose types as class attributes (NOT properties)
    # This allows: socket_api.MessageType.DATA without instantiation issues
    MessageType = MessageType
    SocketMessage = SocketMessage
    
    def __init__(self, config: dict, logger: Any = None):
        """
        Initialize the Socket API.
        
        Args:
            config: Module configuration dictionary
            logger: Logger instance
        """
        self._config = config
        self._logger = logger
        ()
        # SSL API reference (optional, from network_ssl module)
        self._ssl_api = None

        # Encryption API reference (optional, from system_encryption module)
        self._encryption_api = None

        # Active servers
        self._servers: dict[tuple[str, int], SocketServer] = {}
        
        # Connection pool
        pool_config = config.get("pool", {})
        self._pool = ConnectionPool(
            max_per_peer=pool_config.get("max_connections_per_peer", 5),
            idle_timeout=pool_config.get("idle_timeout_seconds", 300.0),
            cleanup_interval=pool_config.get("cleanup_interval_seconds", 60.0),
            logger=logger,
        )
        
        # Heartbeat monitor
        hb_config = config.get("heartbeat", {})
        self._heartbeat = HeartbeatMonitor(
            interval=hb_config.get("interval_seconds", 30.0),
            timeout=hb_config.get("timeout_seconds", 90.0),
            missed_threshold=hb_config.get("missed_threshold", 3),
            logger=logger,
        )
        
        # Global callbacks
        self._on_inbound_connection: Optional[ConnectionCallback] = None
        self._on_inbound_disconnection: Optional[ConnectionCallback] = None
        self._on_inbound_message: Optional[MessageCallback] = None
        self._on_inbound_bytes: Optional[BytesCallback] = None
    
    # =========================================================================
    # Factory Methods (No Direct Imports Needed by Consumer Modules)
    # =========================================================================
    
    def create_message(
        self,
        msg_type: Any, 
        payload: Any = None,
        message_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> SocketMessage:
        """
        Factory method to create a SocketMessage.
        
        This eliminates the need for consumer modules to import types directly.
        
        Args:
            msg_type: Message type - can be:
                     - String like "data", "ping", "pong"
                     - MessageType enum value
                     - Any custom string type
            payload: Message payload (any JSON-serializable data)
            message_id: Optional unique message identifier
            correlation_id: Optional correlation ID for request/reply
            metadata: Optional metadata dictionary
        
        Returns:
            SocketMessage instance
        
        Example:
            >>> # Using string
            >>> msg = socket_api.create_message("data", payload={"key": "value"})
            
            >>> # Using MessageType enum
            >>> msg = socket_api.create_message(
            ...     socket_api.MessageType.DATA,
            ...     payload={"key": "value"}
            ... )
        """
        # Convert string to MessageType if needed
        if isinstance(msg_type, str):
            try:
                msg_type = MessageType(msg_type.lower())
            except ValueError:
                # Allow custom message types as strings
                pass
        
        return SocketMessage(
            type=msg_type,
            payload=payload,
            message_id=message_id,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )
    
    def create_ping(self, message_id: Optional[str] = None) -> SocketMessage:
        """Create a PING message."""
        return self.create_message(MessageType.PING, message_id=message_id)
    
    def create_pong(self, correlation_id: Optional[str] = None) -> SocketMessage:
        """Create a PONG message."""
        return self.create_message(MessageType.PONG, correlation_id=correlation_id)
    
    def create_data_message(
        self,
        payload: Any,
        message_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> SocketMessage:
        """Create a DATA message (most common type)."""
        return self.create_message(
            MessageType.DATA,
            payload=payload,
            message_id=message_id,
            metadata=metadata,
        )
    
    # =========================================================================
    # Service Integration
    # =========================================================================
    
    def set_ssl_api(self, ssl_api: Any):
        """Set the SSL API reference."""
        self._ssl_api = ssl_api
    
    def set_encryption_api(self, encryption_api: Any):
        """Set the encryption API reference."""
        self._encryption_api = encryption_api
    
    # =========================================================================
    # Global Callbacks
    # =========================================================================
    
    def on_inbound_connection(self, callback: ConnectionCallback):
        """Register callback for inbound connections."""
        self._on_inbound_connection = callback
    
    def on_inbound_disconnection(self, callback: ConnectionCallback):
        """Register callback for inbound disconnections."""
        self._on_inbound_disconnection = callback
    
    def on_inbound_message(self, callback: MessageCallback):
        """Register callback for inbound messages."""
        self._on_inbound_message = callback
    
    def on_inbound_bytes(self, callback: BytesCallback):
        """Register callback for inbound bytes (Stream Mode)."""
        self._on_inbound_bytes = callback
    
    # =========================================================================
    # Server Management
    # =========================================================================
    
    async def create_server(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        mode: str = "message",
        use_tls: bool = True,
    ) -> SocketServer:
        """
        Create and start a TCP server.
        
        Args:
            host: Bind host (default from config)
            port: Bind port (default from config)
            mode: "message" or "stream"
            use_tls: Whether to use TLS
        
        Returns:
            SocketServer instance
        """
        server_config = self._config.get("server", {})
        
        host = host or server_config.get("default_host", "0.0.0.0")
        port = port or server_config.get("default_port", 8443)
        mode_enum = SocketMode.MESSAGE if mode == "message" else SocketMode.STREAM
        
        config = SocketConfig(
            host=host,
            port=port,
            mode=mode_enum,
            use_tls=use_tls,
            max_message_size=self._config.get("framing", {}).get(
                "max_message_size_bytes", 16 * 1024 * 1024
            ),
            length_prefix_bytes=self._config.get("framing", {}).get(
                "length_prefix_bytes", 4
            ),
        )
        
        server = SocketServer(config, self._logger)
        
        # Setup TLS if enabled
        if use_tls and self._ssl_api:
            try:
                ssl_ctx = self._ssl_api.get_server_context("default")
                server.set_ssl_context(ssl_ctx)
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to setup TLS for server: {e}",
                        level="WARNING",
                        tag="socket"
                    )
        
        # Register connection handlers
        async def on_conn(conn: Connection):
            # Register message/bytes handler
            if config.mode == SocketMode.MESSAGE:
                async def msg_handler(msg, c):
                    if self._on_inbound_message:
                        result = self._on_inbound_message(msg, c)
                        if asyncio.iscoroutine(result):
                            await result
                conn.on_message(msg_handler)
            else:
                async def bytes_handler(data, c):
                    if self._on_inbound_bytes:
                        result = self._on_inbound_bytes(data, c)
                        if asyncio.iscoroutine(result):
                            await result
                conn.on_bytes(bytes_handler)
            
            # Register with heartbeat if in message mode
            if config.mode == SocketMode.MESSAGE and conn.peer_id:
                self._heartbeat.add_connection(conn.peer_id, conn)
            
            if self._on_inbound_connection:
                result = self._on_inbound_connection(conn)
                if asyncio.iscoroutine(result):
                    await result
        
        async def on_disconn(conn: Connection):
            if conn.peer_id:
                self._heartbeat.remove_connection(conn.peer_id)
            
            if self._on_inbound_disconnection:
                result = self._on_inbound_disconnection(conn)
                if asyncio.iscoroutine(result):
                    await result
        
        server.on_connection(on_conn)
        server.on_disconnection(on_disconn)
        
        # Start server
        await server.start()
        
        # Store
        key = (host, port)
        self._servers[key] = server
        
        return server
    
    async def stop_server(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """Stop a specific server or all servers."""
        if host is not None and port is not None:
            key = (host, port)
            server = self._servers.get(key)
            if server:
                await server.stop()
                del self._servers[key]
        else:
            # Stop all
            for server in list(self._servers.values()):
                await server.stop()
            self._servers.clear()
    
    # =========================================================================
    # Client Management
    # =========================================================================

    async def connect_to_peer(
        self,
        peer_id: PeerId,
        host: str,
        port: int,
        mode: str = "message",
        use_tls: bool = True,
    ) -> SocketClient:
        """
        Connect to a peer.
        
        Args:
            peer_id: Peer identifier
            host: Remote host
            port: Remote port
            mode: "message" or "stream"
            use_tls: Whether to use TLS
        
        Returns:
            SocketClient instance (may not be connected yet if initial
            connection failed - auto-reconnect will keep trying)
        """
        client_config = self._config.get("client", {})
        framing_config = self._config.get("framing", {})
        
        mode_enum = SocketMode.MESSAGE if mode == "message" else SocketMode.STREAM
        
        config = SocketConfig(
            host=host,
            port=port,
            mode=mode_enum,
            use_tls=use_tls,
            peer_id=peer_id,
            connect_timeout=client_config.get("connect_timeout_seconds", 10.0),
            reconnect_enabled=client_config.get("reconnect_enabled", True),
            reconnect_initial_delay=client_config.get(
                "reconnect_initial_delay_seconds", 1.0
            ),
            reconnect_max_delay=client_config.get(
                "reconnect_max_delay_seconds", 60.0
            ),
            reconnect_backoff_multiplier=client_config.get(
                "reconnect_backoff_multiplier", 2.0
            ),
            reconnect_max_attempts=client_config.get(
                "reconnect_max_attempts", 0
            ),
            send_queue_size=client_config.get("send_queue_size", 1000),
            max_message_size=framing_config.get(
                "max_message_size_bytes", 16 * 1024 * 1024
            ),
            length_prefix_bytes=framing_config.get("length_prefix_bytes", 4),
        )
        
        client = SocketClient(config, self._logger)
        
        # Setup TLS
        if use_tls and self._ssl_api:
            try:
                ssl_ctx = self._ssl_api.get_client_context(peer_id)
                client.set_ssl_context(ssl_ctx)
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to setup TLS for peer '{peer_id}': {e}. "
                        f"Falling back to plain connection.",
                        level="WARNING",
                        tag="socket"
                    )
                    # Continue without TLS
    
        # Add to pool (will attempt connect, but won't fail if connect fails)
        await self._pool.add_client(peer_id, client, connect=True)
        
        # Register with heartbeat (only if connected and in message mode)
        if mode_enum == SocketMode.MESSAGE and client.connection:
            self._heartbeat.add_connection(peer_id, client.connection)
        
        return client

    async def disconnect_from_peer(self, peer_id: PeerId):
        """Disconnect all connections to a peer."""
        self._heartbeat.remove_connection(peer_id)
        await self._pool.remove_client(peer_id)
    
    def get_client(self, peer_id: PeerId) -> Optional[SocketClient]:
        """Get an active client for a peer."""
        return self._pool.get_client(peer_id)
    
    def get_all_peers(self) -> list[PeerId]:
        """Get all connected peers."""
        return self._pool.get_all_peers()
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    async def send_message(
        self,
        peer_id: PeerId,
        message: SocketMessage,
    ) -> bool:
        """
        Send a message to a peer (Message Mode).
        
        Returns True if sent successfully.
        """
        client = self._pool.get_client(peer_id)
        if not client or not client.is_connected:
            if self._logger:
                self._logger.log(
                    f"Cannot send to peer '{peer_id}': not connected",
                    level="WARNING",
                    tag="socket"
                )
            return False
        
        try:
            await client.send_message(message)
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to send message to '{peer_id}': {e}",
                    level="ERROR",
                    tag="socket"
                )
            return False
    
    async def send_bytes(
        self,
        peer_id: PeerId,
        data: bytes,
        use_queue: bool = False,
    ) -> bool:
        """
        Send raw bytes to a peer.
        
        Args:
            peer_id: Target peer
            data: Bytes to send
            use_queue: Use send queue for backpressure
        
        Returns True if sent successfully.
        """
        client = self._pool.get_client(peer_id)
        if not client or not client.is_connected:
            if self._logger:
                self._logger.log(
                    f"Cannot send bytes to peer '{peer_id}': not connected",
                    level="WARNING",
                    tag="socket"
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
                    f"Failed to send bytes to '{peer_id}': {e}",
                    level="ERROR",
                    tag="socket"
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
            self._logger.log("SocketAPI stopped", tag="socket")
    
    # =========================================================================
    # Utility
    # =========================================================================
    
    def get_info(self) -> dict[str, Any]:
        """Get API information."""
        return {
            "module": "network_socket",
            "version": "1.0.0",
            "servers": len(self._servers),
            "pool": self._pool.get_stats(),
            "tracked_peers": self._heartbeat.get_tracked_peers(),
        }
    
    def get_all_connection_info(self) -> list[dict[str, Any]]:
        """Get information about all active connections."""
        info = []
        
        # Server connections
        for server in self._servers.values():
            for conn in server.get_connections():
                info.append(conn.get_info().to_dict())
        
        # Client connections
        for peer_id in self._pool.get_all_peers():
            for client in self._pool.get_all_clients(peer_id):
                if client.connection:
                    info.append(client.connection.get_info().to_dict())
        
        return info