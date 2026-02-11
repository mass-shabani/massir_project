"""
Users API Module - Example of using http_api.

This module demonstrates how to create REST API endpoints
using the http_api abstraction without importing FastAPI.
"""
from typing import List, Dict, Optional
from massir.core.interfaces import IModule


class UsersAPIModule(IModule):
    """
    Users API module demonstrating http_api usage.
    
    Provides CRUD operations for users without importing FastAPI.
    """
    
    name = "users_api"
    
    # In-memory user storage
    _users: Dict[int, Dict] = {}
    _next_id: int = 1
    
    def __init__(self):
        self.http_api = None
        self.logger = None
    
    async def load(self, context):
        """Get HTTP API from services."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        
        if self.logger:
            self.logger.log("UsersAPI module loaded", tag="users")
    
    async def start(self, context):
        """Register user management routes."""
        
        # GET /users - Get all users
        @self.http_api.get("/users", tags=["users"], summary="Get all users")
        async def get_users():
            """Retrieve all users."""
            return list(self._users.values())
        
        # GET /users/{id} - Get user by ID
        @self.http_api.get("/users/{user_id}", tags=["users"], summary="Get user by ID")
        async def get_user(user_id: int):
            """Retrieve a specific user by ID."""
            user = self._users.get(user_id)
            if user is None:
                return self.http_api.error(
                    message="User not found",
                    status_code=404,
                    code="USER_NOT_FOUND"
                )
            return user
        
        # POST /users - Create new user
        @self.http_api.post("/users", tags=["users"], summary="Create new user")
        async def create_user(user_data: dict):
            """Create a new user."""
            user_id = self._next_id
            self._next_id += 1
            
            user = {
                "id": user_id,
                "name": user_data.get("name", ""),
                "email": user_data.get("email", "")
            }
            
            self._users[user_id] = user
            
            if self.logger:
                self.logger.log(f"Created user: {user['name']}", tag="users")
            
            return self.http_api.response(
                data=user,
                status_code=201
            )
        
        # PUT /users/{id} - Update user
        @self.http_api.put("/users/{user_id}", tags=["users"], summary="Update user")
        async def update_user(user_id: int, user_data: dict):
            """Update an existing user."""
            user = self._users.get(user_id)
            if user is None:
                return self.http_api.error(
                    message="User not found",
                    status_code=404,
                    code="USER_NOT_FOUND"
                )
            
            if "name" in user_data:
                user["name"] = user_data["name"]
            if "email" in user_data:
                user["email"] = user_data["email"]
            
            if self.logger:
                self.logger.log(f"Updated user: {user['name']}", tag="users")
            
            return user
        
        # DELETE /users/{id} - Delete user
        @self.http_api.delete("/users/{user_id}", tags=["users"], summary="Delete user")
        async def delete_user(user_id: int):
            """Delete a user."""
            user = self._users.get(user_id)
            if user is None:
                return self.http_api.error(
                    message="User not found",
                    status_code=404,
                    code="USER_NOT_FOUND"
                )
            
            del self._users[user_id]
            
            if self.logger:
                self.logger.log(f"Deleted user: {user['name']}", tag="users")
            
            return self.http_api.response(status_code=204)
        
        if self.logger:
            self.logger.log("Users API routes registered", tag="users")
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log("UsersAPI module is ready", tag="users")
    
    async def stop(self, context):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("UsersAPI module stopped", tag="users")
