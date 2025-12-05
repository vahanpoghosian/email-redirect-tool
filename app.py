"""
Email Redirection Tool - Flask Application
View existing email forwarding for Namecheap domains
"""

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, send_from_directory, flash, get_flashed_messages
from flask_cors import CORS
import json
import os
from datetime import datetime
from functools import wraps
from namecheap_client import EmailRedirectionManager, NamecheapAPIClient
from models import Database
import time
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
            clientCell.innerHTML = '<select class="form-control" onchange="updateDomainClient(this, \'' + domain.domain_name + '\')" id="client-' + domain.domain_name.replace(/\\./g, '-') + '"><option value="">Unassigned</option></select>';
            
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
                    const selectId = `client-${domainName.replace(/\\./g, '-')}`;
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
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div style="padding: 1rem; margin-bottom: 1rem; border-radius: 8px; {% if category == 'success' %}background: #d1fae5; color: #065f46; border: 1px solid #10b981;{% elif category == 'warning' %}background: #fef3c7; color: #92400e; border: 1px solid #f59e0b;{% else %}background: #fee2e2; color: #991b1b; border: 1px solid #ef4444;{% endif %}">
                        {{ message }}
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                <h1>Client Management</h1>
                <a href="/" class="btn">← Back to Dashboard</a>
            </div>
            
            <!-- Single Client Add -->
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

            <!-- Bulk Import Section -->
            <div style="margin-bottom: 2rem; padding: 1.5rem; background: #eff6ff; border-radius: 8px; border: 2px solid #3b82f6;">
                <h2 style="margin-bottom: 1rem; color: #1e40af;">📋 Bulk Import from Google Sheets</h2>
                <p style="margin-bottom: 1rem; color: #64748b;">Paste your client data from Google Sheets. Format: <strong>Client Name</strong> (tab) <strong>Website URL</strong> per line</p>

                <form method="POST" style="display: flex; flex-direction: column; gap: 1rem;">
                    <input type="hidden" name="action" value="bulk_import">
                    <div>
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Client Data (Tab-separated values)</label>
                        <textarea name="bulk_data" class="form-control" placeholder="ApeX	https://www.apex.exchange/
Atmos	https://atmosfunded.com/
Ben's Natural Health	https://www.bensnaturalhealth.com/
CasinooftheKings	https://casinoofthekings.ca/
Click Intelligence	http://clickintelligence.co.uk/"
                        style="min-height: 150px; font-family: monospace; font-size: 14px;" required></textarea>
                        <small style="color: #6b7280; margin-top: 0.5rem; display: block;">
                            💡 <strong>Tip:</strong> Copy and paste directly from Google Sheets. Each row should have Client Name in first column, URL in second column.
                        </small>
                    </div>
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <button type="submit" class="btn btn-success" style="background: #1d4ed8;">📥 Import All Clients</button>
                        <span style="color: #64748b; font-size: 14px;">This will add all clients at once</span>
                    </div>
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

# Initialize database
db = Database()

# Lazy initialization - don't connect to Namecheap on startup
email_manager = None

def get_email_manager():
    """Get or initialize the email manager lazily"""
    global email_manager
    if email_manager is None:
        try:
            print("Attempting to initialize Email Redirection Manager...")
            print(f"Environment variables present:")
            print(f"  NAMECHEAP_API_USER: {bool(os.environ.get('NAMECHEAP_API_USER'))}")
            print(f"  NAMECHEAP_API_KEY: {bool(os.environ.get('NAMECHEAP_API_KEY'))}")
            print(f"  NAMECHEAP_USERNAME: {bool(os.environ.get('NAMECHEAP_USERNAME'))}")
            print(f"  NAMECHEAP_CLIENT_IP: {os.environ.get('NAMECHEAP_CLIENT_IP', 'Not set')}")

            email_manager = EmailRedirectionManager()
            print("✅ Email Redirection Manager initialized successfully")
        except Exception as e:
            print(f"❌ Error: Could not initialize Email Redirection Manager: {e}")
            import traceback
            traceback.print_exc()
            # Don't raise - return None so endpoints can show error
            return None
    return email_manager

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
            return redirect(url_for('index'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
@require_auth
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

        elif action == 'bulk_import':
            bulk_data = request.form.get('bulk_data', '').strip()

            if bulk_data:
                success_count = 0
                error_count = 0
                errors = []

                # Process each line
                lines = bulk_data.split('\n')
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue

                    # Split by tab or multiple spaces/tabs
                    import re
                    parts = re.split(r'\t+|\s{2,}', line)

                    if len(parts) >= 1:
                        client_name = parts[0].strip()
                        client_url = parts[1].strip() if len(parts) > 1 else None

                        # Clean up URL if present
                        if client_url:
                            if not client_url.startswith(('http://', 'https://')):
                                client_url = 'https://' + client_url

                        try:
                            if client_name:
                                # Check if client already exists
                                existing_clients = db.get_all_clients()
                                client_exists = any(c['name'].lower() == client_name.lower() for c in existing_clients)

                                if not client_exists:
                                    db.add_client(client_name, client_url)
                                    success_count += 1
                                else:
                                    errors.append(f"Line {line_num}: Client '{client_name}' already exists")
                                    error_count += 1
                            else:
                                errors.append(f"Line {line_num}: Empty client name")
                                error_count += 1
                        except Exception as e:
                            errors.append(f"Line {line_num}: Error adding '{client_name}': {str(e)}")
                            error_count += 1
                    else:
                        errors.append(f"Line {line_num}: Invalid format - need at least client name")
                        error_count += 1

                # Add flash message with results
                if success_count > 0:
                    flash(f"✅ Successfully imported {success_count} clients!", "success")
                if error_count > 0:
                    flash(f"⚠️ {error_count} errors occurred: " + "; ".join(errors[:3]) + ("..." if len(errors) > 3 else ""), "warning")
    
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
    "errors": [],
    "should_stop": False,
    "paused_at_index": None,
    "rate_limit_message": None,
    "paused_domains": None
}

# Global variable to track bulk DNS update progress
bulk_dns_progress = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "current_domain": "",
    "successful": 0,
    "errors": [],
    "should_stop": False,
    "paused_at_index": None,
    "rate_limit_message": None,
    "paused_domains": None,
    "record_data": None
}

# Global variable to track bulk DNS remove progress
bulk_dns_remove_progress = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "current_domain": "",
    "successful": 0,
    "errors": [],
    "should_stop": False,
    "paused_at_index": None,
    "rate_limit_message": None,
    "paused_domains": None,
    "remove_criteria": None
}

dns_check_progress = {
    "status": "idle",
    "processed": 0,
    "total": 0,
    "current_domain": "",
    "successful": 0,
    "errors": [],
    "should_stop": False,
    "paused_at_index": None,
    "rate_limit_message": None,
    "paused_domains": None,
    "pause_until": None
}

import threading
import time

def background_sync_with_rate_limiting(resume_from_index=None):
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
        
        # Check if we're resuming from a paused state
        if resume_from_index is not None and sync_progress.get("paused_domains"):
            print(f"🔄 Resuming sync from domain index {resume_from_index}")
            namecheap_domains = sync_progress["paused_domains"]
            # Start from where we left off
            start_index = resume_from_index
        else:
            # Get all domains from Namecheap with retry logic (fresh start)
            namecheap_domains = []
            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                try:
                    namecheap_domains = get_email_manager().get_all_domains()
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

            # Fresh start, clear database
            # Store existing domain numbers before clearing
            existing_domains = db.get_all_domains_with_redirections()
            domain_numbers = {d['domain_name']: d['domain_number'] for d in existing_domains}

            # Clear existing domains from database
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM redirections')
                cursor.execute('DELETE FROM domains WHERE id NOT IN (SELECT DISTINCT client_id FROM domains WHERE client_id IS NOT NULL)')
                conn.commit()

            start_index = 0
        
        sync_progress["total"] = len(namecheap_domains)
        print(f"🔄 Starting background sync of {sync_progress['total']} domains...")
        
        # Process domains with aggressive rate limiting
        for i, domain_name in enumerate(namecheap_domains[start_index:], start_index + 1):
            # Check if sync should stop
            if sync_progress["should_stop"]:
                sync_progress["status"] = "stopped"
                sync_progress["current_domain"] = ""
                print(f"⏹ Sync stopped by user at domain {i}/{sync_progress['total']}")
                return

            sync_progress["processed"] = i
            sync_progress["current_domain"] = domain_name

            try:
                print(f"Processing {i}/{sync_progress['total']}: {domain_name}")
                
                # Add domain using the proper function
                try:
                    if domain_name in domain_numbers:
                        # Update existing domain (it should already exist, just update timestamp)
                        db.add_or_update_domain(domain_name)
                        sync_progress["domains_updated"] += 1
                    else:
                        # New domain gets new number
                        db.add_or_update_domain(domain_name)
                        sync_progress["domains_added"] += 1
                except Exception as domain_error:
                    print(f"⚠️ Error adding domain {domain_name}: {domain_error}")
                    # Continue processing even if domain add fails
                    sync_progress["errors"].append(f"{domain_name}: Database error - {str(domain_error)}")
                
                # Get redirections and DNS records with retry logic for rate limits
                redirections_fetched = False
                redirect_retry = 0
                max_redirect_retries = 5  # Increased from 3 to 5 retries

                while redirect_retry < max_redirect_retries and not redirections_fetched:
                    try:
                        # Fetch all DNS records (includes redirections, TXT, MX, etc.)
                        all_dns_records = get_email_manager().api_client._get_all_hosts(domain_name)
                        redirections_fetched = True

                        if all_dns_records:
                            # Store all DNS records in database
                            db.backup_dns_records(domain_name, all_dns_records)
                            print(f"  📋 Stored {len(all_dns_records)} DNS records for {domain_name}")

                            # Extract URL redirections from DNS records
                            redirections = []
                            for record in all_dns_records:
                                if isinstance(record, dict):
                                    record_type = record.get('Type', '').upper()
                                    if record_type in ['URL', 'URL301', 'URL302', 'REDIRECT']:
                                        redirections.append({
                                            'type': 'URL Redirect (301)' if record_type == 'URL301' else 'URL Redirect',
                                            'target': record.get('Address', ''),
                                            'name': record.get('Name', '@')
                                        })

                            if redirections:
                                db.update_redirections(domain_name, redirections)
                                print(f"  ✅ Added {len(redirections)} redirections for {domain_name}")

                            # Check and update DNS issues
                            dns_issues = db.check_dns_records_for_domain(domain_name)
                            db.update_domain_dns_issues(domain_name, dns_issues)

                            db.update_domain_sync_status(domain_name, 'synced')
                        else:
                            db.update_domain_sync_status(domain_name, 'synced')
                            print(f"  ℹ️ No DNS records found for {domain_name}")

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
                            if redirect_retry <= 2:  # Only retry twice, then pause
                                # Short wait times for initial retries: 5s, 10s
                                wait_time = 5 * redirect_retry
                                print(f"  ⏳ Rate limited for {domain_name}, waiting {wait_time}s (attempt {redirect_retry}/{max_redirect_retries})")
                                time.sleep(wait_time)
                                continue
                            else:
                                # Rate limit hit, pause the sync
                                print(f"🚫 Rate limit detected at domain {domain_name}. Pausing sync...")
                                sync_progress["status"] = "rate_limited"
                                sync_progress["current_domain"] = domain_name
                                sync_progress["paused_at_index"] = i - 1  # Index where we need to resume (0-based)
                                sync_progress["paused_domains"] = namecheap_domains  # Store the domain list for resume
                                sync_progress["rate_limit_message"] = f"Namecheap rate limit exceeded at domain {domain_name}. Please wait a few minutes and click Resume to continue."
                                return  # Exit the sync function
                        else:
                            print(f"  ⚠️ Error getting redirections for {domain_name}: {redirect_error}")
                            db.update_domain_sync_status(domain_name, 'not_synced')
                            sync_progress["errors"].append(f"{domain_name}: {str(redirect_error)}")
                            break
                
                # Balanced delays to avoid rate limiting
                base_delay = 1.5  # Start with 1.5 second delay
                if len(sync_progress["errors"]) > 5:  # If we're getting errors, slow down
                    base_delay = 4
                elif len(sync_progress["errors"]) > 2:
                    base_delay = 3

                # Add slight progressive delay for large batches
                if i > 100:  # After 100 domains, longer delays
                    base_delay += 1
                elif i > 50:  # After 50 domains, medium delays
                    base_delay += 0.5

                time.sleep(base_delay)
                    
            except Exception as e:
                print(f"Error syncing domain {domain_name}: {e}")
                sync_progress["errors"].append(f"{domain_name}: {str(e)}")
                # Still add the domain to database even if redirect fetch failed
                try:
                    # Use the proper add_or_update function
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
        manager = get_email_manager()
        if not manager:
            return jsonify({"error": "Email manager not initialized"}), 503
        
        # Check if sync is already running
        if sync_progress["status"] == "running":
            return jsonify({"error": "Sync already in progress"}), 409
        
        # Get all domains from Namecheap
        namecheap_domains = get_email_manager().get_all_domains()
        
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
        "errors": sync_progress["errors"][-5:] if sync_progress["errors"] else [],  # Last 5 errors
        "total_errors": len(sync_progress["errors"]) if sync_progress["errors"] else 0,
        "rate_limit_message": sync_progress.get("rate_limit_message"),
        "paused_at_index": sync_progress.get("paused_at_index")
    })

@app.route('/api/sync-errors', methods=['GET'])
def get_sync_errors():
    """Get detailed sync errors"""
    global sync_progress

    return jsonify({
        "errors": sync_progress["errors"] if sync_progress["errors"] else [],
        "total_errors": len(sync_progress["errors"]) if sync_progress["errors"] else 0,
        "last_sync_status": sync_progress["status"]
    })

@app.route('/api/backup-database', methods=['POST'])
def backup_database():
    """Create a backup of current database state"""
    try:
        import json
        from datetime import datetime

        # Get all data
        domains = db.get_all_domains_with_redirections()
        clients = db.get_all_clients()

        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "domains": domains,
            "clients": clients
        }

        # Save to a backup file (this would ideally be sent to external storage)
        backup_filename = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_filename, 'w') as f:
            json.dump(backup_data, f, indent=2)

        return jsonify({
            "status": "success",
            "message": f"Database backed up to {backup_filename}",
            "backup_file": backup_filename,
            "domains_count": len(domains),
            "clients_count": len(clients)
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/debug-dns/<domain_name>', methods=['GET'])
def debug_dns_records(domain_name):
    """Debug DNS records for a specific domain"""
    try:
        manager = get_email_manager()
        if not manager:
            return jsonify({"error": "Email manager not initialized"}), 503

        print(f"🔍 DEBUGGING DNS for domain: {domain_name}")

        # Get all DNS records
        dns_records = get_email_manager().api_client._get_all_hosts(domain_name)

        print(f"📋 Retrieved {len(dns_records)} DNS records")

        # Categorize records
        categorized = {
            "url_redirects": [],
            "a_records": [],
            "cname_records": [],
            "mx_records": [],
            "txt_records": [],
            "other_records": []
        }

        for record in dns_records:
            record_type = record.get('Type', '').upper()
            record_info = {
                "name": record.get('Name', ''),
                "type": record_type,
                "address": record.get('Address', ''),
                "ttl": record.get('TTL', ''),
                "mx_pref": record.get('MXPref', '')
            }

            if record_type == 'URL':
                categorized["url_redirects"].append(record_info)
            elif record_type == 'A':
                categorized["a_records"].append(record_info)
            elif record_type == 'CNAME':
                categorized["cname_records"].append(record_info)
            elif record_type == 'MX':
                categorized["mx_records"].append(record_info)
            elif record_type == 'TXT':
                categorized["txt_records"].append(record_info)
            else:
                categorized["other_records"].append(record_info)

        return jsonify({
            "status": "success",
            "domain": domain_name,
            "total_records": len(dns_records),
            "raw_records": dns_records,
            "categorized": categorized,
            "analysis": {
                "has_url_redirects": len(categorized["url_redirects"]) > 0,
                "has_other_dns": len(dns_records) - len(categorized["url_redirects"]) > 0,
                "safe_to_modify": len(categorized["url_redirects"]) > 0 and len(dns_records) == len(categorized["url_redirects"])
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/restore-database', methods=['POST'])
def restore_database():
    """Restore database from backup data"""
    try:
        data = request.get_json()
        backup_data = data.get('backup_data')

        if not backup_data:
            return jsonify({"status": "error", "message": "No backup data provided"}), 400

        # Restore clients first
        clients = backup_data.get('clients', [])
        for client in clients:
            try:
                # Skip default "Unassigned" client
                if client.get('name') != 'Unassigned':
                    db.add_client(client.get('name'), client.get('url'))
            except Exception as e:
                print(f"Warning: Could not restore client {client.get('name')}: {e}")

        # Restore domains and redirections
        domains = backup_data.get('domains', [])
        for domain in domains:
            try:
                domain_name = domain.get('domain_name')
                if domain_name:
                    # Add domain
                    db.add_or_update_domain(domain_name)

                    # Restore redirections
                    redirections = domain.get('redirections', [])
                    if redirections:
                        db.update_redirections(domain_name, redirections)

                    # Restore client assignment
                    if domain.get('client_id'):
                        db.assign_domain_to_client(domain_name, domain.get('client_id'))

            except Exception as e:
                print(f"Warning: Could not restore domain {domain.get('domain_name')}: {e}")

        return jsonify({
            "status": "success",
            "message": "Database restored successfully",
            "restored_domains": len(domains),
            "restored_clients": len(clients)
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stop-sync', methods=['POST'])
def stop_sync():
    """Stop the current sync process"""
    global sync_progress

    if sync_progress["status"] == "running":
        sync_progress["should_stop"] = True
        return jsonify({"status": "stopping"})
    else:
        return jsonify({"error": "No sync in progress"}), 400

@app.route('/api/resume-sync', methods=['POST'])
def resume_sync():
    """Resume a paused sync process"""
    global sync_progress

    if sync_progress["status"] != "rate_limited":
        return jsonify({"error": "No paused sync to resume"}), 400

    if sync_progress.get("paused_at_index") is None:
        return jsonify({"error": "No resume point found"}), 400

    try:
        # Reset sync progress for resume
        sync_progress["status"] = "running"
        sync_progress["should_stop"] = False
        sync_progress["rate_limit_message"] = None

        print(f"🔄 Resuming sync from index {sync_progress['paused_at_index']}")

        # Check if we're resuming a selected domains sync or full sync
        paused_domains = sync_progress.get("paused_domains")
        if paused_domains and len(paused_domains) != len(sync_progress.get("all_domains", [])):
            # This is a selected domains sync - use the specialized function
            sync_thread = threading.Thread(
                target=background_sync_selected_domains,
                args=(paused_domains, sync_progress["paused_at_index"])
            )
        else:
            # This is a full sync - use the main sync function
            sync_thread = threading.Thread(
                target=background_sync_with_rate_limiting,
                args=(sync_progress["paused_at_index"],)
            )

        sync_thread.daemon = True
        sync_thread.start()

        return jsonify({"status": "resumed", "message": "Sync resumed successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sync-selected-domains', methods=['POST'])
def sync_selected_domains():
    """Sync only selected domains"""
    global sync_progress

    try:
        data = request.get_json()
        selected_domains = data.get('domains', [])

        if not selected_domains:
            return jsonify({"error": "No domains selected"}), 400

        # Check if sync is already running
        if sync_progress["status"] == "running":
            return jsonify({"error": "Sync already in progress"}), 409

        # Reset progress
        sync_progress = {
            "status": "starting",
            "processed": 0,
            "total": len(selected_domains),
            "current_domain": "",
            "domains_added": 0,
            "domains_updated": 0,
            "errors": [],
            "should_stop": False,
            "paused_at_index": None,
            "rate_limit_message": None,
            "paused_domains": selected_domains
        }

        # Start background sync for selected domains
        def sync_selected():
            background_sync_selected_domains(selected_domains)

        thread = threading.Thread(target=sync_selected)
        thread.daemon = True
        thread.start()

        return jsonify({"status": "started", "total": len(selected_domains)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def background_sync_selected_domains(selected_domains, resume_from_index=None):
    """Background function to sync selected domains with rate limiting"""
    global sync_progress

    try:
        sync_progress["status"] = "running"
        start_index = resume_from_index if resume_from_index is not None else 0

        for i, domain_name in enumerate(selected_domains[start_index:], start_index + 1):
            # Check if sync should stop
            if sync_progress["should_stop"]:
                sync_progress["status"] = "stopped"
                sync_progress["current_domain"] = ""
                return

            sync_progress["processed"] = i
            sync_progress["current_domain"] = domain_name

            try:
                # Sync single domain with retry logic
                retry = 0
                max_retries = 3
                synced = False

                while retry < max_retries and not synced:
                    try:
                        # Fetch all DNS records (includes redirections, TXT, MX, etc.)
                        all_dns_records = get_email_manager().api_client._get_all_hosts(domain_name)

                        if all_dns_records is not None and len(all_dns_records) > 0:
                            # Update domain in database
                            db.add_or_update_domain(domain_name)

                            # Store all DNS records in database
                            db.backup_dns_records(domain_name, all_dns_records)
                            print(f"  📋 Stored {len(all_dns_records)} DNS records for {domain_name}")

                            # Extract URL redirections from DNS records
                            redirections = []
                            for record in all_dns_records:
                                if isinstance(record, dict):
                                    record_type = record.get('Type', '').upper()
                                    if record_type in ['URL', 'URL301', 'URL302', 'REDIRECT']:
                                        redirections.append({
                                            'type': 'URL Redirect (301)' if record_type == 'URL301' else 'URL Redirect',
                                            'target': record.get('Address', ''),
                                            'name': record.get('Name', '@')
                                        })

                            if redirections:
                                db.update_redirections(domain_name, redirections)
                                print(f"  ✅ Added {len(redirections)} redirections for {domain_name}")

                            # Check and update DNS issues
                            dns_issues = db.check_dns_records_for_domain(domain_name)
                            db.update_domain_dns_issues(domain_name, dns_issues)

                            db.update_domain_sync_status(domain_name, 'synced')
                            sync_progress["domains_updated"] += 1
                            synced = True
                        else:
                            db.update_domain_sync_status(domain_name, 'not_synced')

                    except Exception as e:
                        retry += 1
                        error_msg = str(e)

                        # Check for various rate limiting indicators
                        is_rate_limited = (
                            "too many requests" in error_msg.lower() or
                            "rate limit" in error_msg.lower() or
                            "connection/timeout error" in error_msg.lower() or
                            "502" in error_msg or "503" in error_msg or "504" in error_msg
                        )

                        if is_rate_limited:
                            if retry <= 2:  # Only retry twice, then pause
                                wait_time = 5 * retry
                                print(f"  ⏳ Rate limited for {domain_name}, waiting {wait_time}s (attempt {retry}/{max_retries})")
                                time.sleep(wait_time)
                                continue
                            else:
                                # Rate limit hit, pause the sync
                                print(f"🚫 Rate limit detected at domain {domain_name}. Pausing sync...")
                                sync_progress["status"] = "rate_limited"
                                sync_progress["current_domain"] = domain_name
                                sync_progress["paused_at_index"] = i - 1  # Index where we need to resume (0-based)
                                sync_progress["paused_domains"] = selected_domains
                                sync_progress["rate_limit_message"] = f"Namecheap rate limit exceeded at domain {domain_name}. Please wait a few minutes and click Resume to continue."
                                return  # Exit the sync function
                        else:
                            sync_progress["errors"].append(f"{domain_name}: {str(e)}")
                            db.update_domain_sync_status(domain_name, 'not_synced')
                            break

                # Add delay between domains
                if i < len(selected_domains):
                    time.sleep(1.5)

            except Exception as e:
                sync_progress["errors"].append(f"{domain_name}: {str(e)}")

        sync_progress["status"] = "completed"
        sync_progress["current_domain"] = ""

    except Exception as e:
        print(f"Error in background sync: {e}")
        sync_progress["status"] = "error"
        sync_progress["errors"].append(f"Sync error: {str(e)}")

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

        # Fetch all DNS records (includes redirections, TXT, MX, etc.)
        all_dns_records = get_email_manager().api_client._get_all_hosts(domain_name)

        # Store all DNS records in database
        if all_dns_records:
            db.backup_dns_records(domain_name, all_dns_records)

            # Extract URL redirections from DNS records
            redirections = []
            for record in all_dns_records:
                if isinstance(record, dict):
                    record_type = record.get('Type', '').upper()
                    if record_type in ['URL', 'URL301', 'URL302', 'REDIRECT']:
                        redirections.append({
                            'type': 'URL Redirect (301)' if record_type == 'URL301' else 'URL Redirect',
                            'target': record.get('Address', ''),
                            'name': record.get('Name', '@')
                        })

            # Update redirections in database
            db.update_redirections(domain_name, redirections)

            # Check and update DNS issues
            dns_issues = db.check_dns_records_for_domain(domain_name)
            db.update_domain_dns_issues(domain_name, dns_issues)
        else:
            redirections = []

        return jsonify({
            "status": "success",
            "domain_name": domain_name,
            "domain_number": domain_number,
            "redirections_count": len(redirections),
            "dns_records_count": len(all_dns_records) if all_dns_records else 0
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
def update_client(client_id):
    """Update client name and URL"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        url = data.get('url', '').strip() or None

        if name:
            # Update both name and URL if name is provided
            db.update_client(client_id, name, url)
        else:
            # Just update URL if only URL is provided (backward compatibility)
            db.update_client_url(client_id, url)

        return jsonify({
            "status": "success",
            "message": "Client updated successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/clients/<int:client_id>', methods=['DELETE'])
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
                
                # Use SAFE redirect update with DNS backup/restore
                print(f"🔄 Safe bulk update for {domain_name} -> {target}")
                success = get_email_manager().api_client.set_domain_redirection(domain_name, '@', target)

                if success:
                    results.append({
                        "domain_name": domain_name,
                        "success": True,
                        "message": f"Successfully updated redirect for {domain_name}",
                        "processed": i + 1,
                        "total": len(updates)
                    })
                else:
                    results.append({
                        "domain_name": domain_name,
                        "success": False,
                        "error": "Failed to update redirect",
                        "processed": i + 1,
                        "total": len(updates)
                    })

            except Exception as update_error:
                results.append({
                    "domain_name": update.get('domain_name', 'unknown'),
                    "success": False,
                    "error": str(update_error),
                    "processed": i + 1,
                    "total": len(updates)
                })

        return jsonify({
            "status": "success",
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
        manager = get_email_manager()
        if not manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        # Test API connection first
        connection_test = get_email_manager().api_client.test_connection()
        if not connection_test:
            return jsonify({
                "status": "error",
                "message": "Namecheap API connection failed. Check credentials and IP whitelist.",
                "debug_info": {
                    "api_user": get_email_manager().api_client.api_user,
                    "client_ip": get_email_manager().api_client.client_ip,
                    "api_key_present": bool(get_email_manager().api_client.api_key)
                }
            }), 503
        
        # Get all domains
        domains = get_email_manager().get_all_domains()
        
        if not domains:
            return jsonify({
                "status": "error", 
                "message": "No domains found in your Namecheap account or API connection issue.",
                "debug_info": {
                    "connection_test": connection_test,
                    "api_user": get_email_manager().api_client.api_user,
                    "client_ip": get_email_manager().api_client.client_ip
                }
            }), 404
        
        # Get redirections for each domain (limit to first 50 with slower rate)
        domains_with_redirections = []
        processed = 0
        max_domains = min(100, len(domains))  # Process up to 100 domains with rate limiting
        
        for domain in domains[:max_domains]:
            try:
                redirections = get_email_manager().api_client.get_domain_redirections(domain)
                
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
        manager = get_email_manager()
        if not manager:
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
        success = get_email_manager().api_client.set_domain_redirection(domain, name, target)
        
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
        manager = get_email_manager()
        if not manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25))  # Increased to 25 domains per batch
        
        # Get all domains
        domains = get_email_manager().get_all_domains()
        
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
                redirections = get_email_manager().api_client.get_domain_redirections(domain)
                
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
        manager = get_email_manager()
        if not manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503
        
        # Test API connection first
        connection_test = get_email_manager().api_client.test_connection()
        if not connection_test:
            return jsonify({
                "status": "error",
                "message": "Namecheap API connection failed. Check credentials and IP whitelist.",
                "debug_info": {
                    "api_user": get_email_manager().api_client.api_user,
                    "client_ip": get_email_manager().api_client.client_ip,
                    "api_key_present": bool(get_email_manager().api_client.api_key)
                }
            }), 503
        
        # Get all domains
        domains = get_email_manager().get_all_domains()
        
        if not domains:
            return jsonify({
                "status": "error", 
                "message": "No domains found in your Namecheap account or API connection issue.",
                "debug_info": {
                    "connection_test": connection_test,
                    "api_user": get_email_manager().api_client.api_user,
                    "client_ip": get_email_manager().api_client.client_ip
                }
            }), 404
        
        # Get URL redirections for each domain
        all_redirections = []
        processed = 0
        
        for domain in domains:
            try:
                redirections = get_email_manager().api_client.get_domain_redirections(domain)
                
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
    """Get all domains - try Namecheap first, fallback to database"""
    try:
        manager = get_email_manager()
        if not manager:
            return jsonify({
                "status": "error",
                "message": "Email manager not initialized. Check API credentials."
            }), 503

        # Try to get domains from Namecheap, but fallback to DB if rate limited
        domain_names = []
        try:
            domain_names = get_email_manager().get_all_domains()
            print(f"✅ Successfully fetched {len(domain_names)} domains from Namecheap")
        except Exception as e:
            print(f"⚠️ Could not fetch from Namecheap (likely rate limited): {e}")
            print(f"📚 Falling back to database...")

        # Get domains with redirections from database
        db_domains = db.get_all_domains_with_redirections()

        # Create a lookup for database domains (case-insensitive)
        db_lookup = {d['domain_name'].lower(): d for d in db_domains}

        # Debug logging
        print(f"DEBUG: Namecheap returned {len(domain_names)} domains")
        print(f"DEBUG: Database has {len(db_domains)} domains")
        if db_domains:
            print(f"DEBUG: First DB domain: {db_domains[0]['domain_name']}")
        if domain_names:
            print(f"DEBUG: First Namecheap domain: {domain_names[0]}")
        print(f"DEBUG: db_lookup keys count: {len(db_lookup)}")

        # Get all clients for reference
        clients = db.get_all_clients()
        client_lookup = {c['id']: c for c in clients}

        # If Namecheap failed (no domains), use database domains instead
        if not domain_names and db_domains:
            print(f"📚 Using {len(db_domains)} domains from database (Namecheap unavailable)")
            domain_names = [d['domain_name'] for d in db_domains]

        # Transform domain names into objects that React expects
        domains = []
        for i, domain_name in enumerate(domain_names, 1):
            db_domain = db_lookup.get(domain_name.lower(), {})


            # Use database domain number if available
            domain_number = db_domain.get('domain_number', i)

            # Get the primary redirect URL from the redirections array
            redirect_url = ''
            redirections = db_domain.get('redirections', [])
            for redirect in redirections:
                # Check for @ record with any URL type
                if redirect.get('name') == '@':
                    redirect_type = redirect.get('type', '').lower()
                    if 'url' in redirect_type or redirect_type in ['url', 'url redirect', 'redirect']:
                        redirect_url = redirect.get('target', '')
                        break

            # If no @ record found, check for any URL redirect as fallback
            if not redirect_url:
                for redirect in redirections:
                    redirect_type = redirect.get('type', '').lower()
                    if 'url' in redirect_type and redirect.get('target'):
                        redirect_url = redirect.get('target', '')
                        print(f"DEBUG: Fallback - Using redirect URL: {redirect_url}")
                        break

            domain_obj = {
                "domain_name": domain_name,
                "domain_number": domain_number,
                "redirect_url": redirect_url,
                "status": db_domain.get('sync_status', 'ready'),
                "client_id": db_domain.get('client_id'),
                "client_name": client_lookup.get(db_domain.get('client_id'), {}).get('name', 'Unassigned') if db_domain.get('client_id') else 'Unassigned',
                "updated_at": db_domain.get('updated_at'),
                "dns_issues": db_domain.get('dns_issues', None)
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
        
        manager = get_email_manager()
        if not manager:
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
        connection_test = get_email_manager().api_client.test_connection()
        
        # Try to get domains
        domains = get_email_manager().get_all_domains()
        
        return jsonify({
            "status": "debug",
            "connection_test": connection_test,
            "actual_outbound_ip": actual_ip,
            "configured_ip": get_email_manager().api_client.client_ip,
            "api_credentials": {
                "api_user": get_email_manager().api_client.api_user,
                "client_ip": get_email_manager().api_client.client_ip,
                "api_key_length": len(get_email_manager().api_client.api_key) if get_email_manager().api_client.api_key else 0
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

@app.route('/api/debug-init', methods=['GET'])
def debug_init():
    """Debug endpoint to check initialization issues"""
    import os

    debug_info = {
        "environment_vars": {
            "NAMECHEAP_API_USER": bool(os.environ.get('NAMECHEAP_API_USER')),
            "NAMECHEAP_API_KEY": bool(os.environ.get('NAMECHEAP_API_KEY')),
            "NAMECHEAP_USERNAME": bool(os.environ.get('NAMECHEAP_USERNAME')),
            "NAMECHEAP_CLIENT_IP": os.environ.get('NAMECHEAP_CLIENT_IP', 'Not set'),
            "DATABASE_PATH": os.environ.get('DATABASE_PATH', 'Not set')
        },
        "initialization_attempt": {}
    }

    # Try to initialize and capture the error
    try:
        test_manager = EmailRedirectionManager()
        debug_info["initialization_attempt"]["success"] = True
        debug_info["initialization_attempt"]["message"] = "Manager initialized successfully"
    except Exception as e:
        debug_info["initialization_attempt"]["success"] = False
        debug_info["initialization_attempt"]["error"] = str(e)
        debug_info["initialization_attempt"]["error_type"] = type(e).__name__

        # Try to get more specific info
        import traceback
        debug_info["initialization_attempt"]["traceback"] = traceback.format_exc()

    return jsonify(debug_info)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "email-redirect-tool",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/debug-db', methods=['GET'])
def debug_database():
    """Debug endpoint to see raw database structure"""
    try:
        # Get first 3 domains from database with full structure
        db_domains = db.get_all_domains_with_redirections()[:3]

        return jsonify({
            "status": "success",
            "db_domains_sample": db_domains,
            "total_db_domains": len(db.get_all_domains_with_redirections())
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
        manager = get_email_manager()
        if not manager:
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
            "errors": [],
            "should_stop": False,
            "paused_at_index": None,
            "rate_limit_message": None,
            "paused_domains": None
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

        # Use new SAFE redirect update with complete DNS backup/restore system
        success = False
        save_retry = 0
        max_save_retries = 5

        while save_retry < max_save_retries and not success:
            try:
                success = get_email_manager().api_client.set_domain_redirection(domain, '@', target)
                if success:
                    break  # Success, exit retry loop
                else:
                    raise Exception("Failed to set domain redirection")

            except Exception as save_error:
                save_retry += 1
                error_msg = str(save_error)

                # Check for rate limiting indicators
                is_rate_limited = (
                    "too many requests" in error_msg.lower() or
                    "rate limit" in error_msg.lower() or
                    "connection/timeout error" in error_msg.lower() or
                    "502" in error_msg or "503" in error_msg or "504" in error_msg
                )

                if is_rate_limited and save_retry < max_save_retries:
                    # Progressive wait times: 5s, 10s, 20s, 40s, 60s
                    wait_time = min(5 * (2 ** (save_retry - 1)), 60) if save_retry > 0 else 5
                    print(f"  ⏳ Save: Rate limited for {domain}, waiting {wait_time}s (attempt {save_retry}/{max_save_retries})")
                    time.sleep(wait_time)
                elif save_retry >= max_save_retries:
                    print(f"  ❌ Save: Max retries reached for {domain}")
                    break
                else:
                    # Non-rate-limit error, don't retry
                    print(f"  ⚠️ Save: Error for {domain}: {save_error}")
                    break

        if success:
            # Verify the redirection was actually set correctly
            import time
            time.sleep(2)  # Small delay to allow Namecheap to process
            verified = get_email_manager().api_client.verify_domain_redirection(domain, '@', target)

            if verified:
                # Ensure domain exists in database
                db.add_or_update_domain(domain)

                # Update sync status
                db.update_domain_sync_status(domain, 'synced')

                # Fetch and store the actual redirections from Namecheap to database
                try:
                    redirections = get_email_manager().api_client.get_domain_redirections(domain)
                    if redirections:
                        db.update_redirections(domain, redirections)
                        print(f"✅ Updated database with {len(redirections)} redirections for {domain}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not fetch redirections for {domain}: {e}")

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
                success = get_email_manager().api_client.set_domain_redirection(domain, '@', bulk_target)

                verified = False
                if success:
                    # Verify the redirection was actually set correctly
                    import time
                    time.sleep(2)  # Small delay to allow Namecheap to process
                    verified = get_email_manager().api_client.verify_domain_redirection(domain, '@', bulk_target)

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
@app.route('/api/dns-backup-history/<domain_name>', methods=['GET'])
def get_dns_backup_history(domain_name):
    """Get DNS backup history for a specific domain"""
    try:
        history = db.get_dns_backup_history(domain_name)
        return jsonify({
            "status": "success",
            "domain": domain_name,
            "backups": history
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/dns-records/<domain_name>', methods=['GET'])
def get_dns_records_backup(domain_name):
    """Get current DNS records from backup for a specific domain"""
    try:
        records = db.get_current_dns_records(domain_name)
        return jsonify({
            "status": "success",
            "domain": domain_name,
            "records": records,
            "total_records": len(records)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

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

def background_bulk_dns_update(domains, records_data, resume_from_index=None):
    """Background function to handle bulk DNS updates with rate limiting"""
    global bulk_dns_progress

    try:
        bulk_dns_progress["status"] = "running"
        start_index = resume_from_index if resume_from_index is not None else 0

        print(f"🌐 Starting bulk DNS update for {len(domains)} domains from index {start_index}")
        print(f"📝 Records: {len(records_data)} record(s) to add")
        for record in records_data:
            print(f"   - {record['type']} {record['name']} -> {record['address']}")

        # Process domains with rate limiting
        for i, domain_name in enumerate(domains[start_index:], start_index + 1):
            # Check if update should stop
            if bulk_dns_progress["should_stop"]:
                bulk_dns_progress["status"] = "stopped"
                bulk_dns_progress["current_domain"] = ""
                print(f"⏹ Bulk DNS update stopped by user at domain {i}/{bulk_dns_progress['total']}")
                return

            bulk_dns_progress["processed"] = i
            bulk_dns_progress["current_domain"] = domain_name

            print(f"🌐 Processing DNS {i}/{bulk_dns_progress['total']}: {domain_name}")

            # Add DNS record with retry logic for rate limits
            dns_updated = False
            dns_retry = 0
            max_dns_retries = 3

            while dns_retry < max_dns_retries and not dns_updated:
                try:
                    # Get current DNS records
                    existing_hosts = get_email_manager().api_client._get_all_hosts(domain_name)

                    if existing_hosts is None:
                        raise Exception("Could not fetch existing DNS records")

                    # Start with existing records
                    all_records = list(existing_hosts)

                    # Add each new record
                    for record_data in records_data:
                        new_record = {
                            'Name': record_data['name'],
                            'Type': record_data['type'],
                            'Address': record_data['address'],
                            'TTL': record_data['ttl']
                        }

                        # Add MXPref for MX records
                        if record_data['type'] == 'MX' and record_data.get('mx_pref'):
                            new_record['MXPref'] = record_data['mx_pref']

                        # For TXT records, only remove exact duplicates (same name, type, and value)
                        # For other record types, remove existing records with same name and type
                        if record_data['type'] == 'TXT':
                            # Only remove if exact duplicate (same name, type, and address)
                            all_records = [
                                host for host in all_records
                                if not (host.get('Name') == record_data['name'] and
                                       host.get('Type') == record_data['type'] and
                                       host.get('Address') == record_data['address'])
                            ]
                        else:
                            # For non-TXT records, replace existing records with same name and type
                            all_records = [
                                host for host in all_records
                                if not (host.get('Name') == record_data['name'] and host.get('Type') == record_data['type'])
                            ]

                        # Add the new record
                        all_records.append(new_record)

                    # Update DNS via setHosts API
                    domain_parts = domain_name.split('.')
                    if len(domain_parts) < 2:
                        raise Exception(f"Invalid domain format: {domain_name}")

                    sld = domain_parts[0]
                    tld = '.'.join(domain_parts[1:])

                    # Handle common multi-part TLDs
                    common_tlds = ['co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'com.au', 'net.au', 'org.au']
                    for common_tld in common_tlds:
                        if domain_name.endswith('.' + common_tld):
                            sld = domain_name.replace('.' + common_tld, '')
                            tld = common_tld
                            break

                    # Build setHosts parameters
                    params = {'SLD': sld, 'TLD': tld}

                    for idx, record in enumerate(all_records, 1):
                        params[f'HostName{idx}'] = record['Name']
                        params[f'RecordType{idx}'] = record['Type']
                        params[f'Address{idx}'] = record['Address']
                        params[f'TTL{idx}'] = record['TTL']
                        if record.get('MXPref'):
                            params[f'MXPref{idx}'] = record['MXPref']

                    # Make API call
                    response = get_email_manager().api_client._make_request('namecheap.domains.dns.setHosts', **params)

                    # Check response
                    command_response = None
                    for key, value in response.items():
                        if 'CommandResponse' in key:
                            command_response = value
                            break

                    if command_response:
                        hosts_result = None
                        for key, value in command_response.items():
                            if 'DomainDNSSetHostsResult' in key:
                                hosts_result = value
                                break

                        if hosts_result and hosts_result.get('IsSuccess') == 'true':
                            print(f"  ✅ DNS record added for {domain_name}")
                            bulk_dns_progress["successful"] += 1
                            dns_updated = True
                        else:
                            raise Exception(f"Namecheap API returned failure: {hosts_result}")
                    else:
                        raise Exception("Unexpected response format from Namecheap")

                except Exception as dns_error:
                    dns_retry += 1
                    error_msg = str(dns_error)

                    # Check for rate limiting indicators
                    is_rate_limited = (
                        "too many requests" in error_msg.lower() or
                        "rate limit" in error_msg.lower() or
                        "connection/timeout error" in error_msg.lower() or
                        "502" in error_msg or "503" in error_msg or "504" in error_msg
                    )

                    if is_rate_limited:
                        if dns_retry <= 2:  # Only retry twice, then pause
                            wait_time = 5 * dns_retry
                            print(f"  ⏳ Rate limited for {domain_name}, waiting {wait_time}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            # Rate limit hit, pause the update
                            print(f"🚫 Rate limit detected at domain {domain_name}. Pausing DNS update...")
                            bulk_dns_progress["status"] = "rate_limited"
                            bulk_dns_progress["current_domain"] = domain_name
                            bulk_dns_progress["paused_at_index"] = i - 1
                            bulk_dns_progress["paused_domains"] = domains
                            bulk_dns_progress["rate_limit_message"] = f"Namecheap rate limit exceeded at domain {domain_name}. Please wait and click Resume to continue."
                            return
                    else:
                        print(f"  ⚠️ Error updating DNS for {domain_name}: {dns_error}")
                        bulk_dns_progress["errors"].append(f"{domain_name}: {str(dns_error)}")
                        break

            # Small delay between domains
            time.sleep(1.5)

        bulk_dns_progress["status"] = "completed"
        bulk_dns_progress["current_domain"] = ""
        print(f"✅ Bulk DNS update completed: {bulk_dns_progress['successful']} successful, {len(bulk_dns_progress['errors'])} errors")

    except Exception as e:
        print(f"❌ Bulk DNS update failed: {e}")
        bulk_dns_progress["status"] = "error"
        bulk_dns_progress["error"] = str(e)

@app.route('/api/bulk-dns-update', methods=['POST'])
@require_auth
def bulk_dns_update():
    """Start bulk DNS record update"""
    global bulk_dns_progress

    try:
        data = request.get_json()
        domains = data.get('domains', [])
        records_data = data.get('records', [])

        if not domains:
            return jsonify({"error": "No domains provided"}), 400

        if not records_data:
            return jsonify({"error": "No records data provided"}), 400

        # Validate each record data
        required_fields = ['type', 'name', 'address', 'ttl']
        for record_data in records_data:
            for field in required_fields:
                if field not in record_data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if update is already running
        if bulk_dns_progress["status"] == "running":
            return jsonify({"error": "Bulk DNS update already in progress"}), 409

        # Reset progress
        bulk_dns_progress = {
            "status": "starting",
            "processed": 0,
            "total": len(domains),
            "current_domain": "",
            "successful": 0,
            "errors": [],
            "should_stop": False,
            "paused_at_index": None,
            "rate_limit_message": None,
            "paused_domains": domains,
            "records_data": records_data
        }

        # Start background update
        dns_thread = threading.Thread(target=background_bulk_dns_update, args=(domains, records_data))
        dns_thread.daemon = True
        dns_thread.start()

        return jsonify({
            "status": "started",
            "total": len(domains),
            "record_type": record_data['type']
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bulk-dns-progress', methods=['GET'])
def get_bulk_dns_progress():
    """Get bulk DNS update progress"""
    return jsonify({
        "status": bulk_dns_progress["status"],
        "processed": bulk_dns_progress["processed"],
        "total": bulk_dns_progress["total"],
        "current_domain": bulk_dns_progress["current_domain"],
        "successful": bulk_dns_progress["successful"],
        "errors": bulk_dns_progress["errors"][-5:] if bulk_dns_progress["errors"] else [],
        "total_errors": len(bulk_dns_progress["errors"]) if bulk_dns_progress["errors"] else 0,
        "rate_limit_message": bulk_dns_progress.get("rate_limit_message"),
        "paused_at_index": bulk_dns_progress.get("paused_at_index")
    })

@app.route('/api/stop-bulk-dns', methods=['POST'])
@require_auth
def stop_bulk_dns():
    """Stop bulk DNS update"""
    global bulk_dns_progress

    if bulk_dns_progress["status"] == "running":
        bulk_dns_progress["should_stop"] = True
        return jsonify({"status": "stopping"})
    else:
        return jsonify({"error": "No bulk DNS update in progress"}), 400

@app.route('/api/resume-bulk-dns', methods=['POST'])
@require_auth
def resume_bulk_dns():
    """Resume a paused bulk DNS update"""
    global bulk_dns_progress

    if bulk_dns_progress["status"] != "rate_limited":
        return jsonify({"error": "No paused bulk DNS update to resume"}), 400

    if bulk_dns_progress.get("paused_at_index") is None:
        return jsonify({"error": "No resume point found"}), 400

    try:
        # Reset progress for resume
        bulk_dns_progress["status"] = "running"
        bulk_dns_progress["should_stop"] = False
        bulk_dns_progress["rate_limit_message"] = None

        print(f"🔄 Resuming bulk DNS update from index {bulk_dns_progress['paused_at_index']}")

        # Start background thread to resume
        dns_thread = threading.Thread(
            target=background_bulk_dns_update,
            args=(bulk_dns_progress["paused_domains"], bulk_dns_progress["records_data"], bulk_dns_progress["paused_at_index"])
        )
        dns_thread.daemon = True
        dns_thread.start()

        return jsonify({"status": "resumed", "message": "Bulk DNS update resumed successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def background_bulk_dns_remove(domains, record_type, host_name, record_value=None, resume_from_index=None):
    """Background function to handle bulk DNS record removal with rate limiting"""
    global bulk_dns_remove_progress

    try:
        bulk_dns_remove_progress["status"] = "running"
        start_index = resume_from_index if resume_from_index is not None else 0

        print(f"🗑️ Starting bulk DNS removal for {len(domains)} domains from index {start_index}")
        print(f"📝 Removing: {record_type} {host_name} {record_value if record_value else '(all values)'}")

        # Process domains with rate limiting
        for i, domain_name in enumerate(domains[start_index:], start_index + 1):
            # Check if removal should stop
            if bulk_dns_remove_progress["should_stop"]:
                bulk_dns_remove_progress["status"] = "stopped"
                bulk_dns_remove_progress["current_domain"] = ""
                print(f"⏹ Bulk DNS removal stopped by user at domain {i}/{bulk_dns_remove_progress['total']}")
                return

            bulk_dns_remove_progress["processed"] = i
            bulk_dns_remove_progress["current_domain"] = domain_name

            print(f"🗑️ Processing DNS removal {i}/{bulk_dns_remove_progress['total']}: {domain_name}")

            # Remove DNS record with retry logic for rate limits
            dns_removed = False
            dns_retry = 0
            max_dns_retries = 3

            while dns_retry < max_dns_retries and not dns_removed:
                try:
                    # Get current DNS records
                    existing_hosts = get_email_manager().api_client._get_all_hosts(domain_name)

                    if existing_hosts is None:
                        raise Exception("Could not fetch existing DNS records")

                    # Filter out records to remove
                    filtered_hosts = []
                    removed_count = 0

                    for host in existing_hosts:
                        should_remove = False

                        # Check if this record matches removal criteria
                        if host.get('Type') == record_type and host.get('Name') == host_name:
                            if record_value:
                                # Remove only if value matches
                                if host.get('Address') == record_value:
                                    should_remove = True
                                    removed_count += 1
                            else:
                                # Remove all records matching type and host
                                should_remove = True
                                removed_count += 1

                        if not should_remove:
                            filtered_hosts.append(host)

                    if removed_count == 0:
                        print(f"  ℹ️ No matching records found for {domain_name}")
                        bulk_dns_remove_progress["successful"] += 1
                        dns_removed = True
                        continue

                    print(f"  🗑️ Removing {removed_count} DNS record(s) from {domain_name}")

                    # Update DNS via setHosts API with remaining records
                    domain_parts = domain_name.split('.')
                    if len(domain_parts) < 2:
                        raise Exception(f"Invalid domain format: {domain_name}")

                    sld = domain_parts[0]
                    tld = '.'.join(domain_parts[1:])

                    # Handle common multi-part TLDs
                    common_tlds = ['co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'com.au', 'net.au', 'org.au']
                    for common_tld in common_tlds:
                        if domain_name.endswith('.' + common_tld):
                            sld = domain_name.replace('.' + common_tld, '')
                            tld = common_tld
                            break

                    # Build setHosts parameters with remaining records
                    params = {'SLD': sld, 'TLD': tld}

                    for idx, record in enumerate(filtered_hosts, 1):
                        params[f'HostName{idx}'] = record['Name']
                        params[f'RecordType{idx}'] = record['Type']
                        params[f'Address{idx}'] = record['Address']
                        params[f'TTL{idx}'] = record['TTL']
                        if record.get('MXPref'):
                            params[f'MXPref{idx}'] = record['MXPref']

                    # Make API call
                    response = get_email_manager().api_client._make_request('namecheap.domains.dns.setHosts', **params)

                    # Check response
                    command_response = None
                    for key, value in response.items():
                        if 'CommandResponse' in key:
                            command_response = value
                            break

                    if command_response:
                        hosts_result = None
                        for key, value in command_response.items():
                            if 'DomainDNSSetHostsResult' in key:
                                hosts_result = value
                                break

                        if hosts_result and hosts_result.get('IsSuccess') == 'true':
                            print(f"  ✅ DNS records removed from {domain_name}")
                            bulk_dns_remove_progress["successful"] += 1
                            dns_removed = True
                        else:
                            raise Exception(f"Namecheap API returned failure: {hosts_result}")
                    else:
                        raise Exception("Unexpected response format from Namecheap")

                except Exception as dns_error:
                    dns_retry += 1
                    error_msg = str(dns_error)

                    # Check for rate limiting indicators
                    is_rate_limited = (
                        "too many requests" in error_msg.lower() or
                        "rate limit" in error_msg.lower() or
                        "connection/timeout error" in error_msg.lower() or
                        "502" in error_msg or "503" in error_msg or "504" in error_msg
                    )

                    if is_rate_limited:
                        if dns_retry <= 2:  # Only retry twice, then pause
                            wait_time = 5 * dns_retry
                            print(f"  ⏳ Rate limited for {domain_name}, waiting {wait_time}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            # Rate limit hit, pause the removal
                            print(f"🚫 Rate limit detected at domain {domain_name}. Pausing DNS removal...")
                            bulk_dns_remove_progress["status"] = "rate_limited"
                            bulk_dns_remove_progress["current_domain"] = domain_name
                            bulk_dns_remove_progress["paused_at_index"] = i - 1
                            bulk_dns_remove_progress["paused_domains"] = domains
                            bulk_dns_remove_progress["rate_limit_message"] = f"Namecheap rate limit exceeded at domain {domain_name}. Please wait and click Resume to continue."
                            return
                    else:
                        print(f"  ⚠️ Error removing DNS from {domain_name}: {dns_error}")
                        bulk_dns_remove_progress["errors"].append(f"{domain_name}: {str(dns_error)}")
                        break

            # Small delay between domains
            time.sleep(1.5)

        bulk_dns_remove_progress["status"] = "completed"
        bulk_dns_remove_progress["current_domain"] = ""
        print(f"✅ Bulk DNS removal completed: {bulk_dns_remove_progress['successful']} successful, {len(bulk_dns_remove_progress['errors'])} errors")

    except Exception as e:
        print(f"❌ Bulk DNS removal failed: {e}")
        bulk_dns_remove_progress["status"] = "error"
        bulk_dns_remove_progress["error"] = str(e)

@app.route('/api/bulk-dns-remove', methods=['POST'])
@require_auth
def bulk_dns_remove():
    """Start bulk DNS record removal"""
    global bulk_dns_remove_progress

    try:
        data = request.get_json()
        domains = data.get('domains', [])
        record_type = data.get('record_type')
        host_name = data.get('host_name')
        record_value = data.get('record_value')

        if not domains:
            return jsonify({"error": "No domains provided"}), 400

        if not record_type:
            return jsonify({"error": "Record type is required"}), 400

        if not host_name:
            return jsonify({"error": "Host name is required"}), 400

        # Check if removal is already running
        if bulk_dns_remove_progress["status"] == "running":
            return jsonify({"error": "Bulk DNS removal already in progress"}), 409

        # Reset progress
        bulk_dns_remove_progress = {
            "status": "starting",
            "processed": 0,
            "total": len(domains),
            "current_domain": "",
            "successful": 0,
            "errors": [],
            "should_stop": False,
            "paused_at_index": None,
            "rate_limit_message": None,
            "paused_domains": domains,
            "remove_criteria": {
                "type": record_type,
                "host": host_name,
                "value": record_value
            }
        }

        # Start background removal
        dns_thread = threading.Thread(
            target=background_bulk_dns_remove,
            args=(domains, record_type, host_name, record_value)
        )
        dns_thread.daemon = True
        dns_thread.start()

        return jsonify({
            "status": "started",
            "total": len(domains),
            "record_type": record_type,
            "host_name": host_name
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bulk-dns-remove-progress', methods=['GET'])
def get_bulk_dns_remove_progress():
    """Get bulk DNS removal progress"""
    return jsonify({
        "status": bulk_dns_remove_progress["status"],
        "processed": bulk_dns_remove_progress["processed"],
        "total": bulk_dns_remove_progress["total"],
        "current_domain": bulk_dns_remove_progress["current_domain"],
        "successful": bulk_dns_remove_progress["successful"],
        "errors": bulk_dns_remove_progress["errors"][-5:] if bulk_dns_remove_progress["errors"] else [],
        "total_errors": len(bulk_dns_remove_progress["errors"]) if bulk_dns_remove_progress["errors"] else 0,
        "rate_limit_message": bulk_dns_remove_progress.get("rate_limit_message"),
        "paused_at_index": bulk_dns_remove_progress.get("paused_at_index")
    })

@app.route('/api/stop-bulk-dns-remove', methods=['POST'])
@require_auth
def stop_bulk_dns_remove():
    """Stop bulk DNS removal"""
    global bulk_dns_remove_progress

    if bulk_dns_remove_progress["status"] == "running":
        bulk_dns_remove_progress["should_stop"] = True
        return jsonify({"status": "stopping"})
    else:
        return jsonify({"error": "No bulk DNS removal in progress"}), 400

@app.route('/api/resume-bulk-dns-remove', methods=['POST'])
@require_auth
def resume_bulk_dns_remove():
    """Resume a paused bulk DNS removal"""
    global bulk_dns_remove_progress

    if bulk_dns_remove_progress["status"] != "rate_limited":
        return jsonify({"error": "No paused bulk DNS removal to resume"}), 400

    if bulk_dns_remove_progress.get("paused_at_index") is None:
        return jsonify({"error": "No resume point found"}), 400

    try:
        # Reset progress for resume
        bulk_dns_remove_progress["status"] = "running"
        bulk_dns_remove_progress["should_stop"] = False
        bulk_dns_remove_progress["rate_limit_message"] = None

        print(f"🔄 Resuming bulk DNS removal from index {bulk_dns_remove_progress['paused_at_index']}")

        criteria = bulk_dns_remove_progress.get("remove_criteria", {})

        # Start background thread to resume
        dns_thread = threading.Thread(
            target=background_bulk_dns_remove,
            args=(
                bulk_dns_remove_progress["paused_domains"],
                criteria.get("type"),
                criteria.get("host"),
                criteria.get("value"),
                bulk_dns_remove_progress["paused_at_index"]
            )
        )
        dns_thread.daemon = True
        dns_thread.start()

        return jsonify({"status": "resumed", "message": "Bulk DNS removal resumed successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-dns-for-domain/<domain_name>', methods=['POST'])
def check_dns_for_domain(domain_name):
    """Check stored DNS records for a domain and update DNS issues column"""
    try:
        db = Database()
        issues = db.check_dns_records_for_domain(domain_name)
        db.update_domain_dns_issues(domain_name, issues)

        return jsonify({
            "status": "success",
            "domain": domain_name,
            "dns_issues": issues
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _wait_for_rate_limit_resume(rate_limit_state, progress_dict, domain_index):
    """Wait for rate limit pause to end, updating progress. Returns True if should stop."""
    progress_dict["status"] = "paused"
    progress_dict["paused_at_index"] = domain_index
    rate_status = rate_limit_state.get_status()
    progress_dict["pause_until"] = rate_status["pause_until"]
    progress_dict["rate_limit_message"] = f"Rate limit hit. Auto-resuming in {int(rate_status['time_until_resume'])}s"

    while rate_limit_state.get_status()["is_paused"]:
        if progress_dict["should_stop"]:
            progress_dict["status"] = "stopped"
            return True
        time.sleep(10)
        remaining = rate_limit_state.get_status()["time_until_resume"]
        progress_dict["rate_limit_message"] = f"Rate limit hit. Auto-resuming in {int(remaining)}s"

    progress_dict["status"] = "running"
    progress_dict["rate_limit_message"] = None
    progress_dict["pause_until"] = None
    return False


def background_dns_check(domains, start_index=0):
    """Background function to check DNS records with rate limiting and pause/resume"""
    global dns_check_progress
    from namecheap_client import rate_limit_state

    try:
        dns_check_progress["status"] = "running"
        dns_check_progress["total"] = len(domains)
        dns_check_progress["paused_domains"] = domains

        for i, domain_name in enumerate(domains[start_index:], start=start_index + 1):
            if dns_check_progress["should_stop"]:
                dns_check_progress["status"] = "stopped"
                dns_check_progress["current_domain"] = ""
                print(f"DNS check stopped by user at domain {i}/{len(domains)}")
                return

            if rate_limit_state.get_status()["is_paused"]:
                print(f"DNS check paused due to rate limit at domain {i}/{len(domains)}")
                if _wait_for_rate_limit_resume(rate_limit_state, dns_check_progress, i - 1):
                    return
                print("DNS check resuming after rate limit pause")

            dns_check_progress["processed"] = i
            dns_check_progress["current_domain"] = domain_name

            print(f"Checking DNS {i}/{len(domains)}: {domain_name}")

            max_retries = 3
            for retry in range(max_retries):
                try:
                    thread_db = Database()
                    issues = thread_db.check_dns_records_for_domain(domain_name)

                    if issues is None:
                        print(f"No DNS records in DB for {domain_name}, fetching from API...")
                        dns_records = get_email_manager().api_client._get_all_hosts(domain_name)

                        if dns_records:
                            thread_db.backup_dns_records(domain_name, dns_records)
                            print(f"Stored {len(dns_records)} DNS records for {domain_name}")
                            issues = thread_db.check_dns_records_for_domain(domain_name)
                        else:
                            issues = "No DNS records found"

                    thread_db.update_domain_dns_issues(domain_name, issues)
                    dns_check_progress["successful"] += 1
                    print(f"DNS check for {domain_name}: {issues}")
                    break

                except Exception as e:
                    error_msg = str(e).lower()
                    is_rate_limited = (
                        "too many requests" in error_msg or
                        "rate limit" in error_msg or
                        "429" in error_msg
                    )

                    if is_rate_limited:
                        print(f"Rate limit hit on {domain_name}, pausing for 15 minutes...")
                        rate_limit_state.set_paused(900, f"Rate limit at {domain_name}")
                        if _wait_for_rate_limit_resume(rate_limit_state, dns_check_progress, i - 1):
                            return
                        continue

                    if retry < max_retries - 1:
                        print(f"Retry {retry + 1}/{max_retries} for {domain_name}: {e}")
                        time.sleep(5)
                    else:
                        dns_check_progress["errors"].append(f"{domain_name}: {str(e)}")
                        print(f"Failed DNS check for {domain_name}: {e}")

        dns_check_progress["status"] = "completed"
        dns_check_progress["current_domain"] = ""
        print(f"DNS check completed: {dns_check_progress['successful']} successful, {len(dns_check_progress['errors'])} errors")

    except Exception as e:
        dns_check_progress["status"] = "error"
        dns_check_progress["rate_limit_message"] = str(e)
        print(f"DNS check error: {e}")


@app.route('/api/check-dns-for-selected', methods=['POST'])
def check_dns_for_selected():
    """Start background DNS check for selected domains with rate limiting"""
    global dns_check_progress

    try:
        data = request.json
        domains = data.get('domains', [])

        if not domains:
            return jsonify({"error": "No domains provided"}), 400

        if dns_check_progress["status"] == "running":
            return jsonify({"error": "DNS check already in progress"}), 400

        dns_check_progress = {
            "status": "running",
            "processed": 0,
            "total": len(domains),
            "current_domain": "",
            "successful": 0,
            "errors": [],
            "should_stop": False,
            "paused_at_index": None,
            "rate_limit_message": None,
            "paused_domains": domains,
            "pause_until": None
        }

        thread = threading.Thread(target=background_dns_check, args=(domains,))
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "started",
            "message": f"Started DNS check for {len(domains)} domains",
            "total": len(domains)
        })

    except Exception as e:
        print(f"Error starting DNS check: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/dns-check-progress', methods=['GET'])
def get_dns_check_progress():
    """Get DNS check progress including pause status"""
    from namecheap_client import rate_limit_state

    rate_status = rate_limit_state.get_status()

    return jsonify({
        "status": dns_check_progress["status"],
        "processed": dns_check_progress["processed"],
        "total": dns_check_progress["total"],
        "current_domain": dns_check_progress["current_domain"],
        "successful": dns_check_progress["successful"],
        "errors": dns_check_progress["errors"][-5:] if dns_check_progress["errors"] else [],
        "total_errors": len(dns_check_progress["errors"]) if dns_check_progress["errors"] else 0,
        "rate_limit_message": dns_check_progress.get("rate_limit_message"),
        "paused_at_index": dns_check_progress.get("paused_at_index"),
        "pause_until": dns_check_progress.get("pause_until"),
        "rate_limit_status": rate_status
    })


@app.route('/api/dns-check-stop', methods=['POST'])
def stop_dns_check():
    """Stop the DNS check process"""
    global dns_check_progress

    if dns_check_progress["status"] in ["running", "paused"]:
        dns_check_progress["should_stop"] = True
        return jsonify({"status": "stopping"})

    return jsonify({"status": "not_running"})


@app.route('/api/dns-check-resume', methods=['POST'])
def resume_dns_check():
    """Resume DNS check after rate limit pause"""
    global dns_check_progress
    from namecheap_client import rate_limit_state

    if dns_check_progress["status"] != "paused":
        return jsonify({"error": "DNS check not paused"}), 400

    rate_limit_state.resume()
    dns_check_progress["status"] = "running"
    dns_check_progress["should_stop"] = False
    dns_check_progress["rate_limit_message"] = None

    paused_index = dns_check_progress.get("paused_at_index", 0)
    domains = dns_check_progress.get("paused_domains", [])

    if domains:
        thread = threading.Thread(target=background_dns_check, args=(domains, paused_index))
        thread.daemon = True
        thread.start()

    return jsonify({"status": "resumed", "from_index": paused_index})


@app.route('/api/rate-limit-status', methods=['GET'])
def get_rate_limit_status():
    """Get current rate limit status from Namecheap API client"""
    from namecheap_client import rate_limit_state
    return jsonify(rate_limit_state.get_status())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'

    app.run(debug=debug_mode, host='0.0.0.0', port=port)