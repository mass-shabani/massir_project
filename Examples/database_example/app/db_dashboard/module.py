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
    
    name = "db_dashboard"
    provides = []
    requires = ["db_connection_service"]  # Requires db_connection module
    
    def __init__(self):
        self.http_api = None
        self.logger = None
        self.template = None
        self.menu_manager = None
        self.dashboard_service = None
        self.connection_service = None
    
    async def load(self, context: ModuleContext):
        """Get services and initialize dashboard service."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        self.template = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        self.connection_service = context.services.get("db_connection_service")
        
        # Initialize dashboard service with connection service
        self.dashboard_service = DashboardService(self.connection_service)
    
    async def start(self, context: ModuleContext):
        """Register routes and menu items."""
        # Register web UI routes
        register_routes(
            self.http_api, 
            self.template, 
            self.dashboard_service,
            self.connection_service,
            self.logger
        )
        
        # Register menu item
        if self.menu_manager:
            self.menu_manager.register_menu(
                id="db_dashboard",
                label="Dashboard",
                url="/db/dashboard",
                icon="📊",
                order=60
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        if self.menu_manager:
            self.menu_manager.unregister_menu("db_dashboard")
