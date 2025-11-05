"""
Client API Wrapper
Provides a Flask API interface for a client instance
This allows the web UI to control a local client

Note: User authentication is FORWARDED to central server.
Client API does NOT manage users locally - all user data is centralized on server.
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
import uuid
import requests

# Import the Client class and config
from client import Client, send_json, recv_json, CENTRAL_HOST, CENTRAL_PORT
from config import CLIENT_API_HOST, CLIENT_API_PORT, JWT_SECRET_KEY, SESSION_TIMEOUT
from user_db import find_available_port  # Only need port management
from optimizations.fetch_manager import fetch_manager

app = Flask(__name__)
CORS(app)

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
    """
    Forward registration request to central server
    Client API does NOT manage users - all user data is on server
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    display_name = data.get('display_name')
    server_host = data.get('server_host', CENTRAL_HOST)
    server_port = data.get('server_port', 5500)  # Server API port
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    try:
        # Forward to server API
        server_url = f'http://{server_host}:{server_port}/api/user/register'
        print(f"[AUTH] Forwarding registration to server: {server_url}")
        
        response = requests.post(server_url, json={
            'username': username,
            'password': password,
            'display_name': display_name
        }, timeout=10)
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"[ERROR] Failed to forward registration: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to connect to server: {str(e)}'
        }), 500

@app.route('/api/client/login', methods=['POST'])
def login_user():
    """
    Forward login request to central server
    Client API does NOT manage users - all user data is on server
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')
    server_host = data.get('server_host', CENTRAL_HOST)
    server_port = data.get('server_port', 5500)  # Server API port
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    try:
        # Forward to server API
        server_url = f'http://{server_host}:{server_port}/api/user/login'
        print(f"[AUTH] Forwarding login to server: {server_url}")
        
        response = requests.post(server_url, json={
            'username': username,
            'password': password
        }, timeout=10)
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        print(f"[ERROR] Failed to forward login: {e}")
        return jsonify({
            'success': False,
            'error': f'Failed to connect to server: {str(e)}'
        }), 500

@app.route('/api/client/init', methods=['POST'])
def init_client():
    """
    Initialize a new client session for authenticated user
    User validation is done via JWT token from server
    """
    data = request.json
    username = data.get('username')
    server_ip = data.get('server_ip', '127.0.0.1')
    server_port = data.get('server_port', 9000)
    advertise_ip = data.get('advertise_ip')  # Optional: client can specify IP to advertise
    
    print(f"[INIT] Received init request for username: '{username}'")
    print(f"[INIT] Server IP: {server_ip}, Advertise IP: {advertise_ip}")
    
    if not username:
        print("[INIT] ERROR: No username provided")
        return jsonify({'success': False, 'error': 'Username required'}), 400
    
    # Verify user with server (via token)
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        print("[INIT] ERROR: No authorization token")
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        # Verify token with server
        server_api_port = 5500  # Server API port
        verify_url = f'http://{server_ip}:{server_api_port}/api/user/verify'
        print(f"[INIT] Verifying token with server: {verify_url}")
        
        verify_response = requests.post(verify_url, headers={
            'Authorization': auth_header
        }, timeout=10)
        
        if not verify_response.ok:
            print(f"[INIT] ERROR: Token verification failed")
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        user_data = verify_response.json()
        user = user_data.get('user', {})
        display_name = user.get('display_name', username)
        
        print(f"[INIT] User verified: {username} ({display_name})")
    except Exception as e:
        print(f"[INIT] ERROR: Failed to verify with server: {e}")
        return jsonify({'success': False, 'error': f'Server verification failed: {str(e)}'}), 500
    
    try:
        # Auto-assign port if needed
        port = find_available_port()
        if not port:
            print("[INIT] ERROR: No available ports")
            return jsonify({'success': False, 'error': 'No available ports'}), 500
        
        # Use username as hostname for consistency
        hostname = username
        repo = f'repo_{username}'
        
        print(f"[INIT] Creating client: hostname={hostname}, port={port}, repo={repo}, server={server_ip}:{server_port}")
        if advertise_ip:
            print(f"[INIT] Using advertised IP: {advertise_ip}")
        
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
                # Pass server_ip, server_port, and advertise_ip to Client constructor
                client_instances[username] = Client(
                    hostname, 
                    port, 
                    repo, 
                    display_name,
                    server_host=server_ip,
                    server_port=server_port,
                    advertise_ip=advertise_ip  # Pass advertise_ip
                )
                
                # Get the actual IP being advertised
                actual_ip = client_instances[username].advertise_ip
                
                print(f"[INIT] SUCCESS: Created client instance for '{username}' on port {port}")
                print(f"[INIT] Connected to server at {server_ip}:{server_port}")
                print(f"[INIT] Advertising IP: {actual_ip} for P2P connections")
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
                'repo': repo,
                'server_host': server_ip,
                'server_port': server_port,
                'advertise_ip': actual_ip
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
                'created': meta.created,
                'path': meta.path,
                'is_published': meta.is_published,
                'added_at': meta.added_at,
                'published_at': meta.published_at
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
                'created': meta.created,
                'path': meta.path,
                'added_at': meta.added_at,
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
                        'created': finfo.get('created', finfo.get('modified', 0)),
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
    """Add a file to local tracking by path (no copying)"""
    try:
        client = get_client()
        data = request.json
        filepath = data.get('filepath')
        
        if not filepath:
            return jsonify({'success': False, 'error': 'filepath required'}), 400
        
        # Expand and validate path
        filepath = os.path.abspath(os.path.expanduser(filepath))
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': f'File not found: {filepath}'}), 404
        
        if not os.path.isfile(filepath):
            return jsonify({'success': False, 'error': f'Path is not a file: {filepath}'}), 400
        
        # Add file to tracking (metadata only, no copying)
        success = client.add_local_file(filepath, auto_save_metadata=True)
        
        if success:
            fname = os.path.basename(filepath)
            file_meta = client.local_files.get(fname)
            return jsonify({
                'success': True, 
                'message': f'File "{fname}" tracked (reference to: {filepath})',
                'file': {
                    'name': fname,
                    'size': file_meta.size,
                    'created': file_meta.created,
                    'modified': file_meta.modified,
                    'path': filepath,
                    'added_at': file_meta.added_at
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to add file'}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
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
    """
    Track a file from user's computer by storing its path (NO COPYING).
    For browser uploads, we need to receive the file but can save it to a temp location
    or the user needs to provide a path to an existing file on their system.
    """
    try:
        client = get_client()
        
        # Check if user provided a file path (preferred method)
        file_path = request.form.get('file_path')
        
        if file_path:
            # User specified a file path on their system - just track it
            file_path = os.path.abspath(os.path.expanduser(file_path))
            
            if not os.path.exists(file_path):
                return jsonify({'success': False, 'error': f'File not found: {file_path}'}), 404
            
            if not os.path.isfile(file_path):
                return jsonify({'success': False, 'error': f'Path is not a file: {file_path}'}), 400
            
            fname = os.path.basename(file_path)
            
            # Get file metadata from original location
            from client import get_file_metadata_crossplatform, FileMetadata
            try:
                meta_dict = get_file_metadata_crossplatform(file_path)
            except Exception as e:
                print(f"[WARN] Failed to read metadata, using fallback: {e}")
                stat = os.stat(file_path)
                meta_dict = {
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'created': stat.st_mtime,
                    'path': file_path
                }
            
            # Track metadata only - file stays at original location
            metadata = FileMetadata(
                name=fname,
                size=meta_dict['size'],
                modified=meta_dict['modified'],
                created=meta_dict['created'],
                path=file_path,  # Original path on user's computer
                is_published=False,
                added_at=time.time()  # When added to tracking
            )
            client.local_files[fname] = metadata
            
            # Save metadata to JSON file
            client._save_file_metadata(fname)
            
            # Auto publish if requested
            auto_publish = request.form.get('auto_publish', 'false').lower() == 'true'
            if auto_publish:
                def publish_task():
                    client.publish(file_path, fname, overwrite=True, interactive=False)
                threading.Thread(target=publish_task, daemon=True).start()
                message = f'File "{fname}" tracked and publishing...'
            else:
                message = f'File "{fname}" tracked successfully (reference to: {file_path})'
            
            return jsonify({
                'success': True, 
                'message': message,
                'file': {
                    'name': fname,
                    'size': meta_dict['size'],
                    'path': file_path,
                    'added_at': metadata.added_at
                }
            })
        
        else:
            # Browser file upload - need to save somewhere first
            # For browser uploads, save to repo as temporary storage
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file provided. Use file_path parameter to track existing files.'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Get optional parameters
            auto_publish = request.form.get('auto_publish', 'false').lower() == 'true'
            force_upload = request.form.get('force_upload', 'false').lower() == 'true'
            
            # For browser uploads, we must save the file somewhere
            # Save to repo directory as the "original" location for browser-uploaded files
            fname = os.path.basename(file.filename)
            dest_path = os.path.join(client.repo_dir, fname)
            
            # Check if file exists (unless force_upload is True)
            if os.path.exists(dest_path) and not force_upload:
                return jsonify({'success': False, 'error': f'File "{fname}" already exists'}), 400
            
            # Save the uploaded file
            file.save(dest_path)
            
            # Get file metadata with cross-platform support
            from client import get_file_metadata_crossplatform, FileMetadata
            try:
                meta_dict = get_file_metadata_crossplatform(dest_path)
            except Exception as e:
                print(f"[WARN] Failed to read metadata, using fallback: {e}")
                stat = os.stat(dest_path)
                meta_dict = {
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'created': stat.st_mtime,
                    'path': dest_path
                }
            
            # Add to local files with added_at timestamp
            metadata = FileMetadata(
                name=fname,
                size=meta_dict['size'],
                modified=meta_dict['modified'],
                created=meta_dict['created'],
                path=dest_path,  # Saved in repo for browser uploads
                is_published=False,
                added_at=time.time()  # Track when added
            )
            client.local_files[fname] = metadata
            
            # Save metadata to JSON file
            client._save_file_metadata(fname)
            
            # Auto publish if requested
            if auto_publish:
                def publish_task():
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
                    'size': meta_dict['size'],
                    'path': dest_path,
                    'added_at': metadata.added_at
                }
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/publish', methods=['POST'])
def publish_file():
    """Publish a file to the network (metadata only - no file copying)"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')  # Filename to publish as
        local_path = data.get('local_path')  # Path to actual file
        
        if not fname:
            return jsonify({'success': False, 'error': 'fname required'}), 400
        
        # If local_path not provided, look in local_files
        if not local_path:
            if fname in client.local_files:
                local_path = client.local_files[fname].path
            else:
                return jsonify({'success': False, 'error': f'File "{fname}" not found. Please provide local_path'}), 404
        
        # Validate file path exists
        if not os.path.exists(local_path):
            return jsonify({'success': False, 'error': f'File not found: {local_path}'}), 404
        
        if not os.path.isfile(local_path):
            return jsonify({'success': False, 'error': f'Path is not a file: {local_path}'}), 400
        
        # Publish (stores metadata only, no copying)
        # Returns (success: bool, error_msg: str or None)
        success, error = client.publish(local_path, fname, overwrite=True, interactive=False)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'File "{fname}" published successfully',
                'path': local_path
            })
        else:
            return jsonify({'success': False, 'error': error or 'Failed to publish'}), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/fetch', methods=['POST'])
def fetch_file():
    """Fetch a file from the network with progress tracking (P2P transfer)"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')
        save_path = data.get('save_path')
        
        if not fname:
            return jsonify({'success': False, 'error': 'fname required'}), 400
        
        # Generate unique fetch ID
        fetch_id = str(uuid.uuid4())
        
        # Get file info from network (server provides metadata only)
        with client.central_lock:
            send_json(client.central, {"action": "REQUEST", "data": {"fname": fname}})
            response = recv_json(client.central)
        
        if not response or response.get('status') != 'FOUND':
            return jsonify({'success': False, 'error': 'File not found on network'}), 404
        
        hosts = response.get('hosts', [])
        if not hosts:
            return jsonify({'success': False, 'error': 'No hosts available'}), 404
        
        picked = hosts[0]
        total_size = picked.get('size', 0)
        peer_hostname = picked.get('hostname', '')
        peer_ip = picked['ip']
        
        # Determine save location
        if save_path:
            outpath = os.path.abspath(os.path.expanduser(save_path))
            if os.path.isdir(outpath):
                outpath = os.path.join(outpath, fname)
        else:
            outpath = os.path.join(client.repo_dir, fname)
        
        # Create fetch session (P2P - no server file transfer)
        session = fetch_manager.create_session(
            fetch_id=fetch_id,
            file_name=fname,
            total_size=total_size,
            save_path=outpath,
            peer_hostname=peer_hostname,
            peer_ip=peer_ip
        )
        
        # Download in background thread (direct P2P connection)
        def fetch_task():
            try:
                # Pass fetch_id so download_from_peer uses the managed session
                result = client.download_from_peer(
                    peer_ip,
                    picked['port'],
                    fname,
                    save_path,
                    fetch_id=fetch_id  # Use existing session from fetch_manager
                )
                
                if not result:
                    session.fail("P2P fetch failed")
                    
            except Exception as e:
                session.fail(str(e))
        
        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'P2P fetch started',
            'fetch_id': fetch_id,
            'file_name': fname,
            'total_size': total_size,
            'save_path': outpath,
            'peer_hostname': peer_hostname,
            'peer_ip': peer_ip
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/client/fetch-progress/<fetch_id>', methods=['GET'])
def get_fetch_progress(fetch_id):
    """Get progress for a specific P2P fetch"""
    try:
        session = fetch_manager.get_session(fetch_id)
        if not session:
            return jsonify({'success': False, 'error': 'Fetch not found'}), 404
        
        progress = session.get_progress()
        return jsonify({
            'success': True,
            'progress': progress
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/client/fetches', methods=['GET'])
def get_all_fetches():
    """Get progress for all active P2P fetches"""
    try:
        all_progress = fetch_manager.get_all_progress()
        return jsonify({
            'success': True,
            'fetches': all_progress
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

@app.route('/api/client/validate-file', methods=['POST'])
def validate_file():
    """Validate that a file path exists and is readable"""
    try:
        client = get_client()
        data = request.json
        fname = data.get('fname')
        
        if not fname:
            return jsonify({'success': False, 'error': 'fname required'}), 400
        
        # Check if file is in published files
        if fname not in client.published_files:
            return jsonify({
                'success': False,
                'exists': False,
                'error': 'File not in published files'
            })
        
        file_metadata = client.published_files[fname]
        is_valid, error_msg = file_metadata.validate_path()
        
        if is_valid:
            return jsonify({
                'success': True,
                'exists': True,
                'path': file_metadata.path,
                'size': file_metadata.size,
                'modified': file_metadata.modified
            })
        else:
            return jsonify({
                'success': False,
                'exists': False,
                'error': error_msg,
                'path': file_metadata.path
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/client/logout', methods=['POST'])
def logout():
    """Logout and disconnect client from network"""
    try:
        # Extract username from token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            username = payload.get('username')
            print(f"[LOGOUT] Received logout request from '{username}'")
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401
        
        with clients_lock:
            if username in client_instances:
                client = client_instances[username]
                print(f"[LOGOUT] Disconnecting client '{username}'")
                
                # Unregister from central server and close connection
                try:
                    client.close()
                    print(f"[LOGOUT] Client '{username}' unregistered from server")
                except Exception as e:
                    print(f"[LOGOUT] Error closing client: {e}")
                
                # Remove from active instances
                del client_instances[username]
                print(f"[LOGOUT] Removed '{username}' from active instances")
                
                return jsonify({
                    'success': True,
                    'message': f'Successfully disconnected from network'
                })
            else:
                print(f"[LOGOUT] Client '{username}' not found in active instances. Available: {list(client_instances.keys())}")
                return jsonify({
                    'success': False,
                    'error': 'Client not found'
                }), 404
    except Exception as e:
        print(f"[ERROR] Logout failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
    print("  POST /api/client/logout - Logout and disconnect from network")
    print("  GET /api/health - Health check")
    app.run(host=CLIENT_API_HOST, port=CLIENT_API_PORT, debug=True, threaded=True)
