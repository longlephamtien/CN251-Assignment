import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../common';
import { truncateMiddle } from '../../utils/formatters';
import './NetworkFilesGrid.css';

/**
 * NetworkFilesGrid Component
 */
function NetworkFilesGrid({ files, onDownload, formatFileSize, formatTimestamp }) {
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
    <div className="network-files-grid" ref={gridRef}>
      {files.map((file, idx) => (
        <div key={`${file.owner_hostname}-${file.name}-${idx}`} className="network-files-grid-item">
          <div className="network-files-grid-title" title={file.name}>
            {truncateMiddle(file.name, maxFilenameLength)}
          </div>
          <div className="network-files-grid-meta">
            <div><strong>Size:</strong> {formatFileSize(file.size)}</div>
            <div><strong>Created:</strong> {formatTimestamp(file.created)}</div>
            <div><strong>Modified:</strong> {formatTimestamp(file.modified)}</div>
            <div><strong>Published:</strong> {formatTimestamp(file.published_at)}</div>
            <div><strong>Owner:</strong> {file.owner_name}</div>
          </div>
          <div className="network-files-grid-actions">
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
