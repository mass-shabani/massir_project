"""
Database Transactions Module - Provides transaction management services.

This module provides:
- Begin, commit, rollback transactions
- Execute raw SQL queries
"""
from massir.core.interfaces import IModule, ModuleContext
from .services import TransactionsService
from .routes import register_routes


class DbTransactionsModule(IModule):
    """
    Database transactions module that provides transaction management services.
    
    This module requires db_connection_service to be available.
    """
    
    name = "db_transactions"
    provides = []
    requires = ["db_connection_service"]  # Requires db_connection module
    
    def __init__(self):
        self.http_api = None
        self.logger = None
        self.template = None
        self.menu_manager = None
        self.transaction_service = None
        self.connection_service = None
    
    async def load(self, context: ModuleContext):
        """Get services and initialize transaction service."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        self.template = context.services.get("template_service")
        self.menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        self.connection_service = context.services.get("db_connection_service")
        
        # Initialize transaction service with connection service
        self.transaction_service = TransactionsService(self.connection_service)
    
    async def start(self, context: ModuleContext):
        """Register routes and menu items."""
        # Register web UI routes
        register_routes(
            self.http_api, 
            self.template, 
            self.transaction_service,
            self.connection_service,
            self.logger
        )
        
        # Register menu item
        if self.menu_manager:
            self.menu_manager.register_menu(
                id="db_transactions",
                label="Transactions",
                url="/db/transactions",
                icon="🔄",
                order=40
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        if self.menu_manager:
            self.menu_manager.unregister_menu("db_transactions")
