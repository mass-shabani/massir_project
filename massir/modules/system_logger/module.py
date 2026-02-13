import datetime
import os
import re
from typing import Optional
from massir.core.interfaces import IModule
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.hook_types import SystemHook


# ANSI Color Codes - Available for all modules
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    
    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


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

    def _format_http_request(self, message: str) -> str:
        """
        Format HTTP request log messages with enhanced styling.
        
        Args:
            message: The log message
            
        Returns:
            Formatted message with colors
        """
        # Pattern for HTTP access logs: IP:PORT - "METHOD PATH PROTOCOL" STATUS
        http_pattern = r'^(\d+\.\d+\.\d+\.\d+):(\d+)\s+-\s+"(\w+)\s+([^\s]+)\s+([^"]+)"\s+(\d+)'
        match = re.match(http_pattern, message)
        
        if match:
            ip, port, method, path, protocol, status = match.groups()
            status_code = int(status)
            
            # Determine status color
            if status_code >= 500:
                status_color = Colors.BRIGHT_RED
            elif status_code >= 400:
                status_color = Colors.BRIGHT_YELLOW
            elif status_code >= 300:
                status_color = Colors.BRIGHT_BLUE
            else:
                status_color = Colors.BRIGHT_GREEN
            
            # Format with method highlighting
            method_colors = {
                'GET': Colors.BRIGHT_GREEN,
                'POST': Colors.BRIGHT_BLUE,
                'PUT': Colors.BRIGHT_YELLOW,
                'DELETE': Colors.BRIGHT_RED,
                'PATCH': Colors.BRIGHT_MAGENTA,
            }
            method_color = method_colors.get(method, Colors.BRIGHT_WHITE)
            
            return f"{method_color}{method}{Colors.RESET} {path} {status_color}{status}{Colors.RESET}"
        
        return message

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None,
            level_color: Optional[str] = None, text_color: Optional[str] = None, bracket_color: Optional[str] = None):
        """
        Log a message with color support.

        Args:
            message: The message to log
            level: Log level
            tag: Log tag for filtering
            level_color: Custom color for level tag (use Colors class)
            text_color: Custom color for message text (use Colors class)
            bracket_color: Custom color for timestamp brackets (use Colors class)
        """
        # Check filtering
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

        # Default colors
        _bracket_color = bracket_color if bracket_color else Colors.BRIGHT_GREEN
        _text_color = text_color if text_color else Colors.BRIGHT_WHITE
        _level_color = level_color if level_color else Colors.BRIGHT_GREEN

        # Set level colors based on level (if not provided)
        if level_color is None:
            level_colors = {
                "ERROR": Colors.BRIGHT_RED,
                "WARNING": Colors.BRIGHT_YELLOW,
                "INFO": Colors.BRIGHT_GREEN,
                "DEBUG": Colors.BRIGHT_BLACK,
                "CORE": Colors.BRIGHT_CYAN,
            }
            _level_color = level_colors.get(level, Colors.BRIGHT_GREEN)

        if level == "ERROR" and text_color is None:
            _text_color = Colors.BRIGHT_RED

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        str_time = f"{_bracket_color}[{timestamp}]{Colors.RESET} "
        str_header = f"{_level_color}[{level}]{Colors.RESET} "
        
        # Format HTTP requests specially (only if no custom colors)
        if text_color is None and tag in ["http", "server"]:
            formatted_message = self._format_http_request(message)
        else:
            formatted_message = message
        
        # Add tag if present
        if tag:
            str_message = f"{_text_color}[{tag}]{Colors.RESET} {formatted_message}{Colors.RESET}"
        else:
            str_message = f"{_text_color}{formatted_message}{Colors.RESET}"

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
        
        # Register Colors class for use by other modules
        context.services.set("log_colors", Colors)

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

    async def ready(self, context):
        """
        Called when all modules have started and are ready.

        Args:
            context: Module context
        """
        logger = context.services.get("core_logger")
        if logger:
            logger.log("System Logger Module is ready. All modules have started.", tag="System")

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