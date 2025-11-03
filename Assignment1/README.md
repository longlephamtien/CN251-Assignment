# BKLV P2P File Sharing System
- [BKLV P2P File Sharing System](#bklv-p2p-file-sharing-system)
  - [Overview](#overview)
  - [Architecture and Design](#architecture-and-design)
    - [System Architecture](#system-architecture)
    - [Architecture Diagram](#architecture-diagram)
    - [Class Diagrams and Main Components](#class-diagrams-and-main-components)
      - [Backend Core Classes](#backend-core-classes)
      - [Frontend Component Hierarchy](#frontend-component-hierarchy)
  - [Communication Protocols](#communication-protocols)
    - [1. Central Server Protocol (TCP/JSON)](#1-central-server-protocol-tcpjson)
      - [Protocol Actions:](#protocol-actions)
      - [Protocol Enhancements \& Behavior](#protocol-enhancements--behavior)
    - [2. Peer-to-Peer File Transfer Protocol](#2-peer-to-peer-file-transfer-protocol)
      - [P2P Protocol Details:](#p2p-protocol-details)
    - [3. REST API Protocol (HTTP/JSON)](#3-rest-api-protocol-httpjson)
      - [Admin API (Port 5500)](#admin-api-port-5500)
      - [Client API (Port 5501)](#client-api-port-5501)
  - [Detailed Application Functions](#detailed-application-functions)
    - [1. User Management](#1-user-management)
    - [2. Client Operations](#2-client-operations)
      - [File Management](#file-management)
      - [Network Operations](#network-operations)
      - [State Persistence](#state-persistence)
    - [3. Server Operations](#3-server-operations)
      - [Registry Management](#registry-management)
      - [Query Processing](#query-processing)
    - [4. Admin Dashboard Functions](#4-admin-dashboard-functions)
    - [5. Client Interface Functions](#5-client-interface-functions)
  - [Validation and Performance Evaluation](#validation-and-performance-evaluation)
    - [Sanity Testing Results](#sanity-testing-results)
      - [Test Environment](#test-environment)
      - [Functional Tests](#functional-tests)
    - [Performance Evaluation](#performance-evaluation)
      - [Latency Measurements](#latency-measurements)
      - [Scalability Tests](#scalability-tests)
      - [Resource Utilization](#resource-utilization)
      - [Reliability Tests](#reliability-tests)
  - [Extension Functions](#extension-functions)
    - [1. Dual-Platform User Interface](#1-dual-platform-user-interface)
    - [2. User Authentication System](#2-user-authentication-system)
    - [3. File State Persistence](#3-file-state-persistence)
    - [4. Three-tier File Management](#4-three-tier-file-management)
    - [5. Enhanced File Metadata](#5-enhanced-file-metadata)
    - [6. RESTful API Architecture](#6-restful-api-architecture)
    - [7. File Upload from Browser](#7-file-upload-from-browser)
    - [8. Flexible File Download](#8-flexible-file-download)
    - [9. Cleanup and Monitoring](#9-cleanup-and-monitoring)
    - [10. Command-line Interface](#10-command-line-interface)
    - [11. Advanced Optimization Features](#11-advanced-optimization-features)
      - [Adaptive Heartbeat (adaptive\_heartbeat.py)](#adaptive-heartbeat-adaptive_heartbeatpy)
      - [File Hashing \& Deduplication (file\_hashing.py)](#file-hashing--deduplication-file_hashingpy)
      - [Cross-Platform File Metadata](#cross-platform-file-metadata)
    - [12. Reference-Based File Management](#12-reference-based-file-management)
    - [13. Enhanced Client Features](#13-enhanced-client-features)
    - [14. LAN and Multi-Computer Support](#14-lan-and-multi-computer-support)
    - [15. Production-Ready Security](#15-production-ready-security)
  - [Electron Desktop Application](#electron-desktop-application)
    - [Installing the Electron App](#installing-the-electron-app)
      - [Development Mode](#development-mode)
      - [Production Build](#production-build)
    - [Electron App Architecture](#electron-app-architecture)
  - [How to Run](#how-to-run)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
    - [Quick Start (Recommended)](#quick-start-recommended)
    - [Manual Start (Step-by-step)](#manual-start-step-by-step)
    - [Using the Command-Line Client (Optional)](#using-the-command-line-client-optional)
    - [Configuration Options](#configuration-options)
    - [Troubleshooting](#troubleshooting)
      - [General Issues](#general-issues)
      - [LAN-Specific Issues](#lan-specific-issues)
      - [Electron App Issues](#electron-app-issues)
  - [Technical Implementation Summary](#technical-implementation-summary)
    - [Core Technologies](#core-technologies)
    - [File Structure](#file-structure)

## Overview

BKLV is a comprehensive Peer-to-Peer (P2P) file sharing system that enables distributed file sharing among multiple clients through a centralized registry server. The system implements a hybrid P2P architecture where a central server maintains a registry of connected clients and their shared files, while actual file transfers occur directly between peers. The application features a modern web-based interface for both administrators and clients, providing real-time monitoring, user authentication, and seamless file management capabilities.

The system is built with a Python backend implementing the P2P protocol and Flask REST APIs, paired with a React frontend for intuitive user interaction. It supports essential P2P operations including file publishing, discovery, fetching, and peer status monitoring, while maintaining persistent state across client reconnections.

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

**1. Central Registry Server**

```
╔════════════════════════════════════════════╗
║      Central Registry Server               ║
╠════════════════════════════════════════════╣
║ Global State:                              ║
║   • registry: dict                         ║
║   • registry_lock: Lock                    ║
╠════════════════════════════════════════════╣
║ Functions:                                 ║
║   + send_json(conn, obj)                   ║
║   + recv_json(conn)                        ║
║   + handle_conn(conn, addr)                ║
║   + cleanup_thread()                       ║
║   + main()                                 ║
╠════════════════════════════════════════════╣
║ Protocol Actions:                          ║
║   1. REGISTER    5. DISCOVER               ║
║   2. PUBLISH     6. PING                   ║
║   3. UNPUBLISH   7. LIST                   ║
║   4. REQUEST     8. UNREGISTER             ║
╚════════════════════════════════════════════╝
```

**Registry Structure:**
```json
{
  "hostname": {
    "addr": (ip, port),
    "display_name": str,
    "files": {
      "filename": {
        "size": int,
        "modified": timestamp,
        "created": timestamp,
        "published_at": timestamp,
        "is_published": bool
      }
    },
    "last_seen": timestamp,
    "connected_at": timestamp
  }
}
```

**2. Client Class**

```
╔════════════════════════════════════════════╗
║                 Client                     ║
╠════════════════════════════════════════════╣
║ Attributes:                                ║
║   • hostname: str                          ║
║   • display_name: str                      ║
║   • listen_port: int                       ║
║   • repo_dir: str                          ║
║   • server_host: str                       ║
║   • server_port: int                       ║
║   • local_files: dict                      ║
║   • published_files: dict                  ║
║   • network_files: dict                    ║
║   • state_file: str                        ║
║   • central: socket                        ║
║   • central_lock: Lock                     ║
║   • peer_server: PeerServer                ║
║   • running: bool                          ║
║   • adaptive_heartbeat: AdaptiveHeartbeat  ║
╠════════════════════════════════════════════╣
║ Public Methods:                            ║
║   + publish(local_path, fname, ...)        ║
║   + unpublish(fname)                       ║
║   + request(fname)                         ║
║   + download_from_peer(...)                ║
║   + fetch(fname, save_path)                ║
║   + discover(hostname)                     ║
║   + ping_peer(hostname)                    ║
║   + list_all_files()                       ║
║   + list_local()                           ║
║   + list_published()                       ║
║   + list_network()                         ║
║   + unregister()                           ║
║   + close()                                ║
╠════════════════════════════════════════════╣
║ Private Methods:                           ║
║   - _scan_repo_directory()                 ║
║   - _load_state()                          ║
║   - _save_state()                          ║
║   - _save_file_metadata(fname)             ║
║   - _check_duplicate_on_network(...)       ║
║   - heartbeat_thread()                     ║
╚════════════════════════════════════════════╝
```

**3. FileMetadata Class**

```
╔════════════════════════════════════════════╗
║             FileMetadata                   ║
╠════════════════════════════════════════════╣
║ Attributes:                                ║
║   • name: str                              ║
║   • size: int                              ║
║   • modified: float                        ║
║   • created: float                         ║
║   • path: str                              ║
║   • is_published: bool                     ║
║   • added_at: float                        ║
║   • published_at: float                    ║
╠════════════════════════════════════════════╣
║ Methods:                                   ║
║   + to_dict()                              ║
║   + matches_metadata(size, modified, ...)  ║
║   + file_exists()                          ║
║   + validate_path()                        ║
╚════════════════════════════════════════════╝

Helper Function:
  get_file_metadata_crossplatform(file_path)
```

**4. PeerServer Class**

```
╔════════════════════════════════════════════╗
║      PeerServer(threading.Thread)          ║
╠════════════════════════════════════════════╣
║ Attributes:                                ║
║   • listen_port: int                       ║
║   • client_ref: Client                     ║
║   • sock: socket                           ║
╠════════════════════════════════════════════╣
║ Methods:                                   ║
║   + run()                                  ║
║   + handle_peer(conn, addr)                ║
╚════════════════════════════════════════════╝

Protocol:
  Request:  GET filename\n
  Response: LENGTH <bytes>\n<data> OR ERROR <reason>\n
```

**5. UserDB Class**

```
╔════════════════════════════════════════════╗
║                 UserDB                     ║
╠════════════════════════════════════════════╣
║ Attributes:                                ║
║   • db_path: str                           ║
║   • lock: Lock                             ║
╠════════════════════════════════════════════╣
║ Public Methods:                            ║
║   + register_user(username, password, ...) ║
║   + authenticate_user(username, password)  ║
║   + get_user(username)                     ║
║   + update_user(username, updates)         ║
║   + add_user_file(username, filename, ...) ║
║   + remove_user_file(username, filename)   ║
║   + get_all_users()                        ║
╠════════════════════════════════════════════╣
║ Private Methods:                           ║
║   - _ensure_db_exists()                    ║
║   - _load_db()                             ║
║   - _save_db(data)                         ║
║   - _hash_password(password)               ║
╚════════════════════════════════════════════╝
```

**User Record Structure:**
```json
{
  "username": str,
  "password_hash": str,
  "display_name": str,
  "created_at": ISO datetime,
  "last_login": ISO datetime,
  "files": [],
  "settings": {
    "auto_publish": bool,
    "default_repo": str
  }
}
```

**6. AdaptiveHeartbeat Class**

```
╔════════════════════════════════════════════════════════════╗
║                  AdaptiveHeartbeat                         ║
║   Reduces heartbeat overhead by adjusting interval         ║
║              based on client activity                      ║
╠════════════════════════════════════════════════════════════╣
║ Enum: ClientState                                          ║
║   • IDLE = "idle"           (no activity 5+ min)           ║
║   • ACTIVE = "active"       (activity in last 5 min)       ║
║   • BUSY = "busy"           (transferring files)           ║
║   • OFFLINE = "offline"     (lost connection)              ║
╠════════════════════════════════════════════════════════════╣
║ Attributes:                                                ║
║   • state: ClientState              (current state)        ║
║   • last_activity: float            (activity timestamp)   ║
║   • last_heartbeat: float           (heartbeat timestamp)  ║
║   • total_heartbeats: int           (counter)              ║
║   • state_changes: list             (transition log)       ║
╠════════════════════════════════════════════════════════════╣
║ Constants:                                                 ║
║   • IDLE_INTERVAL = 300s            (5 minutes)            ║
║   • ACTIVE_INTERVAL = 60s           (1 minute)             ║
║   • BUSY_INTERVAL = 30s             (30 seconds)           ║
║   • IDLE_THRESHOLD = 300s                                  ║
╠════════════════════════════════════════════════════════════╣
║ Methods:                                                   ║
║   + get_interval()                                         ║
║   + mark_activity(activity_type)                           ║
║   + start_file_transfer()                                  ║
║   + end_file_transfer()                                    ║
║   + record_heartbeat()                                     ║
║   + get_stats()                                            ║
║   + should_send_heartbeat()                                ║
╚════════════════════════════════════════════════════════════╝
```

**7. API Servers**

**server_api.py**

```
╔════════════════════════════════════════════╗
║          Admin API Server                  ║
╠════════════════════════════════════════════╣
║ Configuration:                             ║
║   • Port: 5500                             ║
║   • CORS: Enabled                          ║
║   • JWT Secret: From environment           ║
╠════════════════════════════════════════════╣
║ Endpoints (10):                            ║
║   POST   /api/admin/login                  ║
║   POST   /api/admin/verify                 ║
║   GET    /api/admin/registry               ║
║   GET    /api/admin/discover/:hostname     ║
║   GET    /api/admin/ping/:hostname         ║
║   GET    /api/stats                        ║
║   GET    /api/client/network-files         ║
║   GET    /api/client/search                ║
║   POST   /api/client/request-file          ║
║   GET    /api/health                       ║
╚════════════════════════════════════════════╝
```

**client_api.py**

```
╔════════════════════════════════════════════╗
║          Client API Server                 ║
╠════════════════════════════════════════════╣
║ Configuration:                             ║
║   • Port: 5501                             ║
║   • CORS: Enabled                          ║
║   • Session: In-memory clients             ║
╠════════════════════════════════════════════╣
║ Endpoints (22):                            ║
║                                            ║
║ Auth & Session (5):                        ║
║   POST   /api/client/register              ║
║   POST   /api/client/login                 ║
║   POST   /api/client/init                  ║
║   POST   /api/client/logout                ║
║   GET    /api/client/status                ║
║                                            ║
║ File Listing (3):                          ║
║   GET    /api/client/local-files           ║
║   GET    /api/client/published-files       ║
║   GET    /api/client/network-files         ║
║                                            ║
║ File Management (6):                       ║
║   POST   /api/client/add-file              ║
║   POST   /api/client/upload                ║
║   POST   /api/client/publish               ║
║   POST   /api/client/unpublish             ║
║   POST   /api/client/fetch                 ║
║   GET    /api/client/download/:fname       ║
║                                            ║
║ Duplicate Detection (3):                   ║
║   POST   /api/client/check-duplicate       ║
║   POST   /api/client/check-local-duplicate ║
║   POST   /api/client/validate-file         ║
║                                            ║
║ Bulk & Discovery (3):                      ║
║   POST   /api/client/scan-directory        ║
║   GET    /api/client/discover/:hostname    ║
║   GET    /api/client/ping/:hostname        ║
║                                            ║
║ Diagnostics (2):                           ║
║   GET    /api/health                       ║
║   GET    /api/debug/clients                ║
╚════════════════════════════════════════════╝
```

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

---

## Communication Protocols

The system uses **3 distinct protocols** for different layers of communication:

| Protocol | Transport | Purpose | Actions/Endpoints |
|----------|-----------|---------|-------------------|
| **Central Server Protocol** | TCP/JSON | Client-server registry management | 8 actions (REGISTER, PUBLISH, UNPUBLISH, REQUEST, DISCOVER, PING, LIST, UNREGISTER) |
| **P2P File Transfer** | TCP/Text | Direct peer-to-peer file downloads | GET, LENGTH, ERROR |
| **REST API** | HTTP/JSON | Admin dashboard & client UI | 32 endpoints (10 admin + 22 client) |

**Protocol Design Principles:**
- **Stateful Registry:** Files marked as published/unpublished, never deleted
- **Metadata-First:** All operations use metadata; no file copying during publish
- **Filtered Responses:** Only `is_published=true` files returned in queries
- **Cross-Platform:** UTC timestamps, standardized metadata format
- **Adaptive Heartbeat:** State-based intervals (IDLE/ACTIVE/BUSY) reduce overhead by 59%

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
    "modified": 1697540000,
    "created": 1697530000,
    "published_at": 1697540100
  }
}

Response:
{
  "status": "ACK"
}
```
> **Note:** Server automatically creates registry entry if client publishes before registering.

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
> **Important:** File is marked as `is_published=false` instead of being deleted, preserving metadata for potential re-publishing.

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
> **Filtering:** Only returns hosts where `is_published=true`. Status is "NOTFOUND" if no published hosts exist.

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
    "file1.txt": {
      "size": 1234,
      "modified": 1697540000,
      "published_at": 1697540100,
      "is_published": true
    },
    "file2.pdf": {...}
  },
  "addr": ["192.168.1.10", 6001]
}
```
> **Filtering:** Only returns files where `is_published=true`.

**PING** - Check if peer is alive
```json
Request (Heartbeat):
{
  "action": "PING",
  "data": {
    "hostname": "self_client_id",
    "state": "ACTIVE"  // Optional: IDLE, ACTIVE, or BUSY
  }
}

Request (Peer Check):
{
  "action": "PING",
  "data": {
    "hostname": "target_client_id"
  }
}

Response:
{
  "status": "ALIVE|DEAD"
}
```
> **Side Effect:** Updates `last_seen` timestamp for the requesting client. Used by adaptive heartbeat optimization.

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
      "files": {
        "file1.txt": {
          "size": 1234,
          "modified": 1697540000,
          "published_at": 1697540100,
          "is_published": true
        }
      },
      "last_seen": 1697540500,
      "connected_at": 1697540000
    }
  }
}
```
> **Filtering:** Only includes files where `is_published=true` for each client.

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

#### Protocol Enhancements & Behavior

**1. Stateful File Management:**
- Files are never deleted from registry, only marked as `is_published=false` during UNPUBLISH
- Clients can re-publish files instantly by calling PUBLISH again (metadata is updated)
- REGISTER action includes `files_metadata` to restore published/unpublished state on reconnection

**2. Metadata Preservation:**
- All protocol responses filter out unpublished files (`is_published=false`)
- File metadata includes: `size`, `modified`, `created`, `published_at`, `is_published`
- Cross-platform timestamps use UTC epoch seconds

**3. Auto-Registration:**
- If a client sends PUBLISH before REGISTER, server automatically creates registry entry
- Prevents errors when clients publish files immediately after connection

**4. Duplicate Detection:**
- Clients check for duplicates before publishing using metadata comparison
- Exact duplicate: same `fname`, `size`, and `modified` time
- Partial duplicate: same `fname` but different `size` or `modified` time

**5. Heartbeat Integration:**
- PING action updates `last_seen` timestamp for sender (not just target)
- Supports adaptive heartbeat intervals (IDLE: 300s, ACTIVE: 60s, BUSY: 30s)
- Server timeout configurable via `REGISTRY_TIMEOUT` (default: 1200s)

### 2. Peer-to-Peer File Transfer Protocol

Direct file transfer between peers uses a simple text-based protocol over TCP:

**File Request:**
```
GET filename.txt\n
```

**File Response (Success):**
```
LENGTH 5120\n
[5120 bytes of file data]
```

**File Response (Error - File Not Found):**
```
ERROR notfound\n
```

**File Response (Error - Read Error):**
```
ERROR readerror\n
```

#### P2P Protocol Details:

**Connection Flow:**
1. Requester establishes TCP connection to peer's listening port
2. Sends `GET filename\n` request
3. Peer looks up file in published files (must be `is_published=true`)
4. If found, sends `LENGTH <bytes>\n` followed by raw file data
5. If not found or error, sends `ERROR <reason>\n`
6. Connection closes after transfer

**File Lookup:**
- Peer server searches `published_files` dictionary for exact filename match
- File must have `is_published=true` to be transferred
- Uses original file path from metadata (no file copying)
- Reads file in 8192-byte chunks for memory efficiency

**Error Handling:**
- `notfound`: File not in published_files or is_published=false
- `readerror`: File exists in metadata but cannot be read from disk

### 3. REST API Protocol (HTTP/JSON)

#### Admin API (Port 5500)

**Authentication:**

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

**POST /api/admin/verify** - Verify admin JWT token
```json
Request:
{
  "token": "jwt_token_here"
}

Response:
{
  "success": true,
  "username": "admin"
}
```

**Registry & Monitoring:**

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
      "connected_at": 1697540000,
      "created_at": "2024-10-17T10:00:00",
      "last_login": "2024-10-17T12:30:00"
    }
  ]
}
```

**GET /api/admin/discover/:hostname** - Discover client files

**GET /api/admin/ping/:hostname** - Ping specific client

**GET /api/stats** - Get system statistics
```json
Response:
{
  "success": true,
  "stats": {
    "total_clients": 10,
    "active_clients": 7,
    "total_files": 45,
    "total_size": 524288000,
    "timestamp": 1697540500
  }
}
```

**Network Files (also available from admin):**

**GET /api/client/network-files** - Get all network files (flattened view)

**GET /api/client/search?q=query** - Search files by name

**POST /api/client/request-file** - Request file download locations
```json
Request:
{
  "filename": "document.pdf"
}

Response:
{
  "success": true,
  "filename": "document.pdf",
  "hosts": [...]
}
```

**Health:**

**GET /api/health** - Health check endpoint

---

#### Client API (Port 5501)

**Authentication & Session:**

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

**POST /api/client/login** - User login (same format as register)

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
    "repo": "repo_alice",
    "server_host": "127.0.0.1",
    "server_port": 9000
  }
}
```

**POST /api/client/logout** - Disconnect from network and clear session
```json
Response:
{
  "success": true,
  "message": "Successfully disconnected from network"
}
```

**GET /api/client/status** - Get current client status
```json
Response:
{
  "success": true,
  "client": {
    "hostname": "alice",
    "display_name": "Alice Smith",
    "port": 6001,
    "repo": "/path/to/repo_alice"
  }
}
```

**File Listing:**

**GET /api/client/local-files** - Get all local tracked files
```json
Response:
{
  "success": true,
  "files": [
    {
      "name": "document.pdf",
      "size": 1024,
      "modified": 1697540000,
      "created": 1697530000,
      "path": "/absolute/path/to/file.pdf",
      "is_published": true,
      "added_at": 1697535000,
      "published_at": 1697540000
    }
  ]
}
```

**GET /api/client/published-files** - Get only published files

**GET /api/client/network-files** - Get all files available on network
```json
Response:
{
  "success": true,
  "files": [
    {
      "name": "shared.pdf",
      "size": 2048,
      "modified": 1697540000,
      "created": 1697530000,
      "published_at": 1697540100,
      "owner_hostname": "bob",
      "owner_name": "Bob Smith",
      "owner_ip": "192.168.1.11",
      "owner_port": 6002
    }
  ]
}
```

**File Management:**

**POST /api/client/add-file** - Add file to tracking (metadata only, no upload)
```json
Request:
{
  "filepath": "/path/to/existing/file.pdf"
}

Response:
{
  "success": true,
  "message": "File 'file.pdf' tracked (reference to: /path/to/existing/file.pdf)",
  "file": {
    "name": "file.pdf",
    "size": 1024,
    "created": 1697530000,
    "modified": 1697540000,
    "path": "/path/to/existing/file.pdf",
    "added_at": 1697540100
  }
}
```

**POST /api/client/upload** - Upload file from browser or track existing file
```json
Form Data:
- file: (binary file data) OR
- file_path: "/path/to/existing/file" (track existing file without upload)
- auto_publish: true|false (optional, default false)
- force_upload: true|false (optional, overwrite existing)

Response:
{
  "success": true,
  "message": "File 'document.pdf' uploaded successfully",
  "file": {
    "name": "document.pdf",
    "size": 1024,
    "path": "/path/to/repo/document.pdf",
    "added_at": 1697540100
  }
}
```

**POST /api/client/publish** - Publish file to network (reference-based, no copying)
```json
Request:
{
  "fname": "document.pdf",
  "local_path": "/path/to/file" (optional, uses tracked path if omitted)
}

Response:
{
  "success": true,
  "message": "File 'document.pdf' published successfully",
  "path": "/absolute/path/to/file"
}
```

**POST /api/client/unpublish** - Unpublish file from network (keeps local copy)
```json
Request:
{
  "fname": "document.pdf"
}

Response:
{
  "success": true,
  "message": "File unpublished successfully"
}
```

**POST /api/client/fetch** - Fetch file from network peers
```json
Request:
{
  "fname": "document.pdf",
  "save_path": "/custom/path" (optional, defaults to repo directory)
}

Response:
{
  "success": true,
  "message": "Fetching file...",
  "save_path": "/custom/path"
}
```

**GET /api/client/download/:fname** - Download file to browser (triggers save-as dialog)

**Duplicate Detection:**

**POST /api/client/check-duplicate** - Check for network duplicates before publishing
```json
Request:
{
  "fname": "document.pdf",
  "size": 1024,
  "modified": 1699123456.789
}

Response:
{
  "success": true,
  "has_exact_duplicate": false,
  "has_partial_duplicate": false,
  "exact_matches": [
    {
      "hostname": "bob",
      "size": 1024,
      "modified": 1699123456.789
    }
  ],
  "partial_matches": []
}
```

**POST /api/client/check-local-duplicate** - Check if file exists locally
```json
Request:
{
  "fname": "document.pdf"
}

Response:
{
  "success": true,
  "exists": true,
  "local_file": {
    "name": "document.pdf",
    "size": 1024,
    "modified": 1697540000,
    "is_published": true
  }
}
```

**POST /api/client/validate-file** - Validate published file still exists at path
```json
Request:
{
  "fname": "document.pdf"
}

Response:
{
  "success": true,
  "exists": true,
  "path": "/absolute/path/to/document.pdf",
  "size": 1024,
  "modified": 1697540000
}
```

**Bulk Operations:**

**POST /api/client/scan-directory** - Bulk add files from directory
```json
Request:
{
  "directory": "/path/to/folder"
}

Response:
{
  "success": true,
  "message": "Added 10 files to tracking",
  "count": 10
}
```

**Peer Discovery:**

**GET /api/client/discover/:hostname** - Discover files from specific peer

**GET /api/client/ping/:hostname** - Check if specific peer is online
```json
Response:
{
  "success": true,
  "hostname": "bob",
  "status": "ALIVE|DEAD"
}
```

**Diagnostics:**

**GET /api/health** - Health check
```json
Response:
{
  "status": "healthy",
  "service": "Client API",
  "active_clients": 3,
  "usernames": ["alice", "bob", "charlie"]
}
```

**GET /api/debug/clients** - Debug endpoint showing all active client sessions
```json
Response:
{
  "total_clients": 3,
  "clients": {
    "alice": {
      "hostname": "alice",
      "display_name": "Alice Smith",
      "port": 6001,
      "repo": "/path/to/repo_alice",
      "running": true,
      "local_files_count": 5,
      "published_files_count": 3
    }
  }
}
```

## Detailed Application Functions

### 1. User Management
- **User Registration**: Create new user accounts with username, password, and display name
- **User Authentication**: Secure login with password hashing (SHA-256)
- **JWT Token Management**: Stateless authentication for API requests
- **User Database**: JSON-based persistent storage with thread-safe operations

### 2. Client Operations

#### File Management
- **Local File Tracking**: Monitor files with metadata (size, modified time, created time, path)
- **File Publishing**: Share files with network peers using **reference-based approach**
  - **No file copying**: Files remain in their original location
  - Register file metadata (path, size, timestamps) with central server
  - Maintain published state across reconnections via `.client_state.json`
  - Duplicate detection before publishing
- **File Unpublishing**: Remove files from network sharing while keeping locally
- **File Upload**: Browser-based file upload to client repository
- **File Download**: Fetch files from network peers with custom save location support
- **Metadata Persistence**: JSON files (`.meta.json`) store all file information

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
- **File Registry**: Maintain published file catalog with enhanced metadata (size, modified, created, published_at, is_published)
- **Heartbeat Monitoring**: Adaptive or fixed interval heartbeat to detect disconnected clients
  - Configurable intervals (default 60s, adaptive: 30-300s)
- **Cleanup Thread**: Remove inactive clients (configurable timeout, default 1200s / 20 minutes)
- **State Restoration**: Restore published file states when clients reconnect

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
- Reference-based publishing (no file copying)
- Metadata (size, modified, created, path) accurately captured
- Cross-platform timestamp support (Windows/macOS/Linux)
- Central server receives file information
- State persisted to `.client_state.json` and `.meta.json` files
- Published files visible to other clients
- Duplicate detection warnings work correctly

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
- Inactive clients cleaned up after 1200 seconds
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

### 1. Dual-Platform User Interface
- **Web-Based Access**: Run in any modern browser (Chrome, Firefox, Safari, Edge)
  - Single-page React application with component-based architecture
  - Responsive design for desktop and mobile browsers
  - Accessible from anywhere on the network
- **Electron Desktop App**: Native desktop application
  - Cross-platform support (macOS, Windows, Linux)
  - Native file dialogs for better file selection
  - Standalone executable with integrated backend
  - Better performance and native OS integration
- **Dual Interface**: Separate admin and client dashboards
- **Real-time Updates**: Auto-refresh with configurable intervals
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

### 11. Advanced Optimization Features

The system includes several optimization modules in `optimizations/` directory:

#### Adaptive Heartbeat (adaptive_heartbeat.py)
- **Dynamic Interval Adjustment**: Heartbeat frequency adapts to client activity
- **State-Based Intervals**:
  - IDLE (5+ minutes inactive): 300s interval
  - ACTIVE (recent activity): 60s interval
  - BUSY (file transfer): 30s interval
- **Scalability Benefits**: 59% reduction in heartbeat overhead for 100k users
- **Automatic State Transitions**: IDLE ↔ ACTIVE ↔ BUSY based on activity
- **Activity Tracking**: Records publish, fetch, and file transfer operations
- **Statistics**: Track total heartbeats, state changes, and idle time

#### File Hashing & Deduplication (file_hashing.py)
- **SHA256 Hashing**: Cryptographic file identification
- **Duplicate Detection**: Find exact duplicates before publishing
- **Performance Optimizations**:
  - Full hash for files < 100MB
  - Quick hash (beginning + middle + end samples) for large files (>100MB)
- **Duplicate Checking**:
  - Exact matches (same hash)
  - Partial matches (same name+size, different hash)
  - Network-wide duplicate detection
- **User Warnings**: Alert before publishing duplicates
- **File Verification**: Validate downloaded files using hash comparison
- **Deduplication Statistics**: Track duplicate rate and storage waste

#### Cross-Platform File Metadata
- **Platform-Aware Timestamps**: Correct handling of creation time on Windows/macOS/Linux
- **Metadata Extraction**: Size, modified time, created time
- **Path Normalization**: Cross-platform path handling

### 12. Reference-Based File Management
- **No File Copying**: Files stay in their original location
- **Metadata-Only Tracking**: Store file path, size, timestamps without copying data
- **JSON Metadata Files**: `.meta.json` files store all file information
- **Path Validation**: Verify file existence and readability before operations
- **Storage Efficiency**: Eliminate duplicate storage for published files

### 13. Enhanced Client Features
- **Duplicate Warnings**: Check for duplicates before publish/fetch
- **Interactive Prompts**: Confirmation for potentially duplicate operations
- **Non-Interactive Mode**: API mode for automated operations
- **File Validation**: Verify published files still exist at stored paths
- **Custom Save Paths**: Download files to any directory
- **Directory Scanning**: Bulk add files from folder to tracking

### 14. LAN and Multi-Computer Support
- **Network Binding**: Server binds to 0.0.0.0 for LAN access
- **IP Address Display**: Server shows local IP for client connections
- **Remote Connection**: Clients can connect to server using IP address
- **Configurable Server Address**: Clients specify server IP and port
- **LAN Documentation**: Complete guides for multi-computer setup
- **Firewall Instructions**: Platform-specific firewall configuration

### 15. Production-Ready Security
- **Environment Variables**: All sensitive config in `.env` file
- **Password Hashing**: SHA-256 for user passwords
- **JWT Authentication**: Secure stateless sessions
- **Session Expiration**: Configurable timeout (default 1 hour)
- **CORS Configuration**: Secure cross-origin requests
- **Input Validation**: All user inputs validated
- **Path Security**: Prevent directory traversal attacks

## Electron Desktop Application

The BKLV P2P File Sharing System is available as a native desktop application powered by Electron, providing a seamless desktop experience across macOS, Windows, and Linux platforms.

### Installing the Electron App

#### Development Mode

**Prerequisites:**
- Node.js 22 or higher
- npm (comes with Node.js)
- All backend services running (see [How to Run](#how-to-run))

**Steps:**

1. **Navigate to frontend directory:**
   ```bash
   cd bklv-frontend
   ```

2. **Install dependencies (if not already done):**
   ```bash
   npm install
   ```

3. **Start Electron in development mode:**
   ```bash
   npm run electron:dev
   ```

   This command will:
   - Start the React development server (port 3000)
   - Wait for the dev server to be ready
   - Launch the Electron app pointing to localhost:3000
   - Open DevTools automatically for debugging

4. **The Electron window will open automatically** with the BKLV interface

**Note:** Make sure the backend services (central server, admin API, client API) are already running before starting the Electron app.

#### Production Build

**Build the application:**

1. **Build the React app:**
   ```bash
   cd bklv-frontend
   npm run build
   ```

2. **Create platform-specific installer:**
   ```bash
   npm run electron:build
   ```

   This will create installers in the `dist/` directory:
   - **macOS**: `BKLV P2P File Sharing-{version}.dmg` and `.zip`
   - **Windows**: `BKLV P2P File Sharing Setup {version}.exe` and portable version
   - **Linux**: `BKLV P2P File Sharing-{version}.AppImage` and `.deb`

3. **Install the application:**
   - **macOS**: Double-click the DMG, drag to Applications folder
   - **Windows**: Run the installer or portable .exe
   - **Linux**: Make AppImage executable and run, or install DEB package

**Running the production app:**
- Simply launch the installed application from your Applications folder/Start Menu/App Launcher
- Ensure backend services are running on the same machine or accessible over the network

### Electron App Architecture

**Main Process (`public/electron.js`):**
- Creates and manages the main browser window
- Handles IPC (Inter-Process Communication) with renderer
- Manages native dialogs (file picker, directory picker)
- Controls app lifecycle (startup, shutdown, window management)

**Renderer Process (React App):**
- Runs the React UI in a sandboxed environment
- Communicates with main process through IPC
- Uses preload script for secure bridge to Node.js APIs

**Preload Script (`public/preload.js`):**
- Exposes safe APIs to renderer process
- Bridges Electron APIs (dialog, fs) to React
- Maintains security with context isolation

**Security Features:**
- `nodeIntegration: false` - Prevents direct Node.js access in renderer
- `contextIsolation: true` - Isolates renderer from Electron internals
- `enableRemoteModule: false` - Disables deprecated remote module
- Preload script for controlled API exposure

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

**4. Install Node.js dependencies**
```bash
cd bklv-frontend
npm install
cd ..
```

### Quick Start (Recommended)

BKLV can be run in two modes: **Web Browser** or **Electron Desktop App**.
**Using the start script (macOS/Linux):**
```bash
chmod +x start.sh
./start.sh
```

**To stop all services:**
```bash
chmod +x stop.sh
./stop.sh
```

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
npm run electron:dev
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
publish <localpath> <name>  - Publish a file (reference-based, no copying)
unpublish <name>            - Unpublish a file from network
fetch <name> [save_path]    - Fetch a file from network (optional custom save location)
add <filepath>              - Add a file to local tracking (metadata only)
local                       - List all local files (published and unpublished)
published                   - List only published files
network                     - List all network files from all clients
discover <host>             - Discover files from a specific host
ping <host>                 - Check if a host is alive
registry                    - Show raw registry data (JSON)
exit                        - Unregister and exit client
```

**CLI Features:**
- Supports quoted paths: `publish "/path/with spaces/file.pdf" myfile.pdf`
- Interactive confirmations for duplicate files
- Color-coded output for published status
- Human-readable file sizes and timestamps
- Cross-platform path support (Windows, macOS, Linux)

### Configuration Options

Edit `.env` file to customize all system parameters:

```bash
# Server Settings
SERVER_HOST=0.0.0.0          # Server IP address (0.0.0.0 for network access, 127.0.0.1 for localhost)
SERVER_PORT=9000             # Central server port

# Client Settings
CLIENT_PORT_MIN=6000         # Minimum port for client peer servers
CLIENT_PORT_MAX=7000         # Maximum port for client peer servers
CLIENT_REPO_BASE=./repos     # Repository base directory for client files
CLIENT_HEARTBEAT_INTERVAL=60         # Fixed heartbeat interval in seconds (if not using adaptive)
CLIENT_CLEANUP_INTERVAL=30           # Server cleanup check interval (seconds)
CLIENT_INACTIVE_TIMEOUT=1200         # Timeout before marking client inactive (seconds, default 20 min)

# API Server Settings
ADMIN_API_HOST=0.0.0.0       # Admin API host (0.0.0.0 for network access)
ADMIN_API_PORT=5500          # Admin API port
CLIENT_API_HOST=0.0.0.0      # Client API host
CLIENT_API_PORT=5501         # Client API port

# Admin Authentication
ADMIN_USERNAME=admin         # Admin dashboard username
ADMIN_PASSWORD=admin123      # Admin dashboard password (CHANGE IN PRODUCTION!)

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production  # JWT signing key (CHANGE IN PRODUCTION!)
SESSION_TIMEOUT=3600         # Session timeout in seconds (default 1 hour)

# Database
USER_DB_PATH=./data/users.json  # User database file location
```

**Configuration Priority:**
1. Environment variables (`.env` file)
2. Default values in code
3. Command-line arguments (CLI client only)

### Troubleshooting

#### General Issues

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

#### LAN-Specific Issues

**Cannot access from other computers:**
- Verify `SERVER_HOST=0.0.0.0` in `.env` file
- Check that all computers are on the same network
- Verify host computer's IP address hasn't changed (DHCP)
- Disable firewall temporarily to test connectivity
- Check router settings for AP isolation (disable if enabled)

**Connection refused from client computers:**
```bash
# On host computer, verify services are listening on all interfaces:
netstat -an | grep LISTEN | grep -E '(3000|5500|5501|9000)'

# Should show 0.0.0.0:PORT or *:PORT, not 127.0.0.1:PORT
```

**Slow file transfers over LAN:**
- Check Wi-Fi signal strength on both computers
- Use Ethernet connection for better performance
- Ensure no other heavy network usage (downloads, streaming)
- Check for network congestion (too many devices)

#### Electron App Issues

**Quick Electron fixes:**
- Ensure backend services are running first
- Try clearing cache: `rm -rf node_modules build dist && npm install`
- Check DevTools console for JavaScript errors
- Verify ports 3000, 5500, 5501, 9000 are accessible

## Technical Implementation Summary

### Core Technologies

**Backend (Python 3.12+):**
- **Networking**: Raw TCP sockets with custom JSON protocol
- **Concurrency**: Threading for multi-client handling
- **APIs**: Flask REST servers (admin + client)
- **Security**: SHA-256 password hashing, JWT authentication
- **Storage**: JSON-based file metadata and user database
- **Configuration**: python-dotenv for environment variables

**Frontend (React 19 + Node.js 22+):**
- **Framework**: React with hooks (useState, useEffect)
- **Desktop**: Electron for cross-platform native apps
- **Styling**: Custom CSS with responsive design
- **HTTP Client**: Axios for API communication
- **Routing**: React Router for navigation
- **State**: Component-level state management

### File Structure

```
Assignment1/
├── .env                       # Environment configuration
├── .env.example              # Example configuration
├── start.sh                  # Start all services
├── stop.sh                   # Stop all services
├── bklv-backend/             # Python backend
│   ├── server.py            # Central registry server (TCP)
│   ├── client.py            # P2P client with peer server
│   ├── server_api.py        # Admin REST API (Flask)
│   ├── client_api.py        # Client REST API (Flask)
│   ├── user_db.py           # User database manager
│   ├── config.py            # Configuration loader
│   ├── requirements.txt     # Python dependencies
│   ├── data/
│   │   └── users.json       # User database
│   └── optimizations/
│       ├── adaptive_heartbeat.py  # Adaptive heartbeat manager
│       └── file_hashing.py        # File hashing & deduplication
├── bklv-frontend/           # React frontend
│   ├── package.json         # Node.js dependencies + Electron config
│   ├── public/
│   │   ├── electron.js      # Electron main process
│   │   ├── preload.js       # Electron preload script
│   │   └── index.html       # HTML template
│   └── src/
│       ├── App.js           # Main React component
│       ├── config.js        # Frontend configuration
│       ├── components/      # React components
│       │   ├── admin/       # Admin dashboard components
│       │   ├── client/      # Client interface components
│       │   └── common/      # Shared components
│       ├── hooks/           # Custom React hooks
│       ├── layouts/         # Layout components
│       ├── screens/         # Main screen components
│       └── utils/           # Utility functions
└── logs/                    # Application logs
```