"""
Socket Node Module

Manages a node in the distributed socket network:
- Starts a TLS server to accept connections
- Connects to all configured peers
- Monitors connections via heartbeat
- Provides node_service to other modules

NOTE: This module does NOT import types directly from network_socket.
All message creation goes through socket_api factory methods to maintain
loose coupling between modules.

OUTPUT STRATEGY:
- logger.print: For visual events (server start, connections, messages)
  → Uses 'color' parameter with optional 'bg_color' and 'bold'
  → Two formats: compact (frequent events) and full (important events)
- logger.log: For general info, warnings, and errors
  → Uses 'text_color' parameter
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
    
    The module acts as both a server (accepting inbound connections) and
    a client (connecting to peers), enabling full mesh topology.
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
        # Retrieve required services from the context
        self.socket_api = context.services.get("socket_api")
        self.ssl_api = context.services.get("ssl_api")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        # Load configuration from app_settings.json
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("socket_node", {})
        
        self._node_id = self._config.get("node_id", "unknown")
        self._peers = self._config.get("peers", [])
        
        # Register this module as 'node_service' for other modules to use
        context.services.set("node_service", self)
        
        if self.logger:
            self.logger.log(
                f"SocketNodeModule loaded - Node ID: {self._node_id}",
                tag="node"
            )
    
    async def start(self, context):
        """Start server and connect to peers."""
        # =========================================================================
        # Step 1: Register global event handlers
        # =========================================================================
        self.socket_api.on_inbound_connection(self._on_inbound_connection)
        self.socket_api.on_inbound_disconnection(self._on_inbound_disconnection)
        self.socket_api.on_inbound_message(self._on_inbound_message)
        
        # =========================================================================
        # Step 2: Start the TLS/TCP server (non-blocking)
        # =========================================================================
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
                self._print_box(
                    title="🖥️  SERVER STARTED",
                    lines=[
                        f"Node ID:  {self._node_id}",
                        f"Address:  {listen_host}:{listen_port}",
                        f"Protocol: {'TLS 1.3' if use_tls else 'Plain TCP'}",
                        f"Mode:     Message (framed JSON)",
                    ],
                    color=self.colors.BRIGHT_GREEN if self.colors else None,
                    bg_color=self.colors.BG_GREEN if self.colors else None
                )
        
        # =========================================================================
        # Step 3: Connect to all configured peers (non-blocking)
        # =========================================================================
        if self._config.get("auto_connect_on_start", True):
            await self._connect_to_all_peers()
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log(
                f"Node '{self._node_id}' ready with {len(self._peers)} configured peer(s)",
                tag="node"
            )
    
    async def stop(self, context):
        """Stop the node and cleanup all connections."""
        # Disconnect from all peers
        for peer in self._peers:
            try:
                await self.socket_api.disconnect_from_peer(peer["node_id"])
            except Exception:
                pass
        
        # Stop the server
        if self._server:
            await self.socket_api.stop_server()
        
        if self.logger:
            self._print_box(
                title="🛑 SERVER STOPPED",
                lines=[f"Node '{self._node_id}' shutdown complete"],
                color=self.colors.BRIGHT_RED if self.colors else None
            )
    
    # =========================================================================
    # Peer Connection Management
    # =========================================================================
    
    async def _connect_to_all_peers(self):
        """
        Connect to all configured peers.
        
        Even if initial connection fails, the client remains in the pool
        and will continue trying to reconnect in the background.
        """
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
                
                # Register disconnect handler for this peer
                async def on_disconnect(conn, pid=peer_id, h=host, p=port):
                    self._connected_peers.pop(pid, None)
                    if self.logger:
                        self._print_box(
                            title=f"❌ PEER DISCONNECTED: {pid}",
                            lines=[
                                f"Address: {h}:{p}",
                                f"Status:  Auto-reconnect enabled",
                            ],
                            color=self.colors.BRIGHT_RED if self.colors else None
                        )
                
                # Register connect handler (triggered on successful reconnect)
                async def on_connect(conn, pid=peer_id, h=host, p=port):
                    self._connected_peers[pid] = client
                    if self.logger:
                        self._print_box(
                            title=f"✅ PEER CONNECTED: {pid}",
                            lines=[
                                f"Address:  {h}:{p}",
                                f"Protocol: {'TLS' if use_tls else 'Plain'}",
                            ],
                            color=self.colors.BRIGHT_GREEN if self.colors else None
                        )
                
                client.on_disconnect(on_disconnect)
                client.on_connect(on_connect)
                
                # Check if already connected on first attempt
                if client.is_connected:
                    self._connected_peers[peer_id] = client
                    if self.logger:
                        self._print_box(
                            title=f"✅ PEER CONNECTED: {peer_id}",
                            lines=[
                                f"Address:  {host}:{port}",
                                f"Protocol: {'TLS' if use_tls else 'Plain'}",
                            ],
                            color=self.colors.BRIGHT_GREEN if self.colors else None
                        )
                else:
                    # Not connected yet, but auto-reconnect is active
                    if self.logger:
                        self.logger.log(
                            f"⏳ Peer '{peer_id}' at {host}:{port} - waiting for connection",
                            tag="node",
                            level="WARNING",
                            text_color=self.colors.BRIGHT_YELLOW if self.colors else None
                        )
            
            except Exception as e:
                if self.logger:
                    self.logger.log(
                        f"⚠️ Failed to setup peer '{peer_id}' at {host}:{port}: {e}",
                        tag="node",
                        level="WARNING",
                        text_color=self.colors.BRIGHT_YELLOW if self.colors else None
                    )
    
    # =========================================================================
    # Inbound Event Handlers
    # =========================================================================
    
    async def _on_inbound_connection(self, conn):
        """Handle a new inbound connection from a remote peer."""
        remote = conn.remote_address
        if self.logger:
            self._print_box(
                title="📥 INBOUND CONNECTION",
                lines=[
                    f"From:   {remote[0]}:{remote[1]}",
                    f"Status: Accepted",
                ],
                color=self.colors.BRIGHT_CYAN if self.colors else None,
                compact=True
            )
    
    async def _on_inbound_disconnection(self, conn):
        """Handle an inbound connection being closed."""
        remote = conn.remote_address
        if self.logger:
            self.logger.log(
                f"Connection closed from {remote[0]}:{remote[1]}",
                tag="node"
            )
    
    async def _on_inbound_message(self, message, conn):
        """
        Handle an inbound message from a peer.
        
        Control messages (PING/PONG) are filtered out as they are handled
        internally by the socket layer for heartbeat purposes.
        """
        MessageType = self.socket_api.MessageType
        
        # Skip control messages - they're handled at the socket level
        if message.type in (MessageType.PING, MessageType.PONG):
            return
        
        if self.logger:
            peer_id = conn.peer_id or "unknown"
            payload_preview = str(message.payload)[:70]
            
            self._print_box(
                title=f"📨 RECEIVED from '{peer_id}'",
                lines=[
                    f"Type:    {message.type.value}",
                    f"Payload: {payload_preview}{'...' if len(str(message.payload)) > 70 else ''}",
                ],
                color=self.colors.BRIGHT_CYAN if self.colors else None,
                compact=True
            )
    
    # =========================================================================
    # Public API (node_service)
    #
    # These methods are exposed to other modules via context.services
    # =========================================================================
    
    def get_node_id(self) -> str:
        """Get this node's unique identifier."""
        return self._node_id
    
    def get_connected_peers(self) -> List[str]:
        """Get list of currently connected peer IDs."""
        return list(self._connected_peers.keys())
    
    def create_message(self, msg_type, payload=None, **kwargs):
        """
        Create a message using socket_api factory.
        
        This convenience method delegates to socket_api.create_message()
        so consumer modules don't need direct access to socket_api or
        any imports from network_socket.
        
        Args:
            msg_type: Message type string or MessageType enum
            payload: Message payload (any JSON-serializable data)
            **kwargs: Additional message fields (message_id, correlation_id, metadata)
        
        Returns:
            SocketMessage instance
        """
        return self.socket_api.create_message(msg_type, payload, **kwargs)
    
    async def send_to_peer(self, peer_id: str, message) -> bool:
        """
        Send a message to a specific peer.
        
        Args:
            peer_id: Target peer identifier
            message: SocketMessage to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        success = await self.socket_api.send_message(peer_id, message)
        
        if self.logger and success:
            payload_preview = str(message.payload)[:60]
            self._print_box(
                title=f"📤 SENT to '{peer_id}'",
                lines=[
                    f"Type:    {message.type.value}",
                    f"Payload: {payload_preview}{'...' if len(str(message.payload)) > 60 else ''}",
                ],
                color=self.colors.BRIGHT_MAGENTA if self.colors else None,
                compact=True
            )
        
        return success
    
    async def broadcast(self, message) -> Dict[str, bool]:
        """
        Broadcast a message to all currently connected peers.
        
        Args:
            message: SocketMessage to broadcast
        
        Returns:
            Dictionary mapping peer_id to success status
        """
        results = {}
        for peer_id in self._connected_peers:
            results[peer_id] = await self.send_to_peer(peer_id, message)
        return results
    
    async def broadcast_to_all(self, message):
        """
        Broadcast to all configured peers (including currently disconnected ones).
        
        Messages to disconnected peers will be queued if send queue is enabled,
        otherwise they will fail silently (auto-reconnect will handle future sends).
        """
        for peer in self._peers:
            await self.socket_api.send_message(peer["node_id"], message)
    
    def get_peer_count(self) -> int:
        """Get the number of currently connected peers."""
        return len(self._connected_peers)
    
    def is_connected_to(self, peer_id: str) -> bool:
        """Check if currently connected to a specific peer."""
        return peer_id in self._connected_peers
    
    # =========================================================================
    # Visual Output Helpers
    #
    # These methods provide consistent visual formatting for important events.
    # Two modes are available:
    # - Full: Double-line borders for important events (server start, connections)
    # - Compact: Single-line borders for frequent events (messages sent/received)
    # =========================================================================
    
    def _print_box(
        self,
        title: str,
        lines: List[str],
        color=None,
        bg_color=None,
        compact: bool = False
    ):
        """
        Print a visually distinct box for important events.
        
        Args:
            title: Box title (typically with emoji)
            lines: List of content lines to display
            color: Text color (ANSI code from Colors class)
            bg_color: Background color for title (ANSI code)
            compact: If True, use single-line borders (for frequent events)
        """
        if not self.logger:
            return
        
        width = 62
        
        if compact:
            # Compact format for frequent messages (received/sent)
            separator = "─" * width
            
            # Top border
            self.logger.print(
                f"┌{separator}┐",
                tag="node",
                color=color
            )
            # Title line (with optional bg_color and bold)
            self.logger.print(
                f"│ {title:<{width-2}} │",
                tag="node",
                color=color,
                bg_color=bg_color,
                bold=True
            )
            # Content lines
            for line in lines:
                if len(line) > width - 4:
                    line = line[:width-7] + "..."
                self.logger.print(
                    f"│   {line:<{width-4}} │",
                    tag="node",
                    color=color
                )
            # Bottom border
            self.logger.print(
                f"└{separator}┘",
                tag="node",
                color=color
            )
        else:
            # Full format for important events (server start, connections)
            separator = "═" * width
            
            # Top border
            self.logger.print(
                f"╔{separator}╗",
                tag="node",
                color=color,
                bold=True
            )
            # Title line with bg_color highlight
            self.logger.print(
                f"║  {title:<{width-3}}║",
                tag="node",
                color=color,
                bg_color=bg_color,
                bold=True
            )
            # Separator between title and content
            self.logger.print(
                f"╠{separator}╣",
                tag="node",
                color=color,
                bold=True
            )
            # Content lines
            for line in lines:
                if len(line) > width - 3:
                    line = line[:width-6] + "..."
                self.logger.print(
                    f"║  {line:<{width-3}} ║",
                    tag="node",
                    color=color
                )
            # Bottom border
            self.logger.print(
                f"╚{separator}╝",
                tag="node",
                color=color,
                bold=True
            )
        
        # Empty line after box for visual separation
        self.logger.print("", tag="node")