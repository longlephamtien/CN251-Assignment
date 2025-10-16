import React from 'react';

/**
 * DashboardHeader Component - Header for dashboard screens
 */
function DashboardHeader({ title, subtitle, onBackClick, backButtonText = 'Back' }) {
  return (
    <div className="header">
      <div className="header-content">
        <div>
          <h1 className="header-title">{title}</h1>
          {subtitle && <p className="header-subtitle">{subtitle}</p>}
        </div>
        {onBackClick && (
          <button className="back-button" onClick={onBackClick}>
            {backButtonText}
          </button>
        )}
      </div>
    </div>
  );
}

export default DashboardHeader;
