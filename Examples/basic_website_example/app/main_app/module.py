"""
Main App Module - Main website pages.

This module provides the main website pages: index, about, contact.
"""
from pathlib import Path
from massir.core.interfaces import IModule


class MainAppModule(IModule):
    """
    Main app module.
    
    Provides main website pages using template_service.
    """
    
    name = "main_app"
    
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
            self.logger.log("MainApp module loaded", tag="main_app")
    
    async def start(self, context):
        """Register main website routes and menu items."""
        
        # Register menu items with template service
        if self.template_service:
            # Home - first item, always visible
            self.template_service.register_menu_item(
                label="Home",
                url="/",
                order=10,  # First item
                module_name=self.name
            )
            
            # About page
            self.template_service.register_menu_item(
                label="About",
                url="/about",
                order=100,
                module_name=self.name
            )
            
            # Contact page
            self.template_service.register_menu_item(
                label="Contact",
                url="/contact",
                order=200,
                module_name=self.name
            )
        
        # GET / - Home page
        @self.http_api.get("/", response_class=self.http_api.HTMLResponse)
        async def index(request: self.http_api.Request):
            """Home page."""
            current_user = request.session.get("user") if hasattr(request, "session") else None
            html = await self.template_service.render(
                "index.html",
                current_user=current_user
            )
            return self.http_api.HTMLResponse(content=html)
        
        # GET /about - About page
        @self.http_api.get("/about", response_class=self.http_api.HTMLResponse)
        async def about(request: self.http_api.Request):
            """About page."""
            current_user = request.session.get("user") if hasattr(request, "session") else None
            html = await self.template_service.render(
                "about.html",
                current_user=current_user
            )
            return self.http_api.HTMLResponse(content=html)
        
        # GET /contact - Contact page
        @self.http_api.get("/contact", response_class=self.http_api.HTMLResponse)
        async def contact(request: self.http_api.Request):
            """Contact page."""
            current_user = request.session.get("user") if hasattr(request, "session") else None
            html = await self.template_service.render(
                "contact.html",
                current_user=current_user
            )
            return self.http_api.HTMLResponse(content=html)
        
        # POST /contact - Handle contact form
        @self.http_api.post("/contact", response_class=self.http_api.HTMLResponse)
        async def contact_post(request: self.http_api.Request):
            """Handle contact form submission."""
            form_data = await request.form()
            name = form_data.get("name", "")
            email = form_data.get("email", "")
            message = form_data.get("message", "")
            
            if self.logger:
                self.logger.log(
                    f"Contact form submitted: name={name}, email={email}",
                    tag="main_app"
                )
            
            current_user = request.session.get("user") if hasattr(request, "session") else None
            html = await self.template_service.render(
                "contact.html",
                current_user=current_user,
                success=True,
                submitted_name=name
            )
            return self.http_api.HTMLResponse(content=html)
        
        if self.logger:
            self.logger.log("Main app routes registered", tag="main_app")
    
    async def stop(self, context):
        """Cleanup resources and unregister menu items."""
        # Unregister menu items when module stops
        if self.template_service:
            self.template_service.unregister_menu_item(module_name=self.name)
        
        if self.logger:
            self.logger.log("MainApp module stopped", tag="main_app")
