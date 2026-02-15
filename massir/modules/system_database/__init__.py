"""
System Database Module - Async database middleware for relational databases.

Provides unified interface for PostgreSQL, MySQL, and SQLite with:
- Connection pooling
- Query caching
- Transaction management with savepoints
- Schema management (DDL)
- Record operations (DML)
- Raw SQL execution
"""

from .module import DatabaseModule
from .database_service import DatabaseService, DatabaseConnection
from .core.types import (
    DatabaseType,
    ColumnType,
    IndexType,
    RelationType,
    ColumnDef,
    IndexDef,
    ForeignKeyDef,
    RelationDef,
    TableDef,
    QueryResult,
    DatabaseConfig,
    TYPE_MAPPING
)
from .core.exceptions import (
    DatabaseError,
    ConnectionError,
    PoolError,
    QueryError,
    SchemaError,
    RecordError,
    TransactionError,
    CacheError,
    DriverNotFoundError,
    UnsupportedFeatureError
)

__version__ = "1.0.0"

__all__ = [
    # Module
    "DatabaseModule",
    # Service
    "DatabaseService",
    "DatabaseConnection",
    # Types
    "DatabaseType",
    "ColumnType",
    "IndexType",
    "RelationType",
    "ColumnDef",
    "IndexDef",
    "ForeignKeyDef",
    "RelationDef",
    "TableDef",
    "QueryResult",
    "DatabaseConfig",
    "TYPE_MAPPING",
    # Exceptions
    "DatabaseError",
    "ConnectionError",
    "PoolError",
    "QueryError",
    "SchemaError",
    "RecordError",
    "TransactionError",
    "CacheError",
    "DriverNotFoundError",
    "UnsupportedFeatureError",
]
