import React, { useState, useEffect } from 'react';
import axios from 'axios';

const DNSRecordManager = ({ domains, onClose }) => {
  const [selectedDomains, setSelectedDomains] = useState([]);
  const [recordType, setRecordType] = useState('A');
  const [hostName, setHostName] = useState('@');
  const [recordValue, setRecordValue] = useState('');
  const [ttl, setTtl] = useState('1800');
  const [mxPref, setMxPref] = useState('10');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState({
    status: 'ready',
    processed: 0,
    total: 0,
    current_domain: '',
    errors: [],
    successful: 0
  });

  // DNS Record Types available in Namecheap
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

  // TTL Options (common Namecheap values)
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

  // MX Priority options
  const mxPriorityOptions = [
    { value: '0', label: '0 (Highest)' },
    { value: '5', label: '5' },
    { value: '10', label: '10 (Standard)' },
    { value: '20', label: '20' },
    { value: '30', label: '30' },
    { value: '40', label: '40' },
    { value: '50', label: '50 (Lowest)' }
  ];

  const handleDomainSelection = (domainName, isSelected) => {
    if (isSelected) {
      setSelectedDomains([...selectedDomains, domainName]);
    } else {
      setSelectedDomains(selectedDomains.filter(d => d !== domainName));
    }
  };

  const selectAllDomains = () => {
    setSelectedDomains(domains.map(d => d.domain_name));
  };

  const clearAllDomains = () => {
    setSelectedDomains([]);
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

  const validateRecord = () => {
    if (!hostName.trim()) {
      return 'Host name is required';
    }
    if (!recordValue.trim()) {
      return 'Record value is required';
    }
    if (selectedDomains.length === 0) {
      return 'Please select at least one domain';
    }

    // Type-specific validation
    switch (recordType) {
      case 'A':
        const ipv4Regex = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/;
        if (!ipv4Regex.test(recordValue.trim())) {
          return 'Invalid IPv4 address format';
        }
        break;
      case 'MX':
        if (!mxPref || isNaN(mxPref)) {
          return 'MX Priority is required and must be a number';
        }
        break;
      case 'URL':
      case 'URL301':
      case 'FRAME':
        if (!recordValue.startsWith('http://') && !recordValue.startsWith('https://')) {
          return 'URL must start with http:// or https://';
        }
        break;
    }

    return null;
  };

  const startBulkDNSUpdate = async () => {
    const validationError = validateRecord();
    if (validationError) {
      alert(validationError);
      return;
    }

    setIsProcessing(true);
    setProgress({
      status: 'running',
      processed: 0,
      total: selectedDomains.length,
      current_domain: '',
      errors: [],
      successful: 0
    });

    try {
      const recordData = {
        type: recordType,
        name: hostName.trim(),
        address: recordValue.trim(),
        ttl: ttl,
        mx_pref: recordType === 'MX' ? mxPref : undefined
      };

      await axios.post('/api/bulk-dns-update', {
        domains: selectedDomains,
        record: recordData
      });

      // Start polling for progress
      pollProgress();
    } catch (error) {
      console.error('Error starting bulk DNS update:', error);
      alert('Failed to start bulk DNS update: ' + error.message);
      setIsProcessing(false);
    }
  };

  const pollProgress = () => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get('/api/bulk-dns-progress');
        const data = response.data;

        setProgress(data);

        if (data.status === 'completed' || data.status === 'error' || data.status === 'stopped') {
          clearInterval(interval);
          setIsProcessing(false);
          setTimeout(() => {
            if (data.status === 'completed') {
              alert(`Bulk DNS update completed!\nSuccessful: ${data.successful}\nErrors: ${data.errors.length}`);
            }
          }, 1000);
        }
      } catch (error) {
        console.error('Error fetching progress:', error);
        clearInterval(interval);
        setIsProcessing(false);
      }
    }, 2000);
  };

  const stopBulkUpdate = async () => {
    try {
      await axios.post('/api/stop-bulk-dns');
      setIsProcessing(false);
    } catch (error) {
      console.error('Error stopping bulk update:', error);
    }
  };

  const resumeBulkUpdate = async () => {
    try {
      await axios.post('/api/resume-bulk-dns');
      setIsProcessing(true);
      pollProgress();
    } catch (error) {
      console.error('Error resuming bulk update:', error);
    }
  };

  const getProgressPercentage = () => {
    if (progress.total === 0) return 0;
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
        maxWidth: '1000px',
        maxHeight: '90%',
        overflow: 'auto',
        boxShadow: '0 10px 25px rgba(0,0,0,0.3)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ color: '#1e293b', margin: 0 }}>🌐 Bulk DNS Record Management</h2>
          <button
            onClick={onClose}
            style={{
              background: '#ef4444',
              color: 'white',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            ✕ Close
          </button>
        </div>

        {/* DNS Record Configuration */}
        <div style={{
          backgroundColor: '#f8fafc',
          padding: '1.5rem',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          border: '1px solid #e2e8f0'
        }}>
          <h3 style={{ marginBottom: '1rem', color: '#374151' }}>DNS Record Configuration</h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#374151' }}>
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
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#374151' }}>
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

          <div style={{ display: 'grid', gridTemplateColumns: recordType === 'MX' ? '1fr 1fr 1fr' : '1fr 2fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#374151' }}>
                Host
              </label>
              <input
                type="text"
                value={hostName}
                onChange={(e) => setHostName(e.target.value)}
                placeholder="@ for root domain, www for subdomain"
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
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#374151' }}>
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
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#374151' }}>
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
        </div>

        {/* Domain Selection */}
        <div style={{
          backgroundColor: '#f8fafc',
          padding: '1.5rem',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          border: '1px solid #e2e8f0'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, color: '#374151' }}>
              Select Domains ({selectedDomains.length} of {domains.length})
            </h3>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                onClick={selectAllDomains}
                style={{
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                Select All
              </button>
              <button
                onClick={clearAllDomains}
                style={{
                  background: '#6b7280',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                Clear All
              </button>
            </div>
          </div>

          <div style={{
            maxHeight: '200px',
            overflow: 'auto',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            backgroundColor: 'white'
          }}>
            {domains.map(domain => (
              <label
                key={domain.domain_name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0.75rem',
                  borderBottom: '1px solid #f3f4f6',
                  cursor: 'pointer',
                  backgroundColor: selectedDomains.includes(domain.domain_name) ? '#eff6ff' : 'transparent'
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedDomains.includes(domain.domain_name)}
                  onChange={(e) => handleDomainSelection(domain.domain_name, e.target.checked)}
                  style={{ marginRight: '0.75rem' }}
                />
                <span style={{ fontWeight: '500' }}>{domain.domain_name}</span>
                {domain.client_name && domain.client_name !== 'Unassigned' && (
                  <span style={{
                    marginLeft: 'auto',
                    fontSize: '0.875rem',
                    color: '#6b7280',
                    backgroundColor: '#f3f4f6',
                    padding: '0.25rem 0.5rem',
                    borderRadius: '4px'
                  }}>
                    {domain.client_name}
                  </span>
                )}
              </label>
            ))}
          </div>
        </div>

        {/* Progress Display */}
        {isProcessing && (
          <div style={{
            backgroundColor: progress.status === 'rate_limited' ? '#fef3c7' : '#eff6ff',
            padding: '1.5rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            border: `1px solid ${progress.status === 'rate_limited' ? '#f59e0b' : '#3b82f6'}`
          }}>
            <h4 style={{ margin: '0 0 1rem 0', color: '#374151' }}>
              {progress.status === 'running' ? '🔄 Processing DNS Records...' :
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

            <div style={{ fontSize: '0.875rem', color: '#374151' }}>
              Successful: {progress.successful} | Errors: {progress.errors.length}
            </div>

            {progress.status === 'rate_limited' && (
              <button
                onClick={resumeBulkUpdate}
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
                🔄 Resume Update
              </button>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
          {isProcessing ? (
            <button
              onClick={stopBulkUpdate}
              style={{
                background: '#ef4444',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600'
              }}
            >
              🛑 Stop Update
            </button>
          ) : (
            <button
              onClick={startBulkDNSUpdate}
              disabled={selectedDomains.length === 0}
              style={{
                background: selectedDomains.length === 0 ? '#94a3b8' : '#10b981',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '6px',
                cursor: selectedDomains.length === 0 ? 'not-allowed' : 'pointer',
                fontWeight: '600'
              }}
            >
              🚀 Start Bulk DNS Update ({selectedDomains.length} domains)
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default DNSRecordManager;