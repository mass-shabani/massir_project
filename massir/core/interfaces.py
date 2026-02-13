from abc import ABC
from typing import TYPE_CHECKING

from massir.core.registry import ModuleRegistry

if TYPE_CHECKING:
    from massir.core.app import App


class ModuleContext:
    """
    Context provided to all modules.

    Contains the service registry and reference to the core for
    registering callbacks.
    """

    def __init__(self):
        """Initialize module context."""
        self._app = None
        self.services = ModuleRegistry()
        self.metadata = {}

    def set_app(self, app: 'App'):
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


class IModule(ABC):
    """
    Base interface for all modules.
    
    All lifecycle methods (load, start, ready, stop) are optional.
    Subclasses can override only the methods they need.
    """
    name: str = ""

    async def load(self, context: 'ModuleContext'):
        """
        Load the module and initialize resources.

        Args:
            context: The module context
        """
        pass

    async def start(self, context: 'ModuleContext'):
        """
        Start the module and execute business logic.

        Args:
            context: The module context
        """
        pass

    async def ready(self, context: 'ModuleContext'):
        """
        Called after all modules have started.
        This method is invoked when all modules' start methods have completed,
        allowing modules to perform initialization that depends on other modules being ready.

        Args:
            context: The module context
        """
        pass

    async def stop(self, context: 'ModuleContext'):
        """
        Stop the module and cleanup resources.

        Args:
            context: The module context
        """
        pass