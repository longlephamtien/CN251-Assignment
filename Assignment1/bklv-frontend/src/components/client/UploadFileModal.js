import React from 'react';
import { Button } from '../common';

/**
 * UploadFileModal Component with duplicate file warnings
 */
function UploadFileModal({ 
  uploadForm, 
  setUploadForm, 
  onSubmit, 
  onFileSelect, 
  onClose,
  formatFileSize,
  duplicateInfo,
  localDuplicateInfo
}) {
  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const hasWarnings = duplicateInfo?.has_exact_duplicate || 
                      duplicateInfo?.has_partial_duplicate ||
                      localDuplicateInfo?.exists;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Upload File</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label className="form-label">Select File</label>
            <input
              type="file"
              className="form-input"
              onChange={onFileSelect}
              required
            />
            {uploadForm.selectedFile && (
              <small className="text-gray">
                Selected: {uploadForm.selectedFile.name} ({formatFileSize(uploadForm.selectedFile.size)})
              </small>
            )}
          </div>

          {/* Local Duplicate Warning */}
          {localDuplicateInfo?.exists && (
            <div style={{
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '4px'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#856404' }}>
                Local File Exists
              </div>
              <div style={{ fontSize: '0.9rem', color: '#856404' }}>
                A file with this name already exists in your repository:
                <ul style={{ marginTop: '0.5rem', marginBottom: 0, paddingLeft: '1.5rem' }}>
                  <li>Size: {formatFileSize(localDuplicateInfo.local_file.size)}</li>
                  <li>Modified: {formatTimestamp(localDuplicateInfo.local_file.modified)}</li>
                  <li>Status: {localDuplicateInfo.local_file.is_published ? 'Published' : 'Not published'}</li>
                </ul>
                <div style={{ marginTop: '0.5rem', fontStyle: 'italic' }}>
                  Uploading will overwrite the existing file.
                </div>
              </div>
            </div>
          )}

          {/* Network Exact Duplicate Warning */}
          {duplicateInfo?.has_exact_duplicate && (
            <div style={{
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: '#f8d7da',
              border: '1px solid #dc3545',
              borderRadius: '4px'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#721c24' }}>
                🚫 Exact Duplicate on Network
              </div>
              <div style={{ fontSize: '0.9rem', color: '#721c24' }}>
                This file (same name, size, and modified time) already exists on the network:
                <ul style={{ marginTop: '0.5rem', marginBottom: 0, paddingLeft: '1.5rem' }}>
                  {duplicateInfo.exact_matches.map((match, idx) => (
                    <li key={idx}>
                      <strong>{match.hostname}</strong> - {formatFileSize(match.size)}, 
                      Modified: {formatTimestamp(match.modified)}
                    </li>
                  ))}
                </ul>
                <div style={{ marginTop: '0.5rem', fontWeight: 'bold' }}>
                  💡 Recommendation: Download from network instead of uploading.
                </div>
              </div>
            </div>
          )}

          {/* Network Partial Duplicate Warning */}
          {!duplicateInfo?.has_exact_duplicate && duplicateInfo?.has_partial_duplicate && (
            <div style={{
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: '#fff3cd',
              border: '1px solid #ffc107',
              borderRadius: '4px'
            }}>
              <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', color: '#856404' }}>
                Similar File on Network
              </div>
              <div style={{ fontSize: '0.9rem', color: '#856404' }}>
                A file with the same name but different metadata exists:
                <ul style={{ marginTop: '0.5rem', marginBottom: 0, paddingLeft: '1.5rem' }}>
                  {duplicateInfo.partial_matches.map((match, idx) => (
                    <li key={idx}>
                      <strong>{match.hostname}</strong> - {formatFileSize(match.size)}, 
                      Modified: {formatTimestamp(match.modified)}
                    </li>
                  ))}
                </ul>
                <div style={{ marginTop: '0.5rem' }}>
                  This appears to be a different version of the file.
                </div>
              </div>
            </div>
          )}

          <div className="form-group">
            <label style={{display: 'flex', alignItems: 'center', cursor: 'pointer'}}>
              <input
                type="checkbox"
                checked={uploadForm.autoPublish}
                onChange={(e) => setUploadForm({...uploadForm, autoPublish: e.target.checked})}
                style={{marginRight: '0.5rem'}}
              />
              <span>Publish to network immediately</span>
            </label>
            <small className="text-gray">
              {uploadForm.autoPublish ? 
                'File will be shared with other users on the network' : 
                'File will be kept private. You can publish it later.'
              }
            </small>
          </div>
          
          <Button 
            type="submit" 
            variant={hasWarnings ? "warning" : "primary"} 
            style={{width: '100%'}}
          >
            {hasWarnings ? 'Upload Anyway' : 'Upload File'}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default UploadFileModal;
