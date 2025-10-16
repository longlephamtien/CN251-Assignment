import React from 'react';

/**
 * ContentCard Component - Card wrapper for content sections
 */
function ContentCard({ title, actions, children }) {
  return (
    <div className="content-card">
      {(title || actions) && (
        <div className="card-header">
          {title && <h2 className="card-title">{title}</h2>}
          {actions && <div className="card-actions">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export default ContentCard;
