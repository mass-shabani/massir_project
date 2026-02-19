# massir/core/settings_default.py
"""
Default settings values.
"""
from massir.core.core_apis import CoreConfigAPI

# Default settings values
DEFAULT_SETTINGS = {
    "modules": [
        {"path": "{massir_dir}/modules", "names": []}
    ],
    "system": {
        "auto_shutdown": False,
        "auto_shutdown_delay": 0.0
    },
    "logs": {
        "show_logs": True,
        "show_banner": True,
        "hide_log_levels": [],
        "hide_log_tags": [],
        "debug_mode": True
    },
    "information": {
        "project_name": "Massir Framework",
        "project_version": "0.0.5 alpha",
        "project_info": "Modular Application Architecture"
    },
    "template": {
        "project_banner_template": "\n\t{project_name}\n\t{project_version}\n\t{project_info}\n",
        "system_log_template": "[{level}]\t{message}",
        "banner_color_code": "33",
        "system_log_color_code": "96"
    },
}


class DefaultConfig(CoreConfigAPI):
    """
    Simple default config class.
    This class is used when the main config does not exist.
    """
    def get(self, key: str) -> None:
        """Always returns None."""
        return None


def get_default_settings() -> dict:
    """
    Get default settings values.

    Returns:
        Dictionary of default values
    """
    return DEFAULT_SETTINGS.copy()


def create_default_config() -> CoreConfigAPI:
    """
    Create an instance of DefaultConfig.

    Returns:
        DefaultConfig instance
    """
    return DefaultConfig()
