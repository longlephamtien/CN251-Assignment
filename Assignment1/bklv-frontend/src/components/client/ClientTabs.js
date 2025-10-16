import React from 'react';

/**
 * ClientTabs Component - Navigation tabs for client interface
 */
function ClientTabs({ activeTab, onTabChange, counts }) {
  return (
    <div className="tabs">
      <button
        className={`tab ${activeTab === 'local' ? 'active' : ''}`}
        onClick={() => onTabChange('local')}
      >
        Your Files ({counts.local || 0})
      </button>
      <button
        className={`tab ${activeTab === 'published' ? 'active' : ''}`}
        onClick={() => onTabChange('published')}
      >
        Published ({counts.published || 0})
      </button>
      <button
        className={`tab ${activeTab === 'network' ? 'active' : ''}`}
        onClick={() => onTabChange('network')}
      >
        Network ({counts.network || 0})
      </button>
    </div>
  );
}

export default ClientTabs;
