"""
Shared pytest fixtures for Massir tests.
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock

from massir.core.interfaces import ModuleContext
from massir.core.registry import ModuleRegistry
from massir.core.hooks import HooksManager
from massir.core.hook_types import SystemHook
from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI


# ============================================================================
# Registry and Context Fixtures
# ============================================================================

@pytest.fixture
def registry():
    """Create a fresh ModuleRegistry for each test."""
    return ModuleRegistry()


@pytest.fixture
def module_context():
    """Create a fresh ModuleContext for each test."""
    return ModuleContext()


@pytest.fixture
def hooks_manager():
    """Create a fresh HooksManager for each test."""
    return HooksManager()


# ============================================================================
# Mock API Fixtures
# ============================================================================

@pytest.fixture
def mock_config_api():
    """Create a mock CoreConfigAPI."""
    config = Mock(spec=CoreConfigAPI)
    config.get = Mock(return_value=None)
    config.get_modules_config_for_type = Mock(return_value=[])
    config.set = Mock()
    config.has = Mock(return_value=False)
    return config


@pytest.fixture
def mock_logger_api():
    """Create a mock CoreLoggerAPI."""
    logger = Mock(spec=CoreLoggerAPI)
    logger.info = Mock()
    logger.error = Mock()
    logger.warning = Mock()
    logger.debug = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def mock_app():
    """Create a mock App instance."""
    app = Mock()
    app.modules = {}
    app.context = ModuleContext()
    app.hooks = HooksManager()
    app.request_shutdown = Mock()
    app.request_restart = Mock()
    return app


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def temp_module_dir(tmp_path):
    """Create a temporary module directory with manifest.json."""
    module_dir = tmp_path / "test_module"
    module_dir.mkdir()
    
    manifest = {
        "name": "test_module",
        "type": "application",
        "entrypoint": "TestModule",
        "provides": [],
        "requires": [],
        "enabled": True
    }
    
    with open(module_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    
    return module_dir


@pytest.fixture
def temp_system_module_dir(tmp_path):
    """Create a temporary system module directory with manifest.json."""
    module_dir = tmp_path / "test_system_module"
    module_dir.mkdir()
    
    manifest = {
        "name": "test_system_module",
        "type": "system",
        "entrypoint": "TestSystemModule",
        "provides": ["test_capability"],
        "requires": [],
        "enabled": True
    }
    
    with open(module_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    
    return module_dir


@pytest.fixture
def temp_app_dir(tmp_path):
    """Create a temporary app directory structure with multiple modules."""
    app_dir = tmp_path / "test_app"
    app_dir.mkdir()
    
    # Create module A (no dependencies)
    module_a_dir = app_dir / "module_a"
    module_a_dir.mkdir()
    manifest_a = {
        "name": "module_a",
        "type": "application",
        "entrypoint": "ModuleA",
        "provides": ["capability_a"],
        "requires": []
    }
    with open(module_a_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_a, f)
    
    # Create module B (depends on A)
    module_b_dir = app_dir / "module_b"
    module_b_dir.mkdir()
    manifest_b = {
        "name": "module_b",
        "type": "application",
        "entrypoint": "ModuleB",
        "provides": ["capability_b"],
        "requires": ["capability_a"]
    }
    with open(module_b_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_b, f)
    
    # Create module C (depends on B)
    module_c_dir = app_dir / "module_c"
    module_c_dir.mkdir()
    manifest_c = {
        "name": "module_c",
        "type": "application",
        "entrypoint": "ModuleC",
        "provides": ["capability_c"],
        "requires": ["capability_b"]
    }
    with open(module_c_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_c, f)
    
    return app_dir


# ============================================================================
# Test Module Classes
# ============================================================================

class MockModule:
    """Mock module for testing."""
    
    name = "mock_module"
    id = "mock_id"
    provides = []
    requires = []
    
    def __init__(self):
        self.load_called = False
        self.start_called = False
        self.ready_called = False
        self.stop_called = False
        self._context = None
    
    async def load(self, context):
        self.load_called = True
        self._context = context
    
    async def start(self, context):
        self.start_called = True
    
    async def ready(self, context):
        self.ready_called = True
    
    async def stop(self, context):
        self.stop_called = True


class MockSystemModule(MockModule):
    """Mock system module for testing."""
    
    name = "mock_system_module"
    provides = ["test_capability"]
    _is_system = True


@pytest.fixture
def mock_module():
    """Create a mock module instance."""
    return MockModule()


@pytest.fixture
def mock_system_module():
    """Create a mock system module instance."""
    return MockSystemModule()


# ============================================================================
# Module Info Fixtures
# ============================================================================

@pytest.fixture
def sample_module_info(tmp_path):
    """Create sample module info dictionary."""
    module_path = tmp_path / "sample_module"
    module_path.mkdir()
    
    return {
        "path": module_path,
        "manifest": {
            "name": "sample_module",
            "id": "sample123",
            "type": "application",
            "entrypoint": "SampleModule",
            "provides": ["sample_capability"],
            "requires": []
        }
    }


@pytest.fixture
def sample_system_module_info(tmp_path):
    """Create sample system module info dictionary."""
    module_path = tmp_path / "sample_system_module"
    module_path.mkdir()
    
    return {
        "path": module_path,
        "manifest": {
            "name": "sample_system_module",
            "id": "sys123",
            "type": "system",
            "entrypoint": "SampleSystemModule",
            "provides": ["system_capability"],
            "requires": []
        }
    }
