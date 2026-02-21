"""
Multi-Database Manager using system_database.

This module provides a unified interface for multi-database operations
by leveraging the system_database module's capabilities.

The manager is composed of three mixins:
- ConnectionMixin: Connection management operations
- TableMixin: Table management operations
- DataMixin: Data CRUD operations
"""
from typing import Any, Dict, List, Optional

# Import from system_database
from massir.modules.system_database import DatabaseService

from .models import ConnectionInfo, LogManager
from .connection import ConnectionMixin
from .tables import TableMixin
from .data import DataMixin


class MultiDatabaseManager(ConnectionMixin, TableMixin, DataMixin):
    """
    Multi-database manager that uses system_database for all operations.
    
    This class combines three mixins to provide:
    - Dynamic connection management (ConnectionMixin)
    - Table operations: create, drop, list (TableMixin)
    - Data operations: CRUD (DataMixin)
    - Sample data generation (TableMixin)
    """
    
    def __init__(self, log_manager: LogManager, path_manager=None):
        """
        Initialize the multi-database manager.
        
        Args:
            log_manager: LogManager instance for logging operations
            path_manager: Optional path manager for resolving path placeholders
        """
        # Initialize DatabaseService
        self._db_service = DatabaseService()
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
