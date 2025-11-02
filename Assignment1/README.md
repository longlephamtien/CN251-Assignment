# BKLV P2P File Sharing System

## Overview

BKLV is a comprehensive Peer-to-Peer (P2P) file sharing system that enables distributed file sharing among multiple clients through a centralized registry server. The system implements a hybrid P2P architecture where a central server maintains a registry of connected clients and their shared files, while actual file transfers occur directly between peers. The application features a modern web-based interface for both administrators and clients, providing real-time monitoring, user authentication, and seamless file management capabilities.

The system is built with a Python backend implementing the P2P protocol and Flask REST APIs, paired with a React frontend for intuitive user interaction. It supports essential P2P operations including file publishing, discovery, fetching, and peer status monitoring, while maintaining persistent state across client reconnections.

**🌐 NEW: LAN Support** - The system now supports multi-computer setup over local networks! See [LAN Setup Guide](./LAN_SETUP.md) or [Quick Start](./LAN_QUICK_START.md) for details.

## Architecture and Design

### System Architecture

The system follows a three-tier hybrid P2P architecture:

1. **Presentation Layer**: React-based web interface
   - Admin Dashboard for system monitoring
   - Client Interface for file operations
   - Real-time updates and notifications

2. **Application Layer**: Flask REST API servers
   - Server API (port 5500): Admin operations and registry queries
   - Client API (port 5501): Client authentication and file operations
   - JWT-based authentication and session management

3. **Network Layer**: P2P communication infrastructure
   - Central Registry Server (port 9000): TCP-based protocol for client registration and file discovery
   - Peer Servers (ports 6000-7000): Direct file transfer between clients
   - Custom JSON-based protocol over TCP sockets

### Architecture Diagram

```
                                    Web Browser
                                         |
                         +---------------+---------------+
                         |                               |
                   Admin Dashboard                Client Interface
                         |                               |
                         v                               v
                +------------------+          +------------------+
                |  Server API      |          |  Client API      |
                |  (Flask:5500)    |          |  (Flask:5501)    |
                +------------------+          +------------------+
                         |                               |
                         +---------------+---------------+
                                         |
                                         v
                            +------------------------+
                            | Central Registry Server|
                            |    (TCP Port 9000)     |
                            +------------------------+
                                         |
                         +---------------+---------------+
                         |               |               |
                         v               v               v
                   +----------+    +----------+    +----------+
                   | Client A |    | Client B |    | Client C |
                   | Peer Svr |    | Peer Svr |    | Peer Svr |
                   | (6001)   |    | (6002)   |    | (6003)   |
                   +----------+    +----------+    +----------+
                         |               |               |
                         +-------[Direct P2P Transfer]---+
```

### Class Diagrams and Main Components

#### Backend Core Classes

**1. Central Registry Server (server.py)**

```
+---------------------------+
|    RegistryServer         |
+---------------------------+
| - registry: dict          |
| - registry_lock: Lock     |
+---------------------------+
| + handle_conn()           |
| + send_json()             |
| + recv_json()             |
| + cleanup_thread()        |
+---------------------------+

Registry Structure:
{
  "hostname": {
    "addr": (ip, port),
    "display_name": str,
    "files": {
      "filename": {
        "size": int,
        "modified": timestamp,
        "published_at": timestamp,
        "is_published": bool
      }
    },
    "last_seen": timestamp,
    "connected_at": timestamp
  }
}
```

**2. Client Class (client.py)**

```
+---------------------------+
|        Client             |
+---------------------------+
| - hostname: str           |
| - display_name: str       |
| - listen_port: int        |
| - repo_dir: str           |
| - local_files: dict       |
| - published_files: dict   |
| - network_files: dict     |
| - central: socket         |
| - peer_server: PeerServer |
| - running: bool           |
+---------------------------+
| + publish()               |
| + unpublish()             |
| + request()               |
| + download_from_peer()    |
| + discover()              |
| + ping()                  |
| + list_local()            |
| + list_published()        |
| + list_network()          |
| + unregister()            |
| + close()                 |
| - _scan_repo_directory()  |
| - _load_state()           |
| - _save_state()           |
| - heartbeat_thread()      |
+---------------------------+
```

**3. File Metadata (client.py)**

```
+---------------------------+
|     FileMetadata          |
+---------------------------+
| - name: str               |
| - size: int               |
| - modified: timestamp     |
| - path: str               |
| - is_published: bool      |
| - published_at: timestamp |
+---------------------------+
| + to_dict()               |
+---------------------------+
```

**4. Peer Server (client.py)**

```
+---------------------------+
|      PeerServer           |
+---------------------------+
| - listen_port: int        |
| - repo_dir: str           |
| - sock: socket            |
+---------------------------+
| + run()                   |
| + handle_peer()           |
+---------------------------+
```

**5. User Database (user_db.py)**

```
+---------------------------+
|       UserDB              |
+---------------------------+
| - db_path: str            |
| - lock: Lock              |
+---------------------------+
| + register_user()         |
| + authenticate_user()     |
| + get_user()              |
| + update_user()           |
| + add_user_file()         |
| + remove_user_file()      |
| + get_all_users()         |
| - _hash_password()        |
| - _load_db()              |
| - _save_state()           |
+---------------------------+
```

**6. API Servers**
- **server_api.py**: Flask application providing REST endpoints for admin operations
- **client_api.py**: Flask application providing REST endpoints for client operations

#### Frontend Component Hierarchy

```
App (React)
|
+-- LandingScreen
|   +-- Button (Admin/Client selection)
|
+-- AdminDashboardScreen
|   +-- DashboardLayout
|   |   +-- DashboardHeader
|   |   +-- AdminLoginForm
|   |   +-- AdminStatsGrid
|   |   +-- ViewToggle (List/Grid)
|   |   +-- ClientsTable / ClientsGrid
|   |   +-- ClientFilesModal
|   +-- NotificationModal
|
+-- ClientInterfaceScreen
    +-- DashboardLayout
    |   +-- DashboardHeader
    |   +-- ClientAuthForm (Login/Register)
    |   +-- ClientTabs (Local/Published/Network)
    |   +-- ViewToggle (List/Grid)
    |   +-- LocalFilesTable / LocalFilesGrid
    |   +-- PublishedFilesTable / PublishedFilesGrid
    |   +-- NetworkFilesTable / NetworkFilesGrid
    |   +-- UploadFileModal
    |   +-- FetchFileModal
    +-- NotificationModal
```

## Communication Protocols

### 1. Central Server Protocol (TCP/JSON)

All messages between clients and the central server follow a JSON-based protocol over TCP:

**Message Format:**
```json
{
  "action": "ACTION_NAME",
  "data": { /* action-specific data */ }
}
```

**Response Format:**
```json
{
  "status": "OK|ERROR|ACK|FOUND|NOTFOUND|ALIVE|DEAD",
  "reason": "error description (if applicable)",
  "data": { /* response-specific data */ }
}
```

#### Protocol Actions:

**REGISTER** - Client registration with central server
```json
Request:
{
  "action": "REGISTER",
  "data": {
    "hostname": "client_id",
    "port": 6001,
    "display_name": "User Name",
    "files_metadata": {
      "file.txt": {
        "size": 1234,
        "modified": 1697540000,
        "published_at": 1697540100,
        "is_published": true
      }
    }
  }
}

Response:
{
  "status": "OK"
}
```

**PUBLISH** - Publish a file to the network
```json
Request:
{
  "action": "PUBLISH",
  "data": {
    "hostname": "client_id",
    "fname": "document.pdf",
    "size": 5120,
    "modified": 1697540000
  }
}

Response:
{
  "status": "ACK"
}
```

**UNPUBLISH** - Remove file from network (mark as unpublished)
```json
Request:
{
  "action": "UNPUBLISH",
  "data": {
    "hostname": "client_id",
    "fname": "document.pdf"
  }
}

Response:
{
  "status": "ACK"
}
```

**REQUEST** - Request file locations
```json
Request:
{
  "action": "REQUEST",
  "data": {
    "fname": "document.pdf"
  }
}

Response:
{
  "status": "FOUND",
  "hosts": [
    {
      "hostname": "client_a",
      "display_name": "Alice",
      "ip": "192.168.1.10",
      "port": 6001,
      "size": 5120,
      "modified": 1697540000,
      "is_published": true
    }
  ]
}
```

**DISCOVER** - Get files from specific host
```json
Request:
{
  "action": "DISCOVER",
  "data": {
    "hostname": "client_a"
  }
}

Response:
{
  "status": "OK",
  "files": {
    "file1.txt": {...},
    "file2.pdf": {...}
  },
  "addr": ["192.168.1.10", 6001]
}
```

**PING** - Check if peer is alive
```json
Request:
{
  "action": "PING",
  "data": {
    "hostname": "client_a"
  }
}

Response:
{
  "status": "ALIVE|DEAD"
}
```

**LIST** - Get full registry
```json
Request:
{
  "action": "LIST"
}

Response:
{
  "status": "OK",
  "registry": {
    "client_a": {
      "addr": ["192.168.1.10", 6001],
      "display_name": "Alice",
      "files": {...},
      "last_seen": 1697540500,
      "connected_at": 1697540000
    }
  }
}
```

**UNREGISTER** - Client disconnection
```json
Request:
{
  "action": "UNREGISTER",
  "data": {
    "hostname": "client_id"
  }
}

Response:
{
  "status": "OK"
}
```

### 2. Peer-to-Peer File Transfer Protocol

Direct file transfer between peers uses a simple text-based protocol:

**File Request:**
```
GET filename.txt\n
```

**File Response (Success):**
```
LENGTH 5120\n
[5120 bytes of file data]
```

**File Response (Error):**
```
ERROR notfound\n
```

### 3. REST API Protocol (HTTP/JSON)

#### Admin API (Port 5500)

**POST /api/admin/login** - Admin authentication
```json
Request:
{
  "username": "admin",
  "password": "admin123"
}

Response:
{
  "success": true,
  "message": "Login successful",
  "token": "jwt_token_here"
}
```

**GET /api/admin/registry** - Get full registry with user data
```json
Response:
{
  "success": true,
  "stats": {
    "total_clients": 5,
    "total_files": 20,
    "active_clients": 3
  },
  "clients": [
    {
      "hostname": "user1",
      "display_name": "Alice",
      "ip": "192.168.1.10",
      "port": 6001,
      "files": {...},
      "file_count": 5,
      "status": "online|offline",
      "last_seen": 1697540500,
      "connected_at": 1697540000
    }
  ]
}
```

**GET /api/admin/ping/:hostname** - Ping specific client

**GET /api/admin/discover/:hostname** - Discover client files

#### Client API (Port 5501)

**POST /api/client/register** - Register new user
```json
Request:
{
  "username": "alice",
  "password": "password123",
  "display_name": "Alice Smith"
}

Response:
{
  "success": true,
  "message": "User registered successfully",
  "token": "jwt_token",
  "user": {
    "username": "alice",
    "display_name": "Alice Smith",
    "created_at": "2024-10-17T10:00:00"
  }
}
```

**POST /api/client/login** - User login

**POST /api/client/init** - Initialize client session
```json
Request:
{
  "username": "alice",
  "server_ip": "127.0.0.1",
  "server_port": 9000
}

Response:
{
  "success": true,
  "client": {
    "username": "alice",
    "hostname": "alice",
    "display_name": "Alice Smith",
    "port": 6001,
    "repo": "repo_alice"
  }
}
```

**GET /api/client/local-files** - Get local files
**GET /api/client/published-files** - Get published files
**GET /api/client/network-files** - Get network files

**POST /api/client/upload** - Upload file from browser
```json
Form Data:
- file: (binary file data)
- auto_publish: true|false
```

**POST /api/client/publish** - Publish file to network
```json
Request:
{
  "fname": "document.pdf",
  "local_path": "/path/to/file" (optional)
}
```

**POST /api/client/fetch** - Fetch file from network
```json
Request:
{
  "fname": "document.pdf",
  "save_path": "/custom/path" (optional)
}
```

**POST /api/client/unpublish** - Unpublish file from network

**GET /api/client/download/:fname** - Download file to browser

## Detailed Application Functions

### 1. User Management
- **User Registration**: Create new user accounts with username, password, and display name
- **User Authentication**: Secure login with password hashing (SHA-256)
- **JWT Token Management**: Stateless authentication for API requests
- **User Database**: JSON-based persistent storage with thread-safe operations

### 2. Client Operations

#### File Management
- **Local File Tracking**: Monitor files in user repository with metadata (size, modified time)
- **File Publishing**: Share files with network peers
  - Copy or reference files to repository
  - Register with central server
  - Maintain published state across reconnections
- **File Unpublishing**: Remove files from network sharing while keeping locally
- **File Upload**: Browser-based file upload to client repository
- **File Download**: Fetch files from network peers to local repository or custom location

#### Network Operations
- **Discovery**: Find all available files on the network
- **Request**: Locate peers hosting specific files
- **Peer Status**: Check if specific peers are online
- **Direct Transfer**: Download files directly from peer servers

#### State Persistence
- **Local State File**: `.client_state.json` stores published file status
- **Auto-restore**: Published files automatically re-registered on client restart
- **Metadata Sync**: File metadata synchronized between client and server

### 3. Server Operations

#### Registry Management
- **Client Registration**: Track connected clients with hostname, display name, and network address
- **File Registry**: Maintain published file catalog with metadata
- **Heartbeat Monitoring**: Periodic ping to detect disconnected clients
- **Cleanup Thread**: Remove inactive clients (120-second timeout)

#### Query Processing
- **File Lookup**: Search for files across all connected clients
- **Peer Discovery**: Retrieve file list from specific peers
- **Status Queries**: Real-time registry snapshots for monitoring

### 4. Admin Dashboard Functions

- **System Statistics**: View total clients, files, and active connections
- **Client Monitoring**: Real-time status of all registered users
- **File Inspection**: Browse files published by each client
- **Peer Testing**: Ping clients and discover their file offerings
- **User Management**: View user database with registration and login history

### 5. Client Interface Functions

- **Three-tier File View**:
  - Local Files: All tracked files (published and unpublished)
  - Published Files: Files currently shared on network
  - Network Files: Files available from other peers
- **Dual View Modes**: List and grid display options
- **Real-time Updates**: Auto-refresh every 5 seconds
- **File Actions**: Publish, unpublish, upload, fetch, download
- **Search and Filter**: Find files by name or owner

## Validation and Performance Evaluation

### Sanity Testing Results

#### Test Environment
- Operating System: macOS/Linux/Windows
- Python Version: 3.12.0
- Node.js Version: 25.0.0
- Network: Local (127.0.0.1) and LAN testing

#### Functional Tests

**1. Server Startup Test**
- Status: PASSED
- Central server starts on port 9000
- API servers start on ports 5500 (admin) and 5501 (client)
- Frontend starts on port 3000

**2. Client Registration and Connection**
- Status: PASSED
- Clients successfully register with unique hostnames
- Display names correctly stored and transmitted
- Heartbeat mechanism maintains connection
- Automatic port assignment (6000-7000 range)

**3. File Publishing**
- Status: PASSED
- Files copied to repository correctly
- Metadata (size, modified time) accurately captured
- Central server receives file information
- State persisted to `.client_state.json`
- Published files visible to other clients

**4. File Discovery**
- Status: PASSED
- LIST command returns all published files
- REQUEST command finds correct peer locations
- DISCOVER command retrieves specific peer files
- Multiple hosts correctly returned for same file

**5. Peer-to-Peer Transfer**
- Status: PASSED
- Direct connection established between peers
- File transfer completes successfully
- Downloaded files match source (size and content)
- Transfer works for various file types and sizes

**6. File Unpublishing**
- Status: PASSED
- Files removed from network visibility
- Local files retained after unpublish
- Registry updated immediately
- State changes persisted

**7. Client Reconnection**
- Status: PASSED
- Published state restored from `.client_state.json`
- Previously published files automatically re-registered
- File metadata synchronized correctly

**8. Session Management**
- Status: PASSED
- JWT tokens properly generated and validated
- Session timeout enforced (3600 seconds)
- Invalid tokens rejected
- User data correctly associated with sessions

**9. Cleanup and Disconnection**
- Status: PASSED
- UNREGISTER removes client from registry
- Inactive clients cleaned up after 120 seconds
- Resources properly released on client shutdown

### Performance Evaluation

#### Latency Measurements

**Registry Query Operations** (Single client):
- REGISTER: TBD ms
- PUBLISH: TBD ms
- REQUEST: TBD ms
- LIST: TBD ms (depends on registry size)
- DISCOVER: TBD ms
- PING: TBD ms

**File Transfer Performance**:
- Small files (< 1 MB): TBD ms (LAN)
- Medium files (1-10 MB): TBD ms (LAN)
- Large files (> 10 MB): TBD seconds (LAN)

**API Response Times**:
- Authentication endpoints: TBD ms (includes password hashing)
- File listing endpoints: TBD ms
- Upload endpoints: TBD ms (small files)
- Registry queries: TBD ms

#### Scalability Tests

- 10 clients: TBD
- 50 clients: TBD
- 100 clients: TBD
- Registry size impact: TBD

#### Resource Utilization

**Server (Idle state)**:
- CPU: TBD
- Memory: TBD
- Network: TBD

**Server (Active, 20 clients)**:
- CPU: TBD
- Memory: TBD
- Network: TBD

**Client (Idle state)**:
- CPU: TBD
- Memory: TBD
- Network: TBD

**Client (Active transfer)**:
- CPU: TBD
- Memory: TBD
- Network: TBD

#### Reliability Tests

**Network Interruption**:
- Graceful handling of disconnections
- Automatic reconnection not implemented (manual restart required)
- State persistence prevents data loss

**Concurrent Access**:
- Thread-safe registry operations
- No race conditions in file metadata
- Proper locking mechanisms throughout

**Error Handling**:
- Invalid commands properly rejected
- File not found errors handled gracefully
- Network errors logged and reported to user

## Extension Functions

Beyond the basic requirements, the system implements several advanced features:

### 1. Web-Based User Interface
- **Modern React Frontend**: Single-page application with component-based architecture
- **Dual Interface**: Separate admin and client dashboards
- **Real-time Updates**: Auto-refresh with configurable intervals
- **Responsive Design**: Works on desktop and mobile browsers
- **View Modes**: Toggle between list and grid displays

### 2. User Authentication System
- **User Registration**: Create accounts with unique usernames
- **Secure Authentication**: Password hashing with SHA-256
- **JWT Tokens**: Stateless session management
- **Session Timeout**: Automatic expiration after 1 hour
- **Persistent User Database**: JSON-based storage with thread-safe operations

### 3. File State Persistence
- **Published State Tracking**: Files remember their published status
- **Auto-restore on Reconnect**: Previously published files automatically re-shared
- **Local State File**: `.client_state.json` stores metadata
- **Metadata Synchronization**: File info synced between client and server

### 4. Three-tier File Management
- **Local Files**: All tracked files with metadata
- **Published Files**: Subset of local files shared on network
- **Network Files**: Files available from other clients
- **Independent Management**: Publish/unpublish without copying

### 5. Enhanced File Metadata
- **Size Tracking**: File sizes displayed in human-readable format
- **Timestamp Management**: Modified time, published time, last seen
- **Owner Information**: Display names and hostnames
- **Status Indicators**: Online/offline, published/unpublished

### 6. RESTful API Architecture
- **Admin API**: Complete registry management and monitoring
- **Client API**: User operations and file management
- **HTTP/JSON Protocol**: Standard web-compatible format
- **CORS Support**: Cross-origin requests for frontend
- **Health Checks**: Endpoint monitoring and status

### 7. File Upload from Browser
- **Direct Upload**: Upload files from web interface
- **Auto-publish Option**: Immediately share uploaded files
- **Progress Feedback**: Notifications for upload status
- **File Validation**: Size and type checking

### 8. Flexible File Download
- **Multiple Destinations**: Download to repository or custom path
- **Browser Download**: Save directly to user's computer
- **Path Expansion**: Support for ~ and relative paths
- **Directory Creation**: Automatic parent directory creation

### 9. Cleanup and Monitoring
- **Automatic Cleanup**: Remove inactive clients (120s timeout)
- **Heartbeat Mechanism**: Periodic connection verification
- **Last Seen Tracking**: Monitor client activity
- **Connection Statistics**: Track uptime and file counts

### 10. Command-line Interface
- **Interactive Shell**: Full CLI for client operations
- **Command History**: Standard terminal features
- **Quoted Arguments**: Support for paths with spaces
- **Comprehensive Help**: Built-in command documentation

## How to Run

### Prerequisites

**Required Software:**
- Python 3.12 or higher
- Node.js 22 or higher
- npm (comes with Node.js)
- pip (comes with Python)

**Operating System:**
- macOS, Linux, or Windows
- Terminal/Command Prompt access

### Installation

**1. Clone or download the repository**
```bash
cd Assignment1
```

**2. Create environment configuration**
```bash
# Copy example configuration
cp .env.example .env

# Edit .env if needed (optional - defaults work for local testing)
# nano .env
```

**3. Install Python dependencies**
```bash
cd bklv-backend
pip install -r requirements.txt
cd ..
```

Required packages:
- flask==3.0.0
- flask-cors==4.0.0
- python-dotenv==1.0.0
- PyJWT==2.8.0
- bcrypt==4.1.2

**4. Install Node.js dependencies**
```bash
cd bklv-frontend
npm install
cd ..
```

### Quick Start (Recommended)

**For single computer (localhost) setup:**

**Using the start script (macOS/Linux):**
```bash
chmod +x start.sh
./start.sh
```

This script will:
1. Check for Python and Node.js
2. Install all dependencies
3. Start all four services:
   - Central Server (port 9000)
   - Admin API Server (port 5500)
   - Client API Server (port 5501)
   - React Frontend (port 3000)

**Access the application:**
- Open browser to http://localhost:3000
- Choose "Admin Dashboard" or "Client Interface"

**Default admin credentials:**
- Username: admin
- Password: admin123

**To stop all services:**
```bash
chmod +x stop.sh
./stop.sh
```

---

**For multi-computer (LAN) setup:**

See the [**LAN Setup Guide**](./LAN_SETUP.md) for detailed instructions on running the server on one computer and connecting clients from other computers on the same network.

Quick summary:
1. **Host computer**: Set `SERVER_HOST=0.0.0.0` in `.env`, run `./start.sh`
2. **Client computers**: Open browser to `http://<host-ip>:3000`, enter host's IP in login form

📖 **[Full LAN Setup Guide](./LAN_SETUP.md)** | 🚀 **[LAN Quick Start](./LAN_QUICK_START.md)**

### Manual Start (Step-by-step)

If you prefer to start services individually or the script doesn't work:

**Terminal 1 - Central Server:**
```bash
cd bklv-backend
python server.py
```
Output: Server running on port 9000

**Terminal 2 - Admin API Server:**
```bash
cd bklv-backend
python server_api.py
```
Output: Admin API running on port 5500

**Terminal 3 - Client API Server:**
```bash
cd bklv-backend
python client_api.py
```
Output: Client API running on port 5501

**Terminal 4 - React Frontend:**
```bash
cd bklv-frontend
npm start
```
Output: Opens browser automatically to http://localhost:3000

**To stop services:**
Press Ctrl+C in each terminal

### Using the Command-Line Client (Optional)

For testing or CLI preference, run a client directly:

```bash
cd bklv-backend
python client.py --host alice --port 6001 --repo repo_alice --name "Alice Smith"
```

Available commands in CLI:
```
publish <localpath> <name>  - Publish a file
unpublish <name>            - Unpublish a file
fetch <name>                - Fetch from network
local                       - List local files
published                   - List published files
network                     - List network files
discover <host>             - Discover peer files
ping <host>                 - Check peer status
exit                        - Exit client
```

### Testing the System

**1. Admin Dashboard Test:**
- Navigate to http://localhost:3000
- Click "Admin Dashboard"
- Login with admin/admin123
- View system statistics and connected clients

**2. Client Interface Test (User 1):**
- Open http://localhost:3000 in a new tab/browser
- Click "Client Interface"
- Register new user (e.g., alice/password123)
- Upload a test file
- Click "Publish" to share it

**3. Client Interface Test (User 2):**
- Open http://localhost:3000 in another tab/browser
- Click "Client Interface"
- Register another user (e.g., bob/password123)
- Go to "Network Files" tab
- See alice's published file
- Click "Fetch" to download it
- Check "Local Files" tab for downloaded file

**4. Verify in Admin Dashboard:**
- Return to admin dashboard
- Refresh to see both clients online
- View their file counts
- Click "View Files" to inspect shared files

### Configuration Options

Edit `.env` file to customize:

```bash
Server Settings:
SERVER_HOST=127.0.0.1        # Server IP address
SERVER_PORT=9000             # Server port

Client Settings:
CLIENT_PORT_MIN=6000         # Min port for clients
CLIENT_PORT_MAX=7000         # Max port for clients
CLIENT_REPO_BASE=./repos     # Repository base directory

API Settings:
ADMIN_API_PORT=5500          # Admin API port
CLIENT_API_PORT=5501         # Client API port

Security:
ADMIN_USERNAME=admin         # Admin username
ADMIN_PASSWORD=admin123      # Admin password
JWT_SECRET_KEY=your-secret   # JWT signing key
SESSION_TIMEOUT=3600         # Session timeout (seconds)
```

### Troubleshooting

**Port already in use:**
```bash
# Find and kill process using port (macOS/Linux)
lsof -ti:9000 | xargs kill -9
lsof -ti:5500 | xargs kill -9
lsof -ti:5501 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

**Python module not found:**
```bash
pip install --upgrade -r bklv-backend/requirements.txt
```

**npm install fails:**
```bash
cd bklv-frontend
rm -rf node_modules package-lock.json
npm install
```

**Cannot connect to server:**
- Verify all services are running
- Check firewall settings
- Ensure ports are not blocked
- Try restarting all services

**Files not appearing:**
- Check file is published (not just local)
- Verify client is connected (check admin dashboard)
- Wait for auto-refresh or reload page
- Check browser console for errors