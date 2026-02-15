"""
SQLite connection and pool implementation.
"""
import asyncio
import time
import aiosqlite
from typing import Any, Dict, List, Optional
from pathlib import Path

from ...core.connection import BaseConnection, BasePool
from ...core.types import DatabaseConfig, QueryResult
from ...core.exceptions import ConnectionError, PoolError, QueryError


class SQLiteConnection(BaseConnection):
    """SQLite connection implementation."""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._db_path = self._resolve_path()
    
    def _resolve_path(self) -> str:
        """Resolve database path."""
        if self.config.path:
            # Handle relative paths
            path = Path(self.config.path)
            if not path.is_absolute():
                # Make relative to current working directory
                path = Path.cwd() / path
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            return str(path)
        return ":memory:"  # In-memory database
    
    async def connect(self) -> bool:
        """Establish database connection."""
        try:
            self._connection = await aiosqlite.connect(
                self._db_path,
                timeout=self.config.connect_timeout
            )
            # Enable foreign keys
            await self._connection.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self._connection.row_factory = aiosqlite.Row
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"Failed to connect to SQLite: {e}")
    
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
            cursor = await self._connection.execute(query, params or ())
            await self._connection.commit()
            
            affected = cursor.rowcount if cursor.rowcount >= 0 else 0
            last_id = cursor.lastrowid
            
            return QueryResult(
                success=True,
                affected_rows=affected,
                last_insert_id=last_id,
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
            cursor = await self._connection.execute(query, params or ())
            row = await cursor.fetchone()
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
            cursor = await self._connection.execute(query, params or ())
            rows = await cursor.fetchall()
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
            cursor = await self._connection.execute(query, params or ())
            row = await cursor.fetchone()
            if row:
                # sqlite3.Row supports indexing, access first column directly
                return row[0]
            return None
        except Exception as e:
            raise QueryError(f"Failed to fetch value: {e}")
    
    async def begin_transaction(self) -> bool:
        """Begin a transaction."""
        await self._connection.execute("BEGIN")
        return True
    
    async def commit(self) -> bool:
        """Commit current transaction."""
        await self._connection.commit()
        return True
    
    async def rollback(self) -> bool:
        """Rollback current transaction."""
        await self._connection.rollback()
        return True
    
    async def ping(self) -> bool:
        """Check if connection is alive."""
        try:
            await self.fetch_value("SELECT 1")
            return True
        except Exception:
            return False


class SQLitePool(BasePool):
    """SQLite connection pool (simplified - SQLite doesn't benefit much from pooling)."""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._connections: List[SQLiteConnection] = []
        self._available: List[SQLiteConnection] = []
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """Initialize the connection pool."""
        # For SQLite, we create a minimal pool
        # SQLite handles concurrency differently
        min_size = min(self.config.pool_min_size, 1)  # At least 1
        
        for _ in range(min_size):
            conn = SQLiteConnection(self.config)
            await conn.connect()
            self._connections.append(conn)
            self._available.append(conn)
        
        self._is_initialized = True
        return True
    
    async def close(self) -> bool:
        """Close all connections."""
        for conn in self._connections:
            await conn.disconnect()
        self._connections.clear()
        self._available.clear()
        self._is_initialized = False
        return True
    
    async def acquire(self) -> SQLiteConnection:
        """Acquire a connection."""
        async with self._lock:
            if self._available:
                return self._available.pop()
            
            # Create new connection if under max
            if len(self._connections) < self.config.pool_max_size:
                conn = SQLiteConnection(self.config)
                await conn.connect()
                self._connections.append(conn)
                return conn
            
            raise PoolError("Connection pool exhausted")
    
    async def release(self, connection: SQLiteConnection) -> None:
        """Release a connection back to the pool."""
        async with self._lock:
            if connection in self._connections:
                self._available.append(connection)
    
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute query using a connection from the pool."""
        conn = await self.acquire()
        try:
            return await conn.execute(query, params)
        finally:
            await self.release(conn)
    
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row using a connection from the pool."""
        conn = await self.acquire()
        try:
            return await conn.fetch_one(query, params)
        finally:
            await self.release(conn)
    
    async def fetch_all(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows using a connection from the pool."""
        conn = await self.acquire()
        try:
            return await conn.fetch_all(query, params)
        finally:
            await self.release(conn)
    
    async def fetch_value(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Any:
        """Fetch single value using a connection from the pool."""
        conn = await self.acquire()
        try:
            return await conn.fetch_value(query, params)
        finally:
            await self.release(conn)
    
    @property
    def size(self) -> int:
        return len(self._connections)
    
    @property
    def idle_size(self) -> int:
        return len(self._available)
