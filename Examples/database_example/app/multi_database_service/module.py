"""
Multi-Database Service Module - Demonstrates dynamic database connections with web UI.

This module provides:
- Dynamic database connection management (SQLite, PostgreSQL, MySQL)
- Table management with CRUD operations
- Data editing with dynamic field generation
- Database dashboard with statistics
"""
from massir.core.interfaces import IModule, ModuleContext
from .services.database import MultiDatabaseManager
from .services.models import LogManager
from .routes.pages import register_page_routes


class MultiDatabaseServiceModule(IModule):
    """
    Multi-database service module with web UI for dynamic database management.
    """
    
    name = "multi_database_service"
    provides = ["multi_database_service"]
    requires = ["database_service"]  # Requires system_database module
    
    def __init__(self):
        self.http_api = None
        self.logger = None
        self.template = None
        self.menu_manager = None
        self.db_manager = None
        self.log_manager = None
        self.database_service = None
    
    async def load(self, context: ModuleContext):
        """Get services."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        self.template = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        self.path_manager = context.services.get("core_path")  # Registered as "core_path" in registry
        
        # Get database_service from system_database module (provided via context)
        self.database_service = context.services.get("database_service")
        
        # Get database_types from system_database module (provided via context)
        self.database_types = context.services.get("database_types")
        
        # Create a LogManager instance for the database manager
        self.log_manager = LogManager(self.logger)
        
        # Initialize database manager with services from context
        self.db_manager = MultiDatabaseManager(
            log_manager=self.log_manager,
            path_manager=self.path_manager,
            database_service=self.database_service,
            database_types=self.database_types
        )
        
        if self.logger:
            self.logger.log("MultiDatabaseService module loaded", tag="multi_db")
    
    async def start(self, context: ModuleContext):
        """Register routes and menu items."""
        # Register web UI routes
        register_page_routes(
            self.http_api, 
            self.template, 
            self.db_manager, 
            self.logger
        )
        
        # Register menu items under 'multi_db' group
        if self.menu_manager:
            # Register the group first
            self.menu_manager.register_group(
                group_id="multi_db",
                label="Multi-Database",
                icon="🔌",
                css_class="multi-db",
                order=5
            )
            
            self.menu_manager.register_menu(
                id="multi_db_connection",
                label="Connection",
                url="/multi-db/connection",
                icon="🔗",
                order=1,
                group="multi_db"
            )
            self.menu_manager.register_menu(
                id="multi_db_tables",
                label="Tables",
                url="/multi-db/tables",
                icon="📋",
                order=2,
                group="multi_db"
            )
            self.menu_manager.register_menu(
                id="multi_db_data",
                label="Data Editor",
                url="/multi-db/data",
                icon="✏️",
                order=3,
                group="multi_db"
            )
            self.menu_manager.register_menu(
                id="multi_db_transactions",
                label="Transactions",
                url="/multi-db/transactions",
                icon="🔄",
                order=4,
                group="multi_db"
            )
            self.menu_manager.register_menu(
                id="multi_db_schema",
                label="Schema",
                url="/multi-db/schema",
                icon="🔧",
                order=5,
                group="multi_db"
            )
            self.menu_manager.register_menu(
                id="multi_db_dashboard",
                label="Dashboard",
                url="/multi-db/dashboard",
                icon="📊",
                order=6,
                group="multi_db"
            )
            
            if self.logger:
                self.logger.log("Multi-Database menus registered", tag="multi_db")
        
        if self.logger:
            self.logger.log("MultiDatabaseService module started", tag="multi_db")
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Disconnect all connections
        if self.db_manager:
            # Disconnect all active connections
            for conn_name in list(self.db_manager._connection_info.keys()):
                await self.db_manager.disconnect(conn_name)
        
        # Unregister menu items
        if self.menu_manager:
            self.menu_manager.unregister_menu("multi_db_connection")
            self.menu_manager.unregister_menu("multi_db_tables")
            self.menu_manager.unregister_menu("multi_db_data")
            self.menu_manager.unregister_menu("multi_db_transactions")
            self.menu_manager.unregister_menu("multi_db_schema")
            self.menu_manager.unregister_menu("multi_db_dashboard")
        
        if self.logger:
            self.logger.log("MultiDatabaseService module stopped", tag="multi_db")
