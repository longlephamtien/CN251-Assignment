"""
Client API Wrapper
Provides a Flask API interface for a client instance
This allows the web UI to control a local client
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import socket
import threading
import json
import os
import sys
from datetime import datetime
import time
import jwt

# Import the Client class and config
from client import Client, send_json, recv_json, CENTRAL_HOST, CENTRAL_PORT
from config import CLIENT_API_HOST, CLIENT_API_PORT, JWT_SECRET_KEY, SESSION_TIMEOUT
from user_db import UserDB, find_available_port

app = Flask(__name__)
CORS(app)

# Initialize user database
user_db = UserDB()

# Session-based client instances - stores multiple clients by username
client_instances = {}
clients_lock = threading.Lock()

def get_client(username=None):
    """Get the client instance for a specific user"""
    if username is None:
        # Try to extract username from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
                username = payload.get('username')
                print(f"[DEBUG] Extracted username '{username}' from token")
            except jwt.ExpiredSignatureError:
                print("[ERROR] Token has expired")
                raise Exception("Token has expired. Please login again.")
            except jwt.InvalidTokenError as e:
                print(f"[ERROR] Invalid token: {e}")
                raise Exception("Invalid token. Please login again.")
            except Exception as e:
                print(f"[ERROR] Token decode error: {e}")
                raise Exception("Invalid or expired token")
        
        if username is None:
            print("[ERROR] No username in token or Authorization header missing")
            raise Exception("Username not provided and token not found")
    
    with clients_lock:
        if username not in client_instances:
            print(f"[ERROR] No client instance for user '{username}'. Available: {list(client_instances.keys())}")
            raise Exception(f"Client not initialized for user '{username}'. Call /api/client/init first.")
        print(f"[DEBUG] Found client instance for user '{username}'")
        return client_instances[username]

@app.route('/api/client/register', methods=['POST'])
def register_user():
    """Register a new user"""
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

@app.route('/api/client/login', methods=['POST'])
def login_user():
    """Login an existing user"""
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

@app.route('/api/client/init', methods=['POST'])
def init_client():
    """Initialize a new client session for authenticated user"""
    
    data = request.json
    username = data.get('username')
    server_ip = data.get('server_ip', '127.0.0.1')
    server_port = data.get('server_port', 9000)
    
    print(f"[INIT] Received init request for username: '{username}'")
    
    if not username:
        print("[INIT] ERROR: No username provided")
        return jsonify({'success': False, 'error': 'Username required'}), 400
    
    # Get user data
    user = user_db.get_user(username)
    if not user:
        print(f"[INIT] ERROR: User '{username}' not found in database")
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    try:
        # Auto-assign port if needed
        port = find_available_port()
        if not port:
            print("[INIT] ERROR: No available ports")
            return jsonify({'success': False, 'error': 'No available ports'}), 500
        
        # Update global server settings if provided
        if server_ip:
            import client as ClientModule
            ClientModule.CENTRAL_HOST = server_ip
        if server_port:
            import client as ClientModule
            ClientModule.CENTRAL_PORT = server_port
        
        # Use username as hostname for consistency
        hostname = username
        display_name = user.get('display_name', username)
        repo = user.get('settings', {}).get('default_repo', f'repo_{username}')
        
        print(f"[INIT] Creating client: hostname={hostname}, port={port}, repo={repo}")
        
        with clients_lock:
            # Close existing client for this user if it exists
            if username in client_instances:
                try:
                    client_instances[username].close()
                    print(f"[INIT] Closed previous client instance for '{username}'")
                except Exception as e:
                    print(f"[INIT] WARN: Error closing previous client for '{username}': {e}")
            
            # Create new client instance for this user
            try:
                client_instances[username] = Client(hostname, port, repo, display_name)
                print(f"[INIT] SUCCESS: Created client instance for '{username}' on port {port}")
                print(f"[INIT] Active clients: {list(client_instances.keys())}")
            except Exception as client_error:
                print(f"[INIT] ERROR: Failed to create Client instance: {client_error}")
                import traceback
                traceback.print_exc()
                raise
        
        return jsonify({
            'success': True,
            'client': {
                'username': username,
                'hostname': hostname,
                'display_name': display_name,
                'port': port,
                'repo': repo
            }
        })
    except Exception as e:
        print(f"[ERROR] Failed to initialize client for '{username}': {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/status', methods=['GET'])
def get_client_status():
    """Get client status"""
    try:
        client = get_client()  # Will extract username from token
        return jsonify({
            'success': True,
            'client': {
                'hostname': client.hostname,
                'display_name': client.display_name,
                'port': client.listen_port,
                'repo': client.repo_dir
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/client/local-files', methods=['GET'])
def get_local_files():
    """Get list of local tracked files"""
    try:
        client = get_client()  # Will extract username from token
        files = []
        for fname, meta in client.local_files.items():
            files.append({
                'name': meta.name,
                'size': meta.size,
                'modified': meta.modified,
                'path': meta.path,
                'is_published': meta.is_published
            })
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/published-files', methods=['GET'])
def get_published_files():
    """Get list of published files"""
    try:
        client = get_client()  # Will extract username from token
        files = []
        for fname, meta in client.published_files.items():
            files.append({
                'name': meta.name,
                'size': meta.size,
                'modified': meta.modified,
                'published_at': meta.published_at
            })
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/network-files', methods=['GET'])
def get_network_files():
    """Get all files available on the network"""
    try:
        client = get_client()  # Will extract username from token
        with client.central_lock:
            send_json(client.central, {"action": "LIST"})
            response = recv_json(client.central)
        
        if response and response.get('status') == 'OK':
            registry = response.get('registry', {})
            files = []
            
            for hostname, info in registry.items():
                for fname, finfo in info.get('files', {}).items():
                    files.append({
                        'name': fname,
                        'size': finfo.get('size', 0),
                        'modified': finfo.get('modified', 0),
                        'published_at': finfo.get('published_at', 0),
                        'owner_hostname': hostname,
                        'owner_name': info.get('display_name', hostname),
                        'owner_ip': info['addr'][0],
                        'owner_port': info['addr'][1]
                    })
            
            return jsonify({'success': True, 'files': files})
        else:
            return jsonify({'success': False, 'error': 'Failed to get network files'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/add-file', methods=['POST'])
def add_file():
    """Add a file to local tracking"""
    try:
        client = get_client()
        data = request.json
        filepath = data.get('filepath')
        
        if not filepath:
            return jsonify({'success': False, 'error': 'filepath required'}), 400
        
        success = client.add_local_file(filepath)
        if success:
            return jsonify({'success': True, 'message': 'File added to tracking'})
        else:
            return jsonify({'success': False, 'error': 'Failed to add file'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/check-duplicate', methods=['POST'])
def check_duplicate():
    """Check if a file with same metadata exists on network (for UI warnings)"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')
        size = data.get('size')
        modified = data.get('modified')
        
        if not fname or size is None:
            return jsonify({'success': False, 'error': 'fname and size required'}), 400
        
        # Use current time if modified not provided
        if modified is None:
            modified = time.time()
        
        # Check for duplicates on network
        duplicate_info = client._check_duplicate_on_network(fname, size, modified)
        
        return jsonify({
            'success': True,
            'has_exact_duplicate': duplicate_info['has_exact_duplicate'],
            'has_partial_duplicate': duplicate_info['has_partial_duplicate'],
            'exact_matches': duplicate_info['exact_matches'],
            'partial_matches': duplicate_info['partial_matches']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/check-local-duplicate', methods=['POST'])
def check_local_duplicate():
    """Check if a file with same name exists in local repository"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')
        
        if not fname:
            return jsonify({'success': False, 'error': 'fname required'}), 400
        
        # Check if file exists locally
        if fname in client.local_files:
            local_meta = client.local_files[fname]
            return jsonify({
                'success': True,
                'exists': True,
                'local_file': {
                    'name': local_meta.name,
                    'size': local_meta.size,
                    'modified': local_meta.modified,
                    'is_published': local_meta.is_published
                }
            })
        else:
            return jsonify({
                'success': True,
                'exists': False
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/upload', methods=['POST'])
def upload_file():
    """Upload a file from browser to repo and optionally publish"""
    try:
        client = get_client()
        
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Get optional parameters
        auto_publish = request.form.get('auto_publish', 'false').lower() == 'true'
        force_upload = request.form.get('force_upload', 'false').lower() == 'true'
        
        # Save file to repo directory
        fname = os.path.basename(file.filename)  # Sanitize filename
        dest_path = os.path.join(client.repo_dir, fname)
        
        # Check if file exists (unless force_upload is True)
        if os.path.exists(dest_path) and not force_upload:
            return jsonify({'success': False, 'error': f'File "{fname}" already exists in repository'}), 400
        
        # Save the uploaded file
        file.save(dest_path)
        
        # Add to local files
        stat = os.stat(dest_path)
        from client import FileMetadata
        metadata = FileMetadata(
            name=fname,
            size=stat.st_size,
            modified=stat.st_mtime,
            path=dest_path,
            is_published=False
        )
        client.local_files[fname] = metadata
        
        # Auto publish if requested
        if auto_publish:
            def publish_task():
                # Use interactive=False for API calls, overwrite=True to auto-replace
                client.publish(dest_path, fname, overwrite=True, interactive=False)
            threading.Thread(target=publish_task, daemon=True).start()
            message = f'File "{fname}" uploaded and publishing...'
        else:
            message = f'File "{fname}" uploaded successfully'
        
        return jsonify({
            'success': True, 
            'message': message,
            'file': {
                'name': fname,
                'size': stat.st_size,
                'path': dest_path
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/publish', methods=['POST'])
def publish_file():
    """Publish a file to the network"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')  # Changed to just fname since file should already be in repo
        local_path = data.get('local_path')  # Optional, if provided will copy to repo
        
        if not fname:
            return jsonify({'success': False, 'error': 'fname required'}), 400
        
        # If local_path provided, use it; otherwise look in repo
        if not local_path:
            # File should already be in local_files
            if fname in client.local_files:
                local_path = client.local_files[fname].path
            else:
                # Try repo directory
                local_path = os.path.join(client.repo_dir, fname)
                if not os.path.exists(local_path):
                    return jsonify({'success': False, 'error': 'File not found in repository'}), 404
        
        # Run publish in a separate thread to avoid blocking
        def publish_task():
            # Use interactive=False for API calls, overwrite=True to auto-replace
            success = client.publish(local_path, fname, overwrite=True, interactive=False)
            if not success:
                print(f"[API] Failed to publish {fname}")
        
        thread = threading.Thread(target=publish_task, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Publishing file...'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/fetch', methods=['POST'])
def fetch_file():
    """Fetch a file from the network with optional save location"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')
        save_path = data.get('save_path')  # Optional: where to save the file
        
        if not fname:
            return jsonify({'success': False, 'error': 'fname required'}), 400
        
        # Run fetch in a separate thread
        def fetch_task():
            client.request(fname, save_path)
        
        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'Fetching file...',
            'save_path': save_path or client.repo_dir
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/download/<fname>', methods=['GET'])
def download_file(fname):
    """Download a fetched file from the repo to browser (for saving anywhere)"""
    try:
        client = get_client()
        
        # Check if file exists in local files
        if fname not in client.local_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = client.local_files[fname].path
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404
        
        return send_file(file_path, as_attachment=True, download_name=fname)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/unpublish', methods=['POST'])
def unpublish_file():
    """Unpublish a file from the network (remove from published list but keep locally)"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')
        
        if not fname:
            return jsonify({'success': False, 'error': 'fname required'}), 400
        
        # Call unpublish method
        success = client.unpublish(fname)
        
        if success:
            return jsonify({'success': True, 'message': 'File unpublished successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to unpublish file'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/discover/<hostname>', methods=['GET'])
def discover_host(hostname):
    """Discover files from a specific host"""
    try:
        client = get_client()
        with client.central_lock:
            send_json(client.central, {"action": "DISCOVER", "data": {"hostname": hostname}})
            response = recv_json(client.central)
        
        if response and response.get('status') == 'OK':
            return jsonify({
                'success': True,
                'hostname': hostname,
                'files': response.get('files', []),
                'addr': response.get('addr')
            })
        else:
            return jsonify({'success': False, 'error': response.get('reason', 'Unknown error')}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/ping/<hostname>', methods=['GET'])
def ping_host(hostname):
    """Ping a specific host"""
    try:
        client = get_client()
        with client.central_lock:
            send_json(client.central, {"action": "PING", "data": {"hostname": hostname}})
            response = recv_json(client.central)
        
        return jsonify({
            'success': True,
            'hostname': hostname,
            'status': response.get('status') if response else 'ERROR'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/scan-directory', methods=['POST'])
def scan_directory():
    """Scan a directory and add all files to local tracking"""
    try:
        client = get_client()
        data = request.json
        directory = data.get('directory')
        
        if not directory:
            return jsonify({'success': False, 'error': 'directory required'}), 400
        
        directory = os.path.abspath(os.path.expanduser(directory))
        if not os.path.isdir(directory):
            return jsonify({'success': False, 'error': 'Invalid directory'}), 400
        
        added = 0
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            if os.path.isfile(fpath):
                if client.add_local_file(fpath):
                    added += 1
        
        return jsonify({
            'success': True,
            'message': f'Added {added} files to tracking',
            'count': added
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    with clients_lock:
        active_clients = len(client_instances)
        usernames = list(client_instances.keys())
    
    return jsonify({
        'status': 'healthy',
        'service': 'Client API',
        'active_clients': active_clients,
        'usernames': usernames
    })

@app.route('/api/debug/clients', methods=['GET'])
def debug_clients():
    """Debug endpoint to see all active clients"""
    with clients_lock:
        client_info = {}
        for username, client in client_instances.items():
            try:
                client_info[username] = {
                    'hostname': client.hostname,
                    'display_name': client.display_name,
                    'port': client.listen_port,
                    'repo': client.repo_dir,
                    'running': client.running,
                    'local_files_count': len(client.local_files),
                    'published_files_count': len(client.published_files)
                }
            except Exception as e:
                client_info[username] = {'error': str(e)}
    
    return jsonify({
        'total_clients': len(client_instances),
        'clients': client_info
    })

if __name__ == '__main__':
    print("=== P2P File Sharing Client API Started ===")
    print(f"Client API: http://{CLIENT_API_HOST}:{CLIENT_API_PORT}")
    print("\nEndpoints:")
    print("  POST /api/client/register - Register new user")
    print("  POST /api/client/login - Login existing user")
    print("  POST /api/client/init - Initialize client session")
    print("  GET /api/health - Health check")
    app.run(host=CLIENT_API_HOST, port=CLIENT_API_PORT, debug=True, threaded=True)
