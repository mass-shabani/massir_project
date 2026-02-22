"""
Transaction management routes for Multi-Database Service.

This module provides routes for:
- Transaction management page
- Begin/Commit/Rollback operations
- Savepoint management
"""


def register_transaction_routes(http_api, template, db_manager, logger):
    """Register transaction management routes."""
    
    @http_api.get("/multi-db/transactions")
    async def transactions_page(request: http_api.Request):
        """Transaction management page."""
        connections = db_manager.get_connections()
        active_name = db_manager.get_active_connection_name()
        transactions = db_manager.get_all_transactions()
        
        # Build connections dropdown
        conn_options = ""
        for conn in connections:
            selected = "selected" if conn["name"] == active_name else ""
            conn_options += f'<option value="{conn["name"]}" {selected}>{conn["name"]} ({conn["driver"].upper()})</option>'
        
        # Build transactions list
        if transactions:
            tx_rows = ""
            for tx in transactions:
                state_class = {
                    "active": "status-connected",
                    "committed": "status-disconnected",
                    "rolled_back": "status-disconnected",
                    "idle": ""
                }.get(tx["state"], "")
                
                savepoints_html = ""
                if tx["savepoints"]:
                    savepoints_html = '<div class="savepoints-list">'
                    for sp in tx["savepoints"]:
                        savepoints_html += f'<span class="badge">{sp}</span> '
                    savepoints_html += '</div>'
                
                tx_rows += f"""
                <tr>
                    <td>{tx['connection_name']}</td>
                    <td><span class="{state_class}">{tx['state'].upper()}</span></td>
                    <td>{tx['started_at'] or '-'}</td>
                    <td>{tx['operations_count']}</td>
                    <td>{savepoints_html or '-'}</td>
                    <td class="actions">
                        <button onclick="selectConnection('{tx['connection_name']}')" class="btn btn-sm">Select</button>
                    </td>
                </tr>
                """
            
            transactions_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Connection</th>
                            <th>State</th>
                            <th>Started At</th>
                            <th>Operations</th>
                            <th>Savepoints</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>{tx_rows}</tbody>
                </table>
            </div>
            """
        else:
            transactions_html = '<p class="text-muted">No active transactions.</p>'
        
        # Get current transaction info
        current_tx = db_manager.get_transaction_info()
        
        content = f"""
        <div class="card">
            <h1>🔄 Transaction Management</h1>
            <p class="text-muted">Manage database transactions with commit/rollback support.</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="card">
            <h2 class="card-title">Select Connection</h2>
            <div class="form-group">
                <select id="connection-select" onchange="loadTransactionInfo()">
                    <option value="">-- Select Connection --</option>
                    {conn_options}
                </select>
            </div>
        </div>
        
        <div class="card" id="transaction-panel" style="display: none;">
            <h2 class="card-title">Transaction Control</h2>
            <div id="transaction-status" class="status-panel">
                <div class="status-row">
                    <span class="status-label">State:</span>
                    <span id="tx-state" class="status-value">-</span>
                </div>
                <div class="status-row">
                    <span class="status-label">Started:</span>
                    <span id="tx-started" class="status-value">-</span>
                </div>
                <div class="status-row">
                    <span class="status-label">Savepoints:</span>
                    <span id="tx-savepoints" class="status-value">-</span>
                </div>
            </div>
            
            <div class="form-actions">
                <button type="button" onclick="beginTransaction()" class="btn btn-primary" id="btn-begin">Begin Transaction</button>
                <button type="button" onclick="commitTransaction()" class="btn btn-success" id="btn-commit" disabled>Commit</button>
                <button type="button" onclick="rollbackTransaction()" class="btn btn-danger" id="btn-rollback" disabled>Rollback</button>
            </div>
        </div>
        
        <div class="card" id="savepoint-panel" style="display: none;">
            <h2 class="card-title">Savepoints</h2>
            <div class="form-row">
                <div class="form-group">
                    <label for="savepoint-name">Savepoint Name</label>
                    <input type="text" id="savepoint-name" placeholder="savepoint_name">
                </div>
            </div>
            <div class="form-actions">
                <button type="button" onclick="createSavepoint()" class="btn btn-sm">Create Savepoint</button>
                <button type="button" onclick="rollbackToSavepoint()" class="btn btn-sm btn-warning">Rollback To</button>
                <button type="button" onclick="releaseSavepoint()" class="btn btn-sm">Release</button>
            </div>
            <div id="savepoints-list" class="savepoints-container"></div>
        </div>
        
        <div class="card">
            <h2 class="card-title">All Transactions</h2>
            <div id="transactions-list">{transactions_html}</div>
        </div>
        
        <script>
        let currentConnection = null;
        
        function selectConnection(name) {{
            document.getElementById('connection-select').value = name;
            loadTransactionInfo();
        }}
        
        async function loadTransactionInfo() {{
            const select = document.getElementById('connection-select');
            currentConnection = select.value;
            
            const panel = document.getElementById('transaction-panel');
            const savepointPanel = document.getElementById('savepoint-panel');
            
            if (!currentConnection) {{
                panel.style.display = 'none';
                savepointPanel.style.display = 'none';
                return;
            }}
            
            panel.style.display = 'block';
            
            try {{
                const response = await fetch(`/multi-db/api/transactions/${{currentConnection}}/info`);
                const result = await response.json();
                
                if (result.transaction) {{
                    updateTransactionUI(result.transaction);
                }} else {{
                    updateTransactionUI(null);
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        function updateTransactionUI(tx) {{
            const stateEl = document.getElementById('tx-state');
            const startedEl = document.getElementById('tx-started');
            const savepointsEl = document.getElementById('tx-savepoints');
            const btnBegin = document.getElementById('btn-begin');
            const btnCommit = document.getElementById('btn-commit');
            const btnRollback = document.getElementById('btn-rollback');
            const savepointPanel = document.getElementById('savepoint-panel');
            
            if (!tx || tx.state === 'idle') {{
                stateEl.textContent = 'IDLE';
                stateEl.className = 'status-value';
                startedEl.textContent = '-';
                savepointsEl.textContent = '-';
                btnBegin.disabled = false;
                btnCommit.disabled = true;
                btnRollback.disabled = true;
                savepointPanel.style.display = 'none';
            }} else if (tx.state === 'active') {{
                stateEl.textContent = 'ACTIVE';
                stateEl.className = 'status-value status-active';
                startedEl.textContent = tx.started_at || '-';
                savepointsEl.textContent = tx.savepoints.length > 0 ? tx.savepoints.join(', ') : '-';
                btnBegin.disabled = true;
                btnCommit.disabled = false;
                btnRollback.disabled = false;
                savepointPanel.style.display = 'block';
                updateSavepointsList(tx.savepoints);
            }} else if (tx.state === 'committed') {{
                stateEl.textContent = 'COMMITTED';
                stateEl.className = 'status-value status-success';
                startedEl.textContent = tx.started_at || '-';
                savepointsEl.textContent = '-';
                btnBegin.disabled = false;
                btnCommit.disabled = true;
                btnRollback.disabled = true;
                savepointPanel.style.display = 'none';
            }} else if (tx.state === 'rolled_back') {{
                stateEl.textContent = 'ROLLED BACK';
                stateEl.className = 'status-value status-error';
                startedEl.textContent = tx.started_at || '-';
                savepointsEl.textContent = '-';
                btnBegin.disabled = false;
                btnCommit.disabled = true;
                btnRollback.disabled = true;
                savepointPanel.style.display = 'none';
            }}
        }}
        
        function updateSavepointsList(savepoints) {{
            const container = document.getElementById('savepoints-list');
            if (savepoints.length === 0) {{
                container.innerHTML = '<p class="text-muted">No savepoints.</p>';
                return;
            }}
            
            let html = '<div class="savepoints-items">';
            savepoints.forEach(sp => {{
                html += `<span class="badge badge-clickable" onclick="document.getElementById('savepoint-name').value='${{sp}}'">${{sp}}</span> `;
            }});
            html += '</div>';
            container.innerHTML = html;
        }}
        
        async function beginTransaction() {{
            if (!currentConnection) return;
            
            try {{
                const response = await fetch(`/multi-db/api/transactions/${{currentConnection}}/begin`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    updateTransactionUI(result.transaction);
                    refreshTransactionsList();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function commitTransaction() {{
            if (!currentConnection) return;
            
            try {{
                const response = await fetch(`/multi-db/api/transactions/${{currentConnection}}/commit`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    updateTransactionUI(result.transaction);
                    refreshTransactionsList();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function rollbackTransaction() {{
            if (!currentConnection) return;
            
            if (!confirm('Are you sure you want to rollback the transaction?')) return;
            
            try {{
                const response = await fetch(`/multi-db/api/transactions/${{currentConnection}}/rollback`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    updateTransactionUI(result.transaction);
                    refreshTransactionsList();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function createSavepoint() {{
            if (!currentConnection) return;
            
            const name = document.getElementById('savepoint-name').value.trim();
            if (!name) {{
                showMessage('Please enter a savepoint name', 'warning');
                return;
            }}
            
            try {{
                const response = await fetch(`/multi-db/api/transactions/${{currentConnection}}/savepoint/${{name}}/create`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    updateTransactionUI(result.transaction);
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function rollbackToSavepoint() {{
            if (!currentConnection) return;
            
            const name = document.getElementById('savepoint-name').value.trim();
            if (!name) {{
                showMessage('Please enter a savepoint name', 'warning');
                return;
            }}
            
            try {{
                const response = await fetch(`/multi-db/api/transactions/${{currentConnection}}/savepoint/${{name}}/rollback`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    updateTransactionUI(result.transaction);
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function releaseSavepoint() {{
            if (!currentConnection) return;
            
            const name = document.getElementById('savepoint-name').value.trim();
            if (!name) {{
                showMessage('Please enter a savepoint name', 'warning');
                return;
            }}
            
            try {{
                const response = await fetch(`/multi-db/api/transactions/${{currentConnection}}/savepoint/${{name}}/release`, {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    updateTransactionUI(result.transaction);
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function refreshTransactionsList() {{
            try {{
                const response = await fetch('/multi-db/api/transactions/list');
                const data = await response.json();
                
                if (data.transactions.length > 0) {{
                    let html = `<div class="table-wrapper"><table><thead><tr>
                        <th>Connection</th><th>State</th><th>Started At</th><th>Operations</th><th>Savepoints</th><th>Actions</th>
                    </tr></thead><tbody>`;
                    
                    data.transactions.forEach(tx => {{
                        const stateClass = {{active: 'status-connected', committed: 'status-disconnected', rolled_back: 'status-disconnected', idle: ''}}[tx.state] || '';
                        
                        let savepointsHtml = '';
                        if (tx.savepoints && tx.savepoints.length > 0) {{
                            savepointsHtml = tx.savepoints.map(sp => `<span class="badge">${{sp}}</span>`).join(' ');
                        }}
                        
                        html += `<tr>
                            <td>${{tx.connection_name}}</td>
                            <td><span class="${{stateClass}}">${{tx.state.toUpperCase()}}</span></td>
                            <td>${{tx.started_at || '-'}}</td>
                            <td>${{tx.operations_count}}</td>
                            <td>${{savepointsHtml || '-'}}</td>
                            <td class="actions">
                                <button onclick="selectConnection('${{tx.connection_name}}')" class="btn btn-sm">Select</button>
                            </td>
                        </tr>`;
                    }});
                    
                    html += '</tbody></table></div>';
                    document.getElementById('transactions-list').innerHTML = html;
                }} else {{
                    document.getElementById('transactions-list').innerHTML = '<p class="text-muted">No active transactions.</p>';
                }}
            }} catch (error) {{
                console.error('Failed to refresh transactions:', error);
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
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {{
            loadTransactionInfo();
        }});
        </script>
        
        <style>
        .status-panel {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .status-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border-color);
        }}
        .status-row:last-child {{
            border-bottom: none;
        }}
        .status-label {{
            font-weight: 600;
        }}
        .status-active {{
            color: var(--success-color);
            font-weight: 600;
        }}
        .status-success {{
            color: var(--success-color);
        }}
        .status-error {{
            color: var(--danger-color);
        }}
        .savepoints-container {{
            margin-top: 1rem;
        }}
        .savepoints-items {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .badge-clickable {{
            cursor: pointer;
        }}
        .badge-clickable:hover {{
            opacity: 0.8;
        }}
        </style>
        """
        
        html = template.render(content, title="Transaction Management", active_menu="multi_db_transactions")
        return http_api.HTMLResponse(content=html)
    
    # ==================== API Routes ====================
    
    @http_api.get("/multi-db/api/transactions/list")
    async def api_transactions_list(request: http_api.Request):
        """Get list of all transactions."""
        transactions = db_manager.get_all_transactions()
        return {"transactions": transactions}
    
    @http_api.get("/multi-db/api/transactions/{connection_name}/info")
    async def api_transaction_info(request: http_api.Request):
        """Get transaction info for a connection."""
        connection_name = request.path_params["connection_name"]
        tx_info = db_manager.get_transaction_info(connection_name)
        return {"transaction": tx_info}
    
    @http_api.post("/multi-db/api/transactions/{connection_name}/begin")
    async def api_transaction_begin(request: http_api.Request):
        """Begin a transaction."""
        connection_name = request.path_params["connection_name"]
        result = await db_manager.begin_transaction(connection_name)
        return result
    
    @http_api.post("/multi-db/api/transactions/{connection_name}/commit")
    async def api_transaction_commit(request: http_api.Request):
        """Commit a transaction."""
        connection_name = request.path_params["connection_name"]
        result = await db_manager.commit_transaction(connection_name)
        return result
    
    @http_api.post("/multi-db/api/transactions/{connection_name}/rollback")
    async def api_transaction_rollback(request: http_api.Request):
        """Rollback a transaction."""
        connection_name = request.path_params["connection_name"]
        result = await db_manager.rollback_transaction(connection_name)
        return result
    
    @http_api.post("/multi-db/api/transactions/{connection_name}/savepoint/{name}/create")
    async def api_savepoint_create(request: http_api.Request):
        """Create a savepoint."""
        connection_name = request.path_params["connection_name"]
        name = request.path_params["name"]
        result = await db_manager.create_savepoint(name, connection_name)
        return result
    
    @http_api.post("/multi-db/api/transactions/{connection_name}/savepoint/{name}/rollback")
    async def api_savepoint_rollback(request: http_api.Request):
        """Rollback to a savepoint."""
        connection_name = request.path_params["connection_name"]
        name = request.path_params["name"]
        result = await db_manager.rollback_to_savepoint(name, connection_name)
        return result
    
    @http_api.post("/multi-db/api/transactions/{connection_name}/savepoint/{name}/release")
    async def api_savepoint_release(request: http_api.Request):
        """Release a savepoint."""
        connection_name = request.path_params["connection_name"]
        name = request.path_params["name"]
        result = await db_manager.release_savepoint(name, connection_name)
        return result
    
    if logger:
        logger.log("Transaction routes registered", tag="multi_db")
