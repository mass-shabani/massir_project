"""
System Logger Module for Massir Framework.

This module provides an advanced logging service that replaces the
default logger with enhanced capabilities including:
- Color-coded output with ANSI escape codes
- Timestamp formatting
- Configurable filtering by level and tag
- HTTP request log formatting
- Raw print with advanced styling options

The module registers two services:
- core_logger: AdvancedLogger instance (replaces DefaultLogger)
- log_colors: Colors class (for use by other modules)
"""
from massir.core.interfaces import IModule, ModuleContext
from massir.core.hook_types import SystemHook
from massir.modules.system_logger.core import Colors, SystemLoggerDefaults
from massir.modules.system_logger.core.logger import AdvancedLogger


class SystemLoggerModule(IModule):
    """
    System logger module.
    
    This module provides an advanced logging service to the framework,
    replacing the default logger with enhanced capabilities.
    """

    async def start(self, context: 'ModuleContext') -> None:
        """
        Start the system logger module.
        
        Args:
            context: Module context providing access to services and app
        """
        self.context = context
        config = context.services.get("core_config")
        
        if config:
            config.apply_module_defaults(SystemLoggerDefaults().to_dict())
        
        # Create and register the advanced logger
        my_logger = AdvancedLogger(config)
        context.services.set("core_logger", my_logger)
        
        # Register Colors class for use by other modules
        context.services.set("log_colors", Colors)
        
        # Update App's logger reference so core uses the new logger
        app = context.get_app()
        if app and hasattr(app, '_logger_api_ref'):
            app._logger_api_ref[0] = my_logger
        
        # Register lifecycle hooks
        app.register_hook(SystemHook.ON_MODULE_STARTED, self._on_module_started)
        app.register_hook(SystemHook.ON_SETTINGS_LOADED, self._on_settings_loaded)
        
        # Log activation
        my_logger.log("System Logger Module Active.", tag="sys_logger")
    
    async def stop(self, context: 'ModuleContext') -> None:
        """
        Stop the system logger module.
        
        Args:
            context: Module context
        """
        logger = context.services.get("core_logger")
        if logger:
            logger.log("System Logger Module stopping.", tag="sys_logger")
    
    def _on_settings_loaded(self):
        """Handle settings loaded event."""
        pass
    
    def _on_module_started(self, module_instance):
        """
        Handle module started event.
        
        Args:
            module_instance: The module instance that just started
        """
        pass
