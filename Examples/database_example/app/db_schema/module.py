"""
Database Schema Module - Provides schema management services.

This module provides:
- Index management
- Foreign key management
"""
from massir.core.interfaces import IModule, ModuleContext
from .services import SchemaService
from .routes import register_routes


class DbSchemaModule(IModule):
    """
    Database schema module that provides schema management services.
    
    This module requires db_connection_service to be available.
    """
    
    async def start(self, context: ModuleContext):
        """Get services, initialize schema service, register routes and menu items."""
        http_api = context.services.get("http_api")
        logger = context.services.get("core_logger")
        template = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        connection_service = context.services.get("db_connection_service")
        
        # Initialize schema service with connection service
        self.schema_service = SchemaService(connection_service)
        
        # Register web UI routes
        register_routes(
            http_api, 
            template, 
            self.schema_service,
            connection_service,
            logger
        )
        
        # Register menu item
        if menu_manager:
            menu_manager.register_menu(
                id="db_schema",
                label="Schema",
                url="/db/schema",
                icon="🔧",
                order=50
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        menu_manager = context.services.get("menu_manager")
        if menu_manager:
            menu_manager.unregister_menu("db_schema")
