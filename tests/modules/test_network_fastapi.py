"""
Unit tests for network_fastapi module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from massir.modules.network_fastapi.module import NetworkFastAPIModule
from massir.modules.network_fastapi.api.http import HTTPAPI, HTTPResponse
from massir.modules.network_fastapi.api.net import NetAPI, NetworkInfo, PortInfo
from massir.modules.network_fastapi.api.router import RouterAPI
from massir.modules.network_fastapi.api.server import ServerAPI, ServerConfig, ServerStatus, UvicornLogHandler
from massir.core.interfaces import ModuleContext


class TestHTTPResponse:
    """Tests for HTTPResponse dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        response = HTTPResponse()
        assert response.status_code == 200
        assert response.data is None
        assert response.headers is None
    
    def test_custom_values(self):
        """Test custom values."""
        response = HTTPResponse(
            status_code=201,
            data={"message": "created"},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 201
        assert response.data == {"message": "created"}
        assert response.headers["Content-Type"] == "application/json"
    
    def test_to_dict(self):
        """Test to_dict method."""
        response = HTTPResponse(
            status_code=200,
            data={"key": "value"},
            headers={"X-Custom": "header"}
        )
        result = response.to_dict()
        
        assert result["status_code"] == 200
        assert result["data"] == {"key": "value"}
        assert result["headers"]["X-Custom"] == "header"


class TestHTTPAPI:
    """Tests for HTTPAPI class."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app."""
        app = Mock()
        app.get = Mock(return_value=lambda f: f)
        app.post = Mock(return_value=lambda f: f)
        app.put = Mock(return_value=lambda f: f)
        app.delete = Mock(return_value=lambda f: f)
        app.patch = Mock(return_value=lambda f: f)
        app.head = Mock(return_value=lambda f: f)
        app.options = Mock(return_value=lambda f: f)
        app.trace = Mock(return_value=lambda f: f)
        app.websocket = Mock(return_value=lambda f: f)
        app.include_router = Mock()
        app.add_middleware = Mock()
        app.on_event = Mock(return_value=lambda f: f)
        return app
    
    @pytest.fixture
    def http_api(self, mock_app):
        """Create HTTPAPI instance."""
        return HTTPAPI(mock_app)
    
    def test_init(self, http_api, mock_app):
        """Test initialization."""
        assert http_api._app == mock_app
    
    def test_get_decorator(self, http_api, mock_app):
        """Test GET decorator."""
        @http_api.get("/test")
        async def test_route():
            return {"status": "ok"}
        
        mock_app.get.assert_called_once_with("/test")
    
    def test_post_decorator(self, http_api, mock_app):
        """Test POST decorator."""
        @http_api.post("/test")
        async def test_route():
            return {"status": "ok"}
        
        mock_app.post.assert_called_once_with("/test")
    
    def test_put_decorator(self, http_api, mock_app):
        """Test PUT decorator."""
        @http_api.put("/test")
        async def test_route():
            return {"status": "ok"}
        
        mock_app.put.assert_called_once_with("/test")
    
    def test_delete_decorator(self, http_api, mock_app):
        """Test DELETE decorator."""
        @http_api.delete("/test")
        async def test_route():
            return {"status": "ok"}
        
        mock_app.delete.assert_called_once_with("/test")
    
    def test_patch_decorator(self, http_api, mock_app):
        """Test PATCH decorator."""
        @http_api.patch("/test")
        async def test_route():
            return {"status": "ok"}
        
        mock_app.patch.assert_called_once_with("/test")
    
    def test_response_method(self, http_api):
        """Test response method."""
        response = http_api.response(
            data={"message": "success"},
            status_code=201,
            headers={"X-Custom": "value"}
        )
        
        assert isinstance(response, HTTPResponse)
        assert response.status_code == 201
        assert response.data == {"message": "success"}
    
    def test_error_method(self, http_api):
        """Test error method."""
        response = http_api.error(
            message="Not found",
            status_code=404,
            code="NOT_FOUND",
            details={"resource": "user"}
        )
        
        assert response.status_code == 404
        assert response.data["error"] == True
        assert response.data["message"] == "Not found"
        assert response.data["code"] == "NOT_FOUND"
        assert response.data["details"] == {"resource": "user"}
    
    def test_error_method_minimal(self, http_api):
        """Test error method with minimal args."""
        response = http_api.error("Bad request")
        
        assert response.status_code == 400
        assert response.data["error"] == True
        assert response.data["message"] == "Bad request"
        assert "code" not in response.data
    
    def test_app_property(self, http_api, mock_app):
        """Test app property."""
        assert http_api.app == mock_app
    
    def test_exposed_types(self, http_api):
        """Test exposed FastAPI types."""
        assert hasattr(HTTPAPI, 'Request')
        assert hasattr(HTTPAPI, 'HTMLResponse')
        assert hasattr(HTTPAPI, 'JSONResponse')
        assert hasattr(HTTPAPI, 'RedirectResponse')
        assert hasattr(HTTPAPI, 'PlainTextResponse')
        assert hasattr(HTTPAPI, 'StaticFiles')


class TestNetAPI:
    """Tests for NetAPI class."""
    
    @pytest.fixture
    def net_api(self):
        """Create NetAPI instance."""
        return NetAPI()
    
    def test_get_hostname(self, net_api):
        """Test get_hostname returns a string."""
        hostname = net_api.get_hostname()
        
        assert isinstance(hostname, str)
        assert len(hostname) > 0
    
    def test_get_hostname_caches(self, net_api):
        """Test get_hostname caches result."""
        h1 = net_api.get_hostname()
        h2 = net_api.get_hostname()
        
        assert h1 == h2
    
    def test_get_ip_address(self, net_api):
        """Test get_ip_address returns valid IP."""
        ip = net_api.get_ip_address()
        
        # Should be a valid IP address format
        parts = ip.split(".")
        assert len(parts) == 4
        assert all(part.isdigit() for part in parts)
    
    def test_is_ipv4_valid(self, net_api):
        """Test is_ipv4 with valid IPv4."""
        assert net_api.is_ipv4("192.168.1.1") == True
        assert net_api.is_ipv4("127.0.0.1") == True
        assert net_api.is_ipv4("10.0.0.1") == True
    
    def test_is_ipv4_invalid(self, net_api):
        """Test is_ipv4 with invalid IPv4."""
        assert net_api.is_ipv4("256.1.1.1") == False
        assert net_api.is_ipv4("::1") == False
        assert net_api.is_ipv4("not_an_ip") == False
    
    def test_is_ipv6_valid(self, net_api):
        """Test is_ipv6 with valid IPv6."""
        assert net_api.is_ipv6("::1") == True
        assert net_api.is_ipv6("2001:db8::1") == True
    
    def test_is_ipv6_invalid(self, net_api):
        """Test is_ipv6 with invalid IPv6."""
        assert net_api.is_ipv6("192.168.1.1") == False
        assert net_api.is_ipv6("not_an_ip") == False
    
    def test_is_valid_ip(self, net_api):
        """Test is_valid_ip."""
        assert net_api.is_valid_ip("192.168.1.1") == True
        assert net_api.is_valid_ip("::1") == True
        assert net_api.is_valid_ip("invalid") == False
    
    def test_is_port_available(self, net_api):
        """Test is_port_available."""
        # Port 0 should always be available (OS assigns)
        result = net_api.is_port_available(0)
        assert isinstance(result, bool)
    
    def test_find_available_port(self, net_api):
        """Test find_available_port."""
        port = net_api.find_available_port(start_port=50000, end_port=50100)
        
        if port is not None:
            assert 50000 <= port <= 50100
    
    def test_get_network_info(self, net_api):
        """Test get_network_info."""
        info = net_api.get_network_info(port=8000)
        
        assert isinstance(info, NetworkInfo)
        assert info.port == 8000
        assert isinstance(info.hostname, str)
        assert isinstance(info.ip_address, str)
        assert isinstance(info.is_ipv6, bool)
    
    def test_parse_url(self, net_api):
        """Test parse_url."""
        result = net_api.parse_url("https://user:pass@example.com:8080/path?query=1#fragment")
        
        assert result["scheme"] == "https"
        assert result["hostname"] == "example.com"
        assert result["port"] == 8080
        assert result["path"] == "/path"
        assert result["query"] == "query=1"
        assert result["fragment"] == "fragment"
        assert result["username"] == "user"
        assert result["password"] == "pass"
    
    def test_build_url(self, net_api):
        """Test build_url."""
        url = net_api.build_url(
            scheme="https",
            host="example.com",
            port=8080,
            path="/api",
            query="key=value"
        )
        
        assert url == "https://example.com:8080/api?key=value"
    
    def test_build_url_minimal(self, net_api):
        """Test build_url with minimal args."""
        url = net_api.build_url(scheme="http", host="localhost")
        
        assert url == "http://localhost"
    
    def test_get_local_networks(self, net_api):
        """Test get_local_networks."""
        networks = net_api.get_local_networks()
        
        assert isinstance(networks, list)
        assert len(networks) > 0


class TestNetAPIAsync:
    """Async tests for NetAPI class."""
    
    @pytest.fixture
    def net_api(self):
        """Create NetAPI instance."""
        return NetAPI()
    
    @pytest.mark.asyncio
    async def test_check_port_closed(self, net_api):
        """Test check_port with closed port."""
        # Port 1 is typically closed
        result = await net_api.check_port("127.0.0.1", 1, timeout=0.1)
        
        assert isinstance(result, PortInfo)
        assert result.port == 1
        assert result.is_open == False
    
    @pytest.mark.asyncio
    async def test_check_ports_multiple(self, net_api):
        """Test check_ports with multiple ports."""
        results = await net_api.check_ports("127.0.0.1", [1, 2, 3], timeout=0.1)
        
        assert len(results) == 3
        assert all(isinstance(r, PortInfo) for r in results)


class TestRouterAPI:
    """Tests for RouterAPI class."""
    
    @pytest.fixture
    def router_api(self):
        """Create RouterAPI instance."""
        return RouterAPI()
    
    def test_init(self, router_api):
        """Test initialization."""
        assert router_api._routers == []
    
    def test_create_router(self, router_api):
        """Test create router."""
        router = router_api.create(prefix="/api", tags=["test"])
        
        assert router is not None
        assert router in router_api._routers
    
    def test_create_router_with_options(self, router_api):
        """Test create router with all options."""
        router = router_api.create(
            prefix="/v1",
            tags=["api"],
            responses={404: {"description": "Not found"}}
        )
        
        assert router is not None
    
    def test_get_all(self, router_api):
        """Test get_all returns all routers."""
        router_api.create(prefix="/api1")
        router_api.create(prefix="/api2")
        
        routers = router_api.get_all()
        
        assert len(routers) == 2
    
    def test_clear(self, router_api):
        """Test clear removes all routers."""
        router_api.create(prefix="/api1")
        router_api.create(prefix="/api2")
        
        router_api.clear()
        
        assert len(router_api._routers) == 0
    
    def test_include(self, router_api):
        """Test include router in app."""
        router = router_api.create(prefix="/api")
        mock_app = Mock()
        mock_app.include_router = Mock()
        
        router_api.include(router, mock_app, prefix="/v1")
        
        mock_app.include_router.assert_called_once()


class TestServerConfig:
    """Tests for ServerConfig dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        config = ServerConfig()
        
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.reload == False
        assert config.workers == 1
        assert config.log_level == "info"
        assert config.access_log == True
    
    def test_custom_values(self):
        """Test custom values."""
        config = ServerConfig(
            host="0.0.0.0",
            port=3000,
            reload=True,
            workers=4,
            log_level="debug",
            access_log=False
        )
        
        assert config.host == "0.0.0.0"
        assert config.port == 3000
        assert config.reload == True
        assert config.workers == 4
        assert config.log_level == "debug"
        assert config.access_log == False


class TestServerStatus:
    """Tests for ServerStatus dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        status = ServerStatus()
        
        assert status.is_running == False
        assert status.host == ""
        assert status.port == 0
        assert status.url == ""
    
    def test_custom_values(self):
        """Test custom values."""
        status = ServerStatus(
            is_running=True,
            host="localhost",
            port=8000,
            url="http://localhost:8000"
        )
        
        assert status.is_running == True
        assert status.host == "localhost"
        assert status.port == 8000
        assert status.url == "http://localhost:8000"


class TestUvicornLogHandler:
    """Tests for UvicornLogHandler class."""
    
    def test_init(self):
        """Test initialization."""
        callback = Mock()
        handler = UvicornLogHandler(callback)
        
        assert handler.log_callback == callback
    
    def test_emit_calls_callback(self):
        """Test emit calls callback."""
        callback = Mock()
        handler = UvicornLogHandler(callback)
        
        import logging
        record = logging.LogRecord(
            name="uvicorn",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        callback.assert_called_once()
    
    def test_emit_suppresses_cancelled_error(self):
        """Test emit suppresses CancelledError."""
        callback = Mock()
        handler = UvicornLogHandler(callback)
        
        import logging
        record = logging.LogRecord(
            name="uvicorn",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Some CancelledError traceback",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        callback.assert_not_called()


class TestServerAPI:
    """Tests for ServerAPI class."""
    
    @pytest.fixture
    def mock_app(self):
        """Create a mock FastAPI app."""
        return Mock()
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config API."""
        config = Mock()
        config.get = Mock(return_value=None)
        return config
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger API."""
        return Mock()
    
    @pytest.fixture
    def server_api(self, mock_app, mock_config, mock_logger):
        """Create ServerAPI instance."""
        return ServerAPI(mock_app, mock_config, mock_logger)
    
    def test_init(self, server_api, mock_app):
        """Test initialization."""
        assert server_api._app == mock_app
        assert server_api._server is None
        assert server_api._status.is_running == False
    
    def test_create_config_defaults(self, server_api, mock_config):
        """Test create_config with defaults."""
        # Setup mock to return default values
        def mock_get(key, default=None):
            return default
        
        mock_config.get = mock_get
        server_api._config_api = mock_config
        
        config = server_api.create_config()
        
        assert isinstance(config, ServerConfig)
        assert config.host == "127.0.0.1"
        assert config.port == 8000
    
    def test_create_config_custom(self, server_api):
        """Test create_config with custom values."""
        config = server_api.create_config(
            host="0.0.0.0",
            port=3000,
            reload=True
        )
        
        assert config.host == "0.0.0.0"
        assert config.port == 3000
        assert config.reload == True
    
    def test_create_config_from_config_api(self, mock_app, mock_logger):
        """Test create_config reads from config_api."""
        mock_config = Mock()
        mock_config.get = Mock(side_effect=lambda k, d: {
            "fastapi_provider.web.host": "0.0.0.0",
            "fastapi_provider.web.port": 9000,
        }.get(k, d))
        
        server_api = ServerAPI(mock_app, mock_config, mock_logger)
        config = server_api.create_config()
        
        assert config.host == "0.0.0.0"
        assert config.port == 9000
    
    def test_status_property(self, server_api):
        """Test status property."""
        status = server_api.status
        
        assert isinstance(status, ServerStatus)
        assert status.is_running == False
    
    def test_is_running_property(self, server_api):
        """Test is_running property."""
        assert server_api.is_running == False
    
    def test_get_url_not_running(self, server_api):
        """Test get_url when not running."""
        url = server_api.get_url("/api")
        
        assert url == ""
    
    def test_get_docs_url_not_running(self, server_api):
        """Test get_docs_url when not running."""
        url = server_api.get_docs_url()
        
        assert url == ""
    
    def test_get_openapi_url_not_running(self, server_api):
        """Test get_openapi_url when not running."""
        url = server_api.get_openapi_url()
        
        assert url == ""
    
    def test_get_server_runner(self, server_api):
        """Test get_server_runner."""
        config = ServerConfig(host="localhost", port=8000)
        runner = server_api.get_server_runner(config)
        
        assert callable(runner)
        assert server_api._status.is_running == True
        assert server_api._status.host == "localhost"
        assert server_api._status.port == 8000
    
    @pytest.mark.asyncio
    async def test_stop_server(self, server_api):
        """Test stop_server."""
        # First set up a server
        config = ServerConfig()
        server_api.get_server_runner(config)
        
        await server_api.stop_server()
        
        assert server_api._server is None
        assert server_api._status.is_running == False


class TestNetworkFastAPIModule:
    """Tests for NetworkFastAPIModule class."""
    
    @pytest.fixture
    def module(self):
        """Create a NetworkFastAPIModule instance."""
        return NetworkFastAPIModule()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock module context."""
        context = ModuleContext()
        
        # Mock app
        mock_app = Mock()
        mock_app.register_hook = Mock()
        context._app = mock_app
        
        # Mock services
        mock_config = Mock()
        mock_config.get = Mock(return_value=None)
        mock_config.show_logs = Mock(return_value=True)
        mock_config.is_debug = Mock(return_value=True)
        mock_config.get_hide_log_levels = Mock(return_value=[])
        mock_config.get_hide_log_tags = Mock(return_value=[])
        
        mock_logger = Mock()
        
        context.services.set("core_config", mock_config)
        context.services.set("core_logger", mock_logger)
        
        return context
    
    def test_module_has_name(self, module):
        """Test module has name attribute."""
        assert module.name == "network_fastapi"
    
    def test_module_provides(self, module):
        """Test module provides list."""
        assert "http_api" in module.provides
        assert "router_api" in module.provides
        assert "net_api" in module.provides
        assert "server_api" in module.provides
    
    @pytest.mark.asyncio
    async def test_module_load_creates_services(self, module, mock_context):
        """Test module load creates services."""
        await module.load(mock_context)
        
        assert mock_context.services.get("http_api") is not None
        assert mock_context.services.get("router_api") is not None
        assert mock_context.services.get("net_api") is not None
        assert mock_context.services.get("server_api") is not None
    
    @pytest.mark.asyncio
    async def test_module_load_creates_fastapi_app(self, module, mock_context):
        """Test module load creates FastAPI app."""
        await module.load(mock_context)
        
        assert module.app is not None
    
    @pytest.mark.asyncio
    async def test_module_start_does_not_raise(self, module, mock_context):
        """Test module start doesn't raise."""
        await module.load(mock_context)
        await module.start(mock_context)
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_module_stop_does_not_raise(self, module, mock_context):
        """Test module stop doesn't raise."""
        await module.load(mock_context)
        await module.stop(mock_context)
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_module_full_lifecycle(self, module, mock_context):
        """Test full module lifecycle."""
        await module.load(mock_context)
        await module.start(mock_context)
        await module.stop(mock_context)
        
        # Services should still be available
        assert mock_context.services.get("http_api") is not None
