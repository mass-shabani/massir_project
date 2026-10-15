"""
PostgreSQL raw SQL executor implementation.
"""
from typing import Any, Dict, List, Optional, AsyncIterator

from ...core.sql import BaseSQLExecutor
from ...core.types import QueryResult
from .connection import PostgreSQLPool


def _split_sql_statements(script: str) -> List[str]:
    """Split SQL script into statements, respecting quotes and comments."""
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    while i < len(script):
        ch = script[i]
        next_ch = script[i+1] if i+1 < len(script) else ""
        
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            current.append(ch)
        elif in_block_comment:
            current.append(ch)
            if ch == "*" and next_ch == "/":
                current.append(next_ch)
                i += 1
                in_block_comment = False
        elif in_single_quote:
            current.append(ch)
            if ch == "'":
                if next_ch == "'":
                    current.append(next_ch)
                    i += 1
                else:
                    in_single_quote = False
        elif in_double_quote:
            current.append(ch)
            if ch == '"':
                in_double_quote = False
        else:
            if ch == "-" and next_ch == "-":
                in_line_comment = True
                current.append(ch)
            elif ch == "/" and next_ch == "*":
                in_block_comment = True
                current.append(ch)
            elif ch == "'":
                in_single_quote = True
                current.append(ch)
            elif ch == '"':
                in_double_quote = True
                current.append(ch)
            elif ch == ";":
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(ch)
        i += 1
    
    stmt = "".join(current).strip()
    if stmt:
        statements.append(stmt)
    return statements


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
        statements = _split_sql_statements(script)
        
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