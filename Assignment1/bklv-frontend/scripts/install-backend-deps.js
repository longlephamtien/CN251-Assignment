#!/usr/bin/env node

/**
 * Cross-platform script to install Python backend dependencies
 * Works on Windows, macOS, and Linux
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  blue: '\x1b[34m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

// Get possible Python commands based on platform
function getPythonCommands() {
  if (process.platform === 'win32') {
    return ['python', 'python3', 'py'];
  } else {
    return ['python3', 'python'];
  }
}

// Check if a command exists
function checkCommand(command) {
  return new Promise((resolve) => {
    const child = spawn(command, ['--version'], {
      stdio: 'pipe',
      shell: process.platform === 'win32'
    });
    
    let output = '';
    child.stdout.on('data', (data) => {
      output += data.toString();
    });
    
    child.on('error', () => resolve({ available: false }));
    child.on('exit', (code) => {
      if (code === 0) {
        resolve({ available: true, version: output.trim() });
      } else {
        resolve({ available: false });
      }
    });
  });
}

// Find available Python command
async function findPython() {
  const commands = getPythonCommands();
  
  for (const cmd of commands) {
    const result = await checkCommand(cmd);
    if (result.available) {
      return { command: cmd, version: result.version };
    }
  }
  
  return null;
}

// Install pip packages
function installPackages(pythonCmd, requirementsPath) {
  return new Promise((resolve, reject) => {
    log('📦 Installing Python packages...', 'blue');
    
    const pipArgs = ['-m', 'pip', 'install', '-r', requirementsPath];
    const child = spawn(pythonCmd, pipArgs, {
      stdio: 'inherit',
      shell: process.platform === 'win32'
    });
    
    child.on('error', (err) => {
      reject(err);
    });
    
    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`pip install failed with code ${code}`));
      }
    });
  });
}

// Main function
async function main() {
  log('\n==========================================', 'blue');
  log('  Backend Dependencies Installation', 'blue');
  log('==========================================\n', 'blue');
  
  // Check if backend directory exists
  const backendDir = path.join(__dirname, '../../bklv-backend');
  const requirementsPath = path.join(backendDir, 'requirements.txt');
  
  if (!fs.existsSync(backendDir)) {
    log('⚠️  Backend directory not found, skipping...', 'yellow');
    log(`    Expected: ${backendDir}\n`, 'yellow');
    return;
  }
  
  if (!fs.existsSync(requirementsPath)) {
    log('⚠️  requirements.txt not found, skipping...', 'yellow');
    log(`    Expected: ${requirementsPath}\n`, 'yellow');
    return;
  }
  
  // Find Python
  log('🔍 Looking for Python installation...', 'blue');
  const python = await findPython();
  
  if (!python) {
    log('\n❌ Python not found!', 'red');
    log('\nPlease install Python 3 from:', 'yellow');
    log('  https://www.python.org/downloads/', 'yellow');
    
    if (process.platform === 'win32') {
      log('\n⚠️  On Windows, make sure to:', 'yellow');
      log('  1. Check "Add Python to PATH" during installation', 'yellow');
      log('  2. Restart your terminal after installation\n', 'yellow');
    } else {
      log('\n⚠️  On macOS/Linux, you may need to install python3:', 'yellow');
      log('  macOS: brew install python3', 'yellow');
      log('  Ubuntu/Debian: sudo apt-get install python3 python3-pip', 'yellow');
      log('  Fedora: sudo dnf install python3 python3-pip\n', 'yellow');
    }
    
    // Don't fail the npm install, just warn
    return;
  }
  
  log(`✅ Found Python: ${python.command}`, 'green');
  log(`   Version: ${python.version}\n`, 'green');
  
  // Install packages
  try {
    await installPackages(python.command, requirementsPath);
    log('\n✅ Backend dependencies installed successfully!\n', 'green');
  } catch (err) {
    log('\n⚠️  Failed to install some packages:', 'yellow');
    log(`   ${err.message}`, 'yellow');
    log('\n   You may need to install them manually:', 'yellow');
    log(`   ${python.command} -m pip install -r ${requirementsPath}\n`, 'yellow');
    
    // Don't fail the npm install
  }
}

// Run main function
main().catch((err) => {
  log(`\n❌ Error: ${err.message}\n`, 'red');
  // Don't exit with error code to avoid breaking npm install
});
