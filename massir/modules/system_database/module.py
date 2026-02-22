"""
System Database Module - Async database middleware for relational databases.

This module provides a unified interface for working with PostgreSQL, MySQL,
and SQLite databases with connection pooling, caching, and transaction support.
"""
from typing import Optional, List, Dict, Any
from massir.core.interfaces import IModule

from .database_service import DatabaseService
from .core.types import (
    DatabaseConfig, TableDef, ColumnDef, IndexDef,
    ForeignKeyDef, QueryResult, ColumnType
)


class DatabaseModule(IModule):
    """
    System database module.
    
    Provides database services for other modules to use.
    Supports PostgreSQL, MySQL, and SQLite.
    """
    
    name = "system_database"
    provides = ["database_service"]
    
    def __init__(self):
        self._service: Optional[DatabaseService] = None
        self._logger = None
        self._config = None
    
    async def load(self, context):
        """Initialize database service."""
        self._logger = context.services.get("core_logger")
        self._config = context.services.get("core_config")
        
        # Create database service
        self._service = DatabaseService()
        self._service.set_logger(self._logger)
        
        # Register service
        context.services.set("database_service", self._service)
        
        # Register types for other modules to use
        context.services.set("database_types", {
            "DatabaseConfig": DatabaseConfig,
            "TableDef": TableDef,
            "ColumnDef": ColumnDef,
            "IndexDef": IndexDef,
            "ForeignKeyDef": ForeignKeyDef,
            "QueryResult": QueryResult,
            "ColumnType": ColumnType
        })
        
        if self._logger:
            self._logger.log("DatabaseModule loaded", tag="database")
    
    async def start(self, context):
        """Start database connections from configuration."""
        if not self._service:
            return
        
        # Get database configurations from settings
        db_configs = self._get_database_configs()
        
        if db_configs:
            # Get cache settings
            cache_enabled = self._config.get("database.cache.enabled", True) if self._config else True
            cache_ttl = self._config.get("database.cache.ttl", 300) if self._config else 300
            cache_max_size = self._config.get("database.cache.max_size", 1000) if self._config else 1000
            
            await self._service.initialize(
                configs=db_configs,
                cache_enabled=cache_enabled,
                cache_ttl=cache_ttl,
                cache_max_size=cache_max_size
            )
            
            if self._logger:
                self._logger.log(
                    f"Database service started with {len(self._service.connections)} connection(s)",
                    tag="database"
                )
        elif self._logger:
            self._logger.log(
                "No database configurations found in settings",
                level="WARNING",
                tag="database"
            )
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self._logger:
            self._logger.log("DatabaseModule is ready", tag="database")
    
    async def stop(self, context):
        """Stop database service and close all connections."""
        if self._service:
            await self._service.close_all()
            
            if self._logger:
                self._logger.log("DatabaseModule stopped", tag="database")
    
    def _get_database_configs(self) -> List[Dict[str, Any]]:
        """
        Get database configurations from settings.
        
        Expected format in app_settings.json:
        {
            "database": {
                "connections": [
                    {
                        "name": "default",
                        "driver": "postgresql",
                        "host": "localhost",
                        "port": 5432,
                        "database": "myapp",
                        "user": "admin",
                        "password": "secret",
                        "pool_min_size": 5,
                        "pool_max_size": 20
                    },
                    {
                        "name": "cache_db",
                        "driver": "sqlite",
                        "path": "{app_dir}/data/cache.db"
                    }
                ],
                "cache": {
                    "enabled": true,
                    "ttl": 300,
                    "max_size": 1000
                }
            }
        }
        """
        if not self._config:
            return []
        
        # Try to get database configurations
        db_settings = self._config.get("database", {})
        
        if isinstance(db_settings, dict):
            connections = db_settings.get("connections", [])
            if connections:
                return connections
        
        # Also support legacy format with single "databases" key
        databases = self._config.get("databases", [])
        if databases:
            return databases
        
        return []


# Export main classes for convenience
__all__ = [
    "DatabaseModule",
    "DatabaseService",
    "DatabaseConfig",
    "TableDef",
    "ColumnDef",
    "IndexDef",
    "ForeignKeyDef",
    "QueryResult",
    "ColumnType"
]
