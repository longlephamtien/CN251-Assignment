import React from 'react';
import { StatusBadge, Button } from '../common';

/**
 * PublishedFilesTable Component
 */
function PublishedFilesTable({ files, onUnpublish, formatFileSize, formatTimestamp }) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Published At</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.name}>
              <td>{file.name}</td>
              <td>{formatFileSize(file.size)}</td>
              <td className="text-small">{formatTimestamp(file.published_at)}</td>
              <td>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onUnpublish(file.name)}
                >
                  Unpublish
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default PublishedFilesTable;
