const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess = null;

// Get the appropriate Python command for the platform
function getPythonCommand() {
  // On Windows, try 'python' first, then 'python3', then 'py'
  // On Unix-like systems, try 'python3' first, then 'python'
  if (process.platform === 'win32') {
    return ['python', 'python3', 'py'];
  } else {
    return ['python3', 'python'];
  }
}

// Check if a Python command is available
function checkPythonCommand(command) {
  return new Promise((resolve) => {
    const child = spawn(command, ['--version'], { 
      stdio: 'pipe',
      shell: process.platform === 'win32' // Use shell on Windows for better compatibility
    });
    
    child.on('error', () => resolve(false));
    child.on('exit', (code) => resolve(code === 0));
  });
}

// Start the Python backend server
async function startPythonBackend() {
  const backendPath = isDev
    ? path.join(__dirname, '../../bklv-backend')
    : path.join(process.resourcesPath, 'backend');
  
  const scriptPath = path.join(backendPath, 'client_api.py');
  
  console.log('[Backend] Starting Python backend...');
  console.log('[Backend] Platform:', process.platform);
  console.log('[Backend] Script path:', scriptPath);
  console.log('[Backend] Working directory:', backendPath);
  
  // Find available Python command
  const pythonCommands = getPythonCommand();
  let pythonCmd = null;
  
  for (const cmd of pythonCommands) {
    const isAvailable = await checkPythonCommand(cmd);
    if (isAvailable) {
      pythonCmd = cmd;
      console.log(`[Backend] Using Python command: ${cmd}`);
      break;
    }
  }
  
  if (!pythonCmd) {
    const errorMsg = process.platform === 'win32'
      ? 'Python is not installed or not in PATH.\n\nPlease install Python 3 from https://www.python.org/\n\nMake sure to check "Add Python to PATH" during installation.'
      : 'Python 3 is not installed or not in PATH.\n\nPlease install Python 3 from https://www.python.org/';
    
    dialog.showErrorBox('Python Not Found', errorMsg);
    console.error('[Backend] No Python command found');
    return;
  }
  
  // Spawn Python process with platform-specific options
  pythonProcess = spawn(pythonCmd, [scriptPath], {
    cwd: backendPath,
    env: { ...process.env },
    shell: process.platform === 'win32', // Use shell on Windows
    windowsHide: true // Hide console window on Windows
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Backend Error] ${data.toString().trim()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Backend] Process exited with code ${code}`);
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    console.error('[Backend] Failed to start:', err);
    dialog.showErrorBox(
      'Backend Error',
      `Failed to start the backend server:\n${err.message}\n\nPlease ensure Python 3 is installed and required packages are available.`
    );
  });
}

// Stop the Python backend server
function stopPythonBackend() {
  if (pythonProcess) {
    console.log('[Backend] Stopping Python backend...');
    pythonProcess.kill();
    pythonProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    title: 'BKLV P2P File Sharing',
    icon: path.join(__dirname, 'icon.png')
  });

  // Load the app
  const startUrl = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, '../build/index.html')}`;
    
  mainWindow.loadURL(startUrl);

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Handle file dialog requests from renderer
ipcMain.handle('dialog:openFile', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    title: 'Select a file to add',
    buttonLabel: 'Add File'
  });

  if (result.canceled || result.filePaths.length === 0) {
    return { canceled: true };
  }

  const filePath = result.filePaths[0];
  const fs = require('fs');
  const stats = fs.statSync(filePath);

  return {
    canceled: false,
    filePath: filePath,
    fileName: path.basename(filePath),
    fileSize: stats.size,
    fileType: path.extname(filePath),
    modified: stats.mtimeMs / 1000, // Convert to seconds
    created: stats.birthtimeMs / 1000
  };
});

// Handle directory dialog requests
ipcMain.handle('dialog:openDirectory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select a directory',
    buttonLabel: 'Select'
  });

  if (result.canceled || result.filePaths.length === 0) {
    return { canceled: true };
  }

  return {
    canceled: false,
    directoryPath: result.filePaths[0]
  };
});

// App lifecycle
app.whenReady().then(() => {
  // Start backend first, then create window
  startPythonBackend();
  
  // Give backend a moment to start up before opening window
  setTimeout(() => {
    createWindow();
  }, 2000);
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  stopPythonBackend();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
