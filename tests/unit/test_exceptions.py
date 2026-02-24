"""
Unit tests for framework exceptions.
"""
import pytest
from massir.core.exceptions import (
    FrameworkError,
    ModuleLoadError,
    DependencyResolutionError
)


class TestFrameworkError:
    """Tests for FrameworkError base exception."""
    
    def test_is_exception(self):
        """Test that FrameworkError is an Exception."""
        assert issubclass(FrameworkError, Exception)
    
    def test_can_be_raised(self):
        """Test that FrameworkError can be raised."""
        with pytest.raises(FrameworkError):
            raise FrameworkError("Test error")
    
    def test_message_preserved(self):
        """Test that error message is preserved."""
        error = FrameworkError("Test error message")
        
        assert str(error) == "Test error message"
    
    def test_can_be_caught_as_exception(self):
        """Test that FrameworkError can be caught as Exception."""
        with pytest.raises(Exception):
            raise FrameworkError("Test error")
    
    def test_no_args(self):
        """Test FrameworkError with no arguments."""
        error = FrameworkError()
        
        assert str(error) == ""


class TestModuleLoadError:
    """Tests for ModuleLoadError exception."""
    
    def test_is_framework_error(self):
        """Test that ModuleLoadError is a FrameworkError."""
        assert issubclass(ModuleLoadError, FrameworkError)
    
    def test_is_exception(self):
        """Test that ModuleLoadError is an Exception."""
        assert issubclass(ModuleLoadError, Exception)
    
    def test_can_be_raised(self):
        """Test that ModuleLoadError can be raised."""
        with pytest.raises(ModuleLoadError):
            raise ModuleLoadError("Module failed to load")
    
    def test_message_preserved(self):
        """Test that error message is preserved."""
        error = ModuleLoadError("Module 'test_module' failed to load")
        
        assert "test_module" in str(error)
    
    def test_can_be_caught_as_framework_error(self):
        """Test that ModuleLoadError can be caught as FrameworkError."""
        with pytest.raises(FrameworkError):
            raise ModuleLoadError("Test error")
    
    def test_typical_usage_missing_entrypoint(self):
        """Test typical usage for missing entrypoint."""
        module_name = "my_module"
        error = ModuleLoadError(f"Module '{module_name}' missing entrypoint.")
        
        assert module_name in str(error)
    
    def test_typical_usage_failed_load(self):
        """Test typical usage for failed load."""
        module_name = "my_module"
        original_error = "ImportError: No module named 'xyz'"
        error = ModuleLoadError(f"Failed to load '{module_name}': {original_error}")
        
        assert module_name in str(error)
        assert original_error in str(error)


class TestDependencyResolutionError:
    """Tests for DependencyResolutionError exception."""
    
    def test_is_framework_error(self):
        """Test that DependencyResolutionError is a FrameworkError."""
        assert issubclass(DependencyResolutionError, FrameworkError)
    
    def test_is_exception(self):
        """Test that DependencyResolutionError is an Exception."""
        assert issubclass(DependencyResolutionError, Exception)
    
    def test_can_be_raised(self):
        """Test that DependencyResolutionError can be raised."""
        with pytest.raises(DependencyResolutionError):
            raise DependencyResolutionError("Circular dependency detected")
    
    def test_message_preserved(self):
        """Test that error message is preserved."""
        error = DependencyResolutionError("Circular dependency in 'module_a'")
        
        assert "Circular dependency" in str(error)
        assert "module_a" in str(error)
    
    def test_can_be_caught_as_framework_error(self):
        """Test that DependencyResolutionError can be caught as FrameworkError."""
        with pytest.raises(FrameworkError):
            raise DependencyResolutionError("Test error")
    
    def test_typical_usage_circular_dependency(self):
        """Test typical usage for circular dependency."""
        module_name = "module_a"
        error = DependencyResolutionError(f"Circular dependency in '{module_name}'")
        
        assert "Circular dependency" in str(error)
        assert module_name in str(error)
    
    def test_typical_usage_missing_capability(self):
        """Test typical usage for missing capability."""
        module_name = "module_b"
        capability = "database"
        error = DependencyResolutionError(
            f"'{module_name}' requires '{capability}' but none provides it."
        )
        
        assert module_name in str(error)
        assert capability in str(error)
        assert "requires" in str(error)


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""
    
    def test_catching_base_catches_derived(self):
        """Test that catching FrameworkError catches derived exceptions."""
        errors_caught = []
        
        try:
            raise ModuleLoadError("Test")
        except FrameworkError as e:
            errors_caught.append(e)
        
        try:
            raise DependencyResolutionError("Test")
        except FrameworkError as e:
            errors_caught.append(e)
        
        assert len(errors_caught) == 2
        assert isinstance(errors_caught[0], ModuleLoadError)
        assert isinstance(errors_caught[1], DependencyResolutionError)
    
    def test_different_exception_types(self):
        """Test that different exception types can be distinguished."""
        with pytest.raises(ModuleLoadError):
            raise ModuleLoadError("Load error")
        
        with pytest.raises(DependencyResolutionError):
            raise DependencyResolutionError("Dependency error")
    
    def test_catching_specific_does_not_catch_others(self):
        """Test that catching specific exception doesn't catch others."""
        caught = []
        
        # This should catch only ModuleLoadError
        try:
            raise ModuleLoadError("Test")
        except ModuleLoadError:
            caught.append("module_load")
        
        # This should not be caught by the above
        try:
            raise DependencyResolutionError("Test")
        except DependencyResolutionError:
            caught.append("dependency")
        
        assert caught == ["module_load", "dependency"]
