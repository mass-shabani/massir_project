# massir/core/api.py
"""
Core interfaces and services.
"""
from massir.core.registry import ModuleRegistry
from massir.core.log import DefaultLogger
from massir.core.settings_manager import SettingsManager
from massir.core.path import Path
import os
from typing import Optional


def initialize_core_services(
    registry: ModuleRegistry,
    initial_settings: Optional[dict] = None,
    settings_path: str = "__dir__",
    app_dir: Optional[str] = None
):
    """
    Create and register core services.

    Args:
        registry: Module registry
        initial_settings: Code settings (highest priority)
        settings_path: Path to JSON settings file
        app_dir: Path to user application directory

    Returns:
        Tuple of (logger_api, config_api, path_manager)
    """
    # Create Path object
    path_manager = Path(app_dir)

    # Resolve settings file path
    if settings_path == "__cwd__":
        full_settings_path = path_manager.resolve("app") / "app_settings.json"
    elif settings_path == "__dir__":
        # Check directly for app_settings.json in app_dir
        app_dir_path = path_manager.resolve("app")
        settings_in_app = app_dir_path / "app_settings.json"
        if settings_in_app.exists():
            full_settings_path = settings_in_app
        else:
            full_settings_path = app_dir_path / "app_settings.json"
    elif not os.path.isabs(settings_path):
        # Relative path - based on app_dir
        full_settings_path = path_manager.resolve("app") / settings_path
    else:
        full_settings_path = settings_path

    # First create DefaultLogger with default config
    # This logger is used for logging errors during settings loading
    logger_api = DefaultLogger(None)  # None = use fallback

    # Register logger in SettingsManager for use in class
    SettingsManager.set_logger(logger_api)

    # Now create SettingsManager (if JSON error, it will be logged with logger)
    config_api = SettingsManager(str(full_settings_path), initial_settings=initial_settings)

    # Update logger with correct config (since config is now loaded)
    logger_api.config = config_api

    # Register services
    registry.set("core_config", config_api)
    registry.set("core_logger", logger_api)
    registry.set("core_path", path_manager)

    return logger_api, config_api, path_manager
