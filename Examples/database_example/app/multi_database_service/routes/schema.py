"""
Schema management routes for Multi-Database Service.

This module provides routes for:
- Index management (create, list, drop)
- Foreign key management
- Advanced schema operations
"""


def register_schema_routes(http_api, template, db_manager, logger):
    """Register schema management routes."""
    
    @http_api.get("/multi-db/schema")
    async def schema_page(request: http_api.Request):
        """Schema management page."""
        if not db_manager.is_connected():
            content = """
            <div class="card">
                <h1>Schema Management</h1>
                <p class="text-muted">No database connection. Please <a href="/multi-db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Schema Management", active_menu="multi_db_schema")
            return http_api.HTMLResponse(content=html)
        
        tables = await db_manager.list_tables()
        indexes = await db_manager.list_indexes()
        foreign_keys = await db_manager.list_foreign_keys()
        
        # Build indexes HTML
        if indexes:
            idx_rows = ""
            for idx in indexes:
                unique_badge = '<span class="badge badge-primary">UNIQUE</span>' if idx.get("unique") else ""
                idx_rows += f"""
                <tr>
                    <td>{idx['name']}</td>
                    <td>{idx['table']}</td>
                    <td>{', '.join(idx['columns'])}</td>
                    <td>{unique_badge}</td>
                    <td class="actions">
                        <button onclick="dropIndex('{idx['name']}', '{idx['table']}')" class="btn btn-sm btn-danger">Drop</button>
                    </td>
                </tr>
                """
            
            indexes_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Index Name</th>
                            <th>Table</th>
                            <th>Columns</th>
                            <th>Type</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>{idx_rows}</tbody>
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
                    <td>{fk['name']}</td>
                    <td>{fk['table']}.{', '.join(fk['columns'])}</td>
                    <td>{fk['ref_table']}.{', '.join(fk['ref_columns'])}</td>
                    <td>{fk['on_delete']}</td>
                    <td class="actions">
                        <button onclick="dropForeignKey('{fk['name']}', '{fk['table']}')" class="btn btn-sm btn-danger">Drop</button>
                    </td>
                </tr>
                """
            
            fks_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Constraint Name</th>
                            <th>From</th>
                            <th>References</th>
                            <th>On Delete</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>{fk_rows}</tbody>
                </table>
            </div>
            """
        else:
            fks_html = '<p class="text-muted">No foreign keys found.</p>'
        
        # Build table options for dropdowns
        table_options = ""
        for table in tables:
            table_options += f'<option value="{table}">{table}</option>'
        
        content = f"""
        <div class="card">
            <h1>🔧 Schema Management</h1>
            <p class="text-muted">Manage indexes and foreign keys.</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="card">
            <h2 class="card-title">Create Index</h2>
            <form id="create-index-form" class="form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="idx-table">Table</label>
                        <select id="idx-table" name="table" required>
                            <option value="">-- Select Table --</option>
                            {table_options}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="idx-name">Index Name</label>
                        <input type="text" id="idx-name" name="name" placeholder="idx_column_name" required>
                    </div>
                </div>
                <div class="form-group">
                    <label for="idx-columns">Columns (comma-separated)</label>
                    <input type="text" id="idx-columns" name="columns" placeholder="column1, column2" required>
                </div>
                <div class="form-group">
                    <label><input type="checkbox" id="idx-unique" name="unique"> Unique Index</label>
                </div>
                <div class="form-actions">
                    <button type="button" onclick="createIndex()" class="btn btn-primary">Create Index</button>
                </div>
            </form>
        </div>
        
        <div class="card">
            <h2 class="card-title">Create Foreign Key</h2>
            <form id="create-fk-form" class="form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="fk-table">From Table</label>
                        <select id="fk-table" name="table" required>
                            <option value="">-- Select Table --</option>
                            {table_options}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="fk-columns">From Columns</label>
                        <input type="text" id="fk-columns" name="columns" placeholder="column1" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="fk-ref-table">References Table</label>
                        <select id="fk-ref-table" name="ref_table" required>
                            <option value="">-- Select Table --</option>
                            {table_options}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="fk-ref-columns">References Columns</label>
                        <input type="text" id="fk-ref-columns" name="ref_columns" placeholder="id" required>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="fk-on-delete">On Delete</label>
                        <select id="fk-on-delete" name="on_delete">
                            <option value="RESTRICT">RESTRICT</option>
                            <option value="CASCADE">CASCADE</option>
                            <option value="SET NULL">SET NULL</option>
                            <option value="NO ACTION">NO ACTION</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="fk-on-update">On Update</label>
                        <select id="fk-on-update" name="on_update">
                            <option value="RESTRICT">RESTRICT</option>
                            <option value="CASCADE">CASCADE</option>
                            <option value="SET NULL">SET NULL</option>
                            <option value="NO ACTION">NO ACTION</option>
                        </select>
                    </div>
                </div>
                <div class="form-actions">
                    <button type="button" onclick="createForeignKey()" class="btn btn-primary">Create Foreign Key</button>
                </div>
            </form>
        </div>
        
        <div class="card">
            <h2 class="card-title">Indexes</h2>
            <div id="indexes-list">{indexes_html}</div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Foreign Keys</h2>
            <div id="fks-list">{fks_html}</div>
        </div>
        
        <script>
        async function createIndex() {{
            const table = document.getElementById('idx-table').value;
            const name = document.getElementById('idx-name').value;
            const columnsStr = document.getElementById('idx-columns').value;
            const unique = document.getElementById('idx-unique').checked;
            
            if (!table || !name || !columnsStr) {{
                showMessage('Please fill all required fields', 'warning');
                return;
            }}
            
            const columns = columnsStr.split(',').map(c => c.trim()).filter(c => c);
            
            try {{
                const response = await fetch('/multi-db/api/schema/index/create', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ table, name, columns, unique }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    location.reload();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function dropIndex(name, table) {{
            if (!confirm(`Are you sure you want to drop index '${{name}}'?`)) return;
            
            try {{
                const response = await fetch(`/multi-db/api/schema/index/${{encodeURIComponent(name)}}/drop?table=${{encodeURIComponent(table)}}`, {{
                    method: 'POST'
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    location.reload();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function createForeignKey() {{
            const table = document.getElementById('fk-table').value;
            const columnsStr = document.getElementById('fk-columns').value;
            const refTable = document.getElementById('fk-ref-table').value;
            const refColumnsStr = document.getElementById('fk-ref-columns').value;
            const onDelete = document.getElementById('fk-on-delete').value;
            const onUpdate = document.getElementById('fk-on-update').value;
            
            if (!table || !columnsStr || !refTable || !refColumnsStr) {{
                showMessage('Please fill all required fields', 'warning');
                return;
            }}
            
            const columns = columnsStr.split(',').map(c => c.trim()).filter(c => c);
            const refColumns = refColumnsStr.split(',').map(c => c.trim()).filter(c => c);
            
            try {{
                const response = await fetch('/multi-db/api/schema/foreign-key/create', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ table, columns, ref_table: refTable, ref_columns: refColumns, on_delete: onDelete, on_update: onUpdate }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    location.reload();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function dropForeignKey(name, table) {{
            if (!confirm(`Are you sure you want to drop foreign key '${{name}}'?`)) return;
            
            try {{
                const response = await fetch(`/multi-db/api/schema/foreign-key/${{encodeURIComponent(name)}}/drop?table=${{encodeURIComponent(table)}}`, {{
                    method: 'POST'
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    location.reload();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        function showMessage(message, type) {{
            const container = document.getElementById('message-container');
            const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-error' : type === 'warning' ? 'alert-warning' : 'alert-info';
            container.innerHTML = `<div class="alert ${{alertClass}}">${{message}}</div>`;
            
            setTimeout(() => {{
                container.innerHTML = '';
            }}, 5000);
        }}
        </script>
        """
        
        html = template.render(content, title="Schema Management", active_menu="multi_db_schema")
        return http_api.HTMLResponse(content=html)
    
    # ==================== API Routes ====================
    
    @http_api.post("/multi-db/api/schema/index/create")
    async def api_index_create(request: http_api.Request):
        """Create an index."""
        data = await request.json()
        result = await db_manager.create_index(
            table_name=data["table"],
            index_name=data["name"],
            columns=data["columns"],
            unique=data.get("unique", False)
        )
        return result
    
    @http_api.post("/multi-db/api/schema/index/{name}/drop")
    async def api_index_drop(request: http_api.Request):
        """Drop an index."""
        name = request.path_params["name"]
        table = request.query_params.get("table")
        result = await db_manager.drop_index(name, table)
        return result
    
    @http_api.post("/multi-db/api/schema/foreign-key/create")
    async def api_fk_create(request: http_api.Request):
        """Create a foreign key."""
        data = await request.json()
        result = await db_manager.add_foreign_key(
            table_name=data["table"],
            columns=data["columns"],
            ref_table=data["ref_table"],
            ref_columns=data["ref_columns"],
            on_delete=data.get("on_delete", "RESTRICT"),
            on_update=data.get("on_update", "RESTRICT")
        )
        return result
    
    @http_api.post("/multi-db/api/schema/foreign-key/{name}/drop")
    async def api_fk_drop(request: http_api.Request):
        """Drop a foreign key."""
        name = request.path_params["name"]
        table = request.query_params.get("table")
        result = await db_manager.drop_foreign_key(name, table)
        return result
    
    @http_api.get("/multi-db/api/schema/indexes")
    async def api_list_indexes(request: http_api.Request):
        """List indexes."""
        table = request.query_params.get("table")
        indexes = await db_manager.list_indexes(table)
        return {"indexes": indexes}
    
    @http_api.get("/multi-db/api/schema/foreign-keys")
    async def api_list_fks(request: http_api.Request):
        """List foreign keys."""
        table = request.query_params.get("table")
        fks = await db_manager.list_foreign_keys(table)
        return {"foreign_keys": fks}
    
    if logger:
        logger.log("Schema routes registered", tag="multi_db")
