import React from 'react';
import { Button, FormInput } from '../common';

/**
 * FetchFileModal Component
 */
function FetchFileModal({ 
  file, 
  fetchForm, 
  setFetchForm, 
  onSubmit, 
  onClose,
  formatFileSize 
}) {
  if (!file) return null;

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
              Size: {formatFileSize(file.size)} • 
              Owner: {file.owner_name}
            </small>
          </div>
          
          <div className="form-group">
            <label className="form-label">Download Option</label>
            <div>
              <label style={{display: 'flex', alignItems: 'center', cursor: 'pointer', marginBottom: '0.5rem'}}>
                <input
                  type="radio"
                  name="downloadOption"
                  checked={fetchForm.fetchToBackend}
                  onChange={() => setFetchForm({...fetchForm, fetchToBackend: true})}
                  style={{marginRight: '0.5rem'}}
                />
                <span>Download to backend repository</span>
              </label>
              <label style={{display: 'flex', alignItems: 'center', cursor: 'pointer'}}>
                <input
                  type="radio"
                  name="downloadOption"
                  checked={!fetchForm.fetchToBackend}
                  onChange={() => setFetchForm({...fetchForm, fetchToBackend: false})}
                  style={{marginRight: '0.5rem'}}
                />
                <span>Download to browser (choose location)</span>
              </label>
            </div>
          </div>
          
          {fetchForm.fetchToBackend && (
            <FormInput
              label="Custom Path (Optional)"
              type="text"
              value={fetchForm.customPath}
              onChange={(e) => setFetchForm({...fetchForm, customPath: e.target.value})}
              placeholder="Leave empty for default repository location"
              helpText="Enter full path on the server, e.g., /path/to/folder or ~/Documents"
            />
          )}
          
          <Button type="submit" variant="primary" style={{width: '100%'}}>
            {fetchForm.fetchToBackend ? 'Download to Backend' : 'Download to Browser'}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default FetchFileModal;
