import React, { useState } from 'react';
import axios from 'axios';

const BulkUpdateModal = ({ selectedDomains, clients, onClose }) => {
  const [activeTab, setActiveTab] = useState('redirect'); // 'redirect', 'dns-add', 'dns-remove'

  // Redirect state
  const [updateType, setUpdateType] = useState('manual');
  const [manualUrl, setManualUrl] = useState('');
  const [selectedClient, setSelectedClient] = useState('');

  // DNS Add state
  const [recordType, setRecordType] = useState('A');
  const [hostName, setHostName] = useState('@');
  const [recordValue, setRecordValue] = useState('');
  const [ttl, setTtl] = useState('1800');
  const [mxPref, setMxPref] = useState('10');

  // DNS Remove state
  const [removeRecordType, setRemoveRecordType] = useState('');
  const [removeHostName, setRemoveHostName] = useState('');
  const [removeRecordValue, setRemoveRecordValue] = useState('');

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(null);

  const recordTypes = [
    { value: 'A', label: 'A Record - IPv4 Address' },
    { value: 'AAAA', label: 'AAAA Record - IPv6 Address' },
    { value: 'CNAME', label: 'CNAME Record - Canonical Name' },
    { value: 'MX', label: 'MX Record - Mail Exchange' },
    { value: 'TXT', label: 'TXT Record - Text' },
    { value: 'NS', label: 'NS Record - Name Server' },
    { value: 'SRV', label: 'SRV Record - Service' },
    { value: 'URL', label: 'URL Redirect' },
    { value: 'URL301', label: 'URL Redirect (301 Permanent)' },
    { value: 'FRAME', label: 'URL Frame' }
  ];

  const ttlOptions = [
    { value: '60', label: '1 min' },
    { value: '300', label: '5 min' },
    { value: '600', label: '10 min' },
    { value: '1800', label: '30 min' },
    { value: '3600', label: '1 hour' },
    { value: '7200', label: '2 hours' },
    { value: '14400', label: '4 hours' },
    { value: '28800', label: '8 hours' },
    { value: '43200', label: '12 hours' },
    { value: '86400', label: '24 hours' }
  ];

  const mxPriorityOptions = [
    { value: '0', label: '0 (Highest)' },
    { value: '5', label: '5' },
    { value: '10', label: '10 (Standard)' },
    { value: '20', label: '20' },
    { value: '30', label: '30' },
    { value: '40', label: '40' },
    { value: '50', label: '50 (Lowest)' }
  ];

  const handleClientChange = (clientId) => {
    setSelectedClient(clientId);
    const client = clients.find(c => c.id === parseInt(clientId));
    if (client && client.url) {
      setManualUrl(client.url);
    }
  };

  const getRecordLabel = () => {
    switch (recordType) {
      case 'A':
      case 'AAAA':
        return 'IP Address';
      case 'CNAME':
        return 'Target Domain';
      case 'MX':
        return 'Mail Server';
      case 'TXT':
        return 'Text Value';
      case 'NS':
        return 'Name Server';
      case 'SRV':
        return 'Target (priority weight port target)';
      case 'URL':
      case 'URL301':
        return 'Redirect URL';
      case 'FRAME':
        return 'Frame URL';
      default:
        return 'Record Value';
    }
  };

  const getRecordPlaceholder = () => {
    switch (recordType) {
      case 'A':
        return '192.168.1.1';
      case 'AAAA':
        return '2001:0db8:85a3:0000:0000:8a2e:0370:7334';
      case 'CNAME':
        return 'example.com';
      case 'MX':
        return 'mail.example.com';
      case 'TXT':
        return 'v=spf1 include:_spf.google.com ~all';
      case 'NS':
        return 'ns1.example.com';
      case 'SRV':
        return '10 5 443 target.example.com';
      case 'URL':
      case 'URL301':
        return 'https://example.com';
      case 'FRAME':
        return 'https://example.com';
      default:
        return 'Enter record value';
    }
  };

  const pollProgress = (progressType) => {
    const endpoint = progressType === 'redirect' ? '/api/bulk-update-progress' :
                     progressType === 'dns' ? '/api/bulk-dns-progress' :
                     '/api/bulk-dns-remove-progress';

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(endpoint);
        const data = response.data;

        setProgress(data);

        if (data.status === 'completed' || data.status === 'error' || data.status === 'stopped') {
          clearInterval(interval);
          setIsProcessing(false);

          if (data.status === 'completed') {
            setTimeout(() => {
              alert(`Operation completed!\nSuccessful: ${data.successful || data.processed}\nErrors: ${data.errors?.length || 0}`);
              onClose();
              window.location.reload();
            }, 1000);
          }
        }
      } catch (error) {
        console.error('Error fetching progress:', error);
        clearInterval(interval);
        setIsProcessing(false);
      }
    }, 2000);
  };

  const handleRedirectSubmit = async () => {
    let targetUrl = '';
    if (updateType === 'manual') {
      targetUrl = manualUrl.trim();
      if (!targetUrl) {
        alert('Please enter a redirect URL');
        return;
      }
    } else if (updateType === 'client') {
      const client = clients.find(c => c.id === parseInt(selectedClient));
      if (!client || !client.url) {
        alert('Please select a client with a URL');
        return;
      }
      targetUrl = client.url;
    }

    setIsProcessing(true);
    setProgress({ status: 'starting', processed: 0, total: selectedDomains.length });

    try {
      const updates = selectedDomains.map(domain => ({
        domain_name: domain,
        name: '@',
        target: targetUrl
      }));

      await axios.post('/api/bulk-update', { updates });
      pollProgress('redirect');
    } catch (error) {
      console.error('Error starting bulk redirect update:', error);
      alert('Failed to start bulk update: ' + error.message);
      setIsProcessing(false);
    }
  };

  const handleDNSAddSubmit = async () => {
    if (!recordValue.trim()) {
      alert('DNS record value is required');
      return;
    }

    // Validate input based on record type
    if (recordType === 'A') {
      const ipv4Regex = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/;
      if (!ipv4Regex.test(recordValue.trim())) {
        alert('Invalid IPv4 address format');
        return;
      }
    }

    if (recordType === 'MX' && !mxPref) {
      alert('MX Priority is required');
      return;
    }

    if ((recordType === 'URL' || recordType === 'URL301' || recordType === 'FRAME') &&
        !recordValue.startsWith('http://') && !recordValue.startsWith('https://')) {
      alert('URL must start with http:// or https://');
      return;
    }

    setIsProcessing(true);
    setProgress({ status: 'starting', processed: 0, total: selectedDomains.length });

    try {
      const recordData = {
        type: recordType,
        name: hostName.trim() || '@',
        address: recordValue.trim(),
        ttl: ttl,
        mx_pref: recordType === 'MX' ? mxPref : undefined
      };

      await axios.post('/api/bulk-dns-update', {
        domains: selectedDomains,
        record: recordData
      });

      pollProgress('dns');
    } catch (error) {
      console.error('Error starting bulk DNS add:', error);
      alert('Failed to start DNS update: ' + error.message);
      setIsProcessing(false);
    }
  };

  const handleDNSRemoveSubmit = async () => {
    if (!removeRecordType) {
      alert('Please select a record type to remove');
      return;
    }

    if (!removeHostName.trim()) {
      alert('Please enter the host name to remove');
      return;
    }

    const confirmRemove = window.confirm(
      `Are you sure you want to remove ${removeRecordType} records with host "${removeHostName}" from ${selectedDomains.length} domains?\n\n` +
      `This will remove ALL ${removeRecordType} records matching the host name${removeRecordValue ? ' and value' : ''}.`
    );

    if (!confirmRemove) return;

    setIsProcessing(true);
    setProgress({ status: 'starting', processed: 0, total: selectedDomains.length });

    try {
      await axios.post('/api/bulk-dns-remove', {
        domains: selectedDomains,
        record_type: removeRecordType,
        host_name: removeHostName.trim(),
        record_value: removeRecordValue.trim() || undefined
      });

      pollProgress('dns-remove');
    } catch (error) {
      console.error('Error starting bulk DNS remove:', error);
      alert('Failed to start DNS removal: ' + error.message);
      setIsProcessing(false);
    }
  };

  const resumeOperation = async () => {
    try {
      const endpoint = activeTab === 'redirect' ? '/api/resume-bulk-update' :
                       activeTab === 'dns-add' ? '/api/resume-bulk-dns' :
                       '/api/resume-bulk-dns-remove';

      await axios.post(endpoint);
      setIsProcessing(true);
      pollProgress(activeTab === 'redirect' ? 'redirect' : activeTab === 'dns-add' ? 'dns' : 'dns-remove');
    } catch (error) {
      alert('Failed to resume: ' + error.message);
    }
  };

  const stopOperation = async () => {
    try {
      const endpoint = activeTab === 'redirect' ? '/api/stop-bulk-update' :
                       activeTab === 'dns-add' ? '/api/stop-bulk-dns' :
                       '/api/stop-bulk-dns-remove';

      await axios.post(endpoint);
      setIsProcessing(false);
    } catch (error) {
      console.error('Error stopping operation:', error);
    }
  };

  const getProgressPercentage = () => {
    if (!progress || progress.total === 0) return 0;
    return Math.round((progress.processed / progress.total) * 100);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '2rem',
        borderRadius: '12px',
        width: '90%',
        maxWidth: '900px',
        maxHeight: '90vh',
        overflow: 'auto',
        boxShadow: '0 10px 25px rgba(0,0,0,0.3)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ color: '#1e293b', margin: 0 }}>
            🔧 Bulk Update ({selectedDomains.length} domains) v2.0
          </h2>
          <button
            onClick={onClose}
            disabled={isProcessing}
            style={{
              background: '#ef4444',
              color: 'white',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              cursor: isProcessing ? 'not-allowed' : 'pointer',
              fontWeight: '600'
            }}
          >
            ✕ Close
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          marginBottom: '1.5rem',
          borderBottom: '2px solid #e5e7eb',
          paddingBottom: '0'
        }}>
          <button
            onClick={() => setActiveTab('redirect')}
            style={{
              background: activeTab === 'redirect' ? '#3b82f6' : 'transparent',
              color: activeTab === 'redirect' ? 'white' : '#6b7280',
              border: 'none',
              padding: '0.75rem 1.5rem',
              borderRadius: '6px 6px 0 0',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '1rem'
            }}
          >
            ↗️ URL Redirects
          </button>
          <button
            onClick={() => setActiveTab('dns-add')}
            style={{
              background: activeTab === 'dns-add' ? '#10b981' : 'transparent',
              color: activeTab === 'dns-add' ? 'white' : '#6b7280',
              border: 'none',
              padding: '0.75rem 1.5rem',
              borderRadius: '6px 6px 0 0',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '1rem'
            }}
          >
            ➕ Add DNS Records
          </button>
          <button
            onClick={() => setActiveTab('dns-remove')}
            style={{
              background: activeTab === 'dns-remove' ? '#ef4444' : 'transparent',
              color: activeTab === 'dns-remove' ? 'white' : '#6b7280',
              border: 'none',
              padding: '0.75rem 1.5rem',
              borderRadius: '6px 6px 0 0',
              cursor: 'pointer',
              fontWeight: '600',
              fontSize: '1rem'
            }}
          >
            🗑️ Remove DNS Records
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'redirect' && !isProcessing && (
          <div>
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                Update Type:
              </label>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="radio"
                    value="manual"
                    checked={updateType === 'manual'}
                    onChange={(e) => setUpdateType(e.target.value)}
                  />
                  Manual URL
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="radio"
                    value="client"
                    checked={updateType === 'client'}
                    onChange={(e) => setUpdateType(e.target.value)}
                  />
                  Client URL
                </label>
              </div>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                Redirect URL:
              </label>
              <input
                type="url"
                value={manualUrl}
                onChange={(e) => setManualUrl(e.target.value)}
                placeholder="https://redirect-url.com"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>

            {updateType === 'client' && (
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                  Select Client:
                </label>
                <select
                  value={selectedClient}
                  onChange={(e) => handleClientChange(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '1rem'
                  }}
                >
                  <option value="">Choose a client...</option>
                  {clients.filter(c => c.url).map(client => (
                    <option key={client.id} value={client.id}>
                      {client.name} ({client.url})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={handleRedirectSubmit}
              style={{
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                width: '100%'
              }}
            >
              🚀 Update Redirects for {selectedDomains.length} Domains
            </button>
          </div>
        )}

        {activeTab === 'dns-add' && !isProcessing && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                  Record Type
                </label>
                <select
                  value={recordType}
                  onChange={(e) => setRecordType(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '1rem'
                  }}
                >
                  {recordTypes.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                  TTL (Time To Live)
                </label>
                <select
                  value={ttl}
                  onChange={(e) => setTtl(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '1rem'
                  }}
                >
                  {ttlOptions.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: recordType === 'MX' ? '1fr 1fr 2fr' : '1fr 3fr', gap: '1rem', marginBottom: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                  Host
                </label>
                <input
                  type="text"
                  value={hostName}
                  onChange={(e) => setHostName(e.target.value)}
                  placeholder="@ for root"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '1rem'
                  }}
                />
              </div>

              {recordType === 'MX' && (
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                    Priority
                  </label>
                  <select
                    value={mxPref}
                    onChange={(e) => setMxPref(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.75rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '6px',
                      fontSize: '1rem'
                    }}
                  >
                    {mxPriorityOptions.map(option => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                  {getRecordLabel()}
                </label>
                <input
                  type="text"
                  value={recordValue}
                  onChange={(e) => setRecordValue(e.target.value)}
                  placeholder={getRecordPlaceholder()}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '1rem'
                  }}
                />
              </div>
            </div>

            <button
              onClick={handleDNSAddSubmit}
              style={{
                background: '#10b981',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                width: '100%'
              }}
            >
              ➕ Add DNS Record to {selectedDomains.length} Domains
            </button>
          </div>
        )}

        {activeTab === 'dns-remove' && !isProcessing && (
          <div>
            <div style={{
              backgroundColor: '#fef2f2',
              padding: '1rem',
              borderRadius: '6px',
              marginBottom: '1.5rem',
              border: '1px solid #fecaca'
            }}>
              <p style={{ color: '#dc2626', fontWeight: '600', marginBottom: '0.5rem' }}>
                ⚠️ Warning: DNS Record Removal
              </p>
              <p style={{ color: '#7f1d1d', fontSize: '0.875rem' }}>
                This will permanently remove DNS records from selected domains.
                Make sure to backup your DNS settings before proceeding.
              </p>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                Record Type to Remove
              </label>
              <select
                value={removeRecordType}
                onChange={(e) => setRemoveRecordType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              >
                <option value="">Select record type...</option>
                {recordTypes.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                Host Name to Remove
              </label>
              <input
                type="text"
                value={removeHostName}
                onChange={(e) => setRemoveHostName(e.target.value)}
                placeholder="@ for root domain, www for subdomain, * for all"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600' }}>
                Specific Value (Optional - leave empty to remove all matching host/type)
              </label>
              <input
                type="text"
                value={removeRecordValue}
                onChange={(e) => setRemoveRecordValue(e.target.value)}
                placeholder="Leave empty to remove all records matching host and type"
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '1rem'
                }}
              />
            </div>

            <button
              onClick={handleDNSRemoveSubmit}
              style={{
                background: '#ef4444',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                width: '100%'
              }}
            >
              🗑️ Remove DNS Records from {selectedDomains.length} Domains
            </button>
          </div>
        )}

        {/* Progress Display */}
        {isProcessing && progress && (
          <div style={{
            backgroundColor: progress.status === 'rate_limited' ? '#fef3c7' : '#eff6ff',
            padding: '1.5rem',
            borderRadius: '8px',
            border: `1px solid ${progress.status === 'rate_limited' ? '#f59e0b' : '#3b82f6'}`
          }}>
            <h4 style={{ margin: '0 0 1rem 0', color: '#374151' }}>
              {progress.status === 'running' ? '🔄 Processing...' :
               progress.status === 'rate_limited' ? '⚠️ Rate Limited - Paused' :
               progress.status === 'completed' ? '✅ Completed' : 'Processing...'}
            </h4>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                {progress.processed} of {progress.total} domains processed
                {progress.current_domain && ` (Current: ${progress.current_domain})`}
              </div>
              <div style={{
                width: '100%',
                backgroundColor: '#e5e7eb',
                borderRadius: '4px',
                height: '8px'
              }}>
                <div
                  style={{
                    width: `${getProgressPercentage()}%`,
                    backgroundColor: progress.status === 'rate_limited' ? '#f59e0b' : '#3b82f6',
                    height: '100%',
                    borderRadius: '4px',
                    transition: 'width 0.3s ease'
                  }}
                />
              </div>
            </div>

            {progress.successful !== undefined && (
              <div style={{ fontSize: '0.875rem', color: '#374151' }}>
                Successful: {progress.successful} | Errors: {progress.errors?.length || 0}
              </div>
            )}

            {progress.status === 'rate_limited' ? (
              <button
                onClick={resumeOperation}
                style={{
                  background: '#10b981',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  marginTop: '1rem'
                }}
              >
                🔄 Resume Operation
              </button>
            ) : (
              <button
                onClick={stopOperation}
                style={{
                  background: '#ef4444',
                  color: 'white',
                  border: 'none',
                  padding: '0.75rem 1.5rem',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '600',
                  marginTop: '1rem'
                }}
              >
                🛑 Stop Operation
              </button>
            )}
          </div>
        )}

        {/* Selected Domains Preview */}
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          backgroundColor: '#f9fafb',
          borderRadius: '6px',
          border: '1px solid #e5e7eb'
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '0.5rem'
          }}>
            <label style={{ fontWeight: '600', color: '#374151' }}>
              Selected Domains ({selectedDomains.length})
            </label>
            <button
              onClick={() => {
                const domainList = selectedDomains.join('\n');
                navigator.clipboard.writeText(domainList);
                alert('Domain list copied to clipboard!');
              }}
              style={{
                background: '#6b7280',
                color: 'white',
                border: 'none',
                padding: '0.25rem 0.75rem',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              📋 Copy List
            </button>
          </div>
          <div style={{
            maxHeight: '100px',
            overflowY: 'auto',
            fontSize: '0.875rem',
            color: '#6b7280'
          }}>
            {selectedDomains.slice(0, 10).map((domain, index) => (
              <div key={domain} style={{ marginBottom: '0.25rem' }}>
                {index + 1}. {domain}
              </div>
            ))}
            {selectedDomains.length > 10 && (
              <div style={{ fontStyle: 'italic', marginTop: '0.5rem' }}>
                ...and {selectedDomains.length - 10} more domains
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BulkUpdateModal;