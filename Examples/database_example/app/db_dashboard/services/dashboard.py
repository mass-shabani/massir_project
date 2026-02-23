"""
Dashboard service for Database Dashboard Module.

This module provides dashboard-related operations:
- Get database statistics
- Get connection info
- Get cache statistics
"""
from typing import Any, Dict, List


class DashboardService:
    """
    Service for dashboard operations.
    
    Requires the following from connection_service:
    - get_database_service(): Returns the DatabaseService instance
    - get_active_connection_name(): Returns the active connection name
    - is_connected(): Checks if there's an active connection
    - get_connections(): Returns all connections info
    - get_cache_stats(): Returns cache statistics
    - get_pool_info(): Returns pool information
    """
    
    def __init__(self, connection_service):
        """
        Initialize the dashboard service.
        
        Args:
            connection_service: ConnectionService instance from db_connection module
        """
        self._connection = connection_service
        self._db_service = connection_service.get_database_service()
    
    @property
    def _active_connection(self):
        """Get active connection name."""
        return self._connection.get_active_connection_name()
    
    async def get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        if not self._active_connection:
            return {"connected": False}
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            tables = await conn.list_tables()
            
            return {
                "connected": True,
                "name": self._active_connection,
                "tables_count": len(tables),
                "tables": tables
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    async def get_table_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all tables."""
        if not self._active_connection:
            return []
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            tables = await conn.list_tables()
            stats = []
            
            for table in tables:
                try:
                    count = await conn.count(table)
                    stats.append({
                        "name": table,
                        "rows": count or 0
                    })
                except Exception:
                    stats.append({
                        "name": table,
                        "rows": 0
                    })
            
            return stats
        except Exception as e:
            return []
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information."""
        connections = self._connection.get_connections()
        active_name = self._connection.get_active_connection_name()
        
        return {
            "active": active_name,
            "connections": connections,
            "count": len(connections)
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._connection.get_cache_stats()
    
    def get_pool_info(self) -> Dict[str, Any]:
        """Get pool information."""
        return self._connection.get_pool_info() or {}
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all dashboard data."""
        db_info = await self.get_database_info()
        table_stats = await self.get_table_stats()
        conn_info = self.get_connection_info()
        cache_stats = self.get_cache_stats()
        pool_info = self.get_pool_info()
        
        return {
            "database": db_info,
            "tables": table_stats,
            "connections": conn_info,
            "cache": cache_stats,
            "pool": pool_info
        }
