"""
PostgreSQL type mappings.
"""
from ...core.types import DatabaseType, ColumnType, TYPE_MAPPING

# PostgreSQL-specific type mappings (extends TYPE_MAPPING)
POSTGRESQL_TYPE_MAPPING = TYPE_MAPPING[DatabaseType.POSTGRESQL].copy()

# Additional PostgreSQL-specific types
POSTGRESQL_EXTRA_TYPES = {
    # PostgreSQL JSON types
    "JSONB": "JSONB",
    "JSON": "JSON",
    # PostgreSQL array types
    "ARRAY": "TEXT[]",
    # PostgreSQL UUID
    "UUID": "UUID",
    # PostgreSQL network types
    "INET": "INET",
    "CIDR": "CIDR",
    "MACADDR": "MACADDR",
    # PostgreSQL geometric types
    "POINT": "POINT",
    "LINE": "LINE",
    "LSEG": "LSEG",
    "BOX": "BOX",
    "PATH": "PATH",
    "POLYGON": "POLYGON",
    "CIRCLE": "CIRCLE",
    # PostgreSQL range types
    "INT4RANGE": "INT4RANGE",
    "INT8RANGE": "INT8RANGE",
    "NUMRANGE": "NUMRANGE",
    "TSRANGE": "TSRANGE",
    "TSTZRANGE": "TSTZRANGE",
    "DATERANGE": "DATERANGE",
}

def get_postgresql_type(column_type: ColumnType) -> str:
    """Convert ColumnType to PostgreSQL type string."""
    return POSTGRESQL_TYPE_MAPPING.get(column_type, "TEXT")

def postgresql_type_to_python(pg_type: str) -> str:
    """Convert PostgreSQL type to Python type hint."""
    type_lower = pg_type.lower()
    if "int" in type_lower or "serial" in type_lower:
        return "int"
    elif "real" in type_lower or "double" in type_lower or "float" in type_lower or "numeric" in type_lower or "decimal" in type_lower:
        return "float"
    elif "text" in type_lower or "char" in type_lower or "varchar" in type_lower:
        return "str"
    elif "bool" in type_lower:
        return "bool"
    elif "bytea" in type_lower or "blob" in type_lower:
        return "bytes"
    elif "json" in type_lower:
        return "dict"
    elif "timestamp" in type_lower or "date" in type_lower or "time" in type_lower:
        return "datetime"
    elif "uuid" in type_lower:
        return "UUID"
    elif "[]" in type_lower or "array" in type_lower:
        return "list"
    else:
        return "Any"