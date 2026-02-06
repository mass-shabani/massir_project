import json
import importlib
from pathlib import Path
from typing import List, Dict, Optional
from massir.core.interfaces import IModule
from massir.core.exceptions import ModuleLoadError, DependencyResolutionError
from massir.core.path import Path as PathManager

class ModuleLoader:
    def __init__(self, path: Optional[PathManager] = None):
        """
        Args:
            path: نمونه PathManager برای دسترسی به مسیرها (اختیاری)
        """
        self._path = path

    def discover(self, directory: str) -> List[Dict]:
        """پیدا کردن تمام فایل‌های manifest.json"""
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
                    else:
                        print(f"[WARNING] Forced load: Module '{name}' requires '{req_cap}' (missing) but loading anyway.")
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

    def instantiate(self, mod_info: Dict, is_system: bool = False) -> IModule:
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
