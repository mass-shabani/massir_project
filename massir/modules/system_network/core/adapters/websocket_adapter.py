"""
WebSocket Transport Adapter.

Adapts network_websocket's websocket_api to the TransportAdapter interface.
"""

from typing import Any, Optional

from .base import (
    TransportAdapter,
    MessageCallback,
    BytesCallback,
    ConnectionCallback,
)


class WebSocketAdapter(TransportAdapter):
    """
    Adapter for network_websocket transport.
    
    Bridges the websocket_api interface with the TransportAdapter contract.
    WebSocket naturally handles dicts as JSON text frames.
    """
    
    def __init__(self, websocket_api: Any, logger: Any = None):
        self._ws_api = websocket_api
        self._logger = logger
        
        # User callbacks
        self._message_callback: Optional[MessageCallback] = None
        self._bytes_callback: Optional[BytesCallback] = None
        self._connection_callback: Optional[ConnectionCallback] = None
        self._disconnection_callback: Optional[ConnectionCallback] = None
        
        self._setup_handlers()
    
    @property
    def transport_name(self) -> str:
        return "websocket"
    
    def _setup_handlers(self) -> None:
        """Wire up internal handlers to websocket_api."""
        
        async def inbound_message_handler(message_dict, connection):
            """Invoke user message callback with dict."""
            if not self._message_callback:
                return
            
            try:
                peer_id = connection.peer_id or "unknown"
                result = self._message_callback(peer_id, message_dict, connection)
                if hasattr(result, '__await__'):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in websocket message handler: {e}",
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
                        f"Error in websocket bytes handler: {e}",
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
                            f"Error in websocket connection handler: {e}",
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
                            f"Error in websocket disconnection handler: {e}",
                            level="ERROR",
                            tag="network"
                        )
        
        self._ws_api.on_inbound_message(inbound_message_handler)
        self._ws_api.on_inbound_bytes(inbound_bytes_handler)
        self._ws_api.on_inbound_connection(inbound_connection_handler)
        self._ws_api.on_inbound_disconnection(inbound_disconnection_handler)
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    async def connect(self, peer_id: str, endpoint: dict) -> bool:
        """Connect to a peer via WebSocket."""
        try:
            client = await self._ws_api.connect_to_peer(
                peer_id=peer_id,
                url=endpoint.get("url"),
                host=endpoint.get("host"),
                port=endpoint.get("port"),
                path=endpoint.get("path", "/ws"),
                use_tls=endpoint.get("use_tls", True),
                subprotocol=endpoint.get("subprotocol"),
                additional_headers=endpoint.get("headers"),
                compression=endpoint.get("compression"),
            )
            return client.is_connected
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"WebSocket connect to '{peer_id}' failed: {e}",
                    level="ERROR",
                    tag="network"
                )
            return False
    
    async def disconnect(self, peer_id: str) -> bool:
        """Disconnect from a peer."""
        try:
            await self._ws_api.disconnect_from_peer(peer_id)
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"WebSocket disconnect from '{peer_id}' failed: {e}",
                    level="WARNING",
                    tag="network"
                )
            return False
    
    def is_connected(self, peer_id: str) -> bool:
        """Check if connected to a peer."""
        client = self._ws_api.get_client(peer_id)
        return client is not None and client.is_connected
    
    def get_connected_peers(self) -> list[str]:
        """Get list of connected peer IDs."""
        peers = []
        for peer_id in self._ws_api.get_all_peers():
            client = self._ws_api.get_client(peer_id)
            if client and client.is_connected:
                peers.append(peer_id)
        return peers
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    async def send_message(self, peer_id: str, message: dict) -> bool:
        """Send a dict message via WebSocket (natively JSON)."""
        return await self._ws_api.send_message(peer_id, message)
    
    async def send_bytes(self, peer_id: str, data: bytes) -> bool:
        """Send raw bytes via WebSocket binary frame."""
        return await self._ws_api.send_bytes(peer_id, data)
    
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
        """Start WebSocket server."""
        try:
            await self._ws_api.create_server(
                host=config.get("host"),
                port=config.get("port"),
                path=config.get("path", "/ws"),
                use_tls=config.get("use_tls", True),
                compression=config.get("compression", True),
                subprotocol=config.get("subprotocol"),
                allowed_origins=config.get("allowed_origins"),
            )
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to start WebSocket server: {e}",
                    level="ERROR",
                    tag="network"
                )
            return False
    
    async def stop_server(self) -> None:
        """Stop WebSocket server."""
        await self._ws_api.stop_server()
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self) -> None:
        """Start the WebSocket adapter."""
        await self._ws_api.start()
    
    async def stop(self) -> None:
        """Stop the WebSocket adapter."""
        await self._ws_api.stop()
    
    def get_info(self) -> dict:
        """Get adapter info."""
        info = self._ws_api.get_info()
        info["transport"] = self.transport_name
        return info