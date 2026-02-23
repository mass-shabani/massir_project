"""
Database Tables Module - Provides table management services.

This module provides:
- Table listing and management
- Create and drop tables
- View table schema and data
- Create sample tables with test data
"""
from massir.core.interfaces import IModule, ModuleContext
from .services import TablesService
from .routes import register_routes


class DbTablesModule(IModule):
    """
    Database tables module that provides table management services.
    
    This module requires db_connection_service to be available.
    """
    
    name = "db_tables"
    provides = []
    requires = ["db_connection_service"]  # Requires db_connection module
    
    def __init__(self):
        self.http_api = None
        self.logger = None
        self.template = None
        self.menu_manager = None
        self.tables_service = None
        self.connection_service = None
    
    async def load(self, context: ModuleContext):
        """Get services and initialize tables service."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        self.template = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        self.connection_service = context.services.get("db_connection_service")
        
        # Initialize tables service with connection service
        self.tables_service = TablesService(self.connection_service)
    
    async def start(self, context: ModuleContext):
        """Register routes and menu items."""
        # Register web UI routes
        register_routes(
            self.http_api, 
            self.template, 
            self.tables_service,
            self.connection_service,
            self.logger
        )
        
        # Register menu item
        if self.menu_manager:
            self.menu_manager.register_menu(
                id="db_tables",
                label="Tables",
                url="/db/tables",
                icon="📋",
                order=20
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        if self.menu_manager:
            self.menu_manager.unregister_menu("db_tables")
