"""
Tables page routes for Database Tables Module.

This module provides routes for:
- Tables listing and management
- Creating and dropping tables
- Viewing table schema and data
"""


def register_routes(http_api, template, tables_service, connection_service, logger):
    """Register tables management routes."""
    
    @http_api.get("/db/tables")
    async def tables_page(request: http_api.Request):
        """Tables management page."""
        if not connection_service.is_connected():
            content = """
            <div class="card">
                <h1>📋 Tables</h1>
                <p class="text-muted">No database connection. Please <a href="/db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Tables", active_menu="db_tables")
            return http_api.HTMLResponse(content=html)
        
        tables = await tables_service.list_tables()
        logs = connection_service.get_logs(20)
        
        # Build tables list HTML
        if tables:
            table_rows = ""
            for table in tables:
                data = await tables_service.get_table_data(table, limit=1)
                row_count = data.get("total", 0)
                table_rows += f"""
                <tr>
                    <td><a href="/db/tables/{table}">{table}</a></td>
                    <td>{row_count}</td>
                    <td class="actions">
                        <a href="/db/data?table={table}" class="btn btn-sm">View Data</a>
                        <a href="/db/tables/{table}/schema" class="btn btn-sm">Schema</a>
                        <a href="/db/tables/{table}/drop" class="btn btn-sm btn-danger">Drop</a>
                    </td>
                </tr>
                """
            
            tables_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Table Name</th>
                            <th>Rows</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
            """
        else:
            tables_html = '<p class="text-muted">No tables found. Create a new table or use sample tables.</p>'
        
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
        
        content = f"""
        <div class="card">
            <h1>📋 Tables</h1>
            <p class="text-muted">Manage database tables. Active: <strong>{connection_service.get_active_connection_name()}</strong></p>
        </div>
        
        <div class="card">
            <div class="card-actions">
                <a href="/db/tables/create" class="btn btn-primary">Create Table</a>
                <a href="/db/tables/create-sample" class="btn">Create Sample Tables</a>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Tables ({len(tables)})</h2>
            {tables_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Operation Logs</h2>
            <div class="log-container">
                {logs_html if logs_html else '<p class="text-muted">No logs yet.</p>'}
            </div>
        </div>
        """
        
        html = template.render(content, title="Tables", active_menu="db_tables")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/db/tables/create")
    async def create_table_form(request: http_api.Request):
        """Create table form page."""
        if not connection_service.is_connected():
            return http_api.RedirectResponse(url="/db/tables", status_code=303)
        
        content = f"""
        <div class="card">
            <h1>Create New Table</h1>
            <p class="text-muted">Define your table structure.</p>
        </div>
        
        <div class="card">
            <form action="/db/tables/create" method="POST" class="form" id="create-table-form">
                <div class="form-group">
                    <label for="table_name">Table Name</label>
                    <input type="text" id="table_name" name="table_name" required>
                </div>
                
                <h3>Columns</h3>
                <div id="columns-container">
                    <div class="column-row" data-index="0">
                        <input type="text" name="col_name_0" placeholder="Column name" required>
                        <select name="col_type_0">
                            <option value="INTEGER">INTEGER</option>
                            <option value="TEXT">TEXT</option>
                            <option value="VARCHAR">VARCHAR</option>
                            <option value="REAL">REAL</option>
                            <option value="FLOAT">FLOAT</option>
                            <option value="BOOLEAN">BOOLEAN</option>
                            <option value="DATE">DATE</option>
                            <option value="DATETIME">DATETIME</option>
                            <option value="BLOB">BLOB</option>
                        </select>
                        <label><input type="checkbox" name="col_pk_0"> PK</label>
                        <label><input type="checkbox" name="col_nn_0"> NOT NULL</label>
                        <label><input type="checkbox" name="col_ai_0"> AUTO</label>
                        <label><input type="checkbox" name="col_uq_0"> UNIQUE</label>
                    </div>
                </div>
                <input type="hidden" name="column_count" id="column-count" value="1">
                <button type="button" onclick="addColumn()" class="btn btn-sm">+ Add Column</button>
                
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Create Table</button>
                    <a href="/db/tables" class="btn">Cancel</a>
                </div>
            </form>
        </div>
        
        <style>
        .column-row {{
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 10px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
        }}
        .column-row input[type="text"] {{
            flex: 1;
        }}
        .column-row select {{
            width: 120px;
        }}
        .column-row label {{
            white-space: nowrap;
            font-size: 0.85em;
        }}
        </style>
        
        <script>
        let columnIndex = 1;
        function addColumn() {{
            const container = document.getElementById('columns-container');
            const row = document.createElement('div');
            row.className = 'column-row';
            row.dataset.index = columnIndex;
            row.innerHTML = `
                <input type="text" name="col_name_${{columnIndex}}" placeholder="Column name" required>
                <select name="col_type_${{columnIndex}}">
                    <option value="INTEGER">INTEGER</option>
                    <option value="TEXT">TEXT</option>
                    <option value="VARCHAR">VARCHAR</option>
                    <option value="REAL">REAL</option>
                    <option value="FLOAT">FLOAT</option>
                    <option value="BOOLEAN">BOOLEAN</option>
                    <option value="DATE">DATE</option>
                    <option value="DATETIME">DATETIME</option>
                    <option value="BLOB">BLOB</option>
                </select>
                <label><input type="checkbox" name="col_pk_${{columnIndex}}"> PK</label>
                <label><input type="checkbox" name="col_nn_${{columnIndex}}"> NOT NULL</label>
                <label><input type="checkbox" name="col_ai_${{columnIndex}}"> AUTO</label>
                <label><input type="checkbox" name="col_uq_${{columnIndex}}"> UNIQUE</label>
                <button type="button" onclick="removeColumn(this)" class="btn btn-sm btn-danger">×</button>
            `;
            container.appendChild(row);
            columnIndex++;
            document.getElementById('column-count').value = columnIndex;
        }}
        
        function removeColumn(btn) {{
            btn.parentElement.remove();
        }}
        </script>
        """
        
        html = template.render(content, title="Create Table", active_menu="db_tables")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/tables/create")
    async def create_table_submit(request: http_api.Request):
        """Handle create table form submission."""
        form = await request.form()
        
        table_name = form.get("table_name")
        column_count = int(form.get("column_count", 0))
        
        columns = []
        for i in range(column_count):
            name = form.get(f"col_name_{i}")
            if name:
                col_type = form.get(f"col_type_{i}", "TEXT")
                is_pk = form.get(f"col_pk_{i}") == "on"
                is_nn = form.get(f"col_nn_{i}") == "on"
                is_ai = form.get(f"col_ai_{i}") == "on"
                is_uq = form.get(f"col_uq_{i}") == "on"
                
                columns.append({
                    "name": name,
                    "type": col_type,
                    "primary_key": is_pk,
                    "nullable": not is_nn,  # NOT NULL checked means nullable=False
                    "auto_increment": is_ai,
                    "unique": is_uq
                })
        
        result = await tables_service.create_table(table_name, columns)
        
        if result["success"]:
            return http_api.RedirectResponse(url="/db/tables", status_code=303)
        else:
            content = f"""
            <div class="card">
                <h1>Error</h1>
                <p class="text-danger">{result['error']}</p>
                <a href="/db/tables/create" class="btn">Try Again</a>
            </div>
            """
            html = template.render(content, title="Error", active_menu="db_tables")
            return http_api.HTMLResponse(content=html, status_code=400)
    
    @http_api.get("/db/tables/create-sample")
    async def create_sample_tables(request: http_api.Request):
        """Create sample tables with test data."""
        if not connection_service.is_connected():
            return http_api.RedirectResponse(url="/db/tables", status_code=303)
        
        result = await tables_service.create_sample_tables()
        
        return http_api.RedirectResponse(url="/db/tables", status_code=303)
    
    @http_api.get("/db/tables/{table_name}")
    async def view_table(request: http_api.Request):
        """View table details."""
        table_name = request.path_params["table_name"]
        
        if not connection_service.is_connected():
            return http_api.RedirectResponse(url="/db/tables", status_code=303)
        
        schema = await tables_service.get_table_schema(table_name)
        data = await tables_service.get_table_data(table_name, limit=50)
        
        # Build schema HTML
        if schema:
            schema_rows = ""
            for col in schema:
                pk_badge = '<span class="badge badge-primary">PK</span>' if col.get("primary_key") else ""
                nn_badge = '<span class="badge">NOT NULL</span>' if not col.get("nullable") else ""
                schema_rows += f"""
                <tr>
                    <td>{col['name']}</td>
                    <td>{col['type']}</td>
                    <td>{pk_badge} {nn_badge}</td>
                    <td>{col.get('default') or '-'}</td>
                </tr>
                """
            
            schema_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Column</th>
                            <th>Type</th>
                            <th>Constraints</th>
                            <th>Default</th>
                        </tr>
                    </thead>
                    <tbody>{schema_rows}</tbody>
                </table>
            </div>
            """
        else:
            schema_html = '<p class="text-muted">Could not retrieve schema.</p>'
        
        # Build data preview HTML
        if data.get("rows"):
            headers = list(data["rows"][0].keys())
            rows = []
            for row in data["rows"][:20]:
                row_data = {h: str(row.get(h, ""))[:50] for h in headers}
                rows.append(row_data)
            
            data_html = template.render_table(headers=headers, rows=rows)
        else:
            data_html = '<p class="text-muted">No data in table.</p>'
        
        content = f"""
        <div class="card">
            <h1>Table: {table_name}</h1>
            <p class="text-muted">{data.get('total', 0)} total rows</p>
        </div>
        
        <div class="card">
            <div class="card-actions">
                <a href="/db/data?table={table_name}" class="btn btn-primary">Edit Data</a>
                <a href="/db/tables" class="btn">Back to Tables</a>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Schema</h2>
            {schema_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Data Preview (first 20 rows)</h2>
            {data_html}
        </div>
        """
        
        html = template.render(content, title=f"Table: {table_name}", active_menu="db_tables")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/db/tables/{table_name}/schema")
    async def view_table_schema(request: http_api.Request):
        """View table schema (redirect to table view)."""
        table_name = request.path_params["table_name"]
        return http_api.RedirectResponse(url=f"/db/tables/{table_name}", status_code=303)
    
    @http_api.get("/db/tables/{table_name}/drop")
    async def drop_table_confirm(request: http_api.Request):
        """Drop table confirmation page."""
        table_name = request.path_params["table_name"]
        
        content = f"""
        <div class="card">
            <h1>Drop Table: {table_name}</h1>
            <p class="text-danger">Are you sure you want to drop this table? This action cannot be undone.</p>
        </div>
        
        <div class="card">
            <form action="/db/tables/{table_name}/drop" method="POST">
                <button type="submit" class="btn btn-danger">Yes, Drop Table</button>
                <a href="/db/tables" class="btn">Cancel</a>
            </form>
        </div>
        """
        
        html = template.render(content, title="Drop Table", active_menu="db_tables")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/tables/{table_name}/drop")
    async def drop_table_submit(request: http_api.Request):
        """Handle drop table form submission."""
        table_name = request.path_params["table_name"]
        
        result = await tables_service.drop_table(table_name)
        
        return http_api.RedirectResponse(url="/db/tables", status_code=303)
