"""
Template Service Module - Provides Jinja2 template rendering.

This module provides template rendering service with themes and CSS
for other modules to use. Also provides menu registration for dynamic navigation.
"""
from pathlib import Path
from typing import Optional, Dict, Any, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from massir.core.interfaces import IModule


class MenuItem:
    """
    Represents a menu item in the navigation.
    """
    
    def __init__(
        self,
        label: str,
        url: str,
        order: int = 100,
        require_auth: bool = False,
        require_no_auth: bool = False,
        module_name: str = ""
    ):
        """
        Initialize a menu item.
        
        Args:
            label: Display text for the menu item
            url: URL path for the link
            order: Order priority (lower = appears first)
            require_auth: Only show when user is logged in
            require_no_auth: Only show when user is NOT logged in
            module_name: Name of the module that registered this item
        """
        self.label = label
        self.url = url
        self.order = order
        self.require_auth = require_auth
        self.require_no_auth = require_no_auth
        self.module_name = module_name
    
    def is_visible(self, current_user: Optional[dict] = None) -> bool:
        """
        Check if this menu item should be visible.
        
        Args:
            current_user: Current logged-in user (None if not logged in)
        
        Returns:
            True if the item should be visible
        """
        if self.require_auth and not current_user:
            return False
        if self.require_no_auth and current_user:
            return False
        return True
    
    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "label": self.label,
            "url": self.url,
            "order": self.order,
            "require_auth": self.require_auth,
            "require_no_auth": self.require_no_auth,
            "module_name": self.module_name
        }


class MenuRegistry:
    """
    Registry for dynamic menu items.
    
    Modules can register their menu items here, and they will be
    automatically included in the navigation. When a module is disabled,
    its menu items won't appear.
    """
    
    def __init__(self):
        """Initialize the menu registry."""
        self._items: Dict[str, MenuItem] = {}
    
    def register(
        self,
        label: str,
        url: str,
        order: int = 100,
        require_auth: bool = False,
        require_no_auth: bool = False,
        module_name: str = ""
    ) -> str:
        """
        Register a menu item.
        
        Args:
            label: Display text for the menu item
            url: URL path for the link
            order: Order priority (lower = appears first)
            require_auth: Only show when user is logged in
            require_no_auth: Only show when user is NOT logged in
            module_name: Name of the module registering this item
        
        Returns:
            Unique key for the registered item
        """
        key = f"{module_name}:{url}" if module_name else url
        item = MenuItem(
            label=label,
            url=url,
            order=order,
            require_auth=require_auth,
            require_no_auth=require_no_auth,
            module_name=module_name
        )
        self._items[key] = item
        return key
    
    def unregister(self, key: str = None, module_name: str = None):
        """
        Unregister menu item(s).
        
        Args:
            key: Specific item key to unregister
            module_name: Unregister all items from this module
        """
        if key:
            self._items.pop(key, None)
        elif module_name:
            # Remove all items from this module
            keys_to_remove = [
                k for k, item in self._items.items()
                if item.module_name == module_name
            ]
            for k in keys_to_remove:
                self._items.pop(k, None)
    
    def get_items(self, current_user: Optional[dict] = None) -> List[dict]:
        """
        Get all visible menu items sorted by order.
        
        Args:
            current_user: Current logged-in user (None if not logged in)
        
        Returns:
            List of visible menu item dictionaries, sorted by order
        """
        visible_items = [
            item for item in self._items.values()
            if item.is_visible(current_user)
        ]
        # Sort by order, then by label for consistent ordering
        sorted_items = sorted(visible_items, key=lambda x: (x.order, x.label))
        return [item.to_dict() for item in sorted_items]
    
    def get_all_items(self) -> List[MenuItem]:
        """Get all registered menu items (for debugging)."""
        return list(self._items.values())


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
        self.menu_registry = MenuRegistry()
        
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
        # Add menu items to context
        current_user = context.get('current_user')
        context['menu_items'] = self.menu_registry.get_items(current_user)
        
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
        # Add menu items to context
        current_user = context.get('current_user')
        context['menu_items'] = self.menu_registry.get_items(current_user)
        
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    def get_static_path(self) -> Path:
        """Get path to static files directory."""
        return self.static_dir
    
    def register_menu_item(
        self,
        label: str,
        url: str,
        order: int = 100,
        require_auth: bool = False,
        require_no_auth: bool = False,
        module_name: str = ""
    ) -> str:
        """
        Register a menu item for the navigation.
        
        Args:
            label: Display text for the menu item
            url: URL path for the link
            order: Order priority (lower = appears first)
            require_auth: Only show when user is logged in
            require_no_auth: Only show when user is NOT logged in
            module_name: Name of the module registering this item
        
        Returns:
            Unique key for the registered item
        """
        return self.menu_registry.register(
            label=label,
            url=url,
            order=order,
            require_auth=require_auth,
            require_no_auth=require_no_auth,
            module_name=module_name
        )
    
    def unregister_menu_item(self, key: str = None, module_name: str = None):
        """
        Unregister menu item(s).
        
        Args:
            key: Specific item key to unregister
            module_name: Unregister all items from this module
        """
        self.menu_registry.unregister(key=key, module_name=module_name)


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
