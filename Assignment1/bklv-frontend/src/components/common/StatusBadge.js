import React from 'react';

/**
 * StatusBadge Component - Display status with colored badge
 */
function StatusBadge({ status, children }) {
  return (
    <span className={`status-badge status-${status}`}>
      {children || status}
    </span>
  );
}

export default StatusBadge;
