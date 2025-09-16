"""
Email Redirection Tool - Flask Application
View existing email forwarding for Namecheap domains
"""

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from functools import wraps
from namecheap_client import EmailRedirectionManager
from models import Database

app = Flask(__name__, static_folder='frontend/build/static', static_url_path='/static')
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
                <form method="POST" action="/sync-domains" style="display: inline;" onsubmit="startSyncOperation(event);">
                    <button class="btn btn-success" type="submit">🔄 Sync All Domains from Namecheap</button>
                </form>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <input type="text" id="bulk-redirect-url" class="form-control" placeholder="https://redirect-url.com" style="width: 250px;">
                    <button class="btn" onclick="performBulkUpdate()" id="bulk-update-btn">🔧 Bulk Update</button>
                </div>
                <a href="/clients" class="btn">👥 Manage Clients</a>
                <form method="POST" action="/export-csv" style="display: inline;">
                    <button class="btn" type="submit">📁 Export to CSV</button>
                </form>
                <a href="/logout" class="btn" style="background: #ef4444;">🚪 Logout</a>
            </div>
            
            <div style="margin-bottom: 1rem;">
                <form method="GET" action="/" style="display: flex; gap: 1rem; align-items: center;">
                    <input type="text" name="search" class="form-control" placeholder="Search domains..." value="{{ request.args.get('search', '') }}" style="width: 300px;">
                    <button class="btn" type="submit">🔍 Search</button>
                    <a href="/" class="btn" style="background: #6b7280;">Clear</a>
                </form>
            </div>
            
            <!-- Sync status display -->
            <div id="sync-status" style="display: none; margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px; border-left: 4px solid #3b82f6; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div id="sync-text" style="font-weight: 600; margin-bottom: 0.5rem; color: #1e293b;">Status: In Progress</div>
                <div id="sync-details" style="color: #6b7280;">Starting sync...</div>
                <div class="progress-bar" style="margin-top: 0.5rem;">
                    <div id="sync-progress-fill" class="progress-fill" style="width: 0%;"></div>
                </div>
            </div>
            
            <!-- Bulk update status display -->
            <div id="bulk-status" style="display: none; margin-bottom: 1rem; padding: 1rem; background: #f8fafc; border-radius: 8px; border-left: 4px solid #10b981; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <div id="bulk-text" style="font-weight: 600; margin-bottom: 0.5rem; color: #1e293b;">Bulk Update Status: In Progress</div>
                <div id="bulk-details" style="color: #6b7280;">Starting bulk update...</div>
            </div>
        </div>
        
        <div class="card">
            <h2>All Domains with URL Redirections</h2>
            <p style="color: #6b7280; margin-bottom: 1rem;">Found {{ domains|length }} domains {% if request.args.get('search') %}(filtered by "{{ request.args.get('search') }}"){% endif %}</p>
            
            <table class="table">
                <thead>
                    <tr>
                        <th style="width: 5%;"><input type="checkbox" id="select-all"></th>
                        <th style="width: 5%;">#</th>
                        <th style="width: 25%;">Domain</th>
                        <th style="width: 35%;">Redirect Target</th>
                        <th style="width: 15%;">Client</th>
                        <th style="width: 15%;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% if domains %}
                        {% for domain in domains %}
                            {% if domain.redirections %}
                                {% for redirect in domain.redirections %}
                                <tr>
                                <td><input type="checkbox" name="domain_check" value="{{ domain.domain_name }}"></td>
                                <td><strong>#{{ domain.domain_number or 'N/A' }}</strong></td>
                                <td>{{ domain.domain_name }}</td>
                                <td>
                                    <form method="POST" action="/update-redirect" style="display: inline-flex; align-items: center; gap: 0.5rem; width: 100%;" onsubmit="event.preventDefault(); handleRedirectSubmit(this, '{{ domain.domain_name }}');">
                                        <input type="hidden" name="domain" value="{{ domain.domain_name }}">
                                        <input type="text" name="target" value="{{ redirect.target }}" class="form-control" placeholder="https://example.com" style="flex: 1;">
                                        <button type="submit" class="btn btn-small btn-success">Save</button>
                                    </form>
                                </td>
                                <td>
                                    <select class="form-control" onchange="updateDomainClient('{{ domain.domain_name }}', this.value)" style="width: 100%;">
                                        <option value="" {% if not domain.client_id %}selected{% endif %}>Unassigned</option>
                                        {% for client in clients %}
                                            <option value="{{ client.id }}" {% if client.id == domain.client_id %}selected{% endif %}>{{ client.name }}</option>
                                        {% endfor %}
                                    </select>
                                </td>
                                <td>
                                    <!-- Status will be shown only after save action -->
                                    <span class="sync-status-cell" id="status-{{ domain.domain_name.replace('.', '-') }}" style="min-height: 1.5rem; display: inline-block;">
                                        <!-- Empty by default, filled after Save action -->
                                    </span>
                                </td>
                                </tr>
                                {% endfor %}
                            {% else %}
                                <tr>
                                <td><input type="checkbox" name="domain_check" value="{{ domain.domain_name }}"></td>
                                <td><strong>#{{ domain.domain_number or 'N/A' }}</strong></td>
                                <td>{{ domain.domain_name }}</td>
                                <td>
                                    <form method="POST" action="/update-redirect" style="display: inline-flex; align-items: center; gap: 0.5rem; width: 100%;" onsubmit="event.preventDefault(); handleRedirectSubmit(this, '{{ domain.domain_name }}');">
                                        <input type="hidden" name="domain" value="{{ domain.domain_name }}">
                                        <input type="text" name="target" value="" class="form-control" placeholder="https://example.com" style="flex: 1;">
                                        <button type="submit" class="btn btn-small btn-success">Save</button>
                                    </form>
                                </td>
                                <td>
                                    <select class="form-control" onchange="updateDomainClient('{{ domain.domain_name }}', this.value)" style="width: 100%;">
                                        <option value="" {% if not domain.client_id %}selected{% endif %}>Unassigned</option>
                                        {% for client in clients %}
                                            <option value="{{ client.id }}" {% if client.id == domain.client_id %}selected{% endif %}>{{ client.name }}</option>
                                        {% endfor %}
                                    </select>
                                </td>
                                <td>
                                    <!-- Status will be shown only after save action -->
                                    <span class="sync-status-cell" id="status-{{ domain.domain_name.replace('.', '-') }}" style="min-height: 1.5rem; display: inline-block;">
                                        <!-- Empty by default, filled after Save action -->
                                    </span>
                                </td>
                                </tr>
                            {% endif %}
                        {% endfor %}
                    {% else %}
                        <tr>
                            <td colspan="6" style="text-align: center; padding: 2rem; color: #6b7280;">
                                No domains found. <a href="javascript:void(0)" onclick="location.reload()">Click here to refresh</a> or <a href="/sync-domains">sync domains from Namecheap</a>.
                            </td>
                        </tr>
                    {% endif %}
                </tbody>
            </table>
            
            <!-- Bulk update modal will be handled by JavaScript -->
            
        </div>
    </div>

    <script>
        // Global sync monitoring
        let syncProgressInterval = null;
        
        // Simple checkbox select all functionality
        document.addEventListener('DOMContentLoaded', function() {
            const selectAllCheckbox = document.getElementById('select-all');
            if (selectAllCheckbox) {
                selectAllCheckbox.addEventListener('change', function() {
                    const checkboxes = document.querySelectorAll('input[name="domain_check"]');
                    checkboxes.forEach(checkbox => {
                        checkbox.checked = this.checked;
                    });
                });
            }
            
            // Start sync progress monitoring if sync is already running
            checkSyncStatus();
            
            // Collect selected domains for bulk update
            function collectSelectedDomains() {
                const selected = [];
                const checkboxes = document.querySelectorAll('input[name="domain_check"]:checked');
                checkboxes.forEach(checkbox => {
                    selected.push(checkbox.value);
                });
                return selected;
            }
            
            // Add selected domains as hidden inputs to bulk update form
            const bulkForm = document.querySelector('form[action="/bulk-update"]');
            if (bulkForm) {
                bulkForm.addEventListener('submit', function(e) {
                    const selectedDomains = collectSelectedDomains();
                    if (selectedDomains.length === 0) {
                        e.preventDefault();
                        alert('Please select at least one domain for bulk update.');
                        return;
                    }
                    
                    // Remove existing hidden inputs
                    const existingInputs = this.querySelectorAll('input[name="selected_domains"]');
                    existingInputs.forEach(input => input.remove());
                    
                    // Add selected domains as hidden inputs
                    selectedDomains.forEach(domain => {
                        const input = document.createElement('input');
                        input.type = 'hidden';
                        input.name = 'selected_domains';
                        input.value = domain;
                        this.appendChild(input);
                    });
                });
            }
        });
        
        
        
        function createDomainTableRow(domain, redirect, redirectIndex) {
            const tbody = document.getElementById('domains-tbody');
            if (!tbody) return;
            
            const row = tbody.insertRow();
            row.className = 'domain-row';
            
            // Checkbox for bulk selection
            const checkboxCell = row.insertCell(0);
            checkboxCell.innerHTML = '<input type="checkbox" class="domain-checkbox" value="' + domain.domain_name + '" onchange="updateBulkButtonState()">';
            
            // Domain number
            const numberCell = row.insertCell(1);
            numberCell.innerHTML = '<strong>#' + (domain.domain_number || 'N/A') + '</strong>';
            
            // Domain name (editable)
            const domainCell = row.insertCell(2);
            domainCell.innerHTML = '<input type="text" value="' + domain.domain_name + '" class="form-control" onchange="updateDomain(this, \'' + domain.domain_name + '\', \'domain\')">';
            
            // Redirect target (editable)
            const redirectCell = row.insertCell(3);
            const redirectTarget = redirect ? redirect.target : '';
            redirectCell.innerHTML = '<input type="text" value="' + redirectTarget + '" class="form-control" placeholder="https://example.com" onchange="updateDomainRedirect(this, \'' + domain.domain_name + '\', \'redirect\')">';
            
            // Client dropdown
            const clientCell = row.insertCell(4);
            clientCell.innerHTML = '<select class="form-control" onchange="updateDomainClient(this, \'' + domain.domain_name + '\')" id="client-' + domain.domain_name.replace(/\./g, '-') + '"><option value="">Unassigned</option></select>';
            
            // Load clients into dropdown
            loadClientsIntoDropdown(domain.domain_name, domain.client_id);
            
            // Status
            const statusCell = row.insertCell(5);
            const syncStatus = domain.sync_status || 'unchanged';
            let statusHtml = '';
            let statusColor = '';
            
            if (syncStatus === 'synced') {
                statusHtml = '✅ Synced';
                statusColor = '#10b981'; // Green
            } else if (syncStatus === 'not_synced') {
                statusHtml = '❌ Not Synced';
                statusColor = '#ef4444'; // Red
            } else {
                statusHtml = '⚪ Unchanged';
                statusColor = '#6b7280'; // Gray
            }
            
            statusCell.innerHTML = '<span style="color: ' + statusColor + '; font-weight: 600;">' + statusHtml + '</span>';
        }
        
        function createDomainsCard() {
            const container = document.querySelector('.container');
            const domainsCard = document.createElement('div');
            domainsCard.className = 'card';
            domainsCard.id = 'domains-view';
            domainsCard.innerHTML = 
                '<h2>All Domains with URL Redirections</h2>' +
                '<div id="domains-summary"></div>' +
                '<div style="margin: 1rem 0; display: flex; gap: 0.5rem; align-items: center;">' +
                    '<button class="btn" onclick="clearAllFilters()" style="background: #6b7280;">Clear All Filters</button>' +
                '</div>' +
                '<table class="table">' +
                    '<thead>' +
                        '<tr>' +
                            '<th>' +
                                '<input type="checkbox" id="select-all-domains" onclick="toggleAllDomains(this)">' +
                            '</th>' +
                            '<th>Number</th>' +
                            '<th>Domain</th>' +
                            '<th>Redirect Target</th>' +
                            '<th>Client</th>' +
                            '<th>Status</th>' +
                        '</tr>' +
                        '<tr style="background: #f8fafc;">' +
                            '<th></th>' +
                            '<th>' +
                                '<input type="text" class="form-control" id="number-filter" placeholder="Filter #..." onkeyup="applyFilters()" style="width: 100%; font-size: 0.875rem; padding: 0.375rem;">' +
                            '</th>' +
                            '<th>' +
                                '<input type="text" class="form-control" id="domain-filter" placeholder="Filter domains..." onkeyup="applyFilters()" style="width: 100%; font-size: 0.875rem; padding: 0.375rem;">' +
                            '</th>' +
                            '<th>' +
                                '<input type="text" class="form-control" id="redirect-filter" placeholder="Filter redirects..." onkeyup="applyFilters()" style="width: 100%; font-size: 0.875rem; padding: 0.375rem;">' +
                            '</th>' +
                            '<th>' +
                                '<select class="form-control" id="client-filter" onchange="applyFilters()" style="width: 100%; font-size: 0.875rem; padding: 0.375rem;">' +
                                    '<option value="">All Clients</option>' +
                                '</select>' +
                            '</th>' +
                            '<th>' +
                                '<select class="form-control" id="status-filter" onchange="applyFilters()" style="width: 100%; font-size: 0.875rem; padding: 0.375rem;">' +
                                    '<option value="">All Status</option>' +
                                    '<option value="synced">Synced</option>' +
                                    '<option value="not_synced">Not Synced</option>' +
                                    '<option value="unchanged">Unchanged</option>' +
                                '</select>' +
                            '</th>' +
                        '</tr>' +
                    '</thead>' +
                    '<tbody id="domains-tbody"></tbody>' +
                '</table>';
            container.appendChild(domainsCard);
            return domainsCard;
        }
        
        function toggleAllDomains(selectAllCheckbox) {
            const domainCheckboxes = document.querySelectorAll('.domain-checkbox');
            domainCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
            updateBulkButtonState();
        }
        
        function updateBulkButtonState() {
            const selectedCheckboxes = document.querySelectorAll('.domain-checkbox:checked');
            const bulkButton = document.querySelector('[onclick="showBulkUpdateModal()"]');
            
            if (bulkButton) {
                if (selectedCheckboxes.length > 0) {
                    bulkButton.textContent = `🔧 Bulk Update (${selectedCheckboxes.length})`;
                    bulkButton.style.background = '#3b82f6';
                } else {
                    bulkButton.textContent = '🔧 Bulk Update';
                    bulkButton.style.background = '';
                }
            }
        }
        
        // Collect selected domains for bulk update
        function collectSelectedDomains() {
            const selected = [];
            const checkboxes = document.querySelectorAll('input[name="domain_check"]:checked');
            checkboxes.forEach(checkbox => {
                selected.push(checkbox.value);
            });
            return selected;
        }
        
        function applyFilters() {
            const numberFilter = document.getElementById('number-filter').value.toLowerCase();
            const domainFilter = document.getElementById('domain-filter').value.toLowerCase();
            const redirectFilter = document.getElementById('redirect-filter').value.toLowerCase();
            const clientFilter = document.getElementById('client-filter').value;
            const statusFilter = document.getElementById('status-filter').value;
            
            const rows = document.querySelectorAll('#domains-tbody tr');
            let visibleCount = 0;
            
            rows.forEach(row => {
                const numberText = row.cells[1].textContent.toLowerCase();
                const domainInput = row.cells[2].querySelector('input');
                const domainText = domainInput ? domainInput.value.toLowerCase() : '';
                const redirectInput = row.cells[3].querySelector('input');
                const redirectText = redirectInput ? redirectInput.value.toLowerCase() : '';
                const clientSelect = row.cells[4].querySelector('select');
                const clientText = clientSelect ? clientSelect.selectedOptions[0].textContent : '';
                const statusSpan = row.cells[5].querySelector('span');
                const statusText = statusSpan ? statusSpan.textContent.toLowerCase() : '';
                
                const numberMatch = !numberFilter || numberText.includes(numberFilter);
                const domainMatch = !domainFilter || domainText.includes(domainFilter);
                const redirectMatch = !redirectFilter || redirectText.includes(redirectFilter);
                const clientMatch = !clientFilter || clientText === clientFilter;
                
                let statusMatch = true;
                if (statusFilter) {
                    if (statusFilter === 'synced' && !statusText.includes('synced')) {
                        statusMatch = false;
                    } else if (statusFilter === 'not_synced' && !statusText.includes('not synced')) {
                        statusMatch = false;
                    } else if (statusFilter === 'unchanged' && !statusText.includes('unchanged')) {
                        statusMatch = false;
                    }
                }
                
                if (numberMatch && domainMatch && redirectMatch && clientMatch && statusMatch) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });
            
            // Update summary with filtered count
            updateFilteredSummary(visibleCount, rows.length);
        }
        
        function clearAllFilters() {
            document.getElementById('number-filter').value = '';
            document.getElementById('domain-filter').value = '';
            document.getElementById('redirect-filter').value = '';
            document.getElementById('client-filter').value = '';
            document.getElementById('status-filter').value = '';
            applyFilters();
        }
        
        function updateFilteredSummary(visibleCount, totalCount) {
            const summary = document.getElementById('domains-summary');
            if (summary && visibleCount !== totalCount) {
                const originalText = summary.innerHTML;
                const filterText = '<div style="color: #3b82f6; font-weight: 600; margin-bottom: 0.5rem;">Showing ' + visibleCount + ' of ' + totalCount + ' domains (filtered)</div>';
                if (!originalText.includes('filtered')) {
                    summary.innerHTML = filterText + originalText;
                }
            } else if (summary && visibleCount === totalCount) {
                // Remove filter text if showing all
                const lines = summary.innerHTML.split('\n');
                const filteredLines = lines.filter(line => !line.includes('filtered'));
                summary.innerHTML = filteredLines.join('\n');
            }
        }
        
        function populateClientFilter() {
            const clientFilter = document.getElementById('client-filter');
            if (!clientFilter) return;
            
            // Get unique client names from current data
            const clients = new Set();
            document.querySelectorAll('#domains-tbody tr').forEach(row => {
                const clientSelect = row.cells[4].querySelector('select');
                if (clientSelect && clientSelect.selectedOptions[0]) {
                    const clientName = clientSelect.selectedOptions[0].textContent;
                    if (clientName && clientName !== 'Unassigned') {
                        clients.add(clientName);
                    }
                }
            });
            
            // Preserve current selection
            const currentValue = clientFilter.value;
            
            // Clear and repopulate filter options
            clientFilter.innerHTML = '<option value="">All Clients</option>';
            clientFilter.innerHTML += '<option value="Unassigned">Unassigned</option>';
            
            clients.forEach(clientName => {
                const option = document.createElement('option');
                option.value = clientName;
                option.textContent = clientName;
                clientFilter.appendChild(option);
            });
            
            // Restore selection
            clientFilter.value = currentValue;
        }
        
        let clientsData = [];
        
        
        
        
        
        
        
        
        async function exportRedirections() {
            try {
                // Get all domains data
                const response = await fetch('/api/domains-from-db');
                const data = await response.json();
                
                if (data.status !== 'success') {
                    alert('Error loading domains for export');
                    return;
                }
                
                // Prepare CSV data
                const csvRows = [];
                csvRows.push('Domain Number,Domain Name,Redirect Target,Client,Status,Last Updated');
                
                data.domains.forEach(domain => {
                    const domainNumber = domain.domain_number || 'N/A';
                    const domainName = domain.domain_name || '';
                    const clientName = domain.client_name || 'Unassigned';
                    const syncStatus = domain.sync_status || 'unchanged';
                    const updatedAt = domain.updated_at ? new Date(domain.updated_at).toLocaleDateString() : 'N/A';
                    
                    if (domain.redirections && domain.redirections.length > 0) {
                        domain.redirections.forEach(redirect => {
                            const target = redirect.target || 'No redirect';
                            csvRows.push(`${domainNumber},"${domainName}","${target}","${clientName}","${syncStatus}","${updatedAt}"`);
                        });
                    } else {
                        csvRows.push(`${domainNumber},"${domainName}","No redirect","${clientName}","${syncStatus}","${updatedAt}"`);
                    }
                });
                
                // Create and download CSV file
                const csvContent = csvRows.join('\n');
                const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                
                if (link.download !== undefined) {
                    const url = URL.createObjectURL(blob);
                    link.setAttribute('href', url);
                    link.setAttribute('download', `domain_redirections_${new Date().toISOString().split('T')[0]}.csv`);
                    link.style.visibility = 'hidden';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                } else {
                    alert('CSV export is not supported in this browser.');
                }
            } catch (error) {
                alert('Error exporting CSV: ' + error.message);
            }
        }
        
        async function loadClientsIntoDropdown(domainName, currentClientId) {
            try {
                const response = await fetch('/api/clients');
                const data = await response.json();
                
                if (data.status === 'success') {
                    const selectId = `client-${domainName.replace(/\./g, '-')}`;
                    const select = document.getElementById(selectId);
                    if (select) {
                        select.innerHTML = '<option value="">Unassigned</option>';
                        data.clients.forEach(client => {
                            const option = document.createElement('option');
                            option.value = client.id;
                            option.textContent = client.name;
                            if (client.id === currentClientId) {
                                option.selected = true;
                            }
                            select.appendChild(option);
                        });
                    }
                }
            } catch (error) {
                console.error('Error loading clients for dropdown:', error);
            }
        }
        
        async function updateDomainClient(select, domainName) {
            const clientId = select.value;
            
            // Auto-fill redirect target with client URL if client is selected
            if (clientId) {
                try {
                    const response = await fetch('/api/clients');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        const client = data.clients.find(c => c.id == clientId);
                        if (client && client.url) {
                            // Find the redirect input in the same row
                            const row = select.closest('tr');
                            const redirectInput = row.querySelector('input[type="text"][placeholder*="example.com"]');
                            if (redirectInput) {
                                redirectInput.value = client.url;
                            }
                        }
                    }
                } catch (error) {
                    console.error('Error getting client URL:', error);
                }
            }
        }
        
        function updateDomain(input, domainName, field) {
            // This function can be used for real-time validation if needed
            console.log('Updated ' + field + ' for ' + domainName + ': ' + input.value);
        }
        
        async function updateDomainRedirect(input, domainName, field) {
            const newValue = input.value.trim();
            
            if (!newValue) {
                return; // Don't update if empty
            }
            
            try {
                // Update the redirection on Namecheap
                const response = await fetch('/api/update-redirection', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        domain: domainName,
                        name: '@',
                        target: newValue
                    })
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    // Update status to synced (only in UI, not database)
                    const row = input.closest('tr');
                    const statusCell = row.cells[5]; // Status is in the 6th column (index 5)
                    statusCell.innerHTML = '<span style="color: #10b981; font-weight: 600;">✅ Synced</span>';
                    
                    console.log('Domain ' + domainName + ' updated and status set to synced');
                } else {
                    // Update status to not synced
                    const row = input.closest('tr');
                    const statusCell = row.cells[5];
                    statusCell.innerHTML = '<span style="color: #ef4444; font-weight: 600;">❌ Not Synced</span>';
                    
                    console.error('Failed to update ' + domainName + ': ' + result.message);
                }
            } catch (error) {
                console.error('Error updating domain redirect: ' + error.message);
                
                // Update status to not synced
                const row = input.closest('tr');
                const statusCell = row.cells[5];
                statusCell.innerHTML = '<span style="color: #ef4444; font-weight: 600;">❌ Not Synced</span>';
            }
        }
        
        // Bulk update modal
        function showBulkUpdateModal() {
            const selectedDomains = collectSelectedDomains();
            if (selectedDomains.length === 0) {
                alert('Please select at least one domain for bulk update.');
                return;
            }
            
            const modal = document.createElement('div');
            modal.style.cssText = 
                'position: fixed; top: 0; left: 0; width: 100%; height: 100%; ' +
                'background: rgba(0,0,0,0.5); z-index: 1000; display: flex; ' +
                'align-items: center; justify-content: center;';
            
            const hiddenInputs = selectedDomains.map(domain => '<input type="hidden" name="selected_domains" value="' + domain + '">').join('');
            const domainsList = selectedDomains.map(domain => '<li>' + domain + '</li>').join('');
            
            modal.innerHTML = 
                '<div style="background: white; padding: 2rem; border-radius: 12px; width: 90%; max-width: 600px; max-height: 80%; overflow-y: auto;">' +
                    '<h2>Bulk Update ' + selectedDomains.length + ' Domains</h2>' +
                    '<div style="margin: 1rem 0; max-height: 200px; overflow-y: auto; border: 1px solid #e5e7eb; padding: 1rem; border-radius: 4px;">' +
                        '<h4>Selected Domains:</h4>' +
                        '<ul style="margin: 0; padding-left: 1rem;">' + domainsList + '</ul>' +
                    '</div>' +
                    '<form method="POST" action="/bulk-update" style="margin-top: 1rem;">' +
                        '<div style="margin-bottom: 1rem;">' +
                            '<label>Choose Option:</label>' +
                            '<div style="margin: 0.5rem 0;">' +
                                '<input type="radio" id="manual-url" name="update-type" value="manual" checked onchange="toggleBulkInputs()"> ' +
                                '<label for="manual-url">Manual URL Entry</label>' +
                            '</div>' +
                            '<div style="margin: 0.5rem 0;">' +
                                '<input type="radio" id="client-url" name="update-type" value="client" onchange="toggleBulkInputs()"> ' +
                                '<label for="client-url">Select Client</label>' +
                            '</div>' +
                        '</div>' +
                        '<div id="manual-input" style="margin-bottom: 1rem;">' +
                            '<label>New Redirect Target:</label>' +
                            '<input type="text" name="bulk_target" class="form-control" placeholder="https://example.com" style="width: 100%; margin-top: 0.5rem;">' +
                        '</div>' +
                        '<div id="client-input" style="margin-bottom: 1rem; display: none;">' +
                            '<label>Select Client:</label>' +
                            '<select name="bulk_client" class="form-control" style="width: 100%; margin-top: 0.5rem;" onchange="updateBulkPreview()"></select>' +
                            '<div id="client-url-preview" style="margin-top: 0.5rem; font-style: italic; color: #666;"></div>' +
                        '</div>' +
                        hiddenInputs +
                        '<div style="display: flex; gap: 1rem; justify-content: flex-end;">' +
                            '<button type="button" class="btn" onclick="closeBulkModal()" style="background: #6b7280;">Cancel</button>' +
                            '<button type="submit" class="btn btn-success">Update All</button>' +
                        '</div>' +
                    '</form>' +
                '</div>';
            
            modal.id = 'bulk-modal';
            document.body.appendChild(modal);
            
            // Load clients for dropdown
            loadClientsForBulk();
            
            // Close modal when clicking outside
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeBulkModal();
                }
            });
        }
        
        function closeBulkModal() {
            const modal = document.getElementById('bulk-modal');
            if (modal) {
                modal.remove();
            }
        }
        
        // Toggle bulk update inputs
        function toggleBulkInputs() {
            const manualRadio = document.getElementById('manual-url');
            const manualInput = document.getElementById('manual-input');
            const clientInput = document.getElementById('client-input');
            
            if (manualRadio && manualRadio.checked) {
                if (manualInput) manualInput.style.display = 'block';
                if (clientInput) clientInput.style.display = 'none';
            } else {
                if (manualInput) manualInput.style.display = 'none';
                if (clientInput) clientInput.style.display = 'block';
            }
        }
        
        // Load clients for bulk update
        async function loadClientsForBulk() {
            try {
                const response = await fetch('/api/clients');
                const data = await response.json();
                
                if (data.status === 'success') {
                    const select = document.querySelector('select[name="bulk_client"]');
                    if (select) {
                        select.innerHTML = '<option value="">Choose a client...</option>';
                        data.clients.forEach(client => {
                            const option = document.createElement('option');
                            option.value = client.id;
                            option.textContent = client.name;
                            option.setAttribute('data-url', client.url || '');
                            select.appendChild(option);
                        });
                    }
                }
            } catch (error) {
                console.error('Error loading clients:', error);
            }
        }
        
        
        
        
        // Table filtering
        function filterTable() {
            const filters = [];
            const filterInputs = document.querySelectorAll('thead tr:nth-child(2) input, thead tr:nth-child(2) select');
            filterInputs.forEach(input => {
                filters.push(input.value.toLowerCase());
            });
            
            const rows = document.querySelectorAll('tbody tr');
            let visibleCount = 0;
            
            rows.forEach(row => {
                const cells = row.cells;
                let visible = true;
                
                // Skip checkbox column (index 0)
                for (let i = 1; i < Math.min(cells.length, filters.length + 1); i++) {
                    const filterValue = filters[i - 1];
                    if (filterValue) {
                        const cellText = cells[i].textContent.toLowerCase();
                        if (!cellText.includes(filterValue)) {
                            visible = false;
                            break;
                        }
                    }
                }
                
                row.style.display = visible ? '' : 'none';
                if (visible) visibleCount++;
            });
        }
        
        // Helper function for bulk operations
        function collectSelectedDomains() {
            const selected = [];
            const checkboxes = document.querySelectorAll('input[name="domain_check"]:checked');
            checkboxes.forEach(checkbox => {
                selected.push(checkbox.value);
            });
            return selected;
        }
        
        // Update bulk button text with count
        function updateBulkButtonText() {
            const bulkBtn = document.getElementById('bulk-update-btn');
            const selectedCount = collectSelectedDomains().length;
            if (bulkBtn) {
                if (selectedCount > 0) {
                    bulkBtn.textContent = '🔧 Bulk Update (' + selectedCount + ')';
                    bulkBtn.style.background = '#3b82f6';
                } else {
                    bulkBtn.textContent = '🔧 Bulk Update';
                    bulkBtn.style.background = '';
                }
            }
        }
        
        // Add event listeners for checkboxes
        document.addEventListener('change', function(e) {
            if (e.target.name === 'domain_check' || e.target.id === 'select-all') {
                updateBulkButtonText();
            }
        });
        
        // Show sync progress when sync form is submitted
        document.addEventListener('DOMContentLoaded', function() {
            const syncForm = document.querySelector('form[action="/sync-domains"]');
            if (syncForm) {
                syncForm.addEventListener('submit', function(e) {
                    console.log('Sync form submitted');
                    const statusDiv = document.getElementById('sync-status');
                    const statusText = document.getElementById('sync-text');
                    const statusDetails = document.getElementById('sync-details');
                    
                    console.log('Status elements found:', {
                        statusDiv: !!statusDiv,
                        statusText: !!statusText, 
                        statusDetails: !!statusDetails
                    });
                    
                    if (statusDiv) {
                        statusDiv.style.display = 'block';
                        console.log('Sync status div made visible');
                        if (statusText) statusText.textContent = 'Status: In Progress';
                        if (statusDetails) statusDetails.textContent = 'Starting sync from Namecheap...';
                    }
                    
                    // Start progress monitoring after a short delay
                    setTimeout(function() {
                        startSyncProgressMonitoring();
                    }, 1000);
                });
            }
        });
        
        // Toggle bulk update inputs
        function toggleBulkInputs() {
            const manualRadio = document.getElementById('manual-url');
            const manualInput = document.getElementById('manual-input');
            const clientInput = document.getElementById('client-input');
            
            if (manualRadio.checked) {
                manualInput.style.display = 'block';
                clientInput.style.display = 'none';
            } else {
                manualInput.style.display = 'none';
                clientInput.style.display = 'block';
            }
        }
        
        // Load clients for bulk update
        async function loadClientsForBulk() {
            try {
                const response = await fetch('/api/clients');
                const data = await response.json();
                
                if (data.status === 'success') {
                    const select = document.querySelector('select[name="bulk_client"]');
                    select.innerHTML = '<option value="">Choose a client...</option>';
                    data.clients.forEach(client => {
                        const option = document.createElement('option');
                        option.value = client.id;
                        option.textContent = client.name;
                        option.setAttribute('data-url', client.url || '');
                        select.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading clients:', error);
            }
        }
        
        // Update bulk preview URL
        function updateBulkPreview() {
            const select = document.querySelector('select[name="bulk_client"]');
            const preview = document.getElementById('client-url-preview');
            const selectedOption = select.selectedOptions[0];
            
            if (selectedOption && selectedOption.getAttribute('data-url')) {
                preview.textContent = 'Target URL: ' + selectedOption.getAttribute('data-url');
            } else {
                preview.textContent = '';
            }
        }
        
        // Load existing clients for management modal
        async function loadExistingClients() {
            try {
                const response = await fetch('/api/clients');
                const data = await response.json();
                
                const container = document.getElementById('clients-list-container');
                if (data.status === 'success' && data.clients.length > 0) {
                    container.innerHTML = data.clients.map(client => 
                        '<div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">' +
                            '<div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">' +
                                '<strong>' + client.name + '</strong>' +
                                '<input type="text" value="' + (client.url || '') + '" class="form-control" style="width: 300px;" id="client-url-' + client.id + '" placeholder="https://client-website.com">' +
                                '<button class="btn btn-small btn-success" onclick="updateClientUrl(' + client.id + ')">Update URL</button>' +
                                '<button class="btn btn-small" style="background: #ef4444;" onclick="deleteClient(' + client.id + ')">Delete</button>' +
                            '</div>' +
                        '</div>'
                    ).join('');
                } else {
                    container.innerHTML = '<p>No clients found. Add some clients to get started.</p>';
                }
            } catch (error) {
                document.getElementById('clients-list-container').innerHTML = '<p>Error loading clients.</p>';
            }
        }
        
        // Update client URL
        async function updateClientUrl(clientId) {
            const urlInput = document.getElementById('client-url-' + clientId);
            const url = urlInput.value.trim();
            
            try {
                const response = await fetch('/api/clients/' + clientId, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                
                const result = await response.json();
                if (result.status === 'success') {
                    alert('Client URL updated successfully!');
                    location.reload(); // Refresh to update dropdowns
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Error updating client: ' + error.message);
            }
        }
        
        // Delete client
        async function deleteClient(clientId) {
            if (!confirm('Are you sure you want to delete this client?')) return;
            
            try {
                const response = await fetch('/api/clients/' + clientId, { method: 'DELETE' });
                const result = await response.json();
                
                if (result.status === 'success') {
                    alert('Client deleted successfully!');
                    loadExistingClients(); // Refresh the list
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Error deleting client: ' + error.message);
            }
        }
        
        // Update domain client assignment
        async function updateDomainClient(domainName, clientId) {
            try {
                // Get client data first to get the URL
                const clientsResponse = await fetch('/api/clients');
                const clientsData = await clientsResponse.json();
                let clientUrl = '';

                if (clientsData.status === 'success' && clientId) {
                    const client = clientsData.clients.find(c => c.id == clientId);
                    if (client && client.url) {
                        clientUrl = client.url;
                    }
                }

                // Update client assignment in database
                if (clientId) {
                    const response = await fetch('/api/assign-client', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ domain_name: domainName, client_id: clientId })
                    });

                    const result = await response.json();
                    if (result.status !== 'success') {
                        console.error('Failed to assign client:', result.error);
                        return;
                    }
                }

                // Auto-fill redirect URL field with client URL
                const domainSafeId = domainName.replace(/\./g, '-');
                const selectElement = document.querySelector(`select[onchange*="${domainName}"]`);

                if (selectElement) {
                    const row = selectElement.closest('tr');
                    const redirectInput = row.querySelector('input[name="target"]');

                    if (redirectInput) {
                        if (clientUrl) {
                            redirectInput.value = clientUrl;
                            console.log(`Auto-filled redirect URL for ${domainName}: ${clientUrl}`);
                        } else if (!clientId) {
                            // If "Unassigned" is selected, don't clear the URL - let user decide
                            console.log(`Client unassigned for ${domainName}, keeping existing redirect URL`);
                        }
                    }
                }
            } catch (error) {
                console.error('Error updating domain client:', error);
            }
        }
        
        // Perform bulk update
        async function performBulkUpdate() {
            const selectedDomains = collectSelectedDomains();
            const bulkUrl = document.getElementById('bulk-redirect-url').value.trim();
            
            console.log('Bulk update called with:', selectedDomains.length, 'domains');
            
            if (selectedDomains.length === 0) {
                alert('Please select at least one domain for bulk update.');
                return;
            }
            
            if (!bulkUrl) {
                alert('Please enter a redirect URL for bulk update.');
                return;
            }
            
            // Show bulk status
            const statusDiv = document.getElementById('bulk-status');
            const statusText = document.getElementById('bulk-text');
            const statusDetails = document.getElementById('bulk-details');
            
            console.log('Bulk status elements found:', {
                statusDiv: !!statusDiv,
                statusText: !!statusText,
                statusDetails: !!statusDetails
            });
            
            if (statusDiv) {
                statusDiv.style.display = 'block';
                console.log('Bulk status div made visible');
                if (statusText) statusText.textContent = 'Bulk Update Status: In Progress';
                if (statusDetails) statusDetails.innerHTML = `Starting bulk update for ${selectedDomains.length} domains...`;
            }
            
            // Disable bulk update button
            const bulkButton = document.getElementById('bulk-update-btn');
            if (bulkButton) {
                bulkButton.disabled = true;
                bulkButton.textContent = 'Updating...';
            }
            
            try {
                let completed = 0;
                let errors = 0;
                
                // Process domains one by one
                for (let i = 0; i < selectedDomains.length; i++) {
                    const domain = selectedDomains[i];
                    
                    try {
                        const formData = new FormData();
                        formData.append('domain', domain);
                        formData.append('target', bulkUrl);
                        
                        const response = await fetch('/update-redirect', {
                            method: 'POST',
                            body: formData
                        });
                        
                        if (response.ok) {
                            completed++;
                        } else {
                            errors++;
                        }
                        
                        // Update progress
                        if (statusDetails) {
                            statusDetails.innerHTML = `Processing ${i + 1} of ${selectedDomains.length} domains<br>Completed: ${completed} | Errors: ${errors}`;
                        }
                        
                        // Small delay to avoid overwhelming the API
                        await new Promise(resolve => setTimeout(resolve, 500));
                        
                    } catch (error) {
                        errors++;
                        console.error(`Error updating ${domain}:`, error);
                    }
                }
                
                // Final status
                if (statusText && statusDetails) {
                    if (errors === 0) {
                        statusDiv.style.borderLeftColor = '#10b981';
                        statusText.textContent = 'Bulk Update Status: Completed';
                        statusDetails.innerHTML = `Successfully updated ${completed} of ${selectedDomains.length} domains`;
                    } else {
                        statusDiv.style.borderLeftColor = '#f59e0b';
                        statusText.textContent = 'Bulk Update Status: Completed with Errors';
                        statusDetails.innerHTML = `Updated ${completed} of ${selectedDomains.length} domains (${errors} errors)`;
                    }
                }
                
                // Reload page after delay
                setTimeout(function() {
                    location.reload();
                }, 2000);
                
            } catch (error) {
                if (statusText && statusDetails) {
                    statusDiv.style.borderLeftColor = '#ef4444';
                    statusText.textContent = 'Bulk Update Status: Failed';
                    statusDetails.textContent = 'Bulk update failed: ' + error.message;
                }
            } finally {
                // Re-enable button
                if (bulkButton) {
                    bulkButton.disabled = false;
                    bulkButton.textContent = '🔧 Bulk Update';
                }
            }
        }
        
        // Sync progress monitoring functions
        function startSyncProgressMonitoring() {
            if (syncProgressInterval) {
                clearInterval(syncProgressInterval);
            }
            
            syncProgressInterval = setInterval(updateSyncProgress, 1000); // Check every 1 second
        }
        
        async function updateSyncProgress() {
            try {
                const response = await fetch('/api/sync-domains-progress');
                const data = await response.json();
                
                const statusDiv = document.getElementById('sync-status');
                const statusText = document.getElementById('sync-text');
                const statusDetails = document.getElementById('sync-details');
                const progressFill = document.getElementById('sync-progress-fill');

                if (statusDiv && statusText && statusDetails) {
                    if (data.status === 'running') {
                        statusDiv.style.display = 'block';
                        statusDiv.style.borderLeftColor = '#3b82f6';

                        statusText.textContent = 'Status: In Progress';

                        let details = `Synced ${data.processed} of ${data.total} domains`;
                        if (data.current_domain) {
                            details += ` (Currently: ${data.current_domain})`;
                        }
                        details += `<br>Added: ${data.domains_added} | Updated: ${data.domains_updated} | Errors: ${data.errors.length}`;

                        statusDetails.innerHTML = details;

                        // Update progress bar
                        if (progressFill && data.total > 0) {
                            const percentage = Math.round((data.processed / data.total) * 100);
                            progressFill.style.width = `${percentage}%`;
                        }
                        
                    } else if (data.status === 'completed') {
                        statusDiv.style.borderLeftColor = '#10b981';
                        statusText.textContent = 'Status: Completed';
                        statusDetails.innerHTML = `Successfully synced ${data.processed} of ${data.total} domains<br>Added: ${data.domains_added} | Updated: ${data.domains_updated} | Errors: ${data.errors.length}`;

                        // Set progress bar to 100%
                        if (progressFill) {
                            progressFill.style.width = '100%';
                        }

                        // Stop monitoring and reload page after delay
                        clearInterval(syncProgressInterval);
                        setTimeout(function() {
                            location.reload();
                        }, 3000);
                        
                    } else if (data.status === 'error') {
                        statusDiv.style.borderLeftColor = '#ef4444';
                        statusText.textContent = 'Status: Failed';
                        statusDetails.textContent = 'Sync failed: ' + (data.error || 'Unknown error');
                        
                        clearInterval(syncProgressInterval);
                    }
                }
            } catch (error) {
                console.error('Error fetching sync progress:', error);
            }
        }
        
        // Check if sync is already running on page load
        async function checkSyncStatus() {
            try {
                const response = await fetch('/api/sync-domains-progress');
                const data = await response.json();

                if (data.status === 'running') {
                    startSyncProgressMonitoring();
                }
            } catch (error) {
                // Ignore errors on initial check
                console.log('No active sync found');
            }
        }

        // Handle sync form submission to show progress immediately
        function startSyncOperation(event) {
            console.log('Starting sync operation...');

            // Show the sync status div immediately
            const statusDiv = document.getElementById('sync-status');
            const statusText = document.getElementById('sync-text');
            const statusDetails = document.getElementById('sync-details');
            const progressFill = document.getElementById('sync-progress-fill');

            if (statusDiv) {
                statusDiv.style.display = 'block';
                statusDiv.style.borderLeftColor = '#3b82f6';

                if (statusText) {
                    statusText.textContent = 'Status: Initializing...';
                }

                if (statusDetails) {
                    statusDetails.innerHTML = 'Starting domain sync from Namecheap...';
                }

                if (progressFill) {
                    progressFill.style.width = '0%';
                }
            }

            // Start monitoring immediately (will begin polling in 1 second)
            startSyncProgressMonitoring();

            // Let the form submit normally
            return true;
        }
        
        // Debug function to test status display
        function testStatus() {
            const allStatusElements = document.querySelectorAll('[id^="status-"]');
            console.log('Found status elements:', allStatusElements.length);

            allStatusElements.forEach((element, index) => {
                console.log('Element', index, ':', element.id);
                element.innerHTML = '<span style="color: #10b981; font-weight: 600;">✅ Test Status</span>';
            });
        }

        // Debug function to test save functionality
        function testSave() {
            const forms = document.querySelectorAll('form[onsubmit*="handleRedirectSubmit"]');
            console.log('Found forms with handleRedirectSubmit:', forms.length);

            if (forms.length > 0) {
                const firstForm = forms[0];
                const domainName = firstForm.querySelector('input[name="domain"]').value;
                const targetInput = firstForm.querySelector('input[name="target"]');

                console.log('Testing with domain:', domainName);
                console.log('Current target:', targetInput.value);

                // Test with a dummy URL
                targetInput.value = 'https://test-redirect.com';
                handleRedirectSubmit(firstForm, domainName);
            } else {
                console.log('No forms found for testing');
            }
        }
        
        // Handle redirect form submission with status updates
        async function handleRedirectSubmit(form, domainName) {
            console.log('handleRedirectSubmit called for:', domainName);
            
            const statusId = 'status-' + domainName.replace(/\./g, '-');
            const statusElement = document.getElementById(statusId);
            const submitButton = form.querySelector('button[type="submit"]');
            const targetInput = form.querySelector('input[name="target"]');
            const newUrl = targetInput.value.trim();
            
            console.log('Status element ID:', statusId);
            console.log('Status element found:', !!statusElement);
            
            // Show loading status
            if (statusElement) {
                statusElement.innerHTML = '<span style="color: #f59e0b; font-weight: 600;">⏳ Updating...</span>';
            } else {
                console.error('Status element not found with ID:', statusId);
            }
            
            // Disable button during submission
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = 'Saving...';
            }
            
            try {
                // Send as JSON for proper AJAX handling
                const response = await fetch('/update-redirect', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        domain: domainName,
                        target: newUrl
                    })
                });

                console.log('Response status:', response.status);
                const responseData = await response.json();
                
                if (response.ok && responseData.status === 'success') {
                    // Success - show synced status and keep the new URL
                    if (statusElement) {
                        statusElement.innerHTML = '<span style="color: #10b981; font-weight: 600;">✅ Synced</span>';
                        console.log('Status updated to Synced');
                    }
                    // Keep the updated URL in the input field
                    targetInput.value = newUrl;
                    console.log('Redirect updated successfully:', responseData.message);
                } else {
                    // Error - show not synced status
                    if (statusElement) {
                        statusElement.innerHTML = '<span style="color: #ef4444; font-weight: 600;">❌ Not Synced</span>';
                        console.log('Status updated to Not Synced');
                    }
                    const errorMsg = responseData.error || 'Unknown error occurred';
                    console.error('Update failed:', errorMsg);
                }
            } catch (error) {
                // Error - show not synced status
                if (statusElement) {
                    statusElement.innerHTML = '<span style="color: #ef4444; font-weight: 600;">❌ Error</span>';
                    console.log('Status updated to Error');
                }
                console.error('Error updating redirect:', error);
                alert('Error updating redirect: ' + error.message);
            } finally {
                // Re-enable button
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Save';
                }
            }
        }
    </script>
</body>
</html>
"""

# Clients management template
CLIENTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>Manage Clients - Domain Redirect Tool</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Inter', sans-serif; background: #f8fafc; }
        .header { background: #1e293b; color: white; padding: 1rem 2rem; }
        .logo { font-size: 1.5rem; font-weight: 700; }
        .container { max-width: 1000px; margin: 2rem auto; padding: 0 2rem; }
        .card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 2rem; }
        .btn { background: #3b82f6; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 1rem; }
        .btn-success { background: #10b981; }
        .btn-danger { background: #ef4444; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.5rem; font-weight: 600; }
        .form-control { padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 6px; width: 100%; }
        .table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        .table th, .table td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb; }
        .table th { background: #f9fafb; font-weight: 600; }
        .client-row { border-bottom: 1px solid #e5e7eb; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">👥 Manage Clients</div>
    </div>
    
    <div class="container">
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                <h1>Client Management</h1>
                <a href="/" class="btn">← Back to Dashboard</a>
            </div>
            
            <div style="margin-bottom: 2rem; padding: 1.5rem; background: #f8fafc; border-radius: 8px;">
                <h2 style="margin-bottom: 1rem;">Add New Client</h2>
                <form method="POST" style="display: flex; gap: 1rem; align-items: end; flex-wrap: wrap;">
                    <input type="hidden" name="action" value="add">
                    <div style="flex: 1; min-width: 200px;">
                        <label>Client Name *</label>
                        <input type="text" name="client_name" class="form-control" placeholder="Client Name" required>
                    </div>
                    <div style="flex: 2; min-width: 300px;">
                        <label>Target URL</label>
                        <input type="text" name="client_url" class="form-control" placeholder="https://client-website.com">
                    </div>
                    <button type="submit" class="btn btn-success">➕ Add Client</button>
                </form>
            </div>
            
            <h2 style="margin-bottom: 1rem;">Existing Clients ({{ clients|length }})</h2>
            
            {% if clients %}
            <table class="table">
                <thead>
                    <tr>
                        <th style="width: 25%;">Client Name</th>
                        <th style="width: 45%;">Target URL</th>
                        <th style="width: 30%;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for client in clients %}
                    <tr class="client-row">
                        <td><strong>{{ client.name }}</strong></td>
                        <td>
                            <form method="POST" style="display: flex; gap: 0.5rem; align-items: center;">
                                <input type="hidden" name="action" value="update">
                                <input type="hidden" name="client_id" value="{{ client.id }}">
                                <input type="text" name="client_url" value="{{ client.url or '' }}" class="form-control" placeholder="https://client-website.com" style="flex: 1;">
                                <button type="submit" class="btn btn-success" style="padding: 0.5rem 1rem; margin: 0;">Update</button>
                            </form>
                        </td>
                        <td>
                            {% if client.name != 'Unassigned' %}
                            <form method="POST" style="display: inline;" onsubmit="return confirm('Are you sure you want to delete this client?');">
                                <input type="hidden" name="action" value="delete">
                                <input type="hidden" name="client_id" value="{{ client.id }}">
                                <button type="submit" class="btn btn-danger" style="padding: 0.5rem 1rem;">🗑 Delete</button>
                            </form>
                            {% else %}
                            <span style="color: #6b7280; font-style: italic;">Default client</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <div style="text-align: center; padding: 2rem; color: #6b7280;">
                <p>No clients found. Add your first client above!</p>
            </div>
            {% endif %}
        </div>
    </div>
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

@app.route('/', methods=['GET'])
def index():
    """Serve React app"""
    try:
        # Serve the built React app with proper content type
        return send_from_directory('frontend/build', 'index.html')
    except FileNotFoundError:
        # If React app not built, show instructions
        return """
        <html>
        <head><title>Domain Redirect Tool</title></head>
        <body style="font-family: Arial, sans-serif; padding: 2rem; text-align: center;">
            <h1>🔗 Domain Redirect Tool</h1>
            <h2>React Frontend Not Built</h2>
            <p>The React frontend needs to be built first:</p>
            <ol style="text-align: left; max-width: 600px; margin: 0 auto;">
                <li>Run: <code>cd frontend</code></li>
                <li>Run: <code>npm install</code></li>
                <li>Run: <code>npm run build</code></li>
                <li>Reload this page</li>
            </ol>
            <p><strong>Legacy Dashboard:</strong> <a href="/dashboard">/dashboard</a></p>
        </body>
        </html>
        """


@app.route('/dashboard', methods=['GET', 'POST'])
@require_auth
def dashboard():
    """Legacy dashboard for backward compatibility"""
    search_query = request.args.get('search', '')
    domains = db.get_all_domains_with_redirections()
    clients = db.get_all_clients()

    print(f"Dashboard: Found {len(domains)} domains, {len(clients)} clients")
    if domains:
        print(f"First domain example: {domains[0]}")

    # Filter domains if search query
    if search_query:
        domains = [d for d in domains if search_query.lower() in d['domain_name'].lower()]
        print(f"After search filter '{search_query}': {len(domains)} domains")

    return render_template_string(DASHBOARD_TEMPLATE, domains=domains, clients=clients, request=request)

@app.route('/clients', methods=['GET', 'POST'])
@require_auth
def clients_page():
    """Clients management page"""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            client_name = request.form.get('client_name', '').strip()
            client_url = request.form.get('client_url', '').strip() or None
            
            if client_name:
                db.add_client(client_name, client_url)
                
        elif action == 'update':
            client_id = request.form.get('client_id')
            client_url = request.form.get('client_url', '').strip() or None
            
            if client_id:
                db.update_client_url(int(client_id), client_url)
                
        elif action == 'delete':
            client_id = request.form.get('client_id')
            
            if client_id:
                db.delete_client(int(client_id))
    
    clients = db.get_all_clients()
    return render_template_string(CLIENTS_TEMPLATE, clients=clients)

# Global variable to track sync progress
sync_progress = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "current_domain": "",
    "domains_added": 0,
    "domains_updated": 0,
    "errors": []
}

import threading
import time

def background_sync_with_rate_limiting():
    """Background sync with improved rate limiting and error handling"""
    global sync_progress
    
    try:
        sync_progress["status"] = "running"
        
        # Store existing domain numbers before clearing
        existing_domains = db.get_all_domains_with_redirections()
        domain_numbers = {d['domain_name']: d['domain_number'] for d in existing_domains}
        
        # Clear existing domains from database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM redirections')
            cursor.execute('DELETE FROM domains WHERE id NOT IN (SELECT DISTINCT client_id FROM domains WHERE client_id IS NOT NULL)')
            conn.commit()
        
        # Get all domains from Namecheap with retry logic
        namecheap_domains = []
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                namecheap_domains = email_manager.get_all_domains()
                if namecheap_domains:
                    break
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Retrying domain list fetch ({retry_count}/{max_retries})...")
                    time.sleep(5)  # Wait 5 seconds before retry
            except Exception as e:
                retry_count += 1
                print(f"Error fetching domains (attempt {retry_count}): {e}")
                if retry_count < max_retries:
                    time.sleep(10)  # Wait longer on error
        
        if not namecheap_domains:
            sync_progress["status"] = "error"
            sync_progress["error"] = "No domains found in Namecheap after retries"
            return
        
        sync_progress["total"] = len(namecheap_domains)
        print(f"🔄 Starting background sync of {sync_progress['total']} domains...")
        
        # Process domains with aggressive rate limiting
        for i, domain_name in enumerate(namecheap_domains, 1):
            sync_progress["processed"] = i
            sync_progress["current_domain"] = domain_name
            
            try:
                print(f"Processing {i}/{sync_progress['total']}: {domain_name}")
                
                # Add domain with preserved number or new number
                if domain_name in domain_numbers:
                    # Update the domain with preserved number
                    with db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO domains (domain_number, domain_name, client_id)
                            VALUES (?, ?, (SELECT id FROM clients WHERE client_name = 'Unassigned'))
                        ''', (domain_numbers[domain_name], domain_name))
                        conn.commit()
                    sync_progress["domains_updated"] += 1
                else:
                    # New domain gets new number
                    db.add_or_update_domain(domain_name)
                    sync_progress["domains_added"] += 1
                
                # Get redirections with retry logic for rate limits
                redirections_fetched = False
                redirect_retry = 0
                max_redirect_retries = 3
                
                while redirect_retry < max_redirect_retries and not redirections_fetched:
                    try:
                        redirections = email_manager.api_client.get_domain_redirections(domain_name)
                        redirections_fetched = True
                        
                        if redirections:
                            db.update_redirections(domain_name, redirections)
                            db.update_domain_sync_status(domain_name, 'synced')
                            print(f"  ✅ Added {len(redirections)} redirections for {domain_name}")
                        else:
                            db.update_domain_sync_status(domain_name, 'synced')
                            print(f"  ℹ️ No redirections found for {domain_name}")
                            
                    except Exception as redirect_error:
                        redirect_retry += 1
                        error_msg = str(redirect_error)
                        
                        # Check for various rate limiting indicators
                        is_rate_limited = (
                            "too many requests" in error_msg.lower() or 
                            "rate limit" in error_msg.lower() or 
                            "connection/timeout error" in error_msg.lower() or
                            "502" in error_msg or "503" in error_msg or "504" in error_msg  # Server errors that might indicate overload
                        )
                        
                        if is_rate_limited:
                            if redirect_retry < max_redirect_retries:
                                wait_time = min(15 * redirect_retry, 60)  # Cap at 60 seconds max wait
                                print(f"  ⏳ Rate limited for {domain_name}, waiting {wait_time}s (attempt {redirect_retry})")
                                time.sleep(wait_time)
                                continue
                            else:
                                print(f"  ❌ Max retries reached for {domain_name}: {redirect_error}")
                                db.update_domain_sync_status(domain_name, 'not_synced')
                                sync_progress["errors"].append(f"{domain_name}: Rate limit exceeded after {max_redirect_retries} retries")
                        else:
                            print(f"  ⚠️ Error getting redirections for {domain_name}: {redirect_error}")
                            db.update_domain_sync_status(domain_name, 'not_synced')
                            sync_progress["errors"].append(f"{domain_name}: {str(redirect_error)}")
                            break
                
                # Progressive delay based on errors and position
                base_delay = 2
                if len(sync_progress["errors"]) > 5:  # Many errors, slow down more
                    base_delay = 8
                elif len(sync_progress["errors"]) > 2:
                    base_delay = 5
                
                if i > 50:  # After 50 domains, longer delays
                    base_delay += 3
                elif i > 20:  # After 20 domains, medium delays
                    base_delay += 1
                
                time.sleep(base_delay)
                    
            except Exception as e:
                print(f"Error syncing domain {domain_name}: {e}")
                sync_progress["errors"].append(f"{domain_name}: {str(e)}")
                # Still add the domain to database even if redirect fetch failed
                try:
                    if domain_name in domain_numbers:
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO domains (domain_number, domain_name, client_id)
                                VALUES (?, ?, (SELECT id FROM clients WHERE client_name = 'Unassigned'))
                            ''', (domain_numbers[domain_name], domain_name))
                            conn.commit()
                    else:
                        db.add_or_update_domain(domain_name)
                    db.update_domain_sync_status(domain_name, 'not_synced')
                except Exception as db_error:
                    print(f"Error adding domain {domain_name} to database: {db_error}")
                
                continue
        
        sync_progress["status"] = "completed"
        sync_progress["current_domain"] = ""
        print(f"✅ Background sync completed: {sync_progress['domains_added']} added, {sync_progress['domains_updated']} updated, {len(sync_progress['errors'])} errors")
        
    except Exception as e:
        print(f"❌ Background sync failed: {e}")
        sync_progress["status"] = "error"
        sync_progress["error"] = str(e)

@app.route('/api/sync-all-domains', methods=['POST'])
def sync_all_domains():
    """Start sync all domains from Namecheap to database"""
    global sync_progress
    
    try:
        if not email_manager:
            return jsonify({"error": "Email manager not initialized"}), 503
        
        # Check if sync is already running
        if sync_progress["status"] == "running":
            return jsonify({"error": "Sync already in progress"}), 409
        
        # Get all domains from Namecheap
        namecheap_domains = email_manager.get_all_domains()
        
        if not namecheap_domains:
            return jsonify({"error": "No domains found in Namecheap"}), 404
        
        # Start background sync task
        sync_thread = threading.Thread(target=background_sync_task, args=(namecheap_domains,))
        sync_thread.daemon = True
        sync_thread.start()
        
        return jsonify({
            "status": "started",
            "total_domains": len(namecheap_domains),
            "processing_count": len(namecheap_domains),
            "message": "Domain sync started in background"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/add-domain-redirection', methods=['POST'])
@require_auth
def add_domain_redirection():
    """Add a domain redirection manually"""
    try:
        data = request.get_json()
        domain = data.get('domain', '').strip()
        target = data.get('target', '').strip()
        client_id = data.get('client_id')
        
        if not domain or not target:
            return jsonify({"status": "error", "message": "Domain and target are required"}), 400
        
        # Add domain to database
        domain_number = db.add_or_update_domain(domain, client_id)
        
        # Add redirection to database
        redirections = [{'name': '@', 'target': target, 'type': 'URL'}]
        db.update_redirections(domain, redirections)
        
        return jsonify({
            "status": "success",
            "message": f"Domain redirection added successfully",
            "domain_number": domain_number,
            "domain": domain,
            "target": target
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sync-domains-progress', methods=['GET'])
def sync_domains_progress():
    """Get real-time progress of domain sync"""
    global sync_progress
    
    return jsonify({
        "status": sync_progress["status"],
        "processed": sync_progress["processed"],
        "total": sync_progress["total"],
        "current_domain": sync_progress["current_domain"],
        "domains_added": sync_progress["domains_added"],
        "domains_updated": sync_progress["domains_updated"],
        "errors": sync_progress["errors"][-5:] if sync_progress["errors"] else []  # Last 5 errors
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

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
    try:
        clients = db.get_all_clients()
        return jsonify({
            "status": "success",
            "clients": clients
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/clients', methods=['POST'])
def add_client():
    """Add new client"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        url = data.get('url', '').strip() or None
        
        if not name:
            return jsonify({"status": "error", "message": "Client name is required"}), 400
        
        client_id = db.add_client(name, url)
        return jsonify({
            "status": "success",
            "message": "Client added successfully",
            "client_id": client_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/clients/<int:client_id>', methods=['PUT'])
@require_auth
def update_client(client_id):
    """Update client URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip() or None
        
        db.update_client_url(client_id, url)
        return jsonify({
            "status": "success",
            "message": "Client updated successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
@require_auth
def delete_client(client_id):
    """Delete client"""
    try:
        db.delete_client(client_id)
        return jsonify({
            "status": "success",
            "message": "Client deleted successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update-domain', methods=['PUT'])
@require_auth
def update_domain():
    """Update domain information"""
    try:
        data = request.get_json()
        original_domain = data.get('original_domain')
        new_domain = data.get('new_domain')
        redirect_target = data.get('redirect_target')
        client_id = data.get('client_id')
        
        if not original_domain or not new_domain or not redirect_target:
            return jsonify({"status": "error", "message": "Domain name and redirect target are required"}), 400
        
        # Update domain name if changed
        if original_domain != new_domain:
            # This would require updating the domain name in the database
            # For now, we'll just update the redirections and client assignment
            pass
        
        # Update redirections
        redirections = [{'name': '@', 'target': redirect_target, 'type': 'URL'}]
        db.update_redirections(new_domain, redirections)
        
        # Update client assignment
        if client_id:
            db.assign_domain_to_client(new_domain, int(client_id))
        
        return jsonify({
            "status": "success",
            "message": "Domain updated successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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


@app.route('/api/assign-client', methods=['POST'])
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

                verified = False
                if success:
                    # Verify the redirection was actually set correctly
                    import time
                    time.sleep(2)  # Small delay to allow Namecheap to process
                    verified = email_manager.api_client.verify_domain_redirection(domain_name, name, target)

                    # Update sync status based on verification
                    if verified:
                        db.update_domain_sync_status(domain_name, 'synced')
                    else:
                        db.update_domain_sync_status(domain_name, 'not_synced')
                else:
                    db.update_domain_sync_status(domain_name, 'not_synced')

                results.append({
                    "domain_name": domain_name,
                    "success": success,
                    "verified": verified,
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
        
        # Get domains from Namecheap
        domain_names = email_manager.get_all_domains()

        # Get domains with redirections from database
        db_domains = db.get_all_domains_with_redirections()

        # Create a lookup for database domains
        db_lookup = {d['domain_name']: d for d in db_domains}

        # Get all clients for reference
        clients = db.get_all_clients()
        client_lookup = {c['id']: c for c in clients}

        # Transform domain names into objects that React expects
        domains = []
        for i, domain_name in enumerate(domain_names, 1):
            db_domain = db_lookup.get(domain_name, {})

            domain_obj = {
                "domain_name": domain_name,
                "domain_number": i,
                "redirect_url": db_domain.get('redirect_url', ''),
                "status": db_domain.get('sync_status', 'ready'),
                "client_id": db_domain.get('client_id'),
                "client_name": client_lookup.get(db_domain.get('client_id'), {}).get('name', 'Unassigned') if db_domain.get('client_id') else 'Unassigned',
                "updated_at": db_domain.get('updated_at')
            }
            domains.append(domain_obj)

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

@app.route('/api/update-domain-status', methods=['POST'])
@require_auth
def update_domain_status():
    """Update the sync status of a domain"""
    try:
        data = request.get_json()
        domain_name = data.get('domain')
        status = data.get('status')
        
        if not domain_name or not status:
            return jsonify({"status": "error", "message": "Domain name and status are required"}), 400
        
        db.update_domain_sync_status(domain_name, status)
        
        return jsonify({
            "status": "success",
            "message": f"Domain status updated to {status}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Server-side routes for HTML forms
@app.route('/sync-domains', methods=['POST'])
@require_auth
def sync_domains_form():
    """Handle sync domains form submission"""
    try:
        if not email_manager:
            return "Email manager not initialized", 503
        
        # Start background sync task
        global sync_progress
        sync_progress = {
            "status": "starting",
            "processed": 0,
            "total": 0,
            "current_domain": "",
            "domains_added": 0,
            "domains_updated": 0,
            "errors": []
        }
        
        sync_thread = threading.Thread(target=background_sync_with_rate_limiting)
        sync_thread.daemon = True
        sync_thread.start()
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/load-domains', methods=['POST'])
@require_auth
def load_domains_form():
    """Handle load domains from database form submission"""
    return redirect(url_for('dashboard'))

@app.route('/update-redirect', methods=['POST'])
@require_auth
def update_redirect_form():
    """Handle individual redirect update form submission"""
    try:
        # Check if it's an AJAX request (JSON response expected)
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            data = request.get_json()
            domain = data.get('domain')
            target = data.get('target')
        else:
            # Form submission
            domain = request.form.get('domain')
            target = request.form.get('target')

        if not domain or not target:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({"error": "Domain and target are required"}), 400
            return "Domain and target are required", 400

        # Update via Namecheap API
        success = email_manager.api_client.set_domain_redirection(domain, '@', target)

        if success:
            # Verify the redirection was actually set correctly
            import time
            time.sleep(2)  # Small delay to allow Namecheap to process
            verified = email_manager.api_client.verify_domain_redirection(domain, '@', target)

            if verified:
                # Update sync status
                db.update_domain_sync_status(domain, 'synced')

                # Return JSON for AJAX requests
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({
                        "status": "success",
                        "message": f"Successfully updated and verified redirection for {domain}",
                        "domain": domain,
                        "target": target,
                        "verified": True
                    })
                else:
                    return redirect(url_for('dashboard'))
            else:
                # Set operation claimed success but verification failed
                db.update_domain_sync_status(domain, 'not_synced')

                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({"error": f"Redirection was set but verification failed for {domain}"}), 500
                else:
                    return f"Redirection was set but verification failed for {domain}", 500
        else:
            db.update_domain_sync_status(domain, 'not_synced')

            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({"error": f"Failed to update redirection for {domain}"}), 500
            else:
                return f"Failed to update redirection for {domain}", 500

    except Exception as e:
        db.update_domain_sync_status(domain, 'not_synced')

        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({"error": f"Error updating redirect: {str(e)}"}), 500
        else:
            return f"Error updating redirect: {str(e)}", 500

@app.route('/bulk-update', methods=['POST'])
@require_auth
def bulk_update_form():
    """Handle bulk update form submission"""
    try:
        selected_domains = request.form.getlist('selected_domains')
        update_type = request.form.get('update-type', 'manual')
        
        if not selected_domains:
            return "No domains selected", 400
        
        # Determine target URL
        if update_type == 'client':
            client_id = request.form.get('bulk_client')
            if not client_id:
                return "Client selection required", 400
            
            # Get client URL
            clients = db.get_all_clients()
            client = next((c for c in clients if c['id'] == int(client_id)), None)
            if not client or not client['url']:
                return "Client URL not found", 400
            
            bulk_target = client['url']
            
            # Also assign domains to this client
            for domain in selected_domains:
                db.assign_domain_to_client(domain, int(client_id))
        else:
            bulk_target = request.form.get('bulk_target')
            if not bulk_target:
                return "Target URL is required", 400
        
        # Process bulk updates
        results = []
        for domain in selected_domains:
            try:
                success = email_manager.api_client.set_domain_redirection(domain, '@', bulk_target)

                verified = False
                if success:
                    # Verify the redirection was actually set correctly
                    import time
                    time.sleep(2)  # Small delay to allow Namecheap to process
                    verified = email_manager.api_client.verify_domain_redirection(domain, '@', bulk_target)

                    # Update sync status based on verification
                    if verified:
                        db.update_domain_sync_status(domain, 'synced')
                    else:
                        db.update_domain_sync_status(domain, 'not_synced')
                else:
                    db.update_domain_sync_status(domain, 'not_synced')

                results.append({'domain': domain, 'success': success, 'verified': verified})
                # Add delay between updates
                import time
                time.sleep(0.6)
            except Exception as e:
                db.update_domain_sync_status(domain, 'not_synced')
                results.append({'domain': domain, 'success': False, 'error': str(e)})
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        return f"Error in bulk update: {str(e)}", 500

@app.route('/export-csv', methods=['POST'])
@require_auth
def export_csv_form():
    """Handle CSV export form submission"""
    try:
        domains = db.get_all_domains_with_redirections()
        
        # Create CSV content
        csv_rows = []
        csv_rows.append('Domain Number,Domain Name,Redirect Target,Client,Status,Last Updated')
        
        for domain in domains:
            domain_number = domain['domain_number'] or 'N/A'
            domain_name = domain['domain_name'] or ''
            client_name = domain['client_name'] or 'Unassigned'
            sync_status = domain['sync_status'] or 'unchanged'
            updated_at = domain['updated_at'] if domain['updated_at'] else 'N/A'
            
            if domain['redirections']:
                for redirect in domain['redirections']:
                    target = redirect['target'] or 'No redirect'
                    csv_rows.append(f'{domain_number},"{domain_name}","{target}","{client_name}","{sync_status}","{updated_at}"')
            else:
                csv_rows.append(f'{domain_number},"{domain_name}","No redirect","{client_name}","{sync_status}","{updated_at}"')
        
        csv_content = '\n'.join(csv_rows)
        
        # Return CSV file
        from flask import make_response
        response = make_response(csv_content)
        response.headers['Content-Disposition'] = f'attachment; filename=domain_redirections_{datetime.now().strftime("%Y%m%d")}.csv'
        response.headers['Content-Type'] = 'text/csv'
        
        return response
        
    except Exception as e:
        return f"Error exporting CSV: {str(e)}", 500

@app.route('/add-client', methods=['POST'])
@require_auth
def add_client_form():
    """Handle add client form submission"""
    try:
        client_name = request.form.get('client_name')
        client_url = request.form.get('client_url')
        
        if not client_name:
            return "Client name is required", 400
        
        client_id = db.add_client(client_name, client_url)
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        return f"Error adding client: {str(e)}", 500

# Catch-all route for React Router (must be last)
@app.route('/<path:path>')
def catch_all(path):
    """Serve React app for any unmatched routes (client-side routing)"""
    # Don't interfere with API routes
    if path.startswith('api/'):
        return {"error": "API endpoint not found"}, 404

    # For any other route, serve the React app
    try:
        return send_from_directory('frontend/build', 'index.html')
    except FileNotFoundError:
        return "React app not built", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'

    app.run(debug=debug_mode, host='0.0.0.0', port=port)