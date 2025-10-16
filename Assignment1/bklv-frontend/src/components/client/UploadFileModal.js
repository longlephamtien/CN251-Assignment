import React from 'react';
import { Button } from '../common';

/**
 * UploadFileModal Component
 */
function UploadFileModal({ 
  uploadForm, 
  setUploadForm, 
  onSubmit, 
  onFileSelect, 
  onClose,
  formatFileSize 
}) {
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
          <Button type="submit" variant="primary" style={{width: '100%'}}>
            Upload File
          </Button>
        </form>
      </div>
    </div>
  );
}

export default UploadFileModal;
