"""
Main App Module - Home and About pages.
"""
from massir.core.interfaces import IModule, ModuleContext
from .routes.pages import register_routes


class MainAppModule(IModule):
    """Main application module providing home and about pages."""
    
    _logger = None
    _http_api = None
    _template = None
    _menu_manager = None
    
    async def load(self, context: ModuleContext):
        """Load the main app module."""
        self._logger = context.services.get("core_logger")
        self._http_api = context.services.get("http_api")
        self._template = context.services.get("template_service")
        self._menu_manager = context.services.get("menu_manager")
        
        if self._logger:
            self._logger.log("Main app module loading", tag="main_app")
    
    async def start(self, context: ModuleContext):
        """Start the main app module - register routes and menus."""
        if self._logger:
            self._logger.log("Main app module starting", tag="main_app")
        
        # Register routes
        register_routes(self._http_api, self._template, self._logger)
        
        # Register menu items
        if self._menu_manager:
            self._menu_manager.register_menu(
                id="main_app_home",
                label="Home",
                url="/",
                icon="🏠",
                order=0
            )
            self._menu_manager.register_menu(
                id="main_app_about",
                label="About",
                url="/about",
                icon="ℹ️",
                order=100
            )
            if self._logger:
                self._logger.log("Main app menus registered", tag="main_app")
    
    async def stop(self, context: ModuleContext):
        """Stop the main app module."""
        # Unregister menu items
        if self._menu_manager:
            self._menu_manager.unregister_menu("main_app_home")
            self._menu_manager.unregister_menu("main_app_about")
        
        if self._logger:
            self._logger.log("Main app module stopped", tag="main_app")
