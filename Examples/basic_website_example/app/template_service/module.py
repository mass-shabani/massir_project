"""
Template Service Module - Provides Jinja2 template rendering.

This module provides template rendering service with themes and CSS
for other modules to use.
"""
from pathlib import Path
from typing import Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from massir.core.interfaces import IModule


class TemplateService:
    """
    Jinja2 template rendering service.
    
    Provides methods for rendering HTML templates with themes.
    """
    
    def __init__(self, templates_dir: Path, static_dir: Path):
        """
        Initialize template service.
        
        Args:
            templates_dir: Path to templates directory
            static_dir: Path to static files directory
        """
        self.templates_dir = templates_dir
        self.static_dir = static_dir
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            enable_async=True
        )
        
        # Add global functions
        self.env.globals['url_for_static'] = self._url_for_static
    
    def _url_for_static(self, filename: str) -> str:
        """Generate URL for static file."""
        return f"/static/{filename}"
    
    async def render(self, template_name: str, **context) -> str:
        """
        Render a template with context.
        
        Args:
            template_name: Name of template file
            **context: Template context variables
        
        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return await template.render_async(**context)
    
    def render_sync(self, template_name: str, **context) -> str:
        """
        Render a template synchronously.
        
        Args:
            template_name: Name of template file
            **context: Template context variables
        
        Returns:
            Rendered HTML string
        """
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def get_static_path(self) -> Path:
        """Get path to static files directory."""
        return self.static_dir


class TemplateServiceModule(IModule):
    """
    Template service module.
    
    Provides Jinja2 template rendering service for other modules.
    """
    
    name = "template_service"
    provides = ["template_service"]
    
    def __init__(self):
        self.template_service = None
        self.logger = None
        self.config = None
        self.http_api = None
    
    async def load(self, context):
        """Initialize template service."""
        self.logger = context.services.get("core_logger")
        self.config = context.services.get("core_config")
        self.http_api = context.services.get("http_api")
        
        # Get module directory
        module_dir = Path(__file__).parent
        
        # Create template service
        templates_dir = module_dir / "templates"
        static_dir = module_dir / "static"
        
        self.template_service = TemplateService(templates_dir, static_dir)
        
        # Register service
        context.services.set("template_service", self.template_service)
        
        if self.logger:
            self.logger.log("TemplateService module loaded", tag="template")
    
    async def start(self, context):
        """Start template service and mount static files."""
        # Mount static files if http_api is available
        if self.http_api and self.template_service:
            # Get the underlying FastAPI app from HTTPAPI
            app = self.http_api._app
            static_path = self.template_service.get_static_path()
            if static_path.exists():
                # Use StaticFiles from http_api instead of direct import
                app.mount("/static", self.http_api.StaticFiles(directory=str(static_path)), name="static")
                if self.logger:
                    self.logger.log(f"Static files mounted at /static from {static_path}", tag="template")
        
        if self.logger:
            self.logger.log("TemplateService module started", tag="template")
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log("TemplateService module is ready", tag="template")
    
    async def stop(self, context):
        """Stop template service."""
        if self.logger:
            self.logger.log("TemplateService module stopped", tag="template")
