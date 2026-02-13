"""
Network FastAPI Module - High-performance network provider.

This module provides HTTP, router, and network APIs using FastAPI.
"""
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from massir.core.interfaces import IModule
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from .api.http import HTTPAPI
from .api.router import RouterAPI
from .api.net import NetAPI


class UvicornLogHandler(logging.Handler):
    """
    Custom log handler that forwards uvicorn logs to the Massir logger.
    """
    
    def __init__(self, logger_api: CoreLoggerAPI):
        super().__init__()
        self.logger_api = logger_api
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record through the Massir logger."""
        if not self.logger_api:
            return
        
        message = self.format(record)
        
        # Map logging levels to Massir levels
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
            tag = "server"
        
        self.logger_api.log(message, level=level, tag=tag)


class NetworkFastAPIModule(IModule):
    """
    Network provider module using FastAPI.
    
    Provides high-performance HTTP, router, and network APIs
    without requiring FastAPI imports in consuming modules.
    """
    
    name = "network_fastapi"
    provides = ["http_api", "router_api", "net_api"]
    
    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.server: Optional[uvicorn.Server] = None
        self.http_api: Optional[HTTPAPI] = None
        self.router_api: Optional[RouterAPI] = None
        self.net_api: Optional[NetAPI] = None
        self.config_api: Optional[CoreConfigAPI] = None
        self.logger_api: Optional[CoreLoggerAPI] = None
    
    async def load(self, context):
        """
        Initialize FastAPI application and APIs.
        
        Sets up the FastAPI app with middleware and default routes.
        """
        self.logger_api = context.services.get("core_logger")
        self.config_api = context.services.get("core_config")
        
        # Create FastAPI app with optimized settings
        self.app = FastAPI(
            title=self.config_api.get("fastapi_provider.title", "Massir API"),
            version=self.config_api.get("fastapi_provider.version", "1.0.0"),
            description=self.config_api.get("fastapi_provider.description", "Modular API"),
            docs_url=self.config_api.get("fastapi_provider.docs_url", "/docs"),
            redoc_url=self.config_api.get("fastapi_provider.redoc_url", "/redoc"),
            openapi_url=self.config_api.get("fastapi_provider.openapi_url", "/openapi.json")
        )
        
        # Create API abstractions
        self.http_api = HTTPAPI(self.app)
        self.router_api = RouterAPI()
        self.net_api = NetAPI(self.config_api)
        
        # Setup middleware
        self._setup_middleware()
        
        # Setup default routes
        self._setup_default_routes()
        
        # Setup exception handlers
        self._setup_exception_handlers()
        
        # Register services
        context.services.set("http_api", self.http_api)
        context.services.set("router_api", self.router_api)
        context.services.set("net_api", self.net_api)
        
        if self.logger_api:
            self.logger_api.log("NetworkFastAPI module loaded", tag="network")
    
    def _setup_middleware(self):
        """Setup middleware for FastAPI app."""
        # Trusted Host middleware
        trusted_hosts = self.config_api.get("fastapi_provider.trusted_hosts", ["*"])
        if trusted_hosts != ["*"]:
            self.app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
        
        # CORS middleware
        cors_origins = self.config_api.get("fastapi_provider.cors.origins", ["*"])
        cors_credentials = self.config_api.get("fastapi_provider.cors.credentials", True)
        cors_methods = self.config_api.get("fastapi_provider.cors.methods", ["*"])
        cors_headers = self.config_api.get("fastapi_provider.cors.headers", ["*"])
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=cors_credentials,
            allow_methods=cors_methods,
            allow_headers=cors_headers
        )
        
        # GZip middleware
        gzip_enabled = self.config_api.get("fastapi_provider.gzip.enabled", True)
        gzip_min_size = self.config_api.get("fastapi_provider.gzip.minimum_size", 1000)
        if gzip_enabled:
            self.app.add_middleware(GZipMiddleware, minimum_size=gzip_min_size)
    
    def _setup_default_routes(self):
        """Setup default health and info routes."""
        
        @self.http_api.get("/health", tags=["system"], summary="Health check endpoint")
        async def health_check():
            """Check if the service is healthy."""
            return {
                "status": "healthy",
                "service": "network_fastapi",
                "version": "1.0.0"
            }
        
        @self.http_api.get("/info", tags=["system"], summary="Service information")
        async def info():
            """Get service information."""
            return {
                "name": "network_fastapi",
                "version": "1.0.0",
                "framework": "Massir",
                "hostname": self.net_api.get_hostname(),
                "ip_address": self.net_api.get_ip_address()
            }
        
        @self.http_api.get("/network", tags=["system"], summary="Network information")
        async def network_info():
            """Get network information."""
            return self.net_api.get_network_info()
    
    def _setup_exception_handlers(self):
        """Setup global exception handlers."""
        
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            """Handle all unhandled exceptions."""
            if self.logger_api:
                self.logger_api.log(
                    f"Unhandled exception: {exc}",
                    level="ERROR",
                    tag="network"
                )
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "message": "Internal server error",
                    "detail": str(exc) if self.config_api.get("fastapi_provider.debug", False) else None
                }
            )
        
        @self.app.exception_handler(404)
        async def not_found_handler(request: Request, exc):
            """Handle 404 errors."""
            return JSONResponse(
                status_code=404,
                content={
                    "error": True,
                    "message": "Resource not found",
                    "path": request.url.path
                }
            )
    
    async def start(self, context):
        """
        Start the FastAPI server.
        
        Registers the server as a background task.
        """
        if self.logger_api:
            self.logger_api.log("Starting FastAPI server...", tag="network")
        
        # Get server configuration
        host = self.config_api.get("fastapi_provider.web.host", "127.0.0.1")
        port = self.config_api.get("fastapi_provider.web.port", 8000)
        reload = self.config_api.get("fastapi_provider.web.reload", False)
        workers = self.config_api.get("fastapi_provider.web.workers", 1)
        log_level = self.config_api.get("fastapi_provider.web.log_level", "info")
        
        # Check if port is available
        if not self.net_api.is_port_available(port, host):
            if self.logger_api:
                self.logger_api.log(
                    f"Port {port} is already in use on {host}",
                    level="ERROR",
                    tag="network"
                )
            # Try to find an available port
            available_port = self.net_api.find_available_port(port, port + 100, host)
            if available_port:
                port = available_port
                if self.logger_api:
                    self.logger_api.log(
                        f"Using available port: {port}",
                        level="WARNING",
                        tag="network"
                    )
            else:
                raise RuntimeError(f"No available ports in range {port}-{port + 100}")
        
        # Setup uvicorn logging to use Massir logger
        self._setup_uvicorn_logging()
        
        # Create uvicorn config with custom logging
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            log_level=log_level,
            access_log=True,
            log_config=None
        )
        
        self.server = uvicorn.Server(config)
        
        # Register as background task
        app = context.get_app()
        app.register_background_task(self.server.serve)
        
        if self.logger_api:
            self.logger_api.log(
                f"FastAPI server started on http://{host}:{port}",
                tag="network"
            )
            self.logger_api.log(
                f"API documentation available at http://{host}:{port}/docs",
                tag="network"
            )
    
    def _setup_uvicorn_logging(self):
        """Setup uvicorn logging to use Massir logger."""
        if not self.logger_api:
            return
        
        # Create custom handler
        handler = UvicornLogHandler(self.logger_api)
        
        # Configure uvicorn loggers
        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
    
    async def stop(self, context):
        """
        Stop the FastAPI server.
        
        Gracefully shuts down the server.
        """
        if self.server:
            if self.logger_api:
                self.logger_api.log("Stopping FastAPI server...", tag="network")
            
            self.server.should_exit = True
            
            try:
                await self.server.shutdown()
            except Exception as e:
                if self.logger_api:
                    self.logger_api.log(
                        f"Error during shutdown: {e}",
                        level="ERROR",
                        tag="network"
                    )
        
        if self.logger_api:
            self.logger_api.log("NetworkFastAPI module stopped", tag="network")
