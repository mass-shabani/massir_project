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
from massir.modules.system_logger.log_defaults import get_color_code
from massir.modules.system_logger.log_defaults import SystemLoggerDefaults


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
    - template.log_color: Default color name for logs
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
        Fallback config for when config_api is None.
        """
        class _SystemLoggerFallbackConfig:
            def get_project_name(self): return "Unknown"
            def get_system_log_template(self): return "{timestamp}--- | {level}:\t{tag} | {message}"
            def get_log_color(self): return "bright_green"
            def is_debug(self): return True
            def show_logs(self): return True
            def get_hide_log_levels(self): return []
            def get_hide_log_tags(self): return []
            def get_banner_color(self): return "yellow"
            def get_print_color(self): return "white"
        return _SystemLoggerFallbackConfig()
    
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
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

        template = self.config.get_system_log_template()
        core_default = "[{level}]\t{message}"
        module_default = "{timestamp} | {level}:\t{tag} | {message}"

        if isinstance(template, str) and template != core_default:
            format_template = template
        else:
            format_template = module_default

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        project_name = ""
        if hasattr(self.config, "get_project_name"):
            project_name = self.config.get_project_name()

        format_kwargs = {
            "project_name": project_name,
            "level": level,
            "message": message,
            "tag": tag or "",
            "timestamp": timestamp
        }

        class _SafeFormatDict(dict):
            def __missing__(self, key):
                return ""

        formatted_msg = format_template.format_map(_SafeFormatDict(format_kwargs))

        log_color = self.config.get_log_color()
        level_colors = {}
        if hasattr(self.config, "get"):
            level_colors = self.config.get("logs.level_colors", {}) or {}

        resolved_level_color = level_color or level_colors.get(level) or log_color
        resolved_timestamp_color = timestamp_color or log_color
        resolved_tag_color = tag_color or log_color
        resolved_text_color = text_color or log_color

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

        def _apply_style(text, fg_color, bg_color=None):
            fg_code = get_color_code(fg_color)
            codes = [f"\033[{fg_code}m"]
            if bg_color:
                bg_code = get_color_code(bg_color)
                codes.append(f"\033[{bg_code}m")
            codes.extend(style_codes)
            return "".join(codes) + text + "\033[0m"

        result = ""
        i = 0
        while i < len(format_template):
            if format_template[i] == "{":
                end = format_template.find("}", i)
                if end != -1:
                    placeholder = format_template[i:end+1]
                    key = placeholder[1:-1]
                    value = format_kwargs.get(key, "")

                    if key == "timestamp":
                        colored = _apply_style(value, resolved_timestamp_color, timestamp_bg_color)
                    elif key == "level":
                        colored = _apply_style(value, resolved_level_color, level_bg_color)
                    elif key == "tag":
                        colored = _apply_style(value, resolved_tag_color, tag_bg_color)
                    elif key == "message":
                        colored = _apply_style(value, resolved_text_color, text_bg_color)
                    elif key == "project_name":
                        colored = _apply_style(value, log_color)
                    else:
                        colored = value

                    result += colored
                    i = end + 1
                    continue
            result += format_template[i]
            i += 1

        if prefix:
            result = prefix + result
        if suffix:
            result = result + suffix

        print(result)

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
            color: Foreground ANSI color code or color name
            bg_color: Background ANSI color code or color name
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
        
        resolved_color = color or self.config.get_print_color()
        color_code = get_color_code(resolved_color)
        
        codes: list[str] = [f"\033[{color_code}m"]
        if bg_color:
            bg_code = get_color_code(bg_color)
            codes.append(f"\033[{bg_code}m")
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
        output = f"{prefix}{message}{suffix}"
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
        
        if config:
            config.apply_module_defaults(SystemLoggerDefaults().to_dict())
        
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
        my_logger.log("System Logger Module Active.", tag="sys_logger")
    
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
            logger.log("System Logger Module stopping.", tag="sys_logger")
    
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