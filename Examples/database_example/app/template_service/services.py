"""
Template Service - Menu and template management.

This module provides services for:
- Menu registration and management with grouping support
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
    group: Optional[str] = None  # Group name: 'sqlite', 'postgresql', 'mysql', None for main
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
            "group": self.group,
            "children": [c.to_dict() for c in self.children]
        }


class MenuManager:
    """Manages menu items for the application with grouping support."""
    
    def __init__(self):
        self._items: Dict[str, MenuItem] = {}
        self._groups: Dict[str, Dict[str, Any]] = {
            # Define database groups with their styling
            'sqlite': {'label': 'SQLite', 'icon': '🗄️', 'class': 'sqlite', 'order': 10},
            'postgresql': {'label': 'PostgreSQL', 'icon': '🐘', 'class': 'postgresql', 'order': 20},
            'mysql': {'label': 'MySQL', 'icon': '🐬', 'class': 'mysql', 'order': 30},
        }
    
    def register_group(self, group_id: str, label: str, icon: str = "", css_class: str = "", order: int = 100):
        """Register a new menu group."""
        self._groups[group_id] = {
            'label': label,
            'icon': icon,
            'class': css_class or group_id,
            'order': order
        }
    
    def register_menu(self, id: str, label: str, url: str, 
                      icon: str = "", order: int = 100, parent_id: Optional[str] = None,
                      group: Optional[str] = None):
        """Register a menu item.
        
        Args:
            id: Unique identifier for the menu item
            label: Display label
            url: Link URL
            icon: Optional icon (emoji or icon class)
            order: Sort order within its group
            parent_id: Parent menu item ID for nested menus
            group: Group name ('sqlite', 'postgresql', 'mysql', or None for main menu)
        """
        item = MenuItem(
            id=id,
            label=label,
            url=url,
            icon=icon,
            order=order,
            parent_id=parent_id,
            group=group
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
    
    def get_grouped_menu(self) -> Dict[str, List[dict]]:
        """Get menu items grouped by their group attribute."""
        grouped = {
            'main': [],  # Items without a group
        }
        
        # Initialize groups
        for group_id in self._groups:
            grouped[group_id] = []
        
        # Categorize items
        for item in self._items.values():
            if item.parent_id is None:  # Only root items
                item_dict = item.to_dict()
                item_dict['children'] = [c.to_dict() for c in self._get_children(item.id)]
                
                if item.group and item.group in grouped:
                    grouped[item.group].append(item_dict)
                else:
                    grouped['main'].append(item_dict)
        
        # Sort items within each group
        for group_id in grouped:
            grouped[group_id].sort(key=lambda x: x['order'])
        
        return grouped
    
    def get_groups(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered groups."""
        return self._groups.copy()


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
                    {self._render_menu(active_menu)}
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
    
    def _render_menu(self, active_menu: str) -> str:
        """Render menu HTML with grouping support."""
        grouped_menu = self.menu_manager.get_grouped_menu()
        groups = self.menu_manager.get_groups()
        
        items = []
        
        # Render main menu items first (no group)
        for item in grouped_menu.get('main', []):
            items.append(self._render_menu_item(item, active_menu))
        
        # Render grouped items as dropdowns
        for group_id, group_info in sorted(groups.items(), key=lambda x: x[1]['order']):
            group_items = grouped_menu.get(group_id, [])
            if group_items:
                items.append(self._render_group_dropdown(group_id, group_info, group_items, active_menu))
        
        return "".join(items)
    
    def _render_menu_item(self, item: dict, active_menu: str) -> str:
        """Render a single menu item."""
        active_class = "active" if item['id'] == active_menu else ""
        icon = f"<span class='icon'>{item['icon']}</span>" if item['icon'] else ""
        
        if item.get('children'):
            children_html = self._render_submenu(item['children'], active_menu)
            return f"""
            <li class="menu-group {active_class}">
                <a href="{item['url']}">{icon}{item['label']}</a>
                <ul class="submenu">{children_html}</ul>
            </li>"""
        else:
            return f"""
            <li class="{active_class}">
                <a href="{item['url']}">{icon}{item['label']}</a>
            </li>"""
    
    def _render_group_dropdown(self, group_id: str, group_info: dict, items: List[dict], active_menu: str) -> str:
        """Render a group as a dropdown menu."""
        icon = f"<span class='icon'>{group_info['icon']}</span>" if group_info.get('icon') else ""
        
        # Check if any item in group is active
        is_active = any(item['id'] == active_menu for item in items)
        active_class = "active" if is_active else ""
        
        # Render group header
        header_class = f"menu-group-header {group_info.get('class', '')}"
        
        # Render items
        items_html = f'<li class="{header_class}">{group_info["label"]}</li>'
        for item in items:
            item_active = "active" if item['id'] == active_menu else ""
            item_icon = f"<span class='icon'>{item['icon']}</span>" if item.get('icon') else ""
            items_html += f"""
            <li class="{item_active}">
                <a href="{item['url']}">{item_icon}{item['label']}</a>
            </li>"""
        
        return f"""
        <li class="menu-group {active_class}">
            <a href="#">{icon}{group_info['label']}</a>
            <ul class="submenu">{items_html}</ul>
        </li>"""
    
    def _render_submenu(self, children: List[dict], active_menu: str) -> str:
        """Render submenu items."""
        items = []
        for child in children:
            active_class = "active" if child['id'] == active_menu else ""
            icon = f"<span class='icon'>{child['icon']}</span>" if child.get('icon') else ""
            items.append(f"""
            <li class="{active_class}">
                <a href="{child['url']}">{icon}{child['label']}</a>
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
        """Render a data table with improved styling."""
        if not rows:
            return f'<div class="table-empty"><p class="text-muted">{empty_message}</p></div>'
        
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
