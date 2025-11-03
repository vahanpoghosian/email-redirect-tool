import React, { useState, useEffect } from 'react';
import axios from 'axios';

const DNSModal = ({ selectedDomains, onClose }) => {
  const [activeTab, setActiveTab] = useState('dns-add');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // DNS Add fields
  const [dnsRecords, setDnsRecords] = useState([{
    type: 'A',
    name: '@',
    address: '',
    ttl: 'Automatic'
  }]);

  // DNS Remove fields
  const [removeRecordType, setRemoveRecordType] = useState('A');
  const [removeRecordName, setRemoveRecordName] = useState('@');

  // Progress tracking
  const [progress, setProgress] = useState(null);
  const [isOperationActive, setIsOperationActive] = useState(false);

  const recordTypes = [
    'A', 'AAAA', 'ALIAS', 'CAA', 'CNAME', 'MX', 'MXE', 'NS', 'SRV', 'TXT', 'URL'
  ];

  const ttlOptions = [
    { value: 'Automatic', label: 'Automatic' },
    { value: '60', label: '1 min' },
    { value: '300', label: '5 min' },
    { value: '1800', label: '30 min (default)' },
    { value: '3600', label: '1 hour' },
    { value: '7200', label: '2 hours' },
    { value: '14400', label: '4 hours' },
    { value: '28800', label: '8 hours' },
    { value: '86400', label: '1 day' }
  ];

  useEffect(() => {
    let interval;
    if (isOperationActive) {
      interval = setInterval(checkProgress, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isOperationActive]);

  const checkProgress = async () => {
    try {
      const endpoint = activeTab === 'dns-add' ? '/api/bulk-dns-progress' : '/api/bulk-dns-remove-progress';
      const response = await axios.get(endpoint);
      const data = response.data;

      setProgress(data);

      if (data.status === 'completed' || data.status === 'stopped') {
        setIsOperationActive(false);
        setIsSubmitting(false);
        setTimeout(() => setProgress(null), 5000);
      }
    } catch (error) {
      console.error('Error checking progress:', error);
    }
  };

  const addDnsRecord = () => {
    setDnsRecords([...dnsRecords, {
      type: 'A',
      name: '@',
      address: '',
      ttl: 'Automatic'
    }]);
  };

  const removeDnsRecord = (index) => {
    if (dnsRecords.length > 1) {
      setDnsRecords(dnsRecords.filter((_, i) => i !== index));
    }
  };

  const updateDnsRecord = (index, field, value) => {
    const updated = [...dnsRecords];
    updated[index][field] = value;
    setDnsRecords(updated);
  };

  const handleBulkDnsAdd = async () => {
    const validRecords = dnsRecords.filter(record =>
      record.address.trim() !== ''
    );

    if (validRecords.length === 0) {
      alert('Please add at least one DNS record with a valid address');
      return;
    }

    setIsSubmitting(true);
    setIsOperationActive(true);

    try {
      const requestData = {
        domains: selectedDomains,
        records: validRecords.map(record => ({
          type: record.type,
          name: record.name || '@',
          address: record.address.trim(),
          ttl: record.ttl === 'Automatic' ? 1800 : parseInt(record.ttl)
        }))
      };

      const response = await axios.post('/api/bulk-dns-update', requestData);

      if (response.data.status === 'started') {
        // Progress tracking will handle the rest
      } else {
        alert('Failed to start DNS update: ' + (response.data.error || 'Unknown error'));
        setIsSubmitting(false);
        setIsOperationActive(false);
      }
    } catch (error) {
      console.error('Error starting bulk DNS update:', error);
      alert('Error starting DNS update: ' + error.message);
      setIsSubmitting(false);
      setIsOperationActive(false);
    }
  };

  const handleBulkDnsRemove = async () => {
    if (!removeRecordName.trim()) {
      alert('Please enter a record name to remove');
      return;
    }

    if (!window.confirm(`Are you sure you want to remove all ${removeRecordType} records with name "${removeRecordName}" from ${selectedDomains.length} domains?`)) {
      return;
    }

    setIsSubmitting(true);
    setIsOperationActive(true);

    try {
      const requestData = {
        domains: selectedDomains,
        record_type: removeRecordType,
        record_name: removeRecordName.trim()
      };

      const response = await axios.post('/api/bulk-dns-remove', requestData);

      if (response.data.status === 'started') {
        // Progress tracking will handle the rest
      } else {
        alert('Failed to start DNS removal: ' + (response.data.error || 'Unknown error'));
        setIsSubmitting(false);
        setIsOperationActive(false);
      }
    } catch (error) {
      console.error('Error starting bulk DNS removal:', error);
      alert('Error starting DNS removal: ' + error.message);
      setIsSubmitting(false);
      setIsOperationActive(false);
    }
  };

  const stopOperation = async () => {
    try {
      await axios.post('/api/stop-sync');
      setIsOperationActive(false);
      setIsSubmitting(false);
    } catch (error) {
      console.error('Error stopping operation:', error);
    }
  };

  const resumeOperation = async () => {
    try {
      const endpoint = activeTab === 'dns-add' ? '/api/resume-bulk-dns' : '/api/resume-bulk-dns-remove';
      await axios.post(endpoint);
      setIsOperationActive(true);
      setIsSubmitting(true);
    } catch (error) {
      console.error('Error resuming operation:', error);
      alert('Error resuming operation: ' + error.message);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="card"
        style={{
          width: '90%',
          maxWidth: '800px',
          margin: 0,
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>🌐 DNS Records Management</h2>
        <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
          Manage DNS records for {selectedDomains.length} selected domain{selectedDomains.length !== 1 ? 's' : ''}
        </p>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid #e5e7eb' }}>
          <button
            onClick={() => setActiveTab('dns-add')}
            style={{
              padding: '0.75rem 1rem',
              border: 'none',
              borderBottom: activeTab === 'dns-add' ? '2px solid #3b82f6' : '2px solid transparent',
              background: activeTab === 'dns-add' ? '#eff6ff' : 'transparent',
              color: activeTab === 'dns-add' ? '#1d4ed8' : '#6b7280',
              cursor: 'pointer',
              fontWeight: activeTab === 'dns-add' ? '600' : '400'
            }}
            disabled={isSubmitting}
          >
            ➕ Add DNS Records
          </button>
          <button
            onClick={() => setActiveTab('dns-remove')}
            style={{
              padding: '0.75rem 1rem',
              border: 'none',
              borderBottom: activeTab === 'dns-remove' ? '2px solid #ef4444' : '2px solid transparent',
              background: activeTab === 'dns-remove' ? '#fef2f2' : 'transparent',
              color: activeTab === 'dns-remove' ? '#dc2626' : '#6b7280',
              cursor: 'pointer',
              fontWeight: activeTab === 'dns-remove' ? '600' : '400'
            }}
            disabled={isSubmitting}
          >
            🗑️ Remove DNS Records
          </button>
        </div>

        {/* Progress Display */}
        {progress && (
          <div className="sync-status">
            <h3>DNS Operation Progress</h3>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${progress.processed / progress.total * 100}%`
                }}
              ></div>
            </div>
            <p>
              {progress.status === 'running' && '🔄 Processing... '}
              {progress.status === 'paused' && '⏸️ Paused (Rate limited) '}
              {progress.status === 'stopped' && '⏹️ Stopped '}
              {progress.status === 'completed' && '✅ Completed '}
              {progress.processed}/{progress.total} domains
            </p>

            {progress.current_domain && (
              <p style={{ fontSize: '0.9em', color: '#6b7280' }}>
                Current: {progress.current_domain}
              </p>
            )}

            <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
              {progress.status === 'running' && (
                <button
                  className="btn"
                  onClick={stopOperation}
                  style={{ background: '#ef4444' }}
                >
                  ⏹️ Stop
                </button>
              )}

              {(progress.status === 'paused' || progress.status === 'stopped') && progress.processed < progress.total && (
                <button
                  className="btn btn-success"
                  onClick={resumeOperation}
                >
                  ▶️ Resume
                </button>
              )}
            </div>
          </div>
        )}

        {/* Add DNS Records Tab */}
        {activeTab === 'dns-add' && (
          <div>
            <h3>Add DNS Records</h3>
            <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
              Add DNS records to all selected domains. Each record will be added to every selected domain.
            </p>

            {dnsRecords.map((record, index) => (
              <div key={index} style={{
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1rem',
                background: '#f9fafb'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h4>DNS Record #{index + 1}</h4>
                  {dnsRecords.length > 1 && (
                    <button
                      onClick={() => removeDnsRecord(index)}
                      style={{
                        background: '#ef4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        padding: '0.25rem 0.5rem',
                        cursor: 'pointer'
                      }}
                      disabled={isSubmitting}
                    >
                      Remove
                    </button>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 2fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                      Type
                    </label>
                    <select
                      className="form-control"
                      value={record.type}
                      onChange={(e) => updateDnsRecord(index, 'type', e.target.value)}
                      disabled={isSubmitting}
                    >
                      {recordTypes.map(type => (
                        <option key={type} value={type}>{type}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                      Host/Name
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="@ or subdomain"
                      value={record.name}
                      onChange={(e) => updateDnsRecord(index, 'name', e.target.value)}
                      disabled={isSubmitting}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                      Value/Address *
                    </label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder={record.type === 'A' ? 'IP Address (e.g., 1.2.3.4)' :
                                 record.type === 'CNAME' ? 'Domain (e.g., example.com)' :
                                 record.type === 'MX' ? 'Mail server (e.g., mail.example.com)' :
                                 record.type === 'TXT' ? 'Text value' : 'Record value'}
                      value={record.address}
                      onChange={(e) => updateDnsRecord(index, 'address', e.target.value)}
                      disabled={isSubmitting}
                      required
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                      TTL
                    </label>
                    <select
                      className="form-control"
                      value={record.ttl}
                      onChange={(e) => updateDnsRecord(index, 'ttl', e.target.value)}
                      disabled={isSubmitting}
                    >
                      {ttlOptions.map(option => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            ))}

            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
              <button
                onClick={addDnsRecord}
                className="btn"
                style={{ background: '#10b981' }}
                disabled={isSubmitting}
              >
                ➕ Add Another Record
              </button>

              <button
                onClick={handleBulkDnsAdd}
                className="btn btn-success"
                disabled={isSubmitting || dnsRecords.every(r => !r.address.trim())}
              >
                {isSubmitting ? '🔄 Adding DNS Records...' : `🚀 Add to ${selectedDomains.length} Domain${selectedDomains.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        )}

        {/* Remove DNS Records Tab */}
        {activeTab === 'dns-remove' && (
          <div>
            <h3>Remove DNS Records</h3>
            <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
              Remove specific DNS records from all selected domains by record type and name.
            </p>

            <div style={{
              border: '1px solid #fecaca',
              borderRadius: '8px',
              padding: '1rem',
              marginBottom: '1.5rem',
              background: '#fef2f2'
            }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                    Record Type
                  </label>
                  <select
                    className="form-control"
                    value={removeRecordType}
                    onChange={(e) => setRemoveRecordType(e.target.value)}
                    disabled={isSubmitting}
                  >
                    {recordTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                    Host/Name to Remove *
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="@ or subdomain name"
                    value={removeRecordName}
                    onChange={(e) => setRemoveRecordName(e.target.value)}
                    disabled={isSubmitting}
                    required
                  />
                </div>
              </div>

              <div style={{ background: '#fee2e2', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem' }}>
                <p style={{ color: '#dc2626', fontWeight: 600, margin: 0 }}>
                  ⚠️ Warning: This will permanently remove all {removeRecordType} records
                  with name "{removeRecordName || '@'}" from {selectedDomains.length} domain{selectedDomains.length !== 1 ? 's' : ''}.
                </p>
              </div>

              <button
                onClick={handleBulkDnsRemove}
                className="btn btn-danger"
                disabled={isSubmitting || !removeRecordName.trim()}
              >
                {isSubmitting ? '🔄 Removing DNS Records...' : `🗑️ Remove from ${selectedDomains.length} Domain${selectedDomains.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </div>
        )}

        {/* Close Button */}
        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <button
            className="btn"
            onClick={onClose}
            style={{ background: '#6b7280' }}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Operation in Progress...' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DNSModal;