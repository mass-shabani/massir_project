# massir/core/log.py
"""
Logging functions and classes.
"""
import os
from typing import Optional
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI


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
    color_code = config_api.get_banner_color_code()
    if os.name == 'nt': os.system('')
    color_start = f'\033[{color_code}m'
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


class _FallbackConfig:
    """
    Fallback config for when main config doesn't exist.
    """
    def get_project_name(self) -> str:
        return "Massir"

    def get_system_log_template(self) -> str:
        return "[{level}]\t{message}"

    def get_system_log_color_code(self) -> str:
        return "96"

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

    def get_banner_color_code(self) -> str:
        return "33"


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
            **kwargs: Additional keyword arguments (e.g., level_color, text_color)
        """
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

        template = self.config.get_system_log_template()
        color_code = self.config.get_system_log_color_code()

        formatted_msg = template.format(
            project_name=self.config.get_project_name(),
            level=level,
            message=message
        )

        color_code_start = f'\033[{color_code}m'
        reset_code = '\033[0m'

        print(f"{color_code_start}{formatted_msg}{reset_code}")
