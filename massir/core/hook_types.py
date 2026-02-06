# massir/core/hook_types.py

from enum import Enum

class SystemHook(Enum):
    ON_SETTINGS_LOADED = "on_settings_loaded"
    ON_APP_BOOTSTRAP_START = "on_app_bootstrap_start"
    ON_APP_BOOTSTRAP_END = "on_app_bootstrap_end"
    ON_MODULE_LOADED = "on_module_loaded"
    ON_ERROR = "on_error"