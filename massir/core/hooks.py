"""
Hooks manager and Hook class for the Massir framework.

This module provides:
1. Hook class - For creating module-defined custom hook types
2. is_coroutine_function() - Compatibility helper for coroutine detection
3. HooksManager - Manages registration and dispatching of hooks

The HooksManager supports both SystemHook (enum) and Hook (custom) types.
"""

import inspect
from typing import Callable, Dict, List, Optional, Union

from massir.core.hook_types import SystemHook
from massir.core.core_apis import CoreLoggerAPI


class Hook:
    """
    Hook type for module-defined custom events.
    
    This class allows modules to define and trigger their own hooks
    for events that are specific to their domain (e.g., ON_NETWORK_READY,
    ON_DATABASE_READY, ON_CACHE_INVALIDATED).
    
    Usage example:
        # Define a hook in a module
        ON_NETWORK_READY = Hook("on_network_ready")
        
        # Register callback (from any module)
        app.register_hook(ON_NETWORK_READY, callback)
        
        # Trigger (from the module that owns the hook)
        await app.trigger_hook(ON_NETWORK_READY, *args)
    
    Attributes:
        name: Unique identifier for the hook
    """
    
    def __init__(self, name: str):
        """
        Initialize a hook.
        
        Args:
            name: Unique hook identifier (e.g., "on_network_ready")
        """
        self.name = name
    
    def __eq__(self, other):
        if isinstance(other, Hook):
            return self.name == other.name
        return False
    
    def __hash__(self):
        return hash(self.name)
    
    def __repr__(self):
        return f"Hook('{self.name}')"


def is_coroutine_function(func: Callable) -> bool:
    """
    Check if a function is a coroutine function.
    
    This helper uses inspect.iscoroutinefunction which is available in
    all supported Python versions (3.5+) and is the recommended
    replacement for asyncio.iscoroutinefunction (deprecated in 3.14).
    
    Args:
        func: Function to check
        
    Returns:
        True if the function is a coroutine function, False otherwise
    """
    return inspect.iscoroutinefunction(func)


class HooksManager:
    """
    Manager for system and custom hooks.
    
    This class manages:
    1. Registration of callback functions for hook events
    2. Dispatching events to registered callbacks
    3. Support for both SystemHook (enum) and Hook (custom) types
    
    The manager supports both synchronous and asynchronous callback functions.
    """
    
    def __init__(self):
        """Initialize hooks manager with empty registry."""
        self._hooks: Dict[Union[SystemHook, Hook], List[Callable]] = {}
        self._logger_api: Optional[CoreLoggerAPI] = None
    
    def set_logger(self, logger_api: CoreLoggerAPI) -> None:
        """
        Set logger for hook error logging.
        
        Args:
            logger_api: Logger API instance
        """
        self._logger_api = logger_api
    
    def register(
        self,
        hook: Union[SystemHook, Hook],
        callback: Callable,
        logger_api: Optional[CoreLoggerAPI] = None
    ) -> None:
        """
        Register a callback for a specific hook.
        
        This method accepts both SystemHook enum values and Hook
        instances created by modules.
        
        Args:
            hook: The hook type (SystemHook or Hook)
            callback: The callback function to execute
            logger_api: Optional logger for error reporting
        """
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
        
        logger = logger_api or self._logger_api
        if logger:
            hook_name = self._get_hook_name(hook)
            logger.log(
                f"Registered hook: {hook_name}",
                level="CORE", tag="core_hooks"
            )
    
    async def dispatch(
        self,
        hook: Union[SystemHook, Hook],
        *args,
        **kwargs
    ) -> None:
        """
        Dispatch a hook to all registered callbacks.
        
        This method supports both SystemHook and Hook types.
        Callbacks can be either synchronous or asynchronous.
        
        Args:
            hook: The hook type to dispatch
            *args: Positional arguments to pass to callbacks
            **kwargs: Keyword arguments to pass to callbacks
        """
        if hook not in self._hooks:
            return
        
        for callback in self._hooks[hook]:
            try:
                if is_coroutine_function(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                hook_name = self._get_hook_name(hook)
                if self._logger_api:
                    self._logger_api.log(
                        f"Hook error in '{hook_name}': {e}",
                        level="ERROR"
                    )
    
    def get_registered_hooks(self) -> List[str]:
        """
        Get list of all registered hook names.
        
        Returns:
            List of hook name strings
        """
        result = []
        for hook in self._hooks.keys():
            result.append(self._get_hook_name(hook))
        return result
    
    def _get_hook_name(self, hook: Union[SystemHook, Hook]) -> str:
        """
        Get the string name of a hook.
        
        Args:
            hook: SystemHook or Hook instance
            
        Returns:
            Hook name string
        """
        if isinstance(hook, SystemHook):
            return hook.value
        return hook.name