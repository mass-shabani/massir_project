"""
Network FastAPI Module for Massir Framework.

This module provides high-performance HTTP, router, network, and server
APIs using FastAPI. It sets up the FastAPI application with middleware,
default routes, and exception handlers, but does NOT start the server
directly. Consuming modules are responsible for starting the server
using the provided ServerAPI.

Services registered:
- http_api: HTTPAPI for route registration
- router_api: RouterAPI for advanced routing
- net_api: NetAPI for network information
- server_api: ServerAPI for server lifecycle control
"""

import secrets
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from massir.core.interfaces import IModule, ModuleContext
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI

from .api.http import HTTPAPI
from .api.router import RouterAPI
from .api.net import NetAPI
from .api.server import ServerAPI


class NetworkFastAPIModule(IModule):
    """
    Network provider module using FastAPI.
    
    Provides high-performance HTTP, router, network, and server APIs
    without requiring FastAPI imports in consuming modules.
    
    This module does NOT start the HTTP server. Consuming modules
    should use the ServerAPI to start the server when needed.
    """
    
    def __init__(self):
        """Initialize module with empty API references."""
        self.app: Optional[FastAPI] = None
        self.http_api: Optional[HTTPAPI] = None
        self.router_api: Optional[RouterAPI] = None
        self.net_api: Optional[NetAPI] = None
        self.server_api: Optional[ServerAPI] = None
        self.config_api: Optional[CoreConfigAPI] = None
        self.logger_api: Optional[CoreLoggerAPI] = None
    
    async def start(self, context: ModuleContext) -> None:
        """
        Start the network FastAPI module.
        
        This method:
        1. Retrieves core services (logger, config) from context
        2. Creates the FastAPI application with configured settings
        3. Creates API abstractions (HTTP, Router, Net, Server)
        4. Sets up middleware (Session, TrustedHost, CORS, GZip)
        5. Sets up default routes (/health, /info, /network)
        6. Sets up exception handlers (global, 404)
        7. Registers all API services in the context
        8. Logs activation confirmation
        
        Note: This method does NOT start the HTTP server.
        Consuming modules should use server_api.start_server() to
        begin serving requests.
        
        Args:
            context: Module context providing access to services
        """
        # Get core services
        self.logger_api = context.services.get("core_logger")
        self.config_api = context.services.get("core_config")
        
        # Create FastAPI application with configured settings
        self.app = FastAPI(
            title=self.config_api.get("fastapi_provider.title", "Massir API"),
            version=self.config_api.get("fastapi_provider.version", "1.0.0"),
            description=self.config_api.get(
                "fastapi_provider.description", "Modular API"
            ),
            docs_url=self.config_api.get(
                "fastapi_provider.docs_url", "/docs"
            ),
            redoc_url=self.config_api.get(
                "fastapi_provider.redoc_url", "/redoc"
            ),
            openapi_url=self.config_api.get(
                "fastapi_provider.openapi_url", "/openapi.json"
            )
        )
        
        # Create API abstractions
        self.http_api = HTTPAPI(self.app)
        self.router_api = RouterAPI()
        self.net_api = NetAPI(self.config_api)
        self.server_api = ServerAPI(
            self.app, self.config_api, self.logger_api
        )
        
        # Setup middleware, routes, and exception handlers
        self._setup_middleware()
        self._setup_default_routes()
        self._setup_exception_handlers()
        
        # Register services for other modules
        context.services.set("http_api", self.http_api)
        context.services.set("router_api", self.router_api)
        context.services.set("net_api", self.net_api)
        context.services.set("server_api", self.server_api)
        
        if self.logger_api:
            self.logger_api.log(
                "NetworkFastAPI module started (server not started, "
                "use server_api to start HTTP server)",
                tag="network"
            )
    
    async def stop(self, context: ModuleContext) -> None:
        """
        Stop the network FastAPI module.
        
        Stops the HTTP server if it is currently running.
        
        Args:
            context: Module context
        """
        if self.server_api and self.server_api.is_running:
            await self.server_api.stop_server()
        
        if self.logger_api:
            self.logger_api.log(
                "NetworkFastAPI module stopped", tag="network"
            )
    
    def _setup_middleware(self) -> None:
        """
        Setup middleware for the FastAPI application.
        
        Middleware order (important for correct operation):
        1. SessionMiddleware - Must be first for proper cookie handling
        2. TrustedHostMiddleware - Host validation (if configured)
        3. CORSMiddleware - Cross-origin resource sharing
        4. GZipMiddleware - Response compression
        """
        # Session middleware (must be added first for proper order)
        secret_key = self.config_api.get(
            "fastapi_provider.session.secret_key",
            secrets.token_hex(32)
        )
        session_cookie = self.config_api.get(
            "fastapi_provider.session.cookie_name", "session"
        )
        max_age = self.config_api.get(
            "fastapi_provider.session.max_age", 14 * 24 * 60 * 60
        )
        self.app.add_middleware(
            SessionMiddleware,
            secret_key=secret_key,
            session_cookie=session_cookie,
            max_age=max_age
        )
        
        # Trusted Host middleware
        trusted_hosts = self.config_api.get(
            "fastapi_provider.trusted_hosts", ["*"]
        )
        if trusted_hosts != ["*"]:
            self.app.add_middleware(
                TrustedHostMiddleware, allowed_hosts=trusted_hosts
            )
        
        # CORS middleware
        cors_origins = self.config_api.get(
            "fastapi_provider.cors.origins", ["*"]
        )
        cors_credentials = self.config_api.get(
            "fastapi_provider.cors.credentials", True
        )
        cors_methods = self.config_api.get(
            "fastapi_provider.cors.methods", ["*"]
        )
        cors_headers = self.config_api.get(
            "fastapi_provider.cors.headers", ["*"]
        )
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=cors_credentials,
            allow_methods=cors_methods,
            allow_headers=cors_headers
        )
        
        # GZip middleware
        gzip_enabled = self.config_api.get(
            "fastapi_provider.gzip.enabled", True
        )
        gzip_min_size = self.config_api.get(
            "fastapi_provider.gzip.minimum_size", 1000
        )
        if gzip_enabled:
            self.app.add_middleware(
                GZipMiddleware, minimum_size=gzip_min_size
            )
    
    def _setup_default_routes(self) -> None:
        """
        Setup default health and info routes.
        
        Routes created:
        - GET /health: Health check endpoint
        - GET /info: Service information
        - GET /network: Network information
        """
        @self.http_api.get(
            "/health", tags=["system"], summary="Health check endpoint"
        )
        async def health_check():
            """Check if the service is healthy."""
            return {
                "status": "healthy",
                "service": "network_fastapi",
                "version": "1.0.0"
            }
        
        @self.http_api.get(
            "/info", tags=["system"], summary="Service information"
        )
        async def info():
            """Get service information."""
            return {
                "name": "network_fastapi",
                "version": "1.0.0",
                "framework": "Massir",
                "hostname": self.net_api.get_hostname(),
                "ip_address": self.net_api.get_ip_address()
            }
        
        @self.http_api.get(
            "/network", tags=["system"], summary="Network information"
        )
        async def network_info():
            """Get network information."""
            return self.net_api.get_network_info()
    
    def _setup_exception_handlers(self) -> None:
        """
        Setup global exception handlers.
        
        Handlers:
        - Global exception handler: Catches all unhandled exceptions
          and returns a 500 response with error details (in debug mode)
        - 404 handler: Returns a structured 404 response with path info
        """
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
                    "detail": str(exc) if self.config_api.get(
                        "fastapi_provider.debug", False
                    ) else None
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