# massir/core/path.py
"""
Project path management.
"""
from typing import Optional, Dict
from pathlib import Path as PathLib


class Path:
    """
    Project path management class.

    This class maintains various project paths and provides
    functionality to change and access them.

    Default paths:
        - massir_dir: Main Massir framework directory
        - app_dir: User application directory (where main.py is located)
    """

    def __init__(self, app_dir: Optional[str] = None):
        """
        Initialize path manager.

        Args:
            app_dir: Path to user application directory
        """
        # Auto-detect massir_dir
        # path.py is at massir/core/path.py
        # massir/__init__.py is at massir/__init__.py
        # So we need to go 2 levels up
        self._massir_dir = PathLib(__file__).parent.parent.resolve()
        # Set app_dir
        if app_dir:
            self._app_dir = PathLib(app_dir).resolve()
        else:
            self._app_dir = PathLib.cwd().resolve()

        # Dictionary of additional paths
        self._custom_paths: Dict[str, PathLib] = {}

    @property
    def massir(self) -> PathLib:
        """Massir framework path (read-only)."""
        return self._massir_dir

    @property
    def app(self) -> PathLib:
        """User application path."""
        return self._app_dir

    def get(self, key: str) -> str:
        """
        Get path as string.

        Args:
            key: Path name (massir, app, or custom name)

        Returns:
            Path string
        """
        if key in ("massir_dir", "massir"):
            return str(self._massir_dir)
        elif key in ("app_dir", "app"):
            return str(self._app_dir)
        elif key in self._custom_paths:
            return str(self._custom_paths[key])
        else:
            raise KeyError(f"Path '{key}' not found")

    def set(self, key: str, value: str):
        """
        Set or add a path.

        Args:
            key: Path name
            value: Path value (string)
        """
        if key in ("massir_dir", "massir"):
            self._massir_dir = PathLib(value).resolve()
        elif key in ("app_dir", "app"):
            self._app_dir = PathLib(value).resolve()
        else:
            self._custom_paths[key] = PathLib(value).resolve()

    def resolve(self, key: str) -> PathLib:
        """
        Get path as PathLib object.

        Args:
            key: Path name (massir, massir_dir, app, app_dir, or custom name)

        Returns:
            PathLib object
        """
        if key in ("massir_dir", "massir"):
            return self._massir_dir
        elif key in ("app_dir", "app"):
            return self._app_dir
        elif key in self._custom_paths:
            return self._custom_paths[key]
        else:
            raise KeyError(f"Path '{key}' not found")

    def get_all_folders(self, base_key: str) -> list[str]:
        """
        Get list of all folders in base path.

        Args:
            base_key: Base path key (e.g., 'massir_dir' or 'app_dir')

        Returns:
            List of folder names
        """
        base_path = self.resolve(base_key)
        if base_path.exists() and base_path.is_dir():
            return [f.name for f in base_path.iterdir() if f.is_dir()]
        return []

    def __str__(self) -> str:
        return f"Path(massir={self._massir_dir}, app={self._app_dir})"

    def __repr__(self) -> str:
        return self.__str__()
