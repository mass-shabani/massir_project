import asyncio
from typing import List, Callable, Dict, Optional
from massir.core.hook_types import SystemHook
from massir.core.log import log_internal
from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI


class HooksManager:
    """
    Manager for system hooks.

    This class manages registration and dispatching of system hooks
    that allow modules to react to specific events in the application lifecycle.
    """

    def __init__(self):
        """Initialize hooks manager."""
        self._hooks: Dict[SystemHook, List[Callable]] = {}

    def register(self, hook: SystemHook, callback: Callable, logger_api: Optional[CoreLoggerAPI] = None):
        """
        Register a callback for a specific hook.

        Args:
            hook: The hook type to register for
            callback: The callback function to execute
            logger_api: Optional logger API for logging
        """
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
        # Use fallback config and logger for log_internal
        config_api = None  # config_api is not available here
        log_internal(config_api, logger_api, f"🪝 Registered hook: {hook.value}", level="CORE", tag="core_hooks")

    async def dispatch(self, hook: SystemHook, *args, **kwargs):
        """
        Dispatch a hook to all registered callbacks.

        Args:
            hook: The hook type to dispatch
            *args: Positional arguments to pass to callbacks
            **kwargs: Keyword arguments to pass to callbacks
        """
        if hook in self._hooks:
            for callback in self._hooks[hook]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    # Use fallback for log_internal
                    log_internal(None, None, f"Hook Error in {hook.value}: {e}", level="ERROR")