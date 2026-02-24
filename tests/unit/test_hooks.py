"""
Unit tests for HooksManager.
"""
import pytest
from massir.core.hooks import HooksManager
from massir.core.hook_types import SystemHook


class TestHooksManager:
    """Tests for HooksManager class."""
    
    def test_init_creates_empty_hooks_dict(self):
        """Test that initialization creates an empty hooks dictionary."""
        manager = HooksManager()
        
        assert manager._hooks == {}
    
    def test_register_hook_creates_list(self):
        """Test that registering a hook creates a list for that hook type."""
        manager = HooksManager()
        
        def callback():
            pass
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback)
        
        assert SystemHook.ON_APP_BOOTSTRAP_START in manager._hooks
        assert len(manager._hooks[SystemHook.ON_APP_BOOTSTRAP_START]) == 1
    
    def test_register_multiple_callbacks_same_hook(self):
        """Test registering multiple callbacks for the same hook."""
        manager = HooksManager()
        
        def callback1():
            pass
        
        def callback2():
            pass
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback1)
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback2)
        
        assert len(manager._hooks[SystemHook.ON_APP_BOOTSTRAP_START]) == 2
    
    def test_register_different_hook_types(self):
        """Test registering callbacks for different hook types."""
        manager = HooksManager()
        
        def callback1():
            pass
        
        def callback2():
            pass
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback1)
        manager.register(SystemHook.ON_MODULE_LOADED, callback2)
        
        assert SystemHook.ON_APP_BOOTSTRAP_START in manager._hooks
        assert SystemHook.ON_MODULE_LOADED in manager._hooks
    
    @pytest.mark.asyncio
    async def test_dispatch_hook_to_sync_callback(self):
        """Test dispatching hook to synchronous callbacks."""
        manager = HooksManager()
        results = []
        
        def callback(value):
            results.append(value)
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback)
        await manager.dispatch(SystemHook.ON_APP_BOOTSTRAP_START, "test_value")
        
        assert "test_value" in results
    
    @pytest.mark.asyncio
    async def test_dispatch_hook_to_async_callback(self):
        """Test dispatching hook to async callbacks."""
        manager = HooksManager()
        results = []
        
        async def async_callback(value):
            results.append(value)
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, async_callback)
        await manager.dispatch(SystemHook.ON_APP_BOOTSTRAP_START, "async_value")
        
        assert "async_value" in results
    
    @pytest.mark.asyncio
    async def test_dispatch_to_multiple_callbacks(self):
        """Test dispatching to multiple callbacks."""
        manager = HooksManager()
        results = []
        
        def callback1(value):
            results.append(f"callback1_{value}")
        
        def callback2(value):
            results.append(f"callback2_{value}")
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback1)
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback2)
        
        await manager.dispatch(SystemHook.ON_APP_BOOTSTRAP_START, "test")
        
        assert "callback1_test" in results
        assert "callback2_test" in results
    
    @pytest.mark.asyncio
    async def test_dispatch_to_nonexistent_hook_does_not_raise(self):
        """Test that dispatching to a hook with no callbacks doesn't raise."""
        manager = HooksManager()
        
        # Should not raise any exception
        await manager.dispatch(SystemHook.ON_SETTINGS_LOADED, "value")
    
    @pytest.mark.asyncio
    async def test_dispatch_with_multiple_arguments(self):
        """Test dispatching with multiple arguments."""
        manager = HooksManager()
        results = []
        
        def callback(arg1, arg2, kwarg1=None):
            results.append((arg1, arg2, kwarg1))
        
        manager.register(SystemHook.ON_MODULE_LOADED, callback)
        await manager.dispatch(SystemHook.ON_MODULE_LOADED, "a", "b", kwarg1="c")
        
        assert ("a", "b", "c") in results
    
    @pytest.mark.asyncio
    async def test_callback_exception_is_caught(self):
        """Test that exceptions in callbacks are caught and don't break dispatch."""
        manager = HooksManager()
        results = []
        
        def failing_callback():
            raise ValueError("Test error")
        
        def working_callback():
            results.append("worked")
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, failing_callback)
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, working_callback)
        
        # Should not raise, and working_callback should still be called
        await manager.dispatch(SystemHook.ON_APP_BOOTSTRAP_START)
        
        assert "worked" in results
    
    @pytest.mark.asyncio
    async def test_dispatch_order_preserved(self):
        """Test that callbacks are called in registration order."""
        manager = HooksManager()
        results = []
        
        def callback1():
            results.append(1)
        
        def callback2():
            results.append(2)
        
        def callback3():
            results.append(3)
        
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback1)
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback2)
        manager.register(SystemHook.ON_APP_BOOTSTRAP_START, callback3)
        
        await manager.dispatch(SystemHook.ON_APP_BOOTSTRAP_START)
        
        assert results == [1, 2, 3]


class TestSystemHook:
    """Tests for SystemHook enum."""
    
    def test_hook_values(self):
        """Test that SystemHook has expected values."""
        assert SystemHook.ON_SETTINGS_LOADED.value == "on_settings_loaded"
        assert SystemHook.ON_APP_BOOTSTRAP_START.value == "on_app_bootstrap_start"
        assert SystemHook.ON_APP_BOOTSTRAP_END.value == "on_app_bootstrap_end"
        assert SystemHook.ON_MODULE_LOADED.value == "on_module_loaded"
        assert SystemHook.ON_ALL_MODULES_READY.value == "on_all_modules_ready"
        assert SystemHook.ON_SHUTDOWN_REQUEST.value == "on_shutdown_request"
        assert SystemHook.ON_RESTART_REQUEST.value == "on_restart_request"
    
    def test_hook_count(self):
        """Test that SystemHook has expected number of hooks."""
        hooks = list(SystemHook)
        assert len(hooks) == 8  # ON_ERROR was added
