"""
Unit tests for core_apis module.
"""
import pytest
from abc import ABC

from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI


class TestCoreLoggerAPI:
    """Tests for CoreLoggerAPI abstract class."""
    
    def test_is_abstract_class(self):
        """Test that CoreLoggerAPI is an abstract class."""
        assert ABC in CoreLoggerAPI.__bases__
    
    def test_cannot_instantiate_directly(self):
        """Test that CoreLoggerAPI cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CoreLoggerAPI()
    
    def test_has_log_method(self):
        """Test that CoreLoggerAPI has log method."""
        assert hasattr(CoreLoggerAPI, 'log')
    
    def test_log_is_abstract(self):
        """Test that log method is abstract."""
        # Check that log is decorated with @abstractmethod
        assert getattr(CoreLoggerAPI.log, '__isabstractmethod__', False)
    
    def test_subclass_must_implement_log(self):
        """Test that subclass must implement log method."""
        class IncompleteLogger(CoreLoggerAPI):
            pass
        
        with pytest.raises(TypeError):
            IncompleteLogger()
    
    def test_complete_subclass(self):
        """Test that complete subclass can be instantiated."""
        class CompleteLogger(CoreLoggerAPI):
            def log(self, message, level="INFO", tag=None, **kwargs):
                pass
        
        logger = CompleteLogger()
        assert isinstance(logger, CoreLoggerAPI)


class TestCoreConfigAPI:
    """Tests for CoreConfigAPI abstract class."""
    
    def test_is_abstract_class(self):
        """Test that CoreConfigAPI is an abstract class."""
        assert ABC in CoreConfigAPI.__bases__
    
    def test_cannot_instantiate_directly(self):
        """Test that CoreConfigAPI cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CoreConfigAPI()
    
    def test_has_get_method(self):
        """Test that CoreConfigAPI has get method."""
        assert hasattr(CoreConfigAPI, 'get')
    
    def test_get_is_abstract(self):
        """Test that get method is abstract."""
        # Check that get is decorated with @abstractmethod
        assert getattr(CoreConfigAPI.get, '__isabstractmethod__', False)
    
    def test_subclass_must_implement_get(self):
        """Test that subclass must implement get method."""
        class IncompleteConfig(CoreConfigAPI):
            pass
        
        with pytest.raises(TypeError):
            IncompleteConfig()
    
    def test_complete_subclass(self):
        """Test that complete subclass can be instantiated."""
        class CompleteConfig(CoreConfigAPI):
            def get(self, key):
                return None
        
        config = CompleteConfig()
        assert isinstance(config, CoreConfigAPI)


class TestAPIContract:
    """Tests for API contracts and signatures."""
    
    def test_logger_log_signature(self):
        """Test that log method has correct signature."""
        import inspect
        sig = inspect.signature(CoreLoggerAPI.log)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'message' in params
        assert 'level' in params
        assert 'tag' in params
    
    def test_config_get_signature(self):
        """Test that get method has correct signature."""
        import inspect
        sig = inspect.signature(CoreConfigAPI.get)
        params = list(sig.parameters.keys())
        
        assert 'self' in params
        assert 'key' in params
    
    def test_logger_implementation_can_be_used(self):
        """Test that a logger implementation can be used polymorphically."""
        class TestLogger(CoreLoggerAPI):
            def __init__(self):
                self.messages = []
            
            def log(self, message, level="INFO", tag=None, **kwargs):
                self.messages.append((message, level, tag))
        
        logger = TestLogger()
        logger.log("test", level="ERROR", tag="core")
        
        assert logger.messages == [("test", "ERROR", "core")]
    
    def test_config_implementation_can_be_used(self):
        """Test that a config implementation can be used polymorphically."""
        class TestConfig(CoreConfigAPI):
            def __init__(self, data):
                self._data = data
            
            def get(self, key):
                return self._data.get(key)
        
        config = TestConfig({"key": "value"})
        
        assert config.get("key") == "value"
        assert config.get("missing") is None
