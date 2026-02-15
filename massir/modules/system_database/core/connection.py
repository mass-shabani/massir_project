"""
Base connection and pool classes for database drivers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from .types import DatabaseConfig, QueryResult
from .exceptions import ConnectionError, PoolError


class BaseConnection(ABC):
    """Abstract base class for database connections."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        self._is_connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish database connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close database connection."""
        pass
    
    @abstractmethod
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute a query and return result."""
        pass
    
    @abstractmethod
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute query and fetch single row."""
        pass
    
    @abstractmethod
    async def fetch_all(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Execute query and fetch all rows."""
        pass
    
    @abstractmethod
    async def fetch_value(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Any:
        """Execute query and fetch single value."""
        pass
    
    @abstractmethod
    async def begin_transaction(self) -> bool:
        """Begin a transaction."""
        pass
    
    @abstractmethod
    async def commit(self) -> bool:
        """Commit current transaction."""
        pass
    
    @abstractmethod
    async def rollback(self) -> bool:
        """Rollback current transaction."""
        pass
    
    @abstractmethod
    async def ping(self) -> bool:
        """Check if connection is alive."""
        pass
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._is_connected
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions."""
        await self.begin_transaction()
        try:
            yield self
            await self.commit()
        except Exception:
            await self.rollback()
            raise


class BasePool(ABC):
    """Abstract base class for connection pools."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool = None
        self._is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the connection pool."""
        pass
    
    @abstractmethod
    async def close(self) -> bool:
        """Close all connections in the pool."""
        pass
    
    @abstractmethod
    async def acquire(self) -> BaseConnection:
        """Acquire a connection from the pool."""
        pass
    
    @abstractmethod
    async def release(self, connection: BaseConnection) -> None:
        """Release a connection back to the pool."""
        pass
    
    @abstractmethod
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> QueryResult:
        """Execute query using a connection from the pool."""
        pass
    
    @abstractmethod
    async def fetch_one(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row using a connection from the pool."""
        pass
    
    @abstractmethod
    async def fetch_all(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows using a connection from the pool."""
        pass
    
    @property
    @abstractmethod
    def size(self) -> int:
        """Current pool size."""
        pass
    
    @property
    @abstractmethod
    def idle_size(self) -> int:
        """Number of idle connections."""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if pool is initialized."""
        return self._is_initialized
    
    @asynccontextmanager
    async def connection(self):
        """Context manager for acquiring/releasing connections."""
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)