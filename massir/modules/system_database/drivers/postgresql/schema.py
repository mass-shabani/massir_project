"""
PostgreSQL schema manager implementation.
"""
from typing import Any, Dict, List, Optional

from ...core.schema import BaseSchemaManager
from ...core.types import (
    DatabaseType, TableDef, ColumnDef, IndexDef,
    ForeignKeyDef, QueryResult, TYPE_MAPPING, ColumnType
)
from ...core.exceptions import UnsupportedFeatureError
from .connection import PostgreSQLPool


class PostgreSQLSchemaManager(BaseSchemaManager):
    """PostgreSQL schema manager implementation."""
    
    def __init__(self, pool: PostgreSQLPool):
        super().__init__(pool, DatabaseType.POSTGRESQL)
        self._pool = pool
    
    def _column_to_sql(self, column: ColumnDef) -> str:
        """Convert column definition to SQL."""
        type_map = TYPE_MAPPING[DatabaseType.POSTGRESQL]
        
        # Get column type
        if isinstance(column.type, ColumnType):
            col_type = type_map.get(column.type, "TEXT")
        else:
            col_type = column.type
        
        parts = [column.name, col_type]
        
        # Length for VARCHAR
        if column.length and column.type in (ColumnType.VARCHAR, ColumnType.CHAR):
            parts[1] = f"{col_type}({column.length})"
        
        # Precision and scale for DECIMAL
        if column.type == ColumnType.DECIMAL and column.precision:
            scale = column.scale or 0
            parts[1] = f"DECIMAL({column.precision}, {scale})"
        
        # Constraints
        if column.primary_key:
            parts.append("PRIMARY KEY")
        if column.auto_increment:
            parts[1] = "SERIAL"  # PostgreSQL uses SERIAL for auto-increment
        if not column.nullable and not column.primary_key:
            parts.append("NOT NULL")
        if column.unique and not column.primary_key:
            parts.append("UNIQUE")
        if column.default is not None:
            if isinstance(column.default, str):
                parts.append(f"DEFAULT '{column.default}'")
            elif isinstance(column.default, bool):
                parts.append(f"DEFAULT {str(column.default).upper()}")
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
            fk_name = fk.name or f"fk_{table_def.name}_{'_'.join(fk.columns)}"
            fk_sql = f"CONSTRAINT {fk_name} FOREIGN KEY ({fk_cols}) REFERENCES {fk.ref_table}({ref_cols})"
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
        
        # Add comment if provided
        if table_def.comment:
            await self._pool.execute(
                f"COMMENT ON TABLE {table_def.name} IS '{table_def.comment}'"
            )
        
        return result
    
    async def drop_table(
        self, 
        name: str, 
        if_exists: bool = True,
        cascade: bool = False
    ) -> QueryResult:
        """Drop a table."""
        if_exists_sql = "IF EXISTS" if if_exists else ""
        cascade_sql = "CASCADE" if cascade else ""
        sql = f"DROP TABLE {if_exists_sql} {name} {cascade_sql}".strip()
        return await self._pool.execute(sql)
    
    async def alter_table(
        self, 
        name: str, 
        alterations: List[Dict[str, Any]]
    ) -> QueryResult:
        """Alter table structure."""
        results = []
        for alt in alterations:
            action = alt.get("action")
            
            if action == "add_column":
                col = ColumnDef(**alt["column"])
                sql = f"ALTER TABLE {name} ADD COLUMN {self._column_to_sql(col)}"
                result = await self._pool.execute(sql)
                results.append(result)
            
            elif action == "drop_column":
                col_name = alt["column_name"]
                sql = f"ALTER TABLE {name} DROP COLUMN {col_name}"
                result = await self._pool.execute(sql)
                results.append(result)
            
            elif action == "alter_column":
                col_name = alt["column_name"]
                changes = alt.get("changes", {})
                
                if "type" in changes:
                    new_type = changes["type"]
                    using = changes.get("using", f"{col_name}::{new_type}")
                    sql = f"ALTER TABLE {name} ALTER COLUMN {col_name} TYPE {new_type} USING {using}"
                    result = await self._pool.execute(sql)
                    results.append(result)
                
                if "nullable" in changes:
                    if changes["nullable"]:
                        sql = f"ALTER TABLE {name} ALTER COLUMN {col_name} DROP NOT NULL"
                    else:
                        sql = f"ALTER TABLE {name} ALTER COLUMN {col_name} SET NOT NULL"
                    result = await self._pool.execute(sql)
                    results.append(result)
                
                if "default" in changes:
                    if changes["default"] is None:
                        sql = f"ALTER TABLE {name} ALTER COLUMN {col_name} DROP DEFAULT"
                    else:
                        sql = f"ALTER TABLE {name} ALTER COLUMN {col_name} SET DEFAULT {changes['default']}"
                    result = await self._pool.execute(sql)
                    results.append(result)
            
            elif action == "rename_column":
                old_name = alt["old_name"]
                new_name = alt["new_name"]
                sql = f"ALTER TABLE {name} RENAME COLUMN {old_name} TO {new_name}"
                result = await self._pool.execute(sql)
                results.append(result)
            
            else:
                raise UnsupportedFeatureError(f"Unsupported ALTER TABLE action: {action}")
        
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
        sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = $1
            )
        """
        result = await self._pool.fetch_value(sql, (name,))
        return result is True
    
    async def get_table_schema(self, name: str) -> Optional[TableDef]:
        """Get table schema information."""
        if not await self.table_exists(name):
            return None
        
        # Get column info
        sql = """
            SELECT column_name, data_type, is_nullable, column_default,
                   character_maximum_length, numeric_precision, numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
        """
        rows = await self._pool.fetch_all(sql, (name,))
        
        columns = []
        primary_key = []
        
        for row in rows:
            col_type = row["data_type"].upper()
            if row["character_maximum_length"]:
                col_type = f"VARCHAR({row['character_maximum_length']})"
            
            col = ColumnDef(
                name=row["column_name"],
                type=col_type,
                nullable=row["is_nullable"] == "YES",
                default=row["column_default"],
                primary_key=False  # Will be updated below
            )
            columns.append(col)
        
        # Get primary key columns
        pk_sql = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary
        """
        pk_rows = await self._pool.fetch_all(pk_sql, (name,))
        primary_key = [row["attname"] for row in pk_rows]
        
        # Mark primary key columns
        for col in columns:
            if col.name in primary_key:
                col.primary_key = True
                col.nullable = False
        
        return TableDef(
            name=name,
            columns=columns,
            primary_key=primary_key
        )
    
    async def list_tables(self) -> List[str]:
        """List all tables."""
        sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        rows = await self._pool.fetch_all(sql)
        return [row["table_name"] for row in rows]
    
    async def create_index(
        self, 
        table: str, 
        index_def: IndexDef
    ) -> QueryResult:
        """Create an index."""
        unique = "UNIQUE" if index_def.unique else ""
        
        # Handle index type
        type_sql = ""
        if index_def.type:
            type_map = {
                "btree": "btree",
                "hash": "hash",
                "gin": "gin",
                "gist": "gist"
            }
            type_sql = f"USING {type_map.get(index_def.type.value, 'btree')}"
        
        columns = ", ".join(index_def.columns)
        sql = f"CREATE {unique} INDEX IF NOT EXISTS {index_def.name} ON {table} {type_sql} ({columns})"
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
        sql = """
            SELECT EXISTS (
                SELECT FROM pg_indexes 
                WHERE indexname = $1
            )
        """
        result = await self._pool.fetch_value(sql, (name,))
        return result is True
    
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
        """Add a foreign key constraint."""
        fk_cols = ", ".join(fk.columns)
        ref_cols = ", ".join(fk.ref_columns)
        fk_name = fk.name or f"fk_{table}_{'_'.join(fk.columns)}"
        
        sql = f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} FOREIGN KEY ({fk_cols}) REFERENCES {fk.ref_table}({ref_cols})"
        if fk.on_delete:
            sql += f" ON DELETE {fk.on_delete}"
        if fk.on_update:
            sql += f" ON UPDATE {fk.on_update}"
        
        return await self._pool.execute(sql)
    
    async def drop_foreign_key(
        self, 
        table: str, 
        fk_name: str
    ) -> QueryResult:
        """Drop a foreign key constraint."""
        sql = f"ALTER TABLE {table} DROP CONSTRAINT {fk_name}"
        return await self._pool.execute(sql)