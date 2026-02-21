"""
Data operations for Multi-Database Manager.

This module provides data-related operations:
- Get table data with pagination
- Insert record
- Update record
- Delete record
- Execute raw SQL
- Get database info
"""
from typing import Any, Dict, List


class DataMixin:
    """
    Mixin class for data management operations.
    
    Requires the following attributes:
    - _db_service: DatabaseService instance
    - _log: Logging function
    - _active_connection: Name of active connection
    - _connection_info: Dict of ConnectionInfo objects
    """
    
    async def get_table_data(
        self: "DataMixin", 
        table_name: str, 
        name: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get data from a table with pagination."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"rows": [], "total": 0, "error": "No connection"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            
            # Get total count
            total = await conn.count(table_name)
            
            # Get data
            rows = await conn.find_many(table_name, limit=limit, offset=offset)
            
            return {"rows": rows, "total": total, "error": None}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error getting table data: {error_msg}", "ERROR", table_name)
            return {"rows": [], "total": 0, "error": error_msg}
    
    async def insert_record(
        self: "DataMixin", 
        table_name: str, 
        data: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Insert a record."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            result = await self._db_service.get_connection(conn_name).insert(table_name, data)
            
            if result.success:
                self._log(f"Record inserted into {table_name}", "INFO")
                return {"success": True}
            else:
                self._log(f"Insert failed: {result.error}", "ERROR", table_name)
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Insert failed: {error_msg}", "ERROR", table_name)
            return {"success": False, "error": error_msg}
    
    async def update_record(
        self: "DataMixin", 
        table_name: str, 
        data: dict,
        where: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Update records."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            result = await self._db_service.get_connection(conn_name).update(table_name, data, where)
            
            if result.success:
                self._log(f"Record updated in {table_name}", "INFO")
                return {"success": True}
            else:
                self._log(f"Update failed: {result.error}", "ERROR", table_name)
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Update failed: {error_msg}", "ERROR", table_name)
            return {"success": False, "error": error_msg}
    
    async def delete_record(
        self: "DataMixin", 
        table_name: str, 
        where: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Delete records."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            result = await self._db_service.get_connection(conn_name).delete(table_name, where)
            
            if result.success:
                self._log(f"Record deleted from {table_name}", "INFO")
                return {"success": True}
            else:
                self._log(f"Delete failed: {result.error}", "ERROR", table_name)
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Delete failed: {error_msg}", "ERROR", table_name)
            return {"success": False, "error": error_msg}
    
    async def execute_sql(
        self: "DataMixin", 
        sql: str, 
        params: tuple = None,
        name: str = None
    ) -> Dict[str, Any]:
        """Execute raw SQL."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection", "rows": []}
        
        try:
            result = await self._db_service.get_connection(conn_name).execute(sql, params)
            
            if result.success:
                return {
                    "success": True, 
                    "rows": result.rows, 
                    "affected": result.affected_rows
                }
            else:
                self._log(f"SQL execution error: {result.error}", "ERROR", sql[:100])
                return {"success": False, "error": result.error, "rows": []}
        except Exception as e:
            error_msg = str(e)
            self._log(f"SQL execution error: {error_msg}", "ERROR", sql[:100])
            return {"success": False, "error": error_msg, "rows": []}
    
    async def get_database_info(self: "DataMixin", name: str = None) -> Dict[str, Any]:
        """Get database information and statistics."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"error": "No connection"}
        
        try:
            tables = await self.list_tables(conn_name)
            table_stats = []
            total_rows = 0
            
            for table in tables:
                count = await self._db_service.get_connection(conn_name).count(table)
                total_rows += count
                table_stats.append({
                    "name": table,
                    "rows": count
                })
            
            conn_info = self._connection_info.get(conn_name)
            
            return {
                "connection": conn_info.to_dict() if conn_info else {},
                "tables": table_stats,
                "total_tables": len(tables),
                "total_rows": total_rows
            }
        except Exception as e:
            self._log(f"Error getting database info: {e}", "ERROR")
            return {"error": str(e)}
