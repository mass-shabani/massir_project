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
    
    async def start(self, context: ModuleContext):
        """Get services, initialize tables service, register routes and menu items."""
        http_api = context.services.get("http_api")
        logger = context.services.get("core_logger")
        template = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        connection_service = context.services.get("db_connection_service")
        
        # Initialize tables service with connection service
        self.tables_service = TablesService(connection_service)
        
        # Register web UI routes
        register_routes(
            http_api, 
            template, 
            self.tables_service,
            connection_service,
            logger
        )
        
        # Register menu item
        if menu_manager:
            menu_manager.register_menu(
                id="db_tables",
                label="Tables",
                url="/db/tables",
                icon="📋",
                order=20
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        menu_manager = context.services.get("menu_manager")
        if menu_manager:
            menu_manager.unregister_menu("db_tables")
