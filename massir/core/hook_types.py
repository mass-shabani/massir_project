# massir/core/hook_types.py
"""
System hook types for framework events.
"""
from enum import Enum


class SystemHook(Enum):
    """
    System hook types for framework lifecycle events.

    These hooks allow modules to react to specific events
    during the application lifecycle.
    """
    ON_SETTINGS_LOADED = "on_settings_loaded"
    """Triggered when settings are loaded."""
    ON_APP_BOOTSTRAP_START = "on_app_bootstrap_start"
    """Triggered when application bootstrap starts."""
    ON_APP_BOOTSTRAP_END = "on_app_bootstrap_end"
    """Triggered when application bootstrap completes."""
    ON_MODULE_LOADED = "on_module_loaded"
    """Triggered when a module is loaded."""
    ON_ALL_MODULES_READY = "on_all_modules_ready"
    """Triggered when all modules have started and are ready."""
    ON_ERROR = "on_error"
    """Triggered when an error occurs."""