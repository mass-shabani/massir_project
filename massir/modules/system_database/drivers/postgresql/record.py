"""
PostgreSQL record manager implementation.
"""
import time
from typing import Any, Dict, List, Optional, AsyncIterator

from ...core.record import BaseRecordManager
from ...core.types import DatabaseType, QueryResult
from .connection import PostgreSQLPool


class PostgreSQLRecordManager(BaseRecordManager):
    """PostgreSQL record manager implementation."""
    
    def __init__(self, pool: PostgreSQLPool):
        super().__init__(pool, DatabaseType.POSTGRESQL)
        self._pool = pool
    
    def _build_where_clause(
        self, 
        where: Dict[str, Any],
        param_start: int = 1
    ) -> tuple:
        """Build WHERE clause from dictionary with $1, $2 style params."""
        if not where:
            return "", ()
        
        conditions = []
        params = []
        param_idx = param_start
        
        for key, value in where.items():
            if value is None:
                conditions.append(f"{key} IS NULL")
            else:
                conditions.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1
        
        return " AND ".join(conditions), tuple(params)
    
    async def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        returning: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert a single record."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f"${i+1}" for i in range(len(data))])
        
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        if returning:
            sql += f" RETURNING {', '.join(returning)}"
        else:
            sql += " RETURNING *"
        
        start_time = time.time()
        try:
            row = await self._pool.fetch_one(sql, tuple(data.values()))
            return QueryResult(
                success=True,
                affected_rows=1,
                last_insert_id=list(row.values())[0] if row else None,
                rows=[row] if row else [],
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return QueryResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def insert_many(
        self, 
        table: str, 
        data: List[Dict[str, Any]]
    ) -> QueryResult:
        """Insert multiple records."""
        if not data:
            return QueryResult(success=True, affected_rows=0)
        
        # Use COPY for bulk insert (more efficient)
        columns = list(data[0].keys())
        col_list = ", ".join(columns)
        
        # Build values with proper placeholders
        total_affected = 0
        start_time = time.time()
        
        try:
            async with self._pool._pool.acquire() as conn:
                async with conn.transaction():
                    for row in data:
                        values = [row[col] for col in columns]
                        placeholders = ", ".join([f"${i+1}" for i in range(len(values))])
                        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
                        await conn.execute(sql, *values)
                        total_affected += 1
            
            return QueryResult(
                success=True,
                affected_rows=total_affected,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return QueryResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def update(
        self, 
        table: str, 
        data: Dict[str, Any],
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> QueryResult:
        """Update records."""
        set_parts = [f"{k} = ${i+1}" for i, k in enumerate(data.keys())]
        set_clause = ", ".join(set_parts)
        params = list(data.values())
        
        if where_sql:
            where_clause = where_sql
            if where_params:
                # Re-number placeholders in where_sql
                offset = len(params)
                for i, p in enumerate(where_params):
                    params.append(p)
                where_clause = where_sql.replace("$1", f"${offset + 1}")
        else:
            where_clause, where_p = self._build_where_clause(where, len(params) + 1)
            params.extend(where_p)
        
        sql = f"UPDATE {table} SET {set_clause}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        
        return await self._pool.execute(sql, tuple(params))
    
    async def delete(
        self, 
        table: str,
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> QueryResult:
        """Delete records."""
        params = []
        
        if where_sql:
            where_clause = where_sql
            params = list(where_params or ())
        else:
            where_clause, params = self._build_where_clause(where)
        
        sql = f"DELETE FROM {table}"
        if where_clause:
            sql += f" WHERE {where_clause}"
        
        return await self._pool.execute(sql, tuple(params))
    
    async def find_one(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a single record."""
        col_list = ", ".join(columns) if columns else "*"
        sql = f"SELECT {col_list} FROM {table}"
        params = ()
        
        if where:
            where_clause, params = self._build_where_clause(where)
            sql += f" WHERE {where_clause}"
        
        if order_by:
            sql += f" ORDER BY {', '.join(order_by)}"
        
        sql += " LIMIT 1"
        
        return await self._pool.fetch_one(sql, params)
    
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
        col_list = ", ".join(columns) if columns else "*"
        sql = f"SELECT {col_list} FROM {table}"
        params = ()
        
        if where:
            where_clause, params = self._build_where_clause(where)
            sql += f" WHERE {where_clause}"
        
        if order_by:
            sql += f" ORDER BY {', '.join(order_by)}"
        
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
        
        return await self._pool.fetch_all(sql, params)
    
    async def count(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> int:
        """Count records."""
        sql = f"SELECT COUNT(*) FROM {table}"
        params = ()
        
        if where_sql:
            sql += f" WHERE {where_sql}"
            params = where_params or ()
        elif where:
            where_clause, params = self._build_where_clause(where)
            sql += f" WHERE {where_clause}"
        
        result = await self._pool.fetch_value(sql, params)
        return result or 0
    
    async def exists(
        self, 
        table: str,
        where: Dict[str, Any]
    ) -> bool:
        """Check if records exist."""
        count = await self.count(table, where)
        return count > 0
    
    async def upsert(
        self, 
        table: str, 
        data: Dict[str, Any],
        key_columns: List[str],
        update_columns: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert or update record (upsert) using ON CONFLICT."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f"${i+1}" for i in range(len(data))])
        
        # ON CONFLICT clause
        key_cols = ", ".join(key_columns)
        
        if update_columns:
            update_parts = [f"{col} = EXCLUDED.{col}" for col in update_columns]
        else:
            update_parts = [f"{col} = EXCLUDED.{col}" for col in data.keys() if col not in key_columns]
        
        update_clause = ", ".join(update_parts) if update_parts else ""
        
        sql = f"""
            INSERT INTO {table} ({columns}) VALUES ({placeholders})
            ON CONFLICT ({key_cols}) DO UPDATE SET {update_clause}
            RETURNING *
        """
        
        start_time = time.time()
        try:
            row = await self._pool.fetch_one(sql, tuple(data.values()))
            return QueryResult(
                success=True,
                affected_rows=1,
                rows=[row] if row else [],
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return QueryResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    async def stream(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        batch_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream records for large result sets."""
        offset = 0
        while True:
            batch = await self.find_many(
                table, where, columns, order_by,
                limit=batch_size, offset=offset
            )
            if not batch:
                break
            for row in batch:
                yield row
            offset += batch_size