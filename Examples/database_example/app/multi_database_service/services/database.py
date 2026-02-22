"""
Multi-Database Manager using system_database.

This module provides a unified interface for multi-database operations
by leveraging the system_database module's capabilities.

The manager is composed of multiple mixins:
- ConnectionMixin: Connection management operations
- TableMixin: Table management operations
- DataMixin: Data CRUD operations
- TransactionMixin: Transaction management operations
- SchemaMixin: Index and foreign key management
"""
from typing import Any, Dict, List, Optional

from .models import ConnectionInfo, LogManager
from .connection import ConnectionMixin
from .tables import TableMixin
from .data import DataMixin
from .transaction import TransactionMixin
from .schema import SchemaMixin


class MultiDatabaseManager(ConnectionMixin, TableMixin, DataMixin, TransactionMixin, SchemaMixin):
    """
    Multi-database manager that uses system_database for all operations.
    
    This class combines multiple mixins to provide:
    - Dynamic connection management (ConnectionMixin)
    - Table operations: create, drop, list (TableMixin)
    - Data operations: CRUD (DataMixin)
    - Transaction management (TransactionMixin)
    - Schema management: indexes, foreign keys (SchemaMixin)
    - Sample data generation (TableMixin)
    """
    
    def __init__(self, log_manager: LogManager, path_manager=None, database_service=None, database_types=None):
        """
        Initialize the multi-database manager.
        
        Args:
            log_manager: LogManager instance for logging operations
            path_manager: Optional path manager for resolving path placeholders
            database_service: DatabaseService instance from system_database module (via context)
            database_types: Dictionary of database types from system_database module (via context)
        """
        # Initialize mixins that need initialization
        TransactionMixin.__init__(self)
        
        # database_service must be provided via context
        if database_service is None:
            raise ValueError("database_service must be provided via context. Ensure system_database module is loaded.")
        
        self._db_service = database_service
        
        # Store database types from context
        self._db_types = database_types or {}
        
        # Set logger for database service
        self._db_service.set_logger(type('Logger', (), {
            'log': lambda self, msg, level='INFO', tag=None: log_manager.log(msg, level, tag)
        })())
        
        # Store references
        self._log = log_manager.log
        self._log_manager = log_manager
        self._path_manager = path_manager
        
        # Connection state
        self._active_connection: Optional[str] = None
        self._connection_info: Dict[str, ConnectionInfo] = {}
    
    # ==================== Logging ====================
    
    def get_logs(self, count: int = 50) -> List[dict]:
        """Get recent logs."""
        return self._log_manager.get_logs(count) if hasattr(self, '_log_manager') else []
    
    def clear_logs(self):
        """Clear all logs."""
        if hasattr(self, '_log_manager'):
            self._log_manager.clear()
    
    # ==================== Cache & Pool ====================
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics from database service."""
        try:
            return self._db_service.cache_stats
        except Exception:
            return {}
    
    async def clear_cache(self):
        """Clear all cached data."""
        await self._db_service.clear_cache()
        self._log("Cache cleared", "INFO")
    
    def get_pool_info(self) -> Optional[Dict[str, Any]]:
        """Get connection pool information."""
        if not self._active_connection:
            return None
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            return {
                "size": conn.pool_size,
                "idle": conn.pool_idle
            }
        except Exception:
            return None
