import React, { useState, useEffect, useRef } from 'react';
import { StatusBadge, Button } from '../common';
import { truncateMiddle } from '../../utils/formatters';
import './LocalFilesGrid.css';

/**
 * LocalFilesGrid Component - Display local files in grid format
 */
function LocalFilesGrid({ files, onPublish, onUnpublish, formatFileSize, formatTimestamp }) {
  const gridRef = useRef(null);
  const [maxFilenameLength, setMaxFilenameLength] = useState(40);

  useEffect(() => {
    const updateMaxLength = () => {
      if (gridRef.current) {
        const gridWidth = gridRef.current.offsetWidth;
        // Each grid item is 1/3 of container width (minus gaps)
        const itemWidth = (gridWidth - 32) / 3; // 32px total gap (16px * 2)
        // Title takes most of the item width (minus padding)
        const titleWidth = itemWidth - 32; // 32px padding
        const charWidth = 9;
        const calculatedMaxLength = Math.floor(titleWidth / charWidth);
        setMaxFilenameLength(Math.max(15, calculatedMaxLength));
      }
    };

    updateMaxLength();
    window.addEventListener('resize', updateMaxLength);
    return () => window.removeEventListener('resize', updateMaxLength);
  }, []);

  return (
    <div className="local-files-grid" ref={gridRef}>
      {files.map((file) => (
        <div key={file.name} className="local-files-grid-item">
          <div className="local-files-grid-title" title={file.name}>
            {truncateMiddle(file.name, maxFilenameLength)}
          </div>
          <div className="local-files-grid-meta">
            <div><strong>Size:</strong> {formatFileSize(file.size)}</div>
            <div><strong>Created:</strong> {formatTimestamp(file.created)}</div>
            <div><strong>Modified:</strong> {formatTimestamp(file.modified)}</div>
            <div><strong>Added:</strong> {formatTimestamp(file.added_at)}</div>
            <div>
              <strong>Status:</strong>{' '}
              {file.is_published ? (
                <StatusBadge status="online">Published</StatusBadge>
              ) : (
                <StatusBadge status="offline">Local Only</StatusBadge>
              )}
            </div>
          </div>
          <div className="local-files-grid-actions">
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
