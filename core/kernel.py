import json
import importlib
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# ایمپورت ModuleContext از interfaces (حالا دیگر چرخه وجود ندارد)
from core.interfaces import IModule, ModuleContext 
from core.registry import ModuleRegistry
from core.exceptions import DependencyResolutionError

class Kernel:
    def __init__(self):
        self._modules: Dict[str, IModule] = {}
        # نیازی به تعریف ModuleContext در اینجا نیست، چون بالاتر ایمپورت شد
        self.context = ModuleContext()

    async def bootstrap(self, modules_dir: str = "modules"):
        print("🚀 Starting Framework Kernel...")
        
        # 1. جمع‌آوری اطلاعات ماژول‌ها (Discovery)
        modules_data = self._discover_modules(modules_dir)
        
        # 2. حل وابستگی‌ها و مرتب‌سازی (Dependency Resolution)
        print("🔍 Resolving dependencies...")
        sorted_modules = self._resolve_load_order(modules_data)

        # 3. ایجاد نمونه (Instantiate) و لود اولیه
        print("📦 Loading modules instances...")
        for mod_info in sorted_modules:
            instance = self._instantiate_module(mod_info)
            await instance.load(self.context)
            self._modules[instance.name] = instance

        # 4. استارت ماژول‌ها (Start Phase)
        print("▶️ Starting modules...")
        for instance in self._modules.values():
            await instance.start(self.context)

        print("✅ Framework initialization complete.\n")

    async def shutdown(self):
        print("\n🛑 Shutting down framework...")
        for instance in reversed(list(self._modules.values())):
            await instance.stop(self.context)

    def _discover_modules(self, directory: str) -> List[Dict]:
        found = []
        base_path = Path(directory)
        if not base_path.exists():
            raise FileNotFoundError(f"Modules directory not found: {directory}")

        for manifest_path in base_path.rglob("manifest.json"):
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                module_folder = manifest_path.parent
                found.append({
                    "path": module_folder,
                    "manifest": data
                })
        return found

    def _resolve_load_order(self, modules_data: List[Dict]) -> List[Dict]:
        sorted_list = []
        visited = set()
        visiting = set() 
        
        provides_map = {}
        for m in modules_data:
            name = m["manifest"]["name"]
            provides = m["manifest"].get("provides", [])
            for cap in provides:
                provides_map[cap] = name

        def visit(mod_info):
            name = mod_info["manifest"]["name"]
            if name in visiting:
                raise DependencyResolutionError(f"Circular dependency detected involving module '{name}'")
            if name in visited:
                return

            visiting.add(name)
            
            requires = mod_info["manifest"].get("requires", [])
            for req_cap in requires:
                if req_cap not in provides_map:
                    raise DependencyResolutionError(
                        f"Module '{name}' requires capability '{req_cap}' but no module provides it."
                    )
                provider_name = provides_map[req_cap]
                provider_info = next((m for m in modules_data if m["manifest"]["name"] == provider_name), None)
                if provider_info:
                    visit(provider_info)

            visiting.remove(name)
            visited.add(name)
            sorted_list.append(mod_info)

        for mod_info in modules_data:
            visit(mod_info)
            
        return sorted_list

    def _instantiate_module(self, mod_info: Dict) -> IModule:
        manifest = mod_info["manifest"]
        mod_name = manifest["name"]
        class_name = manifest.get("entrypoint")
        
        if not class_name:
            raise ModuleLoadError(f"Module '{mod_name}' missing 'entrypoint' in manifest.")

        # ساخت مسیر ایمپورت
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
            raise ModuleLoadError(f"Failed to load module '{mod_name}': {e}")