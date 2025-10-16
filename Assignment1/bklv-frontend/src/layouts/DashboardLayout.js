import React from 'react';

/**
 * DashboardLayout Component - Common layout for dashboard screens
 */
function DashboardLayout({ children }) {
  return (
    <div className="dashboard">
      {children}
    </div>
  );
}

export default DashboardLayout;
