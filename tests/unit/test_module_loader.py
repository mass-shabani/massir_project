"""
Unit tests for ModuleLoader.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from massir.core.module_loader import ModuleLoader
from massir.core.exceptions import DependencyResolutionError, ModuleLoadError
from massir.core.interfaces import IModule, ModuleContext


class TestModuleLoader:
    """Tests for ModuleLoader class."""
    
    def test_init_without_path(self):
        """Test initialization without path parameter."""
        loader = ModuleLoader()
        
        assert loader._path is None
    
    def test_init_with_path(self):
        """Test initialization with path parameter."""
        mock_path = Mock()
        loader = ModuleLoader(path=mock_path)
        
        assert loader._path == mock_path
    
    def test_resolve_path_with_massir_placeholder(self, tmp_path):
        """Test path resolution with {massir_dir} placeholder."""
        mock_path = Mock()
        mock_path.massir = tmp_path / "massir"
        mock_path.app = tmp_path / "app"
        
        loader = ModuleLoader(path=mock_path)
        result = loader._resolve_path("{massir_dir}/modules")
        
        assert "massir" in str(result)
        assert "modules" in str(result)
    
    def test_resolve_path_with_app_placeholder(self, tmp_path):
        """Test path resolution with {app_dir} placeholder."""
        mock_path = Mock()
        mock_path.massir = tmp_path / "massir"
        mock_path.app = tmp_path / "app"
        
        loader = ModuleLoader(path=mock_path)
        result = loader._resolve_path("{app_dir}/my_modules")
        
        assert "app" in str(result)
        assert "my_modules" in str(result)
    
    def test_resolve_path_without_placeholders(self):
        """Test path resolution without placeholders."""
        loader = ModuleLoader()
        result = loader._resolve_path("/absolute/path/to/modules")
        
        assert str(result) == str(Path("/absolute/path/to/modules"))


class TestDependencyResolution:
    """Tests for dependency resolution in ModuleLoader."""
    
    def test_resolve_order_no_dependencies(self):
        """Test dependency resolution with no dependencies."""
        loader = ModuleLoader()
        modules_data = [
            {"manifest": {"name": "module_a", "provides": [], "requires": []}},
            {"manifest": {"name": "module_b", "provides": [], "requires": []}},
            {"manifest": {"name": "module_c", "provides": [], "requires": []}},
        ]
        
        result = loader.resolve_order(modules_data)
        
        assert len(result) == 3
        names = [m["manifest"]["name"] for m in result]
        assert set(names) == {"module_a", "module_b", "module_c"}
    
    def test_resolve_order_with_dependencies(self):
        """Test dependency resolution with dependencies."""
        loader = ModuleLoader()
        modules_data = [
            {"manifest": {"name": "module_a", "provides": ["db"], "requires": []}},
            {"manifest": {"name": "module_b", "provides": [], "requires": ["db"]}},
        ]
        
        result = loader.resolve_order(modules_data)
        
        names = [m["manifest"]["name"] for m in result]
        assert names.index("module_a") < names.index("module_b")
    
    def test_resolve_order_chain_dependencies(self):
        """Test dependency resolution with chain dependencies."""
        loader = ModuleLoader()
        modules_data = [
            {"manifest": {"name": "module_a", "provides": ["cap_a"], "requires": []}},
            {"manifest": {"name": "module_b", "provides": ["cap_b"], "requires": ["cap_a"]}},
            {"manifest": {"name": "module_c", "provides": ["cap_c"], "requires": ["cap_b"]}},
        ]
        
        result = loader.resolve_order(modules_data)
        
        names = [m["manifest"]["name"] for m in result]
        assert names.index("module_a") < names.index("module_b")
        assert names.index("module_b") < names.index("module_c")
    
    def test_resolve_order_missing_dependency_raises_error(self):
        """Test that missing dependency raises DependencyResolutionError."""
        loader = ModuleLoader()
        modules_data = [
            {"manifest": {"name": "module_a", "provides": [], "requires": ["missing_cap"]}},
        ]
        
        with pytest.raises(DependencyResolutionError):
            loader.resolve_order(modules_data)
    
    def test_resolve_order_circular_dependency_raises_error(self):
        """Test that circular dependency raises DependencyResolutionError."""
        loader = ModuleLoader()
        # Create a circular dependency: A needs B, B needs A
        modules_data = [
            {"manifest": {"name": "module_a", "provides": ["cap_a"], "requires": ["cap_b"]}},
            {"manifest": {"name": "module_b", "provides": ["cap_b"], "requires": ["cap_a"]}},
        ]
        
        with pytest.raises(DependencyResolutionError):
            loader.resolve_order(modules_data)
    
    def test_resolve_order_with_existing_provides(self):
        """Test dependency resolution with existing capabilities."""
        loader = ModuleLoader()
        modules_data = [
            {"manifest": {"name": "module_a", "provides": [], "requires": ["existing_cap"]}},
        ]
        existing = {"existing_cap": "system_module"}
        
        result = loader.resolve_order(modules_data, existing_provides=existing)
        
        assert len(result) == 1
    
    def test_resolve_order_force_execute_ignores_missing(self):
        """Test that force_execute ignores missing dependencies."""
        loader = ModuleLoader()
        modules_data = [
            {"manifest": {"name": "module_a", "provides": [], "requires": ["missing_cap"]}},
        ]
        
        result = loader.resolve_order(modules_data, force_execute=True)
        
        assert len(result) == 1
    
    def test_resolve_order_multiple_providers(self):
        """Test resolution when multiple modules provide capabilities."""
        loader = ModuleLoader()
        modules_data = [
            {"manifest": {"name": "provider1", "provides": ["cap_x"], "requires": []}},
            {"manifest": {"name": "provider2", "provides": ["cap_y"], "requires": []}},
            {"manifest": {"name": "consumer", "provides": [], "requires": ["cap_x", "cap_y"]}},
        ]
        
        result = loader.resolve_order(modules_data)
        
        names = [m["manifest"]["name"] for m in result]
        assert names.index("provider1") < names.index("consumer")
        assert names.index("provider2") < names.index("consumer")


class TestModuleDiscovery:
    """Tests for module discovery."""
    
    @pytest.mark.asyncio
    async def test_discover_modules_empty_config(self):
        """Test discovery with empty config."""
        loader = ModuleLoader()
        mock_config = Mock()
        mock_logger = Mock()
        
        discovered, disabled, should_sort = await loader.discover_modules(
            [], is_system=True, config_api=mock_config, logger_api=mock_logger
        )
        
        assert discovered == []
        assert disabled == {}
        assert should_sort is False
    
    @pytest.mark.asyncio
    async def test_discover_modules_nonexistent_path(self, tmp_path):
        """Test discovery with non-existent path."""
        loader = ModuleLoader()
        mock_path = Mock()
        mock_path.massir = tmp_path
        mock_path.app = tmp_path
        loader._path = mock_path
        
        mock_config = Mock()
        mock_logger = Mock()
        
        modules_config = [{"path": "/nonexistent/path", "names": ["module1"]}]
        
        discovered, disabled, should_sort = await loader.discover_modules(
            modules_config, is_system=True, config_api=mock_config, logger_api=mock_logger
        )
        
        assert discovered == []
    
    @pytest.mark.asyncio
    async def test_discover_modules_with_manifest(self, tmp_path):
        """Test discovery with valid manifest."""
        # Create module directory with manifest
        module_dir = tmp_path / "test_module"
        module_dir.mkdir()
        
        manifest = {
            "name": "test_module",
            "type": "application",
            "entrypoint": "TestModule",
            "provides": ["test_cap"],
            "requires": []
        }
        with open(module_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        
        loader = ModuleLoader()
        mock_path = Mock()
        mock_path.massir = tmp_path
        mock_path.app = tmp_path
        loader._path = mock_path
        
        mock_config = Mock()
        mock_logger = Mock()
        
        modules_config = [{"path": str(tmp_path), "names": ["test_module"]}]
        
        discovered, disabled, should_sort = await loader.discover_modules(
            modules_config, is_system=False, config_api=mock_config, logger_api=mock_logger
        )
        
        assert len(discovered) == 1
        assert discovered[0]["manifest"]["name"] == "test_module"
    
    @pytest.mark.asyncio
    async def test_discover_modules_disabled_module(self, tmp_path):
        """Test discovery with disabled module."""
        module_dir = tmp_path / "disabled_module"
        module_dir.mkdir()
        
        manifest = {
            "name": "disabled_module",
            "type": "application",
            "entrypoint": "DisabledModule",
            "provides": ["disabled_cap"],
            "requires": [],
            "enabled": False
        }
        with open(module_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)
        
        loader = ModuleLoader()
        mock_path = Mock()
        mock_path.massir = tmp_path
        mock_path.app = tmp_path
        loader._path = mock_path
        
        mock_config = Mock()
        mock_logger = Mock()
        
        modules_config = [{"path": str(tmp_path), "names": ["disabled_module"]}]
        
        discovered, disabled, should_sort = await loader.discover_modules(
            modules_config, is_system=False, config_api=mock_config, logger_api=mock_logger
        )
        
        assert len(discovered) == 0
        assert "disabled_module" in disabled
        assert "disabled_cap" in disabled["disabled_module"]
    
    @pytest.mark.asyncio
    async def test_discover_modules_names_all(self, tmp_path):
        """Test discovery with names='all'."""
        # Create multiple modules
        for name in ["module_a", "module_b", "module_c"]:
            module_dir = tmp_path / name
            module_dir.mkdir()
            manifest = {
                "name": name,
                "type": "application",
                "entrypoint": name.title().replace("_", ""),
                "provides": [],
                "requires": []
            }
            with open(module_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)
        
        loader = ModuleLoader()
        mock_path = Mock()
        mock_path.massir = tmp_path
        mock_path.app = tmp_path
        loader._path = mock_path
        
        mock_config = Mock()
        mock_logger = Mock()
        
        modules_config = [{"path": str(tmp_path), "names": "all"}]
        
        discovered, disabled, should_sort = await loader.discover_modules(
            modules_config, is_system=False, config_api=mock_config, logger_api=mock_logger
        )
        
        assert len(discovered) == 3
        assert should_sort is True


class TestCheckRequirements:
    """Tests for requirements checking."""
    
    @pytest.mark.asyncio
    async def test_check_requirements_all_met(self):
        """Test when all requirements are met."""
        loader = ModuleLoader()
        
        mod_info = {
            "manifest": {
                "name": "test_module",
                "requires": ["cap_a", "cap_b"]
            }
        }
        system_provides = {"cap_a": "module_x", "cap_b": "module_y"}
        mock_config = Mock()
        mock_logger = Mock()
        
        met, missing = await loader.check_requirements(
            mod_info, system_provides, mock_config, mock_logger
        )
        
        assert met is True
        assert missing == []
    
    @pytest.mark.asyncio
    async def test_check_requirements_missing(self):
        """Test when requirements are missing."""
        loader = ModuleLoader()
        
        mod_info = {
            "manifest": {
                "name": "test_module",
                "requires": ["cap_a", "missing_cap"]
            }
        }
        system_provides = {"cap_a": "module_x"}
        mock_config = Mock()
        mock_logger = Mock()
        
        met, missing = await loader.check_requirements(
            mod_info, system_provides, mock_config, mock_logger
        )
        
        assert met is False
        assert "missing_cap" in missing
    
    @pytest.mark.asyncio
    async def test_check_requirements_no_requirements(self):
        """Test when module has no requirements."""
        loader = ModuleLoader()
        
        mod_info = {
            "manifest": {
                "name": "test_module",
                "requires": []
            }
        }
        system_provides = {}
        mock_config = Mock()
        mock_logger = Mock()
        
        met, missing = await loader.check_requirements(
            mod_info, system_provides, mock_config, mock_logger
        )
        
        assert met is True
        assert missing == []
    
    @pytest.mark.asyncio
    async def test_check_requirements_disabled_module_warning(self):
        """Test warning when requirement is provided by disabled module."""
        loader = ModuleLoader()
        
        mod_info = {
            "manifest": {
                "name": "test_module",
                "requires": ["disabled_cap"]
            }
        }
        system_provides = {}
        disabled_modules = {"disabled_mod": ["disabled_cap"]}
        mock_config = Mock()
        mock_logger = Mock()
        
        met, missing = await loader.check_requirements(
            mod_info, system_provides, mock_config, mock_logger, disabled_modules
        )
        
        assert met is False
        assert "disabled_cap" in missing


class TestModuleInstantiation:
    """Tests for module instantiation."""
    
    @pytest.mark.asyncio
    async def test_instantiate_missing_entrypoint(self, tmp_path):
        """Test instantiation with missing entrypoint."""
        loader = ModuleLoader()
        
        mod_info = {
            "path": tmp_path,
            "manifest": {
                "name": "test_module",
                "id": "test123"
                # No entrypoint
            }
        }
        
        with pytest.raises(ModuleLoadError) as exc_info:
            await loader.instantiate(mod_info, is_system=False)
        
        assert "missing entrypoint" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_instantiate_generates_id_if_missing(self, tmp_path):
        """Test that instantiation generates ID if missing."""
        loader = ModuleLoader()
        
        mod_info = {
            "path": tmp_path,
            "manifest": {
                "name": "test_module",
                "entrypoint": "TestModule"
                # No id
            }
        }
        
        # This will fail because the module doesn't exist, but we can check
        # that ID was generated
        try:
            await loader.instantiate(mod_info, is_system=False)
        except ModuleLoadError:
            pass
        
        # Check that ID was added to manifest
        assert "id" in mod_info["manifest"]
