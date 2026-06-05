"""
SSL Demo Module

Provides a service layer for SSL/TLS operations and runs
a demonstration of secure communications.
"""

import asyncio
import ssl
from typing import Dict, Any, Optional
from pathlib import Path

from massir.core.interfaces import IModule


class SSLDemoModule(IModule):
    """
    Provides ssl_service for other modules and demonstrates
    secure TLS communications.
    """
    
    name = "ssl_demo"
    
    def __init__(self):
        self.ssl_api = None
        self.logger = None
        self._config: Dict = {}
        self._server: Optional[asyncio.Server] = None
    
    async def load(self, context):
        """Load module and initialize services."""
        self.ssl_api = context.services.get("ssl_api")
        self.logger = context.services.get("core_logger")
        
        # Load configuration
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("ssl_demo", {})
        
        # Register the service
        context.services.set("ssl_service", self)
        
        if self.logger:
            self.logger.log(
                "SSLDemo module loaded - ssl_service available",
                tag="demo"
            )
    
    async def start(self, context):
        """Run demo if configured."""
        if self._config.get("auto_demo_on_start", False):
            await self._run_demo()
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log(
                "SSLDemo module ready",
                tag="demo"
            )
    
    async def stop(self, context):
        """Cleanup."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        if self.logger:
            self.logger.log("SSLDemo module stopped", tag="demo")
    
    # =========================================================================
    # Public Service Methods
    # =========================================================================
    
    def get_server_context(self, node_id: str = "default") -> ssl.SSLContext:
        """Get a server SSL context."""
        return self.ssl_api.get_server_context(node_id)
    
    def get_client_context(
        self,
        peer_id: str = "default",
        sni_hostname: Optional[str] = None
    ) -> ssl.SSLContext:
        """Get a client SSL context."""
        return self.ssl_api.get_client_context(peer_id, sni_hostname)
    
    def get_certificate_info(self, node_id: str = "default") -> Dict[str, Any]:
        """Get certificate information as a dictionary."""
        cert_info = self.ssl_api.get_cert_info(node_id)
        if cert_info:
            return cert_info.to_dict()
        return {}
    
    def validate_certificate(self, cert_path: str) -> Dict[str, Any]:
        """Validate a certificate file."""
        result = self.ssl_api.validate_certificate(cert_path)
        return {
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "cert_info": result.cert_info.to_dict() if result.cert_info else None
        }
    
    async def start_secure_server(
        self,
        host: str = "127.0.0.1",
        port: int = 8443,
        handler=None
    ) -> asyncio.Server:
        """
        Start a secure TLS server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            handler: Async function to handle client connections
        
        Returns:
            asyncio.Server instance
        """
        if handler is None:
            handler = self._default_handler
        
        server_ctx = self.get_server_context()
        self._server = await asyncio.start_server(
            handler, host, port, ssl=server_ctx
        )
        
        if self.logger:
            self.logger.print(
                f"🔒 Secure server started on {host}:{port}",
                tag="demo"
            )
        
        return self._server
    
    async def connect_to_server(
        self,
        host: str,
        port: int,
        message: bytes,
        sni_hostname: Optional[str] = None
    ) -> bytes:
        """
        Connect to a TLS server and exchange messages.
        
        Args:
            host: Server host
            port: Server port
            message: Message to send
            sni_hostname: Optional SNI hostname
        
        Returns:
            Response from server
        """
        client_ctx = self.get_client_context(sni_hostname=sni_hostname)
        
        reader, writer = await asyncio.open_connection(
            host, port,
            ssl=client_ctx,
            server_hostname=sni_hostname or host
        )
        
        try:
            writer.write(message)
            await writer.drain()
            
            response = await reader.read(4096)
            return response
        finally:
            writer.close()
            await writer.wait_closed()
    
    # =========================================================================
    # Demo Method
    # =========================================================================
    
    async def _run_demo(self):
        """Run a demonstration of SSL features."""
        if not self.logger:
            return
        
        self.logger.print("", tag="demo")
        self.logger.print("=" * 60, tag="demo")
        self.logger.print("🎬 Running SSL Demo", tag="demo")
        self.logger.print("=" * 60, tag="demo")
        
        host = self._config.get("demo_host", "127.0.0.1")
        port = self._config.get("demo_port", 8444)
        
        # Demo 1: Display certificate info
        self.logger.print("\n📜 Certificate Information:", tag="demo")
        cert_info = self.get_certificate_info("default")
        if cert_info:
            self.logger.print(f"  Subject: {cert_info['subject']}", tag="demo")
            self.logger.print(f"  Issuer: {cert_info['issuer']}", tag="demo")
            self.logger.print(f"  Valid from: {cert_info['not_valid_before']}", tag="demo")
            self.logger.print(f"  Valid until: {cert_info['not_valid_after']}", tag="demo")
            self.logger.print(f"  Days until expiry: {cert_info['days_until_expiry']}", tag="demo")
            self.logger.print(f"  Status: {cert_info.get('status', 'UNKNOWN')}", tag="demo")
            if cert_info.get('san_dns_names'):
                self.logger.print(f"  SAN DNS: {', '.join(cert_info['san_dns_names'])}", tag="demo")
            if cert_info.get('san_ip_addresses'):
                self.logger.print(f"  SAN IPs: {', '.join(cert_info['san_ip_addresses'])}", tag="demo")
        
        # Demo 2: Start server and connect client
        self.logger.print(f"\n🔗 Starting secure server on {host}:{port}...", tag="demo")
        
        server_ready = asyncio.Event()
        
        async def demo_handler(reader, writer):
            try:
                data = await reader.read(1024)
                self.logger.print(f"  📨 Server received: {data.decode()}", tag="demo")
                
                response = f"Server received: {data.decode()}"
                writer.write(response.encode())
                await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
        
        server = await self.start_secure_server(host, port, demo_handler)
        
        async with server:
            await asyncio.sleep(0.1)  # Let server start
            
            # Connect client
            self.logger.print(f"  🔌 Client connecting to {host}:{port}...", tag="demo")
            
            try:
                response = await self.connect_to_server(
                    host, port,
                    b"Hello from SSL client!",
                    sni_hostname="localhost"
                )
                self.logger.print(f"  📨 Client received: {response.decode()}", tag="demo")
                self.logger.print("  ✅ TLS connection successful!", tag="demo")
            except Exception as e:
                self.logger.print(f"  ❌ Connection failed: {e}", tag="demo", level="ERROR")
        
        # Demo 3: Module info
        self.logger.print("\nℹ️ SSL Module Info:", tag="demo")
        info = self.ssl_api.get_info()
        self.logger.print(f"  TLS Version: {info.get('tls_version', 'unknown')}", tag="demo")
        self.logger.print(f"  Client cert verification: {info.get('verify_client_certs', False)}", tag="demo")
        self.logger.print(f"  Server cert verification: {info.get('verify_server_certs', True)}", tag="demo")
        self.logger.print(f"  Auto-reload: {info.get('auto_reload', False)}", tag="demo")
        self.logger.print(f"  Cached contexts: {info.get('cached_contexts', {})}", tag="demo")
        
        self.logger.print("\n" + "=" * 60, tag="demo")
        self.logger.print("🎉 Demo completed successfully!", tag="demo")
        self.logger.print("=" * 60, tag="demo")
    
    async def _default_handler(self, reader, writer):
        """Default handler for demo server."""
        try:
            data = await reader.read(1024)
            if self.logger:
                self.logger.print(f"Received: {data}", tag="demo")
            
            writer.write(b"Hello from SSL demo server!")
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()