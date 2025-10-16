import React from 'react';
import { StatusBadge, Button } from '../common';

/**
 * PublishedFilesGrid Component
 */
function PublishedFilesGrid({ files, onUnpublish, formatFileSize, formatTimestamp }) {
  return (
    <div className="grid-container">
      {files.map((file) => (
        <div key={file.name} className="grid-item">
          <div className="grid-item-title">{file.name}</div>
          <div className="grid-item-meta">
            <div><strong>Size:</strong> {formatFileSize(file.size)}</div>
            <div><strong>Published:</strong> {formatTimestamp(file.published_at)}</div>
            <div>
              <StatusBadge status="online">Published</StatusBadge>
            </div>
          </div>
          <div className="grid-item-actions">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onUnpublish(file.name)}
            >
              Unpublish
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default PublishedFilesGrid;
