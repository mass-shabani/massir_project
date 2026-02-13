"""
Server Manager Module - Manages HTTP server lifecycle.

This module is responsible for starting and managing the HTTP server
using the ServerAPI provided by network_fastapi.
"""
from massir.core.interfaces import IModule


class ServerManagerModule(IModule):
    """
    Server manager module.
    
    This module starts the HTTP server using the ServerAPI.
    It demonstrates how consuming modules control server lifecycle.
    """
    
    name = "server_manager"
    
    def __init__(self):
        self.server_api = None
        self.net_api = None
        self.logger = None
        self.config = None
    
    async def load(self, context):
        """Get APIs from services."""
        self.server_api = context.services.get("server_api")
        self.net_api = context.services.get("net_api")
        self.logger = context.services.get("core_logger")
        self.config = context.services.get("core_config")
        
        if self.logger:
            self.logger.log("ServerManager module loaded", tag="server")
    
    async def start(self, context):
        """Start the HTTP server."""
        if not self.server_api:
            if self.logger:
                self.logger.log("ServerAPI not available, cannot start server", level="ERROR", tag="server")
            return
        
        # Create server configuration
        server_config = self.server_api.create_config()
        
        # Check if port is available
        if not self.net_api.is_port_available(server_config.port, server_config.host):
            if self.logger:
                self.logger.log(
                    f"Port {server_config.port} is already in use on {server_config.host}",
                    level="WARNING",
                    tag="server"
                )
            # Try to find an available port
            available_port = self.net_api.find_available_port(
                server_config.port, 
                server_config.port + 100, 
                server_config.host
            )
            if available_port:
                server_config.port = available_port
                if self.logger:
                    self.logger.log(
                        f"Using available port: {server_config.port}",
                        level="WARNING",
                        tag="server"
                    )
            else:
                if self.logger:
                    self.logger.log(
                        f"No available ports in range {server_config.port}-{server_config.port + 100}",
                        level="ERROR",
                        tag="server"
                    )
                raise RuntimeError(f"No available ports in range {server_config.port}-{server_config.port + 100}")
        
        # Get server runner and register as background task
        app = context.get_app()
        server_runner = self.server_api.get_server_runner(server_config)
        app.register_background_task(server_runner)
        
        if self.logger:
            self.logger.log(
                f"HTTP server starting on http://{server_config.host}:{server_config.port}",
                tag="server"
            )
            self.logger.log(
                f"API documentation: http://{server_config.host}:{server_config.port}/docs",
                tag="server"
            )
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            status = self.server_api.status if self.server_api else None
            if status and status.is_running:
                self.logger.log(
                    f"Server is running at {status.url}",
                    tag="server"
                )
            else:
                self.logger.log("ServerManager module is ready", tag="server")
    
    async def stop(self, context):
        """Stop the HTTP server."""
        if self.server_api:
            await self.server_api.stop_server()
        
        if self.logger:
            self.logger.log("ServerManager module stopped", tag="server")
