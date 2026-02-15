"""
Base schema manager for DDL operations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .types import TableDef, ColumnDef, IndexDef, ForeignKeyDef, QueryResult, DatabaseType


class BaseSchemaManager(ABC):
    """Abstract base class for schema operations (DDL)."""
    
    def __init__(self, pool, db_type: DatabaseType):
        self._pool = pool
        self._db_type = db_type
    
    @abstractmethod
    async def create_table(
        self, 
        table_def: TableDef
    ) -> QueryResult:
        """Create a table."""
        pass
    
    @abstractmethod
    async def drop_table(
        self, 
        name: str, 
        if_exists: bool = True,
        cascade: bool = False
    ) -> QueryResult:
        """Drop a table."""
        pass
    
    @abstractmethod
    async def alter_table(
        self, 
        name: str, 
        alterations: List[Dict[str, Any]]
    ) -> QueryResult:
        """Alter table structure."""
        pass
    
    @abstractmethod
    async def rename_table(
        self, 
        old_name: str, 
        new_name: str
    ) -> QueryResult:
        """Rename a table."""
        pass
    
    @abstractmethod
    async def table_exists(self, name: str) -> bool:
        """Check if table exists."""
        pass
    
    @abstractmethod
    async def get_table_schema(self, name: str) -> Optional[TableDef]:
        """Get table schema information."""
        pass
    
    @abstractmethod
    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        pass
    
    @abstractmethod
    async def create_index(
        self, 
        table: str, 
        index_def: IndexDef
    ) -> QueryResult:
        """Create an index."""
        pass
    
    @abstractmethod
    async def drop_index(
        self, 
        name: str, 
        table: Optional[str] = None
    ) -> QueryResult:
        """Drop an index."""
        pass
    
    @abstractmethod
    async def index_exists(
        self, 
        name: str, 
        table: Optional[str] = None
    ) -> bool:
        """Check if index exists."""
        pass
    
    @abstractmethod
    async def create_view(
        self, 
        name: str, 
        query: str,
        replace: bool = False
    ) -> QueryResult:
        """Create a view."""
        pass
    
    @abstractmethod
    async def drop_view(
        self, 
        name: str, 
        if_exists: bool = True
    ) -> QueryResult:
        """Drop a view."""
        pass
    
    @abstractmethod
    async def add_column(
        self, 
        table: str, 
        column: ColumnDef
    ) -> QueryResult:
        """Add a column to a table."""
        pass
    
    @abstractmethod
    async def drop_column(
        self, 
        table: str, 
        column_name: str
    ) -> QueryResult:
        """Drop a column from a table."""
        pass
    
    @abstractmethod
    async def add_foreign_key(
        self, 
        table: str, 
        fk: ForeignKeyDef
    ) -> QueryResult:
        """Add a foreign key constraint."""
        pass
    
    @abstractmethod
    async def drop_foreign_key(
        self, 
        table: str, 
        fk_name: str
    ) -> QueryResult:
        """Drop a foreign key constraint."""
        pass