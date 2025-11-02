import React from 'react';
import { Button } from '../common';

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
      <div className="modal" onClick={(e) => e.stopPropagation()}>
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
                  style={{ width: '100%', marginBottom: '0.5rem' }}
                >
                  Browse Files
                </Button>
                {addForm.selectedFile && (
                  <div style={{
                    padding: '0.75rem',
                    backgroundColor: '#f0f0f0',
                    borderRadius: '4px',
                    fontSize: '0.9rem'
                  }}>
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

          {/* <div style={{
            padding: '0.75rem',
            marginBottom: '1rem',
            backgroundColor: '#d1ecf1',
            border: '1px solid #17a2b8',
            borderRadius: '4px',
            fontSize: '0.9rem'
          }}>
            <strong>ℹ️ Note:</strong> The file will stay in its original location. 
            Only metadata (name, path, size, created/modified times) will be tracked.
          </div> */}

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
                Exact Duplicate on Network
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
                  Recommendation: Download from network instead of uploading.
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
                checked={addForm.autoPublish}
                onChange={(e) => setAddForm({...addForm, autoPublish: e.target.checked})}
                style={{marginRight: '0.5rem'}}
              />
              <span>Publish to network immediately</span>
            </label>
            {/* <small className="text-gray">
              {addForm.autoPublish ? 
                'File will be shared with other users on the network' : 
                'File will be kept private. You can publish it later.'
              }
            </small> */}
          </div>
          
          <Button 
            type="submit" 
            variant={hasWarnings ? "warning" : "primary"} 
            style={{width: '100%'}}
          >
            {hasWarnings ? 'Add Anyway' : addForm.autoPublish ? 'Add & Publish' : 'Add File'}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default AddFileModal;
