"""
Database service helper functions.
"""
from massir.modules.system_database import TableDef, ColumnDef, ColumnType


async def create_users_table(db, logger=None):
    """Create the users table if it doesn't exist."""
    # Check if table exists
    if await db.default.table_exists("users"):
        if logger:
            logger.log("Users table already exists", tag="sqlite_simple")
        return True
    
    # Define table structure
    users_table = TableDef(
        name="users",
        columns=[
            ColumnDef(
                name="id",
                type=ColumnType.INTEGER,
                primary_key=True,
                auto_increment=True,
                nullable=False
            ),
            ColumnDef(
                name="username",
                type=ColumnType.VARCHAR,
                length=50,
                nullable=False,
                unique=True
            ),
            ColumnDef(
                name="email",
                type=ColumnType.VARCHAR,
                length=100,
                nullable=False,
                unique=True
            ),
            ColumnDef(
                name="password_hash",
                type=ColumnType.VARCHAR,
                length=255,
                nullable=False
            ),
            ColumnDef(
                name="full_name",
                type=ColumnType.VARCHAR,
                length=100,
                nullable=True
            ),
            ColumnDef(
                name="is_active",
                type=ColumnType.BOOLEAN,
                default=True,
                nullable=False
            ),
            ColumnDef(
                name="created_at",
                type=ColumnType.TIMESTAMP,
                nullable=True
            ),
            ColumnDef(
                name="updated_at",
                type=ColumnType.TIMESTAMP,
                nullable=True
            )
        ],
        primary_key=["id"],
        if_not_exists=True
    )
    
    # Create the table
    result = await db.default.schema.create_table(users_table)
    
    if result.success:
        if logger:
            logger.log("Users table created successfully", tag="sqlite_simple")
        return True
    else:
        if logger:
            logger.log(
                f"Failed to create users table: {result.error}",
                level="ERROR",
                tag="sqlite_simple"
            )
        return False


async def create_products_table(db, logger=None):
    """Create the products table if it doesn't exist."""
    if await db.default.table_exists("products"):
        if logger:
            logger.log("Products table already exists", tag="sqlite_simple")
        return True
    
    products_table = TableDef(
        name="products",
        columns=[
            ColumnDef(
                name="id",
                type=ColumnType.INTEGER,
                primary_key=True,
                auto_increment=True,
                nullable=False
            ),
            ColumnDef(
                name="name",
                type=ColumnType.VARCHAR,
                length=100,
                nullable=False
            ),
            ColumnDef(
                name="description",
                type=ColumnType.TEXT,
                nullable=True
            ),
            ColumnDef(
                name="price",
                type=ColumnType.DECIMAL,
                precision=10,
                scale=2,
                nullable=False
            ),
            ColumnDef(
                name="stock",
                type=ColumnType.INTEGER,
                default=0,
                nullable=False
            ),
            ColumnDef(
                name="is_available",
                type=ColumnType.BOOLEAN,
                default=True,
                nullable=False
            ),
            ColumnDef(
                name="created_at",
                type=ColumnType.TIMESTAMP,
                nullable=True
            )
        ],
        primary_key=["id"],
        if_not_exists=True
    )
    
    result = await db.default.schema.create_table(products_table)
    
    if result.success:
        if logger:
            logger.log("Products table created successfully", tag="sqlite_simple")
        return True
    else:
        if logger:
            logger.log(
                f"Failed to create products table: {result.error}",
                level="ERROR",
                tag="sqlite_simple"
            )
        return False


async def get_table_list(db):
    """Get list of all tables in the database."""
    # For SQLite, query sqlite_master
    result = await db.default.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    if result.success and result.rows:
        return [row['name'] for row in result.rows]
    return []


async def get_table_info(db, table_name):
    """Get column information for a table."""
    result = await db.default.execute(f"PRAGMA table_info({table_name})")
    if result.success and result.rows:
        return result.rows
    return []


async def get_table_row_count(db, table_name):
    """Get the number of rows in a table."""
    result = await db.default.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    if result.success and result.rows:
        return result.rows[0]['count']
    return 0
