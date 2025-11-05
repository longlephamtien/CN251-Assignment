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
  AddFileModal,
  FetchFileModal
} from '../components/client';
import { useNotification } from '../hooks/useNotification';
import { formatTimestamp, formatFileSize } from '../utils/formatters';
import './ClientInterfaceScreen.css';

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
  const [showAddFileModal, setShowAddFileModal] = useState(false);
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
  
  const [addForm, setAddForm] = useState({
    selectedFile: null,
    autoPublish: false
  });
  
  const [fetchForm, setFetchForm] = useState({
    fetchToBackend: true,
    customPath: ''
  });

  // Duplicate detection states
  const [addDuplicateInfo, setAddDuplicateInfo] = useState(null);
  const [addLocalDuplicateInfo, setAddLocalDuplicateInfo] = useState(null);
  const [fetchLocalDuplicateInfo, setFetchLocalDuplicateInfo] = useState(null);
  const [fetchValidationWarning, setFetchValidationWarning] = useState(null);

  // Fetch progress tracking (integrated into modal)
  const [currentFetchId, setCurrentFetchId] = useState(null);
  const [fetchProgress, setFetchProgress] = useState(null);
  const [isFetching, setIsFetching] = useState(false);
  const [pollInterval, setPollInterval] = useState(null);

  // Handle authentication
  const handleAuth = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      // CRITICAL: Always use localhost for client_api.py
      // Frontend runs on client machine, so client_api.py MUST be local
      const localClientApi = 'http://localhost:5501/api/client';
      
      console.log(`[Auth] Using local client API: ${localClientApi}`);
      console.log(`[Auth] Server IP from form: ${authForm.server_ip}`);
      
      const endpoint = authMode === 'login' ? '/login' : '/register';
      const response = await fetch(`${localClientApi}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: authForm.username,
          password: authForm.password,
          display_name: authMode === 'register' ? authForm.display_name : undefined,
          server_host: authForm.server_ip,  // Forward server IP to client_api
          server_port: 5500  // Server API port (not central server port)
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Always use localhost for client API
        setApiBaseUrl(localClientApi);
        console.log(`[Auth] Client API base URL set to: ${localClientApi}`);
        
        setToken(data.token);
        setCurrentUser(data.user);
        setAuthenticated(true);
        setShowAuthModal(false);
        showNotification('success', 'Success', `${authMode === 'login' ? 'Logged in' : 'Registered'} successfully!`);
        // Pass token and local API base to initialize client
        await initializeClient(data.user.username, data.token, localClientApi);
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
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${userToken}`
        },
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

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

  // Handle file selection
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

  // Handle file selection from browser
  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (file) {
      setAddForm({ ...addForm, selectedFile: file });
      
      // Check for duplicates
      await checkAddFileDuplicates(file.name, file.size, file.lastModified / 1000);
    }
  };

  // Check for duplicate files when adding
  const checkAddFileDuplicates = async (fname, size, modified) => {
    try {
      // Check local duplicates
      const localResponse = await fetch(`${apiBaseUrl}/check-local-duplicate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ fname })
      });
      
      const localData = await localResponse.json();
      if (localData.success) {
        setAddLocalDuplicateInfo(localData.exists ? localData : null);
      }

      // Check network duplicates
      const networkResponse = await fetch(`${apiBaseUrl}/check-duplicate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ fname, size, modified })
      });
      
      const networkData = await networkResponse.json();
      if (networkData.success) {
        setAddDuplicateInfo(networkData.has_exact_duplicate || networkData.has_partial_duplicate ? {
          has_exact_duplicate: networkData.has_exact_duplicate,
          has_partial_duplicate: networkData.has_partial_duplicate,
          exact_matches: networkData.exact_matches || [],
          partial_matches: networkData.partial_matches || []
        } : null);
      }
    } catch (error) {
      console.error('Failed to check duplicates:', error);
    }
  };

  // Handle Electron file selection
  const handleElectronFileSelect = async () => {
    if (!window.electronAPI) {
      console.error('Electron API not available');
      return;
    }

    const result = await window.electronAPI.openFileDialog();
    
    if (!result.canceled) {
      // Create a file-like object with the path information
      const fileInfo = {
        name: result.fileName,
        size: result.fileSize,
        type: result.fileType,
        path: result.filePath,
        modified: result.modified,
        created: result.created,
        lastModified: result.modified * 1000 // Convert to milliseconds for consistency
      };
      
      setAddForm({ ...addForm, selectedFile: fileInfo });
      
      // Check for duplicates
      await checkAddFileDuplicates(result.fileName, result.fileSize, result.modified);
    }
  };

  // Add file to tracking by path (no upload/copy)
  const handleAddFile = async (e) => {
    e.preventDefault();
    
    if (!addForm.selectedFile) {
      showNotification('warning', 'No File Selected', 'Please select a file');
      return;
    }
    
    try {
      const file = addForm.selectedFile;
      // Check if running in Electron (file will have .path property)
      const isElectron = window.electronAPI?.isElectron || false;
      let filePath;
      
      if (isElectron && file.path) {
        // Electron: Use the actual file path from the file dialog
        filePath = file.path;
      } else {
        // Browser: Try to get path (will likely just be filename)
        filePath = file.path || file.webkitRelativePath || file.name;
      }
      
      showNotification('info', 'Adding File', `Tracking file: ${file.name}...`);
      
      const response = await fetch(`${apiBaseUrl}/add-file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          filepath: filePath,
          auto_publish: addForm.autoPublish
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        showNotification('success', 'Success', data.message);
        
        // Auto publish if requested
        if (addForm.autoPublish && data.file) {
          setTimeout(async () => {
            try {
              const publishResponse = await fetch(`${apiBaseUrl}/publish`, {
                method: 'POST',
                headers: { 
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                  fname: data.file.name,
                  local_path: data.file.path
                })
              });
              
              const publishData = await publishResponse.json();
              if (publishData.success) {
                showNotification('success', 'Published', `File "${data.file.name}" published to network!`);
              }
            } catch (err) {
              console.error('Publish error:', err);
            }
          }, 500);
        }
        
        setShowAddFileModal(false);
        setAddForm({ selectedFile: null, autoPublish: false });
        setAddDuplicateInfo(null);
        setAddLocalDuplicateInfo(null);
        setTimeout(() => {
          fetchAllData();
        }, 1000);
      } else {
        // Handle file validation errors with more specific messages
        const errorMsg = data.error || 'Failed to add file';
        if (errorMsg.includes('not found') || errorMsg.includes('Not found')) {
          showNotification('error', 'File Not Found', `The file could not be found at: ${filePath}`);
        } else if (errorMsg.includes('not readable') || errorMsg.includes('permission')) {
          showNotification('error', 'Permission Denied', `Cannot read the file. Please check file permissions.`);
        } else if (errorMsg.includes('not a file')) {
          showNotification('error', 'Invalid Path', `The path is not a valid file: ${filePath}`);
        } else {
          showNotification('error', 'Failed', errorMsg);
        }
      }
    } catch (error) {
      console.error('Add file error:', error);
      showNotification('error', 'Error', `Failed to add file: ${error.message}`);
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
        // Handle file validation errors
        const errorMsg = data.error || 'Publish failed';
        if (errorMsg.includes('not found') || errorMsg.includes('Not found')) {
          showNotification('error', 'File Not Found', 
            `The file "${file.name}" no longer exists at its original location. Please remove it from local files or re-upload.`);
        } else if (errorMsg.includes('not readable') || errorMsg.includes('permission')) {
          showNotification('error', 'Permission Denied', 
            `Cannot read "${file.name}". Please check file permissions.`);
        } else if (errorMsg.includes('not a file')) {
          showNotification('error', 'Invalid Path', 
            `The path for "${file.name}" is not a valid file.`);
        } else {
          showNotification('error', 'Publish Failed', errorMsg);
        }
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
    setFetchValidationWarning(null);
    
    // Check for local duplicates before showing modal
    await checkFetchDuplicates(file.name);
    
    // Optionally validate that the source file still exists at the peer
    // This is a client-side warning, actual validation happens during transfer
    try {
      // We can add peer-side validation here if needed
      // For now, we'll rely on the PeerServer's validation during transfer
    } catch (error) {
      console.warn('Failed to pre-validate file:', error);
    }
    
    setShowFetchModal(true);
  };

  const handleFetchConfirm = async (e) => {
    e.preventDefault();
    
    try {
      // Prompt user to select download location
      let downloadPath = null;
      
      // Check if running in Electron
      if (window.electronAPI?.isElectron) {
        // Show directory picker
        const result = await window.electronAPI.openDirectoryDialog();
        
        if (result.canceled) {
          // User cancelled the directory selection
          return;
        }
        
        downloadPath = result.directoryPath;
      } else {
        // Browser mode - use a simple prompt
        downloadPath = window.prompt(
          'Enter the full path where you want to save the file:',
          '/Users/you/Downloads'
        );
        
        if (!downloadPath) {
          // User cancelled
          return;
        }
      }
      
      // Start P2P fetch with progress tracking in modal
      setIsFetching(true);
      
      const response = await fetch(`${apiBaseUrl}/fetch`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          fname: selectedNetworkFile.name,
          save_path: downloadPath
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        const fetchId = data.fetch_id;
        setCurrentFetchId(fetchId);
        
        // Start polling for progress (updates modal)
        pollFetchProgress(fetchId);
        
      } else {
        setIsFetching(false);
        // Enhanced error handling for file validation issues
        const errorMsg = data.error || 'Fetch failed';
        if (errorMsg.includes('not found') || errorMsg.includes('Not found')) {
          showNotification('error', 'File Not Found', 
            `The file "${selectedNetworkFile.name}" is no longer available from ${selectedNetworkFile.owner_name}.`);
        } else if (errorMsg.includes('not readable') || errorMsg.includes('permission')) {
          showNotification('error', 'Access Denied', 
            `Cannot access "${selectedNetworkFile.name}" from the source.`);
        } else if (errorMsg.includes('Connection') || errorMsg.includes('timeout')) {
          showNotification('error', 'Connection Failed', 
            `Cannot connect to ${selectedNetworkFile.owner_name}. The peer may be offline.`);
        } else {
          showNotification('error', 'Fetch Failed', errorMsg);
        }
      }
    } catch (error) {
      console.error('Fetch error:', error);
      setIsFetching(false);
      showNotification('error', 'Error', 'Failed to fetch file: ' + error.message);
    }
  };

  // Poll fetch progress (integrated into modal)
  const pollFetchProgress = (fetchId) => {
    // Clear any existing interval
    if (pollInterval) {
      clearInterval(pollInterval);
    }
    
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/fetch-progress/${fetchId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        const data = await response.json();
        
        if (data.success) {
          const progress = data.progress;
          
          // Debug: Log progress updates
          console.log('[POLL] Progress update:', {
            percent: progress.progress_percent,
            downloaded: progress.downloaded_size,
            total: progress.total_size,
            speed: progress.speed_bps,
            status: progress.status
          });
          
          // Update progress in modal
          setFetchProgress(progress);
          
          // Check if fetch is complete or failed
          if (progress.status === 'completed') {
            clearInterval(interval);
            setPollInterval(null);
            // Status shown in modal, no notification needed
            
            // Refresh local files in background
            setTimeout(() => {
              fetchLocalFiles();
            }, 1000);
            
          } else if (progress.status === 'failed') {
            clearInterval(interval);
            setPollInterval(null);
            // Error shown in modal, no notification needed
          }
        }
      } catch (error) {
        console.error('Progress polling error:', error);
      }
    }, 500); // Poll every 500ms for smooth progress updates
    
    setPollInterval(interval);
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
                  onClick={() => setShowAddFileModal(true)}
                  className="add-file-button"
                >
                  + Add File
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
                formatTimestamp={formatTimestamp}
              />
            ) : (
              <NetworkFilesGrid
                files={networkFiles}
                onDownload={handleFetchFile}
                formatFileSize={formatFileSize}
                formatTimestamp={formatTimestamp}
              />
            )
          )}
        </ContentCard>
      </div>

      {/* Add File Modal */}
      {showAddFileModal && (
        <AddFileModal
          addForm={addForm}
          setAddForm={setAddForm}
          onSubmit={handleAddFile}
          onFileSelect={handleFileSelect}
          onElectronFileSelect={handleElectronFileSelect}
          onClose={() => {
            setShowAddFileModal(false);
            setAddForm({ selectedFile: null, autoPublish: false });
            setAddDuplicateInfo(null);
            setAddLocalDuplicateInfo(null);
          }}
          formatFileSize={formatFileSize}
          duplicateInfo={addDuplicateInfo}
          localDuplicateInfo={addLocalDuplicateInfo}
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
            // Clear polling interval if still running
            if (pollInterval) {
              clearInterval(pollInterval);
              setPollInterval(null);
            }
            // Reset all fetch-related state
            setShowFetchModal(false);
            setFetchLocalDuplicateInfo(null);
            setFetchValidationWarning(null);
            setFetchProgress(null);
            setCurrentFetchId(null);
            setIsFetching(false);
            // Refresh local files in case download completed
            if (fetchProgress?.status === 'completed') {
              fetchLocalFiles();
            }
          }}
          formatFileSize={formatFileSize}
          localDuplicateInfo={fetchLocalDuplicateInfo}
          validationWarning={fetchValidationWarning}
          fetchProgress={fetchProgress}
          isFetching={isFetching}
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
