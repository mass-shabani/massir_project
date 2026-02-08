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
from massir.core.path import Path as PathManager

if TYPE_CHECKING:
    from massir.core.app import App

class App:
    """
    کلاس اصلی برنامه.
    مسئولیت مدیریت چرخه حیات، ماژول‌ها و تنظیمات را بر عهده دارد.
    """
    def __init__(
        self,
        initial_settings: Optional[dict] = None,
        settings_path: Optional[str] = None,
        app_dir: Optional[str] = None
    ):
        """
        Args:
            initial_settings: تنظیمات کد (بالاترین اولویت)
            settings_path: مسیر فایل تنظیمات JSON
                - "./config/settings.json" : مسیر نسبی
                - "/absolute/path.json" : مسیر مطلق
                - "__cwd__" : پوشه جاری
            app_dir: مسیر پوشه برنامه کاربر (جایی که main.py قرار دارد)
        """
        # مدیریت مسیرها
        self.path = PathManager(app_dir)
        
        # ماژول‌لودر با دسترسی به path
        self.loader = ModuleLoader(path=self.path)
        
        self.modules: Dict[str, IModule] = {}
        self.context = ModuleContext()
        self.hooks = HooksManager()
        
        # رفرنس‌ها برای اجازه تغییر توسط ماژول‌های دیگر
        self._logger_api_ref = [None]
        self._config_api_ref = [None]
        self._background_tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        
        # متغیرهای مدیریت نام ماژول‌ها
        self._system_module_names: List[str] = []
        self._app_module_names: List[str] = []
        
        # مقداردهی اولیه سرویس‌ها
        self._bootstrap_system(initial_settings, settings_path)

    def _bootstrap_system(self, initial_settings: Optional[dict], settings_path: str):
        # ابتدا سرویس‌ها را با تنظیمات کامل رجیستر می‌کنیم
        _, _, self.path = initialize_core_services(
            self.context.services,
            initial_settings,
            settings_path,
            str(self.path.app)
        )
        
        # گرفتن رفرنس به سرویس‌های ثبت شده
        self._config_api_ref[0] = self.context.services.get("core_config")
        self._logger_api_ref[0] = self.context.services.get("core_logger")
        
        self.context.set_app(self)

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
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "\n\nShutdown signal received. Initiating graceful shutdown...", level="INFO")
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
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Application is running. Press Ctrl+C to stop.", level="INFO")
            await self._stop_event.wait()
            
        except asyncio.CancelledError:
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Core run loop cancelled.", tag="core")
        except Exception as e:
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], f"Fatal Error in core execution: {e}", level="ERROR", tag="core")
        finally:
            await shutdown(self.modules, self._background_tasks, 
                          self._config_api_ref[0], self._logger_api_ref[0],
                          self._system_module_names, self._app_module_names)

    async def _bootstrap_phases(self):
        """مدیریت فازهای بوت‌استرپ ماژول‌ها"""
        # فاز ۰
        await self.hooks.dispatch(SystemHook.ON_SETTINGS_LOADED)
        print_banner(self._config_api_ref[0])

        # فاز ۱
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_START)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Starting Massir Framework...", tag="core_init")

        # دریافت تنظیمات ماژول‌ها بر اساس type پوشه
        # فاز سیستمی: پوشه‌های با type='systems' یا type='all'
        system_modules_config = self._config_api_ref[0].get_modules_config_for_type("systems")
        system_data = await self._discover_modules(system_modules_config, is_system=True)
        await self._load_system_modules(system_data)

        # فاز کاربردی: پوشه‌های با type='applications' یا type='all'
        app_modules_config = self._config_api_ref[0].get_modules_config_for_type("applications")
        app_data = await self._discover_modules(app_modules_config, is_system=False)
        await self._load_application_modules(app_data)

        # فاز ۳ - استارت ماژول‌ها به ترتیب
        await self._start_all_modules()

        # فاز نهایی
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_END)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Framework initialization complete.", tag="core")

    async def _discover_modules(self, modules_config: List[Dict], is_system: bool) -> List[Dict]:
        """
        کشف ماژول‌ها از تنظیمات
        
        Args:
            modules_config: لیست تنظیمات ماژول‌ها
            is_system: آیا ماژول‌های سیستمی هستند؟
            
        Returns:
            لیست ماژول‌های کشف شده
        """
        return await self.loader.discover_modules(
            modules_config, 
            is_system, 
            self._config_api_ref[0], 
            self._logger_api_ref[0]
        )

    async def _load_system_modules(self, system_data: List[Dict]):
        """لود ماژول‌های سیستمی"""
        await self.loader.load_system_modules(
            system_data, 
            self.modules, 
            self._config_api_ref[0], 
            self._logger_api_ref[0]
        )
        
        # جمع‌آوری نام ماژول‌های سیستمی
        for mod_info in system_data:
            mod_name = mod_info["manifest"]["name"]
            if mod_name in self.modules:
                self._system_module_names.append(mod_name)

    async def _load_application_modules(self, app_data: List[Dict]):
        """لود ماژول‌های کاربردی"""
        await self.loader.load_application_modules(
            app_data, 
            self.modules, 
            self._config_api_ref[0], 
            self._logger_api_ref[0]
        )
        
        # جمع‌آوری نام ماژول‌های کاربردی
        for mod_info in app_data:
            mod_name = mod_info["manifest"]["name"]
            if mod_name in self.modules:
                self._app_module_names.append(mod_name)

    async def _start_all_modules(self):
        """استارت تمام ماژول‌ها"""
        await self.loader.start_all_modules(
            self.modules, 
            self._system_module_names, 
            self._app_module_names, 
            self._config_api_ref[0], 
            self._logger_api_ref[0], 
            self.hooks
        )


