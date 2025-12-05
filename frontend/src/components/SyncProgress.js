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

        if (data.status === 'completed' || data.status === 'error' || data.status === 'stopped') {
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
      case 'stopped':
        return 'sync-status stopped';
      case 'rate_limited':
        return 'sync-status rate-limited';
      default:
        return 'sync-status';
    }
  };

  const getStatusText = () => {
    switch (progress.status) {
      case 'completed':
        return 'Status: Completed';
      case 'error':
        return 'Status: Failed';
      case 'stopped':
        return 'Status: Stopped by User';
      case 'rate_limited':
        return 'Status: Paused - Rate Limited';
      default:
        return 'Status: In Progress';
    }
  };

  return (
    <div className={getStatusClass()}>
      <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#1e293b' }}>
        {getStatusText()}
      </div>

      <div style={{ color: '#6b7280', marginBottom: '0.5rem' }}>
        {(progress.status === 'running' || (progress.status !== 'completed' && progress.status !== 'error' && progress.status !== 'stopped' && progress.status !== 'rate_limited')) && (
          <>
            Synced {progress.processed || 0} of {progress.total || 0} domains
            {progress.current_domain && (
              <> (Currently: {progress.current_domain})</>
            )}
            <br />
            Added: {progress.domains_added || 0} | Updated: {progress.domains_updated || 0}
            {(progress.total_errors || (progress.errors && progress.errors.length)) > 0 && (
              <> | Errors: {progress.total_errors || progress.errors.length}</>
            )}
          </>
        )}

        {progress.status === 'completed' && (
          <>
            Successfully synced {progress.processed} of {progress.total} domains
            <br />
            Added: {progress.domains_added} | Updated: {progress.domains_updated}
            {(progress.total_errors || progress.errors.length) > 0 && (
              <> | Errors: {progress.total_errors || progress.errors.length}</>
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

        {progress.status === 'rate_limited' && (
          <>
            Synced {progress.processed} of {progress.total} domains (paused)
            <br />
            Added: {progress.domains_added} | Updated: {progress.domains_updated}
            {(progress.total_errors || progress.errors.length) > 0 && (
              <> | Errors: {progress.total_errors || progress.errors.length}</>
            )}
            <br />
            <div style={{
              marginTop: '1rem',
              padding: '1rem',
              backgroundColor: '#fef3c7',
              borderRadius: '6px',
              borderLeft: '4px solid #f59e0b'
            }}>
              <div style={{ fontWeight: '600', color: '#92400e', marginBottom: '0.5rem' }}>
                ⚠️ Rate Limit Reached
              </div>
              <div style={{ color: '#92400e', fontSize: '0.875rem', marginBottom: '1rem' }}>
                {progress.rate_limit_message || 'Sync paused due to Namecheap API rate limits.'}
              </div>
              <button
                onClick={async () => {
                  try {
                    await axios.post('/api/resume-sync');
                  } catch (error) {
                    alert('Failed to resume sync: ' + error.message);
                  }
                }}
                style={{
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: '600'
                }}
              >
                🔄 Resume Sync
              </button>
            </div>
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

      {/* Show detailed errors if any */}
      {progress.errors && progress.errors.length > 0 && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem',
          backgroundColor: '#fef2f2',
          borderRadius: '6px',
          borderLeft: '4px solid #ef4444'
        }}>
          <div style={{ fontWeight: '600', fontSize: '0.875rem', color: '#dc2626', marginBottom: '0.5rem' }}>
            Recent Sync Errors ({progress.total_errors || progress.errors.length} total):
          </div>
          <div style={{ fontSize: '0.8rem', color: '#7f1d1d' }}>
            {progress.errors.slice(-5).map((error, index) => (
              <div key={index} style={{ marginBottom: '0.25rem', fontFamily: 'monospace' }}>
                • {error}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SyncProgress;