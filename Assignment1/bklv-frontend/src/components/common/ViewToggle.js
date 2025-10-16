import React from 'react';

/**
 * ViewToggle Component - Switch between list and grid views
 */
function ViewToggle({ viewMode, onViewModeChange }) {
  return (
    <div className="view-toggle">
      <button
        className={viewMode === 'list' ? 'active' : ''}
        onClick={() => onViewModeChange('list')}
      >
        List
      </button>
      <button
        className={viewMode === 'grid' ? 'active' : ''}
        onClick={() => onViewModeChange('grid')}
      >
        Grid
      </button>
    </div>
  );
}

export default ViewToggle;
