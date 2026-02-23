"""
Database Connection Module - Provides connection management services.

This module provides:
- Database connection management (SQLite, PostgreSQL, MySQL)
- Connection testing and establishment
- Session-based connection storage
- Connection service for other modules to use
"""
from massir.core.interfaces import IModule, ModuleContext
from .services import ConnectionService, LogManager
from .routes import register_routes


class DbConnectionModule(IModule):
    """
    Database connection module that provides connection services to other modules.
    
    This module is the core of database management and must be loaded before
    other database-related modules (tables, data_editor, transactions, schema, dashboard).
    """
    
    name = "db_connection"
    provides = ["db_connection_service", "db_connection_types"]
    requires = ["database_service"]  # Requires system_database module
    
    def __init__(self):
        self.http_api = None
        self.logger = None
        self.template = None
        self.menu_manager = None
        self.connection_service = None
        self.log_manager = None
    
    async def load(self, context: ModuleContext):
        """Get services and initialize connection service."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        self.template = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        self.path_manager = context.services.get("core_path")
        
        # Get database_service from system_database module (provided via context)
        database_service = context.services.get("database_service")
        
        # Get database_types from system_database module (provided via context)
        database_types = context.services.get("database_types")
        
        # Create a LogManager instance for the connection service
        self.log_manager = LogManager(self.logger)
        
        # Initialize connection service with services from context
        self.connection_service = ConnectionService(
            log_manager=self.log_manager,
            path_manager=self.path_manager,
            database_service=database_service,
            database_types=database_types
        )
        
        # Register the connection service for other modules to use
        context.services.set("db_connection_service", self.connection_service)
        
        # Also register types that other modules might need
        context.services.set("db_connection_types", {
            "ConnectionInfo": type(self.connection_service.get_connection().__class__) if self.connection_service.get_connection() else None,
            "LogManager": LogManager
        })
    
    async def start(self, context: ModuleContext):
        """Register routes and menu items."""
        # Register web UI routes
        register_routes(
            self.http_api, 
            self.template, 
            self.connection_service, 
            self.logger
        )
        
        # Register menu item
        if self.menu_manager:
            self.menu_manager.register_menu(
                id="db_connection",
                label="Connection",
                url="/db/connection",
                icon="🔗",
                order=10
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Disconnect all connections
        if self.connection_service:
            # Disconnect all active connections
            for conn_name in list(self.connection_service._connection_info.keys()):
                await self.connection_service.disconnect(conn_name)
        
        # Unregister menu items
        if self.menu_manager:
            self.menu_manager.unregister_menu("db_connection")
