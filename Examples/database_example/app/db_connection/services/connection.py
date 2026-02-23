"""
Connection management service for Database Connection Module.

This module provides connection-related operations:
- Test connection
- Create database
- Connect/Disconnect
- Connection info management
"""
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path

from .models import ConnectionInfo, LogManager


class ConnectionService:
    """
    Connection management service that provides database connection services.
    
    This service is the core of the db_connection module and provides
    connection management to other modules.
    """
    
    def __init__(self, log_manager: LogManager, path_manager=None, database_service=None, database_types=None):
        """
        Initialize the connection service.
        
        Args:
            log_manager: LogManager instance for logging operations
            path_manager: Optional path manager for resolving path placeholders
            database_service: DatabaseService instance from system_database module (via context)
            database_types: Dictionary of database types from system_database module (via context)
        """
        # database_service must be provided via context
        if database_service is None:
            raise ValueError("database_service must be provided via context. Ensure system_database module is loaded.")
        
        self._db_service = database_service
        self._db_types = database_types or {}
        
        # Set logger for database service
        self._db_service.set_logger(type('Logger', (), {
            'log': lambda self, msg, level='INFO', tag=None: log_manager.log(msg, level, tag)
        })())
        
        # Store references
        self._log = log_manager.log
        self._log_manager = log_manager
        self._path_manager = path_manager
        
        # Connection state
        self._active_connection: Optional[str] = None
        self._connection_info: Dict[str, ConnectionInfo] = {}
    
    def _resolve_path(self, path: str) -> str:
        """Resolve path with support for placeholders."""
        path_str = str(path)
        
        if "{massir_dir}" in path_str:
            if self._path_manager:
                massir_dir = self._path_manager.get("massir_dir")
                path_str = path_str.replace("{massir_dir}", massir_dir)
        
        if "{app_dir}" in path_str:
            if self._path_manager:
                app_dir = self._path_manager.get("app_dir")
                path_str = path_str.replace("{app_dir}", app_dir)
        
        db_path = Path(path_str)
        
        if not db_path.is_absolute():
            if self._path_manager:
                app_dir = Path(self._path_manager.get("app_dir"))
                db_path = app_dir / path_str
        
        return str(db_path.resolve())
    
    async def test_connection(self, config: dict) -> Dict[str, Any]:
        """Test a database connection without persisting it."""
        driver = config.get("driver", "sqlite").lower()
        
        # Resolve path for SQLite
        if driver == "sqlite" and config.get("path"):
            resolved_path = self._resolve_path(config["path"])
            config = {**config, "path": resolved_path}
        
        result = await self._db_service.test_connection(config)
        
        if result["success"]:
            self._log(f"{driver.upper()} connection test successful", "INFO")
        else:
            self._log(f"Connection test failed: {result['message']}", "ERROR")
        
        return result
    
    async def create_database(self, config: dict) -> Dict[str, Any]:
        """Create a new SQLite database."""
        if config.get("path"):
            resolved_path = self._resolve_path(config["path"])
            config = {**config, "path": resolved_path}
        
        result = await self._db_service.create_database(config)
        
        if result["success"]:
            self._log(f"Created new database: {result.get('resolved_path', config.get('path'))}", "INFO")
        else:
            self._log(f"Failed to create database: {result['message']}", "ERROR")
        
        return result
    
    async def connect(self, config: dict) -> Dict[str, Any]:
        """Establish a database connection."""
        name = config.get("name", "default")
        driver = config.get("driver", "sqlite").lower()
        
        # Check if already connected
        if self._db_service.has_connection(name):
            return {
                "success": False,
                "message": f"Connection '{name}' already exists. Disconnect first."
            }
        
        # Resolve path for SQLite
        resolved_path = None
        if driver == "sqlite" and config.get("path"):
            resolved_path = self._resolve_path(config["path"])
            config = {**config, "path": resolved_path}
        
        # Test connection first
        test_result = await self.test_connection(config)
        if not test_result["success"]:
            return test_result
        
        try:
            # Build config with pool settings
            db_config_dict = {
                "name": name,
                "driver": driver,
                "host": config.get("host", "localhost"),
                "port": config.get("port"),
                "database": config.get("database"),
                "user": config.get("user"),
                "password": config.get("password"),
                "path": config.get("path"),
                # Pool settings
                "pool_min_size": config.get("pool_min_size", 5),
                "pool_max_size": config.get("pool_max_size", 20),
                "pool_timeout": config.get("pool_timeout", 30.0),
                "connect_timeout": config.get("connect_timeout", 10.0),
                # Cache settings
                "cache_enabled": config.get("cache_enabled", True),
                "cache_ttl": config.get("cache_ttl", 300)
            }
            
            # Get DatabaseConfig type from context
            DatabaseConfig = self._db_types.get("DatabaseConfig")
            
            if not DatabaseConfig:
                return {
                    "success": False,
                    "message": "Database types not available from context"
                }
            
            # Add connection to database service
            db_config = DatabaseConfig.from_dict(db_config_dict)
            await self._db_service.add_connection(db_config)
            
            # Store connection info
            conn_info = ConnectionInfo(
                name=name,
                driver=driver,
                host=config.get("host", "localhost"),
                port=config.get("port"),
                database=config.get("database"),
                user=config.get("user"),
                password=config.get("password"),
                path=config.get("path"),
                connected=True,
                connection_time=datetime.now()
            )
            if resolved_path:
                conn_info.resolved_path = resolved_path
            
            self._connection_info[name] = conn_info
            self._active_connection = name
            
            self._log(f"Connected to {driver} database: {name}", "INFO")
            
            return {
                "success": True,
                "message": f"Successfully connected to {driver} database: {name}",
                "connection": conn_info.to_dict()
            }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Failed to connect: {error_msg}", "ERROR")
            return {
                "success": False,
                "message": error_msg
            }
    
    async def disconnect(self, name: str = None) -> Dict[str, Any]:
        """Disconnect a database connection."""
        conn_name = name or self._active_connection
        
        if not conn_name:
            return {
                "success": False,
                "message": "No connection to disconnect"
            }
        
        if not self._db_service.has_connection(conn_name):
            return {
                "success": False,
                "message": f"Connection '{conn_name}' not found"
            }
        
        await self._db_service.remove_connection(conn_name)
        
        if conn_name in self._connection_info:
            del self._connection_info[conn_name]
        
        if self._active_connection == conn_name:
            self._active_connection = next(iter(self._connection_info), None)
        
        self._log(f"Disconnected from database: {conn_name}", "INFO")
        
        return {
            "success": True,
            "message": f"Disconnected from {conn_name}"
        }
    
    def is_connected(self, name: str = None) -> bool:
        """Check if connected."""
        conn_name = name or self._active_connection
        return self._db_service.has_connection(conn_name) if conn_name else False
    
    def get_connection(self, name: str = None) -> Optional[ConnectionInfo]:
        """Get connection info."""
        conn_name = name or self._active_connection
        return self._connection_info.get(conn_name) if conn_name else None
    
    def get_connections(self) -> list:
        """Get all connections info."""
        return [conn.to_dict() for conn in self._connection_info.values()]
    
    def get_active_connection_name(self) -> Optional[str]:
        """Get active connection name."""
        return self._active_connection
    
    def set_active_connection(self, name: str) -> bool:
        """Set a connection as active."""
        if name in self._connection_info:
            self._active_connection = name
            return True
        return False
    
    def get_database_service(self):
        """Get the underlying database service."""
        return self._db_service
    
    def get_database_types(self):
        """Get database types from context."""
        return self._db_types
    
    # ==================== Logging ====================
    
    def get_logs(self, count: int = 50) -> list:
        """Get recent logs."""
        return self._log_manager.get_logs(count) if hasattr(self, '_log_manager') else []
    
    def clear_logs(self):
        """Clear all logs."""
        if hasattr(self, '_log_manager'):
            self._log_manager.clear()
    
    # ==================== Cache & Pool ====================
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics from database service."""
        try:
            return self._db_service.cache_stats
        except Exception:
            return {}
    
    async def clear_cache(self):
        """Clear all cached data."""
        await self._db_service.clear_cache()
        self._log("Cache cleared", "INFO")
    
    def get_pool_info(self) -> Optional[Dict[str, Any]]:
        """Get connection pool information."""
        if not self._active_connection:
            return None
        
        try:
            conn = self._db_service.get_connection(self._active_connection)
            return {
                "size": conn.pool_size,
                "idle": conn.pool_idle
            }
        except Exception:
            return None
