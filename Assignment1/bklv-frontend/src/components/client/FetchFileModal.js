import React from 'react';
import { Button, FormInput } from '../common';

/**
 * FetchFileModal Component with duplicate warning and source validation
 */
function FetchFileModal({ 
  file, 
  fetchForm, 
  setFetchForm, 
  onSubmit, 
  onClose,
  formatFileSize,
  localDuplicateInfo,
  validationWarning
}) {
  if (!file) return null;

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const hasLocalDuplicate = localDuplicateInfo?.exists;
  const filesAreSame = hasLocalDuplicate && 
                       localDuplicateInfo.local_file.size === file.size &&
                       Math.abs(localDuplicateInfo.local_file.modified - file.modified) < 2;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Download File</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label className="form-label">File</label>
            <input
              type="text"
              className="form-input"
              value={file.name}
              disabled
            />
            <small className="text-gray">
              {/* Size: {formatFileSize(file.size)} • 
              Modified: {formatTimestamp(file.modified)} • */}
              Owner: {file.owner_name}
            </small>
          </div>

          {/* Source File Validation Warning */}
          {validationWarning && (
            <div style={{
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: '#f8d7da',
              border: '1px solid #dc3545',
              borderRadius: '4px'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#721c24' }}>
                Source File May Be Unavailable
              </div>
              <div style={{ fontSize: '0.9rem', color: '#721c24' }}>
                {validationWarning}
                <div style={{ marginTop: '0.5rem', fontStyle: 'italic' }}>
                  Download may fail if the file has been moved or deleted at the source.
                </div>
              </div>
            </div>
          )}

          {/* Local Duplicate Warning */}
          {hasLocalDuplicate && (
            <div style={{
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: filesAreSame ? '#d1ecf1' : '#fff3cd',
              border: `1px solid ${filesAreSame ? '#17a2b8' : '#ffc107'}`,
              borderRadius: '4px'
            }}>
              <div style={{ 
                fontWeight: 'bold', 
                marginBottom: '0.5rem', 
                color: filesAreSame ? '#0c5460' : '#856404' 
              }}>
                {filesAreSame ? 'File Already Downloaded' : 'Local File Exists'}
              </div>
              <div style={{ 
                fontSize: '0.9rem', 
                color: filesAreSame ? '#0c5460' : '#856404' 
              }}>
                You already have this file in your repository:
                <div style={{ marginTop: '0.5rem' }}>
                  <strong>Local file:</strong>
                  <ul style={{ marginTop: '0.25rem', marginBottom: 0, paddingLeft: '1.5rem' }}>
                    <li>Size: {formatFileSize(localDuplicateInfo.local_file.size)}</li>
                    <li>Modified: {formatTimestamp(localDuplicateInfo.local_file.modified)}</li>
                  </ul>
                </div>
                <div style={{ marginTop: '0.5rem' }}>
                  <strong>Network file:</strong>
                  <ul style={{ marginTop: '0.25rem', marginBottom: 0, paddingLeft: '1.5rem' }}>
                    <li>Size: {formatFileSize(file.size)}</li>
                    <li>Modified: {formatTimestamp(file.modified)}</li>
                  </ul>
                </div>
                {/* {filesAreSame ? (
                  <div style={{ marginTop: '0.5rem', fontWeight: 'bold' }}>
                    Files appear identical
                  </div>
                ) : (
                  <div style={{ marginTop: '0.5rem', fontWeight: 'bold' }}>
                    Files have different content. Downloading will overwrite your local file.
                  </div>
                )} */}
              </div>
            </div>
          )}
          
          <Button 
            type="submit" 
            variant={hasLocalDuplicate && !filesAreSame ? "warning" : "primary"}
            style={{width: '100%'}}
          >
            {filesAreSame  ? 
              'Download Anyway' : 
              'Download'
            }
          </Button>
        </form>
      </div>
    </div>
  );
}

export default FetchFileModal;
