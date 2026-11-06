from typing import Any, Callable, Optional


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

    def find(
        self,
        prefix: Optional[str] = None,
        predicate: Optional[Callable[[str, Any], bool]] = None,
        type_filter: Optional[type] = None,
    ) -> dict[str, Any]:
        """
        Find services matching all provided filters.

        All provided filters are combined with logical AND. Omitted
        filters impose no constraint. The returned dict preserves the
        insertion order of the underlying registry (Python 3.7+ dict
        semantics), so callers can rely on registration order.

        Args:
            prefix:
                If provided, only keys that start with this string
                match. Useful for discovering families of services
                registered under a shared namespace
                (e.g. "crypto_provider_").

            predicate:
                If provided, must be a callable of the form
                ``predicate(key: str, instance: Any) -> bool``.
                Only entries for which it returns a truthy value match.
                Exceptions raised by the predicate propagate to the
                caller — predicates should not hide bugs.

            type_filter:
                If provided, only instances that are ``isinstance`` of
                this type match. Useful for gathering all providers
                of a given interface, for example.

        Returns:
            A dict mapping each matching service key to its instance.
            Empty dict when nothing matches. The returned dict is a
            fresh object; callers may mutate it without affecting the
            registry.

        Examples:
            >>> registry.find()  # all services
            {'core_logger': <...>, 'core_config': <...>, ...}

            >>> registry.find(prefix="crypto_provider_")
            {'crypto_provider_nobitex': <...>}

            >>> registry.find(type_filter=BaseCryptoProvider)
            {'crypto_provider_nobitex': <...>, 'crypto_provider_coingecko': <...>}

            >>> registry.find(
            ...     prefix="crypto_provider_",
            ...     predicate=lambda k, v: "klines" in v.capabilities,
            ... )
            {'crypto_provider_nobitex': <...>}
        """
        results: dict[str, Any] = {}
        for key, instance in self._services.items():
            if prefix is not None and not key.startswith(prefix):
                continue
            if type_filter is not None and not isinstance(instance, type_filter):
                continue
            if predicate is not None and not predicate(key, instance):
                continue
            results[key] = instance
        return results