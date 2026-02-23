"""
Table operations service for Database Tables Module.

This module provides table-related operations:
- List tables
- Get table schema
- Create table
- Drop table
- Create sample tables with test data
"""
from typing import Any, Dict, List
from datetime import datetime, timedelta
import random


class TablesService:
    """
    Service for table management operations.
    
    Requires the following from connection_service:
    - get_database_service(): Returns the DatabaseService instance
    - get_database_types(): Returns database types dictionary
    - get_active_connection_name(): Returns the active connection name
    - is_connected(): Checks if there's an active connection
    - _log: Logging function
    """
    
    def __init__(self, connection_service):
        """
        Initialize the tables service.
        
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
    
    async def list_tables(self, name: str = None) -> List[str]:
        """List all tables."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return []
        
        try:
            tables = await self._db_service.get_connection(conn_name).list_tables()
            self._log(f"Listed {len(tables)} tables", "INFO")
            return tables
        except Exception as e:
            self._log(f"Error listing tables: {e}", "ERROR")
            return []
    
    async def get_table_schema(self, table_name: str, name: str = None) -> List[dict]:
        """Get table schema."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return []
        
        try:
            schema = await self._db_service.get_table_schema(table_name, conn_name)
            return schema
        except Exception as e:
            self._log(f"Error getting table schema: {e}", "ERROR")
            return []
    
    async def create_table(
        self, 
        table_name: str, 
        columns: List[dict],
        name: str = None
    ) -> Dict[str, Any]:
        """Create a table using unified TableDef."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            # Get types from context
            TableDef = self._db_types.get("TableDef")
            ColumnDef = self._db_types.get("ColumnDef")
            ColumnType = self._db_types.get("ColumnType")
            
            if not TableDef or not ColumnDef or not ColumnType:
                return {"success": False, "error": "Database types not available from context"}
            
            # Convert dict columns to ColumnDef
            col_defs = []
            for col in columns:
                col_type = col.get("type", "TEXT")
                # Convert string type to ColumnType if possible
                if isinstance(col_type, str):
                    type_map = {
                        "INTEGER": ColumnType.INTEGER,
                        "INT": ColumnType.INTEGER,
                        "TEXT": ColumnType.TEXT,
                        "VARCHAR": ColumnType.VARCHAR,
                        "REAL": ColumnType.FLOAT,
                        "FLOAT": ColumnType.FLOAT,
                        "DOUBLE": ColumnType.DOUBLE,
                        "DECIMAL": ColumnType.DECIMAL,
                        "BOOLEAN": ColumnType.BOOLEAN,
                        "DATE": ColumnType.DATE,
                        "TIME": ColumnType.TIME,
                        "DATETIME": ColumnType.DATETIME,
                        "TIMESTAMP": ColumnType.TIMESTAMP,
                        "BLOB": ColumnType.BLOB,
                    }
                    col_type = type_map.get(col_type.upper(), ColumnType.TEXT)
                
                col_def = ColumnDef(
                    name=col["name"],
                    type=col_type,
                    nullable=col.get("nullable", True),
                    primary_key=col.get("primary_key", False),
                    auto_increment=col.get("auto_increment", False),
                    unique=col.get("unique", False),
                    default=col.get("default"),
                    length=col.get("length"),
                    precision=col.get("precision"),
                    scale=col.get("scale"),
                )
                col_defs.append(col_def)
            
            # Create TableDef
            table_def = TableDef(
                name=table_name,
                columns=col_defs,
                if_not_exists=True
            )
            
            result = await self._db_service.get_connection(conn_name).create_table(table_def)
            
            if result.success:
                self._log(f"Table created: {table_name}", "INFO")
                return {"success": True}
            else:
                self._log(f"Failed to create table: {result.error}", "ERROR", table_name)
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error creating table: {error_msg}", "ERROR", table_name)
            return {"success": False, "error": error_msg}
    
    async def drop_table(self, table_name: str, name: str = None) -> Dict[str, Any]:
        """Drop a table."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            result = await self._db_service.get_connection(conn_name).drop_table(table_name)
            
            if result.success:
                self._log(f"Table dropped: {table_name}", "INFO")
                return {"success": True}
            else:
                self._log(f"Failed to drop table: {result.error}", "ERROR", table_name)
                return {"success": False, "error": result.error}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error dropping table: {error_msg}", "ERROR", table_name)
            return {"success": False, "error": error_msg}
    
    async def get_table_data(self, table_name: str, limit: int = 100, offset: int = 0, name: str = None) -> Dict[str, Any]:
        """Get data from a table."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"rows": [], "total": 0}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            rows = await conn.find_many(table_name, limit=limit, offset=offset)
            total = await conn.count(table_name)
            
            return {
                "rows": rows if rows else [],
                "total": total if total else len(rows if rows else [])
            }
        except Exception as e:
            self._log(f"Error getting table data: {e}", "ERROR")
            return {"rows": [], "total": 0}
    
    async def create_sample_tables(self, name: str = None) -> Dict[str, Any]:
        """Create sample tables with test data."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            # Create users table
            users_columns = [
                {"name": "id", "type": "INTEGER", "primary_key": True, "auto_increment": True},
                {"name": "username", "type": "TEXT", "nullable": False},
                {"name": "email", "type": "TEXT", "nullable": False},
                {"name": "created_at", "type": "TEXT"},
            ]
            
            result1 = await self.create_table("users", users_columns, conn_name)
            if not result1["success"]:
                return result1
            
            # Create posts table
            posts_columns = [
                {"name": "id", "type": "INTEGER", "primary_key": True, "auto_increment": True},
                {"name": "title", "type": "TEXT", "nullable": False},
                {"name": "content", "type": "TEXT"},
                {"name": "user_id", "type": "INTEGER"},
                {"name": "created_at", "type": "TEXT"},
            ]
            
            result2 = await self.create_table("posts", posts_columns, conn_name)
            if not result2["success"]:
                return result2
            
            # Insert sample data
            conn = self._db_service.get_connection(conn_name)
            
            # Sample users
            users = [
                {"username": f"user{i}", "email": f"user{i}@example.com", "created_at": datetime.now().isoformat()}
                for i in range(1, 11)
            ]
            
            for user in users:
                await conn.insert("users", user)
            
            # Sample posts
            posts = []
            for i in range(1, 21):
                posts.append({
                    "title": f"Post {i}",
                    "content": f"This is the content of post {i}. " + "Lorem ipsum " * random.randint(5, 20),
                    "user_id": random.randint(1, 10),
                    "created_at": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat()
                })
            
            for post in posts:
                await conn.insert("posts", post)
            
            self._log("Created sample tables with test data", "INFO")
            return {"success": True, "message": "Created users and posts tables with sample data"}
            
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error creating sample tables: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
