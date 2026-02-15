"""
Type definitions and mappings for the database module.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class DatabaseType(Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class ColumnType(Enum):
    """Common column types across databases."""
    # Integer types
    INTEGER = "integer"
    BIGINT = "bigint"
    SMALLINT = "smallint"
    
    # Float types
    FLOAT = "float"
    DOUBLE = "double"
    DECIMAL = "decimal"
    
    # String types
    VARCHAR = "varchar"
    TEXT = "text"
    CHAR = "char"
    
    # Boolean
    BOOLEAN = "boolean"
    
    # Date/Time
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    
    # Binary
    BLOB = "blob"
    BINARY = "binary"
    
    # JSON
    JSON = "json"
    
    # UUID
    UUID = "uuid"


class IndexType(Enum):
    """Index types."""
    BTREE = "btree"
    HASH = "hash"
    GIN = "gin"  # PostgreSQL specific
    GIST = "gist"  # PostgreSQL specific


class RelationType(Enum):
    """Relationship types between tables."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_MANY = "many_to_many"


@dataclass
class ColumnDef:
    """Column definition for table creation."""
    name: str
    type: Union[ColumnType, str]
    nullable: bool = True
    default: Any = None
    primary_key: bool = False
    auto_increment: bool = False
    unique: bool = False
    length: Optional[int] = None  # For VARCHAR, CHAR
    precision: Optional[int] = None  # For DECIMAL
    scale: Optional[int] = None  # For DECIMAL
    comment: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.value if isinstance(self.type, ColumnType) else self.type,
            "nullable": self.nullable,
            "default": self.default,
            "primary_key": self.primary_key,
            "auto_increment": self.auto_increment,
            "unique": self.unique,
            "length": self.length,
            "precision": self.precision,
            "scale": self.scale,
            "comment": self.comment
        }


@dataclass
class IndexDef:
    """Index definition."""
    name: str
    columns: List[str]
    unique: bool = False
    type: IndexType = IndexType.BTREE
    table: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": self.columns,
            "unique": self.unique,
            "type": self.type.value,
            "table": self.table
        }


@dataclass
class ForeignKeyDef:
    """Foreign key definition."""
    columns: List[str]
    ref_table: str
    ref_columns: List[str]
    on_delete: str = "RESTRICT"  # CASCADE, SET NULL, NO ACTION, RESTRICT
    on_update: str = "RESTRICT"
    name: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "ref_table": self.ref_table,
            "ref_columns": self.ref_columns,
            "on_delete": self.on_delete,
            "on_update": self.on_update,
            "name": self.name
        }


@dataclass
class RelationDef:
    """Relationship definition between tables."""
    name: str
    type: RelationType
    from_table: str
    from_columns: List[str]
    to_table: str
    to_columns: List[str]
    through_table: Optional[str] = None  # For many-to-many
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "from_table": self.from_table,
            "from_columns": self.from_columns,
            "to_table": self.to_table,
            "to_columns": self.to_columns,
            "through_table": self.through_table
        }


@dataclass
class TableDef:
    """Table definition."""
    name: str
    columns: List[ColumnDef]
    primary_key: List[str] = field(default_factory=list)
    indexes: List[IndexDef] = field(default_factory=list)
    foreign_keys: List[ForeignKeyDef] = field(default_factory=list)
    comment: Optional[str] = None
    if_not_exists: bool = True
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key": self.primary_key,
            "indexes": [i.to_dict() for i in self.indexes],
            "foreign_keys": [fk.to_dict() for fk in self.foreign_keys],
            "comment": self.comment,
            "if_not_exists": self.if_not_exists
        }


@dataclass
class QueryResult:
    """Result of a query execution."""
    success: bool
    affected_rows: int = 0
    last_insert_id: Optional[int] = None
    rows: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    execution_time: float = 0.0  # seconds
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "affected_rows": self.affected_rows,
            "last_insert_id": self.last_insert_id,
            "rows": self.rows,
            "error": self.error,
            "execution_time": self.execution_time
        }


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    name: str  # Connection name/alias
    driver: str  # postgresql, mysql, sqlite
    host: str = "localhost"
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    path: Optional[str] = None  # For SQLite
    
    # Pool settings
    pool_min_size: int = 5
    pool_max_size: int = 20
    pool_max_idle: int = 10
    pool_timeout: float = 30.0
    
    # Connection settings
    connect_timeout: float = 10.0
    command_timeout: float = 60.0
    
    # Additional options
    ssl_mode: Optional[str] = None
    charset: str = "utf8mb4"
    
    # Cache settings
    cache_enabled: bool = True
    cache_ttl: int = 300  # seconds
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "driver": self.driver,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": "***",  # Don't expose password
            "path": self.path,
            "pool_min_size": self.pool_min_size,
            "pool_max_size": self.pool_max_size,
            "pool_max_idle": self.pool_max_idle,
            "pool_timeout": self.pool_timeout,
            "connect_timeout": self.connect_timeout,
            "command_timeout": self.command_timeout,
            "ssl_mode": self.ssl_mode,
            "charset": self.charset,
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DatabaseConfig":
        """Create config from dictionary."""
        return cls(
            name=data.get("name", "default"),
            driver=data.get("driver", "sqlite"),
            host=data.get("host", "localhost"),
            port=data.get("port"),
            database=data.get("database"),
            user=data.get("user"),
            password=data.get("password"),
            path=data.get("path"),
            pool_min_size=data.get("pool_min_size", 5),
            pool_max_size=data.get("pool_max_size", 20),
            pool_max_idle=data.get("pool_max_idle", 10),
            pool_timeout=data.get("pool_timeout", 30.0),
            connect_timeout=data.get("connect_timeout", 10.0),
            command_timeout=data.get("command_timeout", 60.0),
            ssl_mode=data.get("ssl_mode"),
            charset=data.get("charset", "utf8mb4"),
            cache_enabled=data.get("cache_enabled", True),
            cache_ttl=data.get("cache_ttl", 300)
        )


# Type mapping between common types and database-specific types
TYPE_MAPPING = {
    DatabaseType.POSTGRESQL: {
        ColumnType.INTEGER: "INTEGER",
        ColumnType.BIGINT: "BIGINT",
        ColumnType.SMALLINT: "SMALLINT",
        ColumnType.FLOAT: "REAL",
        ColumnType.DOUBLE: "DOUBLE PRECISION",
        ColumnType.DECIMAL: "DECIMAL",
        ColumnType.VARCHAR: "VARCHAR",
        ColumnType.TEXT: "TEXT",
        ColumnType.CHAR: "CHAR",
        ColumnType.BOOLEAN: "BOOLEAN",
        ColumnType.DATE: "DATE",
        ColumnType.TIME: "TIME",
        ColumnType.DATETIME: "TIMESTAMP",
        ColumnType.TIMESTAMP: "TIMESTAMP",
        ColumnType.BLOB: "BYTEA",
        ColumnType.BINARY: "BYTEA",
        ColumnType.JSON: "JSONB",
        ColumnType.UUID: "UUID",
    },
    DatabaseType.MYSQL: {
        ColumnType.INTEGER: "INT",
        ColumnType.BIGINT: "BIGINT",
        ColumnType.SMALLINT: "SMALLINT",
        ColumnType.FLOAT: "FLOAT",
        ColumnType.DOUBLE: "DOUBLE",
        ColumnType.DECIMAL: "DECIMAL",
        ColumnType.VARCHAR: "VARCHAR",
        ColumnType.TEXT: "TEXT",
        ColumnType.CHAR: "CHAR",
        ColumnType.BOOLEAN: "TINYINT(1)",
        ColumnType.DATE: "DATE",
        ColumnType.TIME: "TIME",
        ColumnType.DATETIME: "DATETIME",
        ColumnType.TIMESTAMP: "TIMESTAMP",
        ColumnType.BLOB: "BLOB",
        ColumnType.BINARY: "BINARY",
        ColumnType.JSON: "JSON",
        ColumnType.UUID: "CHAR(36)",
    },
    DatabaseType.SQLITE: {
        ColumnType.INTEGER: "INTEGER",
        ColumnType.BIGINT: "INTEGER",
        ColumnType.SMALLINT: "INTEGER",
        ColumnType.FLOAT: "REAL",
        ColumnType.DOUBLE: "REAL",
        ColumnType.DECIMAL: "REAL",
        ColumnType.VARCHAR: "TEXT",
        ColumnType.TEXT: "TEXT",
        ColumnType.CHAR: "TEXT",
        ColumnType.BOOLEAN: "INTEGER",
        ColumnType.DATE: "TEXT",
        ColumnType.TIME: "TEXT",
        ColumnType.DATETIME: "TEXT",
        ColumnType.TIMESTAMP: "TEXT",
        ColumnType.BLOB: "BLOB",
        ColumnType.BINARY: "BLOB",
        ColumnType.JSON: "TEXT",
        ColumnType.UUID: "TEXT",
    }
}
