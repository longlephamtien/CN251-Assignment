import React from 'react';

/**
 * LandingScreen - Main landing page
 */
function LandingScreen({ setMode }) {
  return (
    <div className="landing">
      <div className="landing-content">
        <h1 className="landing-title">BKLV File Sharing</h1>
        <p className="landing-subtitle">
          Peer-to-peer file sharing system with centralized discovery
        </p>
        <div className="landing-buttons">
          <div className="landing-card" onClick={() => setMode('admin')}>
            <h3>Admin Dashboard</h3>
            <p>Monitor and manage the central server</p>
          </div>
          <div className="landing-card" onClick={() => setMode('client')}>
            <h3>Client Interface</h3>
            <p>Share and download files with other users</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LandingScreen;
