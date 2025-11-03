import React from 'react';
import './AdminStatsGrid.css';

/**
 * AdminStatsGrid Component - Display admin statistics
 */
function AdminStatsGrid({ stats }) {
  return (
    <div className="stats-grid admin-stats-grid">
      <div className="stat-card">
        <div className="stat-label">Total Registered</div>
        <div className="stat-value">{stats?.total_clients || 0}</div>
        <div className="stat-description">All registered users</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Online Now</div>
        <div className="stat-value online">
          {stats?.active_clients || 0}
        </div>
        <div className="stat-description">Currently connected</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Offline</div>
        <div className="stat-value offline">
          {(stats?.total_clients || 0) - (stats?.active_clients || 0)}
        </div>
        <div className="stat-description">Not connected</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Shared Files</div>
        <div className="stat-value">{stats?.total_files || 0}</div>
        <div className="stat-description">Total files online</div>
      </div>
    </div>
  );
}

export default AdminStatsGrid;
