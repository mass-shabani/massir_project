# massir/core/log.py
"""
Logging functions and classes.
"""
import os
import datetime
from typing import List, Optional
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI


_COLOR_NAME_TO_CODE = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}


def _get_color_code(color_name: Optional[str]) -> str:
    if not color_name:
        return "37"
    return _COLOR_NAME_TO_CODE.get(color_name.lower(), "37")


def print_banner(config_api: CoreConfigAPI):
    """
    Print the project banner.

    Args:
        config_api: Configuration API
    """
    if not config_api.show_banner():
        return
    template = config_api.get_banner_template()
    project_name = config_api.get_project_name()
    project_version = config_api.get_project_version()
    project_info = config_api.get_project_info()

    banner_content = template.format(
        project_name=project_name,
        project_version=project_version,
        project_info=project_info
    )
    color_name = config_api.get_banner_color()
    if os.name == 'nt': os.system('')
    color_start = f'\033[{_get_color_code(color_name)}m'
    reset_code = '\033[0m'
    print(f"{color_start}{banner_content}{reset_code}")


def log_internal(config_api: CoreConfigAPI, logger_api: CoreLoggerAPI, message: str, level: str = "INFO", tag: str = "core"):
    """
    Print internal core messages.

    Args:
        config_api: Configuration API
        logger_api: Logger API
        message: Log message
        level: Log level (INFO, WARNING, ERROR, DEBUG, etc.)
        tag: Tag for filtering
    """
    if logger_api is None:
        # Fallback to print if logger_api doesn't exist
        print(f"[{level}][{tag}] {message}")
        return
    logger_api.log(message, level=level, tag=tag)


# --- Helper classes for logging ---

class _FallbackLogger:
    """
    Temporary logger for when main logger doesn't exist.
    This class is used when DefaultLogger is created with config_api=None.
    """
    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None, **kwargs):
        level_prefix = f"[{level}]" if level else ""
        tag_prefix = f" [{tag}]" if tag else ""
        print(f"{level_prefix}{tag_prefix} {message}")

    def print(self, message: str, *, color: Optional[str] = None, bg_color: Optional[str] = None, bold: bool = False,
              underline: bool = False, italic: bool = False, dim: bool = False, blink: bool = False,
              inverse: bool = False, prefix: Optional[str] = None, suffix: Optional[str] = None,
              styles: Optional[List[str]] = None, end: str = "\n"):
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
            output = "".join(codes) + output + "\033[0m"

        print(output, end=end)


class _FallbackConfig:
    """
    Fallback config for when main config doesn't exist.
    """
    def get_project_name(self) -> str:
        return "Massir"

    def get_system_log_template(self) -> str:
        return "[{level}]\t{message}"

    def get_log_color(self) -> str:
        return "bright_cyan"

    def is_debug(self) -> bool:
        return True

    def show_logs(self) -> bool:
        return True

    def get_hide_log_levels(self) -> list:
        return []

    def get_hide_log_tags(self) -> list:
        return []

    def show_banner(self) -> bool:
        return True

    def get_banner_template(self) -> str:
        return "{project_name}\n"

    def get_banner_color(self) -> str:
        return "yellow"

    def get_print_color(self) -> str:
        return "white"


class DefaultLogger(CoreLoggerAPI):
    """
    Simple default logger.
    """
    def __init__(self, config_api: CoreConfigAPI):
        """
        Initialize default logger.

        Args:
            config_api: Configuration API
        """
        self.config = config_api
        if self.config is None:
            self.config = _FallbackConfig()

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

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None, **kwargs):
        """
        Log message with color support.

        Args:
            message: Log message
            level: Log level
            tag: Log tag
            **kwargs: Additional keyword arguments (e.g., color)
        """
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

        template = self.config.get_system_log_template()
        color_name = kwargs.get("color") or self.config.get_log_color()
        color_code = _get_color_code(color_name)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        format_kwargs = {
            "project_name": self.config.get_project_name(),
            "level": level,
            "message": message,
            "tag": tag or "",
            "timestamp": timestamp
        }

        class _SafeFormatDict(dict):
            def __missing__(self, key):
                return ""

        formatted_msg = template.format_map(_SafeFormatDict(format_kwargs))

        color_code_start = f'\033[{color_code}m'
        reset_code = '\033[0m'

        print(f"{color_code_start}{formatted_msg}{reset_code}")

    def print(self, message: str, 
              level: str = "INFO", 
              tag: Optional[str] = None, 
              end: str = "\n",
              color: Optional[str] = None, 
              **kwargs):
        """
        Print a raw message without log metadata.

        Args:
            message: The message to print
            level: Log level (INFO, WARNING, ERROR, etc.), This is not displayed
            tag: Optional tag for filtering, This is not displayed
            end: String appended after the message (defaults to newline)
            color: Foreground ANSI color code or color name
            **kwargs: Additional keyword arguments
        """
        if not self._should_log(level, tag):
            return

        if not isinstance(message, str):
            message = repr(message)

        output = f"{message}"

        if os.name == 'nt':
            os.system('')

        resolved_color = color or self.config.get_print_color()
        color_code = _get_color_code(resolved_color)
        if color_code:
            output = f"\033[{color_code}m" + output + "\033[0m"

        print(output, end=end)
