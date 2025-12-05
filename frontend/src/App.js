import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DomainTable from './components/DomainTable';
import SyncProgress from './components/SyncProgress';
import BulkUpdateModal from './components/BulkUpdateModal';
import ClientManager from './components/ClientManager';
import DNSModal from './components/DNSModal';

function App() {
  const [domains, setDomains] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncInProgress, setSyncInProgress] = useState(false);
  const [selectedDomains, setSelectedDomains] = useState([]);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showClientManager, setShowClientManager] = useState(false);
  const [showDNSModal, setShowDNSModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [clientFilter, setClientFilter] = useState('');
  const [bulkUpdateResults, setBulkUpdateResults] = useState({});
  const [dnsCheckInProgress, setDnsCheckInProgress] = useState(false);
  const [dnsCheckProgress, setDnsCheckProgress] = useState('');
  const [dnsIssueFilter, setDnsIssueFilter] = useState('');

  // Load initial data
  useEffect(() => {
    loadDomainsAndClients();
    checkSyncStatus();
  }, []);

  const loadDomainsAndClients = async () => {
    try {
      const [domainsRes, clientsRes] = await Promise.all([
        axios.get('/api/domains-from-db'),
        axios.get('/api/clients')
      ]);

      if (domainsRes.data.status === 'success') {
        setDomains(domainsRes.data.domains || []);
      }

      if (clientsRes.data.status === 'success') {
        setClients(clientsRes.data.clients || []);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      setDomains([]);
    } finally {
      setLoading(false);
    }
  };

  const checkSyncStatus = async () => {
    try {
      const response = await axios.get('/api/sync-domains-progress');
      if (response.data.status === 'running') {
        setSyncInProgress(true);
      }
    } catch (error) {
      // No active sync
    }
  };

  const startSync = async () => {
    try {
      setSyncInProgress(true);
      await axios.post('/sync-domains');
    } catch (error) {
      console.error('Error starting sync:', error);
      setSyncInProgress(false);
    }
  };

  const stopSync = async () => {
    try {
      await axios.post('/api/stop-sync');
    } catch (error) {
      console.error('Error stopping sync:', error);
    }
  };

  const syncSelectedDomains = async () => {
    try {
      if (selectedDomains.length === 0) {
        alert('Please select domains to sync');
        return;
      }
      setSyncInProgress(true);
      await axios.post('/api/sync-selected-domains', { domains: selectedDomains });
    } catch (error) {
      console.error('Error syncing selected domains:', error);
      if (error.response?.data?.error === 'Sync already in progress') {
        alert('A sync is already in progress. Please wait for it to complete or stop it first.');
      } else {
        alert('Error syncing selected domains: ' + (error.response?.data?.error || error.message));
      }
      setSyncInProgress(false);
    }
  };

  const backupDatabase = async () => {
    try {
      const response = await axios.post('/api/backup-database');
      if (response.data.status === 'success') {
        // Store backup data in localStorage as a simple solution
        const backupData = {
          timestamp: new Date().toISOString(),
          domains: domains,
          clients: clients
        };
        localStorage.setItem('db_backup', JSON.stringify(backupData));
        alert(`Database backed up locally! Domains: ${response.data.domains_count}, Clients: ${response.data.clients_count}`);
      }
    } catch (error) {
      console.error('Error backing up database:', error);
      alert('Error creating backup: ' + (error.response?.data?.message || error.message));
    }
  };

  const restoreDatabase = async () => {
    try {
      const backupData = localStorage.getItem('db_backup');
      if (!backupData) {
        alert('No backup found in local storage');
        return;
      }

      if (!window.confirm('This will restore the database from your local backup. Continue?')) {
        return;
      }

      const response = await axios.post('/api/restore-database', {
        backup_data: JSON.parse(backupData)
      });

      if (response.data.status === 'success') {
        alert(`Database restored! Domains: ${response.data.restored_domains}, Clients: ${response.data.restored_clients}`);
        // Reload the page to show restored data
        window.location.reload();
      }
    } catch (error) {
      console.error('Error restoring database:', error);
      alert('Error restoring backup: ' + (error.response?.data?.message || error.message));
    }
  };

  const handleSaveRedirect = async (domainName, redirectUrl) => {
    try {
      const response = await axios.post('/update-redirect', {
        domain: domainName,
        target: redirectUrl
      });

      if (response.data.status === 'success') {
        // Update domain in state
        setDomains(domains.map(domain =>
          domain.domain_name === domainName
            ? { ...domain, redirections: [{ name: '@', target: redirectUrl, type: 'URL' }] }
            : domain
        ));
        return { success: true, verified: response.data.verified };
      } else {
        return { success: false, error: response.data.error };
      }
    } catch (error) {
      console.error('Error saving redirect:', error);
      return { success: false, error: error.message };
    }
  };

  const handleClientChange = async (domainName, clientId) => {
    try {
      if (clientId) {
        await axios.post('/api/assign-client', {
          domain_name: domainName,
          client_id: clientId
        });

        // Find client and get URL
        const client = clients.find(c => c.id === parseInt(clientId));
        if (client && client.url) {
          // Update domain in state
          setDomains(domains.map(domain =>
            domain.domain_name === domainName
              ? { ...domain, client_id: parseInt(clientId), client_name: client.name }
              : domain
          ));
          return client.url;
        }
      }
      return null;
    } catch (error) {
      console.error('Error updating client:', error);
      return null;
    }
  };

  const handleBulkUpdate = async (updateData) => {
    try {
      const updates = selectedDomains.map(domainName => ({
        domain_name: domainName,
        name: '@',
        target: updateData.target
      }));

      const response = await axios.post('/api/bulk-update', { updates });

      if (response.data.status === 'success') {
        // Store bulk update results for status display
        const resultsMap = {};
        response.data.results.forEach(result => {
          resultsMap[result.domain_name] = {
            success: result.success,
            verified: result.verified,
            timestamp: Date.now()
          };
        });
        setBulkUpdateResults(resultsMap);

        // Clear results after 10 seconds
        setTimeout(() => setBulkUpdateResults({}), 10000);

        // Refresh domains
        await loadDomainsAndClients();
        setSelectedDomains([]);
        setShowBulkModal(false);
        return { success: true, results: response.data.results };
      } else {
        return { success: false, error: response.data.error };
      }
    } catch (error) {
      console.error('Error with bulk update:', error);

      // Handle axios error responses with better formatting
      let errorMessage = 'Unknown error occurred';
      if (error.response) {
        // Server responded with error status
        if (error.response.data && error.response.data.error) {
          errorMessage = error.response.data.error;
        } else if (error.response.data && typeof error.response.data === 'string') {
          errorMessage = error.response.data;
        } else {
          errorMessage = `Server error: ${error.response.status}`;
        }
      } else if (error.request) {
        // Request was made but no response received
        errorMessage = 'Network error - no response from server';
      } else {
        // Something else happened
        errorMessage = error.message;
      }

      // Truncate very long error messages (like base64 strings)
      if (errorMessage.length > 200) {
        errorMessage = errorMessage.substring(0, 200) + '... (error truncated)';
      }

      return { success: false, error: errorMessage };
    }
  };

  const checkDnsForSelected = async () => {
    try {
      if (selectedDomains.length === 0) {
        alert('Please select domains to check DNS records');
        return;
      }

      setDnsCheckInProgress(true);

      // If more than 40 domains, send in batches of 40 with 15-second interval
      if (selectedDomains.length > 40) {
        const batchSize = 40;
        const totalBatches = Math.ceil(selectedDomains.length / batchSize);
        let successfulBatches = 0;
        let failedBatches = 0;

        for (let i = 0; i < selectedDomains.length; i += batchSize) {
          const batch = selectedDomains.slice(i, i + batchSize);
          const batchNumber = Math.floor(i / batchSize) + 1;

          setDnsCheckProgress(`Processing batch ${batchNumber}/${totalBatches} (${batch.length} domains)...`);

          try {
            const response = await axios.post('/api/check-dns-for-selected', {
              domains: batch
            });

            if (response.data.status === 'success') {
              successfulBatches++;
              console.log(`Batch ${batchNumber}/${totalBatches} completed successfully`);
            } else {
              failedBatches++;
              console.error(`Batch ${batchNumber}/${totalBatches} failed:`, response.data.error);
            }
          } catch (error) {
            failedBatches++;
            console.error(`Error in batch ${batchNumber}/${totalBatches}:`, error);
          }

          // Wait 15 seconds before next batch (except for the last batch)
          if (i + batchSize < selectedDomains.length) {
            setDnsCheckProgress(`Waiting 15 seconds before next batch...`);
            await new Promise(resolve => setTimeout(resolve, 15000));
          }
        }

        setDnsCheckProgress('');
        alert(`DNS check completed!\nTotal domains: ${selectedDomains.length}\nBatches processed: ${successfulBatches}/${totalBatches}\nFailed batches: ${failedBatches}`);
      } else {
        // For 40 or fewer domains, send all at once
        const response = await axios.post('/api/check-dns-for-selected', {
          domains: selectedDomains
        });

        if (response.data.status === 'success') {
          alert(`DNS check completed for ${selectedDomains.length} domains`);
        } else {
          alert('Error checking DNS records: ' + (response.data.error || 'Unknown error'));
        }
      }

      // Refresh domains to show updated DNS status
      await loadDomainsAndClients();
      setSelectedDomains([]);
    } catch (error) {
      console.error('Error checking DNS records:', error);
      alert('Error checking DNS records: ' + (error.response?.data?.error || error.message));
    } finally {
      setDnsCheckInProgress(false);
      setDnsCheckProgress('');
    }
  };

  const dnsIssueOptions = React.useMemo(() => {
    const issues = new Set();
    domains.forEach(d => {
      if (d.dns_issues) issues.add(d.dns_issues);
    });
    return Array.from(issues).sort();
  }, [domains]);

  const filteredDomains = domains.filter(domain => {
    const matchesSearch = domain.domain_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesClient = !clientFilter || domain.client_id === parseInt(clientFilter);
    const matchesDnsIssue = !dnsIssueFilter || domain.dns_issues === dnsIssueFilter;
    return matchesSearch && matchesClient && matchesDnsIssue;
  });

  const exportToCsv = () => {
    const headers = ['#', 'Domain', 'Redirect URL', 'Client', 'DNS Issues', 'Status'];
    const rows = filteredDomains.map(d => [
      d.domain_number || '',
      d.domain_name,
      d.redirect_url || '',
      d.client_name || 'Unassigned',
      d.dns_issues || 'Not Checked',
      d.status || ''
    ]);
    const csvContent = [headers, ...rows].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `domains_export_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };


  if (loading) {
    return (
      <div className="container">
        <div className="card text-center">
          <h2>Loading...</h2>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="header">
        <div className="logo">🔗 Domain URL Redirections Manager v2.1</div>
      </div>

      <div className="container">
        {/* Welcome Card */}
        <div className="card">
          <h1>Domain URL Redirection Management</h1>
          <p>Manage domain redirections for all your domains using Namecheap API with real-time sync and verification.</p>
        </div>

        {/* Controls */}
        <div className="card">
          <h2>Domain Management</h2>

          <div className="flex gap-2 items-center mb-4" style={{ flexWrap: 'wrap' }}>
            <button
              className="btn btn-success"
              onClick={startSync}
              disabled={syncInProgress}
            >
              {syncInProgress ? '🔄 Syncing...' : '🔄 Sync All Domains from Namecheap'}
            </button>

            {syncInProgress && (
              <button
                className="btn"
                onClick={stopSync}
                style={{ backgroundColor: '#ef4444' }}
              >
                ⏹ Stop Sync
              </button>
            )}

            <button
              className="btn"
              onClick={syncSelectedDomains}
              disabled={selectedDomains.length === 0 || syncInProgress}
            >
              🔄 Sync Selected ({selectedDomains.length})
            </button>

            <button
              className="btn"
              onClick={() => setShowBulkModal(true)}
              disabled={selectedDomains.length === 0}
            >
              🔧 Bulk Update ({selectedDomains.length})
            </button>

            <button
              className="btn"
              onClick={() => setShowClientManager(true)}
            >
              👥 Manage Clients
            </button>

            <button
              className="btn"
              onClick={checkDnsForSelected}
              disabled={selectedDomains.length === 0 || dnsCheckInProgress}
            >
              {dnsCheckInProgress
                ? (dnsCheckProgress ? `🔍 ${dnsCheckProgress}` : '🔍 Checking...')
                : `🔍 Check DNS (${selectedDomains.length})`}
            </button>

            <button
              className="btn"
              onClick={() => {
                if (selectedDomains.length === 0) {
                  alert('Please select at least one domain first');
                  return;
                }
                setShowDNSModal(true);
              }}
              disabled={selectedDomains.length === 0}
              style={{
                background: selectedDomains.length === 0 ? '#94a3b8' : '#8b5cf6',
                color: 'white',
                cursor: selectedDomains.length === 0 ? 'not-allowed' : 'pointer',
                border: '2px solid #7c3aed',
                fontWeight: 'bold'
              }}
            >
              🌐 DNS Records ({selectedDomains.length})
            </button>

            <button
              className="btn"
              onClick={loadDomainsAndClients}
            >
              📁 Refresh
            </button>

            <button
              className="btn"
              onClick={exportToCsv}
              style={{ backgroundColor: '#059669' }}
            >
              📥 Export CSV
            </button>

            <button
              className="btn"
              onClick={backupDatabase}
              style={{ backgroundColor: '#6366f1' }}
            >
              💾 Backup DB
            </button>

            <button
              className="btn"
              onClick={restoreDatabase}
              style={{ backgroundColor: '#8b5cf6' }}
            >
              🔄 Restore DB
            </button>
          </div>

          <div className="flex gap-2 items-center" style={{ flexWrap: 'wrap' }}>
            <input
              type="text"
              className="form-control"
              placeholder="Search domains..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '300px' }}
            />
            <select
              className="form-control"
              value={clientFilter}
              onChange={(e) => setClientFilter(e.target.value)}
              style={{ width: '200px' }}
            >
              <option value="">All Clients</option>
              {clients.map(client => (
                <option key={client.id} value={client.id}>
                  {client.name}
                </option>
              ))}
            </select>
            <select
              className="form-control"
              value={dnsIssueFilter}
              onChange={(e) => setDnsIssueFilter(e.target.value)}
              style={{ width: '200px' }}
            >
              <option value="">All DNS Issues</option>
              {dnsIssueOptions.map(issue => (
                <option key={issue} value={issue}>
                  {issue === 'ok' ? '✅ OK' : issue}
                </option>
              ))}
            </select>
            <button
              className="btn"
              onClick={() => {
                setSearchQuery('');
                setClientFilter('');
                setDnsIssueFilter('');
              }}
            >
              Clear All
            </button>
          </div>
        </div>

        {/* Sync Progress */}
        {syncInProgress && (
          <SyncProgress
            onComplete={() => {
              setSyncInProgress(false);
              loadDomainsAndClients();
            }}
          />
        )}

        {/* Domain Table */}
        <div className="card">
          <h2>All Domains with URL Redirections</h2>
          <p style={{ color: '#6b7280', marginBottom: '1rem' }}>
            Found {filteredDomains.length} domains
            {(searchQuery || clientFilter) && ` (filtered${searchQuery ? ` by "${searchQuery}"` : ''}${clientFilter ? ` by client` : ''})`}
          </p>

          <DomainTable
            domains={filteredDomains}
            clients={clients}
            selectedDomains={selectedDomains}
            onSelectionChange={setSelectedDomains}
            onSaveRedirect={handleSaveRedirect}
            onClientChange={handleClientChange}
            bulkUpdateResults={bulkUpdateResults}
          />
        </div>

        {/* Bulk Update Modal with DNS Management */}
        {showBulkModal && (
          <BulkUpdateModal
            selectedDomains={selectedDomains}
            clients={clients}
            onClose={() => {
              setShowBulkModal(false);
              loadDomainsAndClients();
            }}
          />
        )}

        {/* Client Manager Modal */}
        {showClientManager && (
          <ClientManager
            clients={clients}
            onClose={() => {
              setShowClientManager(false);
              loadDomainsAndClients();
            }}
          />
        )}

        {/* DNS Management Modal */}
        {showDNSModal && (
          <DNSModal
            selectedDomains={selectedDomains}
            onClose={() => {
              setShowDNSModal(false);
              loadDomainsAndClients();
            }}
          />
        )}
      </div>
    </div>
  );
}

export default App;