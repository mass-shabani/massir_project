"""
Core database module components.
"""
from .types import (
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
from .exceptions import (
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
from .connection import BaseConnection, BasePool
from .schema import BaseSchemaManager
from .record import BaseRecordManager
from .sql import BaseSQLExecutor
from .transaction import BaseTransaction
from .cache import QueryCache, CacheManager

__all__ = [
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
    # Base classes
    "BaseConnection",
    "BasePool",
    "BaseSchemaManager",
    "BaseRecordManager",
    "BaseSQLExecutor",
    "BaseTransaction",
    # Cache
    "QueryCache",
    "CacheManager"
]
