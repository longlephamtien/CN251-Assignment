import React from 'react';
import { Button, FormInput } from '../common';
import './FetchFileModal.css';

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
      <div className="modal fetch-file-modal" onClick={(e) => e.stopPropagation()}>
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
              Owner: {file.owner_name}
            </small>
          </div>

          {/* Source File Validation Warning */}
          {validationWarning && (
            <div className="error-box">
              <div className="error-title">
                Source File May Be Unavailable
              </div>
              <div className="error-content">
                {validationWarning}
                <div className="error-note">
                  Download may fail if the file has been moved or deleted at the source.
                </div>
              </div>
            </div>
          )}

          {/* Local Duplicate Warning */}
          {hasLocalDuplicate && (
            <div className={filesAreSame ? "info-box" : "warning-box"}>
              <div className={filesAreSame ? "info-title" : "warning-title"}>
                {filesAreSame ? 'File Already Downloaded' : 'Local File Exists'}
              </div>
              <div className={filesAreSame ? "info-content" : "warning-content"}>
                You already have this file in your repository:
                <div className="file-details">
                  <strong>Local file:</strong>
                  <ul className="file-details-list">
                    <li>Size: {formatFileSize(localDuplicateInfo.local_file.size)}</li>
                    <li>Modified: {formatTimestamp(localDuplicateInfo.local_file.modified)}</li>
                  </ul>
                </div>
                <div className="file-details">
                  <strong>Network file:</strong>
                  <ul className="file-details-list">
                    <li>Size: {formatFileSize(file.size)}</li>
                    <li>Modified: {formatTimestamp(file.modified)}</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
          
          <Button 
            type="submit" 
            variant={hasLocalDuplicate && !filesAreSame ? "warning" : "primary"}
            className="submit-button"
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
