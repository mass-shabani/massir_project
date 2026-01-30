import json
import importlib
from pathlib import Path
from typing import List, Dict
from core.interfaces import IModule
from core.exceptions import ModuleLoadError, DependencyResolutionError

class ModuleLoader:
    def __init__(self):
        pass

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

    def resolve_order(self, modules_data: List[Dict], existing_provides: Dict[str, str] = None) -> List[Dict]:
        """مرتب‌سازی ماژول‌ها بر اساس وابستگی‌ها"""
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

    def instantiate(self, mod_info: Dict) -> IModule:
        """ایجاد نمونه (Object) از کلاس ماژول"""
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