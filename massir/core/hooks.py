import asyncio
from typing import List, Callable, Dict, Optional
from massir.core.hook_types import SystemHook
from massir.core.log import log_internal
from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI

class HooksManager:
    def __init__(self):
        self._hooks: Dict[SystemHook, List[Callable]] = {}

    def register(self, hook: SystemHook, callback: Callable, logger_api: Optional[CoreLoggerAPI] = None):
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
        # استفاده از fallback config و logger برای log_internal
        config_api = None  # در اینجا config_api در دسترس نیست
        log_internal(config_api, logger_api, f"🪝 Registered hook: {hook.value}", level="DEBUG", tag="core_hooks")

    async def dispatch(self, hook: SystemHook, *args, **kwargs):
        if hook in self._hooks:
            for callback in self._hooks[hook]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    # استفاده از fallback برای log_internal
                    log_internal(None, None, f"Hook Error in {hook.value}: {e}", level="ERROR")