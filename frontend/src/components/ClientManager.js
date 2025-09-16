import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ClientManager = ({ clients: initialClients, onClose }) => {
  const [clients, setClients] = useState(initialClients || []);
  const [newClientName, setNewClientName] = useState('');
  const [newClientUrl, setNewClientUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [editingClient, setEditingClient] = useState(null);

  useEffect(() => {
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      const response = await axios.get('/api/clients');
      if (response.data.status === 'success') {
        setClients(response.data.clients);
      }
    } catch (error) {
      console.error('Error loading clients:', error);
    }
  };

  const handleAddClient = async (e) => {
    e.preventDefault();

    if (!newClientName.trim()) {
      alert('Please enter a client name');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await axios.post('/api/clients', {
        name: newClientName.trim(),
        url: newClientUrl.trim() || null
      });

      if (response.data.status === 'success') {
        setNewClientName('');
        setNewClientUrl('');
        await loadClients();
      } else {
        alert('Failed to add client: ' + (response.data.error || 'Unknown error'));
      }
    } catch (error) {
      alert('Error adding client: ' + error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditClient = (client) => {
    setEditingClient(client);
    setNewClientName(client.name);
    setNewClientUrl(client.url || '');
  };

  const handleUpdateClient = async (e) => {
    e.preventDefault();

    if (!newClientName.trim()) {
      alert('Please enter a client name');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await axios.put(`/api/clients/${editingClient.id}`, {
        name: newClientName.trim(),
        url: newClientUrl.trim() || null
      });

      if (response.data.status === 'success') {
        setEditingClient(null);
        setNewClientName('');
        setNewClientUrl('');
        await loadClients();
      } else {
        alert('Failed to update client: ' + (response.data.error || 'Unknown error'));
      }
    } catch (error) {
      alert('Error updating client: ' + error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteClient = async (clientId) => {
    if (!window.confirm('Are you sure you want to delete this client?')) {
      return;
    }

    try {
      const response = await axios.delete(`/api/clients/${clientId}`);

      if (response.data.status === 'success') {
        await loadClients();
      } else {
        alert('Failed to delete client: ' + (response.data.error || 'Unknown error'));
      }
    } catch (error) {
      alert('Error deleting client: ' + error.message);
    }
  };

  const cancelEdit = () => {
    setEditingClient(null);
    setNewClientName('');
    setNewClientUrl('');
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
          maxWidth: '700px',
          margin: 0,
          maxHeight: '90vh',
          overflowY: 'auto'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Manage Clients</h2>
        <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
          Add, edit, and manage client redirect URLs
        </p>

        {/* Add/Edit Client Form */}
        <form onSubmit={editingClient ? handleUpdateClient : handleAddClient}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
              Client Name:
            </label>
            <input
              type="text"
              className="form-control"
              placeholder="Enter client name"
              value={newClientName}
              onChange={(e) => setNewClientName(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>
              Client URL:
            </label>
            <input
              type="url"
              className="form-control"
              placeholder="https://client-website.com (optional)"
              value={newClientUrl}
              onChange={(e) => setNewClientUrl(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className="flex gap-1 items-center" style={{ marginBottom: '2rem' }}>
            <button
              type="submit"
              className="btn btn-success"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? (editingClient ? 'Updating...' : 'Adding...')
                : (editingClient ? 'Update Client' : 'Add Client')
              }
            </button>

            {editingClient && (
              <button
                type="button"
                className="btn"
                onClick={cancelEdit}
                disabled={isSubmitting}
                style={{ background: '#6b7280' }}
              >
                Cancel
              </button>
            )}
          </div>
        </form>

        {/* Clients List */}
        <h3>Existing Clients ({clients.length})</h3>

        {clients.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#6b7280', padding: '2rem' }}>
            No clients found. Add your first client above.
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>URL</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {clients.map((client) => (
                <tr key={client.id}>
                  <td>
                    <strong>{client.name}</strong>
                  </td>
                  <td>
                    {client.url ? (
                      <a
                        href={client.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: '#3b82f6' }}
                      >
                        {client.url}
                      </a>
                    ) : (
                      <em style={{ color: '#6b7280' }}>No URL</em>
                    )}
                  </td>
                  <td>
                    <div className="flex gap-1">
                      <button
                        className="btn btn-small"
                        onClick={() => handleEditClient(client)}
                        style={{ background: '#f59e0b' }}
                      >
                        Edit
                      </button>
                      <button
                        className="btn btn-danger btn-small"
                        onClick={() => handleDeleteClient(client.id)}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Close Button */}
        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <button className="btn" onClick={onClose} style={{ background: '#6b7280' }}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClientManager;