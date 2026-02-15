"""
Database exceptions for the system_database module.
"""


class DatabaseError(Exception):
    """Base exception for database errors."""
    pass


class ConnectionError(DatabaseError):
    """Error establishing database connection."""
    pass


class PoolError(DatabaseError):
    """Error with connection pool."""
    pass


class QueryError(DatabaseError):
    """Error executing query."""
    pass


class SchemaError(DatabaseError):
    """Error in schema operations."""
    pass


class RecordError(DatabaseError):
    """Error in record operations."""
    pass


class TransactionError(DatabaseError):
    """Error in transaction operations."""
    pass


class CacheError(DatabaseError):
    """Error in caching operations."""
    pass


class DriverNotFoundError(DatabaseError):
    """Requested database driver not found."""
    pass


class UnsupportedFeatureError(DatabaseError):
    """Feature not supported by this database driver."""
    pass
