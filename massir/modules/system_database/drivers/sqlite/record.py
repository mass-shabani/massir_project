"""
SQLite record manager implementation.
"""
from typing import Any, Dict, List, Optional, AsyncIterator

from ...core.record import BaseRecordManager
from ...core.types import DatabaseType, QueryResult
from .connection import SQLitePool


class SQLiteRecordManager(BaseRecordManager):
    """SQLite record manager implementation."""
    
    def __init__(self, pool: SQLitePool):
        super().__init__(pool, DatabaseType.SQLITE)
        self._pool = pool
    
    def _build_where_clause(
        self, 
        where: Dict[str, Any]
    ) -> tuple:
        """Build WHERE clause from dictionary."""
        if not where:
            return "", ()
        
        conditions = []
        params = []
        for key, value in where.items():
            if value is None:
                conditions.append(f"{key} IS NULL")
            else:
                conditions.append(f"{key} = ?")
                params.append(value)
        
        return " AND ".join(conditions), tuple(params)
    
    async def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        returning: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert a single record."""
        if not data:
            sql = f"INSERT INTO {table} DEFAULT VALUES"
            result = await self._pool.execute(sql, ())
            if result.success and result.last_insert_id and returning:
                row = await self.find_one(table, {"id": result.last_insert_id}, returning)
                if row is None:
                    row = await self.find_one(table, {"rowid": result.last_insert_id}, returning)
                if row:
                    result.rows = [row]
            return result
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        result = await self._pool.execute(sql, tuple(data.values()))
        
        if result.success and result.last_insert_id:
            if returning:
                row = await self.find_one(table, {"id": result.last_insert_id}, returning)
                if row is None:
                    row = await self.find_one(table, {"rowid": result.last_insert_id}, returning)
                if row:
                    result.rows = [row]
        
        return result
    
    async def insert_many(
        self, 
        table: str, 
        data: List[Dict[str, Any]]
    ) -> QueryResult:
        """Insert multiple records."""
        if not data:
            return QueryResult(success=True, affected_rows=0)
        
        columns = list(data[0].keys())
        if not columns:
            return QueryResult(
                success=False,
                error="no columns provided for insert_many"
            )
        
        for i, row in enumerate(data):
            if set(row.keys()) != set(columns):
                return QueryResult(
                    success=False,
                    error=f"row {i} has inconsistent columns"
                )
        
        col_list = ", ".join(columns)
        placeholders = ", ".join(["?" for _ in columns])
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        
        total_affected = 0
        conn = await self._pool.acquire()
        try:
            await conn.begin_transaction()
            for row in data:
                values = tuple(row[col] for col in columns)
                result = await conn.execute(sql, values)
                if not result.success:
                    await conn.rollback()
                    return result
                total_affected += result.affected_rows
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
        if not data:
            return QueryResult(
                success=False,
                error="no data provided for update"
            )
        
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
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
            if where_params:
                params = list(where_params)
        else:
            where_clause, where_p = self._build_where_clause(where)
            params = list(where_p)
        
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
        """Insert or update record (upsert)."""
        if not data:
            return QueryResult(
                success=False,
                error="no data provided for upsert"
            )
        
        # SQLite uses INSERT OR REPLACE
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        sql = f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
        
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