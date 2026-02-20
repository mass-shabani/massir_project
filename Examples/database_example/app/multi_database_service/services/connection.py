"""
Connection management for Multi-Database Manager.

This module provides:
- Connection testing for SQLite, PostgreSQL, MySQL
- Connection establishment and management
- Connection state tracking
- Path resolution with support for {massir_dir}, {app_dir}, relative and absolute paths
"""
from typing import Any, Dict, Optional
from pathlib import Path
from datetime import datetime

from .models import ConnectionInfo, LogManager


class ConnectionManager:
    """Manages database connections for multiple database types."""
    
    def __init__(self, log_manager: LogManager, path_manager=None):
        self._connections: Dict[str, ConnectionInfo] = {}
        self._active_connection: Optional[str] = None
        self._log = log_manager.log
        self._path_manager = path_manager
    
    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path string to an absolute path.
        
        Supports:
        - {massir_dir} - Massir framework directory
        - {app_dir} - Application directory  
        - Relative paths (relative to app_dir)
        - Absolute paths
        """
        path_str = str(path)
        
        # Replace placeholders
        if "{massir_dir}" in path_str:
            if self._path_manager:
                massir_dir = self._path_manager.get("massir_dir")
                path_str = path_str.replace("{massir_dir}", massir_dir)
            else:
                # Fallback: assume massir is at project_root/massir
                path_str = path_str.replace("{massir_dir}", str(Path.cwd() / "massir"))
        
        if "{app_dir}" in path_str:
            if self._path_manager:
                app_dir = self._path_manager.get("app_dir")
                path_str = path_str.replace("{app_dir}", app_dir)
            else:
                # Fallback: use current working directory
                path_str = path_str.replace("{app_dir}", str(Path.cwd()))
        
        db_path = Path(path_str)
        
        # If not absolute, make it relative to app_dir
        if not db_path.is_absolute():
            if self._path_manager:
                app_dir = Path(self._path_manager.get("app_dir"))
                db_path = app_dir / path_str
            else:
                db_path = Path.cwd() / path_str
        
        return db_path.resolve()
    
    async def test_connection(self, config: dict) -> Dict[str, Any]:
        """
        Test a database connection without persisting it.
        
        Args:
            config: Connection configuration dictionary
            
        Returns:
            Dict with success status and message
        """
        driver = config.get("driver", "sqlite").lower()
        
        try:
            if driver == "sqlite":
                return await self._test_sqlite(config)
            elif driver in ("postgresql", "postgres", "psql"):
                return await self._test_postgresql(config)
            elif driver == "mysql":
                return await self._test_mysql(config)
            else:
                return {
                    "success": False,
                    "message": f"Unsupported database driver: {driver}"
                }
        except Exception as e:
            error_msg = str(e)
            self._log(f"Connection test failed: {error_msg}", "ERROR", driver)
            return {
                "success": False,
                "message": error_msg
            }
    
    async def _test_sqlite(self, config: dict) -> Dict[str, Any]:
        """Test SQLite connection - file must exist."""
        path = config.get("path", "data/test.db")
        
        # Resolve path
        db_path = self._resolve_path(path)
        
        # Check if file exists
        if not db_path.exists():
            self._log(f"SQLite file not found: {db_path}", "ERROR")
            return {
                "success": False,
                "message": f"Database file not found: {db_path}",
                "file_exists": False
            }
        
        # Check if it's a valid SQLite file
        try:
            import aiosqlite
            async with aiosqlite.connect(str(db_path)) as conn:
                await conn.execute("SELECT 1")
            
            self._log(f"SQLite connection test successful: {db_path}", "INFO")
            return {
                "success": True,
                "message": f"Successfully connected to SQLite database: {db_path}",
                "file_exists": True,
                "resolved_path": str(db_path)
            }
        except Exception as e:
            self._log(f"SQLite connection test failed: {e}", "ERROR")
            return {
                "success": False,
                "message": f"Failed to connect to database: {e}"
            }
    
    async def create_database(self, config: dict) -> Dict[str, Any]:
        """
        Create a new SQLite database.
        
        Args:
            config: Connection configuration dictionary
            
        Returns:
            Dict with success status and message
        """
        path = config.get("path", "data/new.db")
        
        # Resolve path
        db_path = self._resolve_path(path)
        
        # Check if file already exists
        if db_path.exists():
            self._log(f"Database file already exists: {db_path}", "WARNING")
            return {
                "success": False,
                "message": f"Database file already exists: {db_path}. Use 'Connect' to connect to it."
            }
        
        # Create directory if needed
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._log(f"Failed to create directory: {e}", "ERROR")
            return {
                "success": False,
                "message": f"Failed to create directory: {e}"
            }
        
        # Create the database file
        try:
            import aiosqlite
            async with aiosqlite.connect(str(db_path)) as conn:
                # Create a simple table to ensure the file is created
                await conn.execute("CREATE TABLE IF NOT EXISTS _init (id INTEGER PRIMARY KEY)")
                await conn.commit()
            
            self._log(f"Created new SQLite database: {db_path}", "INFO")
            return {
                "success": True,
                "message": f"Successfully created new SQLite database: {db_path}",
                "resolved_path": str(db_path)
            }
        except Exception as e:
            self._log(f"Failed to create database: {e}", "ERROR")
            return {
                "success": False,
                "message": f"Failed to create database: {e}"
            }
    
    async def _test_postgresql(self, config: dict) -> Dict[str, Any]:
        """Test PostgreSQL connection."""
        try:
            import asyncpg
            
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            database = config.get("database", "postgres")
            user = config.get("user", "postgres")
            password = config.get("password", "")
            
            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                timeout=10
            )
            await conn.execute("SELECT 1")
            await conn.close()
            
            self._log(f"PostgreSQL connection test successful: {host}:{port}/{database}", "INFO")
            return {
                "success": True,
                "message": f"Successfully connected to PostgreSQL: {host}:{port}/{database}"
            }
        except ImportError:
            return {
                "success": False,
                "message": "asyncpg library not installed. Run: pip install asyncpg"
            }
        except Exception as e:
            self._log(f"PostgreSQL connection test failed: {e}", "ERROR")
            return {
                "success": False,
                "message": str(e)
            }
    
    async def _test_mysql(self, config: dict) -> Dict[str, Any]:
        """Test MySQL connection."""
        try:
            import aiomysql
            
            host = config.get("host", "localhost")
            port = config.get("port", 3306)
            database = config.get("database", "mysql")
            user = config.get("user", "root")
            password = config.get("password", "")
            
            conn = await aiomysql.connect(
                host=host,
                port=port,
                db=database,  # aiomysql uses 'db' not 'database'
                user=user,
                password=password,
                connect_timeout=10
            )
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
            conn.close()
            
            self._log(f"MySQL connection test successful: {host}:{port}/{database}", "INFO")
            return {
                "success": True,
                "message": f"Successfully connected to MySQL: {host}:{port}/{database}"
            }
        except ImportError:
            return {
                "success": False,
                "message": "aiomysql library not installed. Run: pip install aiomysql"
            }
        except Exception as e:
            self._log(f"MySQL connection test failed: {e}", "ERROR")
            return {
                "success": False,
                "message": str(e)
            }
    
    async def connect(self, config: dict) -> Dict[str, Any]:
        """
        Create and establish a database connection.
        
        Args:
            config: Connection configuration dictionary
            
        Returns:
            Dict with success status and connection info
        """
        name = config.get("name", "default")
        driver = config.get("driver", "sqlite").lower()
        
        # Check if connection already exists
        if name in self._connections and self._connections[name].connected:
            return {
                "success": False,
                "message": f"Connection '{name}' already exists. Disconnect first."
            }
        
        # Test connection first
        test_result = await self.test_connection(config)
        if not test_result["success"]:
            return test_result
        
        # Store resolved path for SQLite
        resolved_path = test_result.get("resolved_path", config.get("path"))
        
        # Create connection info
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
        
        # Store resolved path
        conn_info.resolved_path = resolved_path
        
        self._connections[name] = conn_info
        
        # Set as active if first connection
        if self._active_connection is None:
            self._active_connection = name
        
        self._log(f"Connected to {driver} database: {name}", "INFO")
        
        return {
            "success": True,
            "message": f"Successfully connected to {driver} database: {name}",
            "connection": conn_info.to_dict()
        }
    
    async def disconnect(self, name: str) -> Dict[str, Any]:
        """
        Disconnect a database connection.
        
        Args:
            name: Connection name
            
        Returns:
            Dict with success status
        """
        if name not in self._connections:
            return {
                "success": False,
                "message": f"Connection '{name}' not found"
            }
        
        conn_info = self._connections[name]
        conn_info.connected = False
        conn_info.connection_time = None
        
        # Remove from connections
        del self._connections[name]
        
        # Update active connection
        if self._active_connection == name:
            self._active_connection = next(iter(self._connections), None)
        
        self._log(f"Disconnected from database: {name}", "INFO")
        
        return {
            "success": True,
            "message": f"Disconnected from {name}"
        }
    
    async def disconnect_all(self):
        """Disconnect all database connections."""
        for name in list(self._connections.keys()):
            await self.disconnect(name)
    
    def get_connections(self) -> list:
        """Get all connection info."""
        return [conn.to_dict() for conn in self._connections.values()]
    
    def get_connection(self, name: str = None) -> Optional[ConnectionInfo]:
        """Get a specific connection or the active one."""
        if name:
            return self._connections.get(name)
        return self._connections.get(self._active_connection) if self._active_connection else None
    
    def get_active_connection_name(self) -> Optional[str]:
        """Get the name of the active connection."""
        return self._active_connection
    
    def set_active_connection(self, name: str) -> bool:
        """Set the active connection."""
        if name in self._connections:
            self._active_connection = name
            self._log(f"Active connection changed to: {name}", "INFO")
            return True
        return False
    
    def is_connected(self, name: str = None) -> bool:
        """Check if a connection is active."""
        conn = self.get_connection(name)
        return conn.connected if conn else False
    
    async def get_connection_object(self, name: str = None):
        """Get a raw database connection object for operations."""
        conn_info = self.get_connection(name)
        if not conn_info or not conn_info.connected:
            raise ValueError("No active database connection")
        
        driver = conn_info.driver.lower()
        
        if driver == "sqlite":
            import aiosqlite
            # Use resolved path if available
            path = getattr(conn_info, 'resolved_path', None) or conn_info.path or "data/default.db"
            db_path = self._resolve_path(path) if not Path(path).is_absolute() else Path(path)
            return await aiosqlite.connect(str(db_path))
        
        elif driver in ("postgresql", "postgres", "psql"):
            import asyncpg
            return await asyncpg.connect(
                host=conn_info.host,
                port=conn_info.port or 5432,
                database=conn_info.database or "postgres",
                user=conn_info.user or "postgres",
                password=conn_info.password or ""
            )
        
        elif driver == "mysql":
            import aiomysql
            return await aiomysql.connect(
                host=conn_info.host,
                port=conn_info.port or 3306,
                db=conn_info.database or "mysql",  # aiomysql uses 'db' not 'database'
                user=conn_info.user or "root",
                password=conn_info.password or ""
            )
        
        raise ValueError(f"Unsupported driver: {driver}")
