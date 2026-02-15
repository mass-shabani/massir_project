"""
PostgreSQL connection and pool implementation using asyncpg.
"""
import time
import asyncio
import asyncpg
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from ...core.connection import BaseConnection, BasePool
from ...core.types import DatabaseConfig, QueryResult
from ...core.exceptions import ConnectionError, PoolError, QueryError


class PostgreSQLConnection(BaseConnection):
    """PostgreSQL connection implementation."""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
    
    async def connect(self) -> bool:
        """Establish database connection."""
        try:
            self._connection = await asyncpg.connect(
                host=self.config.host,
                port=self.config.port or 5432,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                timeout=self.config.connect_timeout,
                command_timeout=self.config.command_timeout
            )
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"Failed to connect to PostgreSQL: {e}")
    
    async def disconnect(self) -> bool:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._is_connected = False
        return True
    
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute a query."""
        start_time = time.time()
        try:
            # asyncpg uses $1, $2 style placeholders
            result = await self._connection.execute(query, *(params or ()))
            
            # Parse result tag (e.g., "INSERT 0 5" -> affected_rows=5)
            parts = result.split()
            affected = int(parts[-1]) if len(parts) > 1 and parts[-1].isdigit() else 0
            
            return QueryResult(
                success=True,
                affected_rows=affected,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return QueryResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute query and fetch single row."""
        try:
            row = await self._connection.fetchrow(query, *(params or ()))
            if row:
                return dict(row)
            return None
        except Exception as e:
            raise QueryError(f"Failed to fetch row: {e}")
    
    async def fetch_all(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute query and fetch all rows."""
        try:
            rows = await self._connection.fetch(query, *(params or ()))
            return [dict(row) for row in rows]
        except Exception as e:
            raise QueryError(f"Failed to fetch rows: {e}")
    
    async def fetch_value(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Any:
        """Execute query and fetch single value."""
        try:
            row = await self._connection.fetchrow(query, *(params or ()))
            if row:
                return list(row.values())[0]
            return None
        except Exception as e:
            raise QueryError(f"Failed to fetch value: {e}")
    
    async def begin_transaction(self) -> bool:
        """Begin a transaction."""
        self._connection._con._top_xact = self._connection._con.transaction()
        await self._connection._con._top_xact.start()
        return True
    
    async def commit(self) -> bool:
        """Commit current transaction."""
        if hasattr(self._connection._con, '_top_xact') and self._connection._con._top_xact:
            await self._connection._con._top_xact.commit()
            self._connection._con._top_xact = None
        return True
    
    async def rollback(self) -> bool:
        """Rollback current transaction."""
        if hasattr(self._connection._con, '_top_xact') and self._connection._con._top_xact:
            await self._connection._con._top_xact.rollback()
            self._connection._con._top_xact = None
        return True
    
    async def ping(self) -> bool:
        """Check if connection is alive."""
        try:
            await self.fetch_value("SELECT 1")
            return True
        except Exception:
            return False


class PostgreSQLPool(BasePool):
    """PostgreSQL connection pool implementation."""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
    
    async def initialize(self) -> bool:
        """Initialize the connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                host=self.config.host,
                port=self.config.port or 5432,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                min_size=self.config.pool_min_size,
                max_size=self.config.pool_max_size,
                max_inactive_connection_lifetime=self.config.pool_timeout,
                command_timeout=self.config.command_timeout
            )
            self._is_initialized = True
            return True
        except Exception as e:
            raise PoolError(f"Failed to create PostgreSQL pool: {e}")
    
    async def close(self) -> bool:
        """Close all connections in the pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._is_initialized = False
        return True
    
    async def acquire(self) -> asyncpg.Connection:
        """Acquire a connection from the pool."""
        if not self._pool:
            raise PoolError("Pool not initialized")
        return await self._pool.acquire()
    
    async def release(self, connection: asyncpg.Connection) -> None:
        """Release a connection back to the pool."""
        if self._pool and connection:
            await self._pool.release(connection)
    
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute query using a connection from the pool."""
        start_time = time.time()
        try:
            async with self._pool.acquire() as conn:
                result = await conn.execute(query, *(params or ()))
                parts = result.split()
                affected = int(parts[-1]) if len(parts) > 1 and parts[-1].isdigit() else 0
                return QueryResult(
                    success=True,
                    affected_rows=affected,
                    execution_time=time.time() - start_time
                )
        except Exception as e:
            return QueryResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row using a connection from the pool."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *(params or ()))
            return dict(row) if row else None
    
    async def fetch_all(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows using a connection from the pool."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *(params or ()))
            return [dict(row) for row in rows]
    
    async def fetch_value(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Any:
        """Fetch single value using a connection from the pool."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *(params or ()))
            return list(row.values())[0] if row else None
    
    @property
    def size(self) -> int:
        return self._pool.get_size() if self._pool else 0
    
    @property
    def idle_size(self) -> int:
        return self._pool.get_idle_size() if self._pool else 0
