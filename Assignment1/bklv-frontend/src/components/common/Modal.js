import React from 'react';

/**
 * Generic Modal Component
 */
function Modal({ 
  show, 
  onClose, 
  title, 
  children, 
  maxWidth = '600px',
  showCloseButton = true 
}) {
  if (!show) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div 
        className="modal" 
        style={{ maxWidth }} 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <h3 className="modal-title">{title}</h3>
          {showCloseButton && (
            <button className="close-button" onClick={onClose}>×</button>
          )}
        </div>
        {children}
      </div>
    </div>
  );
}

export default Modal;
