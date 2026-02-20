"""
Data editor page routes for Multi-Database Service.

This module provides routes for:
- Data listing and pagination
- Adding, editing, and deleting records
- Dynamic form generation based on table schema
"""


def register_data_routes(http_api, template, db_manager, logger):
    """Register data editor routes."""
    
    @http_api.get("/multi-db/data")
    async def data_editor_page(request: http_api.Request):
        """Data editor page with table selection."""
        if not db_manager.is_connected():
            content = """
            <div class="card">
                <h1>✏️ Data Editor</h1>
                <p class="text-muted">No database connection. Please <a href="/multi-db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Data Editor", active_menu="multi_db_data")
            return http_api.HTMLResponse(content=html)
        
        tables = await db_manager.list_tables()
        selected_table = request.query_params.get("table")
        
        # Build table selector HTML
        table_options = ""
        for table in tables:
            selected = "selected" if table == selected_table else ""
            table_options += f'<option value="{table}" {selected}>{table}</option>'
        
        table_selector_html = f"""
        <form method="GET" class="form-inline">
            <select name="table" onchange="this.form.submit()">
                <option value="">-- Select Table --</option>
                {table_options}
            </select>
        </form>
        """
        
        # Build data table HTML
        data_html = ""
        schema_html = ""
        
        if selected_table:
            schema = await db_manager.get_table_schema(selected_table)
            page = int(request.query_params.get("page", 1))
            limit = 20
            offset = (page - 1) * limit
            
            data = await db_manager.get_table_data(selected_table, limit=limit, offset=offset)
            
            if data.get("rows"):
                headers = list(data["rows"][0].keys())
                rows = []
                for row in data["rows"]:
                    row_data = {}
                    for h in headers:
                        val = row.get(h, "")
                        # Truncate long values
                        row_data[h] = str(val)[:100] if val else ""
                    
                    # Add action buttons
                    pk_col = None
                    for col in schema:
                        if col.get("primary_key"):
                            pk_col = col["name"]
                            break
                    
                    if pk_col and pk_col in row:
                        pk_val = row[pk_col]
                        row_data["Actions"] = f'''
                        <div class="action-icons">
                            <a href="/multi-db/data/{selected_table}/edit?pk={pk_val}" class="action-icon edit" title="Edit">✏️</a>
                            <a href="/multi-db/data/{selected_table}/delete?pk={pk_val}" class="action-icon delete" title="Delete">🗑️</a>
                        </div>
                        '''
                    rows.append(row_data)
                
                headers.append("Actions")
                data_html = template.render_table(headers=headers, rows=rows)
                
                # Pagination
                total = data.get("total", 0)
                total_pages = (total + limit - 1) // limit
                
                if total_pages > 1:
                    pagination = '<div class="pagination">'
                    for p in range(1, total_pages + 1):
                        if p == page:
                            pagination += f'<span class="page-current">{p}</span>'
                        else:
                            pagination += f'<a href="/multi-db/data?table={selected_table}&page={p}" class="page-link">{p}</a>'
                    pagination += '</div>'
                    data_html += pagination
            else:
                if data.get("error"):
                    data_html = f'<p class="text-danger">Error: {data["error"]}</p>'
                else:
                    data_html = '<p class="text-muted">No data in this table.</p>'
            
            # Show schema info
            if schema:
                schema_info = ", ".join([f"{col['name']} ({col['type']})" for col in schema])
                schema_html = f'<p class="text-muted"><small>Columns: {schema_info}</small></p>'
        
        content = f"""
        <div class="card">
            <h1>✏️ Data Editor</h1>
            <p class="text-muted">Edit table data. Active: <strong>{db_manager.get_active_connection_name()}</strong></p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Select Table</h2>
            {table_selector_html}
            {schema_html}
        </div>
        """
        
        if selected_table:
            content += f"""
            <div class="card">
                <div class="card-actions">
                    <a href="/multi-db/data/{selected_table}/add" class="btn btn-primary">Add Record</a>
                </div>
            </div>
            
            <div class="card">
                <h2 class="card-title">Data: {selected_table}</h2>
                {data_html}
            </div>
            """
        
        html = template.render(content, title="Data Editor", active_menu="multi_db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/multi-db/data/{table_name}/add")
    async def add_record_form(request: http_api.Request):
        """Add record form page."""
        table_name = request.path_params["table_name"]
        
        if not db_manager.is_connected():
            return http_api.RedirectResponse(url="/multi-db/data", status_code=303)
        
        schema = await db_manager.get_table_schema(table_name)
        
        # Build form fields based on schema
        fields_html = ""
        for col in schema:
            if col.get("auto_increment"):
                continue  # Skip auto-increment columns
            
            col_name = col["name"]
            col_type = col["type"].upper()
            required = "required" if not col.get("nullable") and not col.get("primary_key") else ""
            
            # Determine input type
            if "INT" in col_type:
                input_type = "number"
            elif "REAL" in col_type or "FLOAT" in col_type or "DOUBLE" in col_type:
                input_type = "number"
                input_type += ' step="0.01"'
            else:
                input_type = "text"
            
            fields_html += f"""
            <div class="form-group">
                <label for="{col_name}">{col_name}</label>
                <input type="{input_type}" id="{col_name}" name="{col_name}" {required}>
                <small class="text-muted">{col_type}</small>
            </div>
            """
        
        content = f"""
        <div class="card">
            <h1>Add Record to {table_name}</h1>
        </div>
        
        <div class="card">
            <form action="/multi-db/data/{table_name}/add" method="POST" class="form">
                {fields_html}
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Add Record</button>
                    <a href="/multi-db/data?table={table_name}" class="btn">Cancel</a>
                </div>
            </form>
        </div>
        """
        
        html = template.render(content, title="Add Record", active_menu="multi_db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/multi-db/data/{table_name}/add")
    async def add_record_submit(request: http_api.Request):
        """Handle add record form submission."""
        table_name = request.path_params["table_name"]
        form = await request.form()
        
        # Get schema to know which fields to include
        schema = await db_manager.get_table_schema(table_name)
        
        data = {}
        for col in schema:
            col_name = col["name"]
            if col.get("auto_increment"):
                continue
            
            value = form.get(col_name)
            if value:
                # Convert type if needed
                col_type = col["type"].upper()
                if "INT" in col_type:
                    data[col_name] = int(value)
                elif "REAL" in col_type or "FLOAT" in col_type:
                    data[col_name] = float(value)
                else:
                    data[col_name] = value
        
        result = await db_manager.insert_record(table_name, data)
        
        if result["success"]:
            return http_api.RedirectResponse(url=f"/multi-db/data?table={table_name}", status_code=303)
        else:
            content = f"""
            <div class="card">
                <h1>Error</h1>
                <p class="text-danger">{result.get('error', 'Unknown error')}</p>
                <a href="/multi-db/data/{table_name}/add" class="btn">Try Again</a>
            </div>
            """
            html = template.render(content, title="Error", active_menu="multi_db_data")
            return http_api.HTMLResponse(content=html, status_code=400)
    
    @http_api.get("/multi-db/data/{table_name}/edit")
    async def edit_record_form(request: http_api.Request):
        """Edit record form page."""
        table_name = request.path_params["table_name"]
        pk_value = request.query_params.get("pk")
        
        if not db_manager.is_connected():
            return http_api.RedirectResponse(url="/multi-db/data", status_code=303)
        
        schema = await db_manager.get_table_schema(table_name)
        
        # Find primary key column
        pk_col = None
        for col in schema:
            if col.get("primary_key"):
                pk_col = col["name"]
                break
        
        if not pk_col:
            content = """
            <div class="card">
                <h1>Error</h1>
                <p class="text-danger">Cannot edit: No primary key defined for this table.</p>
            </div>
            """
            html = template.render(content, title="Error", active_menu="multi_db_data")
            return http_api.HTMLResponse(content=html, status_code=400)
        
        # Get current record
        data = await db_manager.get_table_data(table_name, limit=100)
        record = None
        for row in data.get("rows", []):
            if str(row.get(pk_col)) == str(pk_value):
                record = row
                break
        
        if not record:
            content = """
            <div class="card">
                <h1>Not Found</h1>
                <p class="text-muted">Record not found.</p>
            </div>
            """
            html = template.render(content, title="Not Found", active_menu="multi_db_data")
            return http_api.HTMLResponse(content=html, status_code=404)
        
        # Build form fields
        fields_html = f'<input type="hidden" name="pk_col" value="{pk_col}">'
        fields_html += f'<input type="hidden" name="pk_val" value="{pk_value}">'
        
        for col in schema:
            col_name = col["name"]
            col_type = col["type"].upper()
            current_value = record.get(col_name, "")
            required = "required" if not col.get("nullable") else ""
            
            if "INT" in col_type:
                input_type = "number"
            elif "REAL" in col_type or "FLOAT" in col_type:
                input_type = 'number step="0.01"'
            else:
                input_type = "text"
            
            readonly = "readonly" if col.get("primary_key") else ""
            
            fields_html += f"""
            <div class="form-group">
                <label for="{col_name}">{col_name}</label>
                <input type="{input_type}" id="{col_name}" name="{col_name}" value="{current_value}" {required} {readonly}>
                <small class="text-muted">{col_type}</small>
            </div>
            """
        
        content = f"""
        <div class="card">
            <h1>Edit Record in {table_name}</h1>
            <p class="text-muted">Primary Key: {pk_col} = {pk_value}</p>
        </div>
        
        <div class="card">
            <form action="/multi-db/data/{table_name}/edit" method="POST" class="form">
                {fields_html}
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Update Record</button>
                    <a href="/multi-db/data?table={table_name}" class="btn">Cancel</a>
                </div>
            </form>
        </div>
        """
        
        html = template.render(content, title="Edit Record", active_menu="multi_db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/multi-db/data/{table_name}/edit")
    async def edit_record_submit(request: http_api.Request):
        """Handle edit record form submission."""
        table_name = request.path_params["table_name"]
        form = await request.form()
        
        pk_col = form.get("pk_col")
        pk_val = form.get("pk_val")
        
        schema = await db_manager.get_table_schema(table_name)
        
        data = {}
        for col in schema:
            col_name = col["name"]
            if col.get("primary_key"):
                continue
            
            value = form.get(col_name)
            if value:
                col_type = col["type"].upper()
                if "INT" in col_type:
                    data[col_name] = int(value)
                elif "REAL" in col_type or "FLOAT" in col_type:
                    data[col_name] = float(value)
                else:
                    data[col_name] = value
        
        # Determine pk value type
        for col in schema:
            if col["name"] == pk_col:
                if "INT" in col["type"].upper():
                    pk_val = int(pk_val)
                break
        
        result = await db_manager.update_record(table_name, data, {pk_col: pk_val})
        
        if result["success"]:
            return http_api.RedirectResponse(url=f"/multi-db/data?table={table_name}", status_code=303)
        else:
            return http_api.RedirectResponse(
                url=f"/multi-db/data?table={table_name}&error={result.get('error', 'Unknown error')}",
                status_code=303
            )
    
    @http_api.get("/multi-db/data/{table_name}/delete")
    async def delete_record_confirm(request: http_api.Request):
        """Delete record confirmation page."""
        table_name = request.path_params["table_name"]
        pk_value = request.query_params.get("pk")
        
        content = f"""
        <div class="card">
            <h1>Delete Record</h1>
            <p class="text-danger">Are you sure you want to delete this record?</p>
            <p><strong>Table:</strong> {table_name}</p>
            <p><strong>ID:</strong> {pk_value}</p>
        </div>
        
        <div class="card">
            <form action="/multi-db/data/{table_name}/delete" method="POST">
                <input type="hidden" name="pk" value="{pk_value}">
                <button type="submit" class="btn btn-danger">Yes, Delete</button>
                <a href="/multi-db/data?table={table_name}" class="btn">Cancel</a>
            </form>
        </div>
        """
        
        html = template.render(content, title="Delete Record", active_menu="multi_db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/multi-db/data/{table_name}/delete")
    async def delete_record_submit(request: http_api.Request):
        """Handle delete record form submission."""
        table_name = request.path_params["table_name"]
        form = await request.form()
        
        pk_value = form.get("pk")
        
        schema = await db_manager.get_table_schema(table_name)
        
        # Find primary key column
        pk_col = None
        for col in schema:
            if col.get("primary_key"):
                pk_col = col["name"]
                break
        
        if pk_col:
            # Convert pk value type if needed
            for col in schema:
                if col["name"] == pk_col:
                    if "INT" in col["type"].upper():
                        pk_value = int(pk_value)
                    break
            
            result = await db_manager.delete_record(table_name, {pk_col: pk_value})
        
        return http_api.RedirectResponse(url=f"/multi-db/data?table={table_name}", status_code=303)
    
    if logger:
        logger.log("Data routes registered", tag="multi_db")
