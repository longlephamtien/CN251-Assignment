import React, { useEffect, useRef } from 'react';
import '../../App.css';

/**
 * NotificationModal Component
 * A reusable modal for displaying notifications that matches the app theme
 * 
 * @param {Object} props
 * @param {string} props.type - Type of notification: 'success', 'error', 'info', 'warning'
 * @param {string} props.title - Title of the notification
 * @param {string} props.message - Message content
 * @param {function} props.onClose - Callback when modal is closed
 * @param {boolean} props.show - Whether to show the modal
 * @param {number} props.autoDismiss - Auto-dismiss after milliseconds (0 = no auto-dismiss)
 */
function NotificationModal({ 
  type = 'info', 
  title, 
  message, 
  onClose, 
  show = false,
  autoDismiss = 0 
}) {
  const timerRef = useRef(null);

  useEffect(() => {
    if (show && autoDismiss > 0) {
      // Auto-dismiss timer
      timerRef.current = setTimeout(() => {
        onClose();
      }, autoDismiss);

      return () => {
        if (timerRef.current) {
          clearTimeout(timerRef.current);
        }
      };
    }
  }, [show, autoDismiss, onClose]);

  if (!show) return null;

  const getIcon = () => {
    switch (type) {
      case 'success':
        return (
          <svg className="notification-icon success" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="notification-icon error" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="notification-icon warning" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        );
      case 'info':
      default:
        return (
          <svg className="notification-icon info" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  return (
    <div className="notification-overlay" onClick={onClose}>
      <div className={`notification-modal notification-${type}`} onClick={(e) => e.stopPropagation()}>
        <div className="notification-header">
          <div className="notification-icon-wrapper">
            {getIcon()}
          </div>
          <div className="notification-body">
            {title && <h4 className="notification-title">{title}</h4>}
            {message && <p className="notification-message">{message}</p>}
          </div>
          <button className="notification-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        {autoDismiss > 0 && (
          <div className="notification-progress-container">
            <div 
              className={`notification-progress-bar notification-progress-${type}`}
              style={{ 
                animation: `progressBar ${autoDismiss}ms linear forwards` 
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default NotificationModal;
