import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SyncProgress = ({ onComplete }) => {
  const [progress, setProgress] = useState({
    status: 'running',
    processed: 0,
    total: 0,
    current_domain: '',
    domains_added: 0,
    domains_updated: 0,
    errors: []
  });

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get('/api/sync-domains-progress');
        const data = response.data;

        setProgress(data);

        if (data.status === 'completed' || data.status === 'error') {
          clearInterval(interval);
          setTimeout(() => {
            onComplete();
          }, 3000); // Show completion for 3 seconds then refresh
        }
      } catch (error) {
        console.error('Error fetching sync progress:', error);
        clearInterval(interval);
        onComplete();
      }
    }, 1000); // Poll every second

    return () => clearInterval(interval);
  }, [onComplete]);

  const getProgressPercentage = () => {
    if (progress.total === 0) return 0;
    return Math.round((progress.processed / progress.total) * 100);
  };

  const getStatusClass = () => {
    switch (progress.status) {
      case 'completed':
        return 'sync-status completed';
      case 'error':
        return 'sync-status error';
      default:
        return 'sync-status';
    }
  };

  const getStatusText = () => {
    switch (progress.status) {
      case 'running':
        return 'Status: In Progress';
      case 'completed':
        return 'Status: Completed';
      case 'error':
        return 'Status: Failed';
      default:
        return 'Status: Initializing...';
    }
  };

  return (
    <div className={getStatusClass()}>
      <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#1e293b' }}>
        {getStatusText()}
      </div>

      <div style={{ color: '#6b7280', marginBottom: '0.5rem' }}>
        {progress.status === 'running' && (
          <>
            Synced {progress.processed} of {progress.total} domains
            {progress.current_domain && (
              <> (Currently: {progress.current_domain})</>
            )}
            <br />
            Added: {progress.domains_added} | Updated: {progress.domains_updated}
            {progress.errors.length > 0 && (
              <> | Errors: {progress.errors.length}</>
            )}
          </>
        )}

        {progress.status === 'completed' && (
          <>
            Successfully synced {progress.processed} of {progress.total} domains
            <br />
            Added: {progress.domains_added} | Updated: {progress.domains_updated}
            {progress.errors.length > 0 && (
              <> | Errors: {progress.errors.length}</>
            )}
            <br />
            <em>Refreshing page in 3 seconds...</em>
          </>
        )}

        {progress.status === 'error' && (
          <>
            Sync failed: {progress.error || 'Unknown error'}
            {progress.errors.length > 0 && (
              <>
                <br />
                Recent errors: {progress.errors.join(', ')}
              </>
            )}
          </>
        )}
      </div>

      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${getProgressPercentage()}%` }}
        />
      </div>

      {progress.status === 'running' && (
        <div style={{ fontSize: '0.875rem', color: '#6b7280', marginTop: '0.5rem' }}>
          {getProgressPercentage()}% complete
        </div>
      )}
    </div>
  );
};

export default SyncProgress;