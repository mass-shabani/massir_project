"""
Unit tests for IModule and ModuleContext interfaces.
"""
import pytest
from unittest.mock import Mock

from massir.core.interfaces import IModule, ModuleContext


class SampleModule(IModule):
    """Sample implementation of IModule for testing."""
    
    def __init__(self):
        self.load_called = False
        self.start_called = False
        self.ready_called = False
        self.stop_called = False
        self.load_context = None
        self.start_context = None
        self.ready_context = None
        self.stop_context = None
    
    async def load(self, context):
        self.load_called = True
        self.load_context = context
    
    async def start(self, context):
        self.start_called = True
        self.start_context = context
    
    async def ready(self, context):
        self.ready_called = True
        self.ready_context = context
    
    async def stop(self, context):
        self.stop_called = True
        self.stop_context = context


class MinimalModule(IModule):
    """Minimal module that doesn't override any methods."""
    name = "minimal_module"


class TestIModule:
    """Tests for IModule interface."""
    
    def test_module_has_name_attribute(self):
        """Test that module has a name attribute."""
        module = SampleModule()
        assert hasattr(module, 'name')
    
    @pytest.mark.asyncio
    async def test_module_load(self):
        """Test module load lifecycle method."""
        module = SampleModule()
        context = ModuleContext()
        
        await module.load(context)
        
        assert module.load_called is True
        assert module.load_context == context
    
    @pytest.mark.asyncio
    async def test_module_start(self):
        """Test module start lifecycle method."""
        module = SampleModule()
        context = ModuleContext()
        
        await module.start(context)
        
        assert module.start_called is True
        assert module.start_context == context
    
    @pytest.mark.asyncio
    async def test_module_ready(self):
        """Test module ready lifecycle method."""
        module = SampleModule()
        context = ModuleContext()
        
        await module.ready(context)
        
        assert module.ready_called is True
        assert module.ready_context == context
    
    @pytest.mark.asyncio
    async def test_module_stop(self):
        """Test module stop lifecycle method."""
        module = SampleModule()
        context = ModuleContext()
        
        await module.stop(context)
        
        assert module.stop_called is True
        assert module.stop_context == context
    
    @pytest.mark.asyncio
    async def test_minimal_module_all_methods_optional(self):
        """Test that all lifecycle methods are optional."""
        module = MinimalModule()
        context = ModuleContext()
        
        # All these should work without raising
        await module.load(context)
        await module.start(context)
        await module.ready(context)
        await module.stop(context)
    
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full module lifecycle in order."""
        module = SampleModule()
        context = ModuleContext()
        
        # Execute lifecycle in order
        await module.load(context)
        await module.start(context)
        await module.ready(context)
        await module.stop(context)
        
        # Verify all were called
        assert module.load_called is True
        assert module.start_called is True
        assert module.ready_called is True
        assert module.stop_called is True


class TestModuleContext:
    """Tests for ModuleContext class."""
    
    def test_init_creates_empty_services(self):
        """Test that initialization creates empty services registry."""
        context = ModuleContext()
        
        assert context.services is not None
        assert hasattr(context.services, 'get')
        assert hasattr(context.services, 'set')
    
    def test_init_creates_empty_metadata(self):
        """Test that initialization creates empty metadata dict."""
        context = ModuleContext()
        
        assert context.metadata == {}
    
    def test_set_and_get_app(self):
        """Test setting and getting app reference."""
        context = ModuleContext()
        mock_app = Mock()
        
        context.set_app(mock_app)
        
        assert context.get_app() == mock_app
    
    def test_get_app_returns_none_before_set(self):
        """Test that get_app returns None before set_app is called."""
        context = ModuleContext()
        
        assert context.get_app() is None
    
    def test_services_registry_operations(self):
        """Test that services registry works correctly."""
        context = ModuleContext()
        
        context.services.set("test_service", "test_value")
        
        assert context.services.get("test_service") == "test_value"
    
    def test_metadata_operations(self):
        """Test metadata dictionary operations."""
        context = ModuleContext()
        
        context.metadata["key1"] = "value1"
        context.metadata["key2"] = {"nested": "value"}
        
        assert context.metadata["key1"] == "value1"
        assert context.metadata["key2"]["nested"] == "value"
    
    def test_context_isolation(self):
        """Test that context instances are isolated."""
        context1 = ModuleContext()
        context2 = ModuleContext()
        
        context1.services.set("service", "value1")
        context2.services.set("service", "value2")
        context1.metadata["key"] = "context1"
        context2.metadata["key"] = "context2"
        
        assert context1.services.get("service") == "value1"
        assert context2.services.get("service") == "value2"
        assert context1.metadata["key"] == "context1"
        assert context2.metadata["key"] == "context2"
    
    def test_multiple_services(self):
        """Test storing multiple services in context."""
        context = ModuleContext()
        
        context.services.set("service1", {"data": 1})
        context.services.set("service2", {"data": 2})
        context.services.set("service3", {"data": 3})
        
        assert context.services.get("service1")["data"] == 1
        assert context.services.get("service2")["data"] == 2
        assert context.services.get("service3")["data"] == 3
