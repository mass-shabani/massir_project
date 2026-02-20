"""
Multi-Database Service - Service layer components.

This package provides:
- models: Data models (ConnectionInfo, LogEntry, LogManager)
- connection: Connection management (ConnectionManager)
- tables: Table operations (TableManager)
- data: Data operations (DataManager)
- database: Unified aggregator (MultiDatabaseManager)
"""

from .models import ConnectionInfo, LogEntry, LogManager
from .connection import ConnectionManager
from .tables import TableManager
from .data import DataManager
from .database import MultiDatabaseManager

__all__ = [
    # Models
    "ConnectionInfo",
    "LogEntry",
    "LogManager",
    # Managers
    "ConnectionManager",
    "TableManager",
    "DataManager",
    # Aggregator
    "MultiDatabaseManager",
]
