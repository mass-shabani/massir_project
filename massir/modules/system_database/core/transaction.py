"""
Base transaction class for database transactions.
"""
from abc import ABC, abstractmethod
from typing import Optional

from .exceptions import TransactionError


class BaseTransaction(ABC):
    """Abstract base class for transaction management."""
    
    def __init__(self, pool):
        self._pool = pool
        self._connection = None
        self._is_active = False
        self._savepoint_counter = 0
    
    @abstractmethod
    async def begin(self) -> bool:
        """Begin the transaction."""
        pass
    
    @abstractmethod
    async def commit(self) -> bool:
        """Commit the transaction."""
        pass
    
    @abstractmethod
    async def rollback(self) -> bool:
        """Rollback the transaction."""
        pass
    
    @abstractmethod
    async def savepoint(self, name: Optional[str] = None) -> str:
        """Create a savepoint for nested transactions."""
        pass
    
    @abstractmethod
    async def rollback_to_savepoint(self, name: str) -> bool:
        """Rollback to a savepoint."""
        pass
    
    @abstractmethod
    async def release_savepoint(self, name: str) -> bool:
        """Release a savepoint."""
        pass
    
    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self._is_active
    
    async def __aenter__(self):
        await self.begin()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()
        return False