import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../common';
import { truncateMiddle, formatTimestampMultiLine } from '../../utils/formatters';
import './PublishedFilesTable.css';

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
      <table className="published-files-table">
        <thead>
          <tr>
            <th className="th-filename">Filename</th>
            <th className="th-size">Size</th>
            <th className="th-created">Created</th>
            <th className="th-modified">Modified</th>
            <th className="th-added">Added</th>
            <th className="th-published">Published</th>
            <th className="th-actions">Actions</th>
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
                <td className="td-timestamp">
                  <div>{publishedTime.date}</div>
                  <div className="td-timestamp-time">{publishedTime.time}</div>
                </td>
                <td className="td-actions">
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
