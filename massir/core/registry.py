from typing import Any, Optional


class ModuleRegistry:
    """
    Registry for managing module services.

    This class provides a simple key-value store for registering and
    retrieving services that can be shared across modules.
    """

    def __init__(self):
        """Initialize the registry with an empty services dictionary."""
        self._services = {}

    def set(self, key: str, instance: Any):
        """
        Register a service with a string key.

        Args:
            key: The service identifier
            instance: The service instance to register
        """
        # if key in self._services:
        #     # Warn that we are overwriting a service
        #     print(f"⚠️ Warning: Overwriting service '{key}'")
        self._services[key] = instance

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a service by string key.

        Args:
            key: The service identifier

        Returns:
            The service instance if found, None otherwise
        """
        return self._services.get(key)

    def has(self, key: str) -> bool:
        """
        Check if a service is registered.

        Args:
            key: The service identifier

        Returns:
            True if the service exists, False otherwise
        """
        return key in self._services

    def remove(self, key: str):
        """
        Remove a service from the registry.

        Args:
            key: The service identifier
        """
        if key in self._services:
            del self._services[key]