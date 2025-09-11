"""
Email Redirection Tool - Flask Application
View existing email forwarding for Namecheap domains
"""

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from flask_cors import CORS
import json
import os
from datetime import datetime
from functools import wraps
from namecheap_client import EmailRedirectionManager
from models import Database

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-in-production-email-redirect-tool')
CORS(app)

# Dashboard template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>Domain Email Redirections Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #f8fafc; }
        .header { background: #1e293b; color: white; padding: 1rem 2rem; }
        .logo { font-size: 1.5rem; font-weight: 700; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 2rem; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem; }
        .btn { background: #3b82f6; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 1rem; }
        .btn-success { background: #10b981; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 600; }
        .form-control { padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 6px; margin-right: 1rem; }
        .table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        .table th, .table td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb; }
        .table th { background: #f9fafb; font-weight: 600; }
        .status-success { color: #10b981; font-weight: 600; }
        .status-error { color: #ef4444; font-weight: 600; }
        .progress-bar { width: 100%; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 8px; background: #3b82f6; transition: width 0.3s; }
        .group-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
        .group-header { color: #1e293b; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }
        .group-count { font-size: 0.8em; color: #64748b; font-weight: normal; }
        .redirect-item { padding: 0.5rem; background: #f8fafc; border-radius: 4px; margin-bottom: 0.5rem; }
        .domain-row { border-bottom: 1px solid #e5e7eb; }
        .domain-name { font-weight: 600; color: #1e293b; }
        .redirect-input { width: 100%; padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px; }
        .btn-small { padding: 0.5rem 1rem; font-size: 0.875rem; }
        .status-updating { color: #f59e0b; font-size: 0.875rem; }
        .status-success { color: #10b981; font-size: 0.875rem; }
        .status-error { color: #ef4444; font-size: 0.875rem; }
        .no-redirect { color: #64748b; font-style: italic; }
        .add-redirect-btn { background: #10b981; color: white; }
        #loading, #domains-view, #raw-data { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🔗 Domain URL Redirections Viewer</div>
    </div>
    
    <div class="container">
        <div class="card">
            <h1>Domain URL Redirection Viewer</h1>
            <p>View existing domain redirections (URL forwarding) for all your domains using Namecheap API</p>
        </div>
        
        <div class="card">
            <h2>Domain Management</h2>
            <div style="margin-bottom: 1rem; display: flex; gap: 1rem; flex-wrap: wrap;">
                <button class="btn btn-success" onclick="syncAllDomainsFromNamecheap()">🔄 Sync All Domains from Namecheap</button>
                <button class="btn" onclick="loadDomainsFromDB()">📊 Load Domains from Database</button>
                <button class="btn" onclick="showBulkUpdateModal()">🔧 Bulk Update</button>
                <button class="btn" onclick="showClientModal()">👥 Manage Clients</button>
                <button class="btn" onclick="exportRedirections()">📁 Export to CSV</button>
                <a href="/logout" class="btn" style="background: #ef4444;">🚪 Logout</a>
            </div>
            
            <div id="sync-progress" style="display: none; margin-bottom: 1rem;">
                <div class="progress-bar">
                    <div class="progress-fill" id="sync-progress-fill" style="width: 0%;"></div>
                </div>
                <p id="sync-progress-text">Syncing domains from Namecheap...</p>
                <div id="sync-status"></div>
            </div>
            
            <div id="loading">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%;"></div>
                </div>
                <p id="progress-text">Loading domains...</p>
            </div>
        </div>
        
        <div class="card" id="domains-view">
            <h2>All Domains with URL Redirections</h2>
            <div id="domains-summary"></div>
            
            <div style="margin: 1rem 0;">
                <input type="text" class="form-control" id="search-filter" placeholder="Search domains..." onkeyup="filterDomains()" style="width: 300px;">
                <button class="btn" onclick="refreshDomains()" style="margin-left: 1rem;">🔄 Refresh</button>
                <button class="btn" onclick="loadMoreDomainsBatch()" id="load-more-btn" style="margin-left: 1rem; display: none;">Load More Domains</button>
            </div>
            
            <table class="table" id="domains-table">
                <thead>
                    <tr>
                        <th style="width: 5%;">#</th>
                        <th style="width: 25%;">Domain</th>
                        <th style="width: 35%;">Redirect Target</th>
                        <th style="width: 15%;">Client</th>
                        <th style="width: 20%;">Action</th>
                    </tr>
                </thead>
                <tbody id="domains-tbody">
                </tbody>
            </table>
            
            <div id="scroll-loader" style="text-align: center; padding: 1rem; display: none;">
                <div>Loading more domains...</div>
            </div>
        </div>
        
        <div class="card" id="raw-data">
            <h2>Raw Data View</h2>
            <table class="table" id="redirections-table">
                <thead>
                    <tr>
                        <th>Domain</th>
                        <th>Redirect Type</th>
                        <th>Target URL</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="redirections-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        let allDomains = [];
        let currentPage = 1;
        let domainsPerPage = 25;
        let isLoading = false;
        let hasMore = true;
        let totalDomains = 0;
        let allRedirections = [];
        let groupedData = {};
        
        async function loadAllDomains() {
            try {
                // Reset state
                allDomains = [];
                currentPage = 1;
                hasMore = true;
                
                document.getElementById('loading').style.display = 'block';
                document.getElementById('domains-view').style.display = 'none';
                document.getElementById('raw-data').style.display = 'none';
                
                // Load first batch
                await loadDomainsBatch(1);
                
                document.getElementById('domains-view').style.display = 'block';
                document.getElementById('raw-data').style.display = 'block';
                
            } catch (error) {
                alert(`Error loading domains: ${error.message}`);
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        async function loadDomainsBatch(page) {
            if (isLoading) return;
            
            isLoading = true;
            
            try {
                const response = await fetch(`/api/domains-batch?page=${page}&per_page=${domainsPerPage}`);
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Add new domains to existing list
                    allDomains = allDomains.concat(data.domains);
                    
                    // Update pagination info
                    hasMore = data.pagination.has_next;
                    totalDomains = data.pagination.total_domains;
                    currentPage = data.pagination.page;
                    
                    // Update display
                    displayDomains();
                    
                    // Show/hide load more button
                    const loadMoreBtn = document.getElementById('load-more-btn');
                    if (hasMore) {
                        loadMoreBtn.style.display = 'inline-block';
                    } else {
                        loadMoreBtn.style.display = 'none';
                    }
                    
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error loading domain batch: ${error.message}`);
            } finally {
                isLoading = false;
            }
        }
        
        async function loadMoreDomainsBatch() {
            if (!hasMore || isLoading) return;
            
            const nextPage = currentPage + 1;
            await loadDomainsBatch(nextPage);
        }
        
        function displayDomains() {
            const tbody = document.getElementById('domains-tbody');
            const summary = document.getElementById('domains-summary');
            
            // Clear existing rows
            tbody.innerHTML = '';
            
            // Update summary
            const totalDomains = allDomains.length;
            const domainsWithRedirects = allDomains.filter(d => d.redirections && d.redirections.length > 0).length;
            
            summary.innerHTML = `
                <div style="display: flex; gap: 2rem; margin-bottom: 1rem; flex-wrap: wrap;">
                    <div><strong>Total Domains:</strong> ${totalDomains}</div>
                    <div><strong>Domains with Redirects:</strong> ${domainsWithRedirects}</div>
                </div>
            `;
            
            // Add all domains to table
            allDomains.forEach((domain, domainIndex) => {
                if (domain.redirections && domain.redirections.length > 0) {
                    // Domain has redirections - show each redirection
                    domain.redirections.forEach((redirect, redirectIndex) => {
                        createDomainRow(domain, redirect, redirectIndex, domainIndex);
                    });
                } else {
                    // Domain has no redirections - show empty row
                    createEmptyDomainRow(domain, domainIndex);
                }
            });
            
            setupInfiniteScroll();
        }
        
        function createDomainRow(domain, redirect, redirectIndex, domainIndex) {
            const tbody = document.getElementById('domains-tbody');
            const row = tbody.insertRow();
            row.className = 'domain-row';
            
            // Domain name cell
            const domainCell = row.insertCell(0);
            domainCell.innerHTML = `<div class="domain-name">${domain.name}</div>`;
            
            // Redirect target cell (editable)
            const redirectCell = row.insertCell(1);
            const safeId = `${domain.name.replace(/\./g, '-')}-${redirectIndex}`;
            redirectCell.innerHTML = `
                <input type="text" class="redirect-input" 
                       value="${redirect.target || ''}" 
                       id="target-${safeId}" 
                       placeholder="https://example.com">
                <div id="status-${safeId}" class="status-updating" style="display: none; margin-top: 0.25rem;"></div>
            `;
            
            // Action cell
            const actionCell = row.insertCell(2);
            actionCell.innerHTML = `
                <button class="btn btn-small btn-success" onclick="updateDomainRedirect('${domain.name}', '${redirect.name || '@'}', ${redirectIndex})">
                    Update
                </button>
            `;
        }
        
        function createEmptyDomainRow(domain, domainIndex) {
            const tbody = document.getElementById('domains-tbody');
            const row = tbody.insertRow();
            row.className = 'domain-row';
            
            // Domain name cell
            const domainCell = row.insertCell(0);
            domainCell.innerHTML = `<div class="domain-name">${domain.name}</div>`;
            
            // Redirect target cell (empty, ready for input)
            const redirectCell = row.insertCell(1);
            const safeId = `${domain.name.replace(/\./g, '-')}-new`;
            redirectCell.innerHTML = `
                <input type="text" class="redirect-input" 
                       value="" 
                       id="target-${safeId}" 
                       placeholder="Enter redirect URL (https://example.com)">
                <div id="status-${safeId}" class="status-updating" style="display: none; margin-top: 0.25rem;"></div>
            `;
            
            // Action cell
            const actionCell = row.insertCell(2);
            actionCell.innerHTML = `
                <button class="btn btn-small add-redirect-btn" onclick="addDomainRedirect('${domain.name}')">
                    + Add
                </button>
            `;
        }
        
        function setupInfiniteScroll() {
            window.addEventListener('scroll', () => {
                if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 1000) {
                    if (!isLoading && currentPage * domainsPerPage < allDomains.length) {
                        loadMoreDomains();
                    }
                }
            });
        }
        
        async function updateDomainRedirect(domainName, redirectName, redirectIndex) {
            const safeId = `${domainName.replace(/\./g, '-')}-${redirectIndex}`;
            const targetField = document.getElementById(`target-${safeId}`);
            const statusDiv = document.getElementById(`status-${safeId}`);
            
            const target = targetField.value.trim();
            
            if (!target) {
                alert('Please enter a target URL');
                return;
            }
            
            // Show loading status
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Updating...';
            statusDiv.className = 'status-updating';
            
            try {
                const response = await fetch('/api/update-redirection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        domain: domainName,
                        name: redirectName,
                        target: target
                    })
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    statusDiv.textContent = '✅ Updated!';
                    statusDiv.className = 'status-success';
                    
                    // Update local data
                    const domain = allDomains.find(d => d.name === domainName);
                    if (domain && domain.redirections && domain.redirections[redirectIndex]) {
                        domain.redirections[redirectIndex].target = target;
                    }
                } else {
                    statusDiv.textContent = '❌ Error!';
                    statusDiv.className = 'status-error';
                    alert(`Update failed: ${result.message}`);
                }
            } catch (error) {
                statusDiv.textContent = '❌ Error!';
                statusDiv.className = 'status-error';
                alert(`Update failed: ${error.message}`);
            }
            
            // Hide status after 3 seconds
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 3000);
        }
        
        async function addDomainRedirect(domainName) {
            const safeId = `${domainName.replace(/\./g, '-')}-new`;
            const targetField = document.getElementById(`target-${safeId}`);
            const statusDiv = document.getElementById(`status-${safeId}`);
            
            const target = targetField.value.trim();
            
            if (!target) {
                alert('Please enter a target URL');
                return;
            }
            
            // Show loading status
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Adding...';
            statusDiv.className = 'status-updating';
            
            try {
                const response = await fetch('/api/update-redirection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        domain: domainName,
                        name: '@',
                        target: target
                    })
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    statusDiv.textContent = '✅ Added!';
                    statusDiv.className = 'status-success';
                    
                    // Refresh the domain list to show the new redirect
                    setTimeout(() => {
                        refreshDomains();
                    }, 1000);
                } else {
                    statusDiv.textContent = '❌ Error!';
                    statusDiv.className = 'status-error';
                    alert(`Add failed: ${result.message}`);
                }
            } catch (error) {
                statusDiv.textContent = '❌ Error!';
                statusDiv.className = 'status-error';
                alert(`Add failed: ${error.message}`);
            }
        }
        
        function refreshDomains() {
            loadAllDomains();
        }
        
        function filterDomains() {
            const searchTerm = document.getElementById('search-filter').value.toLowerCase();
            const rows = document.querySelectorAll('.domain-row');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        }
        
        async function loadAllRedirections() {
            // Legacy function - redirect to new function
            loadAllDomains();
        }
        
        function displayRedirections() {
            // Update summary
            const summary = document.getElementById('redirections-summary');
            const totalDomains = new Set(allRedirections.map(r => r.domain)).size;
            const totalRedirects = allRedirections.length;
            const uniqueTargets = new Set(allRedirections.map(r => r.target)).size;
            
            summary.innerHTML = `
                <div style="display: flex; gap: 2rem; margin-bottom: 1rem; flex-wrap: wrap;">
                    <div><strong>Total Domains:</strong> ${totalDomains}</div>
                    <div><strong>Total Redirections:</strong> ${totalRedirects}</div>
                    <div><strong>Unique Target Emails:</strong> ${uniqueTargets}</div>
                </div>
            `;
            
            // Update raw data table
            const tbody = document.getElementById('redirections-body');
            tbody.innerHTML = '';
            
            allRedirections.forEach(redirect => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = redirect.domain;
                row.insertCell(1).textContent = redirect.type;
                row.insertCell(2).textContent = redirect.target;
                row.insertCell(3).innerHTML = redirect.status === 'active' ? 
                    '<span class="status-success">Active</span>' : 
                    '<span class="status-error">Inactive</span>';
            });
            
            // Update grouping
            updateGrouping();
        }
        
        function updateGrouping() {
            const groupBy = document.getElementById('group-filter').value;
            const groupedDiv = document.getElementById('grouped-redirections');
            
            // Group data
            groupedData = {};
            allRedirections.forEach(redirect => {
                let key;
                switch(groupBy) {
                    case 'target':
                        key = redirect.target;
                        break;
                    case 'domain':
                        key = redirect.domain;
                        break;
                    case 'type':
                        key = redirect.type;
                        break;
                }
                
                if (!groupedData[key]) {
                    groupedData[key] = [];
                }
                groupedData[key].push(redirect);
            });
            
            // Display grouped data
            let html = '';
            Object.entries(groupedData).sort().forEach(([group, redirects]) => {
                html += `
                    <div class="group-card">
                        <div class="group-header">
                            <h3>${groupBy === 'target' ? '🔗' : groupBy === 'domain' ? '🌐' : '📋'} ${group}</h3>
                            <span class="group-count">${redirects.length} ${redirects.length === 1 ? 'redirect' : 'redirects'}</span>
                        </div>
                        <div>
                `;
                
                redirects.forEach(redirect => {
                    if (groupBy === 'target') {
                        html += `<div class="redirect-item">
                            <strong>${redirect.domain}</strong> → ${redirect.target}
                        </div>`;
                    } else if (groupBy === 'domain') {
                        html += `<div class="redirect-item">
                            ${redirect.type}: <strong>${redirect.target}</strong>
                        </div>`;
                    } else {
                        html += `<div class="redirect-item">
                            <strong>${redirect.domain}</strong> → ${redirect.target}
                        </div>`;
                    }
                });
                
                html += `</div></div>`;
            });
            
            groupedDiv.innerHTML = html;
        }
        
        function filterResults() {
            const searchTerm = document.getElementById('search-filter').value.toLowerCase();
            const rows = document.getElementById('redirections-body').querySelectorAll('tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        }
        
        function exportRedirections() {
            if (allRedirections.length === 0) {
                alert('No redirections to export. Load data first.');
                return;
            }
            
            let csv = 'Domain,Redirect Type,Target URL,Status\\n';
            
            allRedirections.forEach(redirect => {
                csv += `${redirect.domain},${redirect.type},${redirect.target},${redirect.status}\\n`;
            });
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `domain_redirections_${new Date().toISOString().slice(0,10)}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
"""

# Initialize database and email redirection manager
db = Database()
email_manager = None

try:
    email_manager = EmailRedirectionManager()
    print("Email Redirection Manager initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize Email Redirection Manager: {e}")

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Login template
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Domain Redirect Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #f8fafc; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .login-card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); width: 400px; }
        .logo { font-size: 1.5rem; font-weight: 700; text-align: center; margin-bottom: 2rem; color: #1e293b; }
        .form-group { margin-bottom: 1.5rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 600; }
        .form-control { width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 6px; }
        .btn { width: 100%; background: #3b82f6; color: white; border: none; padding: 0.75rem; border-radius: 6px; cursor: pointer; font-size: 1rem; }
        .btn:hover { background: #2563eb; }
        .error { color: #ef4444; margin-top: 0.5rem; font-size: 0.875rem; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo">🔗 Domain Redirect Tool</div>
        <form method="POST">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" class="form-control" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" class="form-control" required>
            </div>
            <button type="submit" class="btn">Login</button>
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
        </form>
    </div>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if db.verify_user(username, password):
            session['authenticated'] = True
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@require_auth
def dashboard():
    """Main dashboard"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/sync-all-domains', methods=['POST'])
@require_auth
def sync_all_domains():
    """Sync all domains from Namecheap to database with progress tracking"""
    try:
        if not email_manager:
            return jsonify({"error": "Email manager not initialized"}), 503
        
        # Get all domains from Namecheap
        namecheap_domains = email_manager.get_all_domains()
        
        if not namecheap_domains:
            return jsonify({"error": "No domains found in Namecheap"}), 404
        
        # This will be a long-running process
        # We'll return immediately and handle progress via WebSocket or polling
        # For now, return the count to start the process
        return jsonify({
            "status": "started",
            "total_domains": len(namecheap_domains),
            "message": "Domain sync started"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sync-domains-progress', methods=['GET'])
@require_auth
def sync_domains_progress():
    """Get progress of domain sync - this would need WebSocket in production"""
    # For now, return mock progress
    return jsonify({
        "status": "in_progress", 
        "processed": 50,
        "total": 417,
        "current_domain": "example.com"
    })

@app.route('/api/sync-single-domain', methods=['POST'])
@require_auth
def sync_single_domain():
    """Sync a single domain from Namecheap to database"""
    try:
        data = request.get_json()
        domain_name = data.get('domain_name')
        
        if not domain_name:
            return jsonify({"error": "Domain name required"}), 400
        
        # Add/update domain in database
        domain_number = db.add_or_update_domain(domain_name)
        
        # Get redirections from Namecheap
        redirections = email_manager.api_client.get_domain_redirections(domain_name)
        
        # Update redirections in database
        db.update_redirections(domain_name, redirections)
        
        return jsonify({
            "status": "success",
            "domain_name": domain_name,
            "domain_number": domain_number,
            "redirections_count": len(redirections)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/domains-from-db', methods=['GET'])
@require_auth
def get_domains_from_db():
    """Get all domains from database with client info"""
    try:
        domains = db.get_all_domains_with_redirections()
        clients = db.get_all_clients()
        
        return jsonify({
            "status": "success",
            "domains": domains,
            "clients": clients,
            "total_count": len(domains)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/clients', methods=['GET', 'POST'])
@require_auth
def manage_clients():
    """Get all clients or add new client"""
    if request.method == 'GET':
        try:
            clients = db.get_all_clients()
            return jsonify({"status": "success", "clients": clients})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            client_name = data.get('client_name', '').strip()
            
            if not client_name:
                return jsonify({"error": "Client name required"}), 400
            
            client_id = db.add_client(client_name)
            
            return jsonify({
                "status": "success",
                "client_id": client_id,
                "client_name": client_name
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/assign-client', methods=['POST'])
@require_auth
def assign_client():
    """Assign domain to client"""
    try:
        data = request.get_json()
        domain_name = data.get('domain_name')
        client_id = data.get('client_id')
        
        if not domain_name or not client_id:
            return jsonify({"error": "Domain name and client ID required"}), 400
        
        db.assign_domain_to_client(domain_name, client_id)
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bulk-update', methods=['POST'])
@require_auth
def bulk_update():
    """Bulk update domains with progress tracking"""
    try:
        data = request.get_json()
        updates = data.get('updates', [])  # List of {domain_name, name, target}
        
        if not updates:
            return jsonify({"error": "No updates provided"}), 400
        
        # Process updates with delays
        results = []
        
        for i, update in enumerate(updates):
            try:
                domain_name = update.get('domain_name')
                name = update.get('name', '@')
                target = update.get('target')
                
                # Update via Namecheap API
                success = email_manager.api_client.set_domain_redirection(domain_name, name, target)
                
                results.append({
                    "domain_name": domain_name,
                    "success": success,
                    "processed": i + 1,
                    "total": len(updates)
                })
                
                # Add delay between updates
                if i < len(updates) - 1:
                    import time
                    time.sleep(0.6)
                
            except Exception as e:
                results.append({
                    "domain_name": update.get('domain_name', 'unknown'),
                    "success": False,
                    "error": str(e),
                    "processed": i + 1,
                    "total": len(updates)
                })
        
        return jsonify({
            "status": "completed",
            "results": results,
            "total_processed": len(results)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/domains-with-redirections', methods=['GET'])
@require_auth
def get_domains_with_redirections():
    """Get all domains with their redirections for editing"""
    try:
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        # Test API connection first
        connection_test = email_manager.api_client.test_connection()
        if not connection_test:
            return jsonify({
                "status": "error",
                "message": "Namecheap API connection failed. Check credentials and IP whitelist.",
                "debug_info": {
                    "api_user": email_manager.api_client.api_user,
                    "client_ip": email_manager.api_client.client_ip,
                    "api_key_present": bool(email_manager.api_client.api_key)
                }
            }), 503
        
        # Get all domains
        domains = email_manager.get_all_domains()
        
        if not domains:
            return jsonify({
                "status": "error", 
                "message": "No domains found in your Namecheap account or API connection issue.",
                "debug_info": {
                    "connection_test": connection_test,
                    "api_user": email_manager.api_client.api_user,
                    "client_ip": email_manager.api_client.client_ip
                }
            }), 404
        
        # Get redirections for each domain (limit to first 50 with slower rate)
        domains_with_redirections = []
        processed = 0
        max_domains = min(100, len(domains))  # Process up to 100 domains with rate limiting
        
        for domain in domains[:max_domains]:
            try:
                redirections = email_manager.api_client.get_domain_redirections(domain)
                
                domains_with_redirections.append({
                    'name': domain,
                    'redirections': redirections,
                    'status': 'active'
                })
                
                processed += 1
                print(f"Processed {processed}/{max_domains}: {domain} - {len(redirections)} URL redirections")
                
                # Add delay to avoid rate limiting
                import time
                time.sleep(0.5)  # 500ms delay between requests to be safer
                
            except Exception as e:
                print(f"Error processing domain {domain}: {e}")
                # Add domain even if redirections failed to load
                domains_with_redirections.append({
                    'name': domain,
                    'redirections': [],
                    'status': 'error',
                    'error': str(e)
                })
                processed += 1
                continue
        
        return jsonify({
            "status": "success",
            "domains": domains_with_redirections,
            "total_domains_processed": processed,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve domains: {str(e)}"
        }), 500

@app.route('/api/update-redirection', methods=['POST'])
def update_redirection():
    """Update a domain redirection"""
    try:
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        data = request.get_json()
        domain = data.get('domain')
        name = data.get('name', '@')
        target = data.get('target')
        
        if not domain or not target:
            return jsonify({
                "status": "error",
                "message": "Domain and target URL are required."
            }), 400
        
        # Update the redirection using Namecheap API
        success = email_manager.api_client.set_domain_redirection(domain, name, target)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Successfully updated redirection for {domain}",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Failed to update redirection for {domain}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to update redirection: {str(e)}"
        }), 500

@app.route('/api/domains-batch', methods=['GET'])
def get_domains_batch():
    """Get a batch of domains with redirections (paginated)"""
    try:
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))  # Increased to 25 domains per batch
        
        # Get all domains
        domains = email_manager.get_all_domains()
        
        if not domains:
            return jsonify({
                "status": "error", 
                "message": "No domains found."
            }), 404
        
        # Calculate pagination
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, len(domains))
        batch_domains = domains[start_index:end_index]
        
        # Process batch with delays
        domains_with_redirections = []
        
        for i, domain in enumerate(batch_domains):
            try:
                redirections = email_manager.api_client.get_domain_redirections(domain)
                
                domains_with_redirections.append({
                    'name': domain,
                    'redirections': redirections,
                    'status': 'active'
                })
                
                print(f"Batch {page}: Processed {i+1}/{len(batch_domains)}: {domain} - {len(redirections)} redirections")
                
                # Add delay between requests
                if i < len(batch_domains) - 1:  # Don't delay after last item
                    import time
                    time.sleep(0.6)  # 600ms delay to be extra safe
                
            except Exception as e:
                print(f"Error processing domain {domain}: {e}")
                domains_with_redirections.append({
                    'name': domain,
                    'redirections': [],
                    'status': 'error',
                    'error': str(e)
                })
                continue
        
        return jsonify({
            "status": "success",
            "domains": domains_with_redirections,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_domains": len(domains),
                "total_pages": (len(domains) + per_page - 1) // per_page,
                "has_next": end_index < len(domains),
                "has_prev": page > 1
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve domain batch: {str(e)}"
        }), 500

@app.route('/api/all-redirections', methods=['GET'])
def get_all_redirections():
    """Get all domain URL redirections from all domains"""
    try:
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        # Test API connection first
        connection_test = email_manager.api_client.test_connection()
        if not connection_test:
            return jsonify({
                "status": "error",
                "message": "Namecheap API connection failed. Check credentials and IP whitelist.",
                "debug_info": {
                    "api_user": email_manager.api_client.api_user,
                    "client_ip": email_manager.api_client.client_ip,
                    "api_key_present": bool(email_manager.api_client.api_key)
                }
            }), 503
        
        # Get all domains
        domains = email_manager.get_all_domains()
        
        if not domains:
            return jsonify({
                "status": "error", 
                "message": "No domains found in your Namecheap account or API connection issue.",
                "debug_info": {
                    "connection_test": connection_test,
                    "api_user": email_manager.api_client.api_user,
                    "client_ip": email_manager.api_client.client_ip
                }
            }), 404
        
        # Get URL redirections for each domain
        all_redirections = []
        processed = 0
        
        for domain in domains:
            try:
                redirections = email_manager.api_client.get_domain_redirections(domain)
                
                for redirect in redirections:
                    all_redirections.append({
                        'domain': domain,
                        'type': redirect['type'],
                        'target': redirect['target'],
                        'status': 'active'  # Assume active if returned by API
                    })
                
                processed += 1
                print(f"Processed {processed}/{len(domains)}: {domain} - {len(redirections)} URL redirections")
                
            except Exception as e:
                print(f"Error processing domain {domain}: {e}")
                continue
        
        return jsonify({
            "status": "success",
            "redirections": all_redirections,
            "total_domains_processed": processed,
            "total_redirections": len(all_redirections),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve redirections: {str(e)}"
        }), 500

@app.route('/api/domains', methods=['GET'])
def get_domains():
    """Get all domains from Namecheap account"""
    try:
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        domains = email_manager.get_all_domains()
        
        return jsonify({
            "status": "success",
            "domains": domains,
            "total_count": len(domains),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve domains: {str(e)}"
        }), 500

@app.route('/api/debug', methods=['GET'])
def debug_api():
    """Debug Namecheap API connection"""
    import requests
    
    try:
        # Get our actual outbound IP
        try:
            ip_response = requests.get('https://httpbin.org/ip', timeout=10)
            actual_ip = ip_response.json().get('origin', 'Unknown')
        except:
            actual_ip = 'Could not detect'
        
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized",
                "env_vars": {
                    "NAMECHEAP_API_USER": bool(os.environ.get('NAMECHEAP_API_USER')),
                    "NAMECHEAP_API_KEY": bool(os.environ.get('NAMECHEAP_API_KEY')),
                    "NAMECHEAP_CLIENT_IP": os.environ.get('NAMECHEAP_CLIENT_IP', 'Missing')
                },
                "actual_outbound_ip": actual_ip
            })
        
        # Test connection
        connection_test = email_manager.api_client.test_connection()
        
        # Try to get domains
        domains = email_manager.get_all_domains()
        
        return jsonify({
            "status": "debug",
            "connection_test": connection_test,
            "actual_outbound_ip": actual_ip,
            "configured_ip": email_manager.api_client.client_ip,
            "api_credentials": {
                "api_user": email_manager.api_client.api_user,
                "client_ip": email_manager.api_client.client_ip,
                "api_key_length": len(email_manager.api_client.api_key) if email_manager.api_client.api_key else 0
            },
            "domains_found": len(domains),
            "sample_domains": domains[:3] if domains else [],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "actual_outbound_ip": actual_ip if 'actual_ip' in locals() else 'Unknown',
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "email-redirect-tool",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)