"""
Table operations for Multi-Database Manager.

This module provides:
- Table listing and schema retrieval
- Table creation and deletion
- Sample table generation
"""
from typing import Any, Dict, List, Optional
import random

from .models import LogManager
from .connection import ConnectionManager


class TableManager:
    """Manages table operations for multiple database types."""
    
    def __init__(self, connection_manager: ConnectionManager, log_manager: LogManager):
        self._connections = connection_manager
        self._log = log_manager.log
    
    async def list_tables(self, name: str = None) -> List[str]:
        """List all tables in the database."""
        conn_info = self._connections.get_connection(name)
        if not conn_info or not conn_info.connected:
            return []
        
        driver = conn_info.driver.lower()
        tables = []
        
        try:
            if driver == "sqlite":
                conn = await self._connections.get_connection_object(name)
                try:
                    cursor = await conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                    )
                    rows = await cursor.fetchall()
                    tables = [row[0] for row in rows]
                finally:
                    await conn.close()
            
            elif driver in ("postgresql", "postgres", "psql"):
                conn = await self._connections.get_connection_object(name)
                try:
                    rows = await conn.fetch(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' ORDER BY table_name"
                    )
                    tables = [row["table_name"] for row in rows]
                finally:
                    await conn.close()
            
            elif driver == "mysql":
                conn = await self._connections.get_connection_object(name)
                try:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema = %s ORDER BY table_name",
                            (conn_info.database,)
                        )
                        rows = await cur.fetchall()
                        tables = [row[0] for row in rows]
                finally:
                    conn.close()
            
            self._log(f"Listed {len(tables)} tables", "INFO")
            return tables
            
        except Exception as e:
            self._log(f"Error listing tables: {e}", "ERROR")
            return []
    
    async def get_table_schema(self, table_name: str, name: str = None) -> List[dict]:
        """Get the schema of a table."""
        conn_info = self._connections.get_connection(name)
        if not conn_info or not conn_info.connected:
            return []
        
        driver = conn_info.driver.lower()
        columns = []
        
        try:
            if driver == "sqlite":
                conn = await self._connections.get_connection_object(name)
                try:
                    cursor = await conn.execute(f"PRAGMA table_info({table_name})")
                    rows = await cursor.fetchall()
                    for row in rows:
                        columns.append({
                            "name": row[1],
                            "type": row[2],
                            "nullable": row[3] == 0,
                            "primary_key": row[5] == 1,
                            "default": row[4]
                        })
                finally:
                    await conn.close()
            
            elif driver in ("postgresql", "postgres", "psql"):
                conn = await self._connections.get_connection_object(name)
                try:
                    rows = await conn.fetch(
                        "SELECT column_name, data_type, is_nullable, column_default "
                        "FROM information_schema.columns "
                        "WHERE table_name = $1 ORDER BY ordinal_position",
                        table_name
                    )
                    for row in rows:
                        columns.append({
                            "name": row["column_name"],
                            "type": row["data_type"],
                            "nullable": row["is_nullable"] == "YES",
                            "primary_key": False,  # Would need additional query
                            "default": row["column_default"]
                        })
                finally:
                    await conn.close()
            
            elif driver == "mysql":
                conn = await self._connections.get_connection_object(name)
                try:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT column_name, data_type, is_nullable, column_default, column_key "
                            "FROM information_schema.columns "
                            "WHERE table_schema = %s AND table_name = %s "
                            "ORDER BY ordinal_position",
                            (conn_info.database, table_name)
                        )
                        rows = await cur.fetchall()
                        for row in rows:
                            columns.append({
                                "name": row[0],
                                "type": row[1],
                                "nullable": row[2] == "YES",
                                "primary_key": row[4] == "PRI",
                                "default": row[3]
                            })
                finally:
                    conn.close()
            
            return columns
            
        except Exception as e:
            self._log(f"Error getting table schema: {e}", "ERROR")
            return []
    
    async def create_table(
        self, 
        table_name: str, 
        columns: List[dict],
        name: str = None
    ) -> Dict[str, Any]:
        """Create a new table."""
        if not columns:
            return {"success": False, "error": "No columns defined"}
        
        conn_info = self._connections.get_connection(name)
        if not conn_info:
            return {"success": False, "error": "No connection"}
        
        # Build column definitions
        col_defs = []
        for col in columns:
            col_def = f"{col['name']} {col['type']}"
            if col.get('primary_key'):
                col_def += " PRIMARY KEY"
            if col.get('auto_increment'):
                col_def += " AUTOINCREMENT" if conn_info.driver == "sqlite" else " AUTO_INCREMENT"
            if not col.get('nullable', True):
                col_def += " NOT NULL"
            if col.get('default') is not None:
                col_def += f" DEFAULT '{col['default']}'"
            col_defs.append(col_def)
        
        sql = f"CREATE TABLE {table_name} ({', '.join(col_defs)})"
        result = await self._execute_sql(sql, name=name)
        
        if result["success"]:
            self._log(f"Table created: {table_name}", "INFO")
        else:
            self._log(f"Failed to create table: {result['error']}", "ERROR", table_name)
        
        return result
    
    async def drop_table(self, table_name: str, name: str = None) -> Dict[str, Any]:
        """Drop a table."""
        sql = f"DROP TABLE IF EXISTS {table_name}"
        result = await self._execute_sql(sql, name=name)
        
        if result["success"]:
            self._log(f"Table dropped: {table_name}", "INFO")
        else:
            self._log(f"Failed to drop table: {result['error']}", "ERROR", table_name)
        
        return result
    
    async def create_sample_tables(self, name: str = None) -> Dict[str, Any]:
        """Create sample tables with test data."""
        from datetime import datetime, timedelta
        results = []
        
        # Create customers table
        customers_columns = [
            {"name": "id", "type": "INTEGER", "primary_key": True, "auto_increment": True},
            {"name": "name", "type": "TEXT", "nullable": False},
            {"name": "email", "type": "TEXT", "nullable": False},
            {"name": "phone", "type": "TEXT"},
            {"name": "created_at", "type": "TEXT"}
        ]
        
        result = await self.create_table("customers", customers_columns, name)
        results.append({"table": "customers", "success": result["success"], "error": result.get("error")})
        
        # Create orders table
        orders_columns = [
            {"name": "id", "type": "INTEGER", "primary_key": True, "auto_increment": True},
            {"name": "customer_id", "type": "INTEGER", "nullable": False},
            {"name": "product_name", "type": "TEXT", "nullable": False},
            {"name": "quantity", "type": "INTEGER", "nullable": False},
            {"name": "price", "type": "REAL", "nullable": False},
            {"name": "order_date", "type": "TEXT"}
        ]
        
        result = await self.create_table("orders", orders_columns, name)
        results.append({"table": "orders", "success": result["success"], "error": result.get("error")})
        
        # Insert sample data
        if results[0]["success"]:
            # European names
            names = [
                "James", "Emma", "Liam", "Olivia", "Noah", "Sophia", 
                "William", "Isabella", "Oliver", "Mia", "Lucas", "Charlotte",
                "Henry", "Amelia", "Alexander"
            ]
            # European phone formats
            phone_prefixes = ["+44", "+33", "+49", "+39", "+34", "+31", "+46", "+32"]
            products = ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard", "Mouse", "Headset"]
            
            base_date = datetime.now()
            
            for i in range(30):
                prefix = random.choice(phone_prefixes)
                phone = f"{prefix} {random.randint(100, 999)} {random.randint(1000000, 9999999)}"
                created_date = base_date - timedelta(days=random.randint(0, 365))
                await self._insert_record("customers", {
                    "name": random.choice(names),
                    "email": f"user{i+1}@example.com",
                    "phone": phone,
                    "created_at": created_date.strftime("%Y-%m-%d %H:%M:%S")
                }, name)
            
            for i in range(30):
                order_date = base_date - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
                await self._insert_record("orders", {
                    "customer_id": random.randint(1, 30),
                    "product_name": random.choice(products),
                    "quantity": random.randint(1, 5),
                    "price": round(random.uniform(100, 1000), 2),
                    "order_date": order_date.strftime("%Y-%m-%d %H:%M:%S")
                }, name)
        
        self._log("Sample tables created with 30 records each", "INFO")
        return {"results": results}
    
    async def _execute_sql(self, sql: str, params: tuple = None, name: str = None) -> Dict[str, Any]:
        """Execute raw SQL (helper method)."""
        conn_info = self._connections.get_connection(name)
        if not conn_info or not conn_info.connected:
            return {"success": False, "error": "No connection", "rows": []}
        
        driver = conn_info.driver.lower()
        
        try:
            if driver == "sqlite":
                conn = await self._connections.get_connection_object(name)
                try:
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
                conn = await self._connections.get_connection_object(name)
                try:
                    async with conn.cursor() as cur:
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
    
    async def _insert_record(self, table: str, data: dict, name: str = None) -> Dict[str, Any]:
        """Insert a record (helper method for sample data)."""
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
        
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        return await self._execute_sql(sql, tuple(data.values()), name)