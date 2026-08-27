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

import datetime
import os
import re
from typing import List, Optional

from massir.core.interfaces import IModule, ModuleContext
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.hook_types import SystemHook


class Colors:
    """
    ANSI color codes for terminal output.
    
    This class provides a comprehensive set of ANSI escape codes for:
    - Standard foreground colors (8 colors)
    - Bright foreground colors (8 colors)
    - Standard background colors (8 colors)
    - Bright background colors (8 colors)
    
    All modules can access these colors via:
        context.services.get("log_colors")
    """
    
    # Reset all formatting
    RESET = '\033[0m'
    
    # =========================================================================
    # Standard Foreground Colors (8 colors)
    # =========================================================================
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # =========================================================================
    # Bright Foreground Colors (8 colors)
    # =========================================================================
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # =========================================================================
    # Standard Background Colors (8 colors)
    # =========================================================================
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # =========================================================================
    # Bright Background Colors (8 colors)
    # =========================================================================
    BG_BRIGHT_BLACK = '\033[100m'
    BG_BRIGHT_RED = '\033[101m'
    BG_BRIGHT_GREEN = '\033[102m'
    BG_BRIGHT_YELLOW = '\033[103m'
    BG_BRIGHT_BLUE = '\033[104m'
    BG_BRIGHT_MAGENTA = '\033[105m'
    BG_BRIGHT_CYAN = '\033[106m'
    BG_BRIGHT_WHITE = '\033[107m'


class AdvancedLogger(CoreLoggerAPI):
    """
    Advanced logger with color support and filtering.
    
    This logger provides enhanced logging capabilities including
    color-coded output, timestamp, and configurable filtering.
    
    The logger reads configuration from CoreConfigAPI:
    - logs.show_logs: Enable/disable logging
    - logs.hide_log_levels: List of levels to hide
    - logs.hide_log_tags: List of tags to hide
    - logs.debug_mode: Show debug-level messages
    - template.system_log_template: Log message format template
    - template.system_log_color_code: ANSI color code for logs
    """
    
    def __init__(self, config_api: CoreConfigAPI):
        """
        Initialize advanced logger.
        
        Args:
            config_api: Configuration API for reading log settings
        """
        self.config = config_api
        if self.config is None:
            self.config = self._get_fallback()
    
    def _get_fallback(self):
        """
        Get fallback configuration for when config_api is None.
        
        Returns:
            Fallback config object with default values
        """
        class F:
            def get_project_name(self): return "Unknown"
            def get_system_log_template(self): return "{timestamp} | {level}:\t{tag} | {message}"
            def get_system_log_color_code(self): return "92"
            def is_debug(self): return True
            def show_logs(self): return True
            def get_hide_log_levels(self): return []
            def get_hide_log_tags(self): return []
        return F()
    
    def _should_log(self, level: str, tag: Optional[str] = None) -> bool:
        """
        Check if message should be logged based on config.
        
        Filtering rules:
        1. If show_logs is False, nothing is logged
        2. If tag is in hide_log_tags, message is skipped
        3. If level is in hide_log_levels, message is skipped
        4. Critical levels (ERROR, WARNING, etc.) only show in debug mode
        
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
        
        Parses HTTP access log format: IP:PORT - "METHOD PATH PROTOCOL" STATUS
        and applies color coding based on HTTP method and status code.
        
        Args:
            message: The log message containing HTTP request info
            
        Returns:
            Formatted message with ANSI colors
        """
        # Pattern for HTTP access logs: IP:PORT - "METHOD PATH PROTOCOL" STATUS
        http_pattern = r'^(\d+\.\d+\.\d+\.\d+):(\d+)\s+-\s+"(\w+)\s+([^\s]+)\s+([^"]+)"\s+(\d+)'
        match = re.match(http_pattern, message)
        if match:
            ip, port, method, path, protocol, status = match.groups()
            status_code = int(status)
            
            # Determine status color based on code range
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
            level_color: Optional[str] = None, timestamp_color: Optional[str] = None,
            tag_color: Optional[str] = None, text_color: Optional[str] = None,
            timestamp_bg_color: Optional[str] = None,
            level_bg_color: Optional[str] = None,
            tag_bg_color: Optional[str] = None,
            text_bg_color: Optional[str] = None,
            bold: bool = False, underline: bool = False, italic: bool = False,
            dim: bool = False, blink: bool = False, inverse: bool = False,
            prefix: Optional[str] = None, suffix: Optional[str] = None,
            styles: Optional[List[str]] = None):
        """
        Log a message with advanced color and style support.

        Output format: [timestamp] [level] [tag] message
        Each section can have independent foreground and background colors,
        plus text styles like bold, italic, etc.

        Args:
            message: The message to log
            level: Log level (INFO, WARNING, ERROR, DEBUG, CORE)
            tag: Log tag for filtering
            level_color: Custom color for level tag (use Colors class)
            timestamp_color: Custom color for timestamp brackets (use Colors class)
            tag_color: Custom color for tag brackets (use Colors class)
            text_color: Custom color for message text (use Colors class)
            timestamp_bg_color: Background color for timestamp (use Colors class)
            level_bg_color: Background color for level tag (use Colors class)
            tag_bg_color: Background color for tag brackets (use Colors class)
            text_bg_color: Background color for message text (use Colors class)
            bold: Render bold text
            underline: Render underlined text
            italic: Render italic text
            dim: Render dim text
            blink: Enable blinking text
            inverse: Swap foreground and background colors
            prefix: Text prepended to the message
            suffix: Text appended to the message
            styles: Additional raw ANSI codes to apply
        """
        # Check filtering
        if not self._should_log(level, tag):
            return

        # Enable ANSI on Windows
        if os.name == 'nt':
            os.system('')

        # Build style codes
        style_codes = []
        if bold:
            style_codes.append("\033[1m")
        if italic:
            style_codes.append("\033[3m")
        if dim:
            style_codes.append("\033[2m")
        if underline:
            style_codes.append("\033[4m")
        if blink:
            style_codes.append("\033[5m")
        if inverse:
            style_codes.append("\033[7m")
        if styles:
            style_codes.extend(styles)
        style_prefix = "".join(style_codes)
        style_suffix = Colors.RESET if style_codes else ""

        # Default colors
        _timestamp_color = timestamp_color if timestamp_color else Colors.BRIGHT_GREEN
        _level_color = level_color if level_color else Colors.BRIGHT_GREEN
        _tag_color = tag_color if tag_color else Colors.BRIGHT_WHITE
        _text_color = text_color if text_color else Colors.BRIGHT_WHITE

        # Default backgrounds
        _timestamp_bg = timestamp_bg_color if timestamp_bg_color else ""
        _level_bg = level_bg_color if level_bg_color else ""
        _tag_bg = tag_bg_color if tag_bg_color else ""
        _text_bg = text_bg_color if text_bg_color else ""

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

        # Use red text for errors if no custom text_color
        if level == "ERROR" and text_color is None:
            _text_color = Colors.BRIGHT_RED

        # Build output string
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Timestamp part
        str_time = f"{_timestamp_color}{_timestamp_bg}[{timestamp}]{Colors.RESET}"

        # Level part
        str_header = f"{_level_color}{_level_bg}[{level}]{Colors.RESET}"

        # Format HTTP requests specially (only if no custom text_color)
        if text_color is None and tag in ["http", "server"]:
            formatted_message = self._format_http_request(message)
        else:
            formatted_message = message

        # Build message part with tag and text
        if tag:
            str_message = (
                f"{_tag_color}{_tag_bg}[{tag}]{Colors.RESET} "
                f"{style_prefix}{_text_color}{_text_bg}{formatted_message}{style_suffix}{Colors.RESET}"
            )
        else:
            str_message = (
                f"{style_prefix}{_text_color}{_text_bg}{formatted_message}{style_suffix}{Colors.RESET}"
            )

        # Add prefix and suffix
        if prefix:
            str_message = f"{prefix}{str_message}"
        if suffix:
            str_message = f"{str_message}{suffix}"

        print(f"{str_time} {str_header}\t{str_message}")

    def print(self,
              message: str,
              level: str = "INFO",
              tag: Optional[str] = None,
              end: str = "\n",
              color: Optional[str] = None,
              bg_color: Optional[str] = None,
              bold: bool = False,
              underline: bool = False,
              italic: bool = False,
              dim: bool = False,
              blink: bool = False,
              inverse: bool = False,
              prefix: Optional[str] = None,
              suffix: Optional[str] = None,
              styles: Optional[List[str]] = None):
        """
        Print raw output with advanced styling options but without log headers.
        
        This method provides fine-grained control over terminal output
        with ANSI styling. Unlike log(), it does not add timestamp or
        level headers.
        
        Args:
            message: The text to print
            level: Log level (for filtering only, not displayed)
            tag: Optional tag for filtering (not displayed)
            end: String appended after the message (defaults to newline)
            color: Foreground ANSI color
            bg_color: Background ANSI color
            bold: Render bold text
            underline: Render underlined text
            italic: Render italic text
            dim: Render dim text
            blink: Enable blinking text
            inverse: Swap foreground/background colors
            prefix: Text prepended to the message
            suffix: Text appended to the message
            styles: Additional raw ANSI codes to apply
        """
        if not self._should_log(level, tag):
            return
        if not isinstance(message, str):
            message = repr(message)
        if prefix is None:
            prefix = ""
        if suffix is None:
            suffix = ""
        output = f"{prefix}{message}{suffix}"
        
        codes: list[str] = []
        if color:
            codes.append(color)
        if bg_color:
            codes.append(bg_color)
        if bold:
            codes.append("\033[1m")
        if italic:
            codes.append("\033[3m")
        if dim:
            codes.append("\033[2m")
        if underline:
            codes.append("\033[4m")
        if blink:
            codes.append("\033[5m")
        if inverse:
            codes.append("\033[7m")
        if styles:
            codes.extend(styles)
        
        if os.name == 'nt':
            os.system('')
        if codes:
            output = "".join(codes) + output + Colors.RESET
        print(output, end=end)


class SystemLoggerModule(IModule):
    """
    System logger module.
    
    This module provides an advanced logging service to the framework,
    replacing the default logger with enhanced capabilities.
    
    Services registered:
    - core_logger: AdvancedLogger instance
    - log_colors: Colors class for terminal styling
    
    Hooks registered:
    - ON_MODULE_STARTED: Track when other modules start
    - ON_SETTINGS_LOADED: React to settings reload (restart scenarios)
    """
    
    async def start(self, context: 'ModuleContext') -> None:
        """
        Start the system logger module.
        
        This method:
        1. Creates the AdvancedLogger instance with current config
        2. Registers it as the core_logger service (replaces DefaultLogger)
        3. Registers the Colors class for use by other modules
        4. Updates the App's logger reference so core uses the new logger
        5. Registers lifecycle hooks
        6. Logs activation confirmation
        
        Args:
            context: Module context providing access to services and app
        """
        self.context = context
        config = context.services.get("core_config")
        
        # Create and register the advanced logger
        my_logger = AdvancedLogger(config)
        context.services.set("core_logger", my_logger)
        
        # Register Colors class for use by other modules
        context.services.set("log_colors", Colors)
        
        # Update App's logger reference so core uses the new logger
        # In the new system, inject_system_apis is no longer called by
        # the loader, so the module must update the reference directly
        app = context.get_app()
        if app and hasattr(app, '_logger_api_ref'):
            app._logger_api_ref[0] = my_logger
        
        # Register lifecycle hooks
        # Note: ON_SETTINGS_LOADED fires before this module starts on
        # initial bootstrap, so this hook only catches reloads on restart
        app.register_hook(SystemHook.ON_MODULE_STARTED, self._on_module_started)
        app.register_hook(SystemHook.ON_SETTINGS_LOADED, self._on_settings_loaded)
        
        # Log activation
        my_logger.log("System Logger Module Active.", tag="System")
    
    async def stop(self, context: 'ModuleContext') -> None:
        """
        Stop the system logger module.
        
        The logger service remains registered until shutdown completes
        so other modules can still log during their stop() phase.
        
        Args:
            context: Module context
        """
        logger = context.services.get("core_logger")
        if logger:
            logger.log("System Logger Module stopping.", tag="System")
    
    def _on_settings_loaded(self):
        """
        Handle settings loaded event.
        
        This callback fires when settings are loaded. On initial bootstrap,
        this fires before the module has started, so it only catches
        settings reloads during restart scenarios.
        """
        pass
    
    def _on_module_started(self, module_instance):
        """
        Handle module started event.
        
        Called when another module's start() method completes.
        Can be used for logging or dependency tracking.
        
        Args:
            module_instance: The module instance that just started
        """
        pass