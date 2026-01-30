import asyncio
import signal
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable

from core.interfaces import IModule, ModuleContext
from core.registry import ModuleRegistry
from core.exceptions import FrameworkError
from core.apis.system_apis import CoreLoggerAPI, CoreConfigAPI
from core.hooks.definitions import SystemHook
from core.settings_manager import SettingsManager
from core.module_loader import ModuleLoader # ⭐ ایمپورت لودر جدید

# --- پیاده‌سازی‌های پیش‌فرض (Fallback) ---

class DefaultLogger(CoreLoggerAPI):
    """کلاس لاگر پیش‌فرض که تنظیمات را رعایت می‌کند"""
    def __init__(self, config_api: CoreConfigAPI):
        self.config = config_api

    def log(self, message: str, level: str = "INFO"):
        if not self.config.is_debug():
            return

        if os.name == 'nt':
            os.system('')

        template = self.config.get_system_log_template()
        color_code = self.config.get_system_log_color_code()
        
        formatted_msg = template.format(
            project_name=self.config.get_project_name(),
            level=level,
            message=message
        )

        color_code_start = f'\033[{color_code}m'
        reset_code = '\033[0m'
        
        print(f"{color_code_start}{formatted_msg}{reset_code}")

class DefaultConfig(CoreConfigAPI):
    def get(self, key: str):
        return None

# --- هسته اصلی ---

class Kernel:
    def __init__(self):
        self._modules: Dict[str, IModule] = {}
        self.context = ModuleContext()
        self._loader = ModuleLoader() # ⭐ استفاده از لودر جدید
        
        # لود تنظیمات و ساخت لاگر پیش‌فرض
        self.config_api: CoreConfigAPI = SettingsManager()
        self.logger_api: CoreLoggerAPI = DefaultLogger(self.config_api)
        
        self._hooks: Dict[SystemHook, List[Callable]] = {}
        self._background_tasks: List[asyncio.Task] = []
        
        self.context.set_kernel(self)
        self._register_default_services()

    def _register_default_services(self):
        """ثبت سرویس‌های پیش‌فرض هسته"""
        self.context.services.set("core_logger", self.logger_api)
        self.context.services.set("core_config", self.config_api)

    # --- مدیریت قلاب‌ها (Hooks) ---
    # --- مدیریت قلاب‌ها (Hooks) ---
    def register_hook(self, hook: SystemHook, callback: Callable):
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
        # این خط ممکن است باعث خطا شود اگر logger هنوز آماده نیست، پس بی‌خطر می‌کنیم
        if hasattr(self, 'logger_api'):
            self.logger_api.log(f"🪝 Registered hook: {hook.value}", level="DEBUG")

    async def _dispatch_hook(self, hook: SystemHook, *args, **kwargs):
        """اجرای همگام یا ناهمگام کال‌بک‌ها"""
        if hook in self._hooks:
            for callback in self._hooks[hook]:
                try:
                    # بررسی اینکه کال‌بک async است یا sync
                    if asyncio.iscoroutinefunction(callback):
                        # ⭐ await کردن کال‌بک‌های async (مشکل قبلی اینجا بود)
                        await callback(*args, **kwargs)
                    else:
                        # اجرای sync
                        callback(*args, **kwargs)
                except Exception as e:
                    # اگر logger آماده بود لاگ بزن، وگرنه پرینت ساده
                    if hasattr(self, 'logger_api'):
                        self.logger_api.log(f"Hook Error in {hook.value}: {e}", level="ERROR")
                    else:
                        print(f"Hook Error in {hook.value}: {e}")

    # --- مدیریت تسک‌ها ---
    def register_background_task(self, coroutine):
        if asyncio.iscoroutinefunction(coroutine):
            task = asyncio.create_task(coroutine())
            self._background_tasks.append(task)
        else:
            task = asyncio.create_task(asyncio.to_thread(coroutine))
            self._background_tasks.append(task)

    # --- چرخه حیات (Lifecycle) ---
    async def bootstrap(self, modules_dir: str = "modules"):
        # دریافت تنظیمات از گروه general
        # ⭐ توجه: await اضافه شد
        await self._dispatch_hook(SystemHook.ON_SETTINGS_LOADED)
        self._print_banner()

        # ⭐ توجه: await اضافه شد
        await self._dispatch_hook(SystemHook.ON_KERNEL_BOOTSTRAP_START)
        self._log_internal("🚀 Starting Framework Kernel...")

        # استفاده از لودر برای پیدا کردن ماژول‌ها
        modules_data = self._loader.discover(modules_dir)
        
        system_data = [m for m in modules_data if m["manifest"].get("type") == "system"]
        app_data = [m for m in modules_data if m["manifest"].get("type") != "system"]

        # --- لود سیستم ---
        self._log_internal("🔩 Loading System Modules...")
        for mod_info in system_data:
            instance = self._loader.instantiate(mod_info)
            await instance.load(self.context)
            await self._inject_system_apis(instance)
            await instance.start(self.context)
            self._modules[instance.name] = instance
            
            # ⭐ توجه: await اضافه شد
            await self._dispatch_hook(SystemHook.ON_MODULE_LOADED, instance)

        # --- لود اپلیکیشن ---
        self._log_internal("🔍 Resolving Application Modules...")
        system_provides = {}
        for m in system_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                system_provides[cap] = name
        
        # اضافه کردن قابلیت‌های پیش‌فرض هسته
        system_provides["core_logger"] = "Kernel_Default"
        system_provides["core_config"] = "Kernel_Default"

        sorted_app = self._loader.resolve_order(app_data, existing_provides=system_provides)

        self._log_internal("📦 Loading Application Modules...")
        for mod_info in sorted_app:
            instance = self._loader.instantiate(mod_info)
            await instance.load(self.context)
            self._modules[instance.name] = instance
            
            # ⭐ توجه: await اضافه شد
            await self._dispatch_hook(SystemHook.ON_MODULE_LOADED, instance)

        self._log_internal("▶️ Starting Application Modules...")
        for instance in self._modules.values():
             if instance not in [m['manifest']['name'] for m in system_data]:
                await instance.start(self.context)

        # ⭐ توجه: await اضافه شد
        await self._dispatch_hook(SystemHook.ON_KERNEL_BOOTSTRAP_END)
        self._log_internal("✅ Framework initialization complete.\n")

    async def run(self):
        """مدیریت اجرای برنامه، سیگنال‌ها و حلقه اصلی"""
        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        
        # دریافت پوشه ماژول‌ها از تنظیمات (گروه general)
        modules_dir = self.config_api.get("general.modules_dir", "modules")

        def _shutdown_handler():
            print("\n\n⚠️ Shutdown signal received. Initiating graceful shutdown...")
            stop_event.set()

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _shutdown_handler)
        except NotImplementedError:
            pass

        try:
            await self.bootstrap(modules_dir)
            print("✨ Application is running. Press Ctrl+C to stop.")
            await stop_event.wait()
            
        except asyncio.CancelledError:
            self._log_internal("Core run loop cancelled.")
        except Exception as e:
            self.logger_api.log(f"Fatal Error in core execution: {e}", level="ERROR")
        finally:
            await self.shutdown()

    async def shutdown(self):
        self._log_internal("🛑 Shutting down framework...")
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                
        for instance in reversed(list(self._modules.values())):
            try:
                await instance.stop(self.context)
            except Exception as e:
                self.logger_api.log(f"Error stopping module {instance.name}: {e}", level="ERROR")

    # --- متدهای کمکی ---
    def _log_internal(self, message: str):
        if not self.config_api.is_debug():
            return
        self.logger_api.log(message, level="INFO") 

    def _print_banner(self):
        template = self.config_api.get_banner_template()
        project_name = self.config_api.get_project_name()
        banner_content = template.format(project_name=project_name)
        color_code = self.config_api.get_banner_color_code()
        if os.name == 'nt':
            os.system('')
        color_start = f'\033[{color_code}m'
        reset_code = '\033[0m'
        print(f"{color_start}{banner_content}{reset_code}")

    async def _inject_system_apis(self, system_module: IModule):
        logger_service = self.context.services.get("core_logger")
        if logger_service and isinstance(logger_service, CoreLoggerAPI):
            self.logger_api.log(f"🔄 Overriding Core Logger with module: {system_module.name}")
            self.logger_api = logger_service 
            self.context.services.set("core_logger", self.logger_api)

        config_service = self.context.services.get("core_config")
        if config_service and isinstance(config_service, CoreConfigAPI):
            self.logger_api.log(f"🔄 Overriding Core Config with module: {system_module.name}")
            self.config_api = config_service
            self.context.services.set("core_config", self.config_api)
            
            if isinstance(self.logger_api, DefaultLogger):
                self.logger_api.config = self.config_api