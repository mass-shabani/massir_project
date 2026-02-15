"""
SQLite raw SQL executor implementation.
"""
from typing import Any, Dict, List, Optional, AsyncIterator

from ...core.sql import BaseSQLExecutor
from ...core.types import QueryResult
from .connection import SQLitePool


class SQLiteSQLExecutor(BaseSQLExecutor):
    """SQLite raw SQL executor implementation."""
    
    def __init__(self, pool: SQLitePool):
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
        conn = await self._pool.acquire()
        try:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in script.split(";") if s.strip()]
            for stmt in statements:
                result = await conn.execute(stmt)
                results.append(result)
                if not result.success:
                    break
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
        conn = await self._pool.acquire()
        try:
            return await conn.fetch_value(sql, params)
        finally:
            await self._pool.release(conn)
    
    async def stream(
        self, 
        sql: str, 
        params: Optional[tuple] = None,
        batch_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream results for large queries."""
        # For SQLite, we fetch all and yield
        # A more sophisticated implementation could use LIMIT/OFFSET
        rows = await self.fetch_all(sql, params)
        for row in rows:
            yield row