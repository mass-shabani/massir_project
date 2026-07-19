"""
Socket Node Module

Manages a node in the distributed socket network:
- Starts a TLS server to accept connections
- Connects to all configured peers
- Monitors connections via heartbeat
- Provides node_service to other modules

NOTE: This module does NOT import types directly from network_socket.
All message creation goes through socket_api factory methods.

OUTPUT STRATEGY:
- logger.print: For visual events (server start, connections, messages)
- logger.log: For general info, warnings, and errors
"""

import asyncio
from typing import Any, Dict, List, Optional

from massir.core.interfaces import IModule


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
                tag="node"
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
            
            # ✅ VISUAL OUTPUT: Server started
            if self.logger:
                self._print_box(
                    title="🖥️  SERVER STARTED",
                    lines=[
                        f"Node ID: {self._node_id}",
                        f"Address: {listen_host}:{listen_port}",
                        f"Protocol: {'TLS 1.3' if use_tls else 'Plain TCP'}",
                        f"Mode: Message (framed JSON)",
                    ],
                    color=self.colors.BRIGHT_GREEN if self.colors else None
                )
        
        # Connect to peers
        if self._config.get("auto_connect_on_start", True):
            await self._connect_to_all_peers()
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            # Show summary of configured peers
            self.logger.log(
                f"Node '{self._node_id}' ready with {len(self._peers)} configured peer(s)",
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
        
        # ✅ VISUAL OUTPUT: Server stopped
        if self.logger:
            self._print_box(
                title="🛑 SERVER STOPPED",
                lines=[f"Node '{self._node_id}' shutdown complete"],
                color=self.colors.BRIGHT_RED if self.colors else None
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
                async def on_disconnect(conn, pid=peer_id, h=host, p=port):
                    self._connected_peers.pop(pid, None)
                    if self.logger:
                        # ✅ VISUAL OUTPUT: Disconnection
                        self._print_box(
                            title=f"❌ PEER DISCONNECTED: {pid}",
                            lines=[
                                f"Address: {h}:{p}",
                                f"Status: Auto-reconnect enabled",
                            ],
                            color=self.colors.BRIGHT_RED if self.colors else None
                        )
                
                # Register connect handler (for when reconnect succeeds)
                async def on_connect(conn, pid=peer_id, h=host, p=port):
                    self._connected_peers[pid] = client
                    if self.logger:
                        # ✅ VISUAL OUTPUT: Connection established
                        self._print_box(
                            title=f"✅ PEER CONNECTED: {pid}",
                            lines=[
                                f"Address: {h}:{p}",
                                f"Protocol: {'TLS' if use_tls else 'Plain'}",
                            ],
                            color=self.colors.BRIGHT_GREEN if self.colors else None
                        )
                
                client.on_disconnect(on_disconnect)
                client.on_connect(on_connect)
                
                # Check if already connected
                if client.is_connected:
                    self._connected_peers[peer_id] = client
                    if self.logger:
                        # ✅ VISUAL OUTPUT: Initial connection
                        self._print_box(
                            title=f"✅ PEER CONNECTED: {peer_id}",
                            lines=[
                                f"Address: {host}:{port}",
                                f"Protocol: {'TLS' if use_tls else 'Plain'}",
                            ],
                            color=self.colors.BRIGHT_GREEN if self.colors else None
                        )
                else:
                    # Not connected yet, but auto-reconnect is active
                    if self.logger:
                        self.logger.log(
                            f"⏳ Peer '{peer_id}' at {host}:{port} - waiting for connection (auto-reconnect active)",
                            tag="node",
                            level="WARNING",
                            text_color=self.colors.BRIGHT_YELLOW if self.colors else None
                        )
            
            except Exception as e:
                if self.logger:
                    self.logger.log(
                        f"⚠️ Failed to setup connection to peer '{peer_id}' at {host}:{port}: {e}",
                        tag="node",
                        level="WARNING",
                        text_color=self.colors.BRIGHT_YELLOW if self.colors else None
                    )
    
    # =========================================================================
    # Inbound Handlers
    # =========================================================================
    
    async def _on_inbound_connection(self, conn):
        """Handle inbound connection."""
        remote = conn.remote_address
        if self.logger:
            # ✅ VISUAL OUTPUT: Inbound connection
            self._print_box(
                title="📥 INBOUND CONNECTION",
                lines=[
                    f"From: {remote[0]}:{remote[1]}",
                    f"Status: Accepted",
                ],
                color=self.colors.BRIGHT_CYAN if self.colors else None
            )
    
    async def _on_inbound_disconnection(self, conn):
        """Handle inbound disconnection."""
        remote = conn.remote_address
        if self.logger:
            self.logger.log(
                f"Connection closed from {remote[0]}:{remote[1]}",
                tag="node"
            )
    
    async def _on_inbound_message(self, message, conn):
        """Handle inbound message (dispatch to handlers)."""
        # Use MessageType from socket_api factory (no direct import)
        MessageType = self.socket_api.MessageType
        
        # Skip control messages
        if message.type in (MessageType.PING, MessageType.PONG):
            return
        
        if self.logger:
            peer_id = conn.peer_id or "unknown"
            payload_preview = str(message.payload)[:80]
            
            # ✅ VISUAL OUTPUT: Received message
            self._print_box(
                title=f"📨 RECEIVED from '{peer_id}'",
                lines=[
                    f"Type: {message.type.value}",
                    f"Payload: {payload_preview}{'...' if len(str(message.payload)) > 80 else ''}",
                ],
                color=self.colors.BRIGHT_CYAN if self.colors else None,
                compact=True
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
    
    def create_message(self, msg_type, payload=None, **kwargs):
        """
        Create a message using socket_api factory.
        
        This is a convenience method that delegates to socket_api.create_message()
        so consumer modules don't need direct access to socket_api.
        """
        return self.socket_api.create_message(msg_type, payload, **kwargs)
    
    async def send_to_peer(self, peer_id: str, message) -> bool:
        """Send a message to a specific peer."""
        success = await self.socket_api.send_message(peer_id, message)
        
        if self.logger and success:
            # ✅ VISUAL OUTPUT: Sent message
            payload_preview = str(message.payload)[:60]
            self._print_box(
                title=f"📤 SENT to '{peer_id}'",
                lines=[
                    f"Type: {message.type.value}",
                    f"Payload: {payload_preview}{'...' if len(str(message.payload)) > 60 else ''}",
                ],
                color=self.colors.BRIGHT_MAGENTA if self.colors else None,
                compact=True
            )
        
        return success
    
    async def broadcast(self, message) -> Dict[str, bool]:
        """Broadcast a message to all connected peers."""
        results = {}
        for peer_id in self._connected_peers:
            results[peer_id] = await self.send_to_peer(peer_id, message)
        return results
    
    async def broadcast_to_all(self, message):
        """Broadcast to all configured peers (including disconnected)."""
        for peer in self._peers:
            await self.socket_api.send_message(peer["node_id"], message)
    
    def get_peer_count(self) -> int:
        """Get number of connected peers."""
        return len(self._connected_peers)
    
    def is_connected_to(self, peer_id: str) -> bool:
        """Check if connected to a specific peer."""
        return peer_id in self._connected_peers
    
    # =========================================================================
    # Visual Helpers
    # =========================================================================
    
    def _print_box(
        self,
        title: str,
        lines: List[str],
        color=None,
        compact: bool = False
    ):
        """
        Print a visually distinct box for important events.
        
        Args:
            title: Box title (with emoji)
            lines: List of content lines
            color: Text color
            compact: If True, use single-line borders
        """
        if not self.logger:
            return
        
        width = 60
        
        if compact:
            # Compact format for frequent messages
            separator = "─" * width
            self.logger.print(f"┌{separator}┐", tag="node", text_color=color)
            self.logger.print(f"│ {title:<{width-2}} │", tag="node", text_color=color)
            for line in lines:
                # Truncate if too long
                if len(line) > width - 4:
                    line = line[:width-7] + "..."
                self.logger.print(f"│   {line:<{width-4}} │", tag="node", text_color=color)
            self.logger.print(f"└{separator}┘", tag="node", text_color=color)
        else:
            # Full format for important events
            separator = "═" * width
            self.logger.print(f"╔{separator}╗", tag="node", text_color=color)
            self.logger.print(f"║  {title:<{width-3}} ║", tag="node", text_color=color)
            self.logger.print(f"╠{separator}╣", tag="node", text_color=color)
            for line in lines:
                self.logger.print(f"║  {line:<{width-3}} ║", tag="node", text_color=color)
            self.logger.print(f"╚{separator}╝", tag="node", text_color=color)
        
        self.logger.print("", tag="node")  # Empty line after box