"""
Database Data Editor Module - Provides data editing services.

This module provides:
- View and edit table data
- Add new records
- Update existing records
- Delete records
"""
from massir.core.interfaces import IModule, ModuleContext
from .services import DataEditorService
from .routes import register_routes


class DbDataEditorModule(IModule):
    """
    Database data editor module that provides data editing services.
    
    This module requires db_connection_service to be available.
    """
    
    async def start(self, context: ModuleContext):
        """Get services, initialize data editor service, register routes and menu items."""
        http_api = context.services.get("http_api")
        logger = context.services.get("core_logger")
        template = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        connection_service = context.services.get("db_connection_service")
        
        # Initialize data editor service with connection service
        self.data_service = DataEditorService(connection_service)
        
        # Register web UI routes
        register_routes(
            http_api, 
            template, 
            self.data_service,
            connection_service,
            logger
        )
        
        # Register menu item
        if menu_manager:
            menu_manager.register_menu(
                id="db_data",
                label="Data Editor",
                url="/db/data",
                icon="✏️",
                order=30
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        menu_manager = context.services.get("menu_manager")
        if menu_manager:
            menu_manager.unregister_menu("db_data")
