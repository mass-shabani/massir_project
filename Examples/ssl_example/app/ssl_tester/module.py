"""
SSL Tester Module

Automatically tests all features of the network_ssl module
on startup and displays detailed results.
"""

import asyncio
import ssl
from typing import Dict, Any
from pathlib import Path

from massir.core.interfaces import IModule


class SSLTesterModule(IModule):
    """
    Tests all SSL/TLS operations and displays results.
    
    This module runs comprehensive tests on:
    - Certificate loading and validation
    - Server SSL context creation
    - Client SSL context creation
    - mTLS (mutual TLS)
    - Certificate information extraction
    - Expiry checking
    - Real TLS server/client connection
    """
    
    def __init__(self):
        self.ssl_api = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
        self._test_results: Dict[str, Any] = {}
        self._certs_dir: Path = Path(__file__).parent.parent.parent / "certs"
    
    async def load(self, context):
        """Load module and get required services."""
        self.ssl_api = context.services.get("ssl_api")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        # Load configuration
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("ssl_tester", {})
        
        if self.logger:
            self.logger.log(
                "SSLTester module loaded",
                tag="tester",
                text_color=self.colors.BRIGHT_GREEN if self.colors else None
            )
    
    async def start(self, context):
        """Run all SSL tests."""
        if not self._config.get("run_all_tests", True):
            if self.logger:
                self.logger.log("Tests disabled in config", tag="tester")
            return
        
        await self._run_all_tests()
    
    async def ready(self, context):
        """Display final results when all modules are ready."""
        if self._config.get("output_results", True) and self._test_results:
            await self._display_summary()
    
    async def stop(self, context):
        """Cleanup."""
        if self.logger:
            self.logger.log("SSLTester module stopped", tag="tester")
    
    # =========================================================================
    # Test Runner
    # =========================================================================
    
    async def _run_all_tests(self):
        """Run all SSL tests."""
        if self.logger:
            self._log_header("🔐 Starting SSL Tests")
        
        test_categories = self._config.get(
            "test_categories",
            ["cert_loading", "server_context", "client_context", "mtls", "cert_info", "validation", "integration"]
        )
        
        for category in test_categories:
            test_method = getattr(self, f"_test_{category}", None)
            if test_method:
                try:
                    result = await test_method()
                    self._test_results[category] = result
                except Exception as e:
                    self._test_results[category] = {
                        "passed": False,
                        "error": str(e)
                    }
                    if self.logger:
                        self.logger.print(
                            f"❌ Test {category} FAILED: {e}",
                            tag="tester",
                            level="ERROR"
                        )
    
    # =========================================================================
    # Certificate Loading Tests
    # =========================================================================
    
    async def _test_cert_loading(self) -> Dict:
        """Test certificate loading."""
        results = {"passed": True, "subtests": []}
        
        if self.logger:
            self._log_header("📜 Certificate Loading Tests")
        
        # Test 1: CA certificate exists
        try:
            ca_path = self._certs_dir / "ca.crt"
            assert ca_path.exists(), f"CA cert not found: {ca_path}"
            results["subtests"].append({"name": "ca_exists", "passed": True})
            self._log_success(f"CA certificate exists: {ca_path.name}")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "ca_exists", "passed": False, "error": str(e)})
            self._log_fail("CA exists", e)
        
        # Test 2: Server certificate exists
        try:
            server_cert = self._certs_dir / "server.crt"
            server_key = self._certs_dir / "server.key"
            assert server_cert.exists(), f"Server cert not found: {server_cert}"
            assert server_key.exists(), f"Server key not found: {server_key}"
            results["subtests"].append({"name": "server_exists", "passed": True})
            self._log_success("Server certificate and key exist")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "server_exists", "passed": False, "error": str(e)})
            self._log_fail("Server exists", e)
        
        # Test 3: Client certificate exists
        try:
            client_cert = self._certs_dir / "client.crt"
            client_key = self._certs_dir / "client.key"
            assert client_cert.exists(), f"Client cert not found: {client_cert}"
            assert client_key.exists(), f"Client key not found: {client_key}"
            results["subtests"].append({"name": "client_exists", "passed": True})
            self._log_success("Client certificate and key exist")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "client_exists", "passed": False, "error": str(e)})
            self._log_fail("Client exists", e)
        
        self._log_result("Certificate Loading", results["passed"])
        return results
    
    # =========================================================================
    # Server Context Tests
    # =========================================================================
    
    async def _test_server_context(self) -> Dict:
        """Test server SSL context creation."""
        results = {"passed": True, "subtests": []}
        
        if self.logger:
            self._log_header("🖥️ Server Context Tests")
        
        # Test 1: Create server context
        try:
            server_ctx = self.ssl_api.get_server_context("default")
            assert server_ctx is not None
            assert isinstance(server_ctx, ssl.SSLContext)
            
            # Check TLS version
            assert server_ctx.minimum_version >= ssl.TLSVersion.TLSv1_2
            
            results["subtests"].append({"name": "create_context", "passed": True})
            self._log_success("Server SSL context created successfully")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "create_context", "passed": False, "error": str(e)})
            self._log_fail("Create context", e)
        
        # Test 2: Context caching
        try:
            ctx1 = self.ssl_api.get_server_context("default")
            ctx2 = self.ssl_api.get_server_context("default")
            assert ctx1 is ctx2, "Contexts should be cached"
            
            results["subtests"].append({"name": "context_caching", "passed": True})
            self._log_success("Server context caching works")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "context_caching", "passed": False, "error": str(e)})
            self._log_fail("Context caching", e)
        
        self._log_result("Server Context", results["passed"])
        return results
    
    # =========================================================================
    # Client Context Tests
    # =========================================================================
    
    async def _test_client_context(self) -> Dict:
        """Test client SSL context creation."""
        results = {"passed": True, "subtests": []}
        
        if self.logger:
            self._log_header("👤 Client Context Tests")
        
        # Test 1: Create client context
        try:
            client_ctx = self.ssl_api.get_client_context("client")
            assert client_ctx is not None
            assert isinstance(client_ctx, ssl.SSLContext)
            
            results["subtests"].append({"name": "create_context", "passed": True})
            self._log_success("Client SSL context created successfully")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "create_context", "passed": False, "error": str(e)})
            self._log_fail("Create context", e)
        
        # Test 2: Client context with SNI
        try:
            client_ctx_sni = self.ssl_api.get_client_context(
                "client",
                sni_hostname="massir-server"
            )
            assert client_ctx_sni is not None
            
            results["subtests"].append({"name": "context_with_sni", "passed": True})
            self._log_success("Client context with SNI created")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "context_with_sni", "passed": False, "error": str(e)})
            self._log_fail("Context with SNI", e)
        
        self._log_result("Client Context", results["passed"])
        return results
    
    # =========================================================================
    # Certificate Info Tests
    # =========================================================================
    
    async def _test_cert_info(self) -> Dict:
        """Test certificate information extraction."""
        results = {"passed": True, "subtests": []}
        
        if self.logger:
            self._log_header("ℹ️ Certificate Info Tests")
        
        # Test 1: Get server cert info
        try:
            cert_info = self.ssl_api.get_cert_info("default")
            assert cert_info is not None
            assert cert_info.subject is not None
            assert cert_info.issuer is not None
            assert cert_info.days_until_expiry > 0
            assert not cert_info.is_expired
            
            results["subtests"].append({"name": "get_cert_info", "passed": True})
            self._log_success(f"Server cert info: {cert_info.subject}")
            self._log_success(f"  Issuer: {cert_info.issuer}")
            self._log_success(f"  Expires in: {cert_info.days_until_expiry} days")
            self._log_success(f"  Status: {cert_info.status}")
            
            if cert_info.san_dns_names:
                self._log_success(f"  SAN DNS: {', '.join(cert_info.san_dns_names)}")
            if cert_info.san_ip_addresses:
                self._log_success(f"  SAN IPs: {', '.join(cert_info.san_ip_addresses)}")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "get_cert_info", "passed": False, "error": str(e)})
            self._log_fail("Get cert info", e)
        
        # Test 2: Cert info to_dict
        try:
            cert_info = self.ssl_api.get_cert_info("default")
            info_dict = cert_info.to_dict()
            assert isinstance(info_dict, dict)
            assert "subject" in info_dict
            assert "days_until_expiry" in info_dict
            
            results["subtests"].append({"name": "cert_info_serialization", "passed": True})
            self._log_success("Cert info serialization works")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "cert_info_serialization", "passed": False, "error": str(e)})
            self._log_fail("Cert info serialization", e)
        
        self._log_result("Certificate Info", results["passed"])
        return results
    
    # =========================================================================
    # Validation Tests
    # =========================================================================
    
    async def _test_validation(self) -> Dict:
        """Test certificate validation."""
        results = {"passed": True, "subtests": []}
        
        if self.logger:
            self._log_header("✅ Validation Tests")
        
        # Test 1: Validate server certificate
        try:
            server_cert = self._certs_dir / "server.crt"
            validation = self.ssl_api.validate_certificate(server_cert)
            
            assert validation.is_valid, f"Validation errors: {validation.errors}"
            assert validation.cert_info is not None
            
            results["subtests"].append({"name": "validate_server_cert", "passed": True})
            self._log_success("Server certificate validation: PASSED")
            
            if validation.warnings:
                for warning in validation.warnings:
                    self.logger.print(f"  ⚠️ Warning: {warning}", tag="tester", level="WARNING")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "validate_server_cert", "passed": False, "error": str(e)})
            self._log_fail("Validate server cert", e)
        
        # Test 2: Validate CA certificate
        try:
            ca_cert = self._certs_dir / "ca.crt"
            validation = self.ssl_api.validate_certificate(ca_cert)
            
            assert validation.is_valid
            
            results["subtests"].append({"name": "validate_ca_cert", "passed": True})
            self._log_success("CA certificate validation: PASSED")
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "validate_ca_cert", "passed": False, "error": str(e)})
            self._log_fail("Validate CA cert", e)
        
        self._log_result("Validation", results["passed"])
        return results
    
    # =========================================================================
    # mTLS Tests
    # =========================================================================
    
    async def _test_mtls(self) -> Dict:
        """Test mutual TLS authentication."""
        results = {"passed": True, "subtests": []}
        
        if self.logger:
            self._log_header("🔒 mTLS Tests")
        
        # Test: Verify mTLS configuration
        try:
            # Get server context with client verification
            server_ctx = self.ssl_api.get_server_context("default")
            
            # Check if verify_mode is set for client certs
            # Note: verify_mode depends on config.verify_client_certs
            self._log_success(f"Server verify_mode: {server_ctx.verify_mode}")
            self._log_success(f"Client verification enabled in config: {self.ssl_api._config.get('verify_client_certs', False)}")
            
            # Get client context with certificate
            client_ctx = self.ssl_api.get_client_context("client")
            self._log_success("Client context loaded with certificate for mTLS")
            
            results["subtests"].append({"name": "mtls_config", "passed": True})
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "mtls_config", "passed": False, "error": str(e)})
            self._log_fail("mTLS config", e)
        
        self._log_result("mTLS", results["passed"])
        return results
    
    # =========================================================================
    # Integration Tests (Real TLS Connection)
    # =========================================================================
    
    async def _test_integration(self) -> Dict:
        """Test real TLS server/client connection."""
        results = {"passed": True, "subtests": []}
        
        if self.logger:
            self._log_header("🔗 Integration Tests (Real TLS Connection)")
        
        host = self._config.get("server_host", "127.0.0.1")
        port = self._config.get("server_port", 8443)
        
        # Test 1: Start TLS server and connect client
        try:
            server_ready = asyncio.Event()
            client_connected = asyncio.Event()
            received_data = []
            
            async def handle_client(reader, writer):
                try:
                    data = await reader.read(1024)
                    received_data.append(data)
                    writer.write(b"Hello from TLS server!")
                    await writer.drain()
                finally:
                    writer.close()
                    await writer.wait_closed()
            
            # Get contexts
            server_ctx = self.ssl_api.get_server_context("default")
            client_ctx = self.ssl_api.get_client_context("client")
            
            # Start server
            server = await asyncio.start_server(
                handle_client,
                host, port,
                ssl=server_ctx
            )
            
            async with server:
                server_ready.set()
                
                # Give server time to start
                await asyncio.sleep(0.1)
                
                # Connect client
                reader, writer = await asyncio.open_connection(
                    host, port,
                    ssl=client_ctx,
                    server_hostname="localhost"
                )
                
                client_connected.set()
                
                # Send data
                writer.write(b"Hello from TLS client!")
                await writer.drain()
                
                # Receive response
                response = await reader.read(1024)
                
                writer.close()
                await writer.wait_closed()
            
            # Verify
            assert client_connected.is_set(), "Client should have connected"
            assert len(received_data) > 0, "Server should have received data"
            assert received_data[0] == b"Hello from TLS client!", "Data mismatch"
            assert response == b"Hello from TLS server!", "Response mismatch"
            
            results["subtests"].append({"name": "tls_connection", "passed": True})
            self._log_success(f"TLS connection established on {host}:{port}")
            self._log_success(f"  Client sent: {received_data[0].decode()}")
            self._log_success(f"  Server replied: {response.decode()}")
            
        except Exception as e:
            results["passed"] = False
            results["subtests"].append({"name": "tls_connection", "passed": False, "error": str(e)})
            self._log_fail("TLS connection", e)
        
        self._log_result("Integration", results["passed"])
        return results
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _log_header(self, message: str):
        """Log a section header."""
        if self.logger:
            self.logger.print("", tag="tester")
            self.logger.print("=" * 60, tag="tester")
            self.logger.print(message, tag="tester", color=self.colors.BRIGHT_CYAN if self.colors else None)
            self.logger.print("=" * 60, tag="tester")
    
    def _log_success(self, message: str):
        """Log a success message."""
        if self.logger:
            self.logger.print(
                f"✅ {message}",
                tag="tester",
                color=self.colors.BRIGHT_GREEN if self.colors else None
            )
    
    def _log_fail(self, test_name: str, error: Exception):
        """Log a failure message."""
        if self.logger:
            self.logger.print(
                f"❌ {test_name} FAILED: {error}",
                tag="tester",
                level="ERROR"
            )
    
    def _log_result(self, category: str, passed: bool):
        """Log final result for a category."""
        if self.logger:
            status = "PASSED ✅" if passed else "FAILED ❌"
            color = self.colors.BRIGHT_GREEN if passed else self.colors.BRIGHT_RED
            self.logger.print(
                f"\n{'='*30}\n{category}: {status}\n{'='*30}",
                tag="tester",
                color=color if self.colors else None
            )
    
    async def _display_summary(self):
        """Display summary of all tests."""
        if self.logger:
            self.logger.print("", tag="tester")
            self.logger.print("=" * 60, tag="tester")
            
            total = len(self._test_results)
            passed = sum(1 for r in self._test_results.values() if r.get("passed", False))
            failed = total - passed
            
            self.logger.print(
                f"📊 Test Summary: {passed}/{total} categories passed",
                tag="tester",
                color=self.colors.BRIGHT_YELLOW if self.colors else None
            )
            
            for category, result in self._test_results.items():
                status = "✅ PASSED" if result.get("passed") else "❌ FAILED"
                subtests = result.get("subtests", [])
                sub_passed = sum(1 for s in subtests if s.get("passed", False))
                self.logger.print(
                    f"  {category}: {status} ({sub_passed}/{len(subtests)} subtests)",
                    tag="tester"
                )
            
            if failed == 0:
                self.logger.print(
                    "\n🎉 All SSL tests completed successfully!",
                    tag="tester",
                    color=self.colors.BRIGHT_GREEN if self.colors else None
                )
            else:
                self.logger.print(
                    f"\n⚠️ {failed} test category(ies) failed. Check logs above.",
                    tag="tester",
                    level="WARNING"
                )
            
            self.logger.print("=" * 60, tag="tester")