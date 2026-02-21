"""
Multi-Database Service - Services Package.

This package provides a unified multi-database manager that uses
the system_database module for all database operations.
"""
from .models import ConnectionInfo, LogEntry, LogManager
from .database import MultiDatabaseManager

__all__ = [
    "ConnectionInfo",
    "LogEntry", 
    "LogManager",
    "MultiDatabaseManager",
]
