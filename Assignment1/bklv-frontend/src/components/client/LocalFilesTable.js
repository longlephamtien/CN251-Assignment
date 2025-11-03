import React, { useState, useEffect, useRef } from 'react';
import { StatusBadge, Button } from '../common';
import { truncateMiddle, formatTimestampMultiLine } from '../../utils/formatters';
import './LocalFilesTable.css';

/**
 * LocalFilesTable Component - Display local files in table format
 */
function LocalFilesTable({ files, onPublish, onUnpublish, formatFileSize, formatTimestamp }) {
  const tableRef = useRef(null);
  const [maxFilenameLength, setMaxFilenameLength] = useState(50);

  useEffect(() => {
    const updateMaxLength = () => {
      if (tableRef.current) {
        const tableWidth = tableRef.current.offsetWidth;
        // Filename column is 30% of table width
        const filenameColumnWidth = tableWidth * 0.3;
        // Approximate: 1 character ≈ 8-9 pixels (depends on font)
        // Adjust this multiplier based on your font size
        const charWidth = 9;
        const calculatedMaxLength = Math.floor(filenameColumnWidth / charWidth);
        setMaxFilenameLength(Math.max(20, calculatedMaxLength)); // Minimum 20 chars
      }
    };

    updateMaxLength();
    window.addEventListener('resize', updateMaxLength);
    return () => window.removeEventListener('resize', updateMaxLength);
  }, []);

  return (
    <div className="table-container" ref={tableRef}>
      <table className="local-files-table">
        <thead>
          <tr>
            <th className="th-filename">Filename</th>
            <th className="th-size">Size</th>
            <th className="th-created">Created</th>
            <th className="th-modified">Modified</th>
            <th className="th-added">Added</th>
            <th className="th-status">Status</th>
            <th className="th-actions">Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => {
            const createdTime = formatTimestampMultiLine(file.created);
            const modifiedTime = formatTimestampMultiLine(file.modified);
            const addedTime = formatTimestampMultiLine(file.added_at);
            
            return (
              <tr key={file.name}>
                <td className="td-filename" title={file.name}>
                  {truncateMiddle(file.name, maxFilenameLength)}
                </td>
                <td className="td-size">
                  {formatFileSize(file.size)}
                </td>
                <td className="td-timestamp">
                  <div>{createdTime.date}</div>
                  <div className="td-timestamp-time">{createdTime.time}</div>
                </td>
                <td className="td-timestamp">
                  <div>{modifiedTime.date}</div>
                  <div className="td-timestamp-time">{modifiedTime.time}</div>
                </td>
                <td className="td-timestamp">
                  <div>{addedTime.date}</div>
                  <div className="td-timestamp-time">{addedTime.time}</div>
                </td>
                <td className="td-status">
                  {file.is_published ? (
                    <StatusBadge status="online">Published</StatusBadge>
                  ) : (
                    <StatusBadge status="offline">Local Only</StatusBadge>
                  )}
                </td>
                <td className="td-actions">
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
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default LocalFilesTable;
