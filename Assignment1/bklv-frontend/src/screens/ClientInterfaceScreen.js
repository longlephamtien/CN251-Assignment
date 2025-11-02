import React, { useState, useEffect } from 'react';
import config from '../config';
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

function ClientInterfaceScreen({ onBack }) {
  // Authentication states
  const [authMode, setAuthMode] = useState('login');
  const [authenticated, setAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(null);
  
  // API configuration based on user input
  const [apiBaseUrl, setApiBaseUrl] = useState('http://localhost:5501/api/client');
  
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

  // Duplicate detection states
  const [uploadDuplicateInfo, setUploadDuplicateInfo] = useState(null);
  const [uploadLocalDuplicateInfo, setUploadLocalDuplicateInfo] = useState(null);
  const [fetchLocalDuplicateInfo, setFetchLocalDuplicateInfo] = useState(null);

  // Handle authentication
  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      // Construct API URL based on user's server input
      const serverHost = authForm.server_ip;
      const clientApiPort = 5501;
      const dynamicApiBase = `http://${serverHost}:${clientApiPort}/api/client`;
      
      console.log(`[Auth] Connecting to: ${dynamicApiBase}`);
      
      const endpoint = authMode === 'login' ? '/login' : '/register';
      const response = await fetch(`${dynamicApiBase}${endpoint}`, {
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
        // Store the API base URL for future requests
        setApiBaseUrl(dynamicApiBase);
        console.log(`[Auth] API base URL set to: ${dynamicApiBase}`);
        
        setToken(data.token);
        setCurrentUser(data.user);
        setAuthenticated(true);
        setShowAuthModal(false);
        showNotification('success', 'Success', `${authMode === 'login' ? 'Logged in' : 'Registered'} successfully!`);
        // Pass token explicitly to avoid race condition
        await initializeClient(data.user.username, data.token, dynamicApiBase);
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
  const initializeClient = async (username, userToken, dynamicApiBase) => {
    try {
      const response = await fetch(`${dynamicApiBase}/init`, {
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
        // Pass token explicitly to fetchAllData
        fetchAllData(userToken);
        showNotification('success', 'Connected', `Connected to P2P network as ${data.client.display_name}`);
      } else {
        showNotification('error', 'Initialization Failed', data.error);
      }
    } catch (error) {
      showNotification('error', 'Connection Error', 'Failed to initialize client: ' + error.message);
    }
  };

  // Fetch all data
  const fetchAllData = async (userToken) => {
    // Use provided token or fall back to state token
    const authToken = userToken || token;
    await Promise.all([
      fetchLocalFiles(authToken),
      fetchPublishedFiles(authToken),
      fetchNetworkFiles(authToken)
    ]);
  };

  const fetchLocalFiles = async (authToken) => {
    const useToken = authToken || token;
    try {
      const response = await fetch(`${apiBaseUrl}/local-files`, {
        headers: {
          'Authorization': `Bearer ${useToken}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setLocalFiles(data.files);
      }
    } catch (error) {
      console.error('Failed to fetch local files:', error);
    }
  };

  const fetchPublishedFiles = async (authToken) => {
    const useToken = authToken || token;
    try {
      const response = await fetch(`${apiBaseUrl}/published-files`, {
        headers: {
          'Authorization': `Bearer ${useToken}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setPublishedFiles(data.files);
      }
    } catch (error) {
      console.error('Failed to fetch published files:', error);
    }
  };

  const fetchNetworkFiles = async (authToken) => {
    const useToken = authToken || token;
    try {
      const response = await fetch(`${apiBaseUrl}/network-files`, {
        headers: {
          'Authorization': `Bearer ${useToken}`
        }
      });
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
  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadForm({
        ...uploadForm,
        selectedFile: file
      });
      
      // Check for duplicates when file is selected
      await checkUploadDuplicates(file);
    }
  };

  // Check for duplicates on network and locally
  const checkUploadDuplicates = async (file) => {
    try {
      // Check network duplicates
      const networkResponse = await fetch(`${apiBaseUrl}/check-duplicate`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          fname: file.name,
          size: file.size,
          modified: Math.floor(file.lastModified / 1000) // Convert to seconds
        })
      });
      
      const networkData = await networkResponse.json();
      if (networkData.success) {
        setUploadDuplicateInfo(networkData);
      }
      
      // Check local duplicates
      const localResponse = await fetch(`${apiBaseUrl}/check-local-duplicate`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          fname: file.name
        })
      });
      
      const localData = await localResponse.json();
      if (localData.success) {
        setUploadLocalDuplicateInfo(localData);
      }
    } catch (error) {
      console.error('Failed to check duplicates:', error);
    }
  };

  // Check for local duplicates when fetching a file
  const checkFetchDuplicates = async (fname) => {
    try {
      const response = await fetch(`${apiBaseUrl}/check-local-duplicate`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ fname })
      });
      
      const data = await response.json();
      if (data.success) {
        setFetchLocalDuplicateInfo(data);
      }
    } catch (error) {
      console.error('Failed to check local duplicates:', error);
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
      formData.append('force_upload', 'true'); // Allow overwriting if user confirmed
      
      showNotification('info', 'Uploading', `Uploading ${uploadForm.selectedFile.name}...`);
      
      const response = await fetch(`${apiBaseUrl}/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification('success', 'Success', data.message);
        setShowPublishModal(false);
        setUploadForm({ selectedFile: null, autoPublish: false });
        setUploadDuplicateInfo(null);
        setUploadLocalDuplicateInfo(null);
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
      
      const response = await fetch(`${apiBaseUrl}/publish`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
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
      const response = await fetch(`${apiBaseUrl}/unpublish`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
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
  const handleFetchFile = async (file) => {
    setSelectedNetworkFile(file);
    setFetchForm({ fetchToBackend: true, customPath: '' });
    
    // Check for local duplicates before showing modal
    await checkFetchDuplicates(file.name);
    
    setShowFetchModal(true);
  };

  const handleFetchConfirm = async (e) => {
    e.preventDefault();
    
    try {
      if (fetchForm.fetchToBackend) {
        showNotification('info', 'Downloading', `Downloading ${selectedNetworkFile.name} to backend...`);
        
        const response = await fetch(`${apiBaseUrl}/fetch`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
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
        
        const fetchResponse = await fetch(`${apiBaseUrl}/fetch`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            fname: selectedNetworkFile.name,
            save_path: null
          })
        });
        
        const fetchData = await fetchResponse.json();
        
        if (fetchData.success) {
          setTimeout(async () => {
            // Download file with authentication
            const downloadResponse = await fetch(`${apiBaseUrl}/download/${encodeURIComponent(selectedNetworkFile.name)}`, {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
            
            if (downloadResponse.ok) {
              const blob = await downloadResponse.blob();
              const url = window.URL.createObjectURL(blob);
              const link = document.createElement('a');
              link.href = url;
              link.download = selectedNetworkFile.name;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              window.URL.revokeObjectURL(url);
              
              showNotification('success', 'Download Started', 'File download started to your browser');
            } else {
              showNotification('error', 'Download Failed', 'Failed to download file');
            }
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

  // Handle disconnect/logout
  const handleDisconnect = async () => {
    try {
      showNotification('info', 'Disconnecting', 'Logging out from P2P network...');
      
      const response = await fetch(`${apiBaseUrl}/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification('success', 'Disconnected', 'Successfully logged out from network');
        // Wait a moment for notification to show, then go back
        setTimeout(() => {
          onBack();
        }, 1000);
      } else {
        showNotification('warning', 'Disconnect Issue', data.error || 'Could not disconnect properly');
        // Still go back even if disconnect failed
        setTimeout(() => {
          onBack();
        }, 1500);
      }
    } catch (error) {
      console.error('Disconnect error:', error);
      showNotification('warning', 'Disconnect Issue', 'Connection error during logout');
      // Still go back even if request failed
      setTimeout(() => {
        onBack();
      }, 1500);
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
        onBackClick={handleDisconnect}
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
          onClose={() => {
            setShowPublishModal(false);
            setUploadDuplicateInfo(null);
            setUploadLocalDuplicateInfo(null);
          }}
          formatFileSize={formatFileSize}
          duplicateInfo={uploadDuplicateInfo}
          localDuplicateInfo={uploadLocalDuplicateInfo}
        />
      )}

      {/* Fetch Modal */}
      {showFetchModal && selectedNetworkFile && (
        <FetchFileModal
          file={selectedNetworkFile}
          fetchForm={fetchForm}
          setFetchForm={setFetchForm}
          onSubmit={handleFetchConfirm}
          onClose={() => {
            setShowFetchModal(false);
            setFetchLocalDuplicateInfo(null);
          }}
          formatFileSize={formatFileSize}
          localDuplicateInfo={fetchLocalDuplicateInfo}
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
