"""
User Manager Module - Demonstrates database operations.

This module shows how to:
- Create tables using the schema manager
- Insert, update, delete records
- Query data with find_one, find_many
- Use transactions
- Execute raw SQL
"""
from massir.core.interfaces import IModule
from massir.modules.system_database import TableDef, ColumnDef, ColumnType


class UserManagerModule(IModule):
    """
    User manager module demonstrating database operations.
    """
    
    name = "user_manager"
    provides = ["user_manager"]
    
    def __init__(self):
        self.db = None
        self.http_api = None
        self.logger = None
    
    async def load(self, context):
        """Get services."""
        self.db = context.services.get("database_service")
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        
        if self.logger:
            self.logger.log("UserManager module loaded", tag="user_manager")
    
    async def start(self, context):
        """Initialize database schema and register routes."""
        # Create users table if not exists
        await self._create_users_table()
        
        # Register API routes
        self._register_routes()
        
        if self.logger:
            self.logger.log("UserManager module started", tag="user_manager")
    
    async def _create_users_table(self):
        """Create the users table."""
        # Check if table exists
        if await self.db.default.table_exists("users"):
            if self.logger:
                self.logger.log("Users table already exists", tag="user_manager")
            return
        
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
        result = await self.db.default.schema.create_table(users_table)
        
        if result.success:
            if self.logger:
                self.logger.log("Users table created successfully", tag="user_manager")
        else:
            if self.logger:
                self.logger.log(
                    f"Failed to create users table: {result.error}",
                    level="ERROR",
                    tag="user_manager"
                )
    
    def _register_routes(self):
        """Register HTTP API routes."""
        
        @self.http_api.get("/users")
        async def list_users(request: self.http_api.Request):
            """List all users."""
            users = await self.db.find_many(
                "users",
                columns=["id", "username", "email", "full_name", "is_active", "created_at"],
                order_by=["id"]
            )
            return self.http_api.JSONResponse(content={"users": users})
        
        @self.http_api.get("/users/{user_id:int}")
        async def get_user(request: self.http_api.Request):
            """Get a single user by ID."""
            user_id = request.path_params["user_id"]
            user = await self.db.find_one(
                "users",
                where={"id": user_id},
                columns=["id", "username", "email", "full_name", "is_active", "created_at"]
            )
            if user:
                return self.http_api.JSONResponse(content={"user": user})
            return self.http_api.JSONResponse(
                content={"error": "User not found"},
                status_code=404
            )
        
        @self.http_api.post("/users")
        async def create_user(request: self.http_api.Request):
            """Create a new user."""
            data = await request.json()
            
            # Insert user
            result = await self.db.insert(
                "users",
                {
                    "username": data.get("username"),
                    "email": data.get("email"),
                    "password_hash": data.get("password", "hashed_password_placeholder"),
                    "full_name": data.get("full_name"),
                    "is_active": True
                },
                returning=["id", "username", "email"]
            )
            
            if result.success:
                return self.http_api.JSONResponse(
                    content={"user": result.rows[0] if result.rows else data},
                    status_code=201
                )
            return self.http_api.JSONResponse(
                content={"error": result.error},
                status_code=400
            )
        
        @self.http_api.put("/users/{user_id:int}")
        async def update_user(request: self.http_api.Request):
            """Update a user."""
            user_id = request.path_params["user_id"]
            data = await request.json()
            
            # Check if user exists
            if not await self.db.exists("users", {"id": user_id}):
                return self.http_api.JSONResponse(
                    content={"error": "User not found"},
                    status_code=404
                )
            
            # Update user
            update_data = {}
            if "email" in data:
                update_data["email"] = data["email"]
            if "full_name" in data:
                update_data["full_name"] = data["full_name"]
            if "is_active" in data:
                update_data["is_active"] = data["is_active"]
            
            if update_data:
                result = await self.db.update(
                    "users",
                    update_data,
                    where={"id": user_id}
                )
                if result.success:
                    return self.http_api.JSONResponse(
                        content={"message": "User updated", "affected_rows": result.affected_rows}
                    )
                return self.http_api.JSONResponse(
                    content={"error": result.error},
                    status_code=400
                )
            
            return self.http_api.JSONResponse(content={"message": "No changes"})
        
        @self.http_api.delete("/users/{user_id:int}")
        async def delete_user(request: self.http_api.Request):
            """Delete a user."""
            user_id = request.path_params["user_id"]
            
            result = await self.db.delete("users", where={"id": user_id})
            
            if result.success and result.affected_rows > 0:
                return self.http_api.JSONResponse(
                    content={"message": "User deleted", "affected_rows": result.affected_rows}
                )
            return self.http_api.JSONResponse(
                content={"error": "User not found"},
                status_code=404
            )
        
        @self.http_api.post("/users/batch")
        async def create_users_batch(request: self.http_api.Request):
            """Create multiple users in a batch."""
            data = await request.json()
            users = data.get("users", [])
            
            if not users:
                return self.http_api.JSONResponse(
                    content={"error": "No users provided"},
                    status_code=400
                )
            
            # Prepare batch data
            batch_data = [
                {
                    "username": u.get("username"),
                    "email": u.get("email"),
                    "password_hash": "hashed_placeholder",
                    "full_name": u.get("full_name"),
                    "is_active": True
                }
                for u in users
            ]
            
            result = await self.db.insert_many("users", batch_data)
            
            if result.success:
                return self.http_api.JSONResponse(
                    content={"message": "Users created", "count": result.affected_rows},
                    status_code=201
                )
            return self.http_api.JSONResponse(
                content={"error": result.error},
                status_code=400
            )
        
        @self.http_api.get("/users/count")
        async def count_users(request: self.http_api.Request):
            """Count total users."""
            count = await self.db.count("users")
            return self.http_api.JSONResponse(content={"count": count})
        
        @self.http_api.post("/users/transaction")
        async def transaction_example(request: self.http_api.Request):
            """Example of using transactions."""
            data = await request.json()
            
            # Use transaction context manager
            async with self.db.default.begin_transaction() as tx:
                # Insert first user
                result1 = await self.db.insert(
                    "users",
                    {
                        "username": data.get("username1"),
                        "email": data.get("email1"),
                        "password_hash": "hash1",
                        "is_active": True
                    }
                )
                
                if not result1.success:
                    raise Exception(f"Failed to insert first user: {result1.error}")
                
                # Insert second user
                result2 = await self.db.insert(
                    "users",
                    {
                        "username": data.get("username2"),
                        "email": data.get("email2"),
                        "password_hash": "hash2",
                        "is_active": True
                    }
                )
                
                if not result2.success:
                    raise Exception(f"Failed to insert second user: {result2.error}")
                
                # If we get here, both inserts succeeded and will be committed
                # If any exception is raised, both will be rolled back
            
            return self.http_api.JSONResponse(
                content={"message": "Transaction completed successfully"},
                status_code=201
            )
        
        @self.http_api.get("/db/stats")
        async def database_stats(request: self.http_api.Request):
            """Get database statistics."""
            stats = {
                "connections": self.db.connections,
                "cache_stats": self.db.cache_stats,
                "pool_size": self.db.default.pool_size,
                "pool_idle": self.db.default.pool_idle
            }
            return self.http_api.JSONResponse(content=stats)
        
        if self.logger:
            self.logger.log("User API routes registered", tag="user_manager")
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log("UserManager module is ready", tag="user_manager")
    
    async def stop(self, context):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("UserManager module stopped", tag="user_manager")