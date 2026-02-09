# massir/core/config.py
"""
Re-export of configuration classes.

All classes have been moved to settings_manager.py.
This file is maintained for compatibility with previous code.
"""
from massir.core.settings_manager import (
    SettingsManager,
    DefaultLogger,
)
from massir.core.settings_default import (
    DefaultConfig,
    DEFAULT_SETTINGS,
    get_default_settings,
)

__all__ = [
    'SettingsManager',
    'DefaultLogger',
    'DefaultConfig',
    'DEFAULT_SETTINGS',
    'get_default_settings',
]
