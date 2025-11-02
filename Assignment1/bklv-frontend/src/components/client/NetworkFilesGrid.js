import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../common';
import { truncateMiddle } from '../../utils/formatters';

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
    <div className="grid-container" ref={gridRef} style={{ 
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: '16px',
      padding: '8px'
    }}>
      {files.map((file, idx) => (
        <div key={`${file.owner_hostname}-${file.name}-${idx}`} className="grid-item" style={{
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '16px',
          backgroundColor: '#fff'
        }}>
          <div className="grid-item-title" style={{
            fontWeight: 'bold',
            marginBottom: '12px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }} title={file.name}>
            {truncateMiddle(file.name, maxFilenameLength)}
          </div>
          <div className="grid-item-meta" style={{ fontSize: '0.85em', color: '#666', marginBottom: '12px' }}>
            <div><strong>Size:</strong> {formatFileSize(file.size)}</div>
            <div><strong>Created:</strong> {formatTimestamp(file.created)}</div>
            <div><strong>Modified:</strong> {formatTimestamp(file.modified)}</div>
            <div><strong>Published:</strong> {formatTimestamp(file.published_at)}</div>
            <div><strong>Owner:</strong> {file.owner_name}</div>
          </div>
          <div className="grid-item-actions" style={{ 
            display: 'flex',
            justifyContent: 'center',
            marginTop: '12px'
          }}>
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
