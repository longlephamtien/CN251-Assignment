import React, { useState, useEffect } from 'react';
import config, { API_CONFIG } from '../config';
import { DashboardLayout, DashboardHeader, ContentCard } from '../layouts';
import { Modal, NotificationModal, ViewToggle, EmptyState, Button } from '../components/common';
import {
  ClientAuthForm,
  ClientTabs,
  LocalFilesTable,
  LocalFilesGrid,
  PublishedFilesTable,
  PublishedFilesGrid,
  NetworkFilesTable,
  NetworkFilesGrid,
  UploadFileModal,
  FetchFileModal
} from '../components/client';
import { useNotification } from '../hooks/useNotification';
import { formatTimestamp, formatFileSize } from '../utils/formatters';

const CLIENT_API_BASE = API_CONFIG.clientBaseUrl + '/api/client';

function ClientInterfaceScreen({ onBack }) {
  // Authentication states
  const [authMode, setAuthMode] = useState('login');
  const [authenticated, setAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(null);
  
  // Client states
  const [initialized, setInitialized] = useState(false);
  const [clientInfo, setClientInfo] = useState(null);
  const [activeTab, setActiveTab] = useState('local');
  const [viewMode, setViewMode] = useState('list');
  
  // Data states
  const [localFiles, setLocalFiles] = useState([]);
  const [publishedFiles, setPublishedFiles] = useState([]);
  const [networkFiles, setNetworkFiles] = useState([]);
  
  // Loading states
  const [loading, setLoading] = useState(false);
  
  // Modal states
  const [showAuthModal, setShowAuthModal] = useState(true);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [showFetchModal, setShowFetchModal] = useState(false);
  const [selectedNetworkFile, setSelectedNetworkFile] = useState(null);
  
  // Notification hook
  const { notification, showNotification, closeNotification } = useNotification();
  
  // Form states
  const [authForm, setAuthForm] = useState({
    username: '',
    password: '',
    display_name: '',
    server_ip: config.server.defaultHost,
    server_port: config.server.defaultPort
  });
  
  const [uploadForm, setUploadForm] = useState({
    selectedFile: null,
    autoPublish: false
  });
  
  const [fetchForm, setFetchForm] = useState({
    fetchToBackend: true,
    customPath: ''
  });

  // Handle authentication
  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const endpoint = authMode === 'login' ? '/login' : '/register';
      const response = await fetch(`${CLIENT_API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: authForm.username,
          password: authForm.password,
          display_name: authMode === 'register' ? authForm.display_name : undefined
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setToken(data.token);
        setCurrentUser(data.user);
        setAuthenticated(true);
        setShowAuthModal(false);
        showNotification('success', 'Success', `${authMode === 'login' ? 'Logged in' : 'Registered'} successfully!`);
        await initializeClient(data.user.username);
      } else {
        showNotification('error', 'Authentication Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Connection Error', 'Failed to connect to client API: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Initialize client session
  const initializeClient = async (username) => {
    try {
      const response = await fetch(`${CLIENT_API_BASE}/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: username,
          server_ip: authForm.server_ip,
          server_port: parseInt(authForm.server_port)
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setClientInfo(data.client);
        setInitialized(true);
        fetchAllData();
        showNotification('success', 'Connected', `Connected to P2P network as ${data.client.display_name}`);
      } else {
        showNotification('error', 'Initialization Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Connection Error', 'Failed to initialize client: ' + error.message);
    }
  };

  // Fetch all data
  const fetchAllData = async () => {
    await Promise.all([
      fetchLocalFiles(),
      fetchPublishedFiles(),
      fetchNetworkFiles()
    ]);
  };

  const fetchLocalFiles = async () => {
    try {
      const response = await fetch(`${CLIENT_API_BASE}/local-files`);
      const data = await response.json();
      if (data.success) {
        setLocalFiles(data.files);
      }
    } catch (error) {
      console.error('Failed to fetch local files:', error);
    }
  };

  const fetchPublishedFiles = async () => {
    try {
      const response = await fetch(`${CLIENT_API_BASE}/published-files`);
      const data = await response.json();
      if (data.success) {
        setPublishedFiles(data.files);
      }
    } catch (error) {
      console.error('Failed to fetch published files:', error);
    }
  };

  const fetchNetworkFiles = async () => {
    try {
      const response = await fetch(`${CLIENT_API_BASE}/network-files`);
      const data = await response.json();
      if (data.success) {
        setNetworkFiles(data.files);
      }
    } catch (error) {
      console.error('Failed to fetch network files:', error);
    }
  };

  // Auto-refresh network files
  useEffect(() => {
    if (initialized) {
      const interval = setInterval(fetchNetworkFiles, config.ui.refreshInterval);
      return () => clearInterval(interval);
    }
  }, [initialized]);

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadForm({
        ...uploadForm,
        selectedFile: file
      });
    }
  };

  // Upload and optionally publish file
  const handleUploadFile = async (e) => {
    e.preventDefault();
    
    if (!uploadForm.selectedFile) {
      showNotification('warning', 'No File Selected', 'Please select a file to upload');
      return;
    }
    
    try {
      const formData = new FormData();
      formData.append('file', uploadForm.selectedFile);
      formData.append('auto_publish', uploadForm.autoPublish);
      
      showNotification('info', 'Uploading', `Uploading ${uploadForm.selectedFile.name}...`);
      
      const response = await fetch(`${CLIENT_API_BASE}/upload`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification('success', 'Success', data.message);
        setShowPublishModal(false);
        setUploadForm({ selectedFile: null, autoPublish: false });
        setTimeout(() => {
          fetchAllData();
        }, 1000);
      } else {
        showNotification('error', 'Upload Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Error', 'Failed to upload: ' + error.message);
    }
  };

  // Quick publish for already tracked files
  const handleQuickPublish = async (file) => {
    try {
      showNotification('info', 'Publishing', `Publishing ${file.name}...`);
      
      const response = await fetch(`${CLIENT_API_BASE}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fname: file.name
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification('success', 'Published', `File "${file.name}" published to network!`);
        setTimeout(() => {
          fetchLocalFiles();
          fetchPublishedFiles();
        }, 1000);
      } else {
        showNotification('error', 'Publish Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Error', 'Failed to publish: ' + error.message);
    }
  };

  // Unpublish file
  const handleUnpublish = async (fname) => {
    try {
      const response = await fetch(`${CLIENT_API_BASE}/unpublish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fname })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification('success', 'Unpublished', `File "${fname}" removed from network`);
        setTimeout(() => {
          fetchLocalFiles();
          fetchPublishedFiles();
        }, 1000);
      } else {
        showNotification('error', 'Unpublish Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Error', 'Failed to unpublish: ' + error.message);
    }
  };

  // Fetch file from network
  const handleFetchFile = (file) => {
    setSelectedNetworkFile(file);
    setFetchForm({ fetchToBackend: true, customPath: '' });
    setShowFetchModal(true);
  };

  const handleFetchConfirm = async (e) => {
    e.preventDefault();
    
    try {
      if (fetchForm.fetchToBackend) {
        showNotification('info', 'Downloading', `Downloading ${selectedNetworkFile.name} to backend...`);
        
        const response = await fetch(`${CLIENT_API_BASE}/fetch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fname: selectedNetworkFile.name,
            save_path: fetchForm.customPath || null
          })
        });
        
        const data = await response.json();
        
        if (data.success) {
          showNotification('success', 'Download Started', `Downloading to ${data.save_path}`);
          setShowFetchModal(false);
          setTimeout(() => {
            fetchLocalFiles();
          }, 3000);
        } else {
          showNotification('error', 'Download Failed', data.error);
        }
      } else {
        showNotification('info', 'Downloading', `Fetching ${selectedNetworkFile.name} to browser...`);
        
        const fetchResponse = await fetch(`${CLIENT_API_BASE}/fetch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            fname: selectedNetworkFile.name,
            save_path: null
          })
        });
        
        const fetchData = await fetchResponse.json();
        
        if (fetchData.success) {
          setTimeout(async () => {
            const downloadUrl = `${CLIENT_API_BASE}/download/${encodeURIComponent(selectedNetworkFile.name)}`;
            const link = document.createElement('a');
            link.href = downloadUrl;
            link.download = selectedNetworkFile.name;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showNotification('success', 'Download Started', 'File download started to your browser');
            setShowFetchModal(false);
          }, 2000);
        } else {
          showNotification('error', 'Download Failed', fetchData.error);
        }
      }
    } catch (error) {
      showNotification('error', 'Error', 'Failed to fetch: ' + error.message);
    }
  };

  // Render authentication modal
  if (!authenticated) {
    return (
      <>
        <Modal
          show={true}
          onClose={onBack}
          title={authMode === 'login' ? 'Login to P2P Network' : 'Register New Account'}
          maxWidth="450px"
        >
          <ClientAuthForm
            authMode={authMode}
            authForm={authForm}
            setAuthForm={setAuthForm}
            onSubmit={handleAuth}
            loading={loading}
            onToggleMode={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}
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

  // Main client interface
  return (
    <DashboardLayout>
      <DashboardHeader
        title={clientInfo?.display_name || 'Client Interface'}
        subtitle={`@${clientInfo?.username} • Port ${clientInfo?.port}`}
        onBackClick={onBack}
        backButtonText="Disconnect"
      />

      <div className="main-content">
        <ClientTabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          counts={{
            local: localFiles.length,
            published: publishedFiles.length,
            network: networkFiles.length
          }}
        />

        <ContentCard
          title={
            activeTab === 'local' ? 'Your Files' :
            activeTab === 'published' ? 'Published Files' :
            'Network Files'
          }
          actions={
            <>
              {activeTab === 'local' && (
                <Button
                  variant="primary"
                  onClick={() => setShowPublishModal(true)}
                  style={{ marginRight: '0.5rem' }}
                >
                  + Upload File
                </Button>
              )}
              <Button variant="primary" onClick={fetchAllData}>
                Refresh
              </Button>
              <ViewToggle viewMode={viewMode} onViewModeChange={setViewMode} />
            </>
          }
        >
          {/* Local Files Tab */}
          {activeTab === 'local' && (
            localFiles.length === 0 ? (
              <EmptyState message="No files tracked yet" />
            ) : viewMode === 'list' ? (
              <LocalFilesTable
                files={localFiles}
                onPublish={handleQuickPublish}
                onUnpublish={handleUnpublish}
                formatFileSize={formatFileSize}
                formatTimestamp={formatTimestamp}
              />
            ) : (
              <LocalFilesGrid
                files={localFiles}
                onPublish={handleQuickPublish}
                onUnpublish={handleUnpublish}
                formatFileSize={formatFileSize}
                formatTimestamp={formatTimestamp}
              />
            )
          )}

          {/* Published Files Tab */}
          {activeTab === 'published' && (
            publishedFiles.length === 0 ? (
              <EmptyState message="No files published yet" />
            ) : viewMode === 'list' ? (
              <PublishedFilesTable
                files={publishedFiles}
                onUnpublish={handleUnpublish}
                formatFileSize={formatFileSize}
                formatTimestamp={formatTimestamp}
              />
            ) : (
              <PublishedFilesGrid
                files={publishedFiles}
                onUnpublish={handleUnpublish}
                formatFileSize={formatFileSize}
                formatTimestamp={formatTimestamp}
              />
            )
          )}

          {/* Network Files Tab */}
          {activeTab === 'network' && (
            networkFiles.length === 0 ? (
              <EmptyState message="No files on network" />
            ) : viewMode === 'list' ? (
              <NetworkFilesTable
                files={networkFiles}
                onDownload={handleFetchFile}
                formatFileSize={formatFileSize}
              />
            ) : (
              <NetworkFilesGrid
                files={networkFiles}
                onDownload={handleFetchFile}
                formatFileSize={formatFileSize}
              />
            )
          )}
        </ContentCard>
      </div>

      {/* Upload/Publish Modal */}
      {showPublishModal && (
        <UploadFileModal
          uploadForm={uploadForm}
          setUploadForm={setUploadForm}
          onSubmit={handleUploadFile}
          onFileSelect={handleFileSelect}
          onClose={() => setShowPublishModal(false)}
          formatFileSize={formatFileSize}
        />
      )}

      {/* Fetch Modal */}
      {showFetchModal && selectedNetworkFile && (
        <FetchFileModal
          file={selectedNetworkFile}
          fetchForm={fetchForm}
          setFetchForm={setFetchForm}
          onSubmit={handleFetchConfirm}
          onClose={() => setShowFetchModal(false)}
          formatFileSize={formatFileSize}
        />
      )}

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

export default ClientInterfaceScreen;
