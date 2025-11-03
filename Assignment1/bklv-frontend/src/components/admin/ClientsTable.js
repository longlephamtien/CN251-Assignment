import React from 'react';
import { StatusBadge, Button } from '../common';
import './ClientsTable.css';

/**
 * ClientsTable Component - Display clients in table format
 */
function ClientsTable({ clients, onPing, onDiscover, formatTimestamp }) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Display Name</th>
            <th>Address</th>
            <th>Files</th>
            <th>Status</th>
            <th>Last Seen</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {clients.length === 0 ? (
            <tr>
              <td colSpan="7" className="clients-table-empty">
                No clients registered yet
              </td>
            </tr>
          ) : (
            clients.map((client) => (
              <tr key={client.hostname}>
                <td>{client.hostname}</td>
                <td>{client.display_name}</td>
                <td>
                  {client.status === 'online' 
                    ? `${client.ip}:${client.port}`
                    : <span className="clients-table-address-na">N/A</span>
                  }
                </td>
                <td>{client.file_count}</td>
                <td>
                  <StatusBadge status={client.status}>
                    {client.status}
                  </StatusBadge>
                </td>
                <td className="text-small">
                  {client.status === 'online' 
                    ? formatTimestamp(client.last_seen)
                    : client.last_login 
                      ? `Last login: ${new Date(client.last_login).toLocaleString()}`
                      : 'Never connected'
                  }
                </td>
                <td>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onPing(client.hostname)}
                    disabled={client.status === 'offline'}
                    className="clients-table-action-btn"
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
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ClientsTable;
