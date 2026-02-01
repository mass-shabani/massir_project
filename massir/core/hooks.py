import asyncio
from typing import List, Callable, Dict
from massir.core.hook_types import SystemHook

class HooksManager:
    def __init__(self):
        self._hooks: Dict[SystemHook, List[Callable]] = {}

    def register(self, hook: SystemHook, callback: Callable, logger_api):
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
        logger_api.log(f"🪝 Registered hook: {hook.value}", level="DEBUG", tag="core_pre")

    async def dispatch(self, hook: SystemHook, *args, **kwargs):
        if hook in self._hooks:
            for callback in self._hooks[hook]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    print(f"Hook Error in {hook.value}: {e}")