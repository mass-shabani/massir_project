"""
MySQL record manager implementation.
"""
from typing import Any, Dict, List, Optional, AsyncIterator

from ...core.record import BaseRecordManager
from ...core.types import DatabaseType, QueryResult
from .connection import MySQLPool


class MySQLRecordManager(BaseRecordManager):
    """MySQL record manager implementation."""
    
    def __init__(self, pool: MySQLPool):
        super().__init__(pool, DatabaseType.MYSQL)
        self._pool = pool
    
    def _build_where_clause(
        self, 
        where: Dict[str, Any]
    ) -> tuple:
        """Build WHERE clause from dictionary with %s style params."""
        if not where:
            return "", ()
        
        conditions = []
        params = []
        
        for key, value in where.items():
            if value is None:
                conditions.append(f"{key} IS NULL")
            else:
                conditions.append(f"{key} = %s")
                params.append(value)
        
        return " AND ".join(conditions), tuple(params)
    
    async def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        returning: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert a single record."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s" for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        result = await self._pool.execute(sql, tuple(data.values()))
        
        # MySQL doesn't support RETURNING
        # Return the inserted data with last_insert_id
        if result.success and result.last_insert_id:
            result.rows = [data]
        
        return result
    
    async def insert_many(
        self, 
        table: str, 
        data: List[Dict[str, Any]]
    ) -> QueryResult:
        """Insert multiple records."""
        if not data:
            return QueryResult(success=True, affected_rows=0)
        
        columns = ", ".join(data[0].keys())
        placeholders = ", ".join(["%s" for _ in data[0]])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        # Batch insert
        total_affected = 0
        conn = await self._pool.acquire()
        try:
            await conn.begin()
            async with conn.cursor() as cursor:
                for row in data:
                    await cursor.execute(sql, tuple(row.values()))
                    total_affected += cursor.rowcount
            await conn.commit()
            return QueryResult(success=True, affected_rows=total_affected)
        except Exception as e:
            await conn.rollback()
            return QueryResult(success=False, error=str(e))
        finally:
            await self._pool.release(conn)
    
    async def update(
        self, 
        table: str, 
        data: Dict[str, Any],
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> QueryResult:
        """Update records."""
        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        params = list(data.values())
        
        if where_sql:
            where_clause = where_sql
            if where_params:
                params.extend(where_params)
        else:
            where_clause, where_p = self._build_where_clause(where)
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
        sql = f"SELECT COUNT(*) as cnt FROM {table}"
        params = ()
        
        if where_sql:
            sql += f" WHERE {where_sql}"
            params = where_params or ()
        elif where:
            where_clause, params = self._build_where_clause(where)
            sql += f" WHERE {where_clause}"
        
        result = await self._pool.fetch_one(sql, params)
        return result["cnt"] if result else 0
    
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
        """Insert or update record (upsert) using ON DUPLICATE KEY UPDATE."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s" for _ in data])
        
        if update_columns:
            update_parts = [f"{col} = VALUES({col})" for col in update_columns]
        else:
            update_parts = [f"{col} = VALUES({col})" for col in data.keys() if col not in key_columns]
        
        update_clause = ", ".join(update_parts) if update_parts else ""
        
        sql = f"""
            INSERT INTO {table} ({columns}) VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """
        
        return await self._pool.execute(sql, tuple(data.values()))
    
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