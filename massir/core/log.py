# massir/core/log.py
"""
Logging functions and classes.
"""
import os
import datetime
from typing import List, Optional
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
    if os.name == 'nt': os.system('')
    print(banner_content)


class _FallbackConfig:
    """
    Fallback config for when main config doesn't exist.
    """
    def get_project_name(self) -> str:
        return "Massir"

    def get_system_log_template(self) -> str:
        return "[{level}]\t{message}"

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


class DefaultLogger(CoreLoggerAPI):
    """
    Default logger.
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
        Log message.

        Args:
            message: Log message
            level: Log level
            tag: Log tag
        """
        if not self._should_log(level, tag):
            return

        template = self.config.get_system_log_template()
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

        print(formatted_msg)

    def print(self, message: str, 
              level: str = "INFO", 
              tag: Optional[str] = None, 
              end: str = "\n",
              **kwargs):
        """
        Print a raw message without log metadata.

        Args:
            message: The message to print
            level: Log level (INFO, WARNING, ERROR, etc.), This is not displayed
            tag: Optional tag for filtering, This is not displayed
            end: String appended after the message (defaults to newline)
        """
        if not self._should_log(level, tag):
            return

        if not isinstance(message, str):
            message = repr(message)

        print(message, end=end)
