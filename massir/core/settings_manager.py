# massir/core/settings_manager.py
"""
Project settings management.
"""
import json
import os
from pathlib import Path
from typing import Optional

from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI
from massir.core.settings_default import get_default_settings
from massir.core.log import DefaultLogger, _FallbackConfig, log_internal


class SettingsManager(CoreConfigAPI):
    """
    Project settings management.

    Priority order:
    1. Module defaults (registered by modules, lowest priority)
    2. Core defaults (default values)
    3. Settings from JSON (file)
    4. User Code (initial_settings) - highest priority
    """

    _module_defaults_registry: dict = {}
    _class_logger: Optional[CoreLoggerAPI] = None

    @classmethod
    def set_logger(cls, logger_api: CoreLoggerAPI):
        """Set logger for use in class."""
        cls._class_logger = logger_api

    @classmethod
    def register_module_defaults(cls, defaults: dict):
        """Register module defaults to be merged as base layer."""
        cls._module_defaults_registry.update(defaults)

    @classmethod
    def _deep_merge(cls, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _log(self, message: str, level: str = "ERROR"):
        """Log with class logger or temporary logger."""
        if SettingsManager._class_logger:
            SettingsManager._class_logger.log(message, level=level, tag="config")
        else:
            log_internal(None, None, message, level=level, tag="config")

    def __init__(self, settings_path: str = "app_settings.json", initial_settings: Optional[dict] = None, path_manager=None):
        # 1. Module defaults (lowest priority)
        module_defaults = SettingsManager._module_defaults_registry.copy()

        # 2. Core defaults (override module defaults for overlapping keys)
        core_defaults = get_default_settings()
        self._settings = SettingsManager._deep_merge(module_defaults, core_defaults)

        # 3. Read from JSON
        self._load_settings(settings_path)

        # 4. Substitute path placeholders if path_manager is available
        if path_manager:
            self._substitute_path_placeholders(path_manager)

        # 5. Code settings (highest priority)
        if initial_settings:
            self.update_settings(initial_settings)

    def _load_settings(self, path: str):
        """Read settings from JSON file with error handling."""
        full_path = Path(path)
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    self.update_settings(json_data)
            except json.JSONDecodeError as e:
                self._log(f"Invalid JSON in {full_path}: {e}")
                self._log("Skipping settings file. Using default settings.")
            except Exception as e:
                self._log(f"Failed to load settings from {full_path}: {e}")
                self._log("Skipping settings file. Using default settings.")

    def apply_module_defaults(self, defaults: dict):
        """Apply module defaults only for keys not already present."""
        for key, value in defaults.items():
            if self.get(key) is None:
                self.set(key, value)

    def _substitute_path_placeholders(self, path_manager):
        """
        Substitute {app_dir} and {massir_dir} placeholders in all string settings values.
        
        Args:
            path_manager: Path manager instance
        """
        app_dir = str(path_manager.app)
        massir_dir = str(path_manager.massir)
        
        def substitute_in_value(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    value[k] = substitute_in_value(v)
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    value[i] = substitute_in_value(v)
            elif isinstance(value, str):
                value = value.replace("{app_dir}", app_dir)
                value = value.replace("{massir_dir}", massir_dir)
            return value
        
        self._settings = substitute_in_value(self._settings)

    def get(self, key: str, default=None):
        """Get value with support for nested keys."""
        keys = key.split('.')
        value = self._settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value):
        """Set value."""
        keys = key.split('.')
        current = self._settings
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def update_settings(self, new_settings: dict):
        """Merge new settings with current settings."""
        for key, value in new_settings.items():
            if isinstance(value, dict) and isinstance(self._settings.get(key), dict):
                self._settings[key].update(value)
            else:
                self._settings[key] = value

    # --- System settings ---
    def get_modules_dir(self) -> list:
        """Get module paths (legacy format - for compatibility)."""
        val = self.get("system.modules_dir")
        if isinstance(val, str):
            return [val]
        return val if isinstance(val, list) else ["./massir/modules"]

    def get_modules_config(self) -> list:
        """
        Get module settings.

        Returns:
            List of module settings (including path, type, names)
        """
        val = self.get("modules", [])
        if not isinstance(val, list):
            return []
        return val

    def get_modules_config_for_type(self, config_type: str) -> list:
        """
        Get module settings for a specific type.

        Args:
            config_type: Load phase type (systems, applications, all)

        Returns:
            List of module settings suitable for this phase
        """
        all_config = self.get_modules_config()
        result = []
        for item in all_config:
            folder_type = item.get("type", "all")
            normalized = folder_type.rstrip("s") if folder_type != "all" else "all"
            target = config_type.rstrip("s")
            if folder_type == "all" or normalized == target:
                result.append(item)
        return result

    # --- Log settings ---
    def show_logs(self) -> bool:
        return self.get("logs.show_logs", True)

    def show_banner(self) -> bool:
        return self.get("logs.show_banner", True)

    def get_hide_log_levels(self) -> list:
        val = self.get("logs.hide_log_levels")
        if isinstance(val, list):
            return val
        return []

    def get_hide_log_tags(self) -> list:
        val = self.get("logs.hide_log_tags")
        if isinstance(val, list):
            return val
        return []

    def is_debug(self) -> bool:
        return self.get("logs.debug_mode", True)

    # --- Project information ---
    def get_project_name(self) -> str:
        return self.get("information.project_name", "Unknown Project")

    def get_project_version(self) -> str:
        return self.get("information.project_version", "1.0.0")

    def get_project_info(self) -> str:
        return self.get("information.project_info", "")

    # --- Templates ---
    def get_banner_template(self) -> str:
        return self.get("template.project_banner_template", "{project_name}\n")

    def get_system_log_template(self) -> str:
        return self.get("template.system_log_template", "[{level}]\t{message}")

    def get_banner_color(self) -> str:
        return self.get("template.banner_color", "yellow")

    def get_log_color(self) -> str:
        return self.get("template.log_color", "bright_cyan")

    def get_print_color(self) -> str:
        return self.get("template.print_color", "white")

