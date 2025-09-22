import React, { useState } from 'react';

const DomainTable = ({
  domains,
  clients,
  selectedDomains,
  onSelectionChange,
  onSaveRedirect,
  onClientChange,
  bulkUpdateResults = {}
}) => {
  const [savingDomains, setSavingDomains] = useState(new Set());
  const [domainStatuses, setDomainStatuses] = useState({});
  const [redirectValues, setRedirectValues] = useState({});

  const handleSelectAll = (checked) => {
    if (checked) {
      onSelectionChange(domains.map(d => d.domain_name));
    } else {
      onSelectionChange([]);
    }
  };

  const handleDomainSelect = (domainName, checked) => {
    if (checked) {
      onSelectionChange([...selectedDomains, domainName]);
    } else {
      onSelectionChange(selectedDomains.filter(d => d !== domainName));
    }
  };

  const handleRedirectChange = (domainName, value) => {
    setRedirectValues({
      ...redirectValues,
      [domainName]: value
    });
  };

  const getCurrentRedirectValue = (domain) => {
    if (redirectValues[domain.domain_name] !== undefined) {
      return redirectValues[domain.domain_name];
    }
    return domain.redirect_url || '';
  };

  const handleSave = async (domain) => {
    const domainName = domain.domain_name;
    const redirectUrl = getCurrentRedirectValue(domain);

    if (!redirectUrl.trim()) {
      alert('Please enter a redirect URL');
      return;
    }

    // Add to saving set
    setSavingDomains(prev => new Set([...prev, domainName]));

    // Show updating status
    setDomainStatuses({
      ...domainStatuses,
      [domainName]: { status: 'updating', message: '⏳ Updating...' }
    });

    try {
      const result = await onSaveRedirect(domainName, redirectUrl);

      if (result.success) {
        setDomainStatuses({
          ...domainStatuses,
          [domainName]: {
            status: 'success',
            message: result.verified ? '✅ Synced & Verified' : '✅ Synced'
          }
        });
      } else {
        setDomainStatuses({
          ...domainStatuses,
          [domainName]: {
            status: 'error',
            message: '❌ Failed: ' + (result.error || 'Unknown error')
          }
        });
      }
    } catch (error) {
      setDomainStatuses({
        ...domainStatuses,
        [domainName]: {
          status: 'error',
          message: '❌ Error: ' + error.message
        }
      });
    } finally {
      // Remove from saving set
      setSavingDomains(prev => {
        const newSet = new Set(prev);
        newSet.delete(domainName);
        return newSet;
      });
    }
  };

  const handleClientChange = async (domain, clientId) => {
    if (clientId) {
      const clientUrl = await onClientChange(domain.domain_name, clientId);
      if (clientUrl) {
        // Auto-fill redirect URL
        setRedirectValues({
          ...redirectValues,
          [domain.domain_name]: clientUrl
        });
      }
    }
  };

  const getStatusDisplay = (domainName) => {
    // Check for bulk update results first
    const bulkResult = bulkUpdateResults[domainName];
    if (bulkResult) {
      const className = bulkResult.success ? 'status-success' : 'status-error';
      const message = bulkResult.success
        ? (bulkResult.verified ? '✅ Bulk Updated & Verified' : '✅ Bulk Updated')
        : '❌ Bulk Update Failed';
      return <span className={className}>{message}</span>;
    }

    // Check for individual save status
    const status = domainStatuses[domainName];
    if (!status) return null;

    const className = `status-${status.status}`;
    return <span className={className}>{status.message}</span>;
  };

  if (domains.length === 0) {
    return (
      <div className="text-center" style={{ padding: '2rem', color: '#6b7280' }}>
        No domains found. Click "Sync All Domains" to load domains from Namecheap.
      </div>
    );
  }

  return (
    <table className="table">
      <thead>
        <tr>
          <th style={{ width: '5%' }}>
            <input
              type="checkbox"
              checked={selectedDomains.length === domains.length && domains.length > 0}
              onChange={(e) => handleSelectAll(e.target.checked)}
            />
          </th>
          <th style={{ width: '5%' }}>#</th>
          <th style={{ width: '25%' }}>Domain</th>
          <th style={{ width: '35%' }}>Redirect Target</th>
          <th style={{ width: '15%' }}>Client</th>
          <th style={{ width: '15%' }}>Status</th>
        </tr>
      </thead>
      <tbody>
        {domains.map((domain) => (
          <tr key={domain.domain_name}>
            <td>
              <input
                type="checkbox"
                checked={selectedDomains.includes(domain.domain_name)}
                onChange={(e) => handleDomainSelect(domain.domain_name, e.target.checked)}
              />
            </td>
            <td>
              <strong>#{domain.domain_number || 'N/A'}</strong>
            </td>
            <td>
              <strong>{domain.domain_name}</strong>
            </td>
            <td>
              <div className="flex gap-1 items-center">
                <input
                  type="text"
                  className="form-control"
                  placeholder="https://example.com"
                  value={getCurrentRedirectValue(domain)}
                  onChange={(e) => handleRedirectChange(domain.domain_name, e.target.value)}
                  disabled={savingDomains.has(domain.domain_name)}
                />
                <button
                  className="btn btn-success btn-small"
                  onClick={() => handleSave(domain)}
                  disabled={savingDomains.has(domain.domain_name)}
                >
                  {savingDomains.has(domain.domain_name) ? 'Saving...' : 'Save'}
                </button>
              </div>
            </td>
            <td>
              <select
                className="form-control"
                value={domain.client_id || ''}
                onChange={(e) => handleClientChange(domain, e.target.value)}
              >
                <option value="">Unassigned</option>
                {clients.map(client => (
                  <option key={client.id} value={client.id}>
                    {client.name}
                  </option>
                ))}
              </select>
            </td>
            <td>
              {getStatusDisplay(domain.domain_name)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default DomainTable;