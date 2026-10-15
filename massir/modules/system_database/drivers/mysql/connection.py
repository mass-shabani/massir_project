"""
MySQL connection pool implementation using aiomysql.
"""
import time
from typing import Any, Dict, List, Optional

import aiomysql

from ...core.connection import BasePool
from ...core.types import DatabaseConfig, QueryResult
from ...core.exceptions import PoolError


class MySQLPool(BasePool):
    """MySQL connection pool implementation."""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
    
    async def initialize(self) -> bool:
        """Initialize the connection pool."""
        try:
            self._pool = await aiomysql.create_pool(
                host=self.config.host,
                port=self.config.port or 3306,
                db=self.config.database,
                user=self.config.user,
                password=self.config.password,
                charset=self.config.charset,
                minsize=self.config.pool_min_size,
                maxsize=self.config.pool_max_size,
                connect_timeout=self.config.connect_timeout,
                autocommit=False,
                pool_recycle=3600
            )
            self._is_initialized = True
            return True
        except Exception as e:
            raise PoolError(f"Failed to create MySQL pool: {e}")
    
    async def close(self) -> bool:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            self._is_initialized = False
        return True
    
    async def acquire(self) -> aiomysql.Connection:
        """Acquire a connection from the pool."""
        if not self._pool:
            raise PoolError("Pool not initialized")
        return await self._pool.acquire()
    
    async def release(self, connection: aiomysql.Connection) -> None:
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
        conn = None
        try:
            conn = await self.acquire()
            await conn.ping(reconnect=True)
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                await conn.commit()
                affected = cursor.rowcount if cursor.rowcount >= 0 else 0
                last_id = cursor.lastrowid
                return QueryResult(
                    success=True,
                    affected_rows=affected,
                    last_insert_id=last_id,
                    execution_time=time.time() - start_time
                )
        except Exception as e:
            if conn:
                try:
                    await conn.rollback()
                except:
                    pass
            return QueryResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
        finally:
            if conn:
                await self.release(conn)
    
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row using a connection from the pool."""
        conn = await self.acquire()
        try:
            await conn.ping(reconnect=True)
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params or ())
                row = await cursor.fetchone()
                return dict(row) if row else None
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
            await conn.ping(reconnect=True)
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params or ())
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
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
            await conn.ping(reconnect=True)
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                row = await cursor.fetchone()
                return row[0] if row else None
        finally:
            await self.release(conn)
    
    @property
    def size(self) -> int:
        return self._pool.size if self._pool else 0
    
    @property
    def idle_size(self) -> int:
        return self._pool.freesize if self._pool else 0
