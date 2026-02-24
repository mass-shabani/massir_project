"""
Unit tests for inject module.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from massir.core.inject import inject_system_apis
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.interfaces import IModule
from massir.core.registry import ModuleRegistry


class MockModule(IModule):
    """Mock module for testing."""
    name = "mock_module"


class MockLogger(CoreLoggerAPI):
    """Mock logger for testing."""
    
    def log(self, message, level="INFO", tag=None, **kwargs):
        pass


class MockConfig(CoreConfigAPI):
    """Mock config for testing."""
    
    def get(self, key):
        return None


@pytest.mark.asyncio
class TestInjectSystemAPIs:
    """Tests for inject_system_apis function."""
    
    async def test_inject_logger_override(self):
        """Test logger is injected when module provides it."""
        registry = ModuleRegistry()
        mock_logger = MockLogger()
        registry.set("core_logger", mock_logger)
        
        module = MockModule()
        logger_ref = [None]  # Current logger is None
        config_ref = [MockConfig()]
        
        await inject_system_apis(module, registry, logger_ref, config_ref)
        
        assert logger_ref[0] == mock_logger
    
    async def test_inject_logger_no_override_same_instance(self):
        """Test logger is not replaced when same instance."""
        registry = ModuleRegistry()
        mock_logger = MockLogger()
        registry.set("core_logger", mock_logger)
        
        module = MockModule()
        logger_ref = [mock_logger]  # Already same logger
        config_ref = [MockConfig()]
        
        # Should not change
        await inject_system_apis(module, registry, logger_ref, config_ref)
        
        assert logger_ref[0] == mock_logger
    
    async def test_inject_config_override(self):
        """Test config is injected when module provides it."""
        registry = ModuleRegistry()
        mock_config = MockConfig()
        registry.set("core_config", mock_config)
        
        module = MockModule()
        logger_ref = [MockLogger()]
        config_ref = [None]  # Current config is None
        
        await inject_system_apis(module, registry, logger_ref, config_ref)
        
        assert config_ref[0] == mock_config
    
    async def test_inject_config_no_override_same_instance(self):
        """Test config is not replaced when same instance."""
        registry = ModuleRegistry()
        mock_config = MockConfig()
        registry.set("core_config", mock_config)
        
        module = MockModule()
        logger_ref = [MockLogger()]
        config_ref = [mock_config]  # Already same config
        
        await inject_system_apis(module, registry, logger_ref, config_ref)
        
        assert config_ref[0] == mock_config
    
    async def test_no_injection_when_not_core_api(self):
        """Test no injection when service is not CoreLoggerAPI/CoreConfigAPI."""
        registry = ModuleRegistry()
        registry.set("core_logger", "not_a_logger")  # String, not CoreLoggerAPI
        registry.set("core_config", "not_a_config")  # String, not CoreConfigAPI
        
        module = MockModule()
        logger_ref = [MockLogger()]
        original_logger = logger_ref[0]
        config_ref = [MockConfig()]
        original_config = config_ref[0]
        
        await inject_system_apis(module, registry, logger_ref, config_ref)
        
        # Should not change because services are not correct type
        assert logger_ref[0] == original_logger
        assert config_ref[0] == original_config
    
    async def test_no_injection_when_service_missing(self):
        """Test no injection when services are missing."""
        registry = ModuleRegistry()  # Empty registry
        
        module = MockModule()
        logger_ref = [MockLogger()]
        original_logger = logger_ref[0]
        config_ref = [MockConfig()]
        original_config = config_ref[0]
        
        await inject_system_apis(module, registry, logger_ref, config_ref)
        
        # Should not change
        assert logger_ref[0] == original_logger
        assert config_ref[0] == original_config
    
    async def test_registry_updated_on_injection(self):
        """Test registry is updated when injection occurs."""
        registry = ModuleRegistry()
        mock_logger = MockLogger()
        mock_config = MockConfig()
        registry.set("core_logger", mock_logger)
        registry.set("core_config", mock_config)
        
        module = MockModule()
        logger_ref = [None]
        config_ref = [None]
        
        await inject_system_apis(module, registry, logger_ref, config_ref)
        
        # Registry should have the injected services
        assert registry.get("core_logger") == mock_logger
        assert registry.get("core_config") == mock_config
