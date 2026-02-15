"""
Base record manager for DML operations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator

from .types import QueryResult, DatabaseType


class BaseRecordManager(ABC):
    """Abstract base class for record operations (DML)."""
    
    def __init__(self, pool, db_type: DatabaseType):
        self._pool = pool
        self._db_type = db_type
    
    @abstractmethod
    async def insert(
        self, 
        table: str, 
        data: Dict[str, Any],
        returning: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert a single record."""
        pass
    
    @abstractmethod
    async def insert_many(
        self, 
        table: str, 
        data: List[Dict[str, Any]]
    ) -> QueryResult:
        """Insert multiple records."""
        pass
    
    @abstractmethod
    async def update(
        self, 
        table: str, 
        data: Dict[str, Any],
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> QueryResult:
        """Update records."""
        pass
    
    @abstractmethod
    async def delete(
        self, 
        table: str,
        where: Dict[str, Any],
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> QueryResult:
        """Delete records."""
        pass
    
    @abstractmethod
    async def find_one(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a single record."""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def count(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        where_sql: Optional[str] = None,
        where_params: Optional[tuple] = None
    ) -> int:
        """Count records."""
        pass
    
    @abstractmethod
    async def exists(
        self, 
        table: str,
        where: Dict[str, Any]
    ) -> bool:
        """Check if records exist."""
        pass
    
    @abstractmethod
    async def upsert(
        self, 
        table: str, 
        data: Dict[str, Any],
        key_columns: List[str],
        update_columns: Optional[List[str]] = None
    ) -> QueryResult:
        """Insert or update record (upsert)."""
        pass
    
    @abstractmethod
    async def stream(
        self, 
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None,
        batch_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream records for large result sets."""
        pass