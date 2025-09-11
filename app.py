"""
Email Redirection Tool - Flask Application
Bulk email forwarding management for Namecheap domains
"""

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, flash
from flask_cors import CORS
import json
import os
from datetime import datetime
from namecheap_client import EmailRedirectionManager
import csv
import io

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
    <title>Email Redirection Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #f8fafc; }
        .header { background: #1e293b; color: white; padding: 1rem 2rem; }
        .logo { font-size: 1.5rem; font-weight: 700; }
        .container { max-width: 1200px; margin: 2rem auto; padding: 0 2rem; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem; }
        .btn { background: #3b82f6; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 1rem; }
        .btn-danger { background: #ef4444; }
        .btn-success { background: #10b981; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 600; }
        .form-control { width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 6px; }
        .table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        .table th, .table td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb; }
        .table th { background: #f9fafb; font-weight: 600; }
        .status-success { color: #10b981; font-weight: 600; }
        .status-error { color: #ef4444; font-weight: 600; }
        .progress-bar { width: 100%; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 8px; background: #3b82f6; transition: width 0.3s; }
        #results { display: none; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">📧 Email Redirection Tool</div>
    </div>
    
    <div class="container">
        <div class="card">
            <h1>Bulk Email Redirection Manager</h1>
            <p>Manage email forwarding for 200+ domains using Namecheap API</p>
        </div>
        
        <div class="card">
            <h2>Setup Email Forwarding Rules</h2>
            <div id="forwarding-rules">
                <div class="form-group">
                    <label>Forwarding Rules:</label>
                    <div id="rules-container">
                        <div class="rule-row" style="display: flex; gap: 1rem; margin-bottom: 0.5rem;">
                            <input type="text" class="form-control" placeholder="From (alias)" name="from_0" value="info">
                            <input type="text" class="form-control" placeholder="To (destination email)" name="to_0" value="">
                            <button type="button" class="btn btn-danger" onclick="removeRule(0)">Remove</button>
                        </div>
                    </div>
                    <button type="button" class="btn" onclick="addRule()">Add Rule</button>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Domain Management</h2>
            <div style="margin-bottom: 1rem;">
                <button class="btn" onclick="loadDomainsFromAPI()">Load Domains from Namecheap</button>
                <button class="btn" onclick="document.getElementById('csv-upload').click()">Upload CSV</button>
                <input type="file" id="csv-upload" accept=".csv" style="display: none;" onchange="loadDomainsFromCSV(this)">
            </div>
            
            <div class="form-group">
                <label>Domains to Process:</label>
                <textarea id="domains-list" class="form-control" rows="10" placeholder="Enter domain names, one per line"></textarea>
                <small>Enter domain names, one per line (e.g., example.com)</small>
            </div>
        </div>
        
        <div class="card">
            <h2>Bulk Processing</h2>
            <div style="margin-bottom: 1rem;">
                <button class="btn btn-success" onclick="startBulkProcessing()">Start Bulk Redirection</button>
                <button class="btn" onclick="previewChanges()">Preview Changes</button>
            </div>
            
            <div id="progress" style="display: none;">
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                <p id="progress-text">Processing...</p>
            </div>
        </div>
        
        <div class="card" id="results">
            <h2>Results</h2>
            <div id="results-summary"></div>
            <table class="table" id="results-table">
                <thead>
                    <tr>
                        <th>Domain</th>
                        <th>Status</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody id="results-body"></tbody>
            </table>
            <button class="btn" onclick="exportResults()">Export Results</button>
        </div>
    </div>

    <script>
        let ruleCount = 1;
        let processingResults = [];
        
        function addRule() {
            const container = document.getElementById('rules-container');
            const ruleDiv = document.createElement('div');
            ruleDiv.className = 'rule-row';
            ruleDiv.style.cssText = 'display: flex; gap: 1rem; margin-bottom: 0.5rem;';
            ruleDiv.innerHTML = `
                <input type="text" class="form-control" placeholder="From (alias)" name="from_${ruleCount}" value="">
                <input type="text" class="form-control" placeholder="To (destination email)" name="to_${ruleCount}" value="">
                <button type="button" class="btn btn-danger" onclick="removeRule(${ruleCount})">Remove</button>
            `;
            ruleDiv.id = `rule-${ruleCount}`;
            container.appendChild(ruleDiv);
            ruleCount++;
        }
        
        function removeRule(id) {
            const ruleDiv = document.getElementById(`rule-${id}`);
            if (ruleDiv) ruleDiv.remove();
        }
        
        function getForwardingRules() {
            const rules = [];
            const container = document.getElementById('rules-container');
            const rows = container.querySelectorAll('.rule-row');
            
            rows.forEach(row => {
                const fromInput = row.querySelector('input[name^="from_"]');
                const toInput = row.querySelector('input[name^="to_"]');
                
                if (fromInput.value.trim() && toInput.value.trim()) {
                    rules.push({
                        from: fromInput.value.trim(),
                        to: toInput.value.trim()
                    });
                }
            });
            
            return rules;
        }
        
        function getDomainsList() {
            const domainsText = document.getElementById('domains-list').value;
            return domainsText.split('\\n')
                .map(domain => domain.trim())
                .filter(domain => domain.length > 0);
        }
        
        async function loadDomainsFromAPI() {
            try {
                document.getElementById('domains-list').value = 'Loading domains...';
                
                const response = await fetch('/api/domains');
                const data = await response.json();
                
                if (data.status === 'success') {
                    const domainsList = data.domains.join('\\n');
                    document.getElementById('domains-list').value = domainsList;
                    alert(`Loaded ${data.domains.length} domains from Namecheap API`);
                } else {
                    alert(`Error: ${data.message}`);
                    document.getElementById('domains-list').value = '';
                }
            } catch (error) {
                alert(`Error loading domains: ${error.message}`);
                document.getElementById('domains-list').value = '';
            }
        }
        
        function loadDomainsFromCSV(input) {
            const file = input.files[0];
            if (!file) return;
            
            const reader = new FileReader();
            reader.onload = function(e) {
                const csv = e.target.result;
                const lines = csv.split('\\n');
                const domains = lines
                    .map(line => line.split(',')[0].trim())
                    .filter(domain => domain.length > 0 && domain !== 'domain');
                
                document.getElementById('domains-list').value = domains.join('\\n');
                alert(`Loaded ${domains.length} domains from CSV`);
            };
            reader.readAsText(file);
        }
        
        async function previewChanges() {
            const rules = getForwardingRules();
            const domains = getDomainsList();
            
            if (rules.length === 0) {
                alert('Please add at least one forwarding rule');
                return;
            }
            
            if (domains.length === 0) {
                alert('Please add at least one domain');
                return;
            }
            
            let preview = `Preview Changes:\\n\\n`;
            preview += `Forwarding Rules (${rules.length}):\\n`;
            rules.forEach(rule => {
                preview += `  ${rule.from} → ${rule.to}\\n`;
            });
            
            preview += `\\nDomains to Process (${domains.length}):\\n`;
            domains.slice(0, 10).forEach(domain => {
                preview += `  ${domain}\\n`;
            });
            
            if (domains.length > 10) {
                preview += `  ... and ${domains.length - 10} more domains\\n`;
            }
            
            alert(preview);
        }
        
        async function startBulkProcessing() {
            const rules = getForwardingRules();
            const domains = getDomainsList();
            
            if (rules.length === 0) {
                alert('Please add at least one forwarding rule');
                return;
            }
            
            if (domains.length === 0) {
                alert('Please add at least one domain');
                return;
            }
            
            if (!confirm(`Are you sure you want to process ${domains.length} domains?`)) {
                return;
            }
            
            // Show progress
            document.getElementById('progress').style.display = 'block';
            document.getElementById('results').style.display = 'none';
            
            try {
                const response = await fetch('/api/bulk-redirect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        domains: domains,
                        forwarding_rules: rules
                    })
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    displayResults(data.results);
                } else {
                    alert(`Error: ${data.message}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            } finally {
                document.getElementById('progress').style.display = 'none';
            }
        }
        
        function displayResults(results) {
            document.getElementById('results').style.display = 'block';
            
            // Update summary
            const summary = document.getElementById('results-summary');
            summary.innerHTML = `
                <h3>Processing Complete</h3>
                <p>Total Processed: ${results.total_processed}</p>
                <p>Successful: <span class="status-success">${results.successful.length}</span></p>
                <p>Failed: <span class="status-error">${results.failed.length}</span></p>
                <p>Duration: ${results.duration}</p>
            `;
            
            // Update table
            const tbody = document.getElementById('results-body');
            tbody.innerHTML = '';
            
            // Add successful domains
            results.successful.forEach(domain => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = domain;
                row.insertCell(1).innerHTML = '<span class="status-success">Success</span>';
                row.insertCell(2).textContent = 'Email forwarding configured';
            });
            
            // Add failed domains
            results.failed.forEach(failed => {
                const row = tbody.insertRow();
                row.insertCell(0).textContent = failed.domain;
                row.insertCell(1).innerHTML = '<span class="status-error">Failed</span>';
                row.insertCell(2).textContent = failed.error;
            });
            
            processingResults = results;
        }
        
        function exportResults() {
            if (processingResults.length === 0) {
                alert('No results to export');
                return;
            }
            
            let csv = 'Domain,Status,Message\\n';
            
            processingResults.successful.forEach(domain => {
                csv += `${domain},Success,Email forwarding configured\\n`;
            });
            
            processingResults.failed.forEach(failed => {
                csv += `${failed.domain},Failed,"${failed.error}"\\n`;
            });
            
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `email_redirect_results_${new Date().toISOString().slice(0,10)}.csv`;
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

@app.route('/api/bulk-redirect', methods=['POST'])
def bulk_redirect():
    """Handle bulk email redirection"""
    try:
        if not email_manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        data = request.get_json()
        
        if not data or 'domains' not in data or 'forwarding_rules' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required fields: domains and forwarding_rules"
            }), 400
        
        domains = data['domains']
        forwarding_rules = data['forwarding_rules']
        
        if not domains or not forwarding_rules:
            return jsonify({
                "status": "error",
                "message": "Domains and forwarding rules cannot be empty"
            }), 400
        
        # Process bulk redirection
        results = email_manager.bulk_set_forwarding(domains, forwarding_rules)
        
        return jsonify({
            "status": "success",
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Bulk redirection failed: {str(e)}"
        }), 500

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