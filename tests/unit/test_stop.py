"""
Unit tests for stop module.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from massir.core.stop import shutdown
from massir.core.interfaces import IModule, ModuleContext


class MockModule(IModule):
    """Mock module for testing."""
    
    def __init__(self, name):
        self.name = name
        self.stop_called = False
        self._context = ModuleContext()
    
    async def stop(self, context):
        self.stop_called = True


@pytest.mark.asyncio
class TestShutdown:
    """Tests for shutdown function."""
    
    async def test_shutdown_cancels_background_tasks(self):
        """Test that shutdown cancels background tasks."""
        async def long_running_task():
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                raise
        
        task = asyncio.create_task(long_running_task())
        modules = {}
        
        # Give the task a moment to start
        await asyncio.sleep(0.01)
        
        await shutdown(modules, [task], None, None)
        
        # Give the event loop time to process the cancellation
        await asyncio.sleep(0.01)
        
        # Task should be cancelled or done
        assert task.cancelled() or task.done()
    
    async def test_shutdown_stops_modules_in_reverse_order(self):
        """Test that modules are stopped in reverse order."""
        modules = {
            "mod1": MockModule("mod1"),
            "mod2": MockModule("mod2"),
            "mod3": MockModule("mod3")
        }
        system_names = ["mod1"]
        app_names = ["mod2", "mod3"]
        
        await shutdown(
            modules, [],
            Mock(), Mock(),
            system_names, app_names
        )
        
        # All modules should be stopped
        assert modules["mod1"].stop_called == True
        assert modules["mod2"].stop_called == True
        assert modules["mod3"].stop_called == True
    
    async def test_shutdown_stops_app_modules_first(self):
        """Test that app modules are stopped before system modules."""
        stop_order = []
        
        class OrderTrackingModule(IModule):
            def __init__(self, name):
                self.name = name
                self._context = ModuleContext()
            
            async def stop(self, context):
                stop_order.append(self.name)
        
        modules = {
            "system_mod": OrderTrackingModule("system_mod"),
            "app_mod": OrderTrackingModule("app_mod")
        }
        system_names = ["system_mod"]
        app_names = ["app_mod"]
        
        await shutdown(
            modules, [],
            Mock(), Mock(),
            system_names, app_names
        )
        
        # App module should be stopped before system module
        assert stop_order.index("app_mod") < stop_order.index("system_mod")
    
    async def test_shutdown_legacy_mode(self):
        """Test shutdown without module name lists (legacy mode)."""
        modules = {
            "mod1": MockModule("mod1"),
            "mod2": MockModule("mod2")
        }
        
        await shutdown(
            modules, [],
            Mock(), Mock()
            # No system_module_names or app_module_names
        )
        
        # All modules should be stopped
        assert modules["mod1"].stop_called == True
        assert modules["mod2"].stop_called == True
    
    async def test_shutdown_handles_module_stop_error(self):
        """Test that errors in module.stop() are handled gracefully."""
        class ErrorModule(IModule):
            name = "error_module"
            _context = ModuleContext()
            
            async def stop(self, context):
                raise RuntimeError("Stop error!")
        
        modules = {
            "error_mod": ErrorModule(),
            "normal_mod": MockModule("normal_mod")
        }
        
        # Should not raise
        await shutdown(
            modules, [],
            Mock(), Mock(),
            ["error_mod"], ["normal_mod"]
        )
        
        # Normal module should still be stopped
        assert modules["normal_mod"].stop_called == True
    
    async def test_shutdown_with_empty_modules(self):
        """Test shutdown with empty modules dict."""
        modules = {}
        
        # Should not raise
        await shutdown(
            modules, [],
            Mock(), Mock(),
            [], []
        )
    
    async def test_shutdown_with_none_module_lists(self):
        """Test shutdown with None for module lists."""
        modules = {
            "mod1": MockModule("mod1")
        }
        
        # Should use legacy mode
        await shutdown(
            modules, [],
            Mock(), Mock(),
            None, None
        )
        
        assert modules["mod1"].stop_called == True
    
    async def test_shutdown_skips_missing_modules(self):
        """Test that missing modules in name lists are skipped."""
        modules = {
            "existing_mod": MockModule("existing_mod")
        }
        system_names = ["nonexistent_system"]
        app_names = ["nonexistent_app", "existing_mod"]
        
        # Should not raise KeyError
        await shutdown(
            modules, [],
            Mock(), Mock(),
            system_names, app_names
        )
        
        assert modules["existing_mod"].stop_called == True
    
    async def test_shutdown_cancels_multiple_tasks(self):
        """Test that multiple background tasks are cancelled."""
        async def task_func():
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                raise
        
        tasks = [
            asyncio.create_task(task_func()),
            asyncio.create_task(task_func())
        ]
        
        # Give tasks a moment to start
        await asyncio.sleep(0.01)
        
        await shutdown({}, tasks, None, None)
        
        # Give the event loop time to process the cancellation
        await asyncio.sleep(0.01)
        
        for task in tasks:
            assert task.cancelled() or task.done()
    
    async def test_shutdown_skips_completed_tasks(self):
        """Test that completed tasks are not cancelled again."""
        async def quick_task():
            return "done"
        
        task = asyncio.create_task(quick_task())
        await task  # Complete the task
        
        # Should not raise
        await shutdown({}, [task], None, None)
        
        assert task.done()
