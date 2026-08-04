"""
Socket Transport Adapter.

Adapts network_socket's socket_api to the TransportAdapter interface.
"""

from typing import Any, Optional

from .base import (
    TransportAdapter,
    MessageCallback,
    BytesCallback,
    ConnectionCallback,
)


class SocketAdapter(TransportAdapter):
    """
    Adapter for network_socket transport.
    
    Bridges the socket_api interface with the TransportAdapter contract,
    converting between application-level dicts and SocketMessage objects.
    """
    
    def __init__(self, socket_api: Any, logger: Any = None):
        self._socket_api = socket_api
        self._logger = logger
        
        # User callbacks (set by ConnectionManager)
        self._message_callback: Optional[MessageCallback] = None
        self._bytes_callback: Optional[BytesCallback] = None
        self._connection_callback: Optional[ConnectionCallback] = None
        self._disconnection_callback: Optional[ConnectionCallback] = None
        
        # Wire up our handlers to socket_api
        self._setup_handlers()
    
    @property
    def transport_name(self) -> str:
        return "socket"
    
    def _setup_handlers(self) -> None:
        """Wire up internal handlers to socket_api."""
        
        async def inbound_message_handler(message, connection):
            """Convert SocketMessage to dict and invoke user callback."""
            if not self._message_callback:
                return
            
            # Extract payload from SocketMessage
            try:
                msg_type = message.type.value if hasattr(message.type, 'value') else str(message.type)
                
                # If payload is a dict, use as-is
                if isinstance(message.payload, dict):
                    payload_dict = message.payload
                else:
                    # Wrap non-dict payload
                    payload_dict = {
                        "type": msg_type,
                        "data": message.payload,
                    }
                
                peer_id = connection.peer_id or "unknown"
                result = self._message_callback(peer_id, payload_dict, connection)
                if hasattr(result, '__await__'):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in socket message handler: {e}",
                        level="ERROR",
                        tag="network"
                    )
        
        async def inbound_bytes_handler(data, connection):
            """Invoke user bytes callback."""
            if not self._bytes_callback:
                return
            
            try:
                peer_id = connection.peer_id or "unknown"
                result = self._bytes_callback(peer_id, data, connection)
                if hasattr(result, '__await__'):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in socket bytes handler: {e}",
                        level="ERROR",
                        tag="network"
                    )
        
        async def inbound_connection_handler(connection):
            """Invoke user connection callback."""
            if self._connection_callback:
                try:
                    peer_id = connection.peer_id or "unknown"
                    result = self._connection_callback(peer_id, connection)
                    if hasattr(result, '__await__'):
                        await result
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Error in socket connection handler: {e}",
                            level="ERROR",
                            tag="network"
                        )
        
        async def inbound_disconnection_handler(connection):
            """Invoke user disconnection callback."""
            if self._disconnection_callback:
                try:
                    peer_id = connection.peer_id or "unknown"
                    result = self._disconnection_callback(peer_id, connection)
                    if hasattr(result, '__await__'):
                        await result
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Error in socket disconnection handler: {e}",
                            level="ERROR",
                            tag="network"
                        )
        
        self._socket_api.on_inbound_message(inbound_message_handler)
        self._socket_api.on_inbound_bytes(inbound_bytes_handler)
        self._socket_api.on_inbound_connection(inbound_connection_handler)
        self._socket_api.on_inbound_disconnection(inbound_disconnection_handler)
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    async def connect(self, peer_id: str, endpoint: dict) -> bool:
        """Connect to a peer via socket."""
        try:
            client = await self._socket_api.connect_to_peer(
                peer_id=peer_id,
                host=endpoint.get("host"),
                port=endpoint.get("port"),
                mode=endpoint.get("mode", "message"),
                use_tls=endpoint.get("use_tls", True),
            )
            return client.is_connected
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Socket connect to '{peer_id}' failed: {e}",
                    level="ERROR",
                    tag="network"
                )
            return False
    
    async def disconnect(self, peer_id: str) -> bool:
        """Disconnect from a peer."""
        try:
            await self._socket_api.disconnect_from_peer(peer_id)
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Socket disconnect from '{peer_id}' failed: {e}",
                    level="WARNING",
                    tag="network"
                )
            return False
    
    def is_connected(self, peer_id: str) -> bool:
        """Check if connected to a peer."""
        client = self._socket_api.get_client(peer_id)
        return client is not None and client.is_connected
    
    def get_connected_peers(self) -> list[str]:
        """Get list of connected peer IDs."""
        peers = []
        for peer_id in self._socket_api.get_all_peers():
            client = self._socket_api.get_client(peer_id)
            if client and client.is_connected:
                peers.append(peer_id)
        return peers
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    async def send_message(self, peer_id: str, message: dict) -> bool:
        """Send a dict message via socket."""
        try:
            # Wrap dict in SocketMessage
            socket_msg = self._socket_api.create_message(
                "data",
                payload=message,
            )
            return await self._socket_api.send_message(peer_id, socket_msg)
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Socket send_message to '{peer_id}' failed: {e}",
                    level="ERROR",
                    tag="network"
                )
            return False
    
    async def send_bytes(self, peer_id: str, data: bytes) -> bool:
        """Send raw bytes via socket."""
        return await self._socket_api.send_bytes(peer_id, data)
    
    # =========================================================================
    # Receiving (Callback Registration)
    # =========================================================================
    
    def on_message(self, callback: MessageCallback) -> None:
        self._message_callback = callback
    
    def on_bytes(self, callback: BytesCallback) -> None:
        self._bytes_callback = callback
    
    def on_connection(self, callback: ConnectionCallback) -> None:
        self._connection_callback = callback
    
    def on_disconnection(self, callback: ConnectionCallback) -> None:
        self._disconnection_callback = callback
    
    # =========================================================================
    # Server
    # =========================================================================
    
    async def start_server(self, config: dict) -> bool:
        """Start socket server."""
        try:
            await self._socket_api.create_server(
                host=config.get("host"),
                port=config.get("port"),
                mode=config.get("mode", "message"),
                use_tls=config.get("use_tls", True),
            )
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to start socket server: {e}",
                    level="ERROR",
                    tag="network"
                )
            return False
    
    async def stop_server(self) -> None:
        """Stop socket server."""
        await self._socket_api.stop_server()
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self) -> None:
        """Start the socket adapter."""
        await self._socket_api.start()
    
    async def stop(self) -> None:
        """Stop the socket adapter."""
        await self._socket_api.stop()
    
    def get_info(self) -> dict:
        """Get adapter info."""
        info = self._socket_api.get_info()
        info["transport"] = self.transport_name
        return info