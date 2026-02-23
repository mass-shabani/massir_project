"""
Data operations service for Database Data Editor Module.

This module provides data-related operations:
- Get table data with pagination
- Insert records
- Update records
- Delete records
- Get table schema for form generation
"""
from typing import Any, Dict, List, Optional


class DataEditorService:
    """
    Service for data editing operations.
    
    Requires the following from connection_service:
    - get_database_service(): Returns the DatabaseService instance
    - get_database_types(): Returns database types dictionary
    - get_active_connection_name(): Returns the active connection name
    - is_connected(): Checks if there's an active connection
    - _log: Logging function
    """
    
    def __init__(self, connection_service):
        """
        Initialize the data editor service.
        
        Args:
            connection_service: ConnectionService instance from db_connection module
        """
        self._connection = connection_service
        self._db_service = connection_service.get_database_service()
        self._db_types = connection_service.get_database_types()
        self._log = connection_service._log
    
    @property
    def _active_connection(self):
        """Get active connection name."""
        return self._connection.get_active_connection_name()
    
    async def list_tables(self) -> List[str]:
        """List all tables."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return []
        
        try:
            tables = await self._db_service.get_connection(conn_name).list_tables()
            return tables
        except Exception as e:
            self._log(f"Error listing tables: {e}", "ERROR")
            return []
    
    async def get_table_schema(self, table_name: str) -> List[dict]:
        """Get table schema for form generation."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return []
        
        try:
            schema = await self._db_service.get_table_schema(table_name, conn_name)
            return schema
        except Exception as e:
            self._log(f"Error getting table schema: {e}", "ERROR")
            return []
    
    async def get_table_data(
        self, 
        table_name: str, 
        limit: int = 100, 
        offset: int = 0,
        order_by: str = None,
        order_dir: str = "ASC"
    ) -> Dict[str, Any]:
        """Get data from a table with pagination."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"rows": [], "total": 0}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            
            # Get total count
            total = await conn.count(table_name)
            
            # Get rows with pagination
            order_by_list = [f"{order_by} {order_dir}"] if order_by else None
            rows = await conn.find_many(
                table_name, 
                limit=limit, 
                offset=offset,
                order_by=order_by_list
            )
            
            return {
                "rows": rows,
                "total": total
            }
        except Exception as e:
            self._log(f"Error getting table data: {e}", "ERROR")
            return {"rows": [], "total": 0}
    
    async def get_record(self, table_name: str, record_id: int, pk_column: str = "id") -> Optional[Dict[str, Any]]:
        """Get a single record by ID."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return None
        
        try:
            conn = self._db_service.get_connection(conn_name)
            result = await conn.find_one(
                table_name,
                where={pk_column: record_id}
            )
            
            return result
        except Exception as e:
            self._log(f"Error getting record: {e}", "ERROR")
            return None
    
    async def insert_record(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new record."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            result = await conn.insert(table_name, data)
            
            if result.success:
                self._log(f"Inserted record into {table_name}", "INFO")
                return {"success": True, "id": result.last_insert_id}
            else:
                self._log(f"Failed to insert record: {result.error}", "ERROR")
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error inserting record: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
    
    async def update_record(
        self, 
        table_name: str, 
        record_id: int, 
        data: Dict[str, Any],
        pk_column: str = "id"
    ) -> Dict[str, Any]:
        """Update a record."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            result = await conn.update(
                table_name, 
                data,
                where={pk_column: record_id}
            )
            
            if result.success:
                self._log(f"Updated record {record_id} in {table_name}", "INFO")
                return {"success": True}
            else:
                self._log(f"Failed to update record: {result.error}", "ERROR")
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error updating record: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
    
    async def delete_record(self, table_name: str, record_id: int, pk_column: str = "id") -> Dict[str, Any]:
        """Delete a record."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            result = await conn.delete(
                table_name,
                where={pk_column: record_id}
            )
            
            if result.success:
                self._log(f"Deleted record {record_id} from {table_name}", "INFO")
                return {"success": True}
            else:
                self._log(f"Failed to delete record: {result.error}", "ERROR")
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error deleting record: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
    
    async def delete_records(self, table_name: str, record_ids: List[int], pk_column: str = "id") -> Dict[str, Any]:
        """Delete multiple records."""
        conn_name = self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            # Delete one by one since the API doesn't support IN clause directly
            deleted_count = 0
            for record_id in record_ids:
                result = await conn.delete(
                    table_name,
                    where={pk_column: record_id}
                )
                if result.success:
                    deleted_count += 1
            
            self._log(f"Deleted {deleted_count} records from {table_name}", "INFO")
            return {"success": True, "deleted": deleted_count}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error deleting records: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
