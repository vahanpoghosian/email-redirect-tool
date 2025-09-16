import React, { useState, useEffect } from 'react';
import axios from 'axios';
import DomainTable from './components/DomainTable';
import SyncProgress from './components/SyncProgress';
import BulkUpdateModal from './components/BulkUpdateModal';
import ClientManager from './components/ClientManager';

function App() {
  const [domains, setDomains] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncInProgress, setSyncInProgress] = useState(false);
  const [selectedDomains, setSelectedDomains] = useState([]);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [showClientManager, setShowClientManager] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Load initial data
  useEffect(() => {
    loadDomainsAndClients();
    checkSyncStatus();
  }, []);

  const loadDomainsAndClients = async () => {
    try {
      const [domainsRes, clientsRes] = await Promise.all([
        axios.get('/api/domains'),
        axios.get('/api/clients')
      ]);

      if (domainsRes.data.status === 'success') {
        setDomains(domainsRes.data.domains);
      }

      if (clientsRes.data.status === 'success') {
        setClients(clientsRes.data.clients);
      }
    } catch (error) {
      console.error('Error loading data:', error);
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
        // Refresh domains
        await loadDomainsAndClients();
        setSelectedDomains([]);
        setShowBulkModal(false);
        return { success: true };
      } else {
        return { success: false, error: response.data.error };
      }
    } catch (error) {
      console.error('Error with bulk update:', error);
      return { success: false, error: error.message };
    }
  };

  const filteredDomains = domains.filter(domain =>
    domain.domain_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

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
        <div className="logo">🔗 Domain URL Redirections Manager</div>
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
              onClick={loadDomainsAndClients}
            >
              📁 Refresh
            </button>
          </div>

          <div className="flex gap-2 items-center">
            <input
              type="text"
              className="form-control"
              placeholder="Search domains..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '300px' }}
            />
            <button
              className="btn"
              onClick={() => setSearchQuery('')}
            >
              Clear
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
            {searchQuery && ` (filtered by "${searchQuery}")`}
          </p>

          <DomainTable
            domains={filteredDomains}
            clients={clients}
            selectedDomains={selectedDomains}
            onSelectionChange={setSelectedDomains}
            onSaveRedirect={handleSaveRedirect}
            onClientChange={handleClientChange}
          />
        </div>

        {/* Bulk Update Modal */}
        {showBulkModal && (
          <BulkUpdateModal
            selectedDomains={selectedDomains}
            clients={clients}
            onSubmit={handleBulkUpdate}
            onClose={() => setShowBulkModal(false)}
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
      </div>
    </div>
  );
}

export default App;