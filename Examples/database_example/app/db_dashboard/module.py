"""
Database Dashboard Module - Provides dashboard services.

This module provides:
- Database statistics
- Connection information
- Cache and pool statistics
"""
from massir.core.interfaces import IModule, ModuleContext
from .services import DashboardService
from .routes import register_routes


class DbDashboardModule(IModule):
    """
    Database dashboard module that provides dashboard services.
    
    This module requires db_connection_service to be available.
    """
    
    async def start(self, context: ModuleContext):
        """Get services, initialize dashboard service, register routes and menu items."""
        http_api = context.services.get("http_api")
        logger = context.services.get("core_logger")
        template = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        connection_service = context.services.get("db_connection_service")
        
        # Initialize dashboard service with connection service
        self.dashboard_service = DashboardService(connection_service)
        
        # Register web UI routes
        register_routes(
            http_api, 
            template, 
            self.dashboard_service,
            connection_service,
            logger
        )
        
        # Register menu item
        if menu_manager:
            menu_manager.register_menu(
                id="db_dashboard",
                label="Dashboard",
                url="/db/dashboard",
                icon="📊",
                order=60
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        menu_manager = context.services.get("menu_manager")
        if menu_manager:
            menu_manager.unregister_menu("db_dashboard")
