"""
Database Service - Main service class for database operations.

This service provides a unified interface for working with multiple database
connections, with support for connection pooling, caching, and transactions.
"""
from typing import Any, Dict, List, Optional, AsyncIterator
from contextlib import asynccontextmanager

from .core.types import (
    DatabaseConfig, DatabaseType, TableDef, ColumnDef, IndexDef,
    ForeignKeyDef, QueryResult
)
from .core.exceptions import (
    DatabaseError, ConnectionError, DriverNotFoundError, TransactionError
)
from .core.cache import CacheManager
from .core.connection import BasePool
from .core.schema import BaseSchemaManager
from .core.record import BaseRecordManager
from .core.sql import BaseSQLExecutor
from .core.transaction import BaseTransaction


class DatabaseConnection:
    """
    Represents a single database connection with all its managers.
    
    Provides access to schema, record, SQL, and transaction operations.
    """
    
    def __init__(
        self,
        name: str,
        pool: BasePool,
        schema_manager: BaseSchemaManager,
        record_manager: BaseRecordManager,
        sql_executor: BaseSQLExecutor,
        transaction_class: type,
        cache_manager: Optional[CacheManager] = None,
        cache_enabled: bool = True
    ):
        self.name = name
        self._pool = pool
        self._schema = schema_manager
        self._record = record_manager
        self._sql = sql_executor
        self._transaction_class = transaction_class
        self._cache = cache_manager
        self._cache_enabled = cache_enabled
    
    # --- Schema Operations (DDL) ---
    
    @property
    def schema(self) -> BaseSchemaManager:
        """Access schema manager for DDL operations."""
        return self._schema
    
    async def create_table(self, table_def: TableDef) -> QueryResult:
        """Create a table."""
        return await self._schema.create_table(table_def)
    
    async def drop_table(
        self, 
        name: str, 
        if_exists: bool = True,
        cascade: bool = False
    ) -> QueryResult:
        """Drop a table."""
        return await self._schema.drop_table(name, if_exists, cascade)
    
    async def table_exists(self, name: str) -> bool:
        """Check if table exists."""
        return await self._schema.table_exists(name)
    
    async def list_tables(self) -> List[str]:
        """List all tables."""
        return await self._schema.list_tables()
    
    # --- Record Operations (DML) ---
    
    @property
    def records(self) -> BaseRecordManager:
        """Access record manager for DML operations."""
        return self._record
    
    async def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        returning: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert a record."""
        result = await self._record.insert(table, data, returning)
        if self._cache_enabled and self._cache and result.success:
            await self._cache.invalidate(self.name, table)
        return result
    
    async def insert_many(
        self, 
        table: str, 
        data: List[Dict[str, Any]]
    ) -> QueryResult:
        """Insert multiple records."""
        result = await self._record.insert_many(table, data)
        if self._cache_enabled and self._cache and result.success:
            await self._cache.invalidate(self.name, table)
        return result
    
    async def update(
        self, 
        table: str, 
        data: Dict[str, Any],
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> QueryResult:
        """Update records."""
        result = await self._record.update(table, data, where, where_sql, where_params)
        if self._cache_enabled and self._cache and result.success:
            await self._cache.invalidate(self.name, table)
        return result
    
    async def delete(
        self, 
        table: str,
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> QueryResult:
        """Delete records."""
        result = await self._record.delete(table, where, where_sql, where_params)
        if self._cache_enabled and self._cache and result.success:
            await self._cache.invalidate(self.name, table)
        return result
    
    async def find_one(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Find a single record."""
        # For now, skip caching on find operations
        # A more sophisticated implementation would cache query results
        return await self._record.find_one(table, where, columns, order_by)
    
    async def find_many(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple records."""
        return await self._record.find_many(table, where, columns, order_by, limit, offset)
    
    async def count(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> int:
        """Count records."""
        return await self._record.count(table, where, where_sql, where_params)
    
    async def exists(
        self, 
        table: str,
        where: Dict[str, Any]
    ) -> bool:
        """Check if records exist."""
        return await self._record.exists(table, where)
    
    async def upsert(
        self, 
        table: str, 
        data: Dict[str, Any],
        key_columns: List[str],
        update_columns: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert or update record."""
        result = await self._record.upsert(table, data, key_columns, update_columns)
        if self._cache_enabled and self._cache and result.success:
            await self._cache.invalidate(self.name, table)
        return result
    
    async def stream(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        batch_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream records for large result sets."""
        async for row in self._record.stream(table, where, columns, order_by, batch_size):
            yield row
    
    # --- Raw SQL Operations ---
    
    @property
    def sql(self) -> BaseSQLExecutor:
        """Access SQL executor for raw SQL operations."""
        return self._sql
    
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute raw SQL."""
        return await self._sql.execute(query, params)
    
    async def execute_script(
        self, 
        script: str
    ) -> List[QueryResult]:
        """Execute multiple SQL statements."""
        return await self._sql.execute_script(script)
    
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute SQL and fetch single row."""
        return await self._sql.fetch_one(query, params)
    
    async def fetch_all(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute SQL and fetch all rows."""
        return await self._sql.fetch_all(query, params)
    
    async def fetch_value(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Any:
        """Execute SQL and fetch single value."""
        return await self._sql.fetch_value(query, params)
    
    # --- Transaction Operations ---
    
    def transaction(self) -> BaseTransaction:
        """Create a new transaction."""
        return self._transaction_class(self._pool)
    
    @asynccontextmanager
    async def begin_transaction(self):
        """Context manager for transactions."""
        tx = self.transaction()
        await tx.begin()
        try:
            yield tx
            await tx.commit()
        except Exception:
            await tx.rollback()
            raise
    
    # --- Connection Management ---
    
    async def ping(self) -> bool:
        """Check if connection is alive."""
        try:
            async with self._pool.connection() as conn:
                return await conn.ping()
        except Exception:
            return False
    
    @property
    def pool_size(self) -> int:
        """Get current pool size."""
        return self._pool.size
    
    @property
    def pool_idle(self) -> int:
        """Get number of idle connections."""
        return self._pool.idle_size


class DatabaseService:
    """
    Main database service for managing multiple database connections.
    
    This service provides:
    - Multi-database support (PostgreSQL, MySQL, SQLite)
    - Connection pooling
    - Query caching
    - Unified API for all operations
    - Transaction management with savepoints
    """
    
    def __init__(self):
        self._connections: Dict[str, DatabaseConnection] = {}
        self._cache_manager: Optional[CacheManager] = None
        self._default_connection: Optional[str] = None
        self._logger = None
    
    def set_logger(self, logger):
        """Set logger for the service."""
        self._logger = logger
    
    def _log(self, message: str, level: str = "INFO"):
        """Log a message."""
        if self._logger:
            self._logger.log(message, level=level, tag="database")
    
    async def initialize(
        self,
        configs: List[Dict[str, Any]],
        cache_enabled: bool = True,
        cache_ttl: int = 300,
        cache_max_size: int = 1000
    ) -> bool:
        """
        Initialize database connections from configuration.
        
        Args:
            configs: List of database configurations
            cache_enabled: Enable query caching
            cache_ttl: Default cache TTL in seconds
            cache_max_size: Maximum cache size
            
        Returns:
            True if all connections initialized successfully
        """
        # Initialize cache manager
        if cache_enabled:
            self._cache_manager = CacheManager(
                default_ttl=cache_ttl,
                max_size=cache_max_size
            )
            await self._cache_manager.start_all()
        
        # Initialize each database connection
        for config_dict in configs:
            config = DatabaseConfig.from_dict(config_dict)
            await self.add_connection(config)
            
            # Set first connection as default
            if self._default_connection is None:
                self._default_connection = config.name
        
        self._log(f"Database service initialized with {len(self._connections)} connection(s)")
        return True
    
    async def add_connection(self, config: DatabaseConfig) -> DatabaseConnection:
        """
        Add a new database connection.
        
        Args:
            config: Database configuration
            
        Returns:
            DatabaseConnection instance
        """
        driver = config.driver.lower()
        
        # Import and create appropriate driver
        if driver == "sqlite":
            from .drivers.sqlite import (
                SQLitePool, SQLiteSchemaManager,
                SQLiteRecordManager, SQLiteSQLExecutor, SQLiteTransaction
            )
            pool = SQLitePool(config)
            await pool.initialize()
            
            connection = DatabaseConnection(
                name=config.name,
                pool=pool,
                schema_manager=SQLiteSchemaManager(pool),
                record_manager=SQLiteRecordManager(pool),
                sql_executor=SQLiteSQLExecutor(pool),
                transaction_class=SQLiteTransaction,
                cache_manager=self._cache_manager,
                cache_enabled=config.cache_enabled
            )
        
        elif driver in ("postgresql", "postgres", "psql"):
            from .drivers.postgresql import (
                PostgreSQLPool, PostgreSQLSchemaManager,
                PostgreSQLRecordManager, PostgreSQLSQLExecutor, PostgreSQLTransaction
            )
            pool = PostgreSQLPool(config)
            await pool.initialize()
            
            connection = DatabaseConnection(
                name=config.name,
                pool=pool,
                schema_manager=PostgreSQLSchemaManager(pool),
                record_manager=PostgreSQLRecordManager(pool),
                sql_executor=PostgreSQLSQLExecutor(pool),
                transaction_class=PostgreSQLTransaction,
                cache_manager=self._cache_manager,
                cache_enabled=config.cache_enabled
            )
        
        elif driver == "mysql":
            from .drivers.mysql import (
                MySQLPool, MySQLSchemaManager,
                MySQLRecordManager, MySQLSQLExecutor, MySQLTransaction
            )
            pool = MySQLPool(config)
            await pool.initialize()
            
            connection = DatabaseConnection(
                name=config.name,
                pool=pool,
                schema_manager=MySQLSchemaManager(pool),
                record_manager=MySQLRecordManager(pool),
                sql_executor=MySQLSQLExecutor(pool),
                transaction_class=MySQLTransaction,
                cache_manager=self._cache_manager,
                cache_enabled=config.cache_enabled
            )
        
        else:
            raise DriverNotFoundError(f"Unsupported database driver: {driver}")
        
        self._connections[config.name] = connection
        self._log(f"Database connection '{config.name}' ({driver}) initialized")
        
        return connection
    
    async def remove_connection(self, name: str) -> bool:
        """
        Remove a database connection.
        
        Args:
            name: Connection name
            
        Returns:
            True if removed successfully
        """
        if name not in self._connections:
            return False
        
        conn = self._connections[name]
        await conn._pool.close()
        del self._connections[name]
        
        if self._default_connection == name:
            self._default_connection = next(iter(self._connections), None)
        
        self._log(f"Database connection '{name}' removed")
        return True
    
    async def close_all(self):
        """Close all database connections."""
        for name, conn in list(self._connections.items()):
            await conn._pool.close()
            self._log(f"Database connection '{name}' closed")
        
        self._connections.clear()
        self._default_connection = None
        
        if self._cache_manager:
            await self._cache_manager.stop_all()
    
    def get_connection(self, name: Optional[str] = None) -> DatabaseConnection:
        """
        Get a database connection by name.
        
        Args:
            name: Connection name (uses default if None)
            
        Returns:
            DatabaseConnection instance
            
        Raises:
            DatabaseError if connection not found
        """
        conn_name = name or self._default_connection
        if not conn_name:
            raise DatabaseError("No database connections available")
        
        if conn_name not in self._connections:
            raise DatabaseError(f"Database connection '{conn_name}' not found")
        
        return self._connections[conn_name]
    
    def __getitem__(self, name: str) -> DatabaseConnection:
        """Get connection by name using bracket notation."""
        return self.get_connection(name)
    
    @property
    def default(self) -> DatabaseConnection:
        """Get the default database connection."""
        return self.get_connection()
    
    @property
    def connections(self) -> List[str]:
        """Get list of connection names."""
        return list(self._connections.keys())
    
    @property
    def cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get cache statistics."""
        if self._cache_manager:
            return self._cache_manager.get_all_stats()
        return {}
    
    def enable_cache(self):
        """Enable caching."""
        if self._cache_manager:
            self._cache_manager.enable()
    
    def disable_cache(self):
        """Disable caching."""
        if self._cache_manager:
            self._cache_manager.disable()
    
    async def clear_cache(self):
        """Clear all cached data."""
        if self._cache_manager:
            await self._cache_manager.clear_all()
    
    # --- Convenience methods that use default connection ---
    
    async def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        returning: Optional[List[str]] = None,
        connection: Optional[str] = None
    ) -> QueryResult:
        """Insert a record."""
        return await self.get_connection(connection).insert(table, data, returning)
    
    async def insert_many(
        self, 
        table: str, 
        data: List[Dict[str, Any]],
        connection: Optional[str] = None
    ) -> QueryResult:
        """Insert multiple records."""
        return await self.get_connection(connection).insert_many(table, data)
    
    async def update(
        self, 
        table: str, 
        data: Dict[str, Any],
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None,
        connection: Optional[str] = None
    ) -> QueryResult:
        """Update records."""
        return await self.get_connection(connection).update(
            table, data, where, where_sql, where_params
        )
    
    async def delete(
        self, 
        table: str,
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None,
        connection: Optional[str] = None
    ) -> QueryResult:
        """Delete records."""
        return await self.get_connection(connection).delete(
            table, where, where_sql, where_params
        )
    
    async def find_one(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        connection: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a single record."""
        return await self.get_connection(connection).find_one(
            table, where, columns, order_by
        )
    
    async def find_many(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        connection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple records."""
        return await self.get_connection(connection).find_many(
            table, where, columns, order_by, limit, offset
        )
    
    async def count(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None,
        connection: Optional[str] = None
    ) -> int:
        """Count records."""
        return await self.get_connection(connection).count(
            table, where, where_sql, where_params
        )
    
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None,
        connection: Optional[str] = None
    ) -> QueryResult:
        """Execute raw SQL."""
        return await self.get_connection(connection).execute(query, params)
    
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None,
        connection: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute SQL and fetch single row."""
        return await self.get_connection(connection).fetch_one(query, params)
    
    async def fetch_all(
        self, 
        query: str, 
        params: Optional[tuple] = None,
        connection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute SQL and fetch all rows."""
        return await self.get_connection(connection).fetch_all(query, params)
    
    # --- Dynamic Connection Testing and Creation ---
    
    async def test_connection(
        self, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test a database connection without persisting it.
        
        Args:
            config: Connection configuration dictionary with keys:
                - driver: Database type (sqlite, postgresql, mysql)
                - host, port, database, user, password: For PostgreSQL/MySQL
                - path: For SQLite
                
        Returns:
            Dict with 'success' and 'message' keys
        """
        driver = config.get("driver", "sqlite").lower()
        
        try:
            if driver == "sqlite":
                return await self._test_sqlite_connection(config)
            elif driver in ("postgresql", "postgres", "psql"):
                return await self._test_postgresql_connection(config)
            elif driver == "mysql":
                return await self._test_mysql_connection(config)
            else:
                return {
                    "success": False,
                    "message": f"Unsupported database driver: {driver}"
                }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Connection test failed: {error_msg}", "ERROR")
            return {
                "success": False,
                "message": error_msg
            }
    
    async def _test_sqlite_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test SQLite connection."""
        from pathlib import Path
        import aiosqlite
        
        path = config.get("path", "data/test.db")
        db_path = Path(path)
        
        # Check if file exists
        if not db_path.exists():
            return {
                "success": False,
                "message": f"Database file not found: {db_path}",
                "file_exists": False
            }
        
        # Test connection
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("SELECT 1")
        
        return {
            "success": True,
            "message": f"Successfully connected to SQLite database: {db_path}",
            "file_exists": True,
            "resolved_path": str(db_path.resolve())
        }
    
    async def _test_postgresql_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test PostgreSQL connection."""
        import asyncpg
        
        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        database = config.get("database", "postgres")
        user = config.get("user", "postgres")
        password = config.get("password", "")
        
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            timeout=10
        )
        await conn.execute("SELECT 1")
        await conn.close()
        
        return {
            "success": True,
            "message": f"Successfully connected to PostgreSQL: {host}:{port}/{database}"
        }
    
    async def _test_mysql_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test MySQL connection."""
        import aiomysql
        
        host = config.get("host", "localhost")
        port = config.get("port", 3306)
        database = config.get("database", "mysql")
        user = config.get("user", "root")
        password = config.get("password", "")
        
        conn = await aiomysql.connect(
            host=host,
            port=port,
            db=database,
            user=user,
            password=password,
            connect_timeout=10
        )
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
        conn.close()
        
        return {
            "success": True,
            "message": f"Successfully connected to MySQL: {host}:{port}/{database}"
        }
    
    async def create_database(
        self, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new database (SQLite only).
        
        Args:
            config: Connection configuration with 'path' key
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        from pathlib import Path
        import aiosqlite
        
        driver = config.get("driver", "sqlite").lower()
        
        if driver != "sqlite":
            return {
                "success": False,
                "message": "create_database is only supported for SQLite"
            }
        
        path = config.get("path", "data/new.db")
        db_path = Path(path)
        
        # Check if file already exists
        if db_path.exists():
            return {
                "success": False,
                "message": f"Database file already exists: {db_path}"
            }
        
        # Create directory if needed
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the database file
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute("CREATE TABLE IF NOT EXISTS _init (id INTEGER PRIMARY KEY)")
            await conn.commit()
        
        self._log(f"Created new SQLite database: {db_path}")
        
        return {
            "success": True,
            "message": f"Successfully created new SQLite database: {db_path}",
            "resolved_path": str(db_path.resolve())
        }
    
    async def get_table_schema(
        self, 
        table_name: str,
        connection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get the schema of a table.
        
        Args:
            table_name: Name of the table
            connection: Connection name (uses default if None)
            
        Returns:
            List of column definitions as dictionaries
        """
        conn = self.get_connection(connection)
        table_def = await conn._schema.get_table_schema(table_name)
        
        if table_def is None:
            return []
        
        return [col.to_dict() for col in table_def.columns]
    
    async def list_indexes(
        self,
        table_name: Optional[str] = None,
        connection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List indexes for a table or all tables.
        
        Args:
            table_name: Table name (lists all indexes if None)
            connection: Connection name (uses default if None)
            
        Returns:
            List of index information dictionaries
        """
        conn = self.get_connection(connection)
        return await conn._schema.list_indexes(table_name)
    
    async def list_foreign_keys(
        self,
        table_name: Optional[str] = None,
        connection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List foreign keys for a table or all tables.
        
        Args:
            table_name: Table name (lists all FKs if None)
            connection: Connection name (uses default if None)
            
        Returns:
            List of foreign key information dictionaries
        """
        conn = self.get_connection(connection)
        return await conn._schema.list_foreign_keys(table_name)
    
    async def add_dynamic_connection(
        self, 
        config: Dict[str, Any]
    ) -> DatabaseConnection:
        """
        Add a dynamic database connection from configuration dictionary.
        
        This method allows adding connections at runtime without
        pre-defining them in the initialization config.
        
        Args:
            config: Connection configuration dictionary
            
        Returns:
            DatabaseConnection instance
        """
        db_config = DatabaseConfig.from_dict(config)
        return await self.add_connection(db_config)
    
    def has_connection(self, name: str) -> bool:
        """Check if a connection exists."""
        return name in self._connections
    
    def is_connected(self, name: Optional[str] = None) -> bool:
        """Check if a connection is active."""
        try:
            conn = self.get_connection(name)
            return conn is not None
        except DatabaseError:
            return False
