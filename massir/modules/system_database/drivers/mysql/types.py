"""
MySQL type mappings.
"""
from ...core.types import DatabaseType, ColumnType, TYPE_MAPPING

# MySQL-specific type mappings (extends TYPE_MAPPING)
MYSQL_TYPE_MAPPING = TYPE_MAPPING[DatabaseType.MYSQL].copy()

# Additional MySQL-specific types
MYSQL_EXTRA_TYPES = {
    # MySQL JSON type
    "JSON": "JSON",
    # MySQL binary types
    "BINARY": "BINARY",
    "VARBINARY": "VARBINARY",
    "BLOB": "BLOB",
    "MEDIUMBLOB": "MEDIUMBLOB",
    "LONGBLOB": "LONGBLOB",
    "TINYBLOB": "TINYBLOB",
    # MySQL text types
    "TINYTEXT": "TINYTEXT",
    "MEDIUMTEXT": "MEDIUMTEXT",
    "LONGTEXT": "LONGTEXT",
    # MySQL enum and set
    "ENUM": "ENUM",
    "SET": "SET",
    # MySQL spatial types
    "GEOMETRY": "GEOMETRY",
    "POINT": "POINT",
    "LINESTRING": "LINESTRING",
    "POLYGON": "POLYGON",
    # MySQL year
    "YEAR": "YEAR",
}

def get_mysql_type(column_type: ColumnType) -> str:
    """Convert ColumnType to MySQL type string."""
    return MYSQL_TYPE_MAPPING.get(column_type, "TEXT")

def mysql_type_to_python(mysql_type: str) -> str:
    """Convert MySQL type to Python type hint."""
    type_lower = mysql_type.lower()
    if "int" in type_lower:
        return "int"
    elif "real" in type_lower or "double" in type_lower or "float" in type_lower or "decimal" in type_lower or "numeric" in type_lower:
        return "float"
    elif "text" in type_lower or "char" in type_lower or "varchar" in type_lower or "enum" in type_lower or "set" in type_lower:
        return "str"
    elif "bool" in type_lower or "tinyint(1)" in type_lower:
        return "bool"
    elif "blob" in type_lower or "binary" in type_lower:
        return "bytes"
    elif "json" in type_lower:
        return "dict"
    elif "timestamp" in type_lower or "date" in type_lower or "time" in type_lower or "year" in type_lower:
        return "datetime"
    elif "geometry" in type_lower or "point" in type_lower or "line" in type_lower or "polygon" in type_lower:
        return "object"
    else:
        return "Any"