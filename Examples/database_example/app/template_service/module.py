"""
Template Service Module - Unified theme and template management.

This module provides:
- Menu registration and management
- Template rendering with unified theme
- Static file serving
"""
from massir.core.interfaces import IModule, ModuleContext
from .services import MenuManager, TemplateRenderer


class TemplateServiceModule(IModule):
    """
    Template service module providing unified theme for web modules.
    """
    
    name = "template_service"
    provides = ["template_service", "menu_manager"]
    
    def __init__(self):
        self.http_api = None
        self.logger = None
        self.menu_manager = None
        self.renderer = None
    
    async def load(self, context: ModuleContext):
        """Get services and initialize."""
        self.http_api = context.services.get("http_api")
        self.logger = context.services.get("core_logger")
        
        # Initialize services
        self.menu_manager = MenuManager()
        self.renderer = TemplateRenderer(self.menu_manager)
        
        # Register services
        context.services.set("template_service", self)
        context.services.set("menu_manager", self.menu_manager)
        
        if self.logger:
            self.logger.log("TemplateService module loaded", tag="template")
    
    async def start(self, context: ModuleContext):
        """Register routes and static files."""
        self._register_static_routes()
        
        if self.logger:
            self.logger.log("TemplateService module started", tag="template")
    
    def _register_static_routes(self):
        """Register static file routes."""
        import os
        from pathlib import Path
        
        static_dir = Path(__file__).parent / "static"
        
        @self.http_api.get("/static/template/css/{filename}")
        async def serve_css(request: self.http_api.Request):
            """Serve CSS files."""
            filename = request.path_params["filename"]
            file_path = static_dir / "css" / filename
            
            if not file_path.exists():
                return self.http_api.PlainTextResponse(content="Not Found", status_code=404)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.http_api.PlainTextResponse(
                content=content,
                media_type="text/css"
            )
    
    def register_menu(self, id: str, label: str, url: str,
                      icon: str = "", order: int = 100, parent_id: str = None):
        """Register a menu item."""
        self.menu_manager.register_menu(id, label, url, icon, order, parent_id)
    
    def unregister_menu(self, id: str):
        """Remove a menu item by ID."""
        self.menu_manager.unregister_menu(id)
    
    def get_menu(self) -> list:
        """Get all menu items."""
        return self.menu_manager.get_menu_dict()
    
    def render(self, content: str, title: str = "", active_menu: str = "",
               additional_css: str = "", additional_js: str = "") -> str:
        """Render a page with the base template."""
        return self.renderer.render(content, title, active_menu, additional_css, additional_js)
    
    def render_card(self, title: str, content: str, actions: str = "") -> str:
        """Render a card component."""
        return self.renderer.render_card(title, content, actions)
    
    def render_table(self, headers: list, rows: list, empty_message: str = "No data available.") -> str:
        """Render a data table."""
        return self.renderer.render_table(headers, rows, empty_message)
    
    def render_form(self, action: str, fields: list, submit_text: str = "Submit",
                    method: str = "POST") -> str:
        """Render a form."""
        return self.renderer.render_form(action, fields, submit_text, method)
    
    async def ready(self, context: ModuleContext):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log("TemplateService module is ready", tag="template")
    
    async def stop(self, context: ModuleContext):
        """Cleanup resources."""
        if self.logger:
            self.logger.log("TemplateService module stopped", tag="template")
