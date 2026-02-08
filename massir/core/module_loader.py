import json
import importlib
from pathlib import Path
from typing import List, Dict, Optional
from massir.core.interfaces import IModule, ModuleContext
from massir.core.exceptions import ModuleLoadError, DependencyResolutionError
from massir.core.path import Path as PathManager
from massir.core.log import log_internal
from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI
from massir.core.hook_types import SystemHook
from massir.core.inject import inject_system_apis

class ModuleLoader:
    def __init__(self, path: Optional[PathManager] = None):
        """
        Args:
            path: نمونه PathManager برای دسترسی به مسیرها (اختیاری)
        """
        self._path = path
    
    async def discover_modules(
        self, 
        modules_config: List[Dict], 
        is_system: bool,
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI
    ) -> List[Dict]:
        """
        کشف ماژول‌ها از تنظیمات
        
        Args:
            modules_config: لیست تنظیمات ماژول‌ها
            is_system: آیا ماژول‌های سیستمی هستند؟
            config_api: API تنظیمات
            logger_api: API لاگر
            
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
                # هشدار همیشه - پیدا نشدن پوشه ماژول
                module_type = "System" if is_system else "Application"
                log_internal(
                    config_api, 
                    logger_api, 
                    f"{module_type} module path not found: {path}", 
                    level="WARNING",
                    tag="core"
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
        if self._path:
            path = path.replace("{massir_dir}", str(self._path.massir))
            path = path.replace("{app_dir}", str(self._path.app))
        else:
            # fallback: استفاده از PathManager جدید
            pm = PathManager()
            path = path.replace("{massir_dir}", str(pm.massir))
            path = path.replace("{app_dir}", str(pm.app))
        return Path(path)

    async def check_requirements(
        self, 
        mod_info: Dict, 
        system_provides: Dict,
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI
    ) -> tuple[bool, List[str]]:
        """
        بررسی پیشنیازهای یک ماژول.
        
        Args:
            mod_info: اطلاعات ماژول
            system_provides: دیکشنری قابلیت‌های ارائه شده توسط سیستم
            config_api: API تنظیمات
            logger_api: API لاگر
            
        Returns:
            (all_requirements_met: bool, missing_requirements: List[str])
        """
        requires = mod_info["manifest"].get("requires", [])
        missing = []
        
        for req_cap in requires:
            if req_cap not in system_provides:
                missing.append(req_cap)
        
        return (len(missing) == 0), missing
    
    async def instantiate_and_load(
        self,
        mod_info: Dict,
        is_system: bool,
        context: 'ModuleContext',
        logger_ref: list[CoreLoggerAPI],
        config_ref: list[CoreConfigAPI]
    ) -> 'IModule':
        """
        نمونه‌سازی و load ماژول
        
        Args:
            mod_info: اطلاعات ماژول شامل path و manifest
            is_system: آیا ماژول سیستمی است؟
            context: کانتکست ماژول
            logger_ref: رفرنس به لاگر (برای بروزرسانی)
            config_ref: رفرنس به کانفیگ (برای بروزرسانی)
            
        Returns:
            نمونه ماژول
        """
        instance = await self.instantiate(mod_info, is_system=is_system)
        instance._context = context
        
        await instance.load(context)
        
        # تزریق API های سیستم در صورت ارائه توسط ماژول
        await inject_system_apis(instance, context.services, logger_ref, config_ref)
        
        if is_system:
            setattr(instance, '_is_system', True)
        
        return instance
    
    async def load_system_modules(
        self,
        system_data: List[Dict],
        modules: Dict[str, 'IModule'],
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI,
        context: 'ModuleContext',
        logger_ref: list[CoreLoggerAPI],
        config_ref: list[CoreConfigAPI]
    ):
        """
        لود ماژول‌های سیستمی
        
        Args:
            system_data: لیست اطلاعات ماژول‌های سیستمی
            modules: دیکشنری ماژول‌های لود شده
            config_api: API تنظیمات
            logger_api: API لاگر
            context: کانتکست ماژول
            logger_ref: رفرنس به لاگر (برای بروزرسانی)
            config_ref: رفرنس به کانفیگ (برای بروزرسانی)
        """
        log_internal(config_api, logger_api, "Loading System Modules...", level="CORE", tag="core_init")
        
        for mod_info in system_data:
            mod_name = mod_info["manifest"]["name"]
            is_forced = mod_info["manifest"].get("forced_execute", False)
            
            # استخراج قابلیت‌های سیستم‌های قبلی
            system_provides = {}
            for m in modules.values():
                if hasattr(m, '_is_system') and m._is_system:
                    provides = getattr(m, 'provides', [])
                    if isinstance(provides, list):
                        for cap in provides:
                            system_provides[cap] = m.name
            
            system_provides["core_logger"] = "App_Default"
            system_provides["core_config"] = "App_Default"
            
            try:
                requirements_met, missing = await self.check_requirements(mod_info, system_provides, config_api, logger_api)
                
                if not requirements_met:
                    log_internal(
                        config_api, logger_api,
                        f"System module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    
                    if not is_forced:
                        log_internal(config_api, logger_api, f"Skipping module '{mod_name}' (not forced)", level="CORE", tag="core")
                        continue
                    else:
                        log_internal(config_api, logger_api, f"Forced execution of '{mod_name}'", level="WARNING", tag="core")
                
                mod_instance = await self.instantiate_and_load(
                    mod_info,
                    is_system=True,
                    context=context,
                    logger_ref=logger_ref,
                    config_ref=config_ref
                )
                modules[mod_name] = mod_instance
                log_internal(config_api, logger_api, f"System module '{mod_name}' loaded", level="CORE", tag="core")
                
            except Exception as e:
                log_internal(config_api, logger_api, f"System module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")
    
    async def load_application_modules(
        self,
        app_data: List[Dict],
        modules: Dict[str, 'IModule'],
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI,
        context: 'ModuleContext',
        logger_ref: list[CoreLoggerAPI],
        config_ref: list[CoreConfigAPI]
    ):
        """
        لود ماژول‌های کاربردی
        
        Args:
            app_data: لیست اطلاعات ماژول‌های کاربردی
            modules: دیکشنری ماژول‌های لود شده
            config_api: API تنظیمات
            logger_api: API لاگر
            context: کانتکست ماژول
            logger_ref: رفرنس به لاگر (برای بروزرسانی)
            config_ref: رفرنس به کانفیگ (برای بروزرسانی)
        """
        log_internal(config_api, logger_api, "Loading Application Modules...", level="CORE", tag="core")
        
        # استخراج قابلیت‌های سیستم‌های لود شده (از نمونه‌های واقعی، نه manifest)
        system_provides = {}
        for m in modules.values():
            if hasattr(m, '_is_system') and m._is_system:
                provides = getattr(m, 'provides', [])
                if isinstance(provides, list):
                    for cap in provides:
                        system_provides[cap] = m.name
        
        system_provides["core_logger"] = "App_Default"
        system_provides["core_config"] = "App_Default"
        
        # تفکیک اجباری و معمولی
        forced_app_data = [m for m in app_data if m["manifest"].get("forced_execute", False)]
        regular_app_data = [m for m in app_data if not m["manifest"].get("forced_execute", False)]
        
        # --- پردازش اجباری ---
        for mod_info in forced_app_data:
            mod_name = mod_info["manifest"]["name"]
            
            try:
                requirements_met, missing = await self.check_requirements(mod_info, system_provides, config_api, logger_api)
                
                if not requirements_met:
                    log_internal(
                        config_api, logger_api,
                        f"Application module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    log_internal(config_api, logger_api, f"Forced execution of '{mod_name}'", level="WARNING", tag="core")
                
                mod_instance = await self.instantiate_and_load(
                    mod_info,
                    is_system=False,
                    context=context,
                    logger_ref=logger_ref,
                    config_ref=config_ref
                )
                modules[mod_name] = mod_instance
                log_internal(config_api, logger_api, f"Application module '{mod_name}' loaded", level="CORE", tag="core")
                
            except Exception as e:
                log_internal(config_api, logger_api, f"Application module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")
        
        # --- پردازش معمولی ---
        for mod_info in regular_app_data:
            mod_name = mod_info["manifest"]["name"]
            
            try:
                requirements_met, missing = await self.check_requirements(mod_info, system_provides, config_api, logger_api)
                
                if not requirements_met:
                    log_internal(
                        config_api, logger_api,
                        f"Application module '{mod_name}' requires: {', '.join(missing)} (not found)",
                        level="WARNING", tag="core"
                    )
                    log_internal(config_api, logger_api, f"Skipping module '{mod_name}' (not forced)", level="CORE", tag="core")
                    continue
                
                mod_instance = await self.instantiate_and_load(
                    mod_info,
                    is_system=False,
                    context=context,
                    logger_ref=logger_ref,
                    config_ref=config_ref
                )
                modules[mod_name] = mod_instance
                log_internal(config_api, logger_api, f"Application module '{mod_name}' loaded", level="CORE", tag="core")
                
            except Exception as e:
                log_internal(config_api, logger_api, f"Application module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")
    
    async def start_all_modules(
        self,
        modules: Dict[str, 'IModule'],
        system_module_names: List[str],
        app_module_names: List[str],
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI,
        hooks_manager
    ):
        """
        استارت تمام ماژول‌ها
        
        Args:
            modules: دیکشنری ماژول‌ها
            system_module_names: لیست نام ماژول‌های سیستمی
            app_module_names: لیست نام ماژول‌های کاربردی
            config_api: API تنظیمات
            logger_api: API لاگر
            hooks_manager: مدیریت هوک‌ها
        """
        log_internal(config_api, logger_api, "Starting Modules...", level="CORE", tag="core")
        
        # استارت ماژول‌های سیستمی
        for mod_name in system_module_names:
            if mod_name in modules:
                try:
                    await modules[mod_name].start(modules[mod_name]._context)
                    await hooks_manager.dispatch(SystemHook.ON_MODULE_LOADED, modules[mod_name])
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error starting system module '{mod_name}': {e}", level="ERROR", tag="core")
        
        # استارت ماژول‌های کاربردی
        for mod_name in app_module_names:
            if mod_name in modules:
                try:
                    await modules[mod_name].start(modules[mod_name]._context)
                    await hooks_manager.dispatch(SystemHook.ON_MODULE_LOADED, modules[mod_name])
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error starting application module '{mod_name}': {e}", level="ERROR", tag="core")
    
    def resolve_order(self, modules_data: List[Dict], existing_provides: Dict[str, str] = None, force_execute: bool = False) -> List[Dict]:
        """
        مرتب‌سازی ماژول‌ها بر اساس وابستگی‌ها.
        
        Args:
            force_execute: اگر True باشد، وابستگی‌های گمشده نادیده گرفته می‌شوند
                           و ماژول‌ها در هر صورت لود می‌شوند.
        """
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
                    if not force_execute:
                        raise DependencyResolutionError(f"'{name}' requires '{req_cap}' but none provides it.")
                    # Note: Cannot log here as config_api and logger_api are not available in resolve_order
                else:
                    provider_name = provides_map[req_cap]
                    provider_info = next((m for m in modules_data if m["manifest"]["name"] == provider_name), None)
                    if provider_info: visit(provider_info)
            visiting.remove(name)
            visited.add(name)
            sorted_list.append(mod_info)

        for mod_info in modules_data: visit(mod_info)
        return sorted_list

    def _get_app_dir(self) -> Path:
        """دریافت app_dir از path.py"""
        if self._path:
            return self._path.app
        # fallback: استفاده از PathManager جدید
        return PathManager().app

    def _get_massir_dir(self) -> Path:
        """دریافت massir_dir از path.py"""
        if self._path:
            return self._path.massir
        # fallback: استفاده از PathManager جدید
        return PathManager().massir

    async def instantiate(self, mod_info: Dict, is_system: bool = False) -> IModule:
        """
        ایجاد نمونه (Object) از کلاس ماژول
        
        Args:
            mod_info: اطلاعات ماژول شامل path و manifest
            is_system: آیا ماژول سیستمی است؟
        """
        manifest = mod_info["manifest"]
        mod_name = manifest["name"]
        
        if "id" not in manifest:
            import uuid
            manifest["id"] = str(uuid.uuid4())[:8]
        
        mod_id = manifest["id"]
        class_name = manifest.get("entrypoint")
        if not class_name:
            raise ModuleLoadError(f"Module '{mod_name}' missing entrypoint.")
        
        # مسیر ماژول
        rel_path = mod_info["path"]
        
        # ساخت import_path بر اساس نوع ماژول
        if is_system:
            # ماژول‌های سیستمی از massir لود می‌شوند
            massir_dir = self._get_massir_dir()
            if rel_path.is_absolute():
                try:
                    rel_path = rel_path.relative_to(massir_dir)
                except ValueError:
                    pass
            import_path = "massir." + ".".join(rel_path.parts)
        else:
            # ماژول‌های application از app_dir لود می‌شوند
            app_dir = self._get_app_dir()
            if rel_path.is_absolute():
                try:
                    rel_path = rel_path.relative_to(app_dir)
                except ValueError:
                    pass
            import_path = ".".join(rel_path.parts)
        
        try:
            module_lib = importlib.import_module(f"{import_path}.module")
            entry_class = getattr(module_lib, class_name)
            instance: IModule = entry_class()
            instance.name = mod_name
            instance.id = mod_id
            return instance
        except Exception as e:
            raise ModuleLoadError(f"Failed to load '{mod_name}': {e}")
