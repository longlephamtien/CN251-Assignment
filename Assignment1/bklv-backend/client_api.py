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

# Global client instance
client_instance = None
client_lock = threading.Lock()

def get_client():
    """Get the active client instance"""
    global client_instance
    if client_instance is None:
        raise Exception("Client not initialized. Call /api/client/init first.")
    return client_instance

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
    global client_instance
    
    data = request.json
    username = data.get('username')
    server_ip = data.get('server_ip', '127.0.0.1')
    server_port = data.get('server_port', 9000)
    
    if not username:
        return jsonify({'success': False, 'error': 'Username required'}), 400
    
    # Get user data
    user = user_db.get_user(username)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    try:
        # Auto-assign port if needed
        port = find_available_port()
        if not port:
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
        
        with client_lock:
            if client_instance:
                # Close existing client properly
                try:
                    client_instance.close()
                except:
                    pass
                client_instance = None
            
            client_instance = Client(hostname, port, repo, display_name)
        
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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/status', methods=['GET'])
def get_client_status():
    """Get client status"""
    try:
        client = get_client()
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
        client = get_client()
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
        client = get_client()
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
        client = get_client()
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
        
        # Save file to repo directory
        fname = os.path.basename(file.filename)  # Sanitize filename
        dest_path = os.path.join(client.repo_dir, fname)
        
        # Check if file exists
        if os.path.exists(dest_path):
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
    return jsonify({
        'status': 'healthy',
        'service': 'Client API',
        'client_initialized': client_instance is not None
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
