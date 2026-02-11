"""
Network API for specialized network services.

This module provides network utilities beyond HTTP.
"""
import asyncio
import socket
import ipaddress
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass


@dataclass
class NetworkInfo:
    """Network information."""
    hostname: str
    ip_address: str
    port: int
    is_ipv6: bool


@dataclass
class PortInfo:
    """Port information."""
    port: int
    is_open: bool
    service: Optional[str] = None


class NetAPI:
    """
    Network API for specialized network services.
    
    Provides network utilities beyond HTTP functionality.
    """
    
    def __init__(self, config_api=None):
        """
        Initialize Network API.
        
        Args:
            config_api: Configuration API for settings
        """
        self._config_api = config_api
        self._hostname: Optional[str] = None
        self._ip_address: Optional[str] = None
    
    def get_hostname(self) -> str:
        """
        Get the system hostname.
        
        Returns:
            System hostname
        """
        if self._hostname is None:
            self._hostname = socket.gethostname()
        return self._hostname
    
    def get_ip_address(self, host: str = None) -> str:
        """
        Get the IP address for a host.
        
        Args:
            host: Hostname or None for local host
        
        Returns:
            IP address string
        """
        if host is None:
            host = self.get_hostname()
        
        try:
            ip = socket.gethostbyname(host)
            return ip
        except socket.gaierror:
            return "127.0.0.1"
    
    def is_ipv6(self, address: str) -> bool:
        """
        Check if an address is IPv6.
        
        Args:
            address: IP address string
        
        Returns:
            True if IPv6, False otherwise
        """
        try:
            return isinstance(ipaddress.ip_address(address), ipaddress.IPv6Address)
        except ValueError:
            return False
    
    def is_ipv4(self, address: str) -> bool:
        """
        Check if an address is IPv4.
        
        Args:
            address: IP address string
        
        Returns:
            True if IPv4, False otherwise
        """
        try:
            return isinstance(ipaddress.ip_address(address), ipaddress.IPv4Address)
        except ValueError:
            return False
    
    def is_valid_ip(self, address: str) -> bool:
        """
        Check if an address is a valid IP address.
        
        Args:
            address: IP address string
        
        Returns:
            True if valid IP, False otherwise
        """
        try:
            ipaddress.ip_address(address)
            return True
        except ValueError:
            return False
    
    def is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
        """
        Check if a port is available.
        
        Args:
            port: Port number
            host: Host address
        
        Returns:
            True if port is available, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return True
        except OSError:
            return False
    
    def find_available_port(self, start_port: int = 8000, 
                        end_port: int = 9000,
                        host: str = "127.0.0.1") -> Optional[int]:
        """
        Find an available port in a range.
        
        Args:
            start_port: Starting port number
            end_port: Ending port number
            host: Host address
        
        Returns:
            Available port number or None
        """
        for port in range(start_port, end_port + 1):
            if self.is_port_available(port, host):
                return port
        return None
    
    async def check_port(self, host: str, port: int, 
                     timeout: float = 1.0) -> PortInfo:
        """
        Asynchronously check if a port is open.
        
        Args:
            host: Host address
            port: Port number
            timeout: Connection timeout in seconds
        
        Returns:
            PortInfo object
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return PortInfo(port=port, is_open=True)
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return PortInfo(port=port, is_open=False)
    
    async def check_ports(self, host: str, ports: List[int],
                      timeout: float = 1.0) -> List[PortInfo]:
        """
        Asynchronously check multiple ports.
        
        Args:
            host: Host address
            ports: List of port numbers
            timeout: Connection timeout in seconds
        
        Returns:
            List of PortInfo objects
        """
        tasks = [self.check_port(host, port, timeout) for port in ports]
        return await asyncio.gather(*tasks)
    
    def get_network_info(self, host: str = None, port: int = None) -> NetworkInfo:
        """
        Get comprehensive network information.
        
        Args:
            host: Hostname or None for local
            port: Port number
        
        Returns:
            NetworkInfo object
        """
        hostname = host or self.get_hostname()
        ip = self.get_ip_address(hostname)
        is_ipv6 = self.is_ipv6(ip)
        
        return NetworkInfo(
            hostname=hostname,
            ip_address=ip,
            port=port or 0,
            is_ipv6=is_ipv6
        )
    
    def parse_url(self, url: str) -> Dict[str, Any]:
        """
        Parse a URL into components.
        
        Args:
            url: URL string
        
        Returns:
            Dictionary with URL components
        """
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        return {
            "scheme": parsed.scheme,
            "hostname": parsed.hostname,
            "port": parsed.port,
            "path": parsed.path,
            "query": parsed.query,
            "fragment": parsed.fragment,
            "username": parsed.username,
            "password": parsed.password
        }
    
    def build_url(self, scheme: str, host: str, port: int = None,
                path: str = "", query: str = "") -> str:
        """
        Build a URL from components.
        
        Args:
            scheme: URL scheme (http, https, etc.)
            host: Hostname or IP address
            port: Port number (optional)
            path: URL path
            query: Query string
        
        Returns:
            Complete URL string
        """
        url = f"{scheme}://{host}"
        if port:
            url += f":{port}"
        if path:
            url += path
        if query:
            url += f"?{query}"
        return url
    
    def get_local_networks(self) -> List[str]:
        """
        Get local network interfaces.
        
        Returns:
            List of network interface addresses
        """
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return [ip]
        except socket.gaierror:
            return ["127.0.0.1"]
