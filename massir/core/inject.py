import asyncio
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.interfaces import IModule
from massir.core.log import DefaultLogger, log_internal
from massir.core.registry import ModuleRegistry


async def inject_system_apis(module_instance: IModule, registry: ModuleRegistry,
                              logger_ref: list[CoreLoggerAPI], config_ref: list[CoreConfigAPI]):
    """
    Check and inject system APIs if provided by module.

    This function checks if the module provides logger or config services
    and injects them into the core system.

    Args:
        module_instance: The module instance
        registry: The module registry
        logger_ref: Reference to the logger API (list for mutability)
        config_ref: Reference to the config API (list for mutability)
    """
    # Inject logger
    logger_service = registry.get("core_logger")
    if logger_service and isinstance(logger_service, CoreLoggerAPI):
        if logger_service != logger_ref[0]:
            log_internal(config_ref[0], logger_ref[0], f"🔄 Overriding Core Logger with module: {module_instance.name}", level="CORE", tag="core_init")
            logger_ref[0] = logger_service
            registry.set("core_logger", logger_service)

    # Inject config
    config_service = registry.get("core_config")
    if config_service and isinstance(config_service, CoreConfigAPI):
        if config_service != config_ref[0]:
            log_internal(config_ref[0], logger_ref[0], f"🔄 Overriding Core Config with module: {module_instance.name}", level="CORE", tag="core_init")
            config_ref[0] = config_service
            registry.set("core_config", config_service)

            if isinstance(logger_ref[0], DefaultLogger):
                logger_ref[0].config = config_ref[0]