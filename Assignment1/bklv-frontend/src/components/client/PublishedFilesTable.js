import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../common';
import { truncateMiddle, formatTimestampMultiLine } from '../../utils/formatters';

/**
 * PublishedFilesTable Component
 */
function PublishedFilesTable({ files, onUnpublish, formatFileSize, formatTimestamp }) {
  const tableRef = useRef(null);
  const [maxFilenameLength, setMaxFilenameLength] = useState(50);

  useEffect(() => {
    const updateMaxLength = () => {
      if (tableRef.current) {
        const tableWidth = tableRef.current.offsetWidth;
        const filenameColumnWidth = tableWidth * 0.3;
        const charWidth = 9;
        const calculatedMaxLength = Math.floor(filenameColumnWidth / charWidth);
        setMaxFilenameLength(Math.max(20, calculatedMaxLength));
      }
    };

    updateMaxLength();
    window.addEventListener('resize', updateMaxLength);
    return () => window.removeEventListener('resize', updateMaxLength);
  }, []);

  return (
    <div className="table-container" ref={tableRef}>
      <table style={{ width: '100%', tableLayout: 'fixed' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'center', width: '30%' }}>Filename</th>
            <th style={{ textAlign: 'center', width: '10%' }}>Size</th>
            <th style={{ textAlign: 'center', width: '12%' }}>Created</th>
            <th style={{ textAlign: 'center', width: '12%' }}>Modified</th>
            <th style={{ textAlign: 'center', width: '12%' }}>Added</th>
            <th style={{ textAlign: 'center', width: '12%' }}>Published</th>
            <th style={{ textAlign: 'center', width: '12%' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => {
            const createdTime = formatTimestampMultiLine(file.created);
            const modifiedTime = formatTimestampMultiLine(file.modified);
            const addedTime = formatTimestampMultiLine(file.added_at);
            const publishedTime = formatTimestampMultiLine(file.published_at);
            
            return (
              <tr key={file.name}>
                <td style={{ 
                  padding: '8px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }} title={file.name}>
                  {truncateMiddle(file.name, maxFilenameLength)}
                </td>
                <td style={{ textAlign: 'center', whiteSpace: 'nowrap', minWidth: '60px' }}>
                  {formatFileSize(file.size)}
                </td>
                <td style={{ textAlign: 'center', fontSize: '0.9em', padding: '4px' }}>
                  <div>{createdTime.date}</div>
                  <div style={{ fontSize: '0.85em', color: '#666' }}>{createdTime.time}</div>
                </td>
                <td style={{ textAlign: 'center', fontSize: '0.9em', padding: '4px' }}>
                  <div>{modifiedTime.date}</div>
                  <div style={{ fontSize: '0.85em', color: '#666' }}>{modifiedTime.time}</div>
                </td>
                <td style={{ textAlign: 'center', fontSize: '0.9em', padding: '4px' }}>
                  <div>{addedTime.date}</div>
                  <div style={{ fontSize: '0.85em', color: '#666' }}>{addedTime.time}</div>
                </td>
                <td style={{ textAlign: 'center', fontSize: '0.9em', padding: '4px' }}>
                  <div>{publishedTime.date}</div>
                  <div style={{ fontSize: '0.85em', color: '#666' }}>{publishedTime.time}</div>
                </td>
                <td style={{ textAlign: 'center' }}>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onUnpublish(file.name)}
                  >
                    Unpublish
                  </Button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default PublishedFilesTable;
