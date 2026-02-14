"""
Network FastAPI Module - High-performance network provider.

This module provides HTTP, router, network, and server APIs using FastAPI.
It does NOT start the server directly - consuming modules are responsible
for starting the server using the provided ServerAPI.
"""
import secrets
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from massir.core.interfaces import IModule
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
    
    name = "network_fastapi"
    provides = ["http_api", "router_api", "net_api", "server_api"]
    
    def __init__(self):
        self.app: Optional[FastAPI] = None
        self.http_api: Optional[HTTPAPI] = None
        self.router_api: Optional[RouterAPI] = None
        self.net_api: Optional[NetAPI] = None
        self.server_api: Optional[ServerAPI] = None
        self.config_api: Optional[CoreConfigAPI] = None
        self.logger_api: Optional[CoreLoggerAPI] = None
    
    async def load(self, context):
        """
        Initialize FastAPI application and APIs.
        
        Sets up the FastAPI app with middleware and default routes.
        Does NOT start the server.
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
        self.server_api = ServerAPI(self.app, self.config_api, self.logger_api)
        
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
        context.services.set("server_api", self.server_api)
        
        if self.logger_api:
            self.logger_api.log("NetworkFastAPI module loaded (server not started)", tag="network")
    
    def _setup_middleware(self):
        """Setup middleware for FastAPI app."""
        # Session middleware (must be added first for proper order)
        secret_key = self.config_api.get("fastapi_provider.session.secret_key", secrets.token_hex(32))
        session_cookie = self.config_api.get("fastapi_provider.session.cookie_name", "session")
        max_age = self.config_api.get("fastapi_provider.session.max_age", 14 * 24 * 60 * 60)  # 14 days default
        self.app.add_middleware(
            SessionMiddleware,
            secret_key=secret_key,
            session_cookie=session_cookie,
            max_age=max_age
        )
        
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
        Start the network module.
        
        Note: This does NOT start the HTTP server.
        The consuming module should use server_api to start the server.
        """
        if self.logger_api:
            self.logger_api.log("NetworkFastAPI module started (use server_api to start HTTP server)", tag="network")
    
    async def stop(self, context):
        """
        Stop the network module.
        
        Stops the server if it's running.
        """
        if self.server_api and self.server_api.is_running:
            await self.server_api.stop_server()
        
        if self.logger_api:
            self.logger_api.log("NetworkFastAPI module stopped", tag="network")
