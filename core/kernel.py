import json
import importlib
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Callable

from core.interfaces import IModule, ModuleContext
from core.registry import ModuleRegistry
from core.exceptions import DependencyResolutionError
from core.apis.system_apis import CoreLoggerAPI, CoreConfigAPI
from core.hooks.definitions import SystemHook

# --- پیاده‌سازی‌های پیش‌فرض (Fallback) ---
class DefaultLogger(CoreLoggerAPI):
    def log(self, message: str, level: str = "INFO"):
        print(f"[{level}] {message}")

class DefaultConfig(CoreConfigAPI):
    def get(self, key: str):
        return None

# --- هسته اصلی ---
class Kernel:
    def __init__(self):
        self._modules: Dict[str, IModule] = {}
        self.context = ModuleContext()
        
        # API ها با کلاس‌های پیش‌فرض مقداردهی می‌شوند
        self.logger_api: CoreLoggerAPI = DefaultLogger()
        self.config_api: CoreConfigAPI = DefaultConfig()
        
        # دیکشنری نگهداری کال‌بک‌ها
        self._hooks: Dict[SystemHook, List[Callable]] = {}

        # هسته را در کانتکست ثبت می‌کند تا ماژول‌ها بتوانند register_hook کنند
        self.context.set_kernel(self)

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
        await self._dispatch_hook(SystemHook.ON_KERNEL_BOOTSTRAP_START)
        self.logger_api.log("🚀 Starting Framework Kernel...")
        
        modules_data = self._discover_modules(modules_dir)
        
        # تفکیک ماژول‌های سیستمی و کاربردی
        system_data = [m for m in modules_data if m["manifest"].get("type") == "system"]
        app_data = [m for m in modules_data if m["manifest"].get("type") != "system"]

        # --- فاز ۰: لود سیستم ---
        self.logger_api.log("🔩 Loading System Modules...")
        for mod_info in system_data:
            instance = self._instantiate_module(mod_info)
            await instance.load(self.context)
            await self._inject_system_apis(instance)
            await instance.start(self.context)
            self._modules[instance.name] = instance
            await self._dispatch_hook(SystemHook.ON_MODULE_LOADED, instance)

        # --- فاز ۱: لود اپلیکیشن ---
        self.logger_api.log("🔍 Resolving Application Modules...")
        
        # ⭐ اصلاح شده: ساخت نقشه قابلیت‌های سیستمی برای پاس دادن به رزولور
        system_provides = {}
        for m in system_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                system_provides[cap] = name

        # پاس دادن قابلیت‌های سیستمی به تابع مرتب‌ساز
        sorted_app = self._resolve_load_order(app_data, existing_provides=system_provides)

        self.logger_api.log("📦 Loading Application Modules...")
        for mod_info in sorted_app:
            instance = self._instantiate_module(mod_info)
            await instance.load(self.context)
            self._modules[instance.name] = instance
            await self._dispatch_hook(SystemHook.ON_MODULE_LOADED, instance)

        self.logger_api.log("▶️ Starting Application Modules...")
        for instance in self._modules.values():
             if instance not in [m['manifest']['name'] for m in system_data]:
                await instance.start(self.context)

        await self._dispatch_hook(SystemHook.ON_KERNEL_BOOTSTRAP_END)
        self.logger_api.log("✅ Framework initialization complete.\n")

    async def _inject_system_apis(self, system_module: IModule):
        # تزریق لاگر
        logger_service = self.context.services.get("core_logger")
        if logger_service and isinstance(logger_service, CoreLoggerAPI):
            self.logger_api.log(f"🔄 Overriding Core Logger with module: {system_module.name}")
            self.logger_api = logger_service 
            self.context.services.set("core_logger", self.logger_api)

        # تزریق کانفیگ
        config_service = self.context.services.get("core_config")
        if config_service and isinstance(config_service, CoreConfigAPI):
            self.logger_api.log(f"🔄 Overriding Core Config with module: {system_module.name}")
            self.config_api = config_service

    # ... متدهای کمکی ...
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
        
        # ⭐ اصلاح شده: اگر قابلیت‌های قبلی (سیستم) وجود دارند، اضافه کن
        provides_map = existing_provides.copy() if existing_provides else {}

        # اضافه کردن قابلیت‌های خود ماژول‌های درون لیست فعلی
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
                # اگر ارائه دهنده در سیستم بود (نه در لیست فعلی)، نیاز به بازگشت ندارد چون قبلاً لود شده
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
        self.logger_api.log("🛑 Shutting down framework...")
        for instance in reversed(list(self._modules.values())):
            await instance.stop(self.context)