"""
Email Redirection Tool - Flask Application
View existing email forwarding for Namecheap domains
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import os
from datetime import datetime
from namecheap_client import EmailRedirectionManager

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
        #loading, #redirections-view, #raw-data { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🔍 Domain Email Redirections Viewer</div>
    </div>
    
    <div class="container">
        <div class="card">
            <h1>Domain Email Redirection Viewer</h1>
            <p>View existing email forwarding for all your domains using Namecheap API</p>
        </div>
        
        <div class="card">
            <h2>Load Domain Redirections</h2>
            <div style="margin-bottom: 1rem;">
                <button class="btn btn-success" onclick="loadAllRedirections()">Load All Domain Redirections</button>
                <button class="btn" onclick="exportRedirections()">Export to CSV</button>
            </div>
            
            <div id="loading">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%;"></div>
                </div>
                <p id="progress-text">Loading redirections from domains...</p>
            </div>
        </div>
        
        <div class="card" id="redirections-view">
            <h2>Domain Email Redirections</h2>
            <div id="redirections-summary"></div>
            
            <div style="margin: 1rem 0;">
                <label>Group by:</label>
                <select class="form-control" id="group-filter" onchange="updateGrouping()" style="width: auto;">
                    <option value="target">Target Email</option>
                    <option value="domain">Domain</option>
                    <option value="alias">Email Alias</option>
                </select>
                
                <input type="text" class="form-control" id="search-filter" placeholder="Search domains or emails..." onkeyup="filterResults()" style="width: 300px;">
            </div>
            
            <div id="grouped-redirections"></div>
        </div>
        
        <div class="card" id="raw-data">
            <h2>Raw Data View</h2>
            <table class="table" id="redirections-table">
                <thead>
                    <tr>
                        <th>Domain</th>
                        <th>Email Alias</th>
                        <th>Redirects To</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="redirections-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        let allRedirections = [];
        let groupedData = {};
        
        async function loadAllRedirections() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('redirections-view').style.display = 'none';
                document.getElementById('raw-data').style.display = 'none';
                
                const response = await fetch('/api/all-redirections');
                const data = await response.json();
                
                if (data.status === 'success') {
                    allRedirections = data.redirections;
                    displayRedirections();
                    document.getElementById('redirections-view').style.display = 'block';
                    document.getElementById('raw-data').style.display = 'block';
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error loading redirections: ${error.message}`);
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
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
                row.insertCell(1).textContent = redirect.alias;
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
                    case 'alias':
                        key = redirect.alias;
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
                            <h3>${groupBy === 'target' ? '📧' : groupBy === 'domain' ? '🌐' : '📮'} ${group}</h3>
                            <span class="group-count">${redirects.length} ${redirects.length === 1 ? 'redirect' : 'redirects'}</span>
                        </div>
                        <div>
                `;
                
                redirects.forEach(redirect => {
                    if (groupBy === 'target') {
                        html += `<div class="redirect-item">
                            <strong>${redirect.domain}</strong> → ${redirect.alias}@${redirect.domain}
                        </div>`;
                    } else if (groupBy === 'domain') {
                        html += `<div class="redirect-item">
                            ${redirect.alias}@${redirect.domain} → <strong>${redirect.target}</strong>
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
            
            let csv = 'Domain,Email Alias,Redirects To,Status\\n';
            
            allRedirections.forEach(redirect => {
                csv += `${redirect.domain},${redirect.alias},${redirect.target},${redirect.status}\\n`;
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

# Initialize email redirection manager
email_manager = None
try:
    email_manager = EmailRedirectionManager()
    print("Email Redirection Manager initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize Email Redirection Manager: {e}")

@app.route('/')
def dashboard():
    """Main dashboard"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/all-redirections', methods=['GET'])
def get_all_redirections():
    """Get all email redirections from all domains"""
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
        
        # Get redirections for each domain
        all_redirections = []
        processed = 0
        
        for domain in domains:
            try:
                redirections = email_manager.api_client.get_email_forwarding(domain)
                
                for redirect in redirections:
                    all_redirections.append({
                        'domain': domain,
                        'alias': redirect['from'],
                        'target': redirect['to'],
                        'status': 'active'  # Assume active if returned by API
                    })
                
                processed += 1
                print(f"Processed {processed}/{len(domains)}: {domain} - {len(redirections)} redirections")
                
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
    try:
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized",
                "env_vars": {
                    "NAMECHEAP_API_USER": bool(os.environ.get('NAMECHEAP_API_USER')),
                    "NAMECHEAP_API_KEY": bool(os.environ.get('NAMECHEAP_API_KEY')),
                    "NAMECHEAP_CLIENT_IP": os.environ.get('NAMECHEAP_CLIENT_IP', 'Missing')
                }
            })
        
        # Test connection
        connection_test = email_manager.api_client.test_connection()
        
        # Try to get domains
        domains = email_manager.get_all_domains()
        
        return jsonify({
            "status": "debug",
            "connection_test": connection_test,
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