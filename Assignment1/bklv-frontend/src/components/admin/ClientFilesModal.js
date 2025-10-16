import React from 'react';
import { Button } from '../common';

/**
 * ClientFilesModal Component - Display files from a selected client
 */
function ClientFilesModal({ client, onClose, formatFileSize }) {
  if (!client) return null;

  return (
    <div className="content-card">
      <div className="card-header">
        <h2 className="card-title">Files from {client.hostname}</h2>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>
      {client.files && client.files.length > 0 ? (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Size</th>
                <th>Published At</th>
              </tr>
            </thead>
            <tbody>
              {client.files.map((file, idx) => (
                <tr key={idx}>
                  <td>{file.name}</td>
                  <td>{formatFileSize(file.size)}</td>
                  <td>{new Date(file.published_at * 1000).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <p className="empty-state-text">No files shared by this client</p>
        </div>
      )}
    </div>
  );
}

export default ClientFilesModal;
