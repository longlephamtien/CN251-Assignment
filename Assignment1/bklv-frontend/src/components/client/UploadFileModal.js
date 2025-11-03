import React from 'react';
import { Button } from '../common';
import './UploadFileModal.css';

/**
 * UploadFileModal Component - Track files by path (no upload)
 */
function UploadFileModal({ 
  uploadForm, 
  setUploadForm, 
  onSubmit, 
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
      <div className="modal upload-file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Add File to Tracking</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label className="form-label">File Path</label>
            <input
              type="text"
              className="form-input"
              value={uploadForm.filePath || ''}
              onChange={(e) => setUploadForm({...uploadForm, filePath: e.target.value})}
              placeholder="/path/to/file.txt or ~/Documents/file.txt"
              required
            />
            <small className="text-gray">
              Enter the full path to a file on your computer. The file will NOT be copied.
            </small>
          </div>

          <div className="info-box">
            <strong>ℹ️ Note:</strong> The file will stay in its original location. 
            Only metadata will be tracked by the system.
          </div>

          {/* Local Duplicate Warning */}
          {localDuplicateInfo?.exists && (
            <div className="warning-box">
              <div className="warning-title">
                Local File Exists
              </div>
              <div className="warning-content">
                A file with this name already exists in your repository:
                <ul className="warning-list">
                  <li>Size: {formatFileSize(localDuplicateInfo.local_file.size)}</li>
                  <li>Modified: {formatTimestamp(localDuplicateInfo.local_file.modified)}</li>
                  <li>Status: {localDuplicateInfo.local_file.is_published ? 'Published' : 'Not published'}</li>
                </ul>
                <div className="warning-note">
                  Uploading will overwrite the existing file.
                </div>
              </div>
            </div>
          )}

          {/* Network Exact Duplicate Warning */}
          {duplicateInfo?.has_exact_duplicate && (
            <div className="error-box">
              <div className="error-title">
                🚫 Exact Duplicate on Network
              </div>
              <div className="error-content">
                This file (same name, size, and modified time) already exists on the network:
                <ul className="warning-list">
                  {duplicateInfo.exact_matches.map((match, idx) => (
                    <li key={idx}>
                      <strong>{match.hostname}</strong> - {formatFileSize(match.size)}, 
                      Modified: {formatTimestamp(match.modified)}
                    </li>
                  ))}
                </ul>
                <div className="error-recommendation">
                  💡 Recommendation: Download from network instead of uploading.
                </div>
              </div>
            </div>
          )}

          {/* Network Partial Duplicate Warning */}
          {!duplicateInfo?.has_exact_duplicate && duplicateInfo?.has_partial_duplicate && (
            <div className="warning-box">
              <div className="warning-title">
                Similar File on Network
              </div>
              <div className="warning-content">
                A file with the same name but different metadata exists:
                <ul className="warning-list">
                  {duplicateInfo.partial_matches.map((match, idx) => (
                    <li key={idx}>
                      <strong>{match.hostname}</strong> - {formatFileSize(match.size)}, 
                      Modified: {formatTimestamp(match.modified)}
                    </li>
                  ))}
                </ul>
                <div className="warning-note">
                  This appears to be a different version of the file.
                </div>
              </div>
            </div>
          )}

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={uploadForm.autoPublish}
                onChange={(e) => setUploadForm({...uploadForm, autoPublish: e.target.checked})}
                className="checkbox-input"
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
            className="submit-button"
          >
            {hasWarnings ? 'Add Anyway' : uploadForm.autoPublish ? 'Add & Publish' : 'Add File'}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default UploadFileModal;
