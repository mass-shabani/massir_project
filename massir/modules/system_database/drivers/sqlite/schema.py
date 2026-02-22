"""
SQLite schema manager implementation.
"""
from typing import Any, Dict, List, Optional

from ...core.schema import BaseSchemaManager
from ...core.types import (
    DatabaseType, TableDef, ColumnDef, IndexDef,
    ForeignKeyDef, QueryResult, TYPE_MAPPING, ColumnType
)
from ...core.exceptions import UnsupportedFeatureError
from .connection import SQLitePool


class SQLiteSchemaManager(BaseSchemaManager):
    """SQLite schema manager implementation."""
    
    def __init__(self, pool: SQLitePool):
        super().__init__(pool, DatabaseType.SQLITE)
        self._pool = pool
    
    def _column_to_sql(self, column: ColumnDef) -> str:
        """Convert column definition to SQL."""
        type_map = TYPE_MAPPING[DatabaseType.SQLITE]
        
        # Get column type
        if isinstance(column.type, ColumnType):
            col_type = type_map.get(column.type, "TEXT")
        else:
            col_type = column.type
        
        parts = [column.name, col_type]
        
        # Length for VARCHAR
        if column.length and column.type in (ColumnType.VARCHAR, ColumnType.CHAR):
            parts[1] = f"{col_type}({column.length})"
        
        # Constraints
        if column.primary_key:
            parts.append("PRIMARY KEY")
        if column.auto_increment:
            parts.append("AUTOINCREMENT")
        if not column.nullable and not column.primary_key:
            parts.append("NOT NULL")
        if column.unique and not column.primary_key:
            parts.append("UNIQUE")
        if column.default is not None:
            if isinstance(column.default, str):
                parts.append(f"DEFAULT '{column.default}'")
            else:
                parts.append(f"DEFAULT {column.default}")
        
        return " ".join(parts)
    
    async def create_table(self, table_def: TableDef) -> QueryResult:
        """Create a table."""
        columns_sql = []
        for col in table_def.columns:
            columns_sql.append(self._column_to_sql(col))
        
        # Add primary key constraint if composite
        if len(table_def.primary_key) > 1:
            pk_cols = ", ".join(table_def.primary_key)
            columns_sql.append(f"PRIMARY KEY ({pk_cols})")
        
        # Add foreign keys
        for fk in table_def.foreign_keys:
            fk_cols = ", ".join(fk.columns)
            ref_cols = ", ".join(fk.ref_columns)
            fk_sql = f"FOREIGN KEY ({fk_cols}) REFERENCES {fk.ref_table}({ref_cols})"
            if fk.on_delete:
                fk_sql += f" ON DELETE {fk.on_delete}"
            if fk.on_update:
                fk_sql += f" ON UPDATE {fk.on_update}"
            columns_sql.append(fk_sql)
        
        if_not_exists = "IF NOT EXISTS" if table_def.if_not_exists else ""
        sql = f"CREATE TABLE {if_not_exists} {table_def.name} ({', '.join(columns_sql)})"
        
        result = await self._pool.execute(sql)
        
        # Create indexes
        for idx in table_def.indexes:
            await self.create_index(table_def.name, idx)
        
        return result
    
    async def drop_table(
        self, 
        name: str, 
        if_exists: bool = True,
        cascade: bool = False
    ) -> QueryResult:
        """Drop a table."""
        if_exists_sql = "IF EXISTS" if if_exists else ""
        sql = f"DROP TABLE {if_exists_sql} {name}"
        return await self._pool.execute(sql)
    
    async def alter_table(
        self, 
        name: str, 
        alterations: List[Dict[str, Any]]
    ) -> QueryResult:
        """Alter table structure (limited in SQLite)."""
        # SQLite has limited ALTER TABLE support
        results = []
        for alt in alterations:
            action = alt.get("action")
            if action == "add_column":
                col = ColumnDef(**alt["column"])
                sql = f"ALTER TABLE {name} ADD COLUMN {self._column_to_sql(col)}"
                result = await self._pool.execute(sql)
                results.append(result)
            elif action == "rename_column":
                old_name = alt["old_name"]
                new_name = alt["new_name"]
                sql = f"ALTER TABLE {name} RENAME COLUMN {old_name} TO {new_name}"
                result = await self._pool.execute(sql)
                results.append(result)
            elif action == "drop_column":
                col_name = alt["column_name"]
                sql = f"ALTER TABLE {name} DROP COLUMN {col_name}"
                result = await self._pool.execute(sql)
                results.append(result)
            else:
                raise UnsupportedFeatureError(f"SQLite does not support ALTER TABLE {action}")
        
        return results[-1] if results else QueryResult(success=True)
    
    async def rename_table(
        self, 
        old_name: str, 
        new_name: str
    ) -> QueryResult:
        """Rename a table."""
        sql = f"ALTER TABLE {old_name} RENAME TO {new_name}"
        return await self._pool.execute(sql)
    
    async def table_exists(self, name: str) -> bool:
        """Check if table exists."""
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = await self._pool.fetch_one(sql, (name,))
        return result is not None
    
    async def get_table_schema(self, name: str) -> Optional[TableDef]:
        """Get table schema information."""
        if not await self.table_exists(name):
            return None
        
        # Get column info
        sql = f"PRAGMA table_info({name})"
        rows = await self._pool.fetch_all(sql)
        
        columns = []
        primary_key = []
        
        for row in rows:
            col = ColumnDef(
                name=row["name"],
                type=row["type"],
                nullable=row["notnull"] == 0,
                default=row["dflt_value"],
                primary_key=row["pk"] > 0
            )
            columns.append(col)
            if row["pk"] > 0:
                primary_key.append(row["name"])
        
        return TableDef(
            name=name,
            columns=columns,
            primary_key=primary_key
        )
    
    async def list_tables(self) -> List[str]:
        """List all tables."""
        sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        rows = await self._pool.fetch_all(sql)
        return [row["name"] for row in rows]
    
    async def create_index(
        self, 
        table: str, 
        index_def: IndexDef
    ) -> QueryResult:
        """Create an index."""
        unique = "UNIQUE" if index_def.unique else ""
        columns = ", ".join(index_def.columns)
        sql = f"CREATE {unique} INDEX IF NOT EXISTS {index_def.name} ON {table} ({columns})"
        return await self._pool.execute(sql)
    
    async def drop_index(
        self, 
        name: str, 
        table: Optional[str] = None
    ) -> QueryResult:
        """Drop an index."""
        sql = f"DROP INDEX IF EXISTS {name}"
        return await self._pool.execute(sql)
    
    async def index_exists(
        self, 
        name: str, 
        table: Optional[str] = None
    ) -> bool:
        """Check if index exists."""
        sql = "SELECT name FROM sqlite_master WHERE type='index' AND name=?"
        result = await self._pool.fetch_one(sql, (name,))
        return result is not None
    
    async def create_view(
        self, 
        name: str, 
        query: str,
        replace: bool = False
    ) -> QueryResult:
        """Create a view."""
        replace_sql = "OR REPLACE" if replace else ""
        sql = f"CREATE {replace_sql} VIEW {name} AS {query}"
        return await self._pool.execute(sql)
    
    async def drop_view(
        self, 
        name: str, 
        if_exists: bool = True
    ) -> QueryResult:
        """Drop a view."""
        if_exists_sql = "IF EXISTS" if if_exists else ""
        sql = f"DROP VIEW {if_exists_sql} {name}"
        return await self._pool.execute(sql)
    
    async def add_column(
        self, 
        table: str, 
        column: ColumnDef
    ) -> QueryResult:
        """Add a column to a table."""
        sql = f"ALTER TABLE {table} ADD COLUMN {self._column_to_sql(column)}"
        return await self._pool.execute(sql)
    
    async def drop_column(
        self, 
        table: str, 
        column_name: str
    ) -> QueryResult:
        """Drop a column from a table."""
        sql = f"ALTER TABLE {table} DROP COLUMN {column_name}"
        return await self._pool.execute(sql)
    
    async def add_foreign_key(
        self, 
        table: str, 
        fk: ForeignKeyDef
    ) -> QueryResult:
        """Add a foreign key constraint (requires table recreation in SQLite)."""
        raise UnsupportedFeatureError(
            "SQLite requires table recreation to add foreign keys. "
            "Consider recreating the table or defining FK at creation time."
        )
    
    async def drop_foreign_key(
        self, 
        table: str, 
        fk_name: str
    ) -> QueryResult:
        """Drop a foreign key constraint (requires table recreation in SQLite)."""
        raise UnsupportedFeatureError(
            "SQLite requires table recreation to drop foreign keys."
        )
    
    async def list_indexes(
        self, 
        table: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List indexes for a table or all tables."""
        indexes = []
        
        if table:
            query = "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND tbl_name = ?"
            rows = await self._pool.fetch_all(query, (table,))
        else:
            query = "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"
            rows = await self._pool.fetch_all(query)
        
        for row in rows:
            # Skip internal SQLite indexes
            if row["name"].startswith("sqlite_"):
                continue
            
            # Get index info
            try:
                info = await self._pool.fetch_all(f"PRAGMA index_info({row['name']})")
                columns = [i["name"] for i in info]
                
                # Check if unique
                index_info = await self._pool.fetch_one(f"PRAGMA index_info({row['name']})")
                unique = False
                # Get unique info from sql
                sql_row = await self._pool.fetch_one(
                    "SELECT sql FROM sqlite_master WHERE type='index' AND name = ?",
                    (row["name"],)
                )
                if sql_row and sql_row.get("sql"):
                    unique = "UNIQUE" in sql_row["sql"]
                
                indexes.append({
                    "name": row["name"],
                    "table": row["tbl_name"],
                    "columns": columns,
                    "unique": unique
                })
            except Exception:
                # Skip indexes we can't get info for
                pass
        
        return indexes
    
    async def list_foreign_keys(
        self, 
        table: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List foreign keys for a table or all tables."""
        fks = []
        
        # Get list of tables to check
        if table:
            tables = [table]
        else:
            tables = await self.list_tables()
        
        for tbl in tables:
            try:
                rows = await self._pool.fetch_all(f"PRAGMA foreign_key_list({tbl})")
                for row in rows:
                    fks.append({
                        "name": f"fk_{tbl}_{row['from']}",
                        "table": tbl,
                        "columns": [row["from"]],
                        "ref_table": row["table"],
                        "ref_columns": [row["to"]],
                        "on_delete": row.get("on_delete", "NO ACTION"),
                        "on_update": row.get("on_update", "NO ACTION")
                    })
            except Exception:
                pass
        
        return fks