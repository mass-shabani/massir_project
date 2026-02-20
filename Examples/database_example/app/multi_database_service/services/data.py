"""
Data operations for Multi-Database Manager.

This module provides:
- Table data retrieval with pagination
- Record CRUD operations (insert, update, delete)
- Database information and statistics
"""
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .models import LogManager
from .connection import ConnectionManager

if TYPE_CHECKING:
    from .tables import TableManager


class DataManager:
    """Manages data operations for multiple database types."""
    
    def __init__(
        self, 
        connection_manager: ConnectionManager, 
        log_manager: LogManager,
        table_manager: 'TableManager' = None
    ):
        self._connections = connection_manager
        self._log = log_manager.log
        self._table_manager = table_manager
    
    def set_table_manager(self, table_manager: 'TableManager'):
        """Set the table manager (to avoid circular import)."""
        self._table_manager = table_manager
    
    async def get_table_data(
        self, 
        table_name: str, 
        name: str = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get data from a table with pagination."""
        conn_info = self._connections.get_connection(name)
        if not conn_info or not conn_info.connected:
            return {"rows": [], "total": 0, "error": "No connection"}
        
        driver = conn_info.driver.lower()
        
        try:
            if driver == "sqlite":
                conn = await self._connections.get_connection_object(name)
                try:
                    # Get total count (without row_factory for simple tuple access)
                    cursor = await conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row = await cursor.fetchone()
                    total = row[0] if row else 0
                    
                    # Set row_factory for dict results
                    conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
                    
                    # Get data
                    cursor = await conn.execute(
                        f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
                        (limit, offset)
                    )
                    rows = await cursor.fetchall()
                    
                    return {"rows": rows, "total": total, "error": None}
                finally:
                    await conn.close()
            
            elif driver in ("postgresql", "postgres", "psql"):
                conn = await self._connections.get_connection_object(name)
                try:
                    # Get total count
                    total = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                    
                    # Get data
                    rows = await conn.fetch(
                        f"SELECT * FROM {table_name} LIMIT $1 OFFSET $2",
                        limit, offset
                    )
                    
                    return {"rows": [dict(r) for r in rows], "total": total, "error": None}
                finally:
                    await conn.close()
            
            elif driver == "mysql":
                import aiomysql
                conn = await self._connections.get_connection_object(name)
                try:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        # Get total count
                        await cur.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
                        total = (await cur.fetchone())["cnt"]
                        
                        # Get data
                        await cur.execute(
                            f"SELECT * FROM {table_name} LIMIT %s OFFSET %s",
                            (limit, offset)
                        )
                        rows = await cur.fetchall()
                    
                    return {"rows": rows, "total": total, "error": None}
                finally:
                    conn.close()
            
        except Exception as e:
            error_msg = str(e)
            self._log(f"Error getting table data: {error_msg}", "ERROR", table_name)
            return {"rows": [], "total": 0, "error": error_msg}
    
    async def execute_sql(
        self, 
        sql: str, 
        params: tuple = None,
        name: str = None
    ) -> Dict[str, Any]:
        """Execute raw SQL and return results."""
        conn_info = self._connections.get_connection(name)
        if not conn_info or not conn_info.connected:
            return {"success": False, "error": "No connection", "rows": []}
        
        driver = conn_info.driver.lower()
        
        try:
            if driver == "sqlite":
                conn = await self._connections.get_connection_object(name)
                try:
                    conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
                    
                    cursor = await conn.execute(sql, params or ())
                    if sql.strip().upper().startswith(("SELECT", "PRAGMA", "EXPLAIN")):
                        rows = await cursor.fetchall()
                        return {"success": True, "rows": rows, "affected": 0}
                    else:
                        await conn.commit()
                        return {"success": True, "rows": [], "affected": cursor.rowcount}
                finally:
                    await conn.close()
            
            elif driver in ("postgresql", "postgres", "psql"):
                conn = await self._connections.get_connection_object(name)
                try:
                    if sql.strip().upper().startswith("SELECT"):
                        rows = await conn.fetch(sql, *(params or ()))
                        return {"success": True, "rows": [dict(r) for r in rows], "affected": 0}
                    else:
                        result = await conn.execute(sql, *(params or ()))
                        return {"success": True, "rows": [], "affected": result.split()[-1] if result else 0}
                finally:
                    await conn.close()
            
            elif driver == "mysql":
                import aiomysql
                conn = await self._connections.get_connection_object(name)
                try:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        await cur.execute(sql, params)
                        if sql.strip().upper().startswith("SELECT"):
                            rows = await cur.fetchall()
                            return {"success": True, "rows": rows, "affected": 0}
                        else:
                            await conn.commit()
                            return {"success": True, "rows": [], "affected": cur.rowcount}
                finally:
                    conn.close()
            
        except Exception as e:
            error_msg = str(e)
            self._log(f"SQL execution error: {error_msg}", "ERROR", sql[:100])
            return {"success": False, "error": error_msg, "rows": []}
    
    async def insert_record(
        self, 
        table_name: str, 
        data: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Insert a record into a table."""
        conn_info = self._connections.get_connection(name)
        if not conn_info:
            return {"success": False, "error": "No connection"}
        
        driver = conn_info.driver.lower()
        columns = list(data.keys())
        
        if driver == "sqlite":
            placeholders = ", ".join(["?"] * len(columns))
        elif driver in ("postgresql", "postgres", "psql"):
            placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
        else:
            placeholders = ", ".join(["%s"] * len(columns))
        
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        result = await self.execute_sql(sql, tuple(data.values()), name)
        
        if result["success"]:
            self._log(f"Record inserted into {table_name}", "INFO")
        else:
            self._log(f"Insert failed: {result['error']}", "ERROR", table_name)
        
        return result
    
    async def update_record(
        self, 
        table_name: str, 
        data: dict,
        where: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Update records in a table."""
        conn_info = self._connections.get_connection(name)
        if not conn_info:
            return {"success": False, "error": "No connection"}
        
        driver = conn_info.driver.lower()
        
        set_clauses = []
        values = []
        
        if driver == "sqlite":
            for col, val in data.items():
                set_clauses.append(f"{col} = ?")
                values.append(val)
            where_clauses = []
            for col, val in where.items():
                where_clauses.append(f"{col} = ?")
                values.append(val)
        
        elif driver in ("postgresql", "postgres", "psql"):
            # Use $1, $2, etc. for PostgreSQL
            set_clauses = [f"{col} = ${i+1}" for i, col in enumerate(data.keys())]
            where_clauses = [f"{col} = ${i+len(data)+1}" for i, col in enumerate(where.keys())]
            values = list(data.values()) + list(where.values())
        
        else:  # MySQL
            for col, val in data.items():
                set_clauses.append(f"{col} = %s")
                values.append(val)
            where_clauses = []
            for col, val in where.items():
                where_clauses.append(f"{col} = %s")
                values.append(val)
        
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {' AND '.join(where_clauses)}"
        result = await self.execute_sql(sql, tuple(values), name)
        
        if result["success"]:
            self._log(f"Record updated in {table_name}", "INFO")
        else:
            self._log(f"Update failed: {result['error']}", "ERROR", table_name)
        
        return result
    
    async def delete_record(
        self, 
        table_name: str, 
        where: dict,
        name: str = None
    ) -> Dict[str, Any]:
        """Delete records from a table."""
        conn_info = self._connections.get_connection(name)
        if not conn_info:
            return {"success": False, "error": "No connection"}
        
        driver = conn_info.driver.lower()
        
        where_clauses = []
        values = []
        
        if driver == "sqlite":
            for col, val in where.items():
                where_clauses.append(f"{col} = ?")
                values.append(val)
        
        elif driver in ("postgresql", "postgres", "psql"):
            where_clauses = [f"{col} = ${i+1}" for i, col in enumerate(where.keys())]
            values = list(where.values())
        
        else:  # MySQL
            for col, val in where.items():
                where_clauses.append(f"{col} = %s")
                values.append(val)
        
        sql = f"DELETE FROM {table_name} WHERE {' AND '.join(where_clauses)}"
        result = await self.execute_sql(sql, tuple(values), name)
        
        if result["success"]:
            self._log(f"Record deleted from {table_name}", "INFO")
        else:
            self._log(f"Delete failed: {result['error']}", "ERROR", table_name)
        
        return result
    
    async def get_database_info(self, name: str = None) -> Dict[str, Any]:
        """Get database information and statistics."""
        conn_info = self._connections.get_connection(name)
        if not conn_info or not conn_info.connected:
            return {"error": "No connection"}
        
        # Use injected table_manager
        if self._table_manager is None:
            return {"error": "Table manager not initialized"}
        
        tables = await self._table_manager.list_tables(name)
        table_stats = []
        total_rows = 0
        
        for table in tables:
            data = await self.get_table_data(table, name, limit=1)
            count = data.get("total", 0)
            total_rows += count
            table_stats.append({
                "name": table,
                "rows": count
            })
        
        return {
            "connection": conn_info.to_dict(),
            "tables": table_stats,
            "total_tables": len(tables),
            "total_rows": total_rows
        }
