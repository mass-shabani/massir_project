from abc import ABC, abstractmethod
from typing import Optional


class CoreLoggerAPI(ABC):
    """
    Standard core logging interface.

    This interface defines the contract for logging services
    used throughout the framework.
    """
    @abstractmethod
    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None, **kwargs):
        """
        Log a message.

        Args:
            message: The message to log
            level: Log level (INFO, WARNING, ERROR, etc.)
            tag: Optional tag for filtering
            **kwargs: Additional keyword arguments (e.g., level_color, text_color)
        """
        pass


class CoreConfigAPI(ABC):
    """
    Standard configuration access interface.

    This interface defines the contract for accessing
    configuration settings throughout the framework.
    """
    @abstractmethod
    def get(self, key: str):
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested keys)

        Returns:
            The configuration value or None if not found
        """
        pass