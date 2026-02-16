"""
Web UI routes for SQLite Simple Service.
"""


def register_page_routes(http_api, template, db, logger, services):
    """Register web page routes for database management UI."""
    
    @http_api.get("/db")
    async def database_dashboard(request: http_api.Request):
        """Database dashboard page."""
        tables = await services['get_table_list'](db)
        table_stats = []
        
        for table in tables:
            count = await services['get_table_row_count'](db, table)
            table_stats.append({
                'name': table,
                'rows': count
            })
        
        # Build table cards HTML
        table_cards = ""
        for stat in table_stats:
            table_cards += f"""
            <div class="stat-card">
                <div class="stat-value">{stat['rows']}</div>
                <div class="stat-label">{stat['name']}</div>
                <a href="/db/table/{stat['name']}" class="btn btn-sm">View</a>
            </div>
            """
        
        content = f"""
        <div class="card">
            <h1>Database Dashboard</h1>
            <p class="text-muted">Manage your SQLite database tables and data.</p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Tables Overview</h2>
            <div class="stats-grid">
                {table_cards if table_cards else '<p class="text-muted">No tables found.</p>'}
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Quick Actions</h2>
            <div class="card-actions">
                <a href="/db/query" class="btn btn-primary">Execute SQL Query</a>
                <a href="/db/users" class="btn">Manage Users</a>
                <a href="/db/products" class="btn">Manage Products</a>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Database Statistics</h2>
            <div class="grid grid-3">
                <div class="stat-card">
                    <div class="stat-value">{len(tables)}</div>
                    <div class="stat-label">Total Tables</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{db.connections}</div>
                    <div class="stat-label">Connections</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{db.default.pool_size}</div>
                    <div class="stat-label">Pool Size</div>
                </div>
            </div>
        </div>
        """
        html = template.render(content, title="Database Dashboard", active_menu="db_dashboard")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/db/table/{table_name}")
    async def view_table(request: http_api.Request):
        """View table data page."""
        table_name = request.path_params["table_name"]
        
        # Get table info
        columns = await services['get_table_info'](db, table_name)
        
        # Get table data (limit to 50 rows)
        result = await db.default.execute(f"SELECT * FROM {table_name} LIMIT 50")
        rows = result.rows if result.success else []
        
        # Build column headers
        headers = [col['name'] for col in columns] if columns else (list(rows[0].keys()) if rows else [])
        
        # Build table HTML
        table_html = template.render_table(
            headers=headers,
            rows=rows,
            empty_message="No data in this table."
        )
        
        content = f"""
        <div class="card">
            <h1>Table: {table_name}</h1>
            <p class="text-muted">{len(rows)} rows (showing max 50)</p>
        </div>
        
        <div class="card">
            <div class="card-actions">
                <a href="/db/table/{table_name}/add" class="btn btn-primary">Add Row</a>
                <a href="/db" class="btn">Back to Dashboard</a>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Data</h2>
            {table_html}
        </div>
        """
        html = template.render(content, title=f"Table: {table_name}", active_menu="db_dashboard")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/db/users")
    async def manage_users(request: http_api.Request):
        """User management page."""
        users = await db.find_many(
            "users",
            columns=["id", "username", "email", "full_name", "is_active", "created_at"],
            order_by=["id"]
        )
        
        # Build users table
        if users:
            headers = ["ID", "Username", "Email", "Full Name", "Active", "Created", "Actions"]
            rows = []
            for u in users:
                rows.append({
                    "ID": u.get("id"),
                    "Username": u.get("username"),
                    "Email": u.get("email"),
                    "Full Name": u.get("full_name") or "-",
                    "Active": "✅" if u.get("is_active") else "❌",
                    "Created": str(u.get("created_at", ""))[:10] if u.get("created_at") else "-",
                    "Actions": f'<a href="/db/users/{u.get("id")}/edit" class="btn btn-sm">Edit</a> <a href="/db/users/{u.get("id")}/delete" class="btn btn-sm btn-danger">Delete</a>'
                })
            table_html = template.render_table(headers=headers, rows=rows)
        else:
            table_html = '<p class="text-muted">No users found. <a href="/db/users/add">Add the first user</a></p>'
        
        content = f"""
        <div class="card">
            <h1>User Management</h1>
            <p class="text-muted">Manage user accounts in the database.</p>
        </div>
        
        <div class="card">
            <div class="card-actions">
                <a href="/db/users/add" class="btn btn-primary">Add User</a>
                <a href="/db" class="btn">Back to Dashboard</a>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Users</h2>
            {table_html}
        </div>
        """
        html = template.render(content, title="User Management", active_menu="db_users")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/db/users/add")
    async def add_user_form(request: http_api.Request):
        """Add user form page."""
        form_html = template.render_form(
            action="/db/users/add",
            method="POST",
            fields=[
                {"name": "username", "label": "Username", "type": "text", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "full_name", "label": "Full Name", "type": "text", "required": False},
                {"name": "password", "label": "Password", "type": "password", "required": True},
            ],
            submit_text="Create User"
        )
        
        content = f"""
        <div class="card">
            <h1>Add New User</h1>
            <p class="text-muted">Create a new user account.</p>
        </div>
        
        <div class="card">
            {form_html}
        </div>
        
        <div class="card">
            <a href="/db/users" class="btn">Cancel</a>
        </div>
        """
        html = template.render(content, title="Add User", active_menu="db_users")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/users/add")
    async def add_user_submit(request: http_api.Request):
        """Handle add user form submission."""
        form = await request.form()
        
        result = await db.insert(
            "users",
            {
                "username": form.get("username"),
                "email": form.get("email"),
                "password_hash": f"hashed_{form.get('password')}",  # Simple placeholder
                "full_name": form.get("full_name"),
                "is_active": True
            }
        )
        
        if result.success:
            return http_api.RedirectResponse(url="/db/users", status_code=303)
        else:
            content = f"""
            <div class="card">
                <h1>Error</h1>
                <p class="text-danger">Failed to create user: {result.error}</p>
                <a href="/db/users/add" class="btn">Try Again</a>
            </div>
            """
            html = template.render(content, title="Error", active_menu="db_users")
            return http_api.HTMLResponse(content=html, status_code=400)
    
    @http_api.get("/db/users/{user_id:int}/edit")
    async def edit_user_form(request: http_api.Request):
        """Edit user form page."""
        user_id = request.path_params["user_id"]
        user = await db.find_one("users", where={"id": user_id})
        
        if not user:
            content = '<div class="card"><h1>User not found</h1></div>'
            html = template.render(content, title="Not Found", active_menu="db_users")
            return http_api.HTMLResponse(content=html, status_code=404)
        
        form_html = template.render_form(
            action=f"/db/users/{user_id}/edit",
            method="POST",
            fields=[
                {"name": "username", "label": "Username", "type": "text", "value": user.get("username", ""), "required": True},
                {"name": "email", "label": "Email", "type": "email", "value": user.get("email", ""), "required": True},
                {"name": "full_name", "label": "Full Name", "type": "text", "value": user.get("full_name", ""), "required": False},
                {"name": "is_active", "label": "Active", "type": "checkbox", "checked": user.get("is_active", True)},
            ],
            submit_text="Update User"
        )
        
        content = f"""
        <div class="card">
            <h1>Edit User: {user.get('username')}</h1>
        </div>
        
        <div class="card">
            {form_html}
        </div>
        
        <div class="card">
            <a href="/db/users" class="btn">Cancel</a>
        </div>
        """
        html = template.render(content, title="Edit User", active_menu="db_users")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/users/{user_id:int}/edit")
    async def edit_user_submit(request: http_api.Request):
        """Handle edit user form submission."""
        user_id = request.path_params["user_id"]
        form = await request.form()
        
        result = await db.update(
            "users",
            {
                "email": form.get("email"),
                "full_name": form.get("full_name"),
                "is_active": form.get("is_active") == "on"
            },
            where={"id": user_id}
        )
        
        if result.success:
            return http_api.RedirectResponse(url="/db/users", status_code=303)
        else:
            content = f"""
            <div class="card">
                <h1>Error</h1>
                <p class="text-danger">Failed to update user: {result.error}</p>
            </div>
            """
            html = template.render(content, title="Error", active_menu="db_users")
            return http_api.HTMLResponse(content=html, status_code=400)
    
    @http_api.get("/db/users/{user_id:int}/delete")
    async def delete_user_confirm(request: http_api.Request):
        """Delete user confirmation page."""
        user_id = request.path_params["user_id"]
        user = await db.find_one("users", where={"id": user_id})
        
        if not user:
            content = '<div class="card"><h1>User not found</h1></div>'
            html = template.render(content, title="Not Found", active_menu="db_users")
            return http_api.HTMLResponse(content=html, status_code=404)
        
        content = f"""
        <div class="card">
            <h1>Delete User</h1>
            <p class="text-muted">Are you sure you want to delete this user?</p>
        </div>
        
        <div class="card">
            <p><strong>Username:</strong> {user.get('username')}</p>
            <p><strong>Email:</strong> {user.get('email')}</p>
            <p><strong>Full Name:</strong> {user.get('full_name', '-')}</p>
        </div>
        
        <div class="card">
            <form action="/db/users/{user_id}/delete" method="POST">
                <button type="submit" class="btn btn-danger">Yes, Delete</button>
                <a href="/db/users" class="btn">Cancel</a>
            </form>
        </div>
        """
        html = template.render(content, title="Delete User", active_menu="db_users")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/users/{user_id:int}/delete")
    async def delete_user_submit(request: http_api.Request):
        """Handle delete user form submission."""
        user_id = request.path_params["user_id"]
        
        result = await db.delete("users", where={"id": user_id})
        
        if result.success:
            return http_api.RedirectResponse(url="/db/users", status_code=303)
        else:
            content = f"""
            <div class="card">
                <h1>Error</h1>
                <p class="text-danger">Failed to delete user: {result.error}</p>
            </div>
            """
            html = template.render(content, title="Error", active_menu="db_users")
            return http_api.HTMLResponse(content=html, status_code=400)
    
    @http_api.get("/db/products")
    async def manage_products(request: http_api.Request):
        """Product management page."""
        products = await db.find_many(
            "products",
            columns=["id", "name", "description", "price", "stock", "is_available"],
            order_by=["id"]
        )
        
        if products:
            headers = ["ID", "Name", "Price", "Stock", "Available", "Actions"]
            rows = []
            for p in products:
                rows.append({
                    "ID": p.get("id"),
                    "Name": p.get("name"),
                    "Price": f"${p.get('price', 0):.2f}",
                    "Stock": p.get("stock", 0),
                    "Available": "✅" if p.get("is_available") else "❌",
                    "Actions": f'<a href="/db/products/{p.get("id")}/edit" class="btn btn-sm">Edit</a>'
                })
            table_html = template.render_table(headers=headers, rows=rows)
        else:
            table_html = '<p class="text-muted">No products found.</p>'
        
        content = f"""
        <div class="card">
            <h1>Product Management</h1>
            <p class="text-muted">Manage products in the database.</p>
        </div>
        
        <div class="card">
            <div class="card-actions">
                <a href="/db/products/add" class="btn btn-primary">Add Product</a>
                <a href="/db" class="btn">Back to Dashboard</a>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Products</h2>
            {table_html}
        </div>
        """
        html = template.render(content, title="Product Management", active_menu="db_products")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/db/query")
    async def query_form(request: http_api.Request):
        """SQL query execution page."""
        content = f"""
        <div class="card">
            <h1>Execute SQL Query</h1>
            <p class="text-muted">Run custom SQL queries on the database.</p>
        </div>
        
        <div class="card">
            <form action="/db/query" method="POST">
                <div class="form-group">
                    <label for="query">SQL Query:</label>
                    <textarea id="query" name="query" rows="6" class="form-control" 
                        placeholder="SELECT * FROM users LIMIT 10"></textarea>
                </div>
                <div class="card-actions">
                    <button type="submit" class="btn btn-primary">Execute</button>
                    <a href="/db" class="btn">Cancel</a>
                </div>
            </form>
        </div>
        """
        html = template.render(content, title="Execute Query", active_menu="db_query")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/db/query")
    async def query_execute(request: http_api.Request):
        """Execute SQL query and show results."""
        form = await request.form()
        query = form.get("query", "").strip()
        
        if not query:
            return http_api.RedirectResponse(url="/db/query", status_code=303)
        
        result = await db.default.execute(query)
        
        if result.success:
            if result.rows:
                headers = list(result.rows[0].keys())
                table_html = template.render_table(headers=headers, rows=result.rows)
            else:
                table_html = f'<p class="text-muted">Query executed successfully. Affected rows: {result.affected_rows}</p>'
            
            content = f"""
            <div class="card">
                <h1>Query Results</h1>
                <p class="text-muted">Query executed successfully.</p>
            </div>
            
            <div class="card">
                <h2 class="card-title">Executed Query</h2>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">{query}</pre>
            </div>
            
            <div class="card">
                <h2 class="card-title">Results ({len(result.rows) if result.rows else 0} rows)</h2>
                {table_html}
            </div>
            
            <div class="card">
                <a href="/db/query" class="btn">Run Another Query</a>
            </div>
            """
        else:
            content = f"""
            <div class="card">
                <h1>Query Error</h1>
                <p class="text-danger">{result.error}</p>
            </div>
            
            <div class="card">
                <h2 class="card-title">Failed Query</h2>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">{query}</pre>
            </div>
            
            <div class="card">
                <a href="/db/query" class="btn">Try Again</a>
            </div>
            """
        
        html = template.render(content, title="Query Results", active_menu="db_query")
        return http_api.HTMLResponse(content=html)
    
    if logger:
        logger.log("Web UI routes registered", tag="sqlite_simple")
