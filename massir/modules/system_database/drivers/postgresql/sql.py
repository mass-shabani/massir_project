"""
PostgreSQL raw SQL executor implementation.
"""
from typing import Any, Dict, List, Optional, AsyncIterator

from ...core.sql import BaseSQLExecutor
from ...core.types import QueryResult
from .connection import PostgreSQLPool


class PostgreSQLSQLExecutor(BaseSQLExecutor):
    """PostgreSQL raw SQL executor implementation."""
    
    def __init__(self, pool: PostgreSQLPool):
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
        
        for stmt in statements:
            result = await self._pool.execute(stmt)
            results.append(result)
            if not result.success:
                break
        
        return results
    
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
        row = await self._pool.fetch_one(sql, params)
        if row:
            return list(row.values())[0]
        return None
    
    async def stream(
        self, 
        sql: str, 
        params: Optional[tuple] = None,
        batch_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream results for large queries using cursor."""
        async with self._pool._pool.acquire() as conn:
            async with conn.transaction():
                # Use a server-side cursor for large results
                async for row in conn.cursor(sql, *(params or ())):
                    yield dict(row)