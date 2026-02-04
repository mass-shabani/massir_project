import asyncio
import signal
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING

# ایمپورت‌ها با ساختار مسطح
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
from massir.core.exceptions import DependencyResolutionError

if TYPE_CHECKING:
    from massir.core.app import App

class App:
    """
    کلاس اصلی برنامه.
    مسئولیت مدیریت چرخه حیات، ماژول‌ها و تنظیمات را بر عهده دارد.
    """
    def __init__(self, initial_settings: Optional[dict] = None):
        self.modules: Dict[str, IModule] = {}
        self.context = ModuleContext()
        self.loader = ModuleLoader()
        self.hooks = HooksManager()
        
        # رفرنس‌ها برای اجازه تغییر توسط ماژول‌های دیگر
        self._logger_api_ref = [None]
        self._config_api_ref = [None]
        self._background_tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        
        # متغیرهای جدید برای مدیریت نام ماژول‌ها
        self._system_module_names: List[str] = []
        self._app_module_names: List[str] = []
        
        # مقداردهی اولیه سرویس‌ها
        self._bootstrap_system(initial_settings)

    def _bootstrap_system(self, initial_settings: Optional[dict]):
        # ابتدا سرویس‌ها را با تنظیمات کامل رجیستر می‌کنیم
        initialize_core_services(self.context.services, initial_settings)
        
        # گرفتن رفرنس به سرویس‌های ثبت شده
        self._config_api_ref[0] = self.context.services.get("core_config")
        self._logger_api_ref[0] = self.context.services.get("core_logger")
        
        self.context.set_kernel(self)

    # --- هوک‌ها ---
    def register_hook(self, hook: SystemHook, callback):
        self.hooks.register(hook, callback, self._logger_api_ref[0])

    # --- مدیریت تسک‌ها ---
    def register_background_task(self, coroutine):
        """ثبت یک تسک پس‌زمینه (مثل Uvicorn)"""
        if asyncio.iscoroutinefunction(coroutine):
            task = asyncio.create_task(coroutine())
            self._background_tasks.append(task)
        else:
            task = asyncio.create_task(asyncio.to_thread(coroutine))
            self._background_tasks.append(task)

    # --- مدیریت سیگنال‌ها ---
    def _setup_signal_handlers(self, loop: asyncio.AbstractEventLoop):
        def _shutdown_handler():
            print("\n\nShutdown signal received. Initiating graceful shutdown...")
            self._stop_event.set()

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _shutdown_handler)
        except NotImplementedError:
            pass

    # --- چرخه حیات (Lifecycle) ---
    async def run(self):
        """نقطه ورود اصلی برنامه"""
        loop = asyncio.get_running_loop()
        self._setup_signal_handlers(loop)

        try:
            await self._bootstrap_phases()
            print("Application is running. Press Ctrl+C to stop.")
            await self._stop_event.wait()
            
        except asyncio.CancelledError:
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Core run loop cancelled.", tag="core")
        except Exception as e:
            self._logger_api_ref[0].log(f"Fatal Error in core execution: {e}", level="ERROR", tag="core")
        finally:
            await shutdown(self.modules, self._background_tasks, 
                          self._config_api_ref[0], self._logger_api_ref[0])

    async def _bootstrap_phases(self):
        """مدیریت فازهای بوت‌استرپ ماژول‌ها"""
        # فاز ۰
        await self.hooks.dispatch(SystemHook.ON_SETTINGS_LOADED)
        print_banner(self._config_api_ref[0])

        # فاز ۱
        await self.hooks.dispatch(SystemHook.ON_KERNEL_BOOTSTRAP_START)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Starting Massir Framework...", tag="core_init")

        # دریافت لیست مسیرها
        modules_dirs = self._config_api_ref[0].get_modules_dir()
        all_modules_data = []
        
        for directory in modules_dirs:
            try:
                discovered = self.loader.discover(directory)
                all_modules_data.extend(discovered)
            except FileNotFoundError:
                if self._logger_api_ref[0]:
                    self._logger_api_ref[0].log(f"Module directory not found: {directory}", level="WARNING", tag="core")
        
        # تفکیک سیستم و اپلیکیشن
        system_data = [m for m in all_modules_data if m["manifest"].get("type") == "system"]
        app_data = [m for m in all_modules_data if m["manifest"].get("type") != "system"]

        # فاز ۲ - لود ماژول‌ها (فقط instantiate و load، نه start)
        await self._load_system_modules(system_data)
        await self._load_application_modules(app_data, system_data)

        # فاز ۳ - استارت ماژول‌ها به ترتیب (سیستمی اول، سپس کاربردی)
        await self._start_all_modules()

        # فاز نهایی
        await self.hooks.dispatch(SystemHook.ON_KERNEL_BOOTSTRAP_END)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Framework initialization complete.", tag="core")

    async def _check_requirements(self, mod_info: Dict, system_provides: Dict) -> tuple[bool, List[str]]:
        """
        بررسی پیشنیازهای یک ماژول.
        Returns: (all_requirements_met: bool, missing_requirements: List[str])
        """
        requires = mod_info["manifest"].get("requires", [])
        missing = []
        
        for req_cap in requires:
            if req_cap not in system_provides:
                missing.append(req_cap)
        
        return (len(missing) == 0), missing

    async def _load_system_modules(self, system_data: List[Dict]):
        """لود ماژول‌های سیستمی (فقط instantiate و load)"""
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Loading System Modules...", tag="core_init")
        
        # سیستم‌ها به ترتیب ورودی
        for mod_info in system_data:
            mod_name = mod_info["manifest"]["name"]
            is_forced = mod_info["manifest"].get("forced_execute", False)
            
            # استخراج قابلیت‌های سیستم‌های قبلی (برای بررسی وابستگی)
            system_provides = {}
            for m in self.modules.values():
                if hasattr(m, '_is_system') and m._is_system:
                    provides = getattr(m, 'provides', [])
                    if isinstance(provides, list):
                        for cap in provides:
                            system_provides[cap] = m.name
            
            # اضافه کردن قابلیت‌های پیش‌فرض
            system_provides["core_logger"] = "App_Default"
            system_provides["core_config"] = "App_Default"
            
            try:
                # بررسی پیشنیازها
                requirements_met, missing = await self._check_requirements(mod_info, system_provides)
                
                if not requirements_met:
                    # پیشنیازها وجود ندارند
                    self._logger_api_ref[0].log(
                        f"System module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    
                    if not is_forced:
                        self._logger_api_ref[0].log(f"Skipping module '{mod_name}' (not forced)", level="INFO", tag="core")
                        continue
                    else:
                        self._logger_api_ref[0].log(f"Forced execution of '{mod_name}' despite missing requirements", level="WARNING", tag="core")
                
                # لود ماژول (instantiate + load)
                mod_instance = await self._instantiate_and_load(mod_info, is_system=True)
                self.modules[mod_name] = mod_instance
                self._system_module_names.append(mod_name)
                self._logger_api_ref[0].log(f"System module '{mod_name}' loaded", level="INFO", tag="core")
                
            except Exception as e:
                self._logger_api_ref[0].log(f"System module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")

    async def _load_application_modules(self, app_data: List[Dict], system_data: List[Dict]):
        """لود ماژول‌های کاربردی (فقط instantiate و load)"""
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Loading Application Modules...", tag="core")
        
        # استخراج قابلیت‌های سیستم‌های لود شده
        system_provides = {}
        for m in system_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                system_provides[cap] = name
        
        # اضافه کردن قابلیت‌های پیش‌فرض
        system_provides["core_logger"] = "App_Default"
        system_provides["core_config"] = "App_Default"
        
        # تفکیک اجباری و معمولی
        forced_app_data = [m for m in app_data if m["manifest"].get("forced_execute", False)]
        regular_app_data = [m for m in app_data if not m["manifest"].get("forced_execute", False)]
        
        # --- ۱. پردازش اجباری ---
        for mod_info in forced_app_data:
            mod_name = mod_info["manifest"]["name"]
            
            try:
                # بررسی پیشنیازها
                requirements_met, missing = await self._check_requirements(mod_info, system_provides)
                
                if not requirements_met:
                    self._logger_api_ref[0].log(
                        f"Application module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    self._logger_api_ref[0].log(f"Forced execution of '{mod_name}'", level="WARNING", tag="core")
                
                # لود ماژول
                mod_instance = await self._instantiate_and_load(mod_info, is_system=False)
                self.modules[mod_name] = mod_instance
                self._app_module_names.append(mod_name)
                self._logger_api_ref[0].log(f"Application module '{mod_name}' loaded", level="INFO", tag="core")
                
            except Exception as e:
                self._logger_api_ref[0].log(f"Application module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")
        
        # --- ۲. پردازش معمولی (با بررسی وابستگی) ---
        for mod_info in regular_app_data:
            mod_name = mod_info["manifest"]["name"]
            
            try:
                # بررسی پیشنیازها
                requirements_met, missing = await self._check_requirements(mod_info, system_provides)
                
                if not requirements_met:
                    self._logger_api_ref[0].log(
                        f"Application module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    self._logger_api_ref[0].log(f"Skipping module '{mod_name}' (not forced)", level="INFO", tag="core")
                    continue
                
                # لود ماژول
                mod_instance = await self._instantiate_and_load(mod_info, is_system=False)
                self.modules[mod_name] = mod_instance
                self._app_module_names.append(mod_name)
                self._logger_api_ref[0].log(f"Application module '{mod_name}' loaded", level="INFO", tag="core")
                
            except Exception as e:
                self._logger_api_ref[0].log(f"Application module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")

    async def _start_all_modules(self):
        """استارت تمام ماژول‌های لود شده به ترتیب (سیستمی اول، سپس کاربردی)"""
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Starting Modules...", tag="core")
        
        # استارت ماژول‌های سیستمی
        for mod_name in self._system_module_names:
            if mod_name in self.modules:
                try:
                    await self.modules[mod_name].start(self.context)
                    await self.hooks.dispatch(SystemHook.ON_MODULE_LOADED, self.modules[mod_name])
                except Exception as e:
                    self._logger_api_ref[0].log(f"Error starting system module '{mod_name}': {e}", level="ERROR", tag="core")
        
        # استارت ماژول‌های کاربردی
        for mod_name in self._app_module_names:
            if mod_name in self.modules:
                try:
                    await self.modules[mod_name].start(self.context)
                    await self.hooks.dispatch(SystemHook.ON_MODULE_LOADED, self.modules[mod_name])
                except Exception as e:
                    self._logger_api_ref[0].log(f"Error starting application module '{mod_name}': {e}", level="ERROR", tag="core")

    async def _instantiate_and_load(self, mod_info: Dict, is_system: bool) -> IModule:
        """
        متد کمکی برای نمونه‌سازی و load (بدون start).
        """
        instance = self.loader.instantiate(mod_info)
        instance._context = self.context
        
        await instance.load(self.context)
        await inject_system_apis(instance, self.context.services, 
                                 self._logger_api_ref, self._config_api_ref)
        
        if is_system:
            setattr(instance, '_is_system', True)
        
        return instance

# --- رفرنس کلاس اصلی برای استفاده خارجی ---
Kernel = App
ModuleContext = ModuleContext
IModule = IModule
