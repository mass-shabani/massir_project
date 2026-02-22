"""
Schema management for Multi-Database Manager.

This module provides schema-related operations:
- Index management
- Foreign key management
- Advanced table operations

Uses system_database's unified interface for database operations.
"""
from typing import Any, Dict, List, Optional


class SchemaMixin:
    """
    Mixin class for schema management operations.
    
    Requires the following attributes:
    - _db_service: DatabaseService instance
    - _db_types: Dictionary of database types from context
    - _log: Logging function
    - _active_connection: Name of active connection
    """
    
    async def list_indexes(self: "SchemaMixin", table_name: str = None) -> List[Dict[str, Any]]:
        """List indexes for a table or all tables using system_database."""
        if not self._active_connection:
            return []
        
        try:
            return await self._db_service.list_indexes(table_name, self._active_connection)
        except Exception as e:
            self._log(f"Failed to list indexes: {e}", "ERROR")
            return []
    
    async def create_index(
        self: "SchemaMixin",
        table_name: str,
        index_name: str,
        columns: List[str],
        unique: bool = False,
        index_type: str = "btree"
    ) -> Dict[str, Any]:
        """Create an index on a table using system_database."""
        if not self._active_connection:
            return {"success": False, "message": "No active connection"}
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            
            # Get types from context
            IndexDef = self._db_types.get("IndexDef")
            IndexType = self._db_types.get("IndexType")
            
            if not IndexDef or not IndexType:
                return {"success": False, "message": "Database types not available from context"}
            
            # Create IndexDef and use schema manager
            index_def = IndexDef(
                name=index_name,
                columns=columns,
                unique=unique,
                type=IndexType(index_type) if index_type in ("btree", "hash", "gin", "gist") else IndexType.BTREE
            )
            
            await conn._schema.create_index(table_name, index_def)
            
            self._log(f"Index '{index_name}' created on {table_name}({', '.join(columns)})", "INFO")
            
            return {
                "success": True,
                "message": f"Index '{index_name}' created successfully"
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to create index: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def drop_index(self: "SchemaMixin", index_name: str, table_name: str = None) -> Dict[str, Any]:
        """Drop an index using system_database."""
        if not self._active_connection:
            return {"success": False, "message": "No active connection"}
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            await conn._schema.drop_index(index_name, table_name)
            
            self._log(f"Index '{index_name}' dropped", "INFO")
            
            return {
                "success": True,
                "message": f"Index '{index_name}' dropped successfully"
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to drop index: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def list_foreign_keys(self: "SchemaMixin", table_name: str = None) -> List[Dict[str, Any]]:
        """List foreign keys for a table using system_database."""
        if not self._active_connection:
            return []
        
        try:
            return await self._db_service.list_foreign_keys(table_name, self._active_connection)
        except Exception as e:
            self._log(f"Failed to list foreign keys: {e}", "ERROR")
            return []
    
    async def add_foreign_key(
        self: "SchemaMixin",
        table_name: str,
        columns: List[str],
        ref_table: str,
        ref_columns: List[str],
        fk_name: str = None,
        on_delete: str = "RESTRICT",
        on_update: str = "RESTRICT"
    ) -> Dict[str, Any]:
        """Add a foreign key constraint to a table using system_database."""
        if not self._active_connection:
            return {"success": False, "message": "No active connection"}
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            
            # Get types from context
            ForeignKeyDef = self._db_types.get("ForeignKeyDef")
            
            if not ForeignKeyDef:
                return {"success": False, "message": "Database types not available from context"}
            
            # Create ForeignKeyDef and use schema manager
            fk_def = ForeignKeyDef(
                name=fk_name or f"fk_{table_name}_{'_'.join(columns)}",
                columns=columns,
                ref_table=ref_table,
                ref_columns=ref_columns,
                on_delete=on_delete,
                on_update=on_update
            )
            
            await conn._schema.add_foreign_key(table_name, fk_def)
            
            self._log(f"Foreign key '{fk_def.name}' added to {table_name}", "INFO")
            
            return {
                "success": True,
                "message": f"Foreign key '{fk_def.name}' added successfully"
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to add foreign key: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def drop_foreign_key(self: "SchemaMixin", fk_name: str, table_name: str) -> Dict[str, Any]:
        """Drop a foreign key constraint using system_database."""
        if not self._active_connection:
            return {"success": False, "message": "No active connection"}
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            await conn._schema.drop_foreign_key(table_name, fk_name)
            
            self._log(f"Foreign key '{fk_name}' dropped", "INFO")
            
            return {
                "success": True,
                "message": f"Foreign key '{fk_name}' dropped successfully"
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to drop foreign key: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
