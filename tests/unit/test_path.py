"""
Unit tests for Path class.
"""
import pytest
from pathlib import Path as PathLib
from massir.core.path import Path


class TestPath:
    """Tests for Path class."""
    
    def test_init_without_app_dir(self):
        """Test initialization without app_dir parameter."""
        path = Path()
        
        assert path._massir_dir.exists()
        assert path._app_dir.exists()
    
    def test_init_with_app_dir(self, tmp_path):
        """Test initialization with app_dir parameter."""
        path = Path(app_dir=str(tmp_path))
        
        assert path._app_dir == tmp_path.resolve()
    
    def test_massir_property(self):
        """Test massir property returns correct path."""
        path = Path()
        
        result = path.massir
        
        assert isinstance(result, PathLib)
        assert result.name == "massir"
    
    def test_app_property(self, tmp_path):
        """Test app property returns correct path."""
        path = Path(app_dir=str(tmp_path))
        
        result = path.app
        
        assert isinstance(result, PathLib)
        assert result == tmp_path.resolve()
    
    def test_get_massir_path(self):
        """Test get method for massir path."""
        path = Path()
        
        result = path.get("massir")
        
        assert isinstance(result, str)
        assert "massir" in result
    
    def test_get_massir_dir_path(self):
        """Test get method for massir_dir path."""
        path = Path()
        
        result = path.get("massir_dir")
        
        assert isinstance(result, str)
        assert "massir" in result
    
    def test_get_app_path(self, tmp_path):
        """Test get method for app path."""
        path = Path(app_dir=str(tmp_path))
        
        result = path.get("app")
        
        assert isinstance(result, str)
        assert str(tmp_path) in result
    
    def test_get_app_dir_path(self, tmp_path):
        """Test get method for app_dir path."""
        path = Path(app_dir=str(tmp_path))
        
        result = path.get("app_dir")
        
        assert isinstance(result, str)
        assert str(tmp_path) in result
    
    def test_get_custom_path(self, tmp_path):
        """Test get method for custom path."""
        path = Path(app_dir=str(tmp_path))
        
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        path.set("custom_path", str(custom_dir))
        
        result = path.get("custom_path")
        
        assert isinstance(result, str)
        assert "custom" in result
    
    def test_get_nonexistent_path_raises_error(self):
        """Test get raises KeyError for nonexistent path."""
        path = Path()
        
        with pytest.raises(KeyError):
            path.get("nonexistent")
    
    def test_set_app_path(self, tmp_path):
        """Test set method for app path."""
        path = Path()
        new_app = tmp_path / "new_app"
        new_app.mkdir()
        
        path.set("app", str(new_app))
        
        assert path.app == new_app.resolve()
    
    def test_set_app_dir_path(self, tmp_path):
        """Test set method for app_dir path."""
        path = Path()
        new_app = tmp_path / "new_app"
        new_app.mkdir()
        
        path.set("app_dir", str(new_app))
        
        assert path.app == new_app.resolve()
    
    def test_set_custom_path(self, tmp_path):
        """Test set method for custom path."""
        path = Path(app_dir=str(tmp_path))
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        
        path.set("my_path", str(custom_dir))
        
        assert path.get("my_path") == str(custom_dir.resolve())
    
    def test_resolve_massir(self):
        """Test resolve method for massir."""
        path = Path()
        
        result = path.resolve("massir")
        
        assert isinstance(result, PathLib)
        assert result.name == "massir"
    
    def test_resolve_app(self, tmp_path):
        """Test resolve method for app."""
        path = Path(app_dir=str(tmp_path))
        
        result = path.resolve("app")
        
        assert isinstance(result, PathLib)
        assert result == tmp_path.resolve()
    
    def test_resolve_nonexistent_raises_error(self):
        """Test resolve raises KeyError for nonexistent path."""
        path = Path()
        
        with pytest.raises(KeyError):
            path.resolve("nonexistent")
    
    def test_get_all_folders(self, tmp_path):
        """Test get_all_folders method."""
        # Create some folders
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder2").mkdir()
        (tmp_path / "folder3").mkdir()
        # Create a file (should not be included)
        (tmp_path / "file.txt").touch()
        
        path = Path(app_dir=str(tmp_path))
        
        folders = path.get_all_folders("app")
        
        assert "folder1" in folders
        assert "folder2" in folders
        assert "folder3" in folders
        assert "file.txt" not in folders
    
    def test_get_all_folders_nonexistent_base_raises_error(self, tmp_path):
        """Test get_all_folders with nonexistent base path raises KeyError."""
        path = Path(app_dir=str(tmp_path))
        
        # Try to get folders from a path that doesn't exist
        with pytest.raises(KeyError):
            path.get_all_folders("nonexistent")
    
    def test_str_representation(self, tmp_path):
        """Test __str__ method."""
        path = Path(app_dir=str(tmp_path))
        
        result = str(path)
        
        assert "Path(" in result
        assert "massir=" in result
        assert "app=" in result
    
    def test_repr_representation(self, tmp_path):
        """Test __repr__ method."""
        path = Path(app_dir=str(tmp_path))
        
        result = repr(path)
        
        assert result == str(path)
    
    def test_path_is_resolved(self, tmp_path):
        """Test that paths are resolved to absolute paths."""
        path = Path(app_dir=str(tmp_path))
        
        # All paths should be absolute
        assert path.massir.is_absolute()
        assert path.app.is_absolute()
