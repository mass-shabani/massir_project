"""
Unit tests for SettingsManager.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from massir.core.settings_manager import SettingsManager
from massir.core.settings_default import DEFAULT_SETTINGS, get_default_settings, DefaultConfig


class TestSettingsManager:
    """Tests for SettingsManager class."""
    
    def test_init_with_defaults(self, tmp_path):
        """Test initialization with default settings."""
        # Use a completely isolated path with a unique subdirectory
        isolated_dir = tmp_path / "test_isolated_unique_12345"
        isolated_dir.mkdir(parents=True, exist_ok=True)
        settings_path = str(isolated_dir / "nonexistent_settings.json")
        
        # Clear any class-level state
        SettingsManager._class_logger = None
        
        manager = SettingsManager(settings_path)
        
        # Should have default settings - check that settings exist
        assert manager.get("system") is not None
        # Check that required keys exist
        assert manager.get("modules") is not None
        assert manager.get("logs") is not None
        assert manager.get("information") is not None
    
    def test_init_with_initial_settings(self, tmp_path):
        """Test initialization with initial settings."""
        settings_path = str(tmp_path / "nonexistent.json")
        initial = {
            "system": {
                "auto_shutdown": True
            }
        }
        
        manager = SettingsManager(settings_path, initial_settings=initial)
        
        assert manager.get("system.auto_shutdown") == True
    
    def test_init_with_json_file(self, tmp_path):
        """Test initialization with JSON settings file."""
        settings_file = tmp_path / "settings.json"
        settings_data = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 1.0
            }
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)
        
        manager = SettingsManager(str(settings_file))
        
        assert manager.get("system.auto_shutdown") == True
        assert manager.get("system.auto_shutdown_delay") == 1.0
    
    def test_initial_settings_override_json(self, tmp_path):
        """Test that initial settings override JSON settings."""
        settings_file = tmp_path / "settings.json"
        settings_data = {
            "system": {
                "auto_shutdown": False
            }
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)
        
        initial = {
            "system": {
                "auto_shutdown": True
            }
        }
        
        manager = SettingsManager(str(settings_file), initial_settings=initial)
        
        assert manager.get("system.auto_shutdown") == True
    
    def test_get_nested_key(self, tmp_path):
        """Test get with nested keys."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("level1.level2.level3", "value")
        
        assert manager.get("level1.level2.level3") == "value"
    
    def test_get_nonexistent_key_returns_default(self, tmp_path):
        """Test get returns default for nonexistent key."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        result = manager.get("nonexistent.key", default="default_value")
        
        assert result == "default_value"
    
    def test_get_nonexistent_key_returns_none(self, tmp_path):
        """Test get returns None for nonexistent key without default."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        result = manager.get("nonexistent.key")
        
        assert result is None
    
    def test_set_simple_key(self, tmp_path):
        """Test set with simple key."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        manager.set("simple_key", "simple_value")
        
        assert manager.get("simple_key") == "simple_value"
    
    def test_set_nested_key(self, tmp_path):
        """Test set with nested key."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        manager.set("nested.key.value", "nested_value")
        
        assert manager.get("nested.key.value") == "nested_value"
    
    def test_set_creates_intermediate_dicts(self, tmp_path):
        """Test set creates intermediate dictionaries."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        manager.set("a.b.c.d", "deep_value")
        
        assert manager.get("a.b.c.d") == "deep_value"
        assert isinstance(manager.get("a.b"), dict)
    
    def test_update_settings_merges_dicts(self, tmp_path):
        """Test update_settings merges dictionaries."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        manager.update_settings({
            "system": {
                "auto_shutdown": True,
                "new_key": "new_value"
            }
        })
        
        assert manager.get("system.auto_shutdown") == True
        assert manager.get("system.new_key") == "new_value"
    
    def test_update_settings_overwrites_non_dicts(self, tmp_path):
        """Test update_settings overwrites non-dict values."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        manager.update_settings({
            "system": "string_value"
        })
        
        assert manager.get("system") == "string_value"


class TestSettingsManagerModules:
    """Tests for module-related settings methods."""
    
    def test_get_modules_dir_default(self, tmp_path):
        """Test get_modules_dir returns default."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        result = manager.get_modules_dir()
        
        assert isinstance(result, list)
    
    def test_get_modules_dir_string(self, tmp_path):
        """Test get_modules_dir with string value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("system.modules_dir", "./custom/path")
        
        result = manager.get_modules_dir()
        
        assert result == ["./custom/path"]
    
    def test_get_modules_dir_list(self, tmp_path):
        """Test get_modules_dir with list value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("system.modules_dir", ["./path1", "./path2"])
        
        result = manager.get_modules_dir()
        
        assert result == ["./path1", "./path2"]
    
    def test_get_modules_config_default(self, tmp_path):
        """Test get_modules_config returns default."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        result = manager.get_modules_config()
        
        assert isinstance(result, list)
    
    def test_get_modules_config_for_type_systems(self, tmp_path):
        """Test get_modules_config_for_type filters systems."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("modules", [
            {"type": "systems", "path": "./sys"},
            {"type": "applications", "path": "./app"},
            {"type": "all", "path": "./all"}
        ])
        
        result = manager.get_modules_config_for_type("systems")
        
        assert len(result) == 2  # systems + all
        paths = [r["path"] for r in result]
        assert "./sys" in paths
        assert "./all" in paths
    
    def test_get_modules_config_for_type_applications(self, tmp_path):
        """Test get_modules_config_for_type filters applications."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("modules", [
            {"type": "systems", "path": "./sys"},
            {"type": "applications", "path": "./app"},
            {"type": "all", "path": "./all"}
        ])
        
        result = manager.get_modules_config_for_type("applications")
        
        assert len(result) == 2  # applications + all
        paths = [r["path"] for r in result]
        assert "./app" in paths
        assert "./all" in paths


class TestSettingsManagerLogging:
    """Tests for logging-related settings methods."""
    
    def test_show_logs_default(self, tmp_path):
        """Test show_logs default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.show_logs() == True
    
    def test_show_logs_custom(self, tmp_path):
        """Test show_logs custom value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("logs.show_logs", False)
        
        assert manager.show_logs() == False
    
    def test_show_banner_default(self, tmp_path):
        """Test show_banner default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.show_banner() == True
    
    def test_get_hide_log_levels_default(self, tmp_path):
        """Test get_hide_log_levels default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.get_hide_log_levels() == []
    
    def test_get_hide_log_levels_custom(self, tmp_path):
        """Test get_hide_log_levels custom value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("logs.hide_log_levels", ["DEBUG", "INFO"])
        
        assert manager.get_hide_log_levels() == ["DEBUG", "INFO"]
    
    def test_get_hide_log_tags_default(self, tmp_path):
        """Test get_hide_log_tags default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.get_hide_log_tags() == []
    
    def test_is_debug_default(self, tmp_path):
        """Test is_debug default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.is_debug() == True


class TestSettingsManagerProjectInfo:
    """Tests for project information methods."""
    
    def test_get_project_name_default(self, tmp_path):
        """Test get_project_name default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.get_project_name() == "Massir Framework"
    
    def test_get_project_name_custom(self, tmp_path):
        """Test get_project_name custom value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        manager.set("information.project_name", "My Project")
        
        assert manager.get_project_name() == "My Project"
    
    def test_get_project_version_default(self, tmp_path):
        """Test get_project_version default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.get_project_version() == "0.0.5 alpha"
    
    def test_get_project_info_default(self, tmp_path):
        """Test get_project_info default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.get_project_info() == "Modular Application Architecture"


class TestSettingsManagerTemplates:
    """Tests for template methods."""
    
    def test_get_banner_template_default(self, tmp_path):
        """Test get_banner_template default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert "{project_name}" in manager.get_banner_template()
    
    def test_get_system_log_template_default(self, tmp_path):
        """Test get_system_log_template default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert "{level}" in manager.get_system_log_template()
    
    def test_get_banner_color_code_default(self, tmp_path):
        """Test get_banner_color_code default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.get_banner_color_code() == "33"
    
    def test_get_system_log_color_code_default(self, tmp_path):
        """Test get_system_log_color_code default value."""
        manager = SettingsManager(str(tmp_path / "settings.json"))
        
        assert manager.get_system_log_color_code() == "96"


class TestSettingsDefault:
    """Tests for settings_default module."""
    
    def test_default_settings_is_dict(self):
        """Test DEFAULT_SETTINGS is a dictionary."""
        assert isinstance(DEFAULT_SETTINGS, dict)
    
    def test_default_settings_has_required_keys(self):
        """Test DEFAULT_SETTINGS has required keys."""
        assert "modules" in DEFAULT_SETTINGS
        assert "system" in DEFAULT_SETTINGS
        assert "logs" in DEFAULT_SETTINGS
        assert "information" in DEFAULT_SETTINGS
        assert "template" in DEFAULT_SETTINGS
    
    def test_get_default_settings_returns_copy(self):
        """Test get_default_settings returns a copy."""
        settings1 = get_default_settings()
        settings2 = get_default_settings()
        
        assert settings1 == settings2
        assert settings1 is not settings2
    
    def test_default_config_get_returns_none(self):
        """Test DefaultConfig.get returns None."""
        config = DefaultConfig()
        
        assert config.get("any_key") is None


class TestSettingsManagerErrorHandling:
    """Tests for error handling in SettingsManager."""
    
    def test_invalid_json_logs_error(self, tmp_path):
        """Test that invalid JSON is handled gracefully."""
        # Use a unique subdirectory to avoid any interference
        unique_dir = tmp_path / "test_invalid_json_unique_67890"
        unique_dir.mkdir(parents=True, exist_ok=True)
        settings_file = unique_dir / "invalid.json"
        with open(settings_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")
        
        # Clear any class-level state
        SettingsManager._class_logger = None
        
        # Should not raise, should use defaults
        manager = SettingsManager(str(settings_file))
        
        # Check that settings exist (the invalid file was skipped)
        assert manager.get("system") is not None
        # Check that modules config exists (from defaults)
        assert manager.get("modules") is not None
    
    def test_set_logger_class_method(self, tmp_path):
        """Test set_logger class method."""
        mock_logger = Mock()
        
        SettingsManager.set_logger(mock_logger)
        
        assert SettingsManager._class_logger == mock_logger
