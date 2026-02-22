"""
MySQL schema manager implementation.
"""
from typing import Any, Dict, List, Optional

from ...core.schema import BaseSchemaManager
from ...core.types import (
    DatabaseType, TableDef, ColumnDef, IndexDef,
    ForeignKeyDef, QueryResult, TYPE_MAPPING, ColumnType
)
from ...core.exceptions import UnsupportedFeatureError, QueryError
from .connection import MySQLPool


class MySQLSchemaManager(BaseSchemaManager):
    """MySQL schema manager implementation."""
    
    def __init__(self, pool: MySQLPool):
        super().__init__(pool, DatabaseType.MYSQL)
        self._pool = pool
    
    def _column_to_sql(self, column: ColumnDef) -> str:
        """Convert column definition to SQL."""
        type_map = TYPE_MAPPING[DatabaseType.MYSQL]
        
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
            parts.append("AUTO_INCREMENT")
        if not column.nullable and not column.primary_key:
            parts.append("NOT NULL")
        if column.unique and not column.primary_key:
            parts.append("UNIQUE")
        if column.default is not None:
            if isinstance(column.default, str):
                parts.append(f"DEFAULT '{column.default}'")
            elif isinstance(column.default, bool):
                parts.append(f"DEFAULT {1 if column.default else 0}")
            else:
                parts.append(f"DEFAULT {column.default}")
        if column.comment:
            parts.append(f"COMMENT '{column.comment}'")
        
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
        
        # Table options
        options = "ENGINE=InnoDB"
        if table_def.comment:
            options += f" COMMENT='{table_def.comment}'"
        
        if_not_exists = "IF NOT EXISTS" if table_def.if_not_exists else ""
        sql = f"CREATE TABLE {if_not_exists} {table_def.name} ({', '.join(columns_sql)}) {options}"
        
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
        cascade_sql = "CASCADE" if cascade else ""
        sql = f"DROP TABLE {if_exists_sql} {name} {cascade_sql}".strip()
        return await self._pool.execute(sql)
    
    async def alter_table(
        self, 
        name: str, 
        alterations: List[Dict[str, Any]]
    ) -> QueryResult:
        """Alter table structure."""
        alter_parts = []
        
        for alt in alterations:
            action = alt.get("action")
            
            if action == "add_column":
                col = ColumnDef(**alt["column"])
                alter_parts.append(f"ADD COLUMN {self._column_to_sql(col)}")
            
            elif action == "drop_column":
                col_name = alt["column_name"]
                alter_parts.append(f"DROP COLUMN {col_name}")
            
            elif action == "modify_column":
                col = ColumnDef(**alt["column"])
                alter_parts.append(f"MODIFY COLUMN {self._column_to_sql(col)}")
            
            elif action == "rename_column":
                old_name = alt["old_name"]
                new_name = alt["new_name"]
                alter_parts.append(f"CHANGE COLUMN {old_name} {new_name}")
            
            else:
                raise UnsupportedFeatureError(f"Unsupported ALTER TABLE action: {action}")
        
        if not alter_parts:
            return QueryResult(success=True)
        
        sql = f"ALTER TABLE {name} {', '.join(alter_parts)}"
        return await self._pool.execute(sql)
    
    async def rename_table(
        self, 
        old_name: str, 
        new_name: str
    ) -> QueryResult:
        """Rename a table."""
        sql = f"RENAME TABLE {old_name} TO {new_name}"
        return await self._pool.execute(sql)
    
    async def table_exists(self, name: str) -> bool:
        """Check if table exists."""
        sql = """
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND TABLE_NAME = %s
        """
        result = await self._pool.fetch_one(sql, (name,))
        return result and list(result.values())[0] > 0
    
    async def get_table_schema(self, name: str) -> Optional[TableDef]:
        """Get table schema information."""
        if not await self.table_exists(name):
            return None
        
        # Get column info
        sql = """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT,
                   CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE,
                   COLUMN_KEY, EXTRA, COLUMN_COMMENT
            FROM information_schema.columns
            WHERE table_schema = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        rows = await self._pool.fetch_all(sql, (name,))
        
        columns = []
        primary_key = []
        
        for row in rows:
            col_type = row["DATA_TYPE"].upper()
            if row["CHARACTER_MAXIMUM_LENGTH"]:
                col_type = f"VARCHAR({row['CHARACTER_MAXIMUM_LENGTH']})"
            
            is_pk = row["COLUMN_KEY"] == "PRI"
            is_auto = "auto_increment" in (row["EXTRA"] or "").lower()
            
            col = ColumnDef(
                name=row["COLUMN_NAME"],
                type=col_type,
                nullable=row["IS_NULLABLE"] == "YES",
                default=row["COLUMN_DEFAULT"],
                primary_key=is_pk,
                auto_increment=is_auto,
                comment=row["COLUMN_COMMENT"]
            )
            columns.append(col)
            if is_pk:
                primary_key.append(row["COLUMN_NAME"])
        
        return TableDef(
            name=name,
            columns=columns,
            primary_key=primary_key
        )
    
    async def list_tables(self) -> List[str]:
        """List all tables."""
        sql = """
            SELECT TABLE_NAME 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """
        rows = await self._pool.fetch_all(sql)
        return [row["TABLE_NAME"] for row in rows]
    
    async def create_index(
        self, 
        table: str, 
        index_def: IndexDef
    ) -> QueryResult:
        """Create an index."""
        unique = "UNIQUE" if index_def.unique else ""
        columns = ", ".join(index_def.columns)
        sql = f"CREATE {unique} INDEX {index_def.name} ON {table} ({columns})"
        return await self._pool.execute(sql)
    
    async def drop_index(
        self, 
        name: str, 
        table: Optional[str] = None
    ) -> QueryResult:
        """Drop an index."""
        if not table:
            raise QueryError("MySQL requires table name to drop index")
        sql = f"DROP INDEX {name} ON {table}"
        return await self._pool.execute(sql)
    
    async def index_exists(
        self, 
        name: str, 
        table: Optional[str] = None
    ) -> bool:
        """Check if index exists."""
        sql = """
            SELECT COUNT(*) FROM information_schema.statistics 
            WHERE table_schema = DATABASE() AND INDEX_NAME = %s
        """
        params = (name,)
        if table:
            sql += " AND TABLE_NAME = %s"
            params = (name, table)
        
        result = await self._pool.fetch_one(sql, params)
        return result and list(result.values())[0] > 0
    
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
        sql = f"ALTER TABLE {table} DROP FOREIGN KEY {fk_name}"
        return await self._pool.execute(sql)
    
    async def list_indexes(
        self, 
        table: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List indexes for a table or all tables."""
        if table:
            query = """
            SELECT INDEX_NAME, TABLE_NAME, COLUMN_NAME, NON_UNIQUE
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
            """
            rows = await self._pool.fetch_all(query, (table,))
        else:
            query = """
            SELECT INDEX_NAME, TABLE_NAME, COLUMN_NAME, NON_UNIQUE
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
            ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX
            """
            rows = await self._pool.fetch_all(query)
        
        # Group by index name
        indexes_dict = {}
        for row in rows:
            idx_name = row["INDEX_NAME"]
            # Skip primary key
            if idx_name == "PRIMARY":
                continue
            
            if idx_name not in indexes_dict:
                indexes_dict[idx_name] = {
                    "name": idx_name,
                    "table": row["TABLE_NAME"],
                    "columns": [],
                    "unique": row["NON_UNIQUE"] == 0
                }
            indexes_dict[idx_name]["columns"].append(row["COLUMN_NAME"])
        
        return list(indexes_dict.values())
    
    async def list_foreign_keys(
        self, 
        table: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List foreign keys for a table or all tables."""
        if table:
            query = """
            SELECT
                CONSTRAINT_NAME,
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME,
                DELETE_RULE,
                UPDATE_RULE
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
                AND REFERENCED_TABLE_NAME IS NOT NULL
                AND TABLE_NAME = %s
            """
            rows = await self._pool.fetch_all(query, (table,))
        else:
            query = """
            SELECT
                CONSTRAINT_NAME,
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME,
                DELETE_RULE,
                UPDATE_RULE
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """
            rows = await self._pool.fetch_all(query)
        
        fks = []
        for row in rows:
            fks.append({
                "name": row["CONSTRAINT_NAME"],
                "table": row["TABLE_NAME"],
                "columns": [row["COLUMN_NAME"]],
                "ref_table": row["REFERENCED_TABLE_NAME"],
                "ref_columns": [row["REFERENCED_COLUMN_NAME"]],
                "on_delete": row["DELETE_RULE"],
                "on_update": row["UPDATE_RULE"]
            })
        
        return fks