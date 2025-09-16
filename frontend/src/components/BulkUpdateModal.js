import React, { useState } from 'react';

const BulkUpdateModal = ({ selectedDomains, clients, onSubmit, onClose }) => {
  const [updateType, setUpdateType] = useState('manual'); // 'manual' or 'client'
  const [manualUrl, setManualUrl] = useState('');
  const [selectedClient, setSelectedClient] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

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

    setIsSubmitting(true);

    try {
      const result = await onSubmit({ target: targetUrl, type: updateType });

      if (result.success) {
        alert(`Successfully updated ${selectedDomains.length} domains`);
        onClose();
      } else {
        alert('Bulk update failed: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      alert('Error during bulk update: ' + error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClientChange = (clientId) => {
    setSelectedClient(clientId);
    const client = clients.find(c => c.id === parseInt(clientId));
    if (client && client.url) {
      setManualUrl(client.url); // Auto-fill the manual URL field
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
          maxWidth: '500px',
          margin: 0,
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Bulk Update Redirects</h2>
        <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
          Update redirect URLs for {selectedDomains.length} selected domains
        </p>

        <form onSubmit={handleSubmit}>
          {/* Update Type Selection */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
              Update Type:
            </label>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="radio"
                  name="updateType"
                  value="manual"
                  checked={updateType === 'manual'}
                  onChange={(e) => setUpdateType(e.target.value)}
                />
                Manual URL
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="radio"
                  name="updateType"
                  value="client"
                  checked={updateType === 'client'}
                  onChange={(e) => setUpdateType(e.target.value)}
                />
                Client URL
              </label>
            </div>
          </div>

          {/* Manual URL Input */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
              Redirect URL:
            </label>
            <input
              type="url"
              className="form-control"
              placeholder="https://redirect-url.com"
              value={manualUrl}
              onChange={(e) => setManualUrl(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </div>

          {/* Client Selection */}
          {updateType === 'client' && (
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
                Select Client:
              </label>
              <select
                className="form-control"
                value={selectedClient}
                onChange={(e) => handleClientChange(e.target.value)}
                disabled={isSubmitting}
                required
              >
                <option value="">Choose a client...</option>
                {clients
                  .filter(client => client.url) // Only show clients with URLs
                  .map(client => (
                    <option key={client.id} value={client.id}>
                      {client.name} ({client.url})
                    </option>
                  ))}
              </select>
            </div>
          )}

          {/* Selected Domains Preview */}
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
              Selected Domains ({selectedDomains.length}):
            </label>
            <div
              style={{
                maxHeight: '150px',
                overflowY: 'auto',
                padding: '0.75rem',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                backgroundColor: '#f9fafb',
                fontSize: '0.875rem'
              }}
            >
              {selectedDomains.map((domain, index) => (
                <div key={domain} style={{ marginBottom: '0.25rem' }}>
                  {index + 1}. {domain}
                </div>
              ))}
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-1 justify-between">
            <button
              type="button"
              className="btn"
              onClick={onClose}
              disabled={isSubmitting}
              style={{ background: '#6b7280' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-success"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Updating...' : 'Update All Domains'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BulkUpdateModal;