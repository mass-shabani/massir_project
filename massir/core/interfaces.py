"""
Core interfaces for the Massir framework.

This module defines the fundamental contracts that all modules and the
framework core must adhere to. The design emphasizes simplicity and
performance by providing only essential lifecycle methods.
"""

from abc import ABC
from typing import TYPE_CHECKING

from massir.core.registry import ModuleRegistry

if TYPE_CHECKING:
    from massir.core.app import App


class ModuleContext:
    """
    Context object provided to all modules during execution.
    
    This class serves as the central access point for modules to:
    - Access the service registry for dependency injection
    - Reference the main application instance
    - Store and retrieve shared metadata
    - Access framework path information
    
    Attributes:
        services: ModuleRegistry instance for service lookup/registration
        metadata: Dict for arbitrary shared data between modules
    """
    
    def __init__(self):
        """Initialize module context with empty registry and metadata."""
        self._app = None
        self.services = ModuleRegistry()
        self.metadata = {}
    
    def set_app(self, app: 'App') -> None:
        """
        Set the application reference.
        
        Args:
            app: The application instance
        """
        self._app = app
    
    def get_app(self) -> 'App':
        """
        Get the application reference.
        
        Returns:
            The application instance
        """
        return self._app
    
    @property
    def app_dir(self) -> str:
        """
        Get the application directory path.
        
        Returns:
            Application directory path string
        """
        app = self.get_app()
        if app and hasattr(app, 'path'):
            return str(app.path.app)
        return ""
    
    @property
    def massir_dir(self) -> str:
        """
        Get the massir framework directory path.
        
        Returns:
            Massir framework directory path string
        """
        app = self.get_app()
        if app and hasattr(app, 'path'):
            return str(app.path.massir)
        return ""


class IModule(ABC):
    """
    Base interface for all modules in the Massir framework.
    
    This abstract class defines the minimal contract for module lifecycle
    management. Only two methods are provided:
    
    - start(): Called when the module should begin operation
    - stop(): Called when the module should cease operation
    
    Both methods are optional (default no-op implementations). Modules
    should override only the methods they need.
    
    For additional initialization or post-start logic, modules should
    use the hook system provided by HooksManager.
    
    Class Attributes:
        name: Unique module identifier (set from manifest.json)
        id: Unique instance identifier (auto-generated if not provided)
        provides: List of capabilities this module offers
        requires: List of capabilities this module depends on
    """
    
    # Metadata attributes - populated by ModuleLoader from manifest.json
    name: str = ""
    id: str = ""
    provides: list = []
    requires: list = []
    
    # Context reference - set by ModuleLoader during instantiation
    _context: 'ModuleContext' = None
    
    async def start(self, context: 'ModuleContext') -> None:
        """
        Start the module.
        
        This method is called when the module's run order group is executed.
        Implementations should:
        - Initialize required resources
        - Register services in the context
        - Start servers or background tasks
        
        Args:
            context: The module context providing access to services
        """
        pass
    
    async def stop(self, context: 'ModuleContext') -> None:
        """
        Stop the module.
        
        This method is called during shutdown in reverse order of
        run order group execution.
        Implementations should:
        - Clean up resources
        - Close connections
        - Flush pending data
        
        Args:
            context: The module context providing access to services
        """
        pass