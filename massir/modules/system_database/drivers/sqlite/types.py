"""
SQLite type mappings.
"""
from ...core.types import DatabaseType, ColumnType, TYPE_MAPPING

# SQLite-specific type mappings (extends TYPE_MAPPING)
SQLITE_TYPE_MAPPING = TYPE_MAPPING[DatabaseType.SQLITE].copy()

# Additional SQLite-specific types
SQLITE_EXTRA_TYPES = {
    # SQLite uses dynamic typing, these are affinity types
    "NUMERIC": "NUMERIC",
    "NONE": "BLOB",  # No affinity
}

def get_sqlite_type(column_type: ColumnType) -> str:
    """Convert ColumnType to SQLite type string."""
    return SQLITE_TYPE_MAPPING.get(column_type, "TEXT")

def sqlite_type_to_python(sqlite_type: str) -> str:
    """Convert SQLite type to Python type hint."""
    type_lower = sqlite_type.lower()
    if "int" in type_lower:
        return "int"
    elif "real" in type_lower or "float" in type_lower or "double" in type_lower:
        return "float"
    elif "text" in type_lower or "char" in type_lower or "varchar" in type_lower:
        return "str"
    elif "blob" in type_lower:
        return "bytes"
    else:
        return "Any"