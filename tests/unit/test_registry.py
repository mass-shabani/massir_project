"""
Unit tests for ModuleRegistry.
"""
import pytest
from massir.core.registry import ModuleRegistry


class TestModuleRegistry:
    """Tests for ModuleRegistry class."""
    
    def test_init_creates_empty_services_dict(self):
        """Test that initialization creates an empty services dictionary."""
        registry = ModuleRegistry()
        
        assert registry._services == {}
    
    def test_set_and_get_service(self):
        """Test basic set and get operations."""
        registry = ModuleRegistry()
        
        registry.set("test_service", {"key": "value"})
        result = registry.get("test_service")
        
        assert result == {"key": "value"}
    
    def test_set_with_string_key(self):
        """Test setting a service with a string key."""
        registry = ModuleRegistry()
        
        registry.set("my_service", "service_value")
        
        assert "my_service" in registry._services
        assert registry._services["my_service"] == "service_value"
    
    def test_get_nonexistent_service_returns_none(self):
        """Test that getting a non-existent service returns None."""
        registry = ModuleRegistry()
        
        result = registry.get("nonexistent")
        
        assert result is None
    
    def test_has_service_returns_true_for_existing(self):
        """Test has() returns True for existing service."""
        registry = ModuleRegistry()
        registry.set("service1", "value")
        
        assert registry.has("service1") is True
    
    def test_has_service_returns_false_for_nonexistent(self):
        """Test has() returns False for non-existent service."""
        registry = ModuleRegistry()
        
        assert registry.has("service2") is False
    
    def test_remove_existing_service(self):
        """Test removing an existing service."""
        registry = ModuleRegistry()
        registry.set("service1", "value")
        
        registry.remove("service1")
        
        assert registry.has("service1") is False
        assert registry.get("service1") is None
    
    def test_remove_nonexistent_service_does_not_raise(self):
        """Test that removing a non-existent service doesn't raise an error."""
        registry = ModuleRegistry()
        
        # Should not raise any exception
        registry.remove("nonexistent")
    
    def test_overwrite_service(self):
        """Test that setting a service with an existing key overwrites it."""
        registry = ModuleRegistry()
        
        registry.set("service1", "value1")
        registry.set("service1", "value2")
        
        assert registry.get("service1") == "value2"
    
    def test_set_multiple_services(self):
        """Test setting multiple services."""
        registry = ModuleRegistry()
        
        registry.set("service1", "value1")
        registry.set("service2", "value2")
        registry.set("service3", "value3")
        
        assert registry.get("service1") == "value1"
        assert registry.get("service2") == "value2"
        assert registry.get("service3") == "value3"
    
    def test_set_with_none_value(self):
        """Test setting a service with None value."""
        registry = ModuleRegistry()
        
        registry.set("null_service", None)
        
        assert registry.has("null_service") is True
        assert registry.get("null_service") is None
    
    def test_set_with_complex_object(self):
        """Test setting a service with a complex object."""
        registry = ModuleRegistry()
        
        class ComplexService:
            def __init__(self):
                self.data = {"nested": {"values": [1, 2, 3]}}
        
        service = ComplexService()
        registry.set("complex", service)
        
        result = registry.get("complex")
        assert isinstance(result, ComplexService)
        assert result.data["nested"]["values"] == [1, 2, 3]
    
    def test_set_with_callable(self):
        """Test setting a service with a callable."""
        registry = ModuleRegistry()
        
        def my_callable(x, y):
            return x + y
        
        registry.set("callable_service", my_callable)
        
        result = registry.get("callable_service")
        assert callable(result)
        assert result(2, 3) == 5
    
    def test_services_isolation_between_instances(self):
        """Test that registry instances are isolated."""
        registry1 = ModuleRegistry()
        registry2 = ModuleRegistry()
        
        registry1.set("service", "value1")
        registry2.set("service", "value2")
        
        assert registry1.get("service") == "value1"
        assert registry2.get("service") == "value2"
