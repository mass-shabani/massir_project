"""
Unit tests for system_database module.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio

from massir.modules.system_database import (
    DatabaseModule,
    DatabaseService,
    DatabaseType,
    ColumnType,
    IndexType,
    RelationType,
    ColumnDef,
    IndexDef,
    ForeignKeyDef,
    RelationDef,
    TableDef,
    QueryResult,
    DatabaseConfig,
    TYPE_MAPPING,
    DatabaseError,
    ConnectionError,
    PoolError,
    QueryError,
    SchemaError,
    RecordError,
    TransactionError,
    CacheError,
    DriverNotFoundError,
    UnsupportedFeatureError
)
from massir.core.interfaces import ModuleContext


class TestDatabaseType:
    """Tests for DatabaseType enum."""
    
    def test_postgresql_value(self):
        """Test PostgreSQL value."""
        assert DatabaseType.POSTGRESQL.value == "postgresql"
    
    def test_mysql_value(self):
        """Test MySQL value."""
        assert DatabaseType.MYSQL.value == "mysql"
    
    def test_sqlite_value(self):
        """Test SQLite value."""
        assert DatabaseType.SQLITE.value == "sqlite"


class TestColumnType:
    """Tests for ColumnType enum."""
    
    def test_integer_types(self):
        """Test integer column types."""
        assert ColumnType.INTEGER.value == "integer"
        assert ColumnType.BIGINT.value == "bigint"
        assert ColumnType.SMALLINT.value == "smallint"
    
    def test_float_types(self):
        """Test float column types."""
        assert ColumnType.FLOAT.value == "float"
        assert ColumnType.DOUBLE.value == "double"
        assert ColumnType.DECIMAL.value == "decimal"
    
    def test_string_types(self):
        """Test string column types."""
        assert ColumnType.VARCHAR.value == "varchar"
        assert ColumnType.TEXT.value == "text"
        assert ColumnType.CHAR.value == "char"
    
    def test_boolean_type(self):
        """Test boolean column type."""
        assert ColumnType.BOOLEAN.value == "boolean"
    
    def test_datetime_types(self):
        """Test datetime column types."""
        assert ColumnType.DATE.value == "date"
        assert ColumnType.TIME.value == "time"
        assert ColumnType.DATETIME.value == "datetime"
        assert ColumnType.TIMESTAMP.value == "timestamp"
    
    def test_binary_types(self):
        """Test binary column types."""
        assert ColumnType.BLOB.value == "blob"
        assert ColumnType.BINARY.value == "binary"
    
    def test_json_type(self):
        """Test JSON column type."""
        assert ColumnType.JSON.value == "json"
    
    def test_uuid_type(self):
        """Test UUID column type."""
        assert ColumnType.UUID.value == "uuid"


class TestIndexType:
    """Tests for IndexType enum."""
    
    def test_btree_value(self):
        """Test BTREE value."""
        assert IndexType.BTREE.value == "btree"
    
    def test_hash_value(self):
        """Test HASH value."""
        assert IndexType.HASH.value == "hash"
    
    def test_gin_value(self):
        """Test GIN value."""
        assert IndexType.GIN.value == "gin"
    
    def test_gist_value(self):
        """Test GIST value."""
        assert IndexType.GIST.value == "gist"


class TestRelationType:
    """Tests for RelationType enum."""
    
    def test_one_to_one(self):
        """Test ONE_TO_ONE value."""
        assert RelationType.ONE_TO_ONE.value == "one_to_one"
    
    def test_one_to_many(self):
        """Test ONE_TO_MANY value."""
        assert RelationType.ONE_TO_MANY.value == "one_to_many"
    
    def test_many_to_many(self):
        """Test MANY_TO_MANY value."""
        assert RelationType.MANY_TO_MANY.value == "many_to_many"


class TestColumnDef:
    """Tests for ColumnDef dataclass."""
    
    def test_minimal_column(self):
        """Test minimal column definition."""
        col = ColumnDef(name="id", type=ColumnType.INTEGER)
        
        assert col.name == "id"
        assert col.type == ColumnType.INTEGER
        assert col.nullable == True
        assert col.default is None
        assert col.primary_key == False
    
    def test_full_column(self):
        """Test full column definition."""
        col = ColumnDef(
            name="email",
            type=ColumnType.VARCHAR,
            nullable=False,
            default="test@example.com",
            primary_key=False,
            auto_increment=False,
            unique=True,
            length=255,
            comment="User email"
        )
        
        assert col.name == "email"
        assert col.nullable == False
        assert col.unique == True
        assert col.length == 255
    
    def test_to_dict(self):
        """Test to_dict method."""
        col = ColumnDef(
            name="id",
            type=ColumnType.INTEGER,
            primary_key=True,
            auto_increment=True
        )
        result = col.to_dict()
        
        assert result["name"] == "id"
        assert result["type"] == "integer"
        assert result["primary_key"] == True
        assert result["auto_increment"] == True
    
    def test_string_type(self):
        """Test column with string type."""
        col = ColumnDef(name="data", type="custom_type")
        
        assert col.type == "custom_type"


class TestIndexDef:
    """Tests for IndexDef dataclass."""
    
    def test_minimal_index(self):
        """Test minimal index definition."""
        idx = IndexDef(name="idx_name", columns=["name"])
        
        assert idx.name == "idx_name"
        assert idx.columns == ["name"]
        assert idx.unique == False
        assert idx.type == IndexType.BTREE
    
    def test_unique_index(self):
        """Test unique index definition."""
        idx = IndexDef(
            name="idx_email",
            columns=["email"],
            unique=True,
            table="users"
        )
        
        assert idx.unique == True
        assert idx.table == "users"
    
    def test_to_dict(self):
        """Test to_dict method."""
        idx = IndexDef(
            name="idx_name",
            columns=["name", "surname"],
            unique=True,
            type=IndexType.HASH
        )
        result = idx.to_dict()
        
        assert result["name"] == "idx_name"
        assert result["columns"] == ["name", "surname"]
        assert result["unique"] == True
        assert result["type"] == "hash"


class TestForeignKeyDef:
    """Tests for ForeignKeyDef dataclass."""
    
    def test_minimal_fk(self):
        """Test minimal foreign key definition."""
        fk = ForeignKeyDef(
            columns=["user_id"],
            ref_table="users",
            ref_columns=["id"]
        )
        
        assert fk.columns == ["user_id"]
        assert fk.ref_table == "users"
        assert fk.ref_columns == ["id"]
        assert fk.on_delete == "RESTRICT"
        assert fk.on_update == "RESTRICT"
    
    def test_full_fk(self):
        """Test full foreign key definition."""
        fk = ForeignKeyDef(
            columns=["user_id"],
            ref_table="users",
            ref_columns=["id"],
            on_delete="CASCADE",
            on_update="CASCADE",
            name="fk_posts_user"
        )
        
        assert fk.on_delete == "CASCADE"
        assert fk.on_update == "CASCADE"
        assert fk.name == "fk_posts_user"
    
    def test_to_dict(self):
        """Test to_dict method."""
        fk = ForeignKeyDef(
            columns=["user_id"],
            ref_table="users",
            ref_columns=["id"],
            on_delete="SET NULL"
        )
        result = fk.to_dict()
        
        assert result["columns"] == ["user_id"]
        assert result["on_delete"] == "SET NULL"


class TestRelationDef:
    """Tests for RelationDef dataclass."""
    
    def test_one_to_many_relation(self):
        """Test one-to-many relation."""
        rel = RelationDef(
            name="user_posts",
            type=RelationType.ONE_TO_MANY,
            from_table="users",
            from_columns=["id"],
            to_table="posts",
            to_columns=["user_id"]
        )
        
        assert rel.type == RelationType.ONE_TO_MANY
        assert rel.through_table is None
    
    def test_many_to_many_relation(self):
        """Test many-to-many relation."""
        rel = RelationDef(
            name="user_roles",
            type=RelationType.MANY_TO_MANY,
            from_table="users",
            from_columns=["id"],
            to_table="roles",
            to_columns=["id"],
            through_table="user_roles"
        )
        
        assert rel.type == RelationType.MANY_TO_MANY
        assert rel.through_table == "user_roles"
    
    def test_to_dict(self):
        """Test to_dict method."""
        rel = RelationDef(
            name="user_posts",
            type=RelationType.ONE_TO_MANY,
            from_table="users",
            from_columns=["id"],
            to_table="posts",
            to_columns=["user_id"]
        )
        result = rel.to_dict()
        
        assert result["type"] == "one_to_many"
        assert result["from_table"] == "users"


class TestTableDef:
    """Tests for TableDef dataclass."""
    
    def test_minimal_table(self):
        """Test minimal table definition."""
        table = TableDef(
            name="users",
            columns=[
                ColumnDef(name="id", type=ColumnType.INTEGER, primary_key=True),
                ColumnDef(name="name", type=ColumnType.VARCHAR)
            ]
        )
        
        assert table.name == "users"
        assert len(table.columns) == 2
        assert table.if_not_exists == True
    
    def test_full_table(self):
        """Test full table definition."""
        table = TableDef(
            name="posts",
            columns=[
                ColumnDef(name="id", type=ColumnType.INTEGER, primary_key=True),
                ColumnDef(name="title", type=ColumnType.VARCHAR),
                ColumnDef(name="user_id", type=ColumnType.INTEGER)
            ],
            primary_key=["id"],
            indexes=[IndexDef(name="idx_user", columns=["user_id"])],
            foreign_keys=[
                ForeignKeyDef(
                    columns=["user_id"],
                    ref_table="users",
                    ref_columns=["id"]
                )
            ],
            comment="Blog posts",
            if_not_exists=False
        )
        
        assert len(table.indexes) == 1
        assert len(table.foreign_keys) == 1
        assert table.comment == "Blog posts"
    
    def test_to_dict(self):
        """Test to_dict method."""
        table = TableDef(
            name="users",
            columns=[
                ColumnDef(name="id", type=ColumnType.INTEGER)
            ]
        )
        result = table.to_dict()
        
        assert result["name"] == "users"
        assert len(result["columns"]) == 1
        assert result["if_not_exists"] == True


class TestQueryResult:
    """Tests for QueryResult dataclass."""
    
    def test_success_result(self):
        """Test successful query result."""
        result = QueryResult(
            success=True,
            affected_rows=5,
            rows=[{"id": 1}, {"id": 2}]
        )
        
        assert result.success == True
        assert result.affected_rows == 5
        assert len(result.rows) == 2
        assert result.error is None
    
    def test_error_result(self):
        """Test error query result."""
        result = QueryResult(
            success=False,
            error="Table not found"
        )
        
        assert result.success == False
        assert result.error == "Table not found"
    
    def test_insert_result(self):
        """Test insert query result."""
        result = QueryResult(
            success=True,
            affected_rows=1,
            last_insert_id=42
        )
        
        assert result.last_insert_id == 42
    
    def test_to_dict(self):
        """Test to_dict method."""
        result = QueryResult(
            success=True,
            affected_rows=3,
            execution_time=0.05
        )
        data = result.to_dict()
        
        assert data["success"] == True
        assert data["affected_rows"] == 3
        assert data["execution_time"] == 0.05


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""
    
    def test_minimal_config(self):
        """Test minimal config."""
        config = DatabaseConfig(name="default", driver="sqlite")
        
        assert config.name == "default"
        assert config.driver == "sqlite"
        assert config.host == "localhost"
        assert config.pool_min_size == 5
    
    def test_full_config(self):
        """Test full config."""
        config = DatabaseConfig(
            name="main",
            driver="postgresql",
            host="db.example.com",
            port=5432,
            database="myapp",
            user="admin",
            password="secret",
            pool_min_size=10,
            pool_max_size=50,
            ssl_mode="require"
        )
        
        assert config.host == "db.example.com"
        assert config.port == 5432
        assert config.pool_max_size == 50
        assert config.ssl_mode == "require"
    
    def test_to_dict_hides_password(self):
        """Test to_dict hides password."""
        config = DatabaseConfig(
            name="main",
            driver="postgresql",
            password="secret"
        )
        result = config.to_dict()
        
        assert result["password"] == "***"
    
    def test_from_dict(self):
        """Test from_dict class method."""
        data = {
            "name": "test",
            "driver": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "testdb",
            "pool_min_size": 3
        }
        config = DatabaseConfig.from_dict(data)
        
        assert config.name == "test"
        assert config.driver == "mysql"
        assert config.port == 3306
        assert config.pool_min_size == 3
    
    def test_from_dict_defaults(self):
        """Test from_dict with defaults."""
        config = DatabaseConfig.from_dict({})
        
        assert config.name == "default"
        assert config.driver == "sqlite"


class TestTypeMapping:
    """Tests for TYPE_MAPPING."""
    
    def test_postgresql_mapping_exists(self):
        """Test PostgreSQL type mapping exists."""
        assert DatabaseType.POSTGRESQL in TYPE_MAPPING
        assert ColumnType.INTEGER in TYPE_MAPPING[DatabaseType.POSTGRESQL]
        assert TYPE_MAPPING[DatabaseType.POSTGRESQL][ColumnType.INTEGER] == "INTEGER"
    
    def test_mysql_mapping_exists(self):
        """Test MySQL type mapping exists."""
        assert DatabaseType.MYSQL in TYPE_MAPPING
        assert ColumnType.INTEGER in TYPE_MAPPING[DatabaseType.MYSQL]
        assert TYPE_MAPPING[DatabaseType.MYSQL][ColumnType.INTEGER] == "INT"
    
    def test_sqlite_mapping_exists(self):
        """Test SQLite type mapping exists."""
        assert DatabaseType.SQLITE in TYPE_MAPPING
        assert ColumnType.INTEGER in TYPE_MAPPING[DatabaseType.SQLITE]
        assert TYPE_MAPPING[DatabaseType.SQLITE][ColumnType.INTEGER] == "INTEGER"


class TestExceptions:
    """Tests for database exceptions."""
    
    def test_database_error_is_exception(self):
        """Test DatabaseError is Exception."""
        assert issubclass(DatabaseError, Exception)
    
    def test_connection_error_is_database_error(self):
        """Test ConnectionError is DatabaseError."""
        assert issubclass(ConnectionError, DatabaseError)
    
    def test_pool_error_is_database_error(self):
        """Test PoolError is DatabaseError."""
        assert issubclass(PoolError, DatabaseError)
    
    def test_query_error_is_database_error(self):
        """Test QueryError is DatabaseError."""
        assert issubclass(QueryError, DatabaseError)
    
    def test_schema_error_is_database_error(self):
        """Test SchemaError is DatabaseError."""
        assert issubclass(SchemaError, DatabaseError)
    
    def test_record_error_is_database_error(self):
        """Test RecordError is DatabaseError."""
        assert issubclass(RecordError, DatabaseError)
    
    def test_transaction_error_is_database_error(self):
        """Test TransactionError is DatabaseError."""
        assert issubclass(TransactionError, DatabaseError)
    
    def test_cache_error_is_database_error(self):
        """Test CacheError is DatabaseError."""
        assert issubclass(CacheError, DatabaseError)
    
    def test_driver_not_found_error_is_database_error(self):
        """Test DriverNotFoundError is DatabaseError."""
        assert issubclass(DriverNotFoundError, DatabaseError)
    
    def test_unsupported_feature_error_is_database_error(self):
        """Test UnsupportedFeatureError is DatabaseError."""
        assert issubclass(UnsupportedFeatureError, DatabaseError)
    
    def test_raise_database_error(self):
        """Test raising DatabaseError."""
        with pytest.raises(DatabaseError):
            raise DatabaseError("Test error")
    
    def test_catch_specific_as_base(self):
        """Test catching specific error as base."""
        with pytest.raises(DatabaseError):
            raise ConnectionError("Connection failed")


class TestDatabaseModule:
    """Tests for DatabaseModule class."""
    
    @pytest.fixture
    def module(self):
        """Create a DatabaseModule instance."""
        return DatabaseModule()
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock module context."""
        context = ModuleContext()
        
        # Mock app
        mock_app = Mock()
        mock_app.register_hook = Mock()
        context._app = mock_app
        
        # Mock services
        mock_config = Mock()
        mock_config.get = Mock(return_value=None)
        
        mock_logger = Mock()
        
        context.services.set("core_config", mock_config)
        context.services.set("core_logger", mock_logger)
        
        return context
    
    def test_module_has_name(self, module):
        """Test module has name attribute."""
        assert module.name == "system_database"
    
    def test_module_provides(self, module):
        """Test module provides list."""
        assert "database_service" in module.provides
    
    @pytest.mark.asyncio
    async def test_module_load_creates_service(self, module, mock_context):
        """Test module load creates database service."""
        await module.load(mock_context)
        
        service = mock_context.services.get("database_service")
        assert service is not None
        assert isinstance(service, DatabaseService)
    
    @pytest.mark.asyncio
    async def test_module_load_registers_types(self, module, mock_context):
        """Test module load registers types."""
        await module.load(mock_context)
        
        types = mock_context.services.get("database_types")
        assert types is not None
        assert "DatabaseConfig" in types
        assert "TableDef" in types
        assert "ColumnDef" in types
    
    @pytest.mark.asyncio
    async def test_module_start_without_configs(self, module, mock_context):
        """Test module start without configs."""
        await module.load(mock_context)
        await module.start(mock_context)
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_module_ready_does_not_raise(self, module, mock_context):
        """Test module ready doesn't raise."""
        await module.load(mock_context)
        await module.ready(mock_context)
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_module_stop_does_not_raise(self, module, mock_context):
        """Test module stop doesn't raise."""
        await module.load(mock_context)
        await module.stop(mock_context)
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_module_full_lifecycle(self, module, mock_context):
        """Test full module lifecycle."""
        await module.load(mock_context)
        await module.start(mock_context)
        await module.ready(mock_context)
        await module.stop(mock_context)
        
        # Service should still be available
        service = mock_context.services.get("database_service")
        assert service is not None


class TestDatabaseService:
    """Tests for DatabaseService class."""
    
    @pytest.fixture
    def service(self):
        """Create a DatabaseService instance."""
        return DatabaseService()
    
    def test_init(self, service):
        """Test initialization."""
        assert service.connections == []
        assert service._logger is None
    
    def test_set_logger(self, service):
        """Test set_logger method."""
        mock_logger = Mock()
        service.set_logger(mock_logger)
        
        assert service._logger == mock_logger
    
    def test_connections_property(self, service):
        """Test connections property returns list of names."""
        assert isinstance(service.connections, list)
    
    @pytest.mark.asyncio
    async def test_close_all_empty(self, service):
        """Test close_all with no connections."""
        await service.close_all()
        # Should not raise
    
    def test_get_connection_nonexistent_raises(self, service):
        """Test get_connection with nonexistent name raises error."""
        with pytest.raises(DatabaseError):
            service.get_connection("nonexistent")
    
    def test_has_connection_false(self, service):
        """Test has_connection returns False for nonexistent."""
        assert service.has_connection("nonexistent") == False
    
    def test_is_connected_false(self, service):
        """Test is_connected returns False when no connections."""
        assert service.is_connected() == False
