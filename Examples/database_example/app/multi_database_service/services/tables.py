"""
Table operations for Multi-Database Manager.

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


class TableMixin:
    """
    Mixin class for table management operations.
    
    Requires the following attributes:
    - _db_service: DatabaseService instance
    - _db_types: Dictionary of database types from context
    - _log: Logging function
    - _active_connection: Name of active connection
    """
    
    async def list_tables(self: "TableMixin", name: str = None) -> List[str]:
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
    
    async def get_table_schema(self: "TableMixin", table_name: str, name: str = None) -> List[dict]:
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
        self: "TableMixin", 
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
    
    async def drop_table(self: "TableMixin", table_name: str, name: str = None) -> Dict[str, Any]:
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
    
    async def create_sample_tables(self: "TableMixin", name: str = None) -> Dict[str, Any]:
        """Create sample tables with test data."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"results": [], "error": "No connection"}
        
        results = []
        
        # Create customers table
        customers_columns = [
            {"name": "id", "type": "INTEGER", "primary_key": True, "auto_increment": True},
            {"name": "name", "type": "VARCHAR", "nullable": False, "length": 255},
            {"name": "email", "type": "VARCHAR", "nullable": False, "length": 255},
            {"name": "phone", "type": "VARCHAR", "length": 50},
            {"name": "created_at", "type": "TIMESTAMP"}
        ]
        
        result = await self.create_table("customers", customers_columns, conn_name)
        results.append({"table": "customers", "success": result["success"], "error": result.get("error")})
        
        # Create orders table
        orders_columns = [
            {"name": "id", "type": "INTEGER", "primary_key": True, "auto_increment": True},
            {"name": "customer_id", "type": "INTEGER", "nullable": False},
            {"name": "product_name", "type": "VARCHAR", "nullable": False, "length": 255},
            {"name": "quantity", "type": "INTEGER", "nullable": False},
            {"name": "price", "type": "DECIMAL", "nullable": False, "precision": 10, "scale": 2},
            {"name": "order_date", "type": "TIMESTAMP"}
        ]
        
        result = await self.create_table("orders", orders_columns, conn_name)
        results.append({"table": "orders", "success": result["success"], "error": result.get("error")})
        
        # Insert sample data if tables created successfully
        if results[0]["success"]:
            # European names
            names = [
                "James", "Emma", "Liam", "Olivia", "Noah", "Sophia", 
                "William", "Isabella", "Oliver", "Mia", "Lucas", "Charlotte",
                "Henry", "Amelia", "Alexander"
            ]
            phone_prefixes = ["+44", "+33", "+49", "+39", "+34", "+31", "+46", "+32"]
            products = ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard", "Mouse", "Headset"]
            
            base_date = datetime.now()
            
            for i in range(30):
                prefix = random.choice(phone_prefixes)
                phone = f"{prefix} {random.randint(100, 999)} {random.randint(1000000, 9999999)}"
                created_date = base_date - timedelta(days=random.randint(0, 365))
                
                await self.insert_record("customers", {
                    "name": random.choice(names),
                    "email": f"user{i+1}@example.com",
                    "phone": phone,
                    "created_at": created_date
                }, conn_name)
            
            for i in range(30):
                order_date = base_date - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))
                
                await self.insert_record("orders", {
                    "customer_id": random.randint(1, 30),
                    "product_name": random.choice(products),
                    "quantity": random.randint(1, 5),
                    "price": round(random.uniform(100, 1000), 2),
                    "order_date": order_date
                }, conn_name)
        
        self._log("Sample tables created with 30 records each", "INFO")
        return {"results": results}
