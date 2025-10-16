import React from 'react';
import { StatusBadge, Button } from '../common';

/**
 * LocalFilesTable Component - Display local files in table format
 */
function LocalFilesTable({ files, onPublish, onUnpublish, formatFileSize, formatTimestamp }) {
  return (
    <div className="table-container">
      <table>
        <thead>
          <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Modified</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.name}>
              <td>{file.name}</td>
              <td>{formatFileSize(file.size)}</td>
              <td className="text-small">{formatTimestamp(file.modified)}</td>
              <td>
                {file.is_published ? (
                  <StatusBadge status="online">Published</StatusBadge>
                ) : (
                  <StatusBadge status="offline">Local Only</StatusBadge>
                )}
              </td>
              <td>
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
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default LocalFilesTable;
