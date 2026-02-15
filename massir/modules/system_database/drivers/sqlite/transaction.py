"""
SQLite transaction implementation.
"""
from typing import Optional

from ...core.transaction import BaseTransaction
from ...core.exceptions import TransactionError
from .connection import SQLitePool


class SQLiteTransaction(BaseTransaction):
    """SQLite transaction implementation."""
    
    def __init__(self, pool: SQLitePool):
        super().__init__(pool)
        self._pool = pool
    
    async def begin(self) -> bool:
        """Begin the transaction."""
        if self._is_active:
            return True
        
        self._connection = await self._pool.acquire()
        await self._connection.begin_transaction()
        self._is_active = True
        return True
    
    async def commit(self) -> bool:
        """Commit the transaction."""
        if not self._is_active:
            return False
        
        await self._connection.commit()
        self._is_active = False
        await self._pool.release(self._connection)
        self._connection = None
        return True
    
    async def rollback(self) -> bool:
        """Rollback the transaction."""
        if not self._is_active:
            return False
        
        await self._connection.rollback()
        self._is_active = False
        await self._pool.release(self._connection)
        self._connection = None
        return True
    
    async def savepoint(self, name: Optional[str] = None) -> str:
        """Create a savepoint for nested transactions."""
        if not self._is_active:
            raise TransactionError("No active transaction")
        
        if not name:
            self._savepoint_counter += 1
            name = f"sp_{self._savepoint_counter}"
        
        await self._connection.execute(f"SAVEPOINT {name}")
        return name
    
    async def rollback_to_savepoint(self, name: str) -> bool:
        """Rollback to a savepoint."""
        if not self._is_active:
            raise TransactionError("No active transaction")
        
        await self._connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        return True
    
    async def release_savepoint(self, name: str) -> bool:
        """Release a savepoint."""
        if not self._is_active:
            raise TransactionError("No active transaction")
        
        await self._connection.execute(f"RELEASE SAVEPOINT {name}")
        return True