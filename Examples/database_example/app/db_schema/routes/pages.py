"""
Schema page routes for Database Schema Module.

This module provides routes for:
- Index management
- Foreign key management
"""


def register_routes(http_api, template, schema_service, connection_service, logger):
    """Register schema management routes."""
    
    @http_api.get("/db/schema")
    async def schema_page(request: http_api.Request):
        """Schema management page."""
        if not connection_service.is_connected():
            content = """
            <div class="card">
                <h1>🔧 Schema</h1>
                <p class="text-muted">No database connection. Please <a href="/db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Schema", active_menu="db_schema")
            return http_api.HTMLResponse(content=html)
        
        tables = await schema_service.list_tables()
        indexes = await schema_service.list_indexes()
        foreign_keys = await schema_service.list_foreign_keys()
        logs = connection_service.get_logs(20)
        
        # Build indexes HTML
        if indexes:
            index_rows = ""
            for idx in indexes:
                index_rows += f"""
                <tr>
                    <td>{idx.get('name', '-')}</td>
                    <td>{idx.get('table', '-')}</td>
                    <td>{', '.join(idx.get('columns', []))}</td>
                    <td>{'✓' if idx.get('unique') else '-'}</td>
                    <td class="actions">
                        <button onclick="dropIndex('{idx.get('name')}', '{idx.get('table')}')" class="btn btn-sm btn-danger">Drop</button>
                    </td>
                </tr>
                """
            indexes_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead><tr><th>Name</th><th>Table</th><th>Columns</th><th>Unique</th><th>Actions</th></tr></thead>
                    <tbody>{index_rows}</tbody>
                </table>
            </div>
            """
        else:
            indexes_html = '<p class="text-muted">No indexes found.</p>'
        
        # Build foreign keys HTML
        if foreign_keys:
            fk_rows = ""
            for fk in foreign_keys:
                fk_rows += f"""
                <tr>
                    <td>{fk.get('name', '-')}</td>
                    <td>{fk.get('table', '-')}</td>
                    <td>{', '.join(fk.get('columns', []))}</td>
                    <td>{fk.get('ref_table', '-')}</td>
                    <td>{', '.join(fk.get('ref_columns', []))}</td>
                    <td class="actions">
                        <button onclick="dropForeignKey('{fk.get('name')}', '{fk.get('table')}')" class="btn btn-sm btn-danger">Drop</button>
                    </td>
                </tr>
                """
            fk_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead><tr><th>Name</th><th>Table</th><th>Columns</th><th>Ref Table</th><th>Ref Columns</th><th>Actions</th></tr></thead>
                    <tbody>{fk_rows}</tbody>
                </table>
            </div>
            """
        else:
            fk_html = '<p class="text-muted">No foreign keys found.</p>'
        
        # Build logs HTML
        logs_html = ""
        for log in logs:
            level_class = f"log-{log['level'].lower()}"
            logs_html += f"""
            <div class="log-entry {level_class}">
                <span class="log-time">{log['timestamp']}</span>
                <span class="log-level">[{log['level']}]</span>
                <span class="log-message">{log['message']}</span>
            </div>
            """
        
        # Build table options for forms
        table_options = ""
        for table in tables:
            table_options += f'<option value="{table}">{table}</option>'
        
        content = f"""
        <div class="card">
            <h1>🔧 Schema</h1>
            <p class="text-muted">Manage indexes and foreign keys. Active: <strong>{connection_service.get_active_connection_name()}</strong></p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Indexes</h2>
            {indexes_html}
            <div class="card-actions">
                <button onclick="showCreateIndexForm()" class="btn btn-primary">Create Index</button>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Foreign Keys</h2>
            {fk_html}
            <div class="card-actions">
                <button onclick="showCreateFKForm()" class="btn btn-primary">Add Foreign Key</button>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Operation Logs</h2>
            <div class="log-container">
                {logs_html if logs_html else '<p class="text-muted">No logs yet.</p>'}
            </div>
        </div>
        
        <!-- Create Index Modal -->
        <div id="index-modal" class="modal" style="display:none;">
            <div class="modal-content">
                <h3>Create Index</h3>
                <form id="index-form" class="form">
                    <div class="form-group">
                        <label>Table</label>
                        <select id="index-table" name="table">{table_options}</select>
                    </div>
                    <div class="form-group">
                        <label>Index Name</label>
                        <input type="text" id="index-name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label>Columns (comma-separated)</label>
                        <input type="text" id="index-columns" name="columns" required>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="index-unique" name="unique"> Unique</label>
                    </div>
                    <div class="form-actions">
                        <button type="button" onclick="createIndex()" class="btn btn-primary">Create</button>
                        <button type="button" onclick="closeModals()" class="btn">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- Create FK Modal -->
        <div id="fk-modal" class="modal" style="display:none;">
            <div class="modal-content">
                <h3>Add Foreign Key</h3>
                <form id="fk-form" class="form">
                    <div class="form-group">
                        <label>Table</label>
                        <select id="fk-table" name="table">{table_options}</select>
                    </div>
                    <div class="form-group">
                        <label>Columns (comma-separated)</label>
                        <input type="text" id="fk-columns" name="columns" required>
                    </div>
                    <div class="form-group">
                        <label>Referenced Table</label>
                        <select id="fk-ref-table" name="ref_table">{table_options}</select>
                    </div>
                    <div class="form-group">
                        <label>Referenced Columns (comma-separated)</label>
                        <input type="text" id="fk-ref-columns" name="ref_columns" required>
                    </div>
                    <div class="form-actions">
                        <button type="button" onclick="createFK()" class="btn btn-primary">Add</button>
                        <button type="button" onclick="closeModals()" class="btn">Cancel</button>
                    </div>
                </form>
            </div>
        </div>
        
        <style>
        .modal {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-content {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            max-width: 500px;
            width: 90%;
        }}
        </style>
        
        <script>
        function showCreateIndexForm() {{
            document.getElementById('index-modal').style.display = 'flex';
        }}
        
        function showCreateFKForm() {{
            document.getElementById('fk-modal').style.display = 'flex';
        }}
        
        function closeModals() {{
            document.getElementById('index-modal').style.display = 'none';
            document.getElementById('fk-modal').style.display = 'none';
        }}
        
        async function createIndex() {{
            const table = document.getElementById('index-table').value;
            const name = document.getElementById('index-name').value;
            const columns = document.getElementById('index-columns').value.split(',').map(c => c.trim());
            const unique = document.getElementById('index-unique').checked;
            
            try {{
                const response = await fetch('/db/api/schema/index/create', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ table_name: table, index_name: name, columns, unique }})
                }});
                
                const result = await response.json();
                if (result.success) {{
                    closeModals();
                    location.reload();
                }} else {{
                    alert(result.message);
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}
        
        async function dropIndex(name, table) {{
            if (!confirm(`Drop index ${{name}}?`)) return;
            
            try {{
                const response = await fetch('/db/api/schema/index/drop', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ index_name: name, table_name: table }})
                }});
                
                const result = await response.json();
                if (result.success) {{
                    location.reload();
                }} else {{
                    alert(result.message);
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}
        
        async function createFK() {{
            const table = document.getElementById('fk-table').value;
            const columns = document.getElementById('fk-columns').value.split(',').map(c => c.trim());
            const ref_table = document.getElementById('fk-ref-table').value;
            const ref_columns = document.getElementById('fk-ref-columns').value.split(',').map(c => c.trim());
            
            try {{
                const response = await fetch('/db/api/schema/fk/create', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ table_name: table, columns, ref_table, ref_columns }})
                }});
                
                const result = await response.json();
                if (result.success) {{
                    closeModals();
                    location.reload();
                }} else {{
                    alert(result.message);
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}
        
        async function dropForeignKey(name, table) {{
            if (!confirm(`Drop foreign key ${{name}}?`)) return;
            
            try {{
                const response = await fetch('/db/api/schema/fk/drop', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ fk_name: name, table_name: table }})
                }});
                
                const result = await response.json();
                if (result.success) {{
                    location.reload();
                }} else {{
                    alert(result.message);
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}
        </script>
        """
        
        html = template.render(content, title="Schema", active_menu="db_schema")
        return http_api.HTMLResponse(content=html)
    
    # API Routes
    @http_api.post("/db/api/schema/index/create")
    async def api_create_index(request: http_api.Request):
        """Create an index."""
        data = await request.json()
        result = await schema_service.create_index(
            table_name=data.get("table_name"),
            index_name=data.get("index_name"),
            columns=data.get("columns", []),
            unique=data.get("unique", False)
        )
        return result
    
    @http_api.post("/db/api/schema/index/drop")
    async def api_drop_index(request: http_api.Request):
        """Drop an index."""
        data = await request.json()
        result = await schema_service.drop_index(
            index_name=data.get("index_name"),
            table_name=data.get("table_name")
        )
        return result
    
    @http_api.post("/db/api/schema/fk/create")
    async def api_create_fk(request: http_api.Request):
        """Add a foreign key."""
        data = await request.json()
        result = await schema_service.add_foreign_key(
            table_name=data.get("table_name"),
            columns=data.get("columns", []),
            ref_table=data.get("ref_table"),
            ref_columns=data.get("ref_columns", [])
        )
        return result
    
    @http_api.post("/db/api/schema/fk/drop")
    async def api_drop_fk(request: http_api.Request):
        """Drop a foreign key."""
        data = await request.json()
        result = await schema_service.drop_foreign_key(
            fk_name=data.get("fk_name"),
            table_name=data.get("table_name")
        )
        return result
