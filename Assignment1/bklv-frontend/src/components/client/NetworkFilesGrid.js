import React from 'react';
import { Button } from '../common';

/**
 * NetworkFilesGrid Component
 */
function NetworkFilesGrid({ files, onDownload, formatFileSize }) {
  return (
    <div className="grid-container">
      {files.map((file, idx) => (
        <div key={`${file.owner_hostname}-${file.name}-${idx}`} className="grid-item">
          <div className="grid-item-title">{file.name}</div>
          <div className="grid-item-meta">
            <div><strong>Size:</strong> {formatFileSize(file.size)}</div>
            <div><strong>Owner:</strong> {file.owner_name}</div>
            <div className="text-small text-gray">
              {file.owner_ip}:{file.owner_port}
            </div>
          </div>
          <div className="grid-item-actions">
            <Button
              variant="primary"
              size="sm"
              onClick={() => onDownload(file)}
            >
              Download
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default NetworkFilesGrid;
