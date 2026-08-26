"""
Module loader for the Massir framework.

This module provides the ModuleLoader class responsible for:
1. Instantiating module classes from manifest information
2. Checking module requirements against available capabilities

The loader is intentionally lightweight - all discovery, grouping,
and execution logic is handled by RunOrderGroupManager.
"""

import importlib
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from massir.core.interfaces import IModule, ModuleContext
from massir.core.exceptions import ModuleLoadError
from massir.core.path import Path as PathManager
from massir.core.log import log_internal
from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI


class ModuleLoader:
    """
    Module loader for instantiating modules and checking requirements.
    
    Responsibilities:
    1. instantiate(): Create module instance from manifest data
    2. check_requirements(): Verify module dependencies are available
    
    This class does NOT handle:
    - Module discovery (handled by RunOrderGroupManager)
    - Module grouping (handled by RunOrderGroupManager)
    - Dependency sorting (handled by RunOrderGroupManager)
    - Module starting/stopping (handled by RunOrderGroupManager)
    """
    
    def __init__(self, path: Optional[PathManager] = None):
        """
        Initialize module loader.
        
        Args:
            path: PathManager instance for path resolution (optional)
        """
        self._path = path
    
    def _get_app_dir(self) -> Path:
        """Get application directory path."""
        if self._path:
            return self._path.app
        return PathManager().app
    
    def _get_massir_dir(self) -> Path:
        """Get massir framework directory path."""
        if self._path:
            return self._path.massir
        return PathManager().massir
    
    def _resolve_path(self, path_template: str) -> Path:
        """
        Replace path placeholders with actual paths.
        
        Supported placeholders:
        - {massir_dir}: Path to the massir framework directory
        - {app_dir}: Path to the application directory
        
        Args:
            path_template: Path string with placeholders
            
        Returns:
            Resolved Path object
        """
        path = path_template
        if self._path:
            path = path.replace("{massir_dir}", str(self._path.massir))
            path = path.replace("{app_dir}", str(self._path.app))
        else:
            pm = PathManager()
            path = path.replace("{massir_dir}", str(pm.massir))
            path = path.replace("{app_dir}", str(pm.app))
        return Path(path)
    
    async def check_requirements(
        self,
        mod_info: Dict[str, Any],
        available_provides: Dict[str, str],
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI,
        disabled_modules: Optional[Dict[str, List[str]]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Check if module requirements are satisfied.
        
        Args:
            mod_info: Module info dict containing manifest
            available_provides: Dict mapping capability to provider module name
            config_api: Configuration API for logging
            logger_api: Logger API for logging
            disabled_modules: Dict of disabled modules and their capabilities
            
        Returns:
            Tuple of (requirements_met: bool, missing: List[str])
        """
        manifest = mod_info.get("manifest", {})
        requires = manifest.get("requires", [])
        missing = []
        disabled_modules = disabled_modules or {}
        
        for req_cap in requires:
            if req_cap not in available_provides:
                missing.append(req_cap)
                
                for disabled_name, disabled_caps in disabled_modules.items():
                    if req_cap in disabled_caps:
                        mod_name = manifest.get("name", "unknown")
                        log_internal(
                            config_api, logger_api,
                            f"Module '{mod_name}' requires '{req_cap}' "
                            f"provided by disabled module '{disabled_name}'",
                            level="WARNING", tag="core"
                        )
                        break
        
        return (len(missing) == 0), missing
    
    async def instantiate(
        self,
        mod_info: Dict[str, Any],
        context: ModuleContext,
        logger_ref: List[CoreLoggerAPI],
        config_ref: List[CoreConfigAPI]
    ) -> IModule:
        """
        Create module instance from manifest data.
        
        This method:
        1. Determines the Python import path
        2. Imports the module class
        3. Creates an instance
        4. Injects metadata from manifest
        
        Args:
            mod_info: Module info dict with path and manifest
            context: Module context for the instance
            logger_ref: Mutable logger reference [logger_api]
            config_ref: Mutable config reference [config_api]
            
        Returns:
            Instantiated module instance
            
        Raises:
            ModuleLoadError: If instantiation fails
        """
        manifest = mod_info["manifest"]
        mod_name = manifest["name"]
        mod_path = mod_info["path"]
        
        # Generate unique ID if not provided
        if "id" not in manifest:
            manifest["id"] = str(uuid.uuid4())[:8]
        mod_id = manifest["id"]
        
        # Get entrypoint class name
        class_name = manifest.get("entrypoint")
        if not class_name:
            raise ModuleLoadError(
                f"Module '{mod_name}' missing entrypoint in manifest"
            )
        
        # Determine Python import path
        import_path = self._determine_import_path(mod_path, mod_name)
        
        # Import module class
        try:
            module_lib = importlib.import_module(f"{import_path}.module")
            entry_class = getattr(module_lib, class_name)
        except ImportError as e:
            raise ModuleLoadError(
                f"Failed to import module '{mod_name}' from '{import_path}': {e}"
            )
        except AttributeError:
            raise ModuleLoadError(
                f"Class '{class_name}' not found in '{import_path}.module'"
            )
        
        # Create instance
        try:
            instance: IModule = entry_class()
        except Exception as e:
            raise ModuleLoadError(f"Failed to instantiate '{mod_name}': {e}")
        
        # Inject metadata from manifest
        instance.name = mod_name
        instance.id = mod_id
        instance.provides = manifest.get("provides", [])
        instance.requires = manifest.get("requires", [])
        
        # Set context reference
        instance._context = context
        
        return instance
    
    def _determine_import_path(self, mod_path: Path, mod_name: str) -> str:
        """
        Determine Python import path for a module.
        
        Algorithm:
        1. If path is under massir_dir -> massir.modules.xxx
        2. If path is under app_dir -> relative path from app_dir
        3. Otherwise -> use path directly (with path separators as dots)
        
        Args:
            mod_path: Path to module directory
            mod_name: Module name for logging
            
        Returns:
            Python import path string
        """
        mod_path = Path(mod_path).resolve()
        massir_dir = self._get_massir_dir().resolve()
        app_dir = self._get_app_dir().resolve()
        
        # Try relative to massir_dir (framework modules)
        try:
            rel_path = mod_path.relative_to(massir_dir)
            parts = rel_path.parts
            if len(parts) >= 2 and parts[0] == "modules":
                return "massir." + ".".join(parts)
        except ValueError:
            pass
        
        # Try relative to app_dir (application modules)
        try:
            rel_path = mod_path.relative_to(app_dir)
            parts = rel_path.parts
            return ".".join(parts)
        except ValueError:
            pass
        
        # Fallback: convert path to dotted notation
        path_str = str(mod_path)
        path_str = path_str.replace("/", ".").replace("\\", ".")
        return path_str