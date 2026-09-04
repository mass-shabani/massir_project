"""
Network Node Module

Starts the appropriate server (socket or websocket) based on configuration.
This module is essential - without it, no server is started and peers cannot connect.
"""

import asyncio
from typing import Any, Dict, List, Optional

from massir.core.interfaces import IModule


class NetworkNodeModule(IModule):
    """
    Manages server startup and provides node_service.
    
    Responsibilities:
    - Start server via appropriate transport (socket or websocket)
    - Register event handlers
    - Provide node_service for other modules
    """
    
    def __init__(self):
        self.network_api = None
        self.socket_api = None
        self.websocket_api = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
        self._node_id: str = ""
    
    async def start(self, context):
        """
        Start the node:
        1. Retrieve required services from the context
        2. Load configuration from app_settings.json
        3. Register as node_service
        4. Start server and connect to peers
        """
        self.network_api = context.services.get("network_api")
        self.socket_api = context.services.get("socket_api")
        self.websocket_api = context.services.get("websocket_api")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("network_node", {})
        
        # Get self node info
        info = self.network_api.get_info()
        self._node_id = info.get("self_node_id", "unknown")
        
        # Register as service
        context.services.set("node_service", self)
        
        if self.logger:
            self.logger.log(
                f"NetworkNodeModule started - Node ID: {self._node_id}",
                tag="node"
            )
        
        # =========================================================================
        # Step 1: Start server
        # =========================================================================
        if self._config.get("auto_start_server", True):
            await self._start_server()
        
        # =========================================================================
        # Step 2: Connect to peers (network_api handles this)
        # =========================================================================
        results = await self.network_api.connect_all()
        success_count = sum(1 for v in results.values() if v)
        
        if self.logger:
            status = self.network_api.get_network_status()
            self._print_box(
                title=f"🌐 NODE READY: {self._node_id}",
                lines=[
                    f"Peers connected: {success_count}/{len(results)}",
                    f"Topology: {self.network_api.get_topology().get('type', 'unknown')}",
                ],
                color=self.colors.BRIGHT_GREEN if self.colors else None
            )
            
            self.logger.log(
                f"Node '{self._node_id}' ready - "
                f"{status.connected_peers}/{status.required_peers} peers connected",
                tag="node"
            )
    
    async def stop(self, context):
        """Stop the node."""
        await self.network_api.disconnect_all()
        
        if self.logger:
            self._print_box(
                title=f"🛑 NODE STOPPED: {self._node_id}",
                lines=["All connections closed"],
                color=self.colors.BRIGHT_RED if self.colors else None
            )
    
    # =========================================================================
    # Server Startup
    # =========================================================================
    
    async def _start_server(self):
        """Start the appropriate server based on configuration."""
        server_transport = self._config.get("server_transport", "socket")
        listen_config = self._config.get("listen", {})
        
        if server_transport == "socket" and self.socket_api:
            socket_conf = listen_config.get("socket", {})
            await self.socket_api.create_server(
                host=socket_conf.get("host", "0.0.0.0"),
                port=socket_conf.get("port", 8443),
                mode="message",
                use_tls=socket_conf.get("use_tls", True),
            )
            if self.logger:
                self._print_box(
                    title="🖥️  SOCKET SERVER STARTED",
                    lines=[
                        f"Node ID:  {self._node_id}",
                        f"Address:  {socket_conf.get('host', '0.0.0.0')}:{socket_conf.get('port', 8443)}",
                        f"Protocol: TLS 1.3",
                    ],
                    color=self.colors.BRIGHT_GREEN if self.colors else None
                )
        
        elif server_transport == "websocket" and self.websocket_api:
            ws_conf = listen_config.get("websocket", {})
            await self.websocket_api.create_server(
                host=ws_conf.get("host", "0.0.0.0"),
                port=ws_conf.get("port", 8444),
                path=ws_conf.get("path", "/ws"),
                use_tls=ws_conf.get("use_tls", True),
                compression=True,
            )
            if self.logger:
                self._print_box(
                    title="🌐 WEBSOCKET SERVER STARTED",
                    lines=[
                        f"Node ID:  {self._node_id}",
                        f"Address:  {ws_conf.get('host', '0.0.0.0')}:{ws_conf.get('port', 8444)}{ws_conf.get('path', '/ws')}",
                        f"Protocol: WSS (TLS)",
                    ],
                    color=self.colors.BRIGHT_GREEN if self.colors else None
                )
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def get_node_id(self) -> str:
        return self._node_id
    
    def get_network_status(self) -> Dict:
        return self.network_api.get_network_status().to_dict()
    
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
        if not self.logger:
            return
        
        width = 62
        
        if compact:
            separator = "─" * width
            self.logger.print(f"┌{separator}┐", tag="node", color=color)
            self.logger.print(
                f"│ {title:<{width-2}} │",
                tag="node",
                color=color,
                bold=True
            )
            for line in lines:
                if len(line) > width - 4:
                    line = line[:width-7] + "..."
                self.logger.print(
                    f"│   {line:<{width-4}} │",
                    tag="node",
                    color=color
                )
            self.logger.print(f"└{separator}┘", tag="node", color=color)
        else:
            separator = "═" * width
            self.logger.print(f"╔{separator}╗", tag="node", color=color, bold=True)
            self.logger.print(
                f"║  {title:<{width-3}}║",
                tag="node",
                color=color,
                bold=True
            )
            self.logger.print(f"╠{separator}╣", tag="node", color=color, bold=True)
            for line in lines:
                if len(line) > width - 3:
                    line = line[:width-6] + "..."
                self.logger.print(
                    f"║  {line:<{width-3}}║",
                    tag="node",
                    color=color
                )
            self.logger.print(f"╚{separator}╝", tag="node", color=color, bold=True)
        
        self.logger.print("", tag="node")
