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
    """
    Module loader for discovering, loading, and managing modules.
    """

    def __init__(self, path: Optional[PathManager] = None):
        """
        Initialize module loader.

        Args:
            path: PathManager instance for accessing paths (optional)
        """
        self._path = path

    async def discover_modules(
        self,
        modules_config: List[Dict],
        is_system: bool,
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI
    ) -> tuple[List[Dict], Dict[str, List[str]], bool]:
        """
        Discover modules from settings.

        Args:
            modules_config: List of module settings
            is_system: Are these system modules?
            config_api: Configuration API
            logger_api: Logger API

        Returns:
            Tuple of (List of discovered modules, Dict of disabled modules with their capabilities, should_sort bool)
            disabled_modules format: {module_name: [list of capabilities it provides]}
            should_sort: True if modules should be sorted by dependencies (when names="all")
        """
        discovered = []
        disabled_modules = {}  # Track disabled modules and their capabilities
        should_sort = False  # Default: don't sort, preserve list order

        for module_group in modules_config:
            path_template = module_group.get("path", "")
            names = module_group.get("names", [])

            # Replace placeholders
            path = self._resolve_path(path_template)

            if not path.exists() or not path.is_dir():
                # Always warn - module folder not found
                module_type = "System" if is_system else "Application"
                log_internal(
                    config_api,
                    logger_api,
                    f"{module_type} module path not found: {path}",
                    level="WARNING",
                    tag="core"
                )
                continue

            # Track if names was explicitly provided as a list (not "all")
            explicit_names = isinstance(names, list)
            
            # If names = "all", list all folders and mark for sorting
            if names == "all":
                # Use resolved path (path), not template
                names = [f.name for f in path.iterdir() if f.is_dir()]
                should_sort = True  # When "all" is used, sort by dependencies

            # Discover each module
            for name in names:
                module_path = path / name
                manifest_path = module_path / "manifest.json"

                if manifest_path.exists():
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)

                    # Check module type
                    manifest_type = manifest.get("type", "application")
                    is_module_system = (manifest_type == "system")

                    # If looking for system modules, only system modules
                    # If looking for application modules, only application modules
                    if is_system and not is_module_system:
                        continue
                    if not is_system and is_module_system:
                        continue

                    # Check if module is enabled (default: true)
                    is_enabled = manifest.get("enabled", True)
                    if not is_enabled:
                        # Only warn if module name was explicitly requested in names list
                        # (not when using "all" to auto-discover)
                        if explicit_names:
                            module_type = "System" if is_system else "Application"
                            log_internal(
                                config_api,
                                logger_api,
                                f"{module_type} module '{name}' is disabled in manifest but was requested in settings",
                                level="WARNING",
                                tag="core"
                            )
                        # Track disabled module and its capabilities
                        provides = manifest.get("provides", [])
                        if provides:
                            disabled_modules[name] = provides
                        continue

                    # Generate unique ID if doesn't exist
                    if "id" not in manifest:
                        import uuid
                        manifest["id"] = str(uuid.uuid4())[:8]

                    discovered.append({
                        "path": module_path,
                        "manifest": manifest
                    })

        return discovered, disabled_modules, should_sort

    def _resolve_path(self, path_template: str) -> Path:
        """
        Replace placeholders in path.

        Args:
            path_template: Path with placeholders

        Returns:
            Resolved path
        """
        path = path_template
        if self._path:
            path = path.replace("{massir_dir}", str(self._path.massir))
            path = path.replace("{app_dir}", str(self._path.app))
        else:
            # fallback: use new PathManager
            pm = PathManager()
            path = path.replace("{massir_dir}", str(pm.massir))
            path = path.replace("{app_dir}", str(pm.app))
        return Path(path)

    async def check_requirements(
        self,
        mod_info: Dict,
        system_provides: Dict,
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI,
        disabled_modules: Dict[str, List[str]] = None
    ) -> tuple[bool, List[str]]:
        """
        Check requirements of a module.

        Args:
            mod_info: Module information
            system_provides: Dictionary of capabilities provided by system
            config_api: Configuration API
            logger_api: Logger API
            disabled_modules: Dictionary of disabled modules and their capabilities

        Returns:
            (all_requirements_met: bool, missing_requirements: List[str])
        """
        requires = mod_info["manifest"].get("requires", [])
        missing = []
        disabled_modules = disabled_modules or {}

        for req_cap in requires:
            if req_cap not in system_provides:
                missing.append(req_cap)
                # Check if this capability is provided by a disabled module
                for disabled_name, disabled_caps in disabled_modules.items():
                    if req_cap in disabled_caps:
                        mod_name = mod_info["manifest"]["name"]
                        log_internal(
                            config_api,
                            logger_api,
                            f"Module '{mod_name}' requires '{req_cap}' which is provided by disabled module '{disabled_name}'",
                            level="WARNING",
                            tag="core"
                        )
                        break

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
        Instantiate and load module.

        Args:
            mod_info: Module information including path and manifest
            is_system: Is this a system module?
            context: Module context
            logger_ref: Reference to logger (for updating)
            config_ref: Reference to config (for updating)

        Returns:
            Module instance
        """
        instance = await self.instantiate(mod_info, is_system=is_system)
        instance._context = context

        await instance.load(context)

        # Inject system APIs if provided by module
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
        config_ref: list[CoreConfigAPI],
        disabled_modules: Dict[str, List[str]] = None
    ):
        """
        Load system modules.

        Args:
            system_data: List of system module information
            modules: Dictionary of loaded modules
            config_api: Configuration API
            logger_api: Logger API
            context: Module context
            logger_ref: Reference to logger (for updating)
            config_ref: Reference to config (for updating)
            disabled_modules: Dictionary of disabled modules and their capabilities
        """
        log_internal(config_api, logger_api, "Loading System Modules...", level="CORE", tag="core_init")
        disabled_modules = disabled_modules or {}

        for mod_info in system_data:
            mod_name = mod_info["manifest"]["name"]
            is_forced = mod_info["manifest"].get("forced_execute", False)

            # Extract capabilities from previous systems
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
                requirements_met, missing = await self.check_requirements(mod_info, system_provides, config_api, logger_api, disabled_modules)

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
        config_ref: list[CoreConfigAPI],
        disabled_modules: Dict[str, List[str]] = None,
        should_sort: bool = False
    ):
        """
        Load application modules.

        Args:
            app_data: List of application module information
            modules: Dictionary of loaded modules
            config_api: Configuration API
            logger_api: Logger API
            context: Module context
            logger_ref: Reference to logger (for updating)
            config_ref: Reference to config (for updating)
            disabled_modules: Dictionary of disabled modules and their capabilities
            should_sort: Whether to sort modules by dependencies (True when names="all")
        """
        log_internal(config_api, logger_api, "Loading Application Modules...", level="CORE", tag="core")
        disabled_modules = disabled_modules or {}

        # Extract capabilities from loaded systems (from actual instances, not manifest)
        system_provides = {}
        for m in modules.values():
            if hasattr(m, '_is_system') and m._is_system:
                provides = getattr(m, 'provides', [])
                if isinstance(provides, list):
                    for cap in provides:
                        system_provides[cap] = m.name

        system_provides["core_logger"] = "App_Default"
        system_provides["core_config"] = "App_Default"

        # Separate forced and regular
        forced_app_data = [m for m in app_data if m["manifest"].get("forced_execute", False)]
        regular_app_data = [m for m in app_data if not m["manifest"].get("forced_execute", False)]

        # Sort regular modules by dependency order only when should_sort is True
        if should_sort:
            try:
                regular_app_data = self.resolve_order(regular_app_data, system_provides, force_execute=False)
            except DependencyResolutionError as e:
                log_internal(config_api, logger_api, f"Dependency resolution error: {e}", level="ERROR", tag="core")

        # --- Process forced ---
        for mod_info in forced_app_data:
            mod_name = mod_info["manifest"]["name"]

            try:
                requirements_met, missing = await self.check_requirements(mod_info, system_provides, config_api, logger_api, disabled_modules)

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
                
                # Update system_provides with capabilities from this module
                provides = getattr(mod_instance, 'provides', [])
                if isinstance(provides, list):
                    for cap in provides:
                        system_provides[cap] = mod_name

            except Exception as e:
                log_internal(config_api, logger_api, f"Application module '{mod_name}' failed to load: {e}", level="ERROR", tag="core")

        # --- Process regular ---
        for mod_info in regular_app_data:
            mod_name = mod_info["manifest"]["name"]

            try:
                requirements_met, missing = await self.check_requirements(mod_info, system_provides, config_api, logger_api, disabled_modules)

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
                
                # Update system_provides with capabilities from this module
                provides = getattr(mod_instance, 'provides', [])
                if isinstance(provides, list):
                    for cap in provides:
                        system_provides[cap] = mod_name

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
        Start all modules.

        Args:
            modules: Dictionary of modules
            system_module_names: List of system module names
            app_module_names: List of application module names
            config_api: Configuration API
            logger_api: Logger API
            hooks_manager: Hooks manager
        """
        log_internal(config_api, logger_api, "Starting Modules...", level="CORE", tag="core")

        # Start system modules
        for mod_name in system_module_names:
            if mod_name in modules:
                try:
                    await modules[mod_name].start(modules[mod_name]._context)
                    await hooks_manager.dispatch(SystemHook.ON_MODULE_LOADED, modules[mod_name])
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error starting system module '{mod_name}': {e}", level="ERROR", tag="core")

        # Start application modules
        for mod_name in app_module_names:
            if mod_name in modules:
                try:
                    await modules[mod_name].start(modules[mod_name]._context)
                    await hooks_manager.dispatch(SystemHook.ON_MODULE_LOADED, modules[mod_name])
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error starting application module '{mod_name}': {e}", level="ERROR", tag="core")

    async def ready_all_modules(
        self,
        modules: Dict[str, 'IModule'],
        system_module_names: List[str],
        app_module_names: List[str],
        config_api: CoreConfigAPI,
        logger_api: CoreLoggerAPI,
        hooks_manager
    ):
        """
        Call ready on all modules after they have started.

        Args:
            modules: Dictionary of modules
            system_module_names: List of system module names
            app_module_names: List of application module names
            config_api: Configuration API
            logger_api: Logger API
            hooks_manager: Hooks manager
        """
        log_internal(config_api, logger_api, "All modules started. Calling ready on modules...", level="CORE", tag="core")

        # Call ready on system modules
        for mod_name in system_module_names:
            if mod_name in modules:
                try:
                    await modules[mod_name].ready(modules[mod_name]._context)
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error calling ready on system module '{mod_name}': {e}", level="ERROR", tag="core")

        # Call ready on application modules
        for mod_name in app_module_names:
            if mod_name in modules:
                try:
                    await modules[mod_name].ready(modules[mod_name]._context)
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error calling ready on application module '{mod_name}': {e}", level="ERROR", tag="core")

        # Dispatch hook after all modules are ready
        await hooks_manager.dispatch(SystemHook.ON_ALL_MODULES_READY)
        log_internal(config_api, logger_api, "All modules are ready.", level="CORE", tag="core")

    def resolve_order(self, modules_data: List[Dict], existing_provides: Dict[str, str] = None, force_execute: bool = False) -> List[Dict]:
        """
        Sort modules based on dependencies.

        Args:
            modules_data: List of module data
            existing_provides: Dictionary of existing capabilities
            force_execute: If True, missing dependencies are ignored
                           and modules are loaded anyway.
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
        """Get app_dir from path.py"""
        if self._path:
            return self._path.app
        # fallback: use new PathManager
        return PathManager().app

    def _get_massir_dir(self) -> Path:
        """Get massir_dir from path.py"""
        if self._path:
            return self._path.massir
        # fallback: use new PathManager
        return PathManager().massir

    async def instantiate(self, mod_info: Dict, is_system: bool = False) -> IModule:
        """
        Create instance (Object) from module class.

        Args:
            mod_info: Module information including path and manifest
            is_system: Is this a system module?

        Returns:
            Module instance
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

        # Module path
        rel_path = mod_info["path"]

        # Build import_path based on module type
        if is_system:
            # System modules are loaded from massir
            massir_dir = self._get_massir_dir()
            if rel_path.is_absolute():
                try:
                    rel_path = rel_path.relative_to(massir_dir)
                except ValueError:
                    pass
            import_path = "massir." + ".".join(rel_path.parts)
        else:
            # Application modules are loaded from app_dir
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
