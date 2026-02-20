"""
Models and utility classes for Multi-Database Manager.

This module provides:
- ConnectionInfo: Data class for connection information
- LogEntry: Data class for log entries
- LogManager: Manages log entries
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class ConnectionInfo:
    """Stores connection information and state."""
    name: str
    driver: str
    host: str = "localhost"
    port: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    path: Optional[str] = None
    connected: bool = False
    connection_time: Optional[datetime] = None
    error_message: str = ""
    resolved_path: Optional[str] = None  # Resolved absolute path for SQLite
    
    def to_dict(self) -> dict:
        """Convert to dictionary for display."""
        return {
            "name": self.name,
            "driver": self.driver,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "path": self.path,
            "resolved_path": self.resolved_path,
            "connected": self.connected,
            "connection_time": str(self.connection_time) if self.connection_time else None,
            "error_message": self.error_message
        }


@dataclass
class LogEntry:
    """Represents a log entry for database operations."""
    timestamp: datetime
    level: str  # INFO, WARNING, ERROR
    message: str
    details: str = ""
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.strftime("%H:%M:%S"),
            "level": self.level,
            "message": self.message,
            "details": self.details
        }


class LogManager:
    """Manages log entries for database operations."""
    
    def __init__(self, logger=None, max_logs: int = 100):
        self._logs: List[LogEntry] = []
        self._max_logs = max_logs
        self._logger = logger
    
    def log(self, message: str, level: str = "INFO", details: str = ""):
        """Add a log entry."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            details=details
        )
        self._logs.append(entry)
        
        # Keep only last N logs
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]
        
        if self._logger:
            self._logger.log(message, tag="multi_db", level=level)
    
    def get_logs(self, limit: int = 50) -> List[dict]:
        """Get recent log entries."""
        return [log.to_dict() for log in self._logs[-limit:]]
    
    def clear(self):
        """Clear all logs."""
        self._logs = []
        self.log("Logs cleared", "INFO")