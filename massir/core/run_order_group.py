"""
Run order group management for the Massir framework.

This module implements:
1. RunAtRegistry - Dynamic registry for valid run_at values
2. RunOrderGroup - Data class for group configuration
3. RunOrderGroupManager - Execution manager for module groups

The run_at system is fully dynamic:
- "on_start" is the default value, executed during bootstrap
- All SystemHook enum values are automatically registered as valid run_at values
- When SystemHook enum changes, valid run_at values update automatically
- Groups with run_at matching a SystemHook are executed when that hook is dispatched
"""

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Set

from massir.core.interfaces import IModule, ModuleContext
from massir.core.hook_types import SystemHook
from massir.core.hooks import HooksManager
from massir.core.module_loader import ModuleLoader
from massir.core.path import Path as PathManager
from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI
from massir.core.exceptions import DependencyResolutionError


class RunAtRegistry:
    """
    Dynamic registry for valid run_at values.
    
    This class automatically discovers and registers all valid run_at
    values from two sources:
    1. The default "on_start" value (executed during application bootstrap)
    2. All SystemHook enum values (executed when the corresponding hook fires)
    
    When the SystemHook enum changes (hooks added or removed), the valid
    run_at values automatically update on the next instantiation.
    
    This centralized registry replaces all static constants that were
    previously scattered across multiple files.
    """
    
    DEFAULT = "on_start"
    """Default run_at value, executed during application bootstrap."""
    
    def __init__(self):
        """Initialize registry with default value and all SystemHook values."""
        # Set of all valid run_at string values
        self._values: Set[str] = {self.DEFAULT}
        
        # Map from run_at string to SystemHook enum member
        self._hook_map: Dict[str, SystemHook] = {}
        
        # Automatically register all SystemHook values
        for hook in SystemHook:
            self._values.add(hook.value)
            self._hook_map[hook.value] = hook
    
    def is_valid(self, run_at: str) -> bool:
        """
        Check if a run_at value is valid.
        
        Args:
            run_at: Run_at string to validate
            
        Returns:
            True if valid, False otherwise
        """
        return run_at in self._values
    
    def get_default(self) -> str:
        """
        Get the default run_at value.
        
        Returns:
            Default run_at string ("on_start")
        """
        return self.DEFAULT
    
    def get_hook(self, run_at: str) -> Optional[SystemHook]:
        """
        Get the SystemHook associated with a run_at value.
        
        Args:
            run_at: Run_at string
            
        Returns:
            SystemHook enum member if mapped, None otherwise
        """
        return self._hook_map.get(run_at)
    
    def get_all_values(self) -> Set[str]:
        """
        Get all valid run_at values.
        
        Returns:
            Copy of the set of all valid run_at strings
        """
        return self._values.copy()
    
    def is_default(self, run_at: str) -> bool:
        """
        Check if a run_at value is the default.
        
        Args:
            run_at: Run_at string
            
        Returns:
            True if this is the default value
        """
        return run_at == self.DEFAULT
    
    def __repr__(self) -> str:
        return f"RunAtRegistry(values={len(self._values)})"


@dataclass
class ModuleInfo:
    """
    Information about a discovered module.
    
    Attributes:
        path: Path to the module directory
        manifest: Module manifest dict from manifest.json
        instance: Instantiated module (None until instantiated)
    """
    path: Path
    manifest: Dict[str, Any]
    instance: Optional[IModule] = None


@dataclass
class RunOrderGroup:
    """
    Represents a group of modules to be executed together.
    
    Groups are processed at their specified run_at trigger point.
    All modules in a group must start before the group is complete.
    During shutdown, groups are stopped in reverse execution order.
    
    Attributes:
        name: Group identifier from configuration
        run_at: Execution trigger point (default: "on_start")
        path: Path template to module directory
        names: List of module names, or "all" for auto-discovery
        modules: List of discovered ModuleInfo objects
        is_started: Whether this group has been started
        is_completed: Whether all modules in this group have started
        is_stopped: Whether this group has been stopped
    """
    name: str
    run_at: str = RunAtRegistry.DEFAULT
    path: str = ""
    names: List[str] = field(default_factory=list)
    modules: List[ModuleInfo] = field(default_factory=list)
    is_started: bool = False
    is_completed: bool = False
    is_stopped: bool = False


class RunOrderGroupManager:
    """
    Manages execution of module groups at system trigger points.
    
    This class uses RunAtRegistry to dynamically determine valid run_at
    values. Groups are executed at their specified trigger point:
    
    - "on_start": Executed during application bootstrap (default)
    - Any SystemHook value: Executed when that hook is dispatched
    
    Auto-callback registration:
    After parsing groups, the manager automatically registers callbacks
    for all non-default run_at values. When the corresponding SystemHook
    is dispatched, the callback executes the matching groups.
    
    Execution order tracking:
    - All started groups are tracked in execution order
    - During shutdown, groups are stopped in reverse execution order
    """
    
    def __init__(
        self,
        hooks_manager: HooksManager,
        module_loader: ModuleLoader,
        path_manager: PathManager
    ):
        """
        Initialize run order group manager.
        
        Args:
            hooks_manager: Hooks manager for event dispatching
            module_loader: Module loader for instantiation
            path_manager: Path manager for path resolution
        """
        self.hooks = hooks_manager
        self.loader = module_loader
        self.path = path_manager
        
        # Dynamic run_at registry
        self.run_at_registry = RunAtRegistry()
        
        # List of RunOrderGroup in configuration order
        self.groups: List[RunOrderGroup] = []
        
        # Track execution order for reverse shutdown
        self._execution_order: List[RunOrderGroup] = []
        
        # Track disabled modules and their capabilities
        self._disabled_modules: Dict[str, List[str]] = {}
    
    # =========================================================================
    # Configuration Parsing
    # =========================================================================
    
    def parse_groups_from_config(
        self,
        modules_config: List[Dict[str, Any]],
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> None:
        """
        Parse group configurations from app_settings.json.
        
        Validates run_at values against the dynamic RunAtRegistry.
        Invalid values fall back to the default ("on_start").
        
        Args:
            modules_config: List of group configurations from settings
            config_api: Configuration API for logging
            logger_api: Logger API for logging
        """
        self.groups.clear()
        self._execution_order.clear()
        self._disabled_modules.clear()
        
        for i, group_config in enumerate(modules_config):
            run_at = group_config.get("run_at", self.run_at_registry.get_default())
            
            # Validate run_at using dynamic registry
            if not self.run_at_registry.is_valid(run_at):
                if logger_api_ref[0]:
                    logger_api_ref[0].log(
                        f"Invalid run_at value '{run_at}' for group "
                        f"'{group_config.get('name', f'group_{i}')}'. "
                        f"Valid values: {self.run_at_registry.get_all_values()}. "
                        f"Using default: {self.run_at_registry.get_default()}",
                        level="WARNING", tag="core"
                    )
                run_at = self.run_at_registry.get_default()
            
            group = RunOrderGroup(
                name=group_config.get("name", f"group_{i}"),
                run_at=run_at,
                path=group_config.get("path", ""),
                names=group_config.get("names", [])
            )
            
            self.groups.append(group)
            
            if logger_api_ref[0]:
                logger_api_ref[0].log(
                    f"Parsed run order group: '{group.name}' "
                    f"(run_at: {group.run_at}, path: {group.path}, "
                    f"names: {group.names})",
                    level="CORE", tag="core_init"
                )
    
    def register_run_at_callbacks(
        self,
        modules_registry: Dict[str, IModule],
        context: ModuleContext,
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> None:
        """
        Register callbacks for all non-default run_at values found in groups.
        
        For each unique run_at value that maps to a SystemHook, a callback
        is registered that executes the matching groups when the hook fires.
        This must be called after parse_groups_from_config() and before
        any hooks are dispatched.
        
        Args:
            modules_registry: Global module registry
            context: Module context
            config_api: Configuration API
            logger_api: Logger API
        """
        unique_values = self._get_unique_run_at_values()
        
        for run_at_value in unique_values:
            # Skip the default (handled by execute_on_start_groups)
            if self.run_at_registry.is_default(run_at_value):
                continue
            
            hook = self.run_at_registry.get_hook(run_at_value)
            if hook is None:
                continue
            
            # Create callback with proper closure (default arg captures value)
            async def callback(*args, rat=run_at_value, **kwargs):
                await self.execute_groups_for_run_at(
                    rat, modules_registry, context,
                    config_api_ref, logger_api_ref
                )
            
            self.hooks.register(hook, callback, logger_api_ref[0])
            
            if logger_api_ref[0]:
                logger_api_ref[0].log(
                    f"Auto-registered callback for run_at='{run_at_value}' "
                    f"(hook: {hook.value})",
                    level="CORE", tag="core"
                )
    
    # =========================================================================
    # Module Discovery
    # =========================================================================
    
    async def discover_modules_for_group(
        self,
        group: RunOrderGroup,
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> List[ModuleInfo]:
        """
        Discover modules for a specific group.
        
        This method reads manifest.json files from the group's path
        and validates required fields.
        
        Args:
            group: The run order group
            config_api: Configuration API
            logger_api: Logger API
            
        Returns:
            List of ModuleInfo for discovered and enabled modules
        """
        # Resolve path placeholders
        path_str = group.path
        path_str = path_str.replace("{massir_dir}", str(self.path.massir))
        path_str = path_str.replace("{app_dir}", str(self.path.app))
        
        group_path = Path(path_str)
        
        if not group_path.exists() or not group_path.is_dir():
            if logger_api_ref[0]:
                logger_api_ref[0].log(
                    f"Group '{group.name}' path not found: {group_path}",
                    level="WARNING", tag="core"
                )
            return []
        
        # Determine module names to load
        names = group.names
        explicit_names = isinstance(names, list)
        
        if names == "all":
            names = [f.name for f in group_path.iterdir() if f.is_dir()]
        
        discovered = []
        for name in names:
            module_path = group_path / name
            manifest_path = module_path / "manifest.json"
            
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    
                    # Validate required fields
                    missing = []
                    if not manifest.get("name"):
                        missing.append("name")
                    if not manifest.get("entrypoint"):
                        missing.append("entrypoint")
                    
                    if missing:
                        if logger_api_ref[0]:
                            logger_api_ref[0].log(
                                f"Module '{name}' in group '{group.name}' "
                                f"missing fields: {', '.join(missing)}",
                                level="ERROR", tag="core"
                            )
                        continue
                    
                    # Check if module is enabled
                    if not manifest.get("enabled", True):
                        if explicit_names:
                            if logger_api_ref[0]:
                                logger_api_ref[0].log(
                                    f"Module '{name}' in group '{group.name}' "
                                    f"is disabled in manifest",
                                    level="WARNING", tag="core"
                                )
                        provides = manifest.get("provides", [])
                        if provides:
                            self._disabled_modules[name] = provides
                        continue
                    
                    # Generate ID if not provided
                    if "id" not in manifest:
                        manifest["id"] = str(uuid.uuid4())[:8]
                    
                    discovered.append(ModuleInfo(
                        path=module_path,
                        manifest=manifest
                    ))
                    
                except Exception as e:
                    if logger_api_ref[0]:
                        logger_api_ref[0].log(
                            f"Invalid manifest for '{name}' in group "
                            f"'{group.name}': {e}",
                            level="ERROR", tag="core"
                        )
            else:
                if logger_api_ref[0]:
                    logger_api_ref[0].log(
                        f"Module '{name}' in group '{group.name}' "
                        f"missing manifest.json",
                        level="ERROR", tag="core"
                    )
        
        return discovered
    
    # =========================================================================
    # Group Execution
    # =========================================================================
    
    async def execute_group(
        self,
        group: RunOrderGroup,
        modules_registry: Dict[str, IModule],
        context: ModuleContext,
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> bool:
        # Use dynamic logger lookup so system_logger updates take effect
        """
        Execute a single run order group.
        
        This method:
        1. Discovers modules in the group
        2. Sorts modules by dependencies
        3. Instantiates each module
        4. Starts each module
        5. Dispatches lifecycle hooks
        6. Tracks group in execution order for shutdown
        
        Args:
            group: The run order group to execute
            modules_registry: Global module registry (updated in-place)
            context: Module context
            config_api: Configuration API
            logger_api: Logger API
            
        Returns:
            True if execution completed, False on error
        """
        if group.is_started:
            return True
        
        group.is_started = True
        
        # Use dynamic logger lookup so system_logger updates take effect
        
        # Dispatch group start hook
        await self.hooks.dispatch(SystemHook.ON_GROUP_START, group.name)
        
        if logger_api_ref[0]:
            logger_api_ref[0].log(
                f"Starting run order group: '{group.name}' "
                f"(run_at: {group.run_at})",
                level="CORE", tag="core"
            )
        
        # Discover modules for this group
        group.modules = await self.discover_modules_for_group(
            group, config_api_ref, logger_api_ref
        )
        
        if not group.modules:
            if logger_api_ref[0]:
                logger_api_ref[0].log(
                    f"No modules found in group '{group.name}'",
                    level="WARNING", tag="core"
                )
            group.is_completed = True
            self._execution_order.append(group)
            await self.hooks.dispatch(SystemHook.ON_GROUP_COMPLETE, group.name)
            return True
        
        # Sort modules by dependencies within the group
        sorted_modules = self._sort_by_dependencies(
            group.modules, config_api_ref, logger_api_ref
        )
        
        # Build available provides from already-loaded modules
        available_provides = self._get_available_provides(modules_registry)
        
        # Include core framework services that are always available after bootstrap
        if config_api_ref[0] is not None:
            available_provides.setdefault("core_config", "core")
        if logger_api_ref[0] is not None:
            available_provides.setdefault("core_logger", "core")
        
        # Instantiate and start each module
        for mod_info in sorted_modules:
            mod_name = mod_info.manifest["name"]
            
            try:
                # Check requirements
                reqs_met, missing = await self.loader.check_requirements(
                    {"manifest": mod_info.manifest, "path": str(mod_info.path)}, 
                    available_provides,
                    config_api_ref[0], logger_api_ref[0], self._disabled_modules
                )
                
                if not reqs_met:
                    is_forced = mod_info.manifest.get("forced_execute", False)
                    if not is_forced:
                        if logger_api_ref[0]:
                            logger_api_ref[0].log(
                                f"Module '{mod_name}' missing requirements: "
                                f"{missing}. Skipping.",
                                level="WARNING", tag="core"
                            )
                        continue
                    else:
                        if logger_api_ref[0]:
                            logger_api_ref[0].log(
                                f"Forced execution of '{mod_name}' "
                                f"despite missing: {missing}",
                                level="WARNING", tag="core"
                            )
                
                # Instantiate module
                instance = await self.loader.instantiate(
                    {"manifest": mod_info.manifest, "path": str(mod_info.path)},
                    context, logger_api_ref, config_api_ref
                )
                
                # Register in global registry
                modules_registry[mod_name] = instance
                
                # Start the module
                await instance.start(context)
                
                # Dispatch module started hook
                await self.hooks.dispatch(SystemHook.ON_MODULE_STARTED, instance)
                
                # Update available provides
                provides = mod_info.manifest.get("provides", [])
                for cap in provides:
                    available_provides[cap] = mod_name
                
                if logger_api_ref[0]:
                    logger_api_ref[0].log(
                        f"Module '{mod_name}' started in group '{group.name}'",
                        level="CORE", tag="core"
                    )
                
            except Exception as e:
                if logger_api_ref[0]:
                    logger_api_ref[0].log(
                        f"Failed to start module '{mod_name}' in group "
                        f"'{group.name}': {e}",
                        level="ERROR", tag="core"
                    )
        
        group.is_completed = True
        
        # Track in execution order for reverse shutdown
        self._execution_order.append(group)
        
        # Dispatch group complete hook
        await self.hooks.dispatch(SystemHook.ON_GROUP_COMPLETE, group.name)
        
        if logger_api_ref[0]:
            logger_api_ref[0].log(
                f"Run order group '{group.name}' completed "
                f"({len(group.modules)} modules)",
                level="CORE", tag="core"
            )
        
        return True
    
    async def execute_on_start_groups(
        self,
        modules_registry: Dict[str, IModule],
        context: ModuleContext,
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> None:
        """
        Execute all groups with run_at='on_start' (the default).
        
        This is the main bootstrap method that starts all modules
        configured for startup. Groups execute sequentially in
        configuration order.
        
        Args:
            modules_registry: Global module registry
            context: Module context
            config_api: Configuration API
            logger_api: Logger API
        """
        for group in self.groups:
            if self.run_at_registry.is_default(group.run_at):
                await self.execute_group(
                    group, modules_registry, context,
                    config_api_ref, logger_api_ref
                )
        
        # Dispatch all modules started hook
        await self.hooks.dispatch(SystemHook.ON_ALL_MODULES_STARTED)
    
    async def execute_groups_for_run_at(
        self,
        run_at: str,
        modules_registry: Dict[str, IModule],
        context: ModuleContext,
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> None:
        """
        Execute all groups with a specific run_at value.
        
        This method is typically called by auto-registered callbacks
        when the corresponding SystemHook is dispatched.
        
        Args:
            run_at: The run_at value to match
            modules_registry: Global module registry
            context: Module context
            config_api: Configuration API
            logger_api: Logger API
        """
        for group in self.groups:
            if group.run_at == run_at and not group.is_started:
                await self.execute_group(
                    group, modules_registry, context,
                    config_api_ref, logger_api_ref
                )
    
    # =========================================================================
    # Shutdown
    # =========================================================================
    
    async def shutdown_all_groups(
        self,
        modules_registry: Dict[str, IModule],
        context: ModuleContext,
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> None:
        # Use dynamic logger lookup so system_logger updates take effect
        """
        Stop all started groups in reverse execution order.
        
        This method stops modules in reverse order of group execution.
        Groups that were started last are stopped first, and groups
        that were started first are stopped last.
        
        Args:
            modules_registry: Global module registry
            context: Module context
            config_api: Configuration API
            logger_api: Logger API
        """
        if logger_api_ref[0]:
            logger_api_ref[0].log(
                "Shutting down all run order groups in reverse order...",
                level="CORE", tag="core"
            )
        
        # Iterate groups in reverse execution order
        for group in reversed(self._execution_order):
            if not group.is_started or group.is_stopped:
                continue
            
            group.is_stopped = True
            
            # Dispatch group stop hook
            await self.hooks.dispatch(SystemHook.ON_GROUP_STOP, group.name)
            
            if logger_api_ref[0]:
                logger_api_ref[0].log(
                    f"Stopping run order group: '{group.name}'",
                    level="CORE", tag="core"
                )
            
            # Stop modules in reverse order within group
            for mod_info in reversed(group.modules):
                mod_name = mod_info.manifest["name"]
                instance = modules_registry.get(mod_name)
                
                if instance:
                    try:
                        await instance.stop(context)
                        await self.hooks.dispatch(
                            SystemHook.ON_MODULE_STOPPED, instance
                        )
                        if logger_api_ref[0]:
                            logger_api_ref[0].log(
                                f"Module '{mod_name}' stopped "
                                f"from group '{group.name}'",
                                level="CORE", tag="core"
                            )
                    except Exception as e:
                        if logger_api_ref[0]:
                            logger_api_ref[0].log(
                                f"Error stopping module '{mod_name}': {e}",
                                level="ERROR", tag="core"
                            )
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _get_unique_run_at_values(self) -> Set[str]:
        """
        Get all unique run_at values from parsed groups.
        
        Returns:
            Set of unique run_at strings
        """
        return {group.run_at for group in self.groups}
    
    def _get_available_provides(
        self,
        modules_registry: Dict[str, IModule]
    ) -> Dict[str, str]:
        """
        Build provides map from already-loaded modules.
        
        Args:
            modules_registry: Global module registry
            
        Returns:
            Dict mapping capability name to provider module name
        """
        provides_map = {}
        for module in modules_registry.values():
            for cap in module.provides:
                provides_map[cap] = module.name
        return provides_map
    
    def _sort_by_dependencies(
        self,
        modules: List[ModuleInfo],
        config_api_ref: List[CoreConfigAPI],
        logger_api_ref: List[CoreLoggerAPI]
    ) -> List[ModuleInfo]:
        """
        Sort modules by dependencies using topological sort.
        
        This method performs a depth-first topological sort to determine
        the correct loading order based on provides/requires declarations.
        
        Args:
            modules: List of ModuleInfo to sort
            config_api: Configuration API for logging
            logger_api: Logger API for logging
            
        Returns:
            Sorted list of ModuleInfo
            
        Raises:
            DependencyResolutionError: If circular dependency is detected
        """
        # Build provides map for this group
        provides_map = {}
        for mod in modules:
            for cap in mod.manifest.get("provides", []):
                provides_map[cap] = mod.manifest["name"]
        
        # Topological sort using DFS
        visited = set()
        visiting = set()
        sorted_list = []
        
        def visit(mod_info: ModuleInfo) -> None:
            """
            Recursive visit function for topological sort.
            
            Args:
                mod_info: Module info to visit
                
            Raises:
                DependencyResolutionError: If circular dependency detected
            """
            name = mod_info.manifest["name"]
            
            if name in visiting:
                raise DependencyResolutionError(
                    f"Circular dependency detected in '{name}'"
                )
            if name in visited:
                return
            
            visiting.add(name)
            
            # Visit dependencies first
            requires = mod_info.manifest.get("requires", [])
            for req_cap in requires:
                if req_cap in provides_map:
                    dep_name = provides_map[req_cap]
                    dep_info = next(
                        (m for m in modules
                         if m.manifest["name"] == dep_name),
                        None
                    )
                    if dep_info:
                        visit(dep_info)
            
            visiting.remove(name)
            visited.add(name)
            sorted_list.append(mod_info)
        
        # Visit all modules
        for mod in modules:
            visit(mod)
        
        return sorted_list