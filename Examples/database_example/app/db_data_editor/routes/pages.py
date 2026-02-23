"""
Data editor page routes for Database Data Editor Module.

This module provides routes for:
- Viewing and editing table data
- Adding new records
- Updating existing records
- Deleting records
"""


def register_routes(http_api, template, data_service, connection_service, logger):
    """Register data editor routes."""
    
    @http_api.get("/db/data")
    async def data_editor_page(request: http_api.Request):
        """Data editor page."""
        if not connection_service.is_connected():
            content = """
            <div class="card">
                <h1>✏️ Data Editor</h1>
                <p class="text-muted">No database connection. Please <a href="/db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Data Editor", active_menu="db_data")
            return http_api.HTMLResponse(content=html)
        
        tables = await data_service.list_tables()
        selected_table = request.query_params.get("table", "")
        
        # Build table selection dropdown
        table_options = '<option value="">-- Select Table --</option>'
        for table in tables:
            selected = "selected" if table == selected_table else ""
            table_options += f'<option value="{table}" {selected}>{table}</option>'
        
        # Get data if table is selected
        data_html = ""
        pagination_html = ""
        if selected_table:
            page = int(request.query_params.get("page", 1))
            limit = 50
            offset = (page - 1) * limit
            
            data = await data_service.get_table_data(selected_table, limit=limit, offset=offset)
            
            if data.get("rows"):
                headers = list(data["rows"][0].keys())
                rows = []
                for row in data["rows"]:
                    row_data = {}
                    for h in headers:
                        val = str(row.get(h, ""))[:100]
                        row_data[h] = val
                    rows.append(row_data)
                
                # Build data table with edit/delete buttons
                data_html = '<div class="table-wrapper"><table><thead><tr>'
                for h in headers:
                    data_html += f'<th>{h}</th>'
                data_html += '<th>Actions</th></tr></thead><tbody>'
                
                for row in data["rows"]:
                    pk_value = row.get("id", row.get(list(headers)[0], ""))
                    data_html += '<tr>'
                    for h in headers:
                        val = str(row.get(h, ""))[:100]
                        data_html += f'<td>{val}</td>'
                    data_html += f'''
                        <td class="actions">
                            <a href="/db/data/{selected_table}/edit/{pk_value}" class="btn btn-sm">Edit</a>
                            <a href="/db/data/{selected_table}/delete/{pk_value}" class="btn btn-sm btn-danger">Delete</a>
                        </td>
                    </tr>'''
                data_html += '</tbody></table></div>'
                
                # Pagination
                total = data.get("total", 0)
                total_pages = (total + limit - 1) // limit
                if total_pages > 1:
                    pagination_html = '<div class="pagination">'
                    if page > 1:
                        pagination_html += f'<a href="/db/data?table={selected_table}&page={page-1}" class="btn btn-sm">Previous</a>'
                    pagination_html += f'<span> Page {page} of {total_pages} </span>'
                    if page < total_pages:
                        pagination_html += f'<a href="/db/data?table={selected_table}&page={page+1}" class="btn btn-sm">Next</a>'
                    pagination_html += '</div>'
            else:
                data_html = '<p class="text-muted">No data in this table.</p>'
        
        content = f"""
        <div class="card">
            <h1>✏️ Data Editor</h1>
            <p class="text-muted">View and edit table data. Active: <strong>{connection_service.get_active_connection_name()}</strong></p>
        </div>
        
        <div class="card">
            <form method="GET" class="form-inline">
                <select name="table" onchange="this.form.submit()">
                    {table_options}
                </select>
            </form>
        </div>
        
        {f'<div class="card"><div class="card-actions"><a href="/db/data/{selected_table}/add" class="btn btn-primary">Add Record</a></div></div>' if selected_table else ''}
        
        <div class="card">
            <h2 class="card-title">{f'Data: {selected_table}' if selected_table else 'Select a Table'}</h2>
            {data_html}
            {pagination_html}
        </div>
        """
        
        html = template.render(content, title="Data Editor", active_menu="db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/db/data/{table_name}/add")
    async def add_record_form(request: http_api.Request):
        """Add record form page."""
        table_name = request.path_params["table_name"]
        
        if not connection_service.is_connected():
            return http_api.RedirectResponse(url="/db/data", status_code=303)
        
        schema = await data_service.get_table_schema(table_name)
        
        # Build form fields
        form_fields = ""
        for col in schema:
            col_name = col["name"]
            col_type = col.get("type", "TEXT")
            nullable = col.get("nullable", True)
            pk = col.get("primary_key", False)
            auto_inc = col.get("auto_increment", False)
            
            # Skip auto-increment primary keys
            if pk and auto_inc:
                continue
            
            input_type = "text"
            if "INT" in col_type.upper():
                input_type = "number"
            elif "REAL" in col_type.upper() or "FLOAT" in col_type.upper():
                input_type = "number"
                input_type += ' step="0.01"'
            elif "DATE" in col_type.upper():
                input_type = "date"
            elif "TIME" in col_type.upper():
                input_type = "datetime-local"
            
            required = "" if nullable or pk else "required"
            
            form_fields += f"""
            <div class="form-group">
                <label for="{col_name}">{col_name} <small>({col_type})</small></label>
                <input type="{input_type}" id="{col_name}" name="{col_name}" {required}>
            </div>
            """
        
        content = f"""
        <div class="card">
            <h1>Add Record to {table_name}</h1>
        </div>
        
        <div class="card">
            <form action="/db/data/{table_name}/add" method="POST" class="form">
                {form_fields}
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Add Record</button>
                    <a href="/db/data?table={table_name}" class="btn">Cancel</a>
                </div>
            </form>
        </div>
        """
        
        html = template.render(content, title="Add Record", active_menu="db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/data/{table_name}/add")
    async def add_record_submit(request: http_api.Request):
        """Handle add record form submission."""
        table_name = request.path_params["table_name"]
        form = await request.form()
        
        data = {}
        for key, value in form.items():
            if value:  # Only include non-empty values
                data[key] = value
        
        result = await data_service.insert_record(table_name, data)
        
        return http_api.RedirectResponse(url=f"/db/data?table={table_name}", status_code=303)
    
    @http_api.get("/db/data/{table_name}/edit/{record_id}")
    async def edit_record_form(request: http_api.Request):
        """Edit record form page."""
        table_name = request.path_params["table_name"]
        record_id = request.path_params["record_id"]
        
        if not connection_service.is_connected():
            return http_api.RedirectResponse(url="/db/data", status_code=303)
        
        schema = await data_service.get_table_schema(table_name)
        record = await data_service.get_record(table_name, record_id)
        
        if not record:
            content = f"""
            <div class="card">
                <h1>Record Not Found</h1>
                <p class="text-muted">The requested record could not be found.</p>
                <a href="/db/data?table={table_name}" class="btn">Back to Data</a>
            </div>
            """
            html = template.render(content, title="Record Not Found", active_menu="db_data")
            return http_api.HTMLResponse(content=html)
        
        # Build form fields with current values
        form_fields = ""
        for col in schema:
            col_name = col["name"]
            col_type = col.get("type", "TEXT")
            nullable = col.get("nullable", True)
            pk = col.get("primary_key", False)
            auto_inc = col.get("auto_increment", False)
            current_value = record.get(col_name, "")
            
            # Make primary keys readonly
            readonly = "readonly" if pk and auto_inc else ""
            
            input_type = "text"
            if "INT" in col_type.upper():
                input_type = "number"
            elif "REAL" in col_type.upper() or "FLOAT" in col_type.upper():
                input_type = 'number step="0.01"'
            elif "DATE" in col_type.upper():
                input_type = "date"
            elif "TIME" in col_type.upper():
                input_type = "datetime-local"
            
            required = "" if nullable or pk else "required"
            value_attr = f'value="{current_value}"' if current_value is not None else ""
            
            form_fields += f"""
            <div class="form-group">
                <label for="{col_name}">{col_name} <small>({col_type})</small></label>
                <input type="{input_type}" id="{col_name}" name="{col_name}" {value_attr} {required} {readonly}>
            </div>
            """
        
        content = f"""
        <div class="card">
            <h1>Edit Record in {table_name}</h1>
            <p class="text-muted">Record ID: {record_id}</p>
        </div>
        
        <div class="card">
            <form action="/db/data/{table_name}/edit/{record_id}" method="POST" class="form">
                {form_fields}
                <div class="form-actions">
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <a href="/db/data?table={table_name}" class="btn">Cancel</a>
                </div>
            </form>
        </div>
        """
        
        html = template.render(content, title="Edit Record", active_menu="db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/data/{table_name}/edit/{record_id}")
    async def edit_record_submit(request: http_api.Request):
        """Handle edit record form submission."""
        table_name = request.path_params["table_name"]
        record_id = request.path_params["record_id"]
        form = await request.form()
        
        data = {}
        for key, value in form.items():
            data[key] = value
        
        result = await data_service.update_record(table_name, int(record_id), data)
        
        return http_api.RedirectResponse(url=f"/db/data?table={table_name}", status_code=303)
    
    @http_api.get("/db/data/{table_name}/delete/{record_id}")
    async def delete_record_confirm(request: http_api.Request):
        """Delete record confirmation page."""
        table_name = request.path_params["table_name"]
        record_id = request.path_params["record_id"]
        
        content = f"""
        <div class="card">
            <h1>Delete Record</h1>
            <p class="text-danger">Are you sure you want to delete record {record_id} from {table_name}?</p>
        </div>
        
        <div class="card">
            <form action="/db/data/{table_name}/delete/{record_id}" method="POST">
                <button type="submit" class="btn btn-danger">Yes, Delete</button>
                <a href="/db/data?table={table_name}" class="btn">Cancel</a>
            </form>
        </div>
        """
        
        html = template.render(content, title="Delete Record", active_menu="db_data")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/data/{table_name}/delete/{record_id}")
    async def delete_record_submit(request: http_api.Request):
        """Handle delete record form submission."""
        table_name = request.path_params["table_name"]
        record_id = request.path_params["record_id"]
        
        result = await data_service.delete_record(table_name, int(record_id))
        
        return http_api.RedirectResponse(url=f"/db/data?table={table_name}", status_code=303)
