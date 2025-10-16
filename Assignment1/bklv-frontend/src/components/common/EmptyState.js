import React from 'react';

/**
 * EmptyState Component - Display when no data is available
 */
function EmptyState({ message, icon }) {
  return (
    <div className="empty-state">
      {icon && <div className="empty-state-icon">{icon}</div>}
      <p className="empty-state-text">{message}</p>
    </div>
  );
}

export default EmptyState;
