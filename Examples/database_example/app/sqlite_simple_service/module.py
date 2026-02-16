"""
SQLite Simple Service Module - Demonstrates database operations with web UI.
"""
from massir.core.interfaces import IModule, ModuleContext
from .services.database import (
    create_users_table,
    create_products_table,
    get_table_list,
    get_table_info,
    get_table_row_count
)
from .routes.pages import register_page_routes


class SqliteSimpleServiceModule(IModule):
    """
    SQLite simple service module with web UI for database management.
    """
    
    name = "sqlite_simple_service"
    provides = ["sqlite_simple_service"]
    
    def __init__(self):
        self.db = None
        self.http_api = None
        self.logger = None
        self.template = None
        self.menu_manager = None
    
    async def load(self, context: ModuleContext):
        """Get services."""
        self.db = context.services.get("database_service")
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        self.template = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        
        if self.logger:
            self.logger.log("SqliteSimpleService module loaded", tag="sqlite_simple")
    
    async def start(self, context: ModuleContext):
        """Initialize database schema and register routes."""
        # Create tables
        await create_users_table(self.db, self.logger)
        await create_products_table(self.db, self.logger)
        
        # Register web UI routes
        services = {
            'get_table_list': get_table_list,
            'get_table_info': get_table_info,
            'get_table_row_count': get_table_row_count
        }
        register_page_routes(self.http_api, self.template, self.db, self.logger, services)
        
        # Register menu items
        if self.menu_manager:
            self.menu_manager.register_menu(
                id="db_dashboard",
                label="Database",
                url="/db",
                icon="🗄️",
                order=10
            )
            self.menu_manager.register_menu(
                id="db_users",
                label="Users",
                url="/db/users",
                icon="👥",
                order=11
            )
            self.menu_manager.register_menu(
                id="db_products",
                label="Products",
                url="/db/products",
                icon="📦",
                order=12
            )
            self.menu_manager.register_menu(
                id="db_query",
                label="SQL Query",
                url="/db/query",
                icon="🔍",
                order=13
            )
            if self.logger:
                self.logger.log("Database menus registered", tag="sqlite_simple")
        
        if self.logger:
            self.logger.log("SqliteSimpleService module started", tag="sqlite_simple")
    
    async def ready(self, context: ModuleContext):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log("SqliteSimpleService module is ready", tag="sqlite_simple")
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        if self.menu_manager:
            self.menu_manager.unregister_menu("db_dashboard")
            self.menu_manager.unregister_menu("db_users")
            self.menu_manager.unregister_menu("db_products")
            self.menu_manager.unregister_menu("db_query")
        
        if self.logger:
            self.logger.log("SqliteSimpleService module stopped", tag="sqlite_simple")
