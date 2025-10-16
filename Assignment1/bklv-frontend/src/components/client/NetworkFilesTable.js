import React from 'react';
import { Button } from '../common';

/**
 * NetworkFilesTable Component
 */
function NetworkFilesTable({ files, onDownload, formatFileSize }) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Owner</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file, idx) => (
            <tr key={`${file.owner_hostname}-${file.name}-${idx}`}>
              <td>{file.name}</td>
              <td>{formatFileSize(file.size)}</td>
              <td>
                {file.owner_name}
                <div className="text-small text-gray">
                  {file.owner_ip}:{file.owner_port}
                </div>
              </td>
              <td>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => onDownload(file)}
                >
                  Download
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default NetworkFilesTable;
