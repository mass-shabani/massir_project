"""
Server API for managing HTTP server lifecycle.

This module provides server management utilities without directly
starting the server, allowing consuming modules to control when
and how the server starts.
"""
import asyncio
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass
import uvicorn


@dataclass
class ServerConfig:
    """Server configuration."""
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: str = "info"
    access_log: bool = True


@dataclass
class ServerStatus:
    """Server status information."""
    is_running: bool = False
    host: str = ""
    port: int = 0
    url: str = ""


class UvicornLogHandler(logging.Handler):
    """
    Custom log handler that forwards uvicorn logs to a callback.
    """
    
    def __init__(self, log_callback: Callable[[str, str, Optional[str]], None]):
        super().__init__()
        self.log_callback = log_callback
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record through the callback."""
        if not self.log_callback:
            return
        
        message = self.format(record)
        
        # Suppress CancelledError traceback during shutdown (normal behavior)
        if "CancelledError" in message:
            return
        
        # Map logging levels
        level_map = {
            logging.DEBUG: "DEBUG",
            logging.INFO: "INFO",
            logging.WARNING: "WARNING",
            logging.ERROR: "ERROR",
            logging.CRITICAL: "CRITICAL"
        }
        level = level_map.get(record.levelno, "INFO")
        
        # Determine tag based on logger name
        if "access" in record.name:
            tag = "http"
        else:
            tag = "server_Uvicorn"
        
        self.log_callback(message, level, tag)


class ServerAPI:
    """
    Server management API.
    
    Provides utilities for creating and managing HTTP servers
    without directly starting them. The consuming module decides
    when to start the server.
    """
    
    _logging_setup = False  # Class-level flag to prevent duplicate setup
    
    def __init__(self, fastapi_app, config_api=None, logger_api=None):
        """
        Initialize Server API.
        
        Args:
            fastapi_app: FastAPI application instance
            config_api: Configuration API for settings
            logger_api: Logger API for logging
        """
        self._app = fastapi_app
        self._config_api = config_api
        self._logger_api = logger_api
        self._server: Optional[uvicorn.Server] = None
        self._status = ServerStatus()
    
    def create_config(self, 
                     host: str = None,
                     port: int = None,
                     reload: bool = None,
                     workers: int = None,
                     log_level: str = None,
                     access_log: bool = None) -> ServerConfig:
        """
        Create a server configuration.
        
        Uses provided values or falls back to config_api settings.
        
        Args:
            host: Server host
            port: Server port
            reload: Enable auto-reload
            workers: Number of workers
            log_level: Log level
            access_log: Enable access log
        
        Returns:
            ServerConfig object
        """
        # Get from config_api if not provided
        if self._config_api:
            config_host = host or self._config_api.get("fastapi_provider.web.host", "127.0.0.1")
            config_port = port or self._config_api.get("fastapi_provider.web.port", 8000)
            config_reload = reload if reload is not None else self._config_api.get("fastapi_provider.web.reload", False)
            config_workers = workers or self._config_api.get("fastapi_provider.web.workers", 1)
            config_log_level = log_level or self._config_api.get("fastapi_provider.web.log_level", "info")
            config_access_log = access_log if access_log is not None else self._config_api.get("fastapi_provider.web.access_log", True)
        else:
            config_host = host or "127.0.0.1"
            config_port = port or 8000
            config_reload = reload if reload is not None else False
            config_workers = workers or 1
            config_log_level = log_level or "info"
            config_access_log = access_log if access_log is not None else True
        
        return ServerConfig(
            host=config_host,
            port=config_port,
            reload=config_reload,
            workers=config_workers,
            log_level=config_log_level,
            access_log=config_access_log
        )
    
    def create_server(self, config: ServerConfig) -> uvicorn.Server:
        """
        Create a uvicorn server instance.
        
        Does NOT start the server. The caller is responsible for starting it.
        
        Args:
            config: Server configuration
        
        Returns:
            Uvicorn Server instance (not started)
        """
        # Setup logging if logger_api is available
        log_config = None
        if self._logger_api:
            self._setup_logging()
            log_config = None  # We handle logging ourselves
        
        uvicorn_config = uvicorn.Config(
            app=self._app,
            host=config.host,
            port=config.port,
            reload=config.reload,
            workers=config.workers,
            log_level=config.log_level,
            access_log=config.access_log,
            log_config=log_config
        )
        
        server = uvicorn.Server(uvicorn_config)
        return server
    
    def _setup_logging(self):
        """Setup uvicorn logging to use Massir logger."""
        if not self._logger_api:
            return
        
        # Only setup once at class level
        if ServerAPI._logging_setup:
            return
        
        ServerAPI._logging_setup = True
        
        def log_callback(message: str, level: str, tag: Optional[str] = None):
            self._logger_api.log(message, level=level, tag=tag)
        
        handler = UvicornLogHandler(log_callback)
        
        # Configure uvicorn loggers
        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
    
    def get_server_runner(self, config: ServerConfig) -> Callable[[], Any]:
        """
        Get a callable that runs the server.
        
        This is useful for registering as a background task.
        
        Args:
            config: Server configuration
        
        Returns:
            Callable that runs the server (can be used with register_background_task)
        
        Usage:
            config = server_api.create_config(port=8000)
            runner = server_api.get_server_runner(config)
            app.register_background_task(runner)
        """
        server = self.create_server(config)
        self._server = server
        self._status = ServerStatus(
            is_running=True,
            host=config.host,
            port=config.port,
            url=f"http://{config.host}:{config.port}"
        )
        return server.serve
    
    async def start_server(self, config: ServerConfig) -> uvicorn.Server:
        """
        Start the server and return the server instance.
        
        This is a convenience method for starting the server directly.
        For background task usage, use get_server_runner() instead.
        
        Args:
            config: Server configuration
        
        Returns:
            Running Uvicorn Server instance
        """
        server = self.create_server(config)
        self._server = server
        self._status = ServerStatus(
            is_running=True,
            host=config.host,
            port=config.port,
            url=f"http://{config.host}:{config.port}"
        )
        
        # Start server in background
        asyncio.create_task(server.serve())
        
        return server
    
    async def stop_server(self):
        """
        Stop the server gracefully.
        """
        if self._server:
            # Signal the server to exit
            self._server.should_exit = True
            
            # Give the server a moment to complete its own shutdown
            # uvicorn's serve() handles shutdown internally when should_exit is True
            for _ in range(10):  # Wait up to 1 second
                if self._server is None or not hasattr(self._server, 'servers'):
                    break
                await asyncio.sleep(0.1)
            
            self._server = None
            self._status = ServerStatus(is_running=False)
    
    @property
    def status(self) -> ServerStatus:
        """
        Get current server status.
        
        Returns:
            ServerStatus object
        """
        return self._status
    
    @property
    def is_running(self) -> bool:
        """
        Check if server is running.
        
        Returns:
            True if server is running
        """
        return self._status.is_running
    
    def get_url(self, path: str = "") -> str:
        """
        Get the server URL with optional path.
        
        Args:
            path: URL path to append
        
        Returns:
            Complete URL string
        """
        if not self._status.is_running:
            return ""
        return f"{self._status.url}{path}"
    
    def get_docs_url(self) -> str:
        """
        Get the API documentation URL.
        
        Returns:
            Docs URL string
        """
        return self.get_url("/docs")
    
    def get_openapi_url(self) -> str:
        """
        Get the OpenAPI JSON URL.
        
        Returns:
            OpenAPI URL string
        """
        return self.get_url("/openapi.json")
