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
        settings_path: str = "__dir__",
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
        self.modules: Dict[str, IModule] = {}
        self.context = ModuleContext()
        self.loader = ModuleLoader()
        self.hooks = HooksManager()
        
        # رفرنس‌ها برای اجازه تغییر توسط ماژول‌های دیگر
        self._logger_api_ref = [None]
        self._config_api_ref = [None]
        self._background_tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        
        # متغیرهای مدیریت نام ماژول‌ها
        self._system_module_names: List[str] = []
        self._app_module_names: List[str] = []
        
        # مدیریت مسیرها
        self.path = PathManager(app_dir)
        
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

        # دریافت لیست ماژول‌ها از تنظیمات جدید
        modules_config = self._config_api_ref[0].get_modules_config()
        
        # کشف و لود ماژول‌های سیستمی
        system_data = await self._discover_modules(modules_config, is_system=True)
        await self._load_system_modules(system_data)

        # کشف و لود ماژول‌های کاربردی
        app_data = await self._discover_modules(modules_config, is_system=False)
        await self._load_application_modules(app_data, system_data)

        # فاز ۳ - استارت ماژول‌ها به ترتیب
        await self._start_all_modules()

        # فاز نهایی
        await self.hooks.dispatch(SystemHook.ON_KERNEL_BOOTSTRAP_END)
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
        discovered = []
        
        for module_group in modules_config:
            path_template = module_group.get("path", "")
            names = module_group.get("names", [])
            
            # جایگزینی placeholders
            path = self._resolve_path(path_template)
            
            if not path.exists() or not path.is_dir():
                # لاگ مسیرهای یافت نشده (فقط در debug mode)
                if self._config_api_ref[0].is_debug():
                    log_internal(
                        self._config_api_ref[0], 
                        self._logger_api_ref[0], 
                        f"Path not found or not a directory: {path}", 
                        tag="core_init"
                    )
                continue
            
            # اگر names = "{all}"، همه پوشه‌ها را لیست کن
            if names == "{all}":
                # از مسیر حل شده (path) استفاده کن، نه از template
                names = [f.name for f in path.iterdir() if f.is_dir()]
            
            # کشف هر ماژول
            for name in names:
                module_path = path / name
                manifest_path = module_path / "manifest.json"
                
                if manifest_path.exists():
                    import json
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                        
                    # بررسی نوع ماژول
                    manifest_type = manifest.get("type", "application")
                    is_module_system = (manifest_type == "system")
                    
                    # اگر دنبال ماژول سیستمی هستیم، فقط سیستمی‌ها
                    # اگر دنبال ماژول کاربردی هستیم، فقط کاربردی‌ها
                    if is_system and not is_module_system:
                        continue
                    if not is_system and is_module_system:
                        continue
                    
                    # تولید شناسه یکتا اگر وجود ندارد
                    if "id" not in manifest:
                        import uuid
                        manifest["id"] = str(uuid.uuid4())[:8]
                    
                    discovered.append({
                        "path": module_path,
                        "manifest": manifest
                    })
        
        return discovered

    def _resolve_path(self, path_template: str) -> Path:
        """
        جایگزینی placeholders در مسیر
        
        Args:
            path_template: مسیر با placeholders
            
        Returns:
            مسیر حل شده
        """
        path = path_template
        path = path.replace("{massir_dir}", str(self.path.massir))
        path = path.replace("{app_dir}", str(self.path.app))
        return Path(path)

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
        """لود ماژول‌های سیستمی"""
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Loading System Modules...", tag="core_init")
        
        for mod_info in system_data:
            mod_name = mod_info["manifest"]["name"]
            is_forced = mod_info["manifest"].get("forced_execute", False)
            
            # استخراج قابلیت‌های سیستم‌های قبلی
            system_provides = {}
            for m in self.modules.values():
                if hasattr(m, '_is_system') and m._is_system:
                    provides = getattr(m, 'provides', [])
                    if isinstance(provides, list):
                        for cap in provides:
                            system_provides[cap] = m.name
            
            system_provides["core_logger"] = "App_Default"
            system_provides["core_config"] = "App_Default"
            
            try:
                requirements_met, missing = await self._check_requirements(mod_info, system_provides)
                
                if not requirements_met:
                    self._logger_api_ref[0].log(
                        f"System module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    
                    if not is_forced:
                        self._logger_api_ref[0].log(f"Skipping module '{mod_name}' (not forced)", level="INFO", tag="core")
                        continue
                    else:
                        self._logger_api_ref[0].log(f"Forced execution of '{mod_name}'", level="WARNING", tag="core")
                
                mod_instance = await self._instantiate_and_load(mod_info, is_system=True)
                self.modules[mod_name] = mod_instance
                self._system_module_names.append(mod_name)
                self._logger_api_ref[0].log(f"System module '{mod_name}' loaded", level="INFO", tag="core")
                
            except Exception as e:
                self._logger_api_ref[0].log(f"System module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")

    async def _load_application_modules(self, app_data: List[Dict], system_data: List[Dict]):
        """لود ماژول‌های کاربردی"""
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Loading Application Modules...", tag="core")
        
        # استخراج قابلیت‌های سیستم‌های لود شده
        system_provides = {}
        for m in system_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                system_provides[cap] = name
        
        system_provides["core_logger"] = "App_Default"
        system_provides["core_config"] = "App_Default"
        
        # تفکیک اجباری و معمولی
        forced_app_data = [m for m in app_data if m["manifest"].get("forced_execute", False)]
        regular_app_data = [m for m in app_data if not m["manifest"].get("forced_execute", False)]
        
        # --- پردازش اجباری ---
        for mod_info in forced_app_data:
            mod_name = mod_info["manifest"]["name"]
            
            try:
                requirements_met, missing = await self._check_requirements(mod_info, system_provides)
                
                if not requirements_met:
                    self._logger_api_ref[0].log(
                        f"Application module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    self._logger_api_ref[0].log(f"Forced execution of '{mod_name}'", level="WARNING", tag="core")
                
                mod_instance = await self._instantiate_and_load(mod_info, is_system=False)
                self.modules[mod_name] = mod_instance
                self._app_module_names.append(mod_name)
                self._logger_api_ref[0].log(f"Application module '{mod_name}' loaded", level="INFO", tag="core")
                
            except Exception as e:
                self._logger_api_ref[0].log(f"Application module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")
        
        # --- پردازش معمولی ---
        for mod_info in regular_app_data:
            mod_name = mod_info["manifest"]["name"]
            
            try:
                requirements_met, missing = await self._check_requirements(mod_info, system_provides)
                
                if not requirements_met:
                    self._logger_api_ref[0].log(
                        f"Application module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    self._logger_api_ref[0].log(f"Skipping module '{mod_name}' (not forced)", level="INFO", tag="core")
                    continue
                
                mod_instance = await self._instantiate_and_load(mod_info, is_system=False)
                self.modules[mod_name] = mod_instance
                self._app_module_names.append(mod_name)
                self._logger_api_ref[0].log(f"Application module '{mod_name}' loaded", level="INFO", tag="core")
                
            except Exception as e:
                self._logger_api_ref[0].log(f"Application module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")

    async def _start_all_modules(self):
        """استارت تمام ماژول‌ها"""
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
        نمونه‌سازی و load ماژول
        """
        instance = self.loader.instantiate(mod_info)
        instance._context = self.context
        
        await instance.load(self.context)
        await inject_system_apis(instance, self.context.services, 
                                 self._logger_api_ref, self._config_api_ref)
        
        if is_system:
            setattr(instance, '_is_system', True)
        
        return instance

# --- رفرنس کلاس اصلی ---
Kernel = App
ModuleContext = ModuleContext
IModule = IModule
