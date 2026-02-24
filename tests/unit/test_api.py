"""
Unit tests for api module.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from massir.core.api import initialize_core_services
from massir.core.registry import ModuleRegistry


class TestInitializeCoreServices:
    """Tests for initialize_core_services function."""
    
    def test_returns_tuple(self, tmp_path):
        """Test that function returns a tuple of three items."""
        registry = ModuleRegistry()
        
        result = initialize_core_services(
            registry,
            initial_settings={"system": {"auto_shutdown": True}},
            settings_path="__dir__",
            app_dir=str(tmp_path)
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3
    
    def test_registers_core_services(self, tmp_path):
        """Test that core services are registered."""
        registry = ModuleRegistry()
        
        initialize_core_services(
            registry,
            initial_settings={"system": {"auto_shutdown": True}},
            settings_path="__dir__",
            app_dir=str(tmp_path)
        )
        
        assert registry.has("core_config")
        assert registry.has("core_logger")
        assert registry.has("core_path")
    
    def test_with_initial_settings(self, tmp_path):
        """Test with initial_settings parameter."""
        registry = ModuleRegistry()
        initial = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.5
            },
            "custom": {
                "value": "test"
            }
        }
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            initial_settings=initial,
            settings_path="__dir__",
            app_dir=str(tmp_path)
        )
        
        assert config_api.get("system.auto_shutdown") == True
        assert config_api.get("custom.value") == "test"
    
    def test_with_settings_file(self, tmp_path):
        """Test with settings from JSON file."""
        settings_file = tmp_path / "app_settings.json"
        settings_data = {
            "system": {
                "auto_shutdown": False
            }
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)
        
        registry = ModuleRegistry()
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            settings_path=str(settings_file),
            app_dir=str(tmp_path)
        )
        
        assert config_api.get("system.auto_shutdown") == False
    
    def test_settings_path_cwd(self, tmp_path):
        """Test with settings_path='__cwd__'."""
        registry = ModuleRegistry()
        
        # Should not raise even if file doesn't exist
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            initial_settings={"system": {}},
            settings_path="__cwd__",
            app_dir=str(tmp_path)
        )
        
        assert config_api is not None
    
    def test_settings_path_dir(self, tmp_path):
        """Test with settings_path='__dir__'."""
        registry = ModuleRegistry()
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            initial_settings={"system": {}},
            settings_path="__dir__",
            app_dir=str(tmp_path)
        )
        
        assert config_api is not None
    
    def test_settings_path_relative(self, tmp_path):
        """Test with relative settings path."""
        registry = ModuleRegistry()
        
        # Relative path should be resolved relative to app_dir
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            initial_settings={"system": {}},
            settings_path="config/settings.json",
            app_dir=str(tmp_path)
        )
        
        assert config_api is not None
    
    def test_settings_path_absolute(self, tmp_path):
        """Test with absolute settings path."""
        settings_file = tmp_path / "custom_settings.json"
        settings_data = {"system": {}}
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)
        
        registry = ModuleRegistry()
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            settings_path=str(settings_file),
            app_dir=str(tmp_path)
        )
        
        assert config_api is not None
    
    def test_path_manager_has_correct_app_dir(self, tmp_path):
        """Test that path_manager has correct app_dir."""
        registry = ModuleRegistry()
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            initial_settings={"system": {}},
            settings_path="__dir__",
            app_dir=str(tmp_path)
        )
        
        assert path_manager.app == tmp_path.resolve()
    
    def test_initial_settings_override_file(self, tmp_path):
        """Test that initial_settings override file settings."""
        settings_file = tmp_path / "app_settings.json"
        settings_data = {
            "system": {
                "auto_shutdown": False
            }
        }
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f)
        
        registry = ModuleRegistry()
        initial = {
            "system": {
                "auto_shutdown": True  # Should override file
            }
        }
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            initial_settings=initial,
            settings_path=str(settings_file),
            app_dir=str(tmp_path)
        )
        
        assert config_api.get("system.auto_shutdown") == True
    
    def test_without_app_dir(self):
        """Test without app_dir parameter (uses cwd)."""
        registry = ModuleRegistry()
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            initial_settings={"system": {}},
            settings_path="__dir__"
        )
        
        assert path_manager is not None
        assert config_api is not None
    
    def test_without_initial_settings(self, tmp_path):
        """Test without initial_settings parameter."""
        registry = ModuleRegistry()
        
        logger_api, config_api, path_manager = initialize_core_services(
            registry,
            settings_path="__dir__",
            app_dir=str(tmp_path)
        )
        
        # Should use default settings
        assert config_api is not None
