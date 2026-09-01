"""
Main App Module - Home and About pages.
"""
from massir.core.interfaces import IModule, ModuleContext
from .routes.pages import register_routes


class MainAppModule(IModule):
    """Main application module providing home and about pages."""
    
    async def start(self, context: ModuleContext):
        """Start the main app module - load services, register routes and menus."""
        logger = context.services.get("core_logger")
        http_api = context.services.get("http_api")
        template = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        
        # Register routes
        register_routes(http_api, template, logger)
        
        # Register menu items
        if menu_manager:
            menu_manager.register_menu(
                id="main_app_home",
                label="Home",
                url="/",
                icon="🏠",
                order=0
            )
            menu_manager.register_menu(
                id="main_app_about",
                label="About",
                url="/about",
                icon="ℹ️",
                order=100
            )
    
    async def stop(self, context: ModuleContext):
        """Stop the main app module."""
        menu_manager = context.services.get("menu_manager")
        if menu_manager:
            menu_manager.unregister_menu("main_app_home")
            menu_manager.unregister_menu("main_app_about")
