import React from 'react';
import { Button } from '../common';
import './AddFileModal.css';

/**
 * AddFileModal Component - Add files to tracking by selecting from file browser
 */
function AddFileModal({ 
  addForm, 
  setAddForm, 
  onSubmit,
  onFileSelect,
  onElectronFileSelect, 
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

  // Check if running in Electron
  const isElectron = window.electronAPI?.isElectron || false;

  // Handle Electron file dialog
  const handleElectronFileSelect = async () => {
    if (onElectronFileSelect) {
      await onElectronFileSelect();
    } else {
      // Fallback if no handler provided
      if (!window.electronAPI) {
        console.error('Electron API not available');
        return;
      }

      const result = await window.electronAPI.openFileDialog();
      
      if (!result.canceled) {
        // Create a file-like object with the path information
        const fileInfo = {
          name: result.fileName,
          size: result.fileSize,
          type: result.fileType,
          path: result.filePath,
          modified: result.modified,
          created: result.created
        };
        
        setAddForm({ ...addForm, selectedFile: fileInfo });
      }
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal add-file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">Add File to Tracking</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        <form onSubmit={onSubmit}>
          <div className="form-group">
            <label className="form-label">Select File</label>
            {isElectron ? (
              // Electron: Use native file dialog button
              <>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleElectronFileSelect}
                  className="browse-button"
                >
                  Browse Files
                </Button>
                {addForm.selectedFile && (
                  <div className="file-info">
                    <div><strong>Selected:</strong> {addForm.selectedFile.name}</div>
                    <div><strong>Size:</strong> {formatFileSize(addForm.selectedFile.size)}</div>
                    <div><strong>Path:</strong> {addForm.selectedFile.path}</div>
                  </div>
                )}
              </>
            ) : (
              // Browser: Use standard file input
              <>
                <input
                  type="file"
                  className="form-input"
                  onChange={onFileSelect}
                  required
                />
                {addForm.selectedFile && (
                  <small className="text-gray">
                    Selected: {addForm.selectedFile.name} ({formatFileSize(addForm.selectedFile.size)})
                    <br />
                    Path will be read from your system
                  </small>
                )}
              </>
            )}
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
                Exact Duplicate on Network
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
                  Recommendation: Download from network instead of uploading.
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
                checked={addForm.autoPublish}
                onChange={(e) => setAddForm({...addForm, autoPublish: e.target.checked})}
                className="checkbox-input"
              />
              <span>Publish to network immediately</span>
            </label>
          </div>
          
          <Button 
            type="submit" 
            variant={hasWarnings ? "warning" : "primary"} 
            className="submit-button"
          >
            {hasWarnings ? 'Add Anyway' : addForm.autoPublish ? 'Add & Publish' : 'Add File'}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default AddFileModal;
