import React from 'react';
import { StatusBadge, Button } from '../common';
import './ClientsGrid.css';

/**
 * ClientsGrid Component - Display clients in grid format
 */
function ClientsGrid({ clients, onPing, onDiscover, formatTimestamp }) {
  return (
    <div className="grid-container">
      {clients.length === 0 ? (
        <div className="clients-grid-empty">
          No clients registered yet
        </div>
      ) : (
        clients.map((client) => (
          <div key={client.hostname} className="grid-item">
            <div className="grid-item-title">{client.display_name}</div>
            <div className="grid-item-meta">
              <div><strong>Hostname:</strong> {client.hostname}</div>
              <div>
                <strong>Address:</strong>{' '}
                {client.status === 'online' 
                  ? `${client.ip}:${client.port}`
                  : <span className="clients-grid-address-na">N/A</span>
                }
              </div>
              <div><strong>Files:</strong> {client.file_count}</div>
              <div>
                <strong>Status:</strong>{' '}
                <StatusBadge status={client.status}>
                  {client.status}
                </StatusBadge>
              </div>
              <div className="text-small text-gray">
                {client.status === 'online' 
                  ? `Last seen: ${formatTimestamp(client.last_seen)}`
                  : client.last_login 
                    ? `Last login: ${new Date(client.last_login).toLocaleString()}`
                    : 'Never connected'
                }
              </div>
            </div>
            <div className="grid-item-actions">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onPing(client.hostname)}
                disabled={client.status === 'offline'}
              >
                Ping
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onDiscover(client.hostname)}
                disabled={client.status === 'offline'}
              >
                View Files
              </Button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

export default ClientsGrid;
