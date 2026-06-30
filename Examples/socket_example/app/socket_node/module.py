"""
Socket Node Module

Manages a node in the distributed socket network:
- Starts a TLS server to accept connections
- Connects to all configured peers
- Monitors connections via heartbeat
- Provides node_service to other modules
"""

import asyncio
from typing import Any, Dict, List, Optional

from massir.core.interfaces import IModule

from massir.modules.network_socket.core.types import (
    SocketMessage,
    MessageType,
    PeerId,
    Connection,
)


class SocketNodeModule(IModule):
    """
    Manages a single node in the distributed network.
    
    Responsibilities:
    - Start server and accept inbound connections
    - Connect to all configured peers
    - Handle connection/disconnection events
    - Provide node_service for peer operations
    """
    
    name = "socket_node"
    
    def __init__(self):
        self.socket_api = None
        self.ssl_api = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
        self._node_id: str = ""
        self._server = None
        self._peers: List[Dict] = []
        self._connected_peers: Dict[str, Any] = {}
    
    async def load(self, context):
        """Load the module and configure."""
        self.socket_api = context.services.get("socket_api")
        self.ssl_api = context.services.get("ssl_api")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        # Load configuration
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("socket_node", {})
        
        self._node_id = self._config.get("node_id", "unknown")
        self._peers = self._config.get("peers", [])
        
        # Register as a service
        context.services.set("node_service", self)
        
        if self.logger:
            self.logger.log(
                f"SocketNodeModule loaded - Node ID: {self._node_id}",
                tag="node",
                text_color=self.colors.BRIGHT_GREEN if self.colors else None
            )
    
    async def start(self, context):
        """Start server and connect to peers."""
        # Register global handlers
        self.socket_api.on_inbound_connection(self._on_inbound_connection)
        self.socket_api.on_inbound_disconnection(self._on_inbound_disconnection)
        self.socket_api.on_inbound_message(self._on_inbound_message)
        
        # Start server
        if self._config.get("auto_start_server", True):
            listen_host = self._config.get("listen_host", "0.0.0.0")
            listen_port = self._config.get("listen_port", 8443)
            use_tls = self._config.get("use_tls", True)
            
            self._server = await self.socket_api.create_server(
                host=listen_host,
                port=listen_port,
                mode="message",
                use_tls=use_tls,
            )
            
            if self.logger:
                self.logger.log(
                    f"🖥️  Server started on {listen_host}:{listen_port} "
                    f"({'TLS' if use_tls else 'plain'})",
                    tag="node",
                    text_color=self.colors.BRIGHT_CYAN if self.colors else None
                )
        
        # Connect to peers
        if self._config.get("auto_connect_on_start", True):
            await self._connect_to_all_peers()
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log(
                f"SocketNode '{self._node_id}' ready - "
                f"{len(self._peers)} peers configured",
                tag="node"
            )
    
    async def stop(self, context):
        """Stop the node."""
        # Disconnect from all peers
        for peer in self._peers:
            try:
                await self.socket_api.disconnect_from_peer(peer["node_id"])
            except Exception:
                pass
        
        # Stop server
        if self._server:
            await self.socket_api.stop_server()
        
        if self.logger:
            self.logger.log(
                f"SocketNode '{self._node_id}' stopped",
                tag="node"
            )
    
    # =========================================================================
    # Peer Connection
    # =========================================================================
    
    async def _connect_to_all_peers(self):
        """Connect to all configured peers."""
        if not self._peers:
            if self.logger:
                self.logger.log("No peers configured", tag="node")
            return
        
        use_tls = self._config.get("use_tls", True)
        
        for peer in self._peers:
            peer_id = peer["node_id"]
            host = peer["host"]
            port = peer["port"]
            
            try:
                client = await self.socket_api.connect_to_peer(
                    peer_id=peer_id,
                    host=host,
                    port=port,
                    mode="message",
                    use_tls=use_tls,
                )
                
                # Register disconnect handler
                async def on_disconnect(conn, pid=peer_id):
                    self._connected_peers.pop(pid, None)
                    if self.logger:
                        self.logger.log(
                            f"❌ Disconnected from peer '{pid}'",
                            tag="node",
                            text_color=self.colors.BRIGHT_RED if self.colors else None
                        )
                
                client.on_disconnect(on_disconnect)
                
                self._connected_peers[peer_id] = client
                
                if self.logger:
                    self.logger.log(
                        f"✅ Connected to peer '{peer_id}' at {host}:{port}",
                        tag="node",
                        text_color=self.colors.BRIGHT_GREEN if self.colors else None
                    )
            
            except Exception as e:
                if self.logger:
                    self.logger.log(
                        f"⚠️ Failed to connect to peer '{peer_id}' "
                        f"at {host}:{port}: {e} (will retry)",
                        tag="node",
                        level="WARNING",
                        text_color=self.colors.BRIGHT_YELLOW if self.colors else None
                    )
    
    # =========================================================================
    # Inbound Handlers
    # =========================================================================
    
    async def _on_inbound_connection(self, conn: Connection):
        """Handle inbound connection."""
        remote = conn.remote_address
        if self.logger:
            self.logger.log(
                f"📥 Inbound connection from {remote[0]}:{remote[1]}",
                tag="node",
                text_color=self.colors.BRIGHT_BLUE if self.colors else None
            )
    
    async def _on_inbound_disconnection(self, conn: Connection):
        """Handle inbound disconnection."""
        remote = conn.remote_address
        if self.logger:
            self.logger.log(
                f"📤 Connection closed from {remote[0]}:{remote[1]}",
                tag="node"
            )
    
    async def _on_inbound_message(self, message: SocketMessage, conn: Connection):
        """Handle inbound message (dispatch to handlers)."""
        # Skip control messages
        if message.type in (MessageType.PING, MessageType.PONG):
            return
        
        if self.logger:
            peer_id = conn.peer_id or "unknown"
            self.logger.log(
                f"📨 Message from '{peer_id}' type={message.type.value}: "
                f"{str(message.payload)[:100]}",
                tag="node"
            )
    
    # =========================================================================
    # Public API (node_service)
    # =========================================================================
    
    def get_node_id(self) -> str:
        """Get this node's ID."""
        return self._node_id
    
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs."""
        return list(self._connected_peers.keys())
    
    async def send_to_peer(self, peer_id: str, message: SocketMessage) -> bool:
        """Send a message to a specific peer."""
        return await self.socket_api.send_message(peer_id, message)
    
    async def broadcast(self, message: SocketMessage) -> Dict[str, bool]:
        """Broadcast a message to all connected peers."""
        results = {}
        for peer_id in self._connected_peers:
            results[peer_id] = await self.send_to_peer(peer_id, message)
        return results
    
    async def broadcast_to_all(self, message: SocketMessage):
        """Broadcast to all configured peers (including disconnected)."""
        for peer in self._peers:
            await self.socket_api.send_message(peer["node_id"], message)
    
    def get_peer_count(self) -> int:
        """Get number of connected peers."""
        return len(self._connected_peers)
    
    def is_connected_to(self, peer_id: str) -> bool:
        """Check if connected to a specific peer."""
        return peer_id in self._connected_peers