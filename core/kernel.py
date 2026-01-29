import json
import importlib
import asyncio
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable

from core.interfaces import IModule, ModuleContext
from core.registry import ModuleRegistry
from core.exceptions import DependencyResolutionError
from core.apis.system_apis import CoreLoggerAPI, CoreConfigAPI
from core.hooks.definitions import SystemHook
from core.settings_manager import SettingsManager

# --- پیاده‌سازی‌های پیش‌فرض (Fallback) ---

class DefaultLogger(CoreLoggerAPI):
    """کلاس لاگر پیش‌فرض که تنظیمات را رعایت می‌کند"""
    def __init__(self, config_api: CoreConfigAPI):
        self.config = config_api

    def log(self, message: str, level: str = "INFO"):
        # اگر دیباگ خاموش است، چاپ نکن
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
        
        # لود تنظیمات و ساخت لاگر پیش‌فرض
        self.config_api: CoreConfigAPI = SettingsManager()
        self.logger_api: CoreLoggerAPI = DefaultLogger(self.config_api)
        
        self._hooks: Dict[SystemHook, List[Callable]] = {}
        self.context.set_kernel(self)

        # ⭐ ثبت سرویس‌های پیش‌فرض هسته در رجیستری
        # این باعث می‌شود حتی اگر ماژول سیستمی لود نشود، ماژول‌ها این سرویس‌ها را پیدا کنند
        self.context.services.set("core_logger", self.logger_api)
        self.context.services.set("core_config", self.config_api)

    # ... متدهای register_hook و _dispatch_hook بدون تغییر ...
    def register_hook(self, hook: SystemHook, callback: Callable):
        if hook not in self._hooks:
            self._hooks[hook] = []
        self._hooks[hook].append(callback)
        self.logger_api.log(f"🪝 Registered hook: {hook.value}", level="DEBUG")

    async def _dispatch_hook(self, hook: SystemHook, *args, **kwargs):
        if hook in self._hooks:
            for callback in self._hooks[hook]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    print(f"Hook Error in {hook.value}: {e}")

    async def bootstrap(self, modules_dir: str = "modules"):
        
        # --- فاز ۰: لود و اعمال تنظیمات ---
        self.logger_api.log("🔧 Loading Project Settings...")
        await self._dispatch_hook(SystemHook.ON_SETTINGS_LOADED)
        self._print_banner()

        await self._dispatch_hook(SystemHook.ON_KERNEL_BOOTSTRAP_START)
        self._log_internal("🚀 Starting Framework Kernel...")

        modules_data = self._discover_modules(modules_dir)
        
        system_data = [m for m in modules_data if m["manifest"].get("type") == "system"]
        app_data = [m for m in modules_data if m["manifest"].get("type") != "system"]

        # --- فاز ۲: لود سیستم ---
        self._log_internal("🔩 Loading System Modules...")
        for mod_info in system_data:
            instance = self._instantiate_module(mod_info)
            await instance.load(self.context)
            await self._inject_system_apis(instance)
            await instance.start(self.context)
            self._modules[instance.name] = instance
            await self._dispatch_hook(SystemHook.ON_MODULE_LOADED, instance)

        # --- فاز ۳: لود اپلیکیشن ---
        self._log_internal("🔍 Resolving Application Modules...")
        
        system_provides = {}
        for m in system_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                system_provides[cap] = name

        # ⭐ اضافه کردن قابلیت‌های پیش‌فرض هسته به لیست تامین‌کنندگان
        # این کار باعث می‌شود حل‌کننده وابستگی بداند که هسته هم می‌تواند Logger و Config را فراهم کند
        system_provides["core_logger"] = "Kernel_Default"
        system_provides["core_config"] = "Kernel_Default"

        sorted_app = self._resolve_load_order(app_data, existing_provides=system_provides)

        self._log_internal("📦 Loading Application Modules...")
        for mod_info in sorted_app:
            instance = self._instantiate_module(mod_info)
            await instance.load(self.context)
            self._modules[instance.name] = instance
            await self._dispatch_hook(SystemHook.ON_MODULE_LOADED, instance)

        self._log_internal("▶️ Starting Application Modules...")
        for instance in self._modules.values():
             if instance not in [m['manifest']['name'] for m in system_data]:
                await instance.start(self.context)

        await self._dispatch_hook(SystemHook.ON_KERNEL_BOOTSTRAP_END)
        self._log_internal("✅ Framework initialization complete.\n")

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

    # ... متدهای inject_system_apis و discover و resolve و instantiate مانند قبل هستند ...
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

    def _discover_modules(self, directory: str) -> List[Dict]:
        found = []
        base_path = Path(directory)
        if not base_path.exists():
            raise FileNotFoundError(f"Modules directory not found: {directory}")
        for manifest_path in base_path.rglob("manifest.json"):
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                module_folder = manifest_path.parent
                found.append({"path": module_folder, "manifest": data})
        return found

    def _resolve_load_order(self, modules_data: List[Dict], existing_provides: Dict[str, str] = None) -> List[Dict]:
        sorted_list = []
        visited = set()
        visiting = set()
        provides_map = existing_provides.copy() if existing_provides else {}

        for m in modules_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                provides_map[cap] = name

        def visit(mod_info):
            name = mod_info["manifest"]["name"]
            if name in visiting: raise DependencyResolutionError(f"Circular dependency in '{name}'")
            if name in visited: return
            visiting.add(name)
            requires = mod_info["manifest"].get("requires", [])
            for req_cap in requires:
                if req_cap not in provides_map:
                    raise DependencyResolutionError(f"'{name}' requires '{req_cap}' but none provides it.")
                provider_name = provides_map[req_cap]
                provider_info = next((m for m in modules_data if m["manifest"]["name"] == provider_name), None)
                if provider_info: visit(provider_info)
            visiting.remove(name)
            visited.add(name)
            sorted_list.append(mod_info)

        for mod_info in modules_data: visit(mod_info)
        return sorted_list

    def _instantiate_module(self, mod_info: Dict) -> IModule:
        manifest = mod_info["manifest"]
        mod_name = manifest["name"]
        class_name = manifest.get("entrypoint")
        if not class_name:
            raise ModuleLoadError(f"Module '{mod_name}' missing entrypoint.")
        rel_path = mod_info["path"]
        parts = list(rel_path.parts)
        import_path = ".".join(parts)
        try:
            module_lib = importlib.import_module(f"{import_path}.module")
            entry_class = getattr(module_lib, class_name)
            instance: IModule = entry_class()
            instance.name = mod_name
            return instance
        except Exception as e:
            raise ModuleLoadError(f"Failed to load '{mod_name}': {e}")

    async def shutdown(self):
        self._log_internal("🛑 Shutting down framework...")
        for instance in reversed(list(self._modules.values())):
            await instance.stop(self.context)