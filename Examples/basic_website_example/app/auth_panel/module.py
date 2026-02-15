"""
Auth Panel Module - Login and user panel.

This module provides login and user panel functionality.
Login with admin/12345 for testing.
"""
from massir.core.interfaces import IModule


# Simple user database for demo
USERS = {
    "admin": {
        "password": "12345",
        "name": "Administrator",
        "email": "admin@example.com",
        "role": "admin"
    }
}


class AuthPanelModule(IModule):
    """
    Auth panel module.
    
    Provides login and user panel pages.
    """
    
    name = "auth_panel"
    
    def __init__(self):
        self.http_api = None
        self.template_service = None
        self.logger = None
    
    async def load(self, context):
        """Get APIs from services."""
        self.http_api = context.services.get("http_api")
        self.template_service = context.services.get("template_service")
        self.logger = context.services.get("core_logger")
        
        if self.logger:
            self.logger.log("AuthPanel module loaded", tag="auth")
    
    async def start(self, context):
        """Register auth routes and menu items."""
        
        # Register menu items with template service
        if self.template_service:
            # Login link - only visible when NOT logged in
            self.template_service.register_menu_item(
                label="Login",
                url="/login",
                order=900,  # Appears near the end
                require_no_auth=True,
                module_name=self.name
            )
            
            # Panel link - only visible when logged in
            self.template_service.register_menu_item(
                label="Panel",
                url="/panel",
                order=500,
                require_auth=True,
                module_name=self.name
            )
            
            # Logout link - only visible when logged in
            self.template_service.register_menu_item(
                label="Logout",
                url="/logout",
                order=999,  # Appears last
                require_auth=True,
                module_name=self.name
            )
        
        # GET /login - Login page
        @self.http_api.get("/login", response_class=self.http_api.HTMLResponse)
        async def login_page(request: self.http_api.Request):
            """Login page."""
            # Check if already logged in
            current_user = request.session.get("user") if hasattr(request, "session") else None
            if current_user:
                return self.http_api.RedirectResponse(url="/panel", status_code=302)
            
            html = await self.template_service.render(
                "login.html",
                current_user=None
            )
            return self.http_api.HTMLResponse(content=html)
        
        # POST /login - Handle login
        @self.http_api.post("/login", response_class=self.http_api.HTMLResponse)
        async def login_post(request: self.http_api.Request):
            """Handle login form submission."""
            form_data = await request.form()
            username = form_data.get("username", "")
            password = form_data.get("password", "")
            
            # Check credentials
            user = USERS.get(username)
            if user and user["password"] == password:
                # Set session
                if hasattr(request, "session"):
                    request.session["user"] = {
                        "username": username,
                        "name": user["name"],
                        "email": user["email"],
                        "role": user["role"]
                    }
                
                if self.logger:
                    self.logger.log(f"User '{username}' logged in", tag="auth")
                
                return self.http_api.RedirectResponse(url="/panel", status_code=302)
            else:
                if self.logger:
                    self.logger.log(f"Failed login attempt for '{username}'", level="WARNING", tag="auth")
                
                html = await self.template_service.render(
                    "login.html",
                    current_user=None,
                    error=True
                )
                return self.http_api.HTMLResponse(content=html)
        
        # GET /logout - Logout
        @self.http_api.get("/logout")
        async def logout(request: self.http_api.Request):
            """Logout user."""
            if hasattr(request, "session"):
                user = request.session.get("user")
                if user and self.logger:
                    self.logger.log(f"User '{user.get('username')}' logged out", tag="auth")
                request.session.clear()
            
            return self.http_api.RedirectResponse(url="/", status_code=302)
        
        # GET /panel - User panel
        @self.http_api.get("/panel", response_class=self.http_api.HTMLResponse)
        async def panel(request: self.http_api.Request):
            """User panel page."""
            current_user = request.session.get("user") if hasattr(request, "session") else None
            
            if not current_user:
                return self.http_api.RedirectResponse(url="/login", status_code=302)
            
            html = await self.template_service.render(
                "panel.html",
                current_user=current_user
            )
            return self.http_api.HTMLResponse(content=html)
        
        if self.logger:
            self.logger.log("Auth panel routes registered", tag="auth")
    
    async def stop(self, context):
        """Cleanup resources and unregister menu items."""
        # Unregister menu items when module stops
        if self.template_service:
            self.template_service.unregister_menu_item(module_name=self.name)
        
        if self.logger:
            self.logger.log("AuthPanel module stopped", tag="auth")
