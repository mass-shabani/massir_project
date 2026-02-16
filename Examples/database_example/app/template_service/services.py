"""
Template Service - Menu and template management.

This module provides services for:
- Menu registration and management
- Template rendering with unified theme
- Static file serving
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class MenuItem:
    """Represents a menu item."""
    id: str
    label: str
    url: str
    icon: str = ""
    order: int = 100
    parent_id: Optional[str] = None
    children: List['MenuItem'] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "id": self.id,
            "label": self.label,
            "url": self.url,
            "icon": self.icon,
            "order": self.order,
            "parent_id": self.parent_id,
            "children": [c.to_dict() for c in self.children]
        }


class MenuManager:
    """Manages menu items for the application."""
    
    def __init__(self):
        self._items: Dict[str, MenuItem] = {}
    
    def register_menu(self, id: str, label: str, url: str, 
                      icon: str = "", order: int = 100, parent_id: Optional[str] = None):
        """Register a menu item."""
        item = MenuItem(
            id=id,
            label=label,
            url=url,
            icon=icon,
            order=order,
            parent_id=parent_id
        )
        self._items[id] = item
    
    def unregister_menu(self, id: str):
        """Remove a menu item by ID."""
        if id in self._items:
            del self._items[id]
    
    def get_menu(self) -> List[MenuItem]:
        """Get all menu items sorted by order."""
        # Get root items (no parent)
        root_items = [item for item in self._items.values() if item.parent_id is None]
        
        # Build tree
        for item in root_items:
            item.children = self._get_children(item.id)
        
        # Sort by order
        root_items.sort(key=lambda x: x.order)
        return root_items
    
    def _get_children(self, parent_id: str) -> List[MenuItem]:
        """Get children of a menu item."""
        children = [item for item in self._items.values() if item.parent_id == parent_id]
        for child in children:
            child.children = self._get_children(child.id)
        children.sort(key=lambda x: x.order)
        return children
    
    def get_menu_dict(self) -> List[dict]:
        """Get menu as list of dictionaries."""
        return [item.to_dict() for item in self.get_menu()]


class TemplateRenderer:
    """Renders templates with unified theme."""
    
    def __init__(self, menu_manager: MenuManager):
        self.menu_manager = menu_manager
        self._site_name = "Database Example"
        self._site_description = "Massir Framework Database Example"
    
    def set_site_info(self, name: str, description: str = ""):
        """Set site information."""
        self._site_name = name
        self._site_description = description
    
    def render(self, content: str, title: str = "", active_menu: str = "", 
               additional_css: str = "", additional_js: str = "") -> str:
        """Render a page with the base template."""
        menu = self.menu_manager.get_menu_dict()
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {self._site_name}</title>
    <link rel="stylesheet" href="/static/template/css/style.css">
    {additional_css}
</head>
<body>
    <header class="header">
        <div class="header-container">
            <a href="/" class="logo">{self._site_name}</a>
            <nav class="nav">
                <ul class="nav-list">
                    {self._render_menu(menu, active_menu)}
                </ul>
            </nav>
        </div>
    </header>
    
    <main class="main">
        <div class="container">
            {content}
        </div>
    </main>
    
    <footer class="footer">
        <div class="container">
            <p>&copy; 2024 {self._site_name}. Powered by Massir Framework.</p>
        </div>
    </footer>
    
    {additional_js}
</body>
</html>"""
    
    def _render_menu(self, menu: List[dict], active_menu: str) -> str:
        """Render menu HTML."""
        if not menu:
            return ""
        
        items = []
        for item in menu:
            active_class = "active" if item['id'] == active_menu else ""
            icon = f"<span class='icon'>{item['icon']}</span>" if item['icon'] else ""
            children = self._render_menu(item['children'], active_menu)
            
            if children:
                items.append(f"""
                <li class="has-children {active_class}">
                    <a href="{item['url']}">{icon}{item['label']}</a>
                    <ul class="submenu">{children}</ul>
                </li>""")
            else:
                items.append(f"""
                <li class="{active_class}">
                    <a href="{item['url']}">{icon}{item['label']}</a>
                </li>""")
        
        return "".join(items)
    
    def render_card(self, title: str, content: str, actions: str = "") -> str:
        """Render a card component."""
        return f"""
        <div class="card">
            {f'<h2 class="card-title">{title}</h2>' if title else ''}
            <div class="card-content">{content}</div>
            {f'<div class="card-actions">{actions}</div>' if actions else ''}
        </div>"""
    
    def render_table(self, headers: List[str], rows: List[dict], 
                     empty_message: str = "No data available.") -> str:
        """Render a data table."""
        if not rows:
            return f'<p class="text-muted">{empty_message}</p>'
        
        header_html = "".join(f"<th>{col}</th>" for col in headers)
        
        rows_html = []
        for row in rows:
            cells = ""
            for col in headers:
                value = row.get(col, '')
                cells += f"<td>{value}</td>"
            rows_html.append(f"<tr>{cells}</tr>")
        
        return f"""
        <div class="table-wrapper">
            <table>
                <thead><tr>{header_html}</tr></thead>
                <tbody>{"".join(rows_html)}</tbody>
            </table>
        </div>"""
    
    def render_form(self, action: str, fields: List[dict], submit_text: str = "Submit",
                    method: str = "POST") -> str:
        """Render a form."""
        fields_html = []
        for field in fields:
            field_type = field.get('type', 'text')
            field_name = field.get('name', '')
            field_label = field.get('label', field_name)
            field_value = field.get('value', '')
            field_required = 'required' if field.get('required', False) else ''
            field_checked = 'checked' if field.get('checked', False) else ''
            
            if field_type == 'textarea':
                fields_html.append(f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <textarea id="{field_name}" name="{field_name}" {field_required}>{field_value}</textarea>
                </div>""")
            elif field_type == 'select':
                options = "".join(
                    f'<option value="{opt["value"]}" {"selected" if opt["value"] == field_value else ""}>{opt["label"]}</option>'
                    for opt in field.get('options', [])
                )
                fields_html.append(f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <select id="{field_name}" name="{field_name}" {field_required}>{options}</select>
                </div>""")
            elif field_type == 'checkbox':
                fields_html.append(f"""
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="{field_name}" name="{field_name}" {field_checked}> {field_label}
                    </label>
                </div>""")
            else:
                fields_html.append(f"""
                <div class="form-group">
                    <label for="{field_name}">{field_label}</label>
                    <input type="{field_type}" id="{field_name}" name="{field_name}" value="{field_value}" {field_required}>
                </div>""")
        
        return f"""
        <form action="{action}" method="{method}" class="form">
            {"".join(fields_html)}
            <div class="form-actions">
                <button type="submit" class="btn btn-primary">{submit_text}</button>
            </div>
        </form>"""
