import asyncio
import signal
from pathlib import Path
from typing import List, Dict

from massir.core.interfaces import IModule, ModuleContext
from massir.core.registry import ModuleRegistry
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.hook_types import SystemHook
from massir.core.config import SettingsManager
from massir.core.module_loader import ModuleLoader
from massir.core.api import initialize_core_services
from massir.core.log import print_banner, log_internal
from massir.core.inject import inject_system_apis
from massir.core.hooks import HooksManager
from massir.core.stop import shutdown

class Kernel:
    def __init__(self):
        self.modules: Dict[str, IModule] = {}
        self.context = ModuleContext()
        self.loader = ModuleLoader()
        self.hooks = HooksManager()
        
        self._logger_api_ref = [None]
        self._config_api_ref = [None]
        self._background_tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        
        self._bootstrap_system()

    def _bootstrap_system(self):
        initialize_core_services(self.context.services)
        self._logger_api_ref[0] = self.context.services.get("core_logger")
        self._config_api_ref[0] = self.context.services.get("core_config")
        
        self.context.set_kernel(self)

    def register_hook(self, hook: SystemHook, callback):
        self.hooks.register(hook, callback, self._logger_api_ref[0])

    def register_background_task(self, coroutine):
        if asyncio.iscoroutinefunction(coroutine):
            task = asyncio.create_task(coroutine())
            self._background_tasks.append(task)
        else:
            task = asyncio.create_task(asyncio.to_thread(coroutine))
            self._background_tasks.append(task)

    def _setup_signal_handlers(self, loop: asyncio.AbstractEventLoop):
        def _shutdown_handler():
            print("\n\n⚠️ Shutdown signal received. Initiating graceful shutdown...")
            self._stop_event.set()
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _shutdown_handler)
        except NotImplementedError:
            pass

    async def run(self):
        loop = asyncio.get_running_loop()
        self._setup_signal_handlers(loop)

        try:
            await self._bootstrap_phases()
            print("✨ Application is running. Press Ctrl+C to stop.")
            await self._stop_event.wait()
            
        except asyncio.CancelledError:
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Core run loop cancelled.", tag="core")
        except Exception as e:
            # اینجا هم تگ core را ارسال می‌کنیم
            self._logger_api_ref[0].log(f"Fatal Error in core execution: {e}", level="ERROR", tag="core")
        finally:
            await shutdown(self.modules, self._background_tasks, 
                          self._config_api_ref[0], self._logger_api_ref[0])

    async def _bootstrap_phases(self):
        # فاز ۰
        await self.hooks.dispatch(SystemHook.ON_SETTINGS_LOADED)
        print_banner(self._config_api_ref[0])

        # فاز ۱
        await self.hooks.dispatch(SystemHook.ON_KERNEL_BOOTSTRAP_START)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "🚀 Starting Framework Kernel...", tag="core_preloaded")

        # ⭐ منطق جدید: دریافت لیست مسیرها و جمع‌آوری همه ماژول‌ها
        modules_dirs = self._config_api_ref[0].get_modules_dir() # این تابع یک لیست برمی‌گرداند
        all_modules_data = []
        
        for directory in modules_dirs:
            try:
                discovered = self.loader.discover(directory)
                all_modules_data.extend(discovered)
            except FileNotFoundError:
                # اگر یکی از پوشه‌ها وجود نداشت، خطا نده فقط لاگ کن
                if self._logger_api_ref[0]:
                    self._logger_api_ref[0].log(f"Module directory not found: {directory}", level="WARNING", tag="core")

        # تفکیک سیستم و اپ
        system_data = [m for m in all_modules_data if m["manifest"].get("type") == "system"]
        app_data = [m for m in all_modules_data if m["manifest"].get("type") != "system"]

        await self._load_system_modules(system_data)
        await self._load_application_modules(app_data, system_data)

        await self.hooks.dispatch(SystemHook.ON_KERNEL_BOOTSTRAP_END)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "✅ Framework initialization complete.\n", tag="core")

    async def _load_system_modules(self, system_data: List[Dict]):
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "🔩 Loading System Modules...", tag="core_preloaded")
        for mod_info in system_data:
            instance = self.loader.instantiate(mod_info)
            instance._context = self.context 
            
            await instance.load(self.context)
            await inject_system_apis(instance, self.context.services, 
                                     self._logger_api_ref, self._config_api_ref)
            await instance.start(self.context)
            self.modules[instance.name] = instance
            await self.hooks.dispatch(SystemHook.ON_MODULE_LOADED, instance)

    async def _load_application_modules(self, app_data: List[Dict], system_data: List[Dict]):
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "🔍 Resolving Application Modules...", tag="core")
        
        system_provides = {}
        for m in system_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                system_provides[cap] = name
        
        system_provides["core_logger"] = "Kernel_Default"
        system_provides["core_config"] = "Kernel_Default"

        sorted_app = self.loader.resolve_order(app_data, existing_provides=system_provides)

        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "📦 Loading Application Modules...", tag="core")
        for mod_info in sorted_app:
            instance = self.loader.instantiate(mod_info)
            instance._context = self.context
            await instance.load(self.context)
            self.modules[instance.name] = instance
            await self.hooks.dispatch(SystemHook.ON_MODULE_LOADED, instance)

        # ⭐ اصلاح باگ: مقایسه instance.name به جای instance
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "▶️ Starting Application Modules...", tag="core")
        for instance in self.modules.values():
            # اصلاح شد: instance.name را با لیست نام‌ها مقایسه می‌کند
             if instance.name not in [m['manifest']['name'] for m in system_data]:
                await instance.start(self.context)