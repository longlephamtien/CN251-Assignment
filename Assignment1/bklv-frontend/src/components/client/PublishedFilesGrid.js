import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../common';
import { truncateMiddle } from '../../utils/formatters';
import './PublishedFilesGrid.css';

/**
 * PublishedFilesGrid Component
 */
function PublishedFilesGrid({ files, onUnpublish, formatFileSize, formatTimestamp }) {
  const gridRef = useRef(null);
  const [maxFilenameLength, setMaxFilenameLength] = useState(40);

  useEffect(() => {
    const updateMaxLength = () => {
      if (gridRef.current) {
        const gridWidth = gridRef.current.offsetWidth;
        const itemWidth = (gridWidth - 32) / 3;
        const titleWidth = itemWidth - 32;
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
    <div className="published-files-grid" ref={gridRef}>
      {files.map((file) => (
        <div key={file.name} className="published-files-grid-item">
          <div className="published-files-grid-title" title={file.name}>
            {truncateMiddle(file.name, maxFilenameLength)}
          </div>
          <div className="published-files-grid-meta">
            <div><strong>Size:</strong> {formatFileSize(file.size)}</div>
            <div><strong>Created:</strong> {formatTimestamp(file.created)}</div>
            <div><strong>Modified:</strong> {formatTimestamp(file.modified)}</div>
            <div><strong>Added:</strong> {formatTimestamp(file.added_at)}</div>
            <div><strong>Published:</strong> {formatTimestamp(file.published_at)}</div>
          </div>
          <div className="published-files-grid-actions">
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
