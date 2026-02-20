"""
Multi-Database Manager Service - Aggregator module.

This module provides a unified interface that aggregates:
- ConnectionManager: Database connection management
- TableManager: Table operations (create, drop, list, schema)
- DataManager: Data operations (CRUD, queries)
- LogManager: Operation logging

The MultiDatabaseManager class provides backward compatibility
with the original monolithic implementation.
"""
from typing import Any, Dict, List, Optional

from .models import ConnectionInfo, LogEntry, LogManager
from .connection import ConnectionManager
from .tables import TableManager
from .data import DataManager


class MultiDatabaseManager:
    """
    Manages multiple dynamic database connections.
    
    This class aggregates specialized managers to provide a unified
    interface for database operations across SQLite, PostgreSQL, and MySQL.
    
    Delegates to:
    - ConnectionManager: Connection testing, establishment, and lifecycle
    - TableManager: Table listing, schema, creation, and deletion
    - DataManager: Data retrieval, insertion, update, and deletion
    - LogManager: Operation logging and display
    """
    
    def __init__(self, logger=None, path_manager=None):
        # Initialize log manager first (used by other managers)
        self._log_manager = LogManager(logger)
        
        # Initialize specialized managers
        self._connection_manager = ConnectionManager(self._log_manager, path_manager)
        self._table_manager = TableManager(self._connection_manager, self._log_manager)
        self._data_manager = DataManager(self._connection_manager, self._log_manager)
        
        # Inject table_manager into data_manager to avoid circular import
        self._data_manager.set_table_manager(self._table_manager)
        
        # Keep reference to logger for compatibility
        self._logger = logger
    
    # --- Log Management (delegates to LogManager) ---
    
    def get_logs(self, limit: int = 50) -> List[dict]:
        """Get recent log entries."""
        return self._log_manager.get_logs(limit)
    
    def clear_logs(self):
        """Clear all logs."""
        self._log_manager.clear_logs()
    
    # --- Connection Management (delegates to ConnectionManager) ---
    
    async def test_connection(self, config: dict) -> Dict[str, Any]:
        """Test a database connection without persisting it."""
        return await self._connection_manager.test_connection(config)
    
    async def create_database(self, config: dict) -> Dict[str, Any]:
        """Create a new SQLite database."""
        return await self._connection_manager.create_database(config)
    
    async def connect(self, config: dict) -> Dict[str, Any]:
        """Create and establish a database connection."""
        return await self._connection_manager.connect(config)
    
    async def disconnect(self, name: str) -> Dict[str, Any]:
        """Disconnect a database connection."""
        return await self._connection_manager.disconnect(name)
    
    async def disconnect_all(self):
        """Disconnect all database connections."""
        await self._connection_manager.disconnect_all()
    
    def get_connections(self) -> List[dict]:
        """Get all connection info."""
        return self._connection_manager.get_connections()
    
    def get_connection(self, name: str = None) -> Optional[ConnectionInfo]:
        """Get a specific connection or the active one."""
        return self._connection_manager.get_connection(name)
    
    def get_active_connection_name(self) -> Optional[str]:
        """Get the name of the active connection."""
        return self._connection_manager.get_active_connection_name()
    
    def set_active_connection(self, name: str) -> bool:
        """Set the active connection."""
        return self._connection_manager.set_active_connection(name)
    
    def is_connected(self, name: str = None) -> bool:
        """Check if a connection is active."""
        return self._connection_manager.is_connected(name)
    
    # --- Table Management (delegates to TableManager) ---
    
    async def list_tables(self, name: str = None) -> List[str]:
        """List all tables in the database."""
        return await self._table_manager.list_tables(name)
    
    async def get_table_schema(self, table_name: str, name: str = None) -> List[dict]:
        """Get the schema of a table."""
        return await self._table_manager.get_table_schema(table_name, name)
    
    async def create_table(
        self, 
        table_name: str, 
        columns: List[dict],
        name: str = None
    ) -> Dict[str, Any]:
        """Create a new table."""
        return await self._table_manager.create_table(table_name, columns, name)
    
    async def drop_table(self, table_name: str, name: str = None) -> Dict[str, Any]:
        """Drop a table."""
        return await self._table_manager.drop_table(table_name, name)
    
    async def create_sample_tables(self, name: str = None) -> Dict[str, Any]:
        """Create sample tables with test data."""
        return await self._table_manager.create_sample_tables(name)
    
    # --- Data Management (delegates to DataManager) ---
    
    async def get_table_data(
        self, 
        table_name: str, 
        name: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get data from a table with pagination."""
        return await self._data_manager.get_table_data(table_name, name, limit, offset)
    
    async def execute_sql(
        self, 
        sql: str, 
        params: tuple = None,
        name: str = None
    ) -> Dict[str, Any]:
        """Execute raw SQL and return results."""
        return await self._data_manager.execute_sql(sql, params, name)
    
    async def insert_record(
        self, 
        table_name: str, 
        data: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Insert a record into a table."""
        return await self._data_manager.insert_record(table_name, data, name)
    
    async def update_record(
        self, 
        table_name: str, 
        data: dict,
        where: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Update records in a table."""
        return await self._data_manager.update_record(table_name, data, where, name)
    
    async def delete_record(
        self, 
        table_name: str, 
        where: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Delete records from a table."""
        return await self._data_manager.delete_record(table_name, where, name)
    
    async def get_database_info(self, name: str = None) -> Dict[str, Any]:
        """Get database information and statistics."""
        return await self._data_manager.get_database_info(name)
    
    # --- Manager Access (for advanced usage) ---
    
    @property
    def connections(self) -> ConnectionManager:
        """Access the connection manager directly."""
        return self._connection_manager
    
    @property
    def tables(self) -> TableManager:
        """Access the table manager directly."""
        return self._table_manager
    
    @property
    def data(self) -> DataManager:
        """Access the data manager directly."""
        return self._data_manager
    
    @property
    def logs(self) -> LogManager:
        """Access the log manager directly."""
        return self._log_manager
