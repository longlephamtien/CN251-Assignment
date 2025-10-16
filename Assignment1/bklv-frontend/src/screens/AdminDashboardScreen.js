import React, { useState, useEffect } from 'react';
import config, { API_CONFIG } from '../config';
import { DashboardLayout, DashboardHeader, ContentCard } from '../layouts';
import { Modal, NotificationModal, ViewToggle, EmptyState, Button } from '../components/common';
import { 
  AdminLoginForm, 
  AdminStatsGrid, 
  ClientsTable, 
  ClientsGrid, 
  ClientFilesModal 
} from '../components/admin';
import { useNotification } from '../hooks/useNotification';
import { formatTimestamp, formatFileSize } from '../utils/formatters';

const API_BASE = API_CONFIG.adminBaseUrl + '/api';

function AdminDashboardScreen({ onBack }) {
  // Authentication states
  const [authenticated, setAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [loginForm, setLoginForm] = useState({
    username: '',
    password: ''
  });

  // Dashboard states
  const [stats, setStats] = useState(null);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [viewMode, setViewMode] = useState('list');
  const [selectedClient, setSelectedClient] = useState(null);

  // Notification hook
  const { notification, showNotification, closeNotification } = useNotification();

  // Handle admin login
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginForm)
      });

      const data = await response.json();

      if (data.success) {
        setToken(data.token);
        setAuthenticated(true);
        showNotification('success', 'Login Successful', 'Welcome to Admin Dashboard');
        fetchData();
      } else {
        showNotification('error', 'Login Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Connection Error', 'Failed to connect to server: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch registry data
  const fetchData = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/registry`);
      const data = await response.json();
      
      if (data.success) {
        setStats(data.stats);
        setClients(data.clients);
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
      showNotification('error', 'Error', 'Failed to fetch registry data');
    }
  };

  // Auto-refresh data
  useEffect(() => {
    if (authenticated) {
      fetchData();
      const interval = setInterval(fetchData, config.ui.refreshInterval);
      return () => clearInterval(interval);
    }
  }, [authenticated]);

  // Handle ping
  const handlePing = async (hostname) => {
    try {
      const response = await fetch(`${API_BASE}/admin/ping/${hostname}`);
      const data = await response.json();
      showNotification('info', 'Ping Result', `${hostname}: ${data.status}`);
    } catch (error) {
      showNotification('error', 'Ping Failed', error.message);
    }
  };

  // Handle discover
  const handleDiscover = async (hostname) => {
    try {
      const response = await fetch(`${API_BASE}/admin/discover/${hostname}`);
      const data = await response.json();
      
      if (data.success) {
        // Convert files object to array with metadata
        const filesArray = Object.entries(data.files || {}).map(([name, meta]) => ({
          name,
          size: meta.size,
          modified: meta.modified,
          published_at: meta.published_at,
          is_published: meta.is_published
        }));
        
        setSelectedClient({
          ...data,
          files: filesArray
        });
        showNotification('success', 'Discovery Complete', `Found ${filesArray.length} files from ${hostname}`);
      } else {
        showNotification('error', 'Discovery Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Error', 'Discovery failed: ' + error.message);
    }
  };

  // Login screen
  if (!authenticated) {
    return (
      <>
        <Modal
          show={true}
          onClose={onBack}
          title="Admin Login"
          maxWidth="400px"
        >
          <AdminLoginForm
            loginForm={loginForm}
            setLoginForm={setLoginForm}
            onSubmit={handleLogin}
            loading={loading}
            onBack={onBack}
          />
        </Modal>

        <NotificationModal
          show={notification.show}
          type={notification.type}
          title={notification.title}
          message={notification.message}
          onClose={closeNotification}
          autoDismiss={3000}
        />
      </>
    );
  }

  // Main dashboard
  return (
    <DashboardLayout>
      <DashboardHeader
        title="Admin Dashboard"
        subtitle="Server Management & Monitoring"
        onBackClick={onBack}
        backButtonText="Logout"
      />

      <div className="main-content">
        {/* Statistics */}
        <AdminStatsGrid stats={stats} />

        {/* Clients List */}
        <ContentCard
          title="Clients List"
          actions={
            <>
              <Button variant="primary" onClick={fetchData}>
                Refresh
              </Button>
              <ViewToggle viewMode={viewMode} onViewModeChange={setViewMode} />
            </>
          }
        >
          {clients.length === 0 ? (
            <EmptyState message="No clients connected" />
          ) : viewMode === 'list' ? (
            <ClientsTable
              clients={clients}
              onPing={handlePing}
              onDiscover={handleDiscover}
              formatTimestamp={formatTimestamp}
            />
          ) : (
            <ClientsGrid
              clients={clients}
              onPing={handlePing}
              onDiscover={handleDiscover}
              formatTimestamp={formatTimestamp}
            />
          )}
        </ContentCard>

        {/* Selected Client Details */}
        {selectedClient && (
          <ClientFilesModal
            client={selectedClient}
            onClose={() => setSelectedClient(null)}
            formatFileSize={formatFileSize}
          />
        )}
      </div>

      {/* Notification Modal */}
      <NotificationModal
        show={notification.show}
        type={notification.type}
        title={notification.title}
        message={notification.message}
        onClose={closeNotification}
        autoDismiss={3000}
      />
    </DashboardLayout>
  );
}

export default AdminDashboardScreen;
