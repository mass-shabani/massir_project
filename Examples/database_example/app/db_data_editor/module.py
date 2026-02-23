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
    
    name = "db_data_editor"
    provides = []
    requires = ["db_connection_service"]  # Requires db_connection module
    
    def __init__(self):
        self.http_api = None
        self.logger = None
        self.template = None
        self.menu_manager = None
        self.data_service = None
        self.connection_service = None
    
    async def load(self, context: ModuleContext):
        """Get services and initialize data editor service."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        self.template = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        self.connection_service = context.services.get("db_connection_service")
        
        # Initialize data editor service with connection service
        self.data_service = DataEditorService(self.connection_service)
    
    async def start(self, context: ModuleContext):
        """Register routes and menu items."""
        # Register web UI routes
        register_routes(
            self.http_api, 
            self.template, 
            self.data_service,
            self.connection_service,
            self.logger
        )
        
        # Register menu item
        if self.menu_manager:
            self.menu_manager.register_menu(
                id="db_data",
                label="Data Editor",
                url="/db/data",
                icon="✏️",
                order=30
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        if self.menu_manager:
            self.menu_manager.unregister_menu("db_data")
