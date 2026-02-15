"""
Base SQL executor for raw SQL operations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncIterator

from .types import QueryResult


class BaseSQLExecutor(ABC):
    """Abstract base class for raw SQL execution."""
    
    def __init__(self, pool):
        self._pool = pool
    
    @abstractmethod
    async def execute(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute raw SQL."""
        pass
    
    @abstractmethod
    async def execute_script(
        self, 
        script: str
    ) -> List[QueryResult]:
        """Execute multiple SQL statements."""
        pass
    
    @abstractmethod
    async def fetch_one(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute SQL and fetch single row."""
        pass
    
    @abstractmethod
    async def fetch_all(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute SQL and fetch all rows."""
        pass
    
    @abstractmethod
    async def fetch_value(
        self, 
        sql: str, 
        params: Optional[tuple] = None
    ) -> Any:
        """Execute SQL and fetch single value."""
        pass
    
    @abstractmethod
    async def stream(
        self, 
        sql: str, 
        params: Optional[tuple] = None,
        batch_size: int = 1000
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream results for large queries."""
        pass