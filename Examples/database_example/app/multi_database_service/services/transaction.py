"""
Transaction management for Multi-Database Manager.

This module provides transaction-related operations:
- Begin/Commit/Rollback transactions
- Savepoint management
- Transaction status tracking
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class TransactionState(Enum):
    """Transaction state enumeration."""
    IDLE = "idle"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"


class TransactionInfo:
    """Information about a transaction."""
    
    def __init__(self, connection_name: str):
        self.connection_name = connection_name
        self.state = TransactionState.IDLE
        self.started_at: Optional[datetime] = None
        self.savepoints: List[str] = []
        self.operations_count = 0
        self.last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_name": self.connection_name,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "savepoints": self.savepoints,
            "operations_count": self.operations_count,
            "last_error": self.last_error
        }


class TransactionMixin:
    """
    Mixin class for transaction management operations.
    
    Requires the following attributes:
    - _db_service: DatabaseService instance
    - _log: Logging function
    - _active_connection: Name of active connection
    - _connection_info: Dict of ConnectionInfo objects
    """
    
    def __init__(self):
        self._transactions: Dict[str, TransactionInfo] = {}
    
    def _get_transaction(self: "TransactionMixin", connection_name: str = None) -> Optional[TransactionInfo]:
        """Get transaction info for a connection."""
        conn_name = connection_name or self._active_connection
        return self._transactions.get(conn_name) if conn_name else None
    
    async def begin_transaction(self: "TransactionMixin", connection_name: str = None) -> Dict[str, Any]:
        """Begin a new transaction."""
        conn_name = connection_name or self._active_connection
        
        if not conn_name:
            return {"success": False, "message": "No active connection"}
        
        if not self._db_service.has_connection(conn_name):
            return {"success": False, "message": f"Connection '{conn_name}' not found"}
        
        # Check if transaction already active
        if conn_name in self._transactions and self._transactions[conn_name].state == TransactionState.ACTIVE:
            return {"success": False, "message": "Transaction already active"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            # Execute BEGIN
            await conn.execute("BEGIN")
            
            # Track transaction
            tx_info = TransactionInfo(conn_name)
            tx_info.state = TransactionState.ACTIVE
            tx_info.started_at = datetime.now()
            self._transactions[conn_name] = tx_info
            
            self._log(f"Transaction started on '{conn_name}'", "INFO")
            
            return {
                "success": True,
                "message": f"Transaction started on '{conn_name}'",
                "transaction": tx_info.to_dict()
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to begin transaction: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def commit_transaction(self: "TransactionMixin", connection_name: str = None) -> Dict[str, Any]:
        """Commit the current transaction."""
        conn_name = connection_name or self._active_connection
        
        tx_info = self._get_transaction(conn_name)
        if not tx_info or tx_info.state != TransactionState.ACTIVE:
            return {"success": False, "message": "No active transaction to commit"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            await conn.execute("COMMIT")
            
            tx_info.state = TransactionState.COMMITTED
            self._log(f"Transaction committed on '{conn_name}'", "INFO")
            
            return {
                "success": True,
                "message": f"Transaction committed on '{conn_name}'",
                "transaction": tx_info.to_dict()
            }
        except Exception as e:
            error_msg = str(e)
            tx_info.last_error = error_msg
            self._log(f"Failed to commit transaction: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def rollback_transaction(self: "TransactionMixin", connection_name: str = None) -> Dict[str, Any]:
        """Rollback the current transaction."""
        conn_name = connection_name or self._active_connection
        
        tx_info = self._get_transaction(conn_name)
        if not tx_info or tx_info.state != TransactionState.ACTIVE:
            return {"success": False, "message": "No active transaction to rollback"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            await conn.execute("ROLLBACK")
            
            tx_info.state = TransactionState.ROLLED_BACK
            self._log(f"Transaction rolled back on '{conn_name}'", "INFO")
            
            return {
                "success": True,
                "message": f"Transaction rolled back on '{conn_name}'",
                "transaction": tx_info.to_dict()
            }
        except Exception as e:
            error_msg = str(e)
            tx_info.last_error = error_msg
            self._log(f"Failed to rollback transaction: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def create_savepoint(self: "TransactionMixin", name: str, connection_name: str = None) -> Dict[str, Any]:
        """Create a savepoint within the current transaction."""
        conn_name = connection_name or self._active_connection
        
        tx_info = self._get_transaction(conn_name)
        if not tx_info or tx_info.state != TransactionState.ACTIVE:
            return {"success": False, "message": "No active transaction"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            await conn.execute(f"SAVEPOINT {name}")
            
            tx_info.savepoints.append(name)
            self._log(f"Savepoint '{name}' created on '{conn_name}'", "INFO")
            
            return {
                "success": True,
                "message": f"Savepoint '{name}' created",
                "transaction": tx_info.to_dict()
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to create savepoint: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def rollback_to_savepoint(self: "TransactionMixin", name: str, connection_name: str = None) -> Dict[str, Any]:
        """Rollback to a savepoint."""
        conn_name = connection_name or self._active_connection
        
        tx_info = self._get_transaction(conn_name)
        if not tx_info or tx_info.state != TransactionState.ACTIVE:
            return {"success": False, "message": "No active transaction"}
        
        if name not in tx_info.savepoints:
            return {"success": False, "message": f"Savepoint '{name}' not found"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            await conn.execute(f"ROLLBACK TO SAVEPOINT {name}")
            
            # Remove savepoints created after this one
            idx = tx_info.savepoints.index(name)
            tx_info.savepoints = tx_info.savepoints[:idx + 1]
            
            self._log(f"Rolled back to savepoint '{name}' on '{conn_name}'", "INFO")
            
            return {
                "success": True,
                "message": f"Rolled back to savepoint '{name}'",
                "transaction": tx_info.to_dict()
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to rollback to savepoint: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    async def release_savepoint(self: "TransactionMixin", name: str, connection_name: str = None) -> Dict[str, Any]:
        """Release a savepoint."""
        conn_name = connection_name or self._active_connection
        
        tx_info = self._get_transaction(conn_name)
        if not tx_info or tx_info.state != TransactionState.ACTIVE:
            return {"success": False, "message": "No active transaction"}
        
        if name not in tx_info.savepoints:
            return {"success": False, "message": f"Savepoint '{name}' not found"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            await conn.execute(f"RELEASE SAVEPOINT {name}")
            
            tx_info.savepoints.remove(name)
            self._log(f"Savepoint '{name}' released on '{conn_name}'", "INFO")
            
            return {
                "success": True,
                "message": f"Savepoint '{name}' released",
                "transaction": tx_info.to_dict()
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to release savepoint: {error_msg}", "ERROR")
            return {"success": False, "message": error_msg}
    
    def get_transaction_info(self: "TransactionMixin", connection_name: str = None) -> Optional[Dict[str, Any]]:
        """Get transaction info for a connection."""
        tx_info = self._get_transaction(connection_name)
        return tx_info.to_dict() if tx_info else None
    
    def get_all_transactions(self: "TransactionMixin") -> List[Dict[str, Any]]:
        """Get all transaction infos."""
        return [tx.to_dict() for tx in self._transactions.values()]
    
    def clear_transaction(self: "TransactionMixin", connection_name: str):
        """Clear transaction info after disconnect."""
        if connection_name in self._transactions:
            del self._transactions[connection_name]
