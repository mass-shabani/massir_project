"""
Async TCP server.
"""

import asyncio
import ssl
from typing import Any, Callable, Optional, Awaitable

from .types import SocketConfig, ConnectionState, SocketMode, PeerId
from .connection import Connection
from .framing import LengthPrefixProtocol, get_codec
from .exceptions import SocketError, SocketConfigError

# Callback types
ConnectionCallback = Callable[[Connection], Awaitable[None] | None]


class SocketServer:
    """
    Async TCP server supporting both Message and Stream modes.
    """
    
    def __init__(self, config: SocketConfig, logger: Any = None):
        self._config = config
        self._logger = logger
        self._server: Optional[asyncio.Server] = None
        self._ssl_context: Optional[ssl.SSLContext] = None
        
        # Active connections by peer_id or (host, port) for unknown peers
        self._connections: dict[PeerId | tuple[str, int], Connection] = {}
        
        # Protocol (only for Message Mode)
        self._protocol: Optional[LengthPrefixProtocol] = None
        if config.mode == SocketMode.MESSAGE:
            codec = get_codec("json")  # Default codec
            self._protocol = LengthPrefixProtocol(
                codec=codec,
                length_prefix_bytes=config.length_prefix_bytes,
                max_message_size=config.max_message_size,
            )
        
        # Callbacks
        self._on_connection: Optional[ConnectionCallback] = None
        self._on_disconnection: Optional[ConnectionCallback] = None
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def set_ssl_context(self, ssl_context: ssl.SSLContext):
        """Set SSL context for TLS."""
        self._ssl_context = ssl_context
    
    def on_connection(self, callback: ConnectionCallback):
        """Register callback for new connections."""
        self._on_connection = callback
    
    def on_disconnection(self, callback: ConnectionCallback):
        """Register callback for closed connections."""
        self._on_disconnection = callback
    
    def get_connections(self) -> list[Connection]:
        """Get all active connections."""
        return list(self._connections.values())
    
    def get_connection(self, peer_id: PeerId) -> Optional[Connection]:
        """Get a specific connection by peer_id."""
        return self._connections.get(peer_id)
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self):
        """Start the server."""
        if self._server is not None:
            return
        
        try:
            self._server = await asyncio.start_server(
                self._handle_client,
                host=self._config.host,
                port=self._config.port,
                ssl=self._ssl_context,
                backlog=100,
            )
            
            if self._logger:
                tls_str = "TLS" if self._ssl_context else "plain"
                self._logger.log(
                    f"SocketServer started on {self._config.host}:{self._config.port} "
                    f"({tls_str}, {self._config.mode.value} mode)",
                    tag="socket"
                )
        
        except OSError as e:
            raise SocketConfigError(
                f"Failed to start server on {self._config.host}:{self._config.port}: {e}"
            ) from e
    
    async def stop(self):
        """Stop the server and close all connections."""
        if self._server is None:
            return
        
        # Stop accepting new connections
        self._server.close()
        
        # Close all active connections
        connections = list(self._connections.values())
        for conn in connections:
            try:
                await conn.close()
            except Exception:
                pass
        
        self._connections.clear()
        
        # Wait for server to close
        try:
            await self._server.wait_closed()
        except Exception:
            pass
        
        self._server = None
        
        if self._logger:
            self._logger.log(
                f"SocketServer stopped on {self._config.host}:{self._config.port}",
                tag="socket"
            )
    
    async def serve_forever(self):
        """Serve until cancelled."""
        if self._server is None:
            await self.start()
        
        async with self._server:
            await self._server.serve_forever()
    
    # =========================================================================
    # Connection Handling
    # =========================================================================
    
    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        """Handle a new client connection."""
        peername = writer.get_extra_info("peername")
        remote = f"{peername[0]}:{peername[1]}" if peername else "unknown"
        
        if self._logger:
            self._logger.log(
                f"New connection from {remote}",
                tag="socket"
            )
        
        # Create connection
        config = SocketConfig(
            host=peername[0] if peername else "",
            port=peername[1] if peername else 0,
            mode=self._config.mode,
            use_tls=self._ssl_context is not None,
            max_message_size=self._config.max_message_size,
            length_prefix_bytes=self._config.length_prefix_bytes,
        )
        
        connection = Connection(
            config=config,
            reader=reader,
            writer=writer,
            protocol=self._protocol,
            is_server_side=True,
        )
        
        # Register close handler
        async def on_close(conn: Connection):
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
        
        # Store connection
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
                        tag="socket"
                    )
        
        # Start receiving
        await connection.start_receiving()
    
    # =========================================================================
    # Utility
    # =========================================================================
    
    def register_peer(self, connection: Connection, peer_id: PeerId):
        """Register a connection with a peer_id."""
        # Remove old key if exists
        old_key = connection.remote_address
        if old_key in self._connections and self._connections[old_key] is connection:
            del self._connections[old_key]
        
        connection.peer_id = peer_id
        self._connections[peer_id] = connection
    
    def __repr__(self):
        return (
            f"SocketServer(host={self._config.host}, "
            f"port={self._config.port}, "
            f"connections={len(self._connections)})"
        )