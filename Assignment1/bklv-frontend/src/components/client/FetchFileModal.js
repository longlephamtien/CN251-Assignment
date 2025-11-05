import React, { useState, useEffect } from 'react';
import { Button, FormInput } from '../common';
import './FetchFileModal.css';

/**
 * FetchFileModal Component with integrated progress tracking
 * Shows duplicate warning, source validation, and real-time P2P fetch progress
 */
function FetchFileModal({ 
  file, 
  fetchForm, 
  setFetchForm, 
  onSubmit, 
  onClose,
  formatFileSize,
  localDuplicateInfo,
  validationWarning,
  fetchProgress,
  isFetching
}) {
  if (!file) return null;

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  // Format bytes to human-readable size
  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  // Format speed
  const formatSpeed = (bps) => {
    if (bps === 0) return '0 B/s';
    const kbps = bps / 1024;
    const mbps = kbps / 1024;
    
    if (mbps >= 1) {
      return `${mbps.toFixed(2)} MB/s`;
    } else if (kbps >= 1) {
      return `${kbps.toFixed(2)} KB/s`;
    } else {
      return `${bps.toFixed(0)} B/s`;
    }
  };

  // Format time (seconds to human-readable)
  const formatTime = (seconds) => {
    if (seconds < 60) {
      return `${Math.floor(seconds)}s`;
    } else if (seconds < 3600) {
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return `${mins}m ${secs}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${mins}m`;
    }
  };

  const hasLocalDuplicate = localDuplicateInfo?.exists;
  const filesAreSame = hasLocalDuplicate && 
                       localDuplicateInfo.local_file.size === file.size &&
                       Math.abs(localDuplicateInfo.local_file.modified - file.modified) < 2;

  return (
    <div className="modal-overlay" onClick={!isFetching ? onClose : undefined}>
      <div className="modal fetch-file-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">
            {isFetching ? 'Downloads' : 'Download File'}
          </h3>
          {!isFetching && (
            <button className="close-button" onClick={onClose}>×</button>
          )}
        </div>

        {/* Show file info when not fetching */}
        {!isFetching && (
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
                Owner: {file.owner_name} • Size: {formatFileSize(file.size)}
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
        )}

        {/* Show progress when fetching - Browser download tray style */}
        {isFetching && fetchProgress && (
          <div className="download-tray">
            {/* Download Item - Browser-style horizontal card */}
            <div 
              className="download-item"
              style={{
                '--progress-percent': fetchProgress.status === 'downloading' 
                  ? `${Math.min(fetchProgress.progress_percent || 0, 100)}%` 
                  : '100%'
              }}
            >
              {/* Left: File Icon */}
              <div className="download-item-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>

              {/* Center: File Info & Progress */}
              <div className="download-item-content">
                {/* File Name */}
                <div className="download-item-name">{fetchProgress.file_name}</div>
                
                {/* Source */}
                <div className="download-item-source">
                  From: {fetchProgress.peer_hostname || 'Unknown peer'}
                </div>

                {/* Transfer Stats - Only show during download */}
                {fetchProgress.status === 'downloading' && (
                  <div className="download-item-stats">
                    <span>
                      {formatBytes(fetchProgress.downloaded_size || 0)} / {formatBytes(fetchProgress.total_size || 0)}
                    </span>
                    {fetchProgress.speed_bps > 0 && (
                      <>
                        <span className="stats-separator">•</span>
                        <span>{formatSpeed(fetchProgress.speed_bps)}</span>
                      </>
                    )}
                    {fetchProgress.eta_seconds > 0 && fetchProgress.eta_seconds < 3600 && (
                      <>
                        <span className="stats-separator">•</span>
                        <span>{formatTime(fetchProgress.eta_seconds)} remaining</span>
                      </>
                    )}
                  </div>
                )}

                {/* Placeholder to maintain height when stats hidden */}
                {fetchProgress.status === 'completed' && (
                  <div className="download-item-stats" style={{ visibility: 'hidden' }}>
                    <span>Placeholder</span>
                  </div>
                )}

                {/* Error Status */}
                {fetchProgress.status === 'failed' && (
                  <div className="download-item-error-msg">
                    {fetchProgress.error_message || 'Download failed'}
                  </div>
                )}
              </div>

              {/* Right: Status Icon */}
              {fetchProgress.status === 'completed' && (
                <div className="download-item-status success">
                  <svg className="status-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                </div>
              )}

              {fetchProgress.status === 'failed' && (
                <div className="download-item-status error">
                  <svg className="status-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                  </svg>
                </div>
              )}
            </div>

            {/* Separator */}
            <div className="download-tray-separator"></div>

            {/* Close Button - Separated from download item */}
            <div className="download-tray-footer">
              {(fetchProgress.status === 'completed' || fetchProgress.status === 'failed') && (
                <Button 
                  onClick={onClose}
                  variant={fetchProgress.status === 'completed' ? 'primary' : 'secondary'}
                  className="download-close-button"
                >
                  {fetchProgress.status === 'completed' ? 'Done' : 'Close'}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default FetchFileModal;
