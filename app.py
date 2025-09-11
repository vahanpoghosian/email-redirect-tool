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
        .domain-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; background: white; }
        .domain-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .domain-name { font-size: 1.2rem; font-weight: 600; color: #1e293b; }
        .redirection-row { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem; padding: 0.5rem; background: #f8fafc; border-radius: 4px; }
        .redirection-input { padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 4px; flex: 1; }
        .btn-small { padding: 0.5rem 1rem; font-size: 0.875rem; }
        .status-updating { color: #f59e0b; }
        .add-redirection { margin-top: 0.5rem; }
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
            <h2>Load All Domains</h2>
            <div style="margin-bottom: 1rem;">
                <button class="btn btn-success" onclick="loadAllDomains()">Load All Domains</button>
                <button class="btn" onclick="exportRedirections()">Export to CSV</button>
            </div>
            
            <div id="loading">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%;"></div>
                </div>
                <p id="progress-text">Loading domains...</p>
            </div>
        </div>
        
        <div class="card" id="domains-view">
            <h2>All Domains with Redirections</h2>
            <div id="domains-summary"></div>
            
            <div style="margin: 1rem 0;">
                <input type="text" class="form-control" id="search-filter" placeholder="Search domains..." onkeyup="filterDomains()" style="width: 300px;">
                <button class="btn" onclick="loadMoreDomains()" id="load-more-btn" style="display: none;">Load More Domains</button>
            </div>
            
            <div id="domains-container"></div>
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
        let currentPage = 0;
        let domainsPerPage = 10;
        let isLoading = false;
        let allRedirections = [];
        let groupedData = {};
        
        async function loadAllDomains() {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('domains-view').style.display = 'none';
                document.getElementById('raw-data').style.display = 'none';
                
                const response = await fetch('/api/domains-with-redirections');
                const data = await response.json();
                
                if (data.status === 'success') {
                    allDomains = data.domains;
                    currentPage = 0;
                    document.getElementById('domains-container').innerHTML = '';
                    displayDomains();
                    document.getElementById('domains-view').style.display = 'block';
                    setupInfiniteScroll();
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error loading domains: ${error.message}`);
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }
        
        function displayDomains() {
            const container = document.getElementById('domains-container');
            const summary = document.getElementById('domains-summary');
            
            // Update summary
            const totalDomains = allDomains.length;
            const domainsWithRedirects = allDomains.filter(d => d.redirections.length > 0).length;
            
            summary.innerHTML = `
                <div style="display: flex; gap: 2rem; margin-bottom: 1rem; flex-wrap: wrap;">
                    <div><strong>Total Domains:</strong> ${totalDomains}</div>
                    <div><strong>Domains with Redirects:</strong> ${domainsWithRedirects}</div>
                </div>
            `;
            
            loadMoreDomains();
        }
        
        function loadMoreDomains() {
            if (isLoading) return;
            
            isLoading = true;
            const container = document.getElementById('domains-container');
            const start = currentPage * domainsPerPage;
            const end = Math.min(start + domainsPerPage, allDomains.length);
            
            for (let i = start; i < end; i++) {
                const domain = allDomains[i];
                const domainCard = createDomainCard(domain);
                container.appendChild(domainCard);
            }
            
            currentPage++;
            isLoading = false;
            
            // Show/hide load more button
            const loadMoreBtn = document.getElementById('load-more-btn');
            if (end >= allDomains.length) {
                loadMoreBtn.style.display = 'none';
            } else {
                loadMoreBtn.style.display = 'inline-block';
            }
        }
        
        function createDomainCard(domain) {
            const card = document.createElement('div');
            card.className = 'domain-card';
            card.innerHTML = `
                <div class="domain-header">
                    <div class="domain-name">${domain.name}</div>
                    <div style="font-size: 0.875rem; color: #64748b;">
                        ${domain.redirections.length} redirect${domain.redirections.length !== 1 ? 's' : ''}
                    </div>
                </div>
                <div id="redirections-${domain.name.replace(/\./g, '-')}">
                    ${domain.redirections.map((redirect, index) => createRedirectionRow(domain.name, redirect, index)).join('')}
                </div>
                <div class="add-redirection">
                    <button class="btn btn-small" onclick="addRedirection('${domain.name}')">+ Add Redirection</button>
                </div>
            `;
            return card;
        }
        
        function createRedirectionRow(domainName, redirect, index) {
            const safeId = domainName.replace(/\./g, '-');
            return `
                <div class="redirection-row" data-index="${index}">
                    <label style="min-width: 80px;">From:</label>
                    <input type="text" class="redirection-input" value="${redirect.name || '@'}" 
                           id="name-${safeId}-${index}" placeholder="@ or subdomain">
                    <label style="min-width: 80px;">Redirect to:</label>
                    <input type="text" class="redirection-input" value="${redirect.target}" 
                           id="target-${safeId}-${index}" placeholder="https://example.com">
                    <button class="btn btn-small btn-success" onclick="updateRedirection('${domainName}', ${index})">
                        Update
                    </button>
                    <button class="btn btn-small" style="background: #ef4444;" onclick="removeRedirection('${domainName}', ${index})">
                        Remove
                    </button>
                    <span id="status-${safeId}-${index}" class="status-updating" style="display: none;">Updating...</span>
                </div>
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
        
        async function updateRedirection(domainName, index) {
            const safeId = domainName.replace(/\./g, '-');
            const nameField = document.getElementById(`name-${safeId}-${index}`);
            const targetField = document.getElementById(`target-${safeId}-${index}`);
            const statusSpan = document.getElementById(`status-${safeId}-${index}`);
            
            const name = nameField.value.trim();
            const target = targetField.value.trim();
            
            if (!target) {
                alert('Please enter a target URL');
                return;
            }
            
            // Show loading status
            statusSpan.style.display = 'inline';
            statusSpan.textContent = 'Updating...';
            statusSpan.className = 'status-updating';
            
            try {
                const response = await fetch('/api/update-redirection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        domain: domainName,
                        name: name,
                        target: target
                    })
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    statusSpan.textContent = 'Updated!';
                    statusSpan.className = 'status-success';
                    
                    // Update local data
                    const domain = allDomains.find(d => d.name === domainName);
                    if (domain && domain.redirections[index]) {
                        domain.redirections[index].name = name;
                        domain.redirections[index].target = target;
                    }
                } else {
                    statusSpan.textContent = 'Error!';
                    statusSpan.className = 'status-error';
                    alert(`Update failed: ${result.message}`);
                }
            } catch (error) {
                statusSpan.textContent = 'Error!';
                statusSpan.className = 'status-error';
                alert(`Update failed: ${error.message}`);
            }
            
            // Hide status after 3 seconds
            setTimeout(() => {
                statusSpan.style.display = 'none';
            }, 3000);
        }
        
        function addRedirection(domainName) {
            const domain = allDomains.find(d => d.name === domainName);
            if (!domain) return;
            
            const newRedirect = { name: '@', target: '', type: 'URL Redirect' };
            domain.redirections.push(newRedirect);
            
            const safeId = domainName.replace(/\./g, '-');
            const container = document.getElementById(`redirections-${safeId}`);
            const newRow = document.createElement('div');
            newRow.innerHTML = createRedirectionRow(domainName, newRedirect, domain.redirections.length - 1);
            container.appendChild(newRow.firstElementChild);
        }
        
        function removeRedirection(domainName, index) {
            if (!confirm('Remove this redirection?')) return;
            
            const domain = allDomains.find(d => d.name === domainName);
            if (!domain) return;
            
            domain.redirections.splice(index, 1);
            
            // Refresh the domain card
            const container = document.getElementById('domains-container');
            const cards = container.children;
            for (let card of cards) {
                if (card.innerHTML.includes(domainName)) {
                    card.replaceWith(createDomainCard(domain));
                    break;
                }
            }
        }
        
        function filterDomains() {
            const searchTerm = document.getElementById('search-filter').value.toLowerCase();
            const cards = document.querySelectorAll('.domain-card');
            
            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                card.style.display = text.includes(searchTerm) ? 'block' : 'none';
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

@app.route('/api/domains-with-redirections', methods=['GET'])
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
        
        # Get redirections for each domain
        domains_with_redirections = []
        processed = 0
        
        for domain in domains:
            try:
                redirections = email_manager.api_client.get_domain_redirections(domain)
                
                domains_with_redirections.append({
                    'name': domain,
                    'redirections': redirections,
                    'status': 'active'
                })
                
                processed += 1
                print(f"Processed {processed}/{len(domains)}: {domain} - {len(redirections)} URL redirections")
                
            except Exception as e:
                print(f"Error processing domain {domain}: {e}")
                # Add domain even if redirections failed to load
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