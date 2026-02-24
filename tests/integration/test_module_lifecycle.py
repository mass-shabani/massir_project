"""
Integration tests for module lifecycle.

Note: Tests that require dynamic module loading from temporary directories
are skipped because the modules aren't in Python's import path.
These scenarios are better tested with the existing Example applications.
"""
import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from massir.core.app import App
from massir.core.interfaces import IModule, ModuleContext
from massir.core.hook_types import SystemHook


class TestAppShutdown:
    """Tests for application shutdown."""
    
    @pytest.mark.asyncio
    async def test_request_shutdown(self, tmp_path):
        """Test programmatic shutdown request."""
        app_dir = tmp_path / "request_shutdown_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": False
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        # Request shutdown after a short delay
        import asyncio
        
        async def delayed_shutdown():
            await asyncio.sleep(0.2)
            app.request_shutdown()
        
        asyncio.create_task(delayed_shutdown())
        
        await app.run()
        
        # App should have shut down
        assert app._stop_event.is_set()


class TestErrorHandling:
    """Tests for error handling during module lifecycle."""
    
    @pytest.mark.asyncio
    async def test_app_initialization_with_settings(self, tmp_path):
        """Test that app initializes correctly with settings."""
        app_dir = tmp_path / "test_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.1
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        # Should have context and services
        assert app.context is not None
        assert app.context.services is not None
        
        # Run should complete without error
        await app.run()
    
    @pytest.mark.asyncio
    async def test_app_with_empty_modules(self, tmp_path):
        """Test app with no modules loads and shuts down correctly."""
        app_dir = tmp_path / "empty_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.1
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        await app.run()
        
        # No modules should be loaded
        assert len(app.modules) == 0


class TestHooks:
    """Tests for hook system integration."""
    
    @pytest.mark.asyncio
    async def test_hooks_are_dispatched(self, tmp_path):
        """Test that system hooks are dispatched during lifecycle."""
        app_dir = tmp_path / "hooks_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.1
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        # Track hook calls
        hook_calls = []
        
        def track_hook(hook_name):
            def callback():
                hook_calls.append(hook_name)
            return callback
        
        app.register_hook(SystemHook.ON_SETTINGS_LOADED, track_hook("settings_loaded"))
        app.register_hook(SystemHook.ON_APP_BOOTSTRAP_START, track_hook("bootstrap_start"))
        app.register_hook(SystemHook.ON_APP_BOOTSTRAP_END, track_hook("bootstrap_end"))
        
        await app.run()
        
        # Verify hooks were called
        assert "settings_loaded" in hook_calls
        assert "bootstrap_start" in hook_calls
        assert "bootstrap_end" in hook_calls
    
    @pytest.mark.asyncio
    async def test_multiple_hooks_same_event(self, tmp_path):
        """Test multiple hooks for the same event."""
        app_dir = tmp_path / "multi_hooks_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.1
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        # Track hook calls
        call_order = []
        
        def callback1():
            call_order.append("first")
        
        def callback2():
            call_order.append("second")
        
        def callback3():
            call_order.append("third")
        
        app.register_hook(SystemHook.ON_APP_BOOTSTRAP_START, callback1)
        app.register_hook(SystemHook.ON_APP_BOOTSTRAP_START, callback2)
        app.register_hook(SystemHook.ON_APP_BOOTSTRAP_START, callback3)
        
        await app.run()
        
        # All callbacks should be called in order
        assert call_order == ["first", "second", "third"]


class TestSettingsIntegration:
    """Tests for settings integration."""
    
    @pytest.mark.asyncio
    async def test_settings_from_initial_settings(self, tmp_path):
        """Test that settings from initial_settings are accessible."""
        app_dir = tmp_path / "settings_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.1
            },
            "custom": {
                "value1": "test",
                "value2": 42
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        # Get config API
        config = app.context.services.get("core_config")
        assert config is not None
        
        # Check custom settings
        assert config.get("custom.value1") == "test"
        assert config.get("custom.value2") == 42
        
        await app.run()
    
    @pytest.mark.asyncio
    async def test_default_settings_applied(self, tmp_path):
        """Test that default settings are applied."""
        app_dir = tmp_path / "defaults_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.1
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        config = app.context.services.get("core_config")
        
        # Check default values exist
        assert config.get("system") is not None
        
        await app.run()


class TestServiceRegistry:
    """Tests for service registry integration."""
    
    @pytest.mark.asyncio
    async def test_core_services_registered(self, tmp_path):
        """Test that core services are registered."""
        app_dir = tmp_path / "services_app"
        app_dir.mkdir()
        
        settings = {
            "system": {
                "auto_shutdown": True,
                "auto_shutdown_delay": 0.1
            },
            "modules": {
                "applications": []
            }
        }
        
        app = App(
            initial_settings=settings,
            settings_path="__dir__",
            app_dir=str(app_dir)
        )
        
        # Core services should be registered
        assert app.context.services.get("core_config") is not None
        assert app.context.services.get("core_logger") is not None
        assert app.context.services.get("core_path") is not None
        
        await app.run()
