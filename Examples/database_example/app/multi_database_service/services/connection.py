"""
Connection management for Multi-Database Manager.

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


class ConnectionMixin:
    """
    Mixin class for connection management operations.
    
    Requires the following attributes:
    - _db_service: DatabaseService instance
    - _db_types: Dictionary of database types from context
    - _log: Logging function
    - _log_manager: LogManager instance
    - _path_manager: Path manager for resolving paths
    - _active_connection: Name of active connection
    - _connection_info: Dict of ConnectionInfo objects
    """
    
    def _resolve_path(self: "ConnectionMixin", path: str) -> str:
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
    
    async def test_connection(self: "ConnectionMixin", config: dict) -> Dict[str, Any]:
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
    
    async def create_database(self: "ConnectionMixin", config: dict) -> Dict[str, Any]:
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
    
    async def connect(self: "ConnectionMixin", config: dict) -> Dict[str, Any]:
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
    
    async def disconnect(self: "ConnectionMixin", name: str = None) -> Dict[str, Any]:
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
    
    def is_connected(self: "ConnectionMixin", name: str = None) -> bool:
        """Check if connected."""
        conn_name = name or self._active_connection
        return self._db_service.has_connection(conn_name) if conn_name else False
    
    def get_connection(self: "ConnectionMixin", name: str = None) -> Optional[ConnectionInfo]:
        """Get connection info."""
        conn_name = name or self._active_connection
        return self._connection_info.get(conn_name) if conn_name else None
    
    def get_connections(self: "ConnectionMixin") -> list:
        """Get all connections info."""
        return [conn.to_dict() for conn in self._connection_info.values()]
    
    def get_active_connection_name(self: "ConnectionMixin") -> Optional[str]:
        """Get active connection name."""
        return self._active_connection
    
    def set_active_connection(self: "ConnectionMixin", name: str) -> bool:
        """Set a connection as active."""
        if name in self._connection_info:
            self._active_connection = name
            return True
        return False
