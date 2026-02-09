import asyncio
from typing import List, Dict, Optional
# Import from massir namespace
from massir.core.interfaces import IModule
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.log import log_internal


async def shutdown(modules: Dict[str, IModule], background_tasks: List[asyncio.Task],
                  config_api: CoreConfigAPI, logger_api: CoreLoggerAPI,
                  system_module_names: Optional[List[str]] = None,
                  app_module_names: Optional[List[str]] = None):
    """
    Execute the shutdown sequence for the application.

    This function cancels background tasks and stops all modules in the
    correct order (application modules first, then system modules, both in
    reverse order of their loading).

    Args:
        modules: Dictionary of all loaded modules
        background_tasks: List of background tasks to cancel
        config_api: Configuration API
        logger_api: Logger API
        system_module_names: List of system module names (optional)
        app_module_names: List of application module names (optional)
    """
    log_internal(config_api, logger_api, "🛑 Shutting down framework...", level="CORE")

    # Cancel background tasks
    for task in background_tasks:
        if not task.done():
            task.cancel()

    # If module name lists are provided, use the correct order
    if system_module_names is not None and app_module_names is not None:
        # Stop application modules in reverse order
        log_internal(config_api, logger_api, "Stopping Application Modules...", level="CORE", tag="core")
        for mod_name in reversed(app_module_names):
            if mod_name in modules:
                try:
                    await modules[mod_name].stop(modules[mod_name]._context)
                    log_internal(config_api, logger_api, f"Application module '{mod_name}' stopped", level="CORE", tag="core")
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error stopping application module '{mod_name}': {e}", level="ERROR", tag="core")

        # Stop system modules in reverse order
        log_internal(config_api, logger_api, "Stopping System Modules...", level="CORE", tag="core")
        for mod_name in reversed(system_module_names):
            if mod_name in modules:
                try:
                    await modules[mod_name].stop(modules[mod_name]._context)
                    log_internal(config_api, logger_api, f"System module '{mod_name}' stopped", level="CORE", tag="core")
                except Exception as e:
                    log_internal(config_api, logger_api, f"Error stopping system module '{mod_name}': {e}", level="ERROR", tag="core")
    else:
        # Legacy mode: stop all modules in reverse order
        log_internal(config_api, logger_api, "Stopping Modules (legacy mode)...", level="CORE", tag="core")
        for instance in reversed(list(modules.values())):
            try:
                await instance.stop(instance._context)
            except Exception as e:
                log_internal(config_api, logger_api, f"Error stopping module {instance.name}: {e}", level="ERROR", tag="core")