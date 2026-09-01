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
    
    async def start(self, context: ModuleContext):
        """Get services, initialize transaction service, register routes and menu items."""
        http_api = context.services.get("http_api")
        logger = context.services.get("core_logger")
        template = context.services.get("template_service")
        menu_manager = context.services.get("menu_manager")
        
        # Get connection_service from db_connection module (provided via context)
        connection_service = context.services.get("db_connection_service")
        
        # Initialize transaction service with connection service
        self.transaction_service = TransactionsService(connection_service)
        
        # Register web UI routes
        register_routes(
            http_api, 
            template, 
            self.transaction_service,
            connection_service,
            logger
        )
        
        # Register menu item
        if menu_manager:
            menu_manager.register_menu(
                id="db_transactions",
                label="Transactions",
                url="/db/transactions",
                icon="🔄",
                order=40
            )
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        # Unregister menu items
        menu_manager = context.services.get("menu_manager")
        if menu_manager:
            menu_manager.unregister_menu("db_transactions")
