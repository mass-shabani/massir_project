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
    """
    
    async def start(self, context):
        """Start the HTTP server."""
        server_api = context.services.get("server_api")
        net_api = context.services.get("net_api")
        logger = context.services.get("core_logger")
        config = context.services.get("core_config")
        
        if not server_api:
            if logger:
                logger.log("ServerAPI not available, cannot start server", level="ERROR", tag="server")
            return
        
        # Create server configuration
        server_config = server_api.create_config()
        
        # Check if port is available
        if not net_api.is_port_available(server_config.port, server_config.host):
            if logger:
                logger.log(
                    f"Port {server_config.port} is already in use on {server_config.host}",
                    level="WARNING",
                    tag="server"
                )
            # Try to find an available port
            available_port = net_api.find_available_port(
                server_config.port, 
                server_config.port + 100, 
                server_config.host
            )
            if available_port:
                server_config.port = available_port
                if logger:
                    logger.log(
                        f"Using available port: {server_config.port}",
                        level="WARNING",
                        tag="server"
                    )
            else:
                if logger:
                    logger.log(
                        f"No available ports in range {server_config.port}-{server_config.port + 100}",
                        level="ERROR",
                        tag="server"
                    )
                raise RuntimeError(f"No available ports in range {server_config.port}-{server_config.port + 100}")
        
        # Get server runner and register as background task
        app = context.get_app()
        server_runner = server_api.get_server_runner(server_config)
        app.register_background_task(server_runner)
        
        if logger:
            logger.log(
                f"HTTP Server is running and Database Example API available at http://{server_config.host}:{server_config.port}",
                tag="server"
            )
    
    async def stop(self, context):
        """Stop the HTTP server."""
        server_api = context.services.get("server_api")
        if server_api:
            await server_api.stop_server()
