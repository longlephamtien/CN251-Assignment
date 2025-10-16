import React from 'react';
import { StatusBadge, Button } from '../common';

/**
 * LocalFilesGrid Component - Display local files in grid format
 */
function LocalFilesGrid({ files, onPublish, onUnpublish, formatFileSize, formatTimestamp }) {
  return (
    <div className="grid-container">
      {files.map((file) => (
        <div key={file.name} className="grid-item">
          <div className="grid-item-title">{file.name}</div>
          <div className="grid-item-meta">
            <div><strong>Size:</strong> {formatFileSize(file.size)}</div>
            <div><strong>Modified:</strong> {formatTimestamp(file.modified)}</div>
            <div>
              <strong>Status:</strong>{' '}
              {file.is_published ? (
                <StatusBadge status="online">Published</StatusBadge>
              ) : (
                <StatusBadge status="offline">Local Only</StatusBadge>
              )}
            </div>
          </div>
          <div className="grid-item-actions">
            {!file.is_published ? (
              <Button
                variant="primary"
                size="sm"
                onClick={() => onPublish(file)}
              >
                Publish
              </Button>
            ) : (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onUnpublish(file.name)}
              >
                Unpublish
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default LocalFilesGrid;
