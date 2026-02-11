"""
Network Info Module - Example of using net_api and router_api.

This module demonstrates how to use network utilities and
create a separate router using router_api.
"""
from massir.core.interfaces import IModule


class NetworkInfoModule(IModule):
    """
    Network info module demonstrating net_api and router_api usage.
    
    Provides network information endpoints using net_api utilities.
    """
    
    name = "network_info"
    
    def __init__(self):
        self.http_api = None
        self.router_api = None
        self.net_api = None
        self.logger = None
    
    async def load(self, context):
        """Get APIs from services."""
        self.http_api = context.services.get("http_api")
        self.router_api = context.services.get("router_api")
        self.net_api = context.services.get("net_api")
        self.logger = context.services.get("core_logger")
        
        if self.logger:
            self.logger.log("NetworkInfo module loaded", tag="network")
    
    async def start(self, context):
        """Register network information routes using router_api."""
        
        # Create a separate router for network info
        router = self.router_api.create(
            prefix="/network",
            tags=["network"]
        )
        
        # GET /network/hostname - Get hostname
        @self.http_api.get("/hostname", tags=["network"], summary="Get system hostname")
        async def get_hostname():
            """Get the system hostname."""
            return {
                "hostname": self.net_api.get_hostname()
            }
        
        # GET /network/ip - Get IP address
        @self.http_api.get("/ip", tags=["network"], summary="Get IP address")
        async def get_ip():
            """Get the local IP address."""
            return {
                "ip_address": self.net_api.get_ip_address()
            }
        
        # GET /network/info - Get full network info
        @self.http_api.get("/info", tags=["network"], summary="Get network information")
        async def get_network_info():
            """Get comprehensive network information."""
            return self.net_api.get_network_info()
        
        # GET /network/validate/{ip} - Validate IP address
        @self.http_api.get("/validate/{ip}", tags=["network"], summary="Validate IP address")
        async def validate_ip(ip: str):
            """Validate if the given string is a valid IP address."""
            is_valid = self.net_api.is_valid_ip(ip)
            is_ipv4 = self.net_api.is_ipv4(ip) if is_valid else False
            is_ipv6 = self.net_api.is_ipv6(ip) if is_valid else False
            
            return {
                "ip": ip,
                "valid": is_valid,
                "type": "IPv4" if is_ipv4 else "IPv6" if is_ipv6 else "Invalid"
            }
        
        # GET /network/port/{port} - Check port availability
        @self.http_api.get("/port/{port}", tags=["network"], summary="Check port availability")
        async def check_port(port: int):
            """Check if a port is available."""
            is_available = self.net_api.is_port_available(port)
            
            return {
                "port": port,
                "available": is_available,
                "status": "Available" if is_available else "In use"
            }
        
        # GET /network/parse - Parse URL
        @self.http_api.get("/parse", tags=["network"], summary="Parse URL")
        async def parse_url(url: str):
            """Parse a URL into components."""
            return self.net_api.parse_url(url)
        
        # GET /network/build - Build URL
        @self.http_api.get("/build", tags=["network"], summary="Build URL")
        async def build_url(
            scheme: str = "http",
            host: str = "localhost",
            port: int = None,
            path: str = "",
            query: str = ""
        ):
            """Build a URL from components."""
            url = self.net_api.build_url(scheme, host, port, path, query)
            
            return {
                "url": url
            }
        
        if self.logger:
            self.logger.log("Network info routes registered", tag="network")
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log("NetworkInfo module is ready", tag="network")
    
    async def stop(self, context):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("NetworkInfo module stopped", tag="network")
