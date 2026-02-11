"""
High-performance HTTP API abstraction for FastAPI.

This module provides a thin wrapper around FastAPI to avoid performance overhead
while hiding FastAPI imports from consuming modules.
"""
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic
from functools import wraps
from dataclasses import dataclass


T = TypeVar('T')


@dataclass
class HTTPResponse:
    """Simple HTTP response wrapper."""
    status_code: int = 200
    data: Any = None
    headers: Dict[str, str] = None
    
    def to_dict(self):
        return {
            "status_code": self.status_code,
            "data": self.data,
            "headers": self.headers or {}
        }


class HTTPAPI:
    """
    High-performance HTTP API abstraction.
    
    Uses direct FastAPI decorator references to minimize overhead.
    Other modules use this class without importing FastAPI.
    """
    
    def __init__(self, fastapi_app):
        """
        Initialize HTTP API with FastAPI app.
        
        Args:
            fastapi_app: FastAPI application instance
        """
        self._app = fastapi_app
        # Direct references to FastAPI methods for zero overhead
        self._get = fastapi_app.get
        self._post = fastapi_app.post
        self._put = fastapi_app.put
        self._delete = fastapi_app.delete
        self._patch = fastapi_app.patch
        self._head = fastapi_app.head
        self._options = fastapi_app.options
        self._trace = fastapi_app.trace
    
    def get(self, path: str, **kwargs):
        """
        Decorator for GET routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        
        Usage:
            @http_api.get("/items", tags=["items"])
            async def get_items():
                return {"items": []}
        """
        return self._get(path, **kwargs)
    
    def post(self, path: str, **kwargs):
        """
        Decorator for POST routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        """
        return self._post(path, **kwargs)
    
    def put(self, path: str, **kwargs):
        """
        Decorator for PUT routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        """
        return self._put(path, **kwargs)
    
    def delete(self, path: str, **kwargs):
        """
        Decorator for DELETE routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        """
        return self._delete(path, **kwargs)
    
    def patch(self, path: str, **kwargs):
        """
        Decorator for PATCH routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        """
        return self._patch(path, **kwargs)
    
    def head(self, path: str, **kwargs):
        """
        Decorator for HEAD routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        """
        return self._head(path, **kwargs)
    
    def options(self, path: str, **kwargs):
        """
        Decorator for OPTIONS routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        """
        return self._options(path, **kwargs)
    
    def trace(self, path: str, **kwargs):
        """
        Decorator for TRACE routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        """
        return self._trace(path, **kwargs)
    
    def websocket(self, path: str, **kwargs):
        """
        Decorator for WebSocket routes.
        
        Args:
            path: Route path
            **kwargs: Additional FastAPI route arguments
        
        Usage:
            @http_api.websocket("/ws")
            async def websocket_endpoint(websocket):
                await websocket.accept()
                await websocket.send_text("Hello")
                await websocket.close()
        """
        return self._app.websocket(path, **kwargs)
    
    def include_router(self, router, **kwargs):
        """
        Include a router in the FastAPI app.
        
        Args:
            router: Router to include
            **kwargs: Additional FastAPI include_router arguments
        """
        self._app.include_router(router, **kwargs)
    
    def add_middleware(self, middleware_class, **kwargs):
        """
        Add middleware to the FastAPI app.
        
        Args:
            middleware_class: Middleware class
            **kwargs: Additional middleware arguments
        """
        self._app.add_middleware(middleware_class, **kwargs)
    
    def exception_handler(self, exc_class, handler):
        """
        Add exception handler.
        
        Args:
            exc_class: Exception class to handle
            handler: Handler function
        """
        self._app.add_exception_handler(exc_class, handler)
    
    def on_event(self, event_type: str):
        """
        Decorator for event handlers.
        
        Args:
            event_type: Event type ("startup" or "shutdown")
        
        Usage:
            @http_api.on_event("startup")
            async def startup_event():
                print("Application starting")
        """
        return self._app.on_event(event_type)
    
    def response(self, data: Any = None, status_code: int = 200, 
                headers: Dict[str, str] = None) -> HTTPResponse:
        """
        Create a structured HTTP response.
        
        Args:
            data: Response data
            status_code: HTTP status code
            headers: Response headers
        
        Returns:
            HTTPResponse object
        
        Usage:
            return http_api.response(data={"message": "success"}, status_code=201)
        """
        return HTTPResponse(
            status_code=status_code,
            data=data,
            headers=headers
        )
    
    def error(self, message: str, status_code: int = 400, 
              code: str = None, details: Any = None) -> HTTPResponse:
        """
        Create an error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            code: Error code
            details: Additional error details
        
        Returns:
            HTTPResponse object
        
        Usage:
            return http_api.error("Invalid input", status_code=400, code="INVALID_INPUT")
        """
        error_data = {
            "error": True,
            "message": message
        }
        if code:
            error_data["code"] = code
        if details is not None:
            error_data["details"] = details
        
        return HTTPResponse(
            status_code=status_code,
            data=error_data
        )
    
    @property
    def app(self):
        """
        Get the underlying FastAPI app instance.
        
        Returns:
            FastAPI application instance
        """
        return self._app
