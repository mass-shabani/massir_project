"""
Router API abstraction for FastAPI.

This module provides router management capabilities.
"""
from typing import List, Callable, Optional, Any
from fastapi import APIRouter


class RouterAPI:
    """
    Router API for managing API routers.
    
    Provides methods to create and manage routers without importing FastAPI.
    """
    
    def __init__(self):
        """Initialize Router API."""
        self._routers: List[APIRouter] = []
    
    def create(self, prefix: str = "", tags: List[str] = None,
              dependencies: List[Callable] = None,
              responses: dict = None,
              default_response_class: type = None) -> APIRouter:
        """
        Create a new router.
        
        Args:
            prefix: URL path prefix for all routes in this router
            tags: List of tags for grouping routes in documentation
            dependencies: List of dependency injection functions
            responses: Dictionary of response schemas
            default_response_class: Default response class
        
        Returns:
            APIRouter instance
        
        Usage:
            router = router_api.create(prefix="/api/v1", tags=["users"])
        """
        router = APIRouter(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            responses=responses,
            default_response_class=default_response_class
        )
        self._routers.append(router)
        return router
    
    def add_route(self, router: APIRouter, path: str, methods: List[str],
                 endpoint: Callable, **kwargs):
        """
        Add a route to an existing router.
        
        Args:
            router: Router to add route to
            path: Route path
            methods: List of HTTP methods (GET, POST, etc.)
            endpoint: Endpoint function
            **kwargs: Additional route arguments
        """
        router.add_api_route(path, endpoint, methods=methods, **kwargs)
    
    def add_websocket_route(self, router: APIRouter, path: str, 
                          endpoint: Callable, **kwargs):
        """
        Add a WebSocket route to an existing router.
        
        Args:
            router: Router to add route to
            path: Route path
            endpoint: WebSocket endpoint function
            **kwargs: Additional route arguments
        """
        router.add_websocket_route(path, endpoint, **kwargs)
    
    def add_middleware(self, router: APIRouter, middleware: Callable):
        """
        Add middleware to a router.
        
        Args:
            router: Router to add middleware to
            middleware: Middleware function
        """
        router.middleware(middleware)
    
    def include(self, router: APIRouter, app, **kwargs):
        """
        Include a router in the FastAPI app.
        
        Args:
            router: Router to include
            app: FastAPI application instance
            **kwargs: Additional include_router arguments
        """
        app.include_router(router, **kwargs)
    
    def get_all(self) -> List[APIRouter]:
        """
        Get all created routers.
        
        Returns:
            List of APIRouter instances
        """
        return self._routers
    
    def clear(self):
        """Clear all routers."""
        self._routers.clear()
