"""
MySQL raw SQL executor implementation.
"""
import aiomysql
from typing import Any, Dict, List, Optional, AsyncIterator

from ...core.sql import BaseSQLExecutor
from ...core.types import QueryResult
from .connection import MySQLPool


class MySQLSQLExecutor(BaseSQLExecutor):
    """MySQL raw SQL executor implementation."""
    
    def __init__(self, pool: MySQLPool):
        self._pool = pool
    
    async def execute(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute raw SQL."""
        return await self._pool.execute(sql, params)
    
    async def execute_script(
        self, 
        script: str
    ) -> List[QueryResult]:
        """Execute multiple SQL statements."""
        results = []
        statements = [s.strip() for s in script.split(";") if s.strip()]
        
        conn = await self._pool.acquire()
        try:
            await conn.begin()
            for stmt in statements:
                async with conn.cursor() as cursor:
                    await cursor.execute(stmt)
                result = QueryResult(success=True, affected_rows=cursor.rowcount)
                results.append(result)
                if not result.success:
                    await conn.rollback()
                    break
            else:
                await conn.commit()
            return results
        except Exception as e:
            await conn.rollback()
            results.append(QueryResult(success=False, error=str(e)))
            return results
        finally:
            await self._pool.release(conn)
    
    async def fetch_one(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute SQL and fetch single row."""
        return await self._pool.fetch_one(sql, params)
    
    async def fetch_all(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute SQL and fetch all rows."""
        return await self._pool.fetch_all(sql, params)
    
    async def fetch_value(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> Any:
        """Execute SQL and fetch single value."""
        return await self._pool.fetch_value(sql, params)
    
    async def stream(
        self, 
        sql: str, 
        params: Optional[tuple] = None,
        batch_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream results for large queries."""
        conn = await self._pool.acquire()
        try:
            async with conn.cursor(aiomysql.SSCursor) as cursor:
                await cursor.execute(sql, params or ())
                while True:
                    rows = await cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    for row in rows:
                        yield dict(row)
        finally:
            await self._pool.release(conn)