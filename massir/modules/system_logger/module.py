import datetime
import os
from typing import Optional
from massir.core.interfaces import IModule
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.hook_types import SystemHook


class AdvancedLogger(CoreLoggerAPI):
    """
    Advanced logger with color support and filtering.

    This logger provides enhanced logging capabilities including
    color-coded output, timestamp, and configurable filtering.
    """

    def __init__(self, config_api: CoreConfigAPI):
        """
        Initialize advanced logger.

        Args:
            config_api: Configuration API
        """
        self.config = config_api
        if self.config is None:
            self.config = self._get_fallback()

    def _get_fallback(self):
        """Get fallback configuration."""
        class F:
            def get_project_name(self): return "Unknown"
            def get_system_log_template(self): return "[{level}]\t{message}"
            def get_system_log_color_code(self): return "92"
            def is_debug(self): return True
            def show_logs(self): return True
            def get_hide_log_levels(self): return []
            def get_hide_log_tags(self): return []
        return F()

    def _should_log(self, level: str, tag: Optional[str] = None) -> bool:
        """
        Check if message should be logged based on config.

        Args:
            level: Log level
            tag: Log tag

        Returns:
            True if should log, False otherwise
        """
        config = self.config

        if not config.show_logs():
            return False

        if tag:
            hidden_tags = config.get_hide_log_tags()
            if isinstance(hidden_tags, list) and tag in hidden_tags:
                return False

        hidden_levels = config.get_hide_log_levels()
        if isinstance(hidden_levels, list):
            if level in hidden_levels:
                return False

        critical_levels = ["ERROR", "WARNING", "EXCEPTION", "CRITICAL"]
        if level in critical_levels and not config.is_debug():
            return False

        return True

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None,
            level_color: Optional[str] = None, text_color: Optional[str] = None, bracket_color: Optional[str] = None):
        """
        Log a message with color support.

        Args:
            message: The message to log
            level: Log level
            tag: Log tag for filtering
            level_color: Custom color for level tag
            text_color: Custom color for message text
            bracket_color: Custom color for timestamp brackets
        """
        # Check filtering
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

        # Default colors
        _bracket_color = bracket_color if bracket_color else '\033[92m'
        _text_color = text_color if text_color else '\033[97m'
        _level_color = level_color if level_color else '\033[92m'

        RESET = '\033[0m'
        COLOR_RED = '\033[91m'

        if level == "ERROR" and level_color is None:
            _level_color = COLOR_RED
            _text_color = COLOR_RED

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        str_time = f"{_bracket_color}[{timestamp}]{RESET} "
        str_header = f"{_level_color}[{level}]{RESET} "

        if level == "ERROR":
            str_message = f"{_text_color}{message}{RESET}"
        else:
            str_message = f"{_text_color}{message}{RESET}"

        print(f"{str_time}{str_header}\t{str_message}")


class SystemLoggerModule(IModule):
    """
    System logger module.

    This module provides an advanced logging service to the framework,
    replacing the default logger with enhanced capabilities.
    """

    async def load(self, context):
        """
        Load the system logger module.

        Args:
            context: Module context
        """
        self.context = context
        config = context.services.get("core_config")

        my_logger = AdvancedLogger(config)
        context.services.set("core_logger", my_logger)

        app = context.get_app()
        app.register_hook(SystemHook.ON_MODULE_LOADED, self._on_module_loaded)
        app.register_hook(SystemHook.ON_SETTINGS_LOADED, self._on_settings_loaded)

    async def start(self, context):
        """
        Start the system logger module.

        Args:
            context: Module context
        """
        # Important fix: update module config reference
        # Since code settings (initial_settings) may have been applied after load
        # or config may have been replaced in registry.
        logger = context.services.get("core_logger")
        if logger and hasattr(logger, 'config'):
            logger.config = context.services.get("core_config")

        logger.log("System Logger Module Active.", tag="System")

    async def stop(self, context):
        """
        Stop the system logger module.

        Args:
            context: Module context
        """
        pass

    def _on_settings_loaded(self):
        """Handle settings loaded event."""
        pass

    def _on_module_loaded(self, module_instance):
        """
        Handle module loaded event.

        Args:
            module_instance: The loaded module instance
        """
        logger = self.context.services.get("core_logger")
        logger.log(f"Detected loaded module: {module_instance.name}", level="CORE", tag="Detailed")