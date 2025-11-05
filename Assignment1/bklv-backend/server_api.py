"""
Flask API Server for File Sharing Application
Provides REST API endpoints for web UI to interact with the P2P file sharing system
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import socket
import json
import threading
import time
import os
from datetime import datetime
import jwt

from config import (
    SERVER_HOST, SERVER_PORT, 
    ADMIN_API_HOST, ADMIN_API_PORT,
    ADMIN_USERNAME, ADMIN_PASSWORD,
    JWT_SECRET_KEY, SESSION_TIMEOUT
)
from user_db import UserDB

# Initialize user database
user_db = UserDB('./data/users.json')

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Connection to central server
CENTRAL_HOST = SERVER_HOST
CENTRAL_PORT = SERVER_PORT

# Admin session storage (in production, use Redis or similar)
admin_sessions = {}

def send_json(conn, obj):
    data = json.dumps(obj) + '\n'
    conn.sendall(data.encode())

def recv_json(conn):
    buf = b''
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            return None
        buf += chunk
        if b'\n' in buf:
            line, rest = buf.split(b'\n', 1)
            return json.loads(line.decode())

def query_central_server(action, data=None):
    """Send a query to the central server and return response"""
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(10)
        conn.connect((CENTRAL_HOST, CENTRAL_PORT))
        send_json(conn, {"action": action, "data": data or {}})
        response = recv_json(conn)
        conn.close()
        return response
    except Exception as e:
        return {"status": "ERROR", "reason": str(e)}

# ===== USER MANAGEMENT (Centralized on Server) =====

@app.route('/api/user/register', methods=['POST'])
def user_register():
    """Register a new user - centralized on server"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    display_name = data.get('display_name')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    success, message, user = user_db.register_user(username, password, display_name)
    
    if success:
        # Generate JWT token
        token = jwt.encode({
            'username': username,
            'exp': time.time() + SESSION_TIMEOUT
        }, JWT_SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': message,
            'token': token,
            'user': user
        })
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/user/login', methods=['POST'])
def user_login():
    """Login an existing user - centralized on server"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    success, message, user = user_db.authenticate_user(username, password)
    
    if success:
        # Generate JWT token
        token = jwt.encode({
            'username': username,
            'exp': time.time() + SESSION_TIMEOUT
        }, JWT_SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': message,
            'token': token,
            'user': user
        })
    else:
        return jsonify({'success': False, 'error': message}), 401

@app.route('/api/user/verify', methods=['POST'])
def user_verify():
    """Verify user token"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'No token provided'}), 401
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        username = payload.get('username')
        user = user_db.get_user(username)
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            })
        else:
            return jsonify({'success': False, 'error': 'User not found'}), 404
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

# ===== ADMIN AUTHENTICATION =====

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # Generate JWT token
        token = jwt.encode({
            'username': username,
            'role': 'admin',
            'exp': time.time() + SESSION_TIMEOUT
        }, JWT_SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Invalid credentials'
        }), 401

@app.route('/api/admin/verify', methods=['POST'])
def admin_verify():
    """Verify admin token"""
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({'success': False, 'error': 'Token required'}), 400
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        if payload.get('role') == 'admin':
            return jsonify({'success': True, 'username': payload.get('username')})
        else:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

# Admin API endpoints (for server dashboard)
@app.route('/api/admin/registry', methods=['GET'])
def get_registry():
    """Get full registry information merged with user database"""
    response = query_central_server("LIST")
    
    # Get all registered users from database
    all_users = user_db.get_all_users()
    
    if response and response.get('status') == 'OK':
        registry = response.get('registry', {})
        
        # Build clients list from all users
        clients = []
        for username, user_data in all_users.items():
            # Check if user is in registry (online)
            registry_info = registry.get(username)
            
            if registry_info:
                # User is online
                clients.append({
                    'hostname': username,
                    'display_name': user_data.get('display_name', username),
                    'ip': registry_info['addr'][0],
                    'port': registry_info['addr'][1],
                    'files': registry_info.get('files', {}),
                    'file_count': len(registry_info.get('files', {})),
                    'last_seen': registry_info.get('last_seen', 0),
                    'connected_at': registry_info.get('connected_at', 0),
                    'status': 'online' if time.time() - registry_info.get('last_seen', 0) < 120 else 'offline',
                    'created_at': user_data.get('created_at'),
                    'last_login': user_data.get('last_login')
                })
            else:
                # User is offline (not in registry)
                clients.append({
                    'hostname': username,
                    'display_name': user_data.get('display_name', username),
                    'ip': 'N/A',
                    'port': 'N/A',
                    'files': {},
                    'file_count': 0,
                    'last_seen': 0,
                    'connected_at': 0,
                    'status': 'offline',
                    'created_at': user_data.get('created_at'),
                    'last_login': user_data.get('last_login')
                })
        
        # Calculate statistics
        total_files = sum(c['file_count'] for c in clients)
        active_clients = sum(1 for c in clients if c['status'] == 'online')
        
        return jsonify({
            'success': True,
            'stats': {
                'total_clients': len(clients),
                'total_files': total_files,
                'active_clients': active_clients
            },
            'clients': clients
        })
    else:
        # If server query fails, still show all users as offline
        clients = []
        for username, user_data in all_users.items():
            clients.append({
                'hostname': username,
                'display_name': user_data.get('display_name', username),
                'ip': 'N/A',
                'port': 'N/A',
                'files': {},
                'file_count': 0,
                'last_seen': 0,
                'connected_at': 0,
                'status': 'offline',
                'created_at': user_data.get('created_at'),
                'last_login': user_data.get('last_login')
            })
        
        return jsonify({
            'success': True,
            'stats': {
                'total_clients': len(clients),
                'total_files': 0,
                'active_clients': 0
            },
            'clients': clients
        })

@app.route('/api/admin/discover/<hostname>', methods=['GET'])
def admin_discover(hostname):
    """Discover files from a specific host"""
    response = query_central_server("DISCOVER", {"hostname": hostname})
    if response and response.get('status') == 'OK':
        return jsonify({
            'success': True,
            'hostname': hostname,
            'files': response.get('files', []),
            'addr': response.get('addr')
        })
    else:
        return jsonify({
            'success': False,
            'error': response.get('reason', 'Unknown error')
        }), 404

@app.route('/api/admin/ping/<hostname>', methods=['GET'])
def admin_ping(hostname):
    """Ping a specific host"""
    response = query_central_server("PING", {"hostname": hostname})
    return jsonify({
        'success': True,
        'hostname': hostname,
        'status': response.get('status') if response else 'ERROR'
    })

# Client API endpoints (for user interface)
# Note: These endpoints require client integration
# For full functionality, the client should run its own API server
# or we need to maintain persistent connections

@app.route('/api/client/network-files', methods=['GET'])
def get_network_files():
    """Get all files available on the network"""
    response = query_central_server("LIST")
    if response and response.get('status') == 'OK':
        registry = response.get('registry', {})
        
        # Flatten all files from all clients
        network_files = []
        for hostname, info in registry.items():
            files = info.get('files', {})
            for fname, finfo in files.items():
                network_files.append({
                    'filename': fname,
                    'size': finfo.get('size', 0),
                    'modified': finfo.get('modified', 0),
                    'published_at': finfo.get('published_at', 0),
                    'owner_hostname': hostname,
                    'owner_name': info.get('display_name', hostname),
                    'owner_ip': info['addr'][0],
                    'owner_port': info['addr'][1]
                })
        
        return jsonify({
            'success': True,
            'files': network_files
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to get network files'}), 500

@app.route('/api/client/search', methods=['GET'])
def search_files():
    """Search for files by name"""
    query = request.args.get('q', '').lower()
    
    response = query_central_server("LIST")
    if response and response.get('status') == 'OK':
        registry = response.get('registry', {})
        
        # Search through all files
        results = []
        for hostname, info in registry.items():
            files = info.get('files', {})
            for fname, finfo in files.items():
                if query in fname.lower():
                    results.append({
                        'filename': fname,
                        'size': finfo.get('size', 0),
                        'modified': finfo.get('modified', 0),
                        'owner_hostname': hostname,
                        'owner_name': info.get('display_name', hostname),
                        'owner_ip': info['addr'][0],
                        'owner_port': info['addr'][1]
                    })
        
        return jsonify({
            'success': True,
            'query': query,
            'results': results
        })
    else:
        return jsonify({'success': False, 'error': 'Search failed'}), 500

@app.route('/api/client/request-file', methods=['POST'])
def request_file():
    """Request download locations for a file"""
    data = request.json
    fname = data.get('filename')
    
    if not fname:
        return jsonify({'success': False, 'error': 'Filename required'}), 400
    
    response = query_central_server("REQUEST", {"fname": fname})
    if response and response.get('status') == 'FOUND':
        return jsonify({
            'success': True,
            'filename': fname,
            'hosts': response.get('hosts', [])
        })
    elif response and response.get('status') == 'NOTFOUND':
        return jsonify({
            'success': False,
            'error': 'File not found on network'
        }), 404
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to request file'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'File Sharing API',
        'timestamp': time.time()
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    response = query_central_server("LIST")
    if response and response.get('status') == 'OK':
        registry = response.get('registry', {})
        
        total_files = 0
        total_size = 0
        active_clients = 0
        
        for hostname, info in registry.items():
            files = info.get('files', {})
            total_files += len(files)
            for finfo in files.values():
                total_size += finfo.get('size', 0)
            
            if time.time() - info.get('last_seen', 0) < 120:
                active_clients += 1
        
        return jsonify({
            'success': True,
            'stats': {
                'total_clients': len(registry),
                'active_clients': active_clients,
                'total_files': total_files,
                'total_size': total_size,
                'timestamp': time.time()
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to get stats'}), 500

if __name__ == '__main__':
    print("=== P2P File Sharing Admin API Started ===")
    print(f"Admin API: http://{ADMIN_API_HOST}:{ADMIN_API_PORT}")
    print(f"Connecting to server at {CENTRAL_HOST}:{CENTRAL_PORT}")
    print("\nEndpoints:")
    print("  POST /api/admin/login - Admin login")
    print("  GET /api/admin/registry - Get registry")
    print("  GET /api/health - Health check")
    app.run(host=ADMIN_API_HOST, port=ADMIN_API_PORT, debug=True)
