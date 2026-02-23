"""
Transaction operations service for Database Transactions Module.

This module provides transaction-related operations:
- Begin, commit, rollback transactions
- Execute raw SQL queries
- Get transaction status
"""
from typing import Any, Dict, List, Optional


class TransactionsService:
    """
    Service for transaction management operations.
    
    Requires the following from connection_service:
    - get_database_service(): Returns the DatabaseService instance
    - get_active_connection_name(): Returns the active connection name
    - is_connected(): Checks if there's an active connection
    - _log: Logging function
    """
    
    def __init__(self, connection_service):
        """
        Initialize the transactions service.
        
        Args:
            connection_service: ConnectionService instance from db_connection module
        """
        self._connection = connection_service
        self._db_service = connection_service.get_database_service()
        self._log = connection_service._log
        self._active_transaction = None
        self._transaction_obj = None
    
    @property
    def _active_connection(self):
        """Get active connection name."""
        return self._connection.get_active_connection_name()
    
    async def begin_transaction(self, name: str = None) -> Dict[str, Any]:
        """Begin a new transaction."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            # Create a new transaction object
            self._transaction_obj = conn.transaction()
            await self._transaction_obj.begin()
            self._active_transaction = conn_name
            self._log(f"Transaction started on {conn_name}", "INFO")
            return {"success": True, "message": "Transaction started"}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to begin transaction: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
    
    async def commit_transaction(self, name: str = None) -> Dict[str, Any]:
        """Commit the current transaction."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            if self._transaction_obj:
                await self._transaction_obj.commit()
                self._transaction_obj = None
                self._active_transaction = None
                self._log(f"Transaction committed on {conn_name}", "INFO")
                return {"success": True, "message": "Transaction committed"}
            else:
                return {"success": False, "error": "No active transaction"}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to commit transaction: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
    
    async def rollback_transaction(self, name: str = None) -> Dict[str, Any]:
        """Rollback the current transaction."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            if self._transaction_obj:
                await self._transaction_obj.rollback()
                self._transaction_obj = None
                self._active_transaction = None
                self._log(f"Transaction rolled back on {conn_name}", "INFO")
                return {"success": True, "message": "Transaction rolled back"}
            else:
                return {"success": False, "error": "No active transaction"}
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to rollback transaction: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
    
    async def execute_sql(self, sql: str, params: List = None, name: str = None) -> Dict[str, Any]:
        """Execute raw SQL query."""
        conn_name = name or self._active_connection
        if not conn_name or not self._db_service.has_connection(conn_name):
            return {"success": False, "error": "No connection"}
        
        try:
            conn = self._db_service.get_connection(conn_name)
            
            # Use fetch_all for SELECT queries, execute for others
            sql_upper = sql.strip().upper()
            if sql_upper.startswith("SELECT") or sql_upper.startswith("SHOW") or sql_upper.startswith("PRAGMA"):
                rows = await conn.fetch_all(sql, params or [])
                self._log(f"Executed query: {sql[:100]}...", "INFO")
                return {
                    "success": True,
                    "rows": rows[:100] if rows else [],  # Limit to 100 rows
                    "rowcount": len(rows) if rows else 0
                }
            else:
                result = await conn.execute(sql, params or [])
                self._log(f"Executed SQL: {sql[:100]}...", "INFO")
                return {
                    "success": True,
                    "rowcount": result.rowcount,
                    "last_insert_id": result.last_insert_id
                }
        except Exception as e:
            error_msg = str(e)
            self._log(f"SQL execution failed: {error_msg}", "ERROR")
            return {"success": False, "error": error_msg}
    
    def get_transaction_status(self) -> Dict[str, Any]:
        """Get current transaction status."""
        return {
            "active_transaction": self._active_transaction,
            "has_active": self._active_transaction is not None
        }
