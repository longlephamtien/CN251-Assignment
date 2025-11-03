import socket
import threading
import json
import shutil
import sys
import os
import shlex
import time
import argparse
import platform
from datetime import datetime

# Import adaptive heartbeat
try:
    from optimizations.adaptive_heartbeat import AdaptiveHeartbeat, ClientState
    ADAPTIVE_HEARTBEAT_AVAILABLE = True
except ImportError:
    print("[WARN] Adaptive heartbeat module not found, using fixed interval")
    ADAPTIVE_HEARTBEAT_AVAILABLE = False

try:
    from config import (
        SERVER_HOST, 
        SERVER_PORT,
        CLIENT_HEARTBEAT_INTERVAL
    )
    CENTRAL_HOST = SERVER_HOST if SERVER_HOST != '0.0.0.0' else '127.0.0.1'
    CENTRAL_PORT = SERVER_PORT
except:
    CENTRAL_HOST = '127.0.0.1'
    CENTRAL_PORT = 9000
    CLIENT_HEARTBEAT_INTERVAL = 60

def get_file_metadata_crossplatform(file_path):
    """
    Get file metadata in a cross-platform way (Windows, macOS, Linux)
    
    Returns:
        dict with: size, modified, created, path
    """
    try:
        stat_info = os.stat(file_path)
        
        # Size in bytes
        size = stat_info.st_size
        
        # Modified time (works on all platforms)
        modified = stat_info.st_mtime
        
        # Created/birth time (platform-specific)
        if platform.system() == 'Windows':
            # Windows: st_ctime is creation time
            created = stat_info.st_ctime
        elif platform.system() == 'Darwin':  # macOS
            # macOS: st_birthtime is creation time
            created = stat_info.st_birthtime if hasattr(stat_info, 'st_birthtime') else stat_info.st_ctime
        else:
            # Linux: st_ctime is metadata change time, not creation time
            # Use modified time as fallback
            created = stat_info.st_mtime
        
        return {
            'size': size,
            'modified': modified,
            'created': created,
            'path': os.path.abspath(file_path)
        }
    except Exception as e:
        raise Exception(f"Failed to get file metadata: {e}")

class FileMetadata:
    """Tracks file metadata for local, published, and network files"""
    def __init__(self, name, size, modified, path=None, is_published=False, created=None, added_at=None, published_at=None):
        self.name = name
        self.size = size
        self.modified = modified  # File's last modified time (from filesystem)
        self.created = created or modified  # File's creation time (from filesystem)
        self.path = path  # Absolute path to the actual file
        self.is_published = is_published
        self.added_at = added_at  # When file was added to local tracking
        self.published_at = published_at  # When file was published to network
    
    def to_dict(self):
        return {
            'name': self.name,
            'size': self.size,
            'modified': self.modified,
            'created': self.created,
            'path': self.path,
            'is_published': self.is_published,
            'added_at': self.added_at,
            'published_at': self.published_at
        }
    
    def matches_metadata(self, other_size, other_modified, tolerance_seconds=2):
        """
        Check if file metadata matches (for duplicate detection without hashing)
        
        Args:
            other_size: Size to compare
            other_modified: Modified time to compare
            tolerance_seconds: Tolerance for time comparison (default 2 seconds)
        
        Returns:
            Tuple (exact_match, size_match, time_match)
        """
        size_match = self.size == other_size
        time_match = abs(self.modified - other_modified) < tolerance_seconds
        exact_match = size_match and time_match
        
        return exact_match, size_match, time_match
    
    def file_exists(self):
        """Check if the file still exists at the stored path"""
        if not self.path:
            return False
        return os.path.isfile(self.path)
    
    def validate_path(self):
        """
        Validate file path and check existence
        Returns: (is_valid, error_message)
        """
        if not self.path:
            return False, "No file path specified"
        
        # Check if path exists
        if not os.path.exists(self.path):
            return False, f"File not found: {self.path}"
        
        # Check if it's a file (not directory)
        if not os.path.isfile(self.path):
            return False, f"Path is not a file: {self.path}"
        
        # Check if readable
        if not os.access(self.path, os.R_OK):
            return False, f"File is not readable: {self.path}"
        
        return True, None

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

class PeerServer(threading.Thread):
    def __init__(self, listen_port, client_ref):
        """
        Args:
            listen_port: Port to listen on
            client_ref: Reference to Client instance (to access published_files)
        """
        super().__init__(daemon=True)
        self.listen_port = listen_port
        self.client_ref = client_ref  # Reference to parent Client
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow port reuse
        self.sock.bind(('', self.listen_port))
        self.sock.listen(5)
        self.sock.settimeout(1.0)  # Set timeout so accept() doesn't block forever

    def run(self):
        print(f"[PEER] Server started on port {self.listen_port}")
        while self.client_ref.running:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self.handle_peer, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                # Timeout allows us to check running flag periodically
                continue
            except Exception as e:
                if self.client_ref.running:  # Only log if we're supposed to be running
                    print(f"[PEER] Accept error: {e}")
                break
        print(f"[PEER] Server stopped on port {self.listen_port}")
    
    def stop(self):
        """Stop the peer server"""
        print(f"[PEER] Stopping peer server on port {self.listen_port}")
        try:
            self.sock.close()
        except Exception as e:
            print(f"[PEER] Error closing socket: {e}")

    def handle_peer(self, conn, addr):
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                data += chunk
                if b'\n' in data:
                    line, _ = data.split(b'\n',1)
                    break
            cmd = line.decode().strip().split(' ',1)
            if cmd[0] == 'GET' and len(cmd) == 2:
                fname = cmd[1]
                
                # Look up file in published files to get actual path
                if fname not in self.client_ref.published_files:
                    conn.sendall(b"ERROR notfound\n")
                    print(f"[PEER] File '{fname}' not found in published files")
                    return
                
                file_metadata = self.client_ref.published_files[fname]
                
                # Validate file still exists at stored path
                is_valid, error_msg = file_metadata.validate_path()
                if not is_valid:
                    conn.sendall(b"ERROR filenotfound\n")
                    print(f"[PEER] File validation failed: {error_msg}")
                    return
                
                fpath = file_metadata.path
                
                try:
                    size = os.path.getsize(fpath)
                    conn.sendall(f"LENGTH {size}\n".encode())
                    print(f"[PEER] Sending file '{fname}' ({size:,} bytes) from: {fpath}")
                    
                    # Use larger chunks for better performance with large files
                    # 1MB chunks for files > 100MB, otherwise 256KB
                    chunk_size = 1024*1024 if size > 100*1024*1024 else 256*1024
                    
                    bytes_sent = 0
                    last_progress_report = 0
                    
                    with open(fpath, 'rb') as f:
                        while True:
                            # Check if client is shutting down
                            if not self.client_ref.running:
                                print(f"[PEER] Transfer of '{fname}' interrupted - client shutting down")
                                conn.sendall(b"ERROR interrupted\n")
                                return
                            
                            chunk = f.read(chunk_size)
                            if not chunk:
                                break
                            conn.sendall(chunk)
                            bytes_sent += len(chunk)
                            
                            # Progress reporting for large files (every 10%)
                            if size > 10*1024*1024:
                                progress = (bytes_sent / size) * 100
                                if int(progress) >= last_progress_report + 10:
                                    last_progress_report = int(progress)
                                    print(f"[PEER] Sent {progress:.0f}% of '{fname}'")
                    
                    print(f"[PEER] Completed sending '{fname}' ({bytes_sent:,} bytes)")
                    
                except Exception as e:
                    conn.sendall(b"ERROR readerror\n")
                    print(f"[PEER] Error reading file '{fname}': {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"[PEER] Connection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()

class Client:
    def __init__(self, hostname, listen_port, repo_dir, display_name=None, server_host=None, server_port=None):
        self.hostname = hostname
        self.display_name = display_name or hostname
        self.listen_port = listen_port
        self.repo_dir = repo_dir
        os.makedirs(self.repo_dir, exist_ok=True)
        
        # Server connection info (use provided or default)
        self.server_host = server_host or CENTRAL_HOST
        self.server_port = server_port or CENTRAL_PORT
        
        # Three-tier file management
        self.local_files = {}  # All files tracked by client (metadata only)
        self.published_files = {}  # Files published to network (subset of local)
        self.network_files = {}  # Files available from other clients
        
        # State file to persist published status
        self.state_file = os.path.join(self.repo_dir, '.client_state.json')
        
        # Control flag for threads
        self.running = True
        
        # Initialize adaptive heartbeat if available
        if ADAPTIVE_HEARTBEAT_AVAILABLE:
            self.adaptive_heartbeat = AdaptiveHeartbeat(ClientState.ACTIVE)
            print("[INFO] Adaptive heartbeat enabled")
        else:
            self.adaptive_heartbeat = None
            print("[INFO] Using fixed heartbeat interval")
        
        # IMPORTANT: Scan repo directory FIRST to get current files
        self._scan_repo_directory()
        
        # Load state from local file (if exists)
        self._load_state()
        
        # Then connect and register
        print(f"[INFO] Connecting to server at {self.server_host}:{self.server_port}")
        self.central_lock = threading.Lock()
        self.central = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.central.connect((self.server_host, self.server_port))
            print(f"[SUCCESS] Connected to server at {self.server_host}:{self.server_port}")
        except Exception as e:
            print(f"[ERROR] Failed to connect to server at {self.server_host}:{self.server_port}")
            raise RuntimeError(f"Cannot connect to server: {e}")
        
        # Prepare files metadata for server (with restored state)
        files_metadata = {}
        for fname, meta in self.local_files.items():
            files_metadata[fname] = {
                "size": meta.size,
                "modified": meta.modified,
                "published_at": meta.published_at,
                "is_published": meta.is_published
            }
        
        # Now REGISTER with correct metadata
        send_json(self.central, {
            "action": "REGISTER", 
            "data": {
                "hostname": self.hostname, 
                "port": self.listen_port,
                "display_name": self.display_name,
                "files_metadata": files_metadata
            }
        })
        resp = recv_json(self.central)
        if not resp or resp.get('status') != 'OK':
            error_msg = f"Register failed: {resp}"
            print(f"[ERROR] {error_msg}")
            raise RuntimeError(error_msg)
        
        self.pub_lock = threading.Lock()
        self.peer_server = PeerServer(self.listen_port, self)  # Pass client reference
        self.peer_server.start()
        threading.Thread(target=self.heartbeat_thread, daemon=True).start()
    
    def _load_state(self):
        """Load published state from local file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    
                restored_count = 0
                for fname, file_state in state.get('files', {}).items():
                    if fname in self.local_files:
                        # Restore published state
                        is_published = file_state.get('is_published', False)
                        published_at = file_state.get('published_at', None)
                        
                        self.local_files[fname].is_published = is_published
                        self.local_files[fname].published_at = published_at
                        
                        if is_published:
                            self.published_files[fname] = self.local_files[fname]
                            restored_count += 1
                
                print(f"[INFO] Restored {restored_count} published files from local state")
        except Exception as e:
            print(f"[WARN] Failed to load state file: {e}")
    
    def _save_state(self):
        """Save published state to local file"""
        try:
            state = {
                'hostname': self.hostname,
                'files': {}
            }
            
            for fname, meta in self.local_files.items():
                state['files'][fname] = {
                    'is_published': meta.is_published,
                    'published_at': meta.published_at
                }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save state file: {e}")

    def _scan_repo_directory(self):
        """Scan repository directory and load file metadata from JSON files"""
        try:
            for fname in os.listdir(self.repo_dir):
                # Skip hidden files and internal state files
                if fname.startswith('.'):
                    continue
                
                # Look for metadata JSON files
                if fname.endswith('.meta.json'):
                    meta_path = os.path.join(self.repo_dir, fname)
                    try:
                        with open(meta_path, 'r') as f:
                            meta_data = json.load(f)
                        
                        # Reconstruct FileMetadata from JSON
                        file_meta = FileMetadata(
                            name=meta_data['name'],
                            size=meta_data['size'],
                            modified=meta_data['modified'],
                            created=meta_data.get('created', meta_data['modified']),
                            path=meta_data['path'],
                            is_published=meta_data.get('is_published', False),
                            added_at=meta_data.get('added_at'),
                            published_at=meta_data.get('published_at')
                        )
                        self.local_files[file_meta.name] = file_meta
                        
                        if file_meta.is_published:
                            self.published_files[file_meta.name] = file_meta
                            
                    except Exception as e:
                        print(f"[WARN] Failed to load metadata from {fname}: {e}")
                        
            print(f"[INFO] Loaded {len(self.local_files)} file metadata entries from repository")
        except Exception as e:
            print(f"[ERROR] Failed to scan repository: {e}")
    
    def _save_file_metadata(self, fname):
        """Save file metadata to JSON file in repo directory"""
        try:
            if fname not in self.local_files:
                return False
            
            meta = self.local_files[fname]
            meta_filename = f"{fname}.meta.json"
            meta_path = os.path.join(self.repo_dir, meta_filename)
            
            with open(meta_path, 'w') as f:
                json.dump(meta.to_dict(), f, indent=2)
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save metadata for {fname}: {e}")
            return False
    
    def add_local_file(self, filepath, auto_save_metadata=True):
        """Add a file to local tracking (without copying or publishing)"""
        filepath = os.path.abspath(os.path.expanduser(filepath))
        if not os.path.isfile(filepath):
            print(f"[ERROR] File not found: {filepath}")
            return False
        
        fname = os.path.basename(filepath)
        
        # Get cross-platform metadata
        try:
            meta_dict = get_file_metadata_crossplatform(filepath)
        except Exception as e:
            print(f"[ERROR] Failed to read metadata: {e}")
            return False
        
        self.local_files[fname] = FileMetadata(
            name=fname,
            size=meta_dict['size'],
            modified=meta_dict['modified'],
            created=meta_dict['created'],
            path=filepath,
            is_published=False,
            added_at=time.time()  # Track when added to local files
        )
        
        # Save metadata to JSON
        if auto_save_metadata:
            self._save_file_metadata(fname)
        
        print(f"[INFO] Added '{fname}' to local tracking")
        return True
    
    def heartbeat_thread(self):
        """Send periodic heartbeat to central server with adaptive intervals"""
        while self.running:
            try:
                # Get interval (adaptive or fixed)
                if self.adaptive_heartbeat:
                    interval = self.adaptive_heartbeat.get_interval()
                else:
                    interval = CLIENT_HEARTBEAT_INTERVAL
                
                time.sleep(interval)
                
                if not self.running:
                    break
                
                with self.central_lock:
                    ping_data = {"hostname": self.hostname}
                    
                    # Include state if using adaptive heartbeat
                    if self.adaptive_heartbeat:
                        ping_data["state"] = self.adaptive_heartbeat.state.value
                    
                    send_json(self.central, {"action": "PING", "data": ping_data})
                    recv_json(self.central)
                    
                    # Record heartbeat
                    if self.adaptive_heartbeat:
                        self.adaptive_heartbeat.record_heartbeat()
                        
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    print(f"[HEARTBEAT] Failed: {e}")
                break

    # def publish(self, local_path, fname):
    #     if not os.path.isfile(local_path):
    #         print("local file not found")
    #         return
    #     dest = os.path.join(self.repo_dir, fname)
    #     if local_path != dest:
    #         try:
    #             with open(local_path,'rb') as fr, open(dest,'wb') as fw:
    #                 fw.write(fr.read())
    #         except Exception as e:
    #             print("copy error", e)
    #             return
    #
    #     self.local_files.add(fname)
    #     with self.central_lock:
    #         send_json(self.central, {"action":"PUBLISH","data":{"hostname":self.hostname,"fname":fname}})
    #         r = recv_json(self.central)
    #     if r and r.get('status') == 'ACK':
    #         print("Published", fname)
    #     else:
    #         print("Publish failed", r)

    def publish(self, local_path, fname=None, overwrite=True, interactive=True):
        """
        Publish a file by registering its metadata (NO COPYING - just track the file path).
        The file stays in its original location.
        
        Args:
            local_path: Path to the file to publish
            fname: Name to register (defaults to filename from path)
            overwrite: If True, allow re-publishing with updated metadata
            interactive: If True, prompt user for confirmation (CLI mode)
        """
        try:
            # Mark activity for adaptive heartbeat
            if self.adaptive_heartbeat:
                self.adaptive_heartbeat.mark_activity("publish")
            
            # Normalize path (expand ~ and make absolute)
            local_path = os.path.expanduser(local_path)
            local_path = os.path.abspath(local_path)

            # Check if file exists and is valid
            if not os.path.exists(local_path):
                print(f"[ERROR] File not found: {local_path}")
                return False, f"File not found: {local_path}"
            
            if not os.path.isfile(local_path):
                print(f"[ERROR] Path is not a file: {local_path}")
                return False, f"Path is not a file: {local_path}"
            
            if not os.access(local_path, os.R_OK):
                print(f"[ERROR] File is not readable: {local_path}")
                return False, f"File is not readable: {local_path}"

            # Get file metadata (cross-platform)
            try:
                metadata_dict = get_file_metadata_crossplatform(local_path)
                file_size = metadata_dict['size']
                file_modified = metadata_dict['modified']
                file_created = metadata_dict['created']
            except Exception as e:
                print(f"[ERROR] Failed to read file metadata: {e}")
                return False, f"Failed to read file metadata: {e}"

            # Use filename from path if fname not provided
            if fname is None:
                fname = os.path.basename(local_path)

            # Check for duplicates on network based on metadata
            duplicate_info = self._check_duplicate_on_network(fname, file_size, file_modified)
            
            if duplicate_info['has_exact_duplicate']:
                # Exact duplicate found (same name, size, and modified time)
                hosts = duplicate_info['exact_matches']
                print(f"\n[WARNING] File '{fname}' with exact same size and modified time already exists on network!")
                print(f"   Size: {file_size} bytes")
                print(f"   Modified: {datetime.fromtimestamp(file_modified).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Available from: {', '.join(h['hostname'] for h in hosts)}")
                
                if interactive:
                    print("\n[RECOMMENDATION] File appears to be identical. Consider fetching instead of publishing.")
                    choice = input("Do you still want to publish? (y/n): ").strip().lower()
                    if choice != 'y':
                        print("[INFO] Publish cancelled.")
                        return False, "Publish cancelled by user"
                else:
                    # In non-interactive mode, allow duplicates but warn
                    print("[WARNING] Exact duplicate exists. Publishing anyway (reference-based).")
            
            elif duplicate_info['has_partial_duplicate']:
                # Partial duplicate (same name, but different size or time)
                print(f"\n[WARNING] File '{fname}' with different metadata already exists on network!")
                print(f"   Your file - Size: {file_size} bytes, Modified: {datetime.fromtimestamp(file_modified).strftime('%Y-%m-%d %H:%M:%S')}")
                
                for match in duplicate_info['partial_matches']:
                    print(f"   {match['hostname']} - Size: {match['size']} bytes, Modified: {datetime.fromtimestamp(match['modified']).strftime('%Y-%m-%d %H:%M:%S')}")
                
                if interactive:
                    choice = input("Files have same name but different content. Continue? (y/n): ").strip().lower()
                    if choice != 'y':
                        print("[INFO] Publish cancelled.")
                        return False, "Publish cancelled by user"

            # Check if already published locally
            if fname in self.published_files and not overwrite:
                print(f"[ERROR] File '{fname}' is already published and overwrite=False")
                return False, f"File '{fname}' is already published"

            # Track when file was added (if not already tracked)
            added_timestamp = time.time()
            if fname in self.local_files:
                # File already tracked, preserve added_at
                added_timestamp = self.local_files[fname].added_at or time.time()

            # Create metadata object (no file copying!)
            metadata = FileMetadata(
                name=fname,
                size=file_size,
                modified=file_modified,
                created=file_created,
                path=local_path,  # Store original path
                is_published=True,
                added_at=added_timestamp,  # When added to local tracking
                published_at=time.time()  # When published to network
            )
            
            # Update tracking
            self.local_files[fname] = metadata
            self.published_files[fname] = metadata
            
            # Save metadata to JSON file
            self._save_file_metadata(fname)

            # Notify central server with metadata
            with self.central_lock:
                send_json(self.central, {
                    "action": "PUBLISH",
                    "data": {
                        "hostname": self.hostname, 
                        "fname": fname,
                        "size": file_size,
                        "modified": file_modified,
                        "created": file_created,
                        "published_at": metadata.published_at
                    }
                })
                r = recv_json(self.central)

            if r and r.get('status') == 'ACK':
                print(f"[SUCCESS] Published '{fname}' to network (reference to: {local_path})")
                print(f"   Size: {file_size} bytes, Modified: {datetime.fromtimestamp(file_modified).strftime('%Y-%m-%d %H:%M:%S')}")
                self._save_state()
                return True, None
            else:
                print(f"[ERROR] Publish failed: {r}")
                return False, f"Server error: {r}"

        except Exception as e:
            print(f"[ERROR] Exception during publish: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    def _check_duplicate_on_network(self, fname, size, modified):
        """
        Check if file with same metadata exists on network
        Uses metadata comparison (size + modified time) instead of hashing
        
        Returns:
            {
                'has_exact_duplicate': bool,
                'has_partial_duplicate': bool,
                'exact_matches': [...],
                'partial_matches': [...]
            }
        """
        try:
            with self.central_lock:
                send_json(self.central, {"action": "LIST"})
                response = recv_json(self.central)
            
            if not response or response.get('status') != 'OK':
                return {
                    'has_exact_duplicate': False,
                    'has_partial_duplicate': False,
                    'exact_matches': [],
                    'partial_matches': []
                }
            
            registry = response.get('registry', {})
            exact_matches = []
            partial_matches = []
            
            for hostname, info in registry.items():
                # Skip own files
                if hostname == self.hostname:
                    continue
                
                files = info.get('files', {})
                if fname in files:
                    finfo = files[fname]
                    other_size = finfo.get('size', 0)
                    other_modified = finfo.get('modified', 0)
                    
                    # Check if metadata matches
                    exact_match, size_match, time_match = FileMetadata(
                        fname, size, modified
                    ).matches_metadata(other_size, other_modified)
                    
                    if exact_match:
                        exact_matches.append({
                            'hostname': hostname,
                            'size': other_size,
                            'modified': other_modified
                        })
                    elif size_match or time_match:
                        # Partial match (different file)
                        partial_matches.append({
                            'hostname': hostname,
                            'size': other_size,
                            'modified': other_modified,
                            'size_match': size_match,
                            'time_match': time_match
                        })
            
            return {
                'has_exact_duplicate': len(exact_matches) > 0,
                'has_partial_duplicate': len(partial_matches) > 0,
                'exact_matches': exact_matches,
                'partial_matches': partial_matches
            }
            
        except Exception as e:
            print(f"[WARN] Failed to check duplicates: {e}")
            return {
                'has_exact_duplicate': False,
                'has_partial_duplicate': False,
                'exact_matches': [],
                'partial_matches': []
            }
    
    def unpublish(self, fname):
        """Remove a file from the published list and notify the server"""
        try:
            if fname not in self.published_files:
                print(f"[ERROR] File '{fname}' is not published")
                return False
            
            # Remove from published files
            self.published_files.pop(fname)
            
            # Update local file metadata
            if fname in self.local_files:
                self.local_files[fname].is_published = False
                self.local_files[fname].published_at = None
                # Save updated metadata
                self._save_file_metadata(fname)
            
            # Notify central server
            with self.central_lock:
                send_json(self.central, {
                    "action": "UNPUBLISH",
                    "data": {
                        "hostname": self.hostname,
                        "fname": fname
                    }
                })
                r = recv_json(self.central)
            
            if r and r.get('status') == 'ACK':
                print(f"[SUCCESS] Unpublished '{fname}' from network")
                # Save state to persist across reconnects
                self._save_state()
                return True
            else:
                print(f"[ERROR] Failed to unpublish: {r}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Exception during unpublish: {e}")
            return False

    def request(self, fname, save_path=None):
        """
        Request a file from the network with duplicate name warning
        
        Args:
            fname: Name of the file to download
            save_path: Optional custom save path. If None, saves to repo directory
        """
        # Mark activity for adaptive heartbeat
        if self.adaptive_heartbeat:
            self.adaptive_heartbeat.mark_activity("fetch")
        
        # Check if file with same name already exists locally
        if fname in self.local_files:
            local_meta = self.local_files[fname]
            print(f"\n[WARNING] File '{fname}' already exists in local repository!")
            print(f"   Local file - Size: {local_meta.size} bytes, Modified: {datetime.fromtimestamp(local_meta.modified).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Try to get info about the file to download
            with self.central_lock:
                send_json(self.central, {"action":"REQUEST","data":{"fname":fname}})
                r = recv_json(self.central)
            
            if r and r.get('status') == 'FOUND':
                hosts = r.get('hosts', [])
                if hosts:
                    remote_host = hosts[0]
                    print(f"   Remote file - Size: {remote_host.get('size', 'unknown')} bytes")
                    
                    # Check if they're the same file
                    if remote_host.get('size') == local_meta.size:
                        remote_modified = remote_host.get('modified', 0)
                        if abs(remote_modified - local_meta.modified) < 2:
                            print(f"\n[INFO] Files appear identical (same size and time). Download may be unnecessary.")
                        else:
                            print(f"\n[WARNING] Files have same size but different modified times!")
                    else:
                        print(f"\n[WARNING] Files have different sizes - different content!")
                    
                    # Ask user if they want to continue
                    try:
                        choice = input("\nContinue with download? (y/n): ").strip().lower()
                        if choice != 'y':
                            print("[INFO] Download cancelled.")
                            return None
                    except (EOFError, OSError):
                        # Non-interactive mode, continue anyway
                        print("[INFO] Non-interactive mode, continuing download...")
        
        with self.central_lock:
            send_json(self.central, {"action":"REQUEST","data":{"fname":fname}})
            r = recv_json(self.central)
        
        if not r:
            print("No response from server")
            return None
        if r.get('status') == 'NOTFOUND':
            print("File not found on network")
            return None
        hosts = r.get('hosts', [])
        if not hosts:
            print("No hosts returned")
            return None
        
        picked = hosts[0]
        print("Attempting download from", picked['hostname'], picked['ip'], picked['port'])
        threading.Thread(target=self.download_from_peer, args=(picked['ip'], picked['port'], fname, save_path), daemon=True).start()
        return picked

    def download_from_peer(self, ip, port, fname, save_path=None, progress_callback=None, fetch_id=None):
        """
        Download a file from a peer with chunked streaming and progress tracking
        This is a direct P2P transfer - no server intervention for file bits
        
        Args:
            ip: Peer IP address
            port: Peer port
            fname: Filename to download
            save_path: Optional custom save path. If None, saves to repo directory
            progress_callback: Optional callback(downloaded_bytes, total_bytes, speed_bps)
            fetch_id: Optional fetch ID to use existing FetchSession from fetch_manager
        
        Returns:
            Path to downloaded file or None on failure
        """
        # Mark as busy for large file transfers
        if self.adaptive_heartbeat:
            self.adaptive_heartbeat.start_file_transfer()
        
        try:
            # Import fetch manager (P2P-focused, no hashing)
            try:
                from optimizations.fetch_manager import FetchSession
                use_fetch_manager = True
            except ImportError:
                print("[WARN] Fetch manager not available, using legacy method")
                use_fetch_manager = False
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(30)  # Increased timeout for large files
            s.connect((ip, port))
            s.sendall(f"GET {fname}\n".encode())
            
            # Read header
            buf = b''
            while b'\n' not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    s.close()
                    print("[ERROR] Connection closed before receiving header")
                    if self.adaptive_heartbeat:
                        self.adaptive_heartbeat.end_file_transfer()
                    return None
                buf += chunk
            
            line, rest = buf.split(b'\n', 1)
            header = line.decode().strip().split(' ', 1)
            
            if header[0] != 'LENGTH':
                print(f"[ERROR] Peer error: {line.decode().strip()}")
                s.close()
                if self.adaptive_heartbeat:
                    self.adaptive_heartbeat.end_file_transfer()
                return None
            
            total_size = int(header[1])
            
            # Determine save location
            if save_path:
                outpath = os.path.abspath(os.path.expanduser(save_path))
                if os.path.isdir(outpath):
                    outpath = os.path.join(outpath, fname)
                os.makedirs(os.path.dirname(outpath), exist_ok=True)
            else:
                outpath = os.path.join(self.repo_dir, fname)
            
            print(f"[FETCH] Starting P2P download: {fname} ({total_size:,} bytes) from {ip}")
            
            # Use fetch session for large files (> 10MB) or if fetch_id provided
            fetch_session = None
            if use_fetch_manager and (total_size > 10*1024*1024 or fetch_id):
                if fetch_id:
                    # Use existing session from fetch_manager
                    from optimizations.fetch_manager import fetch_manager
                    fetch_session = fetch_manager.get_session(fetch_id)
                    if fetch_session:
                        print(f"[FETCH] Using managed session: {fetch_id}")
                        fetch_session.start()
                    else:
                        print(f"[WARN] Fetch session {fetch_id} not found, creating new one")
                        fetch_session = FetchSession(
                            file_name=fname,
                            total_size=total_size,
                            save_path=outpath,
                            peer_hostname="",
                            peer_ip=ip,
                            chunk_size=256*1024
                        )
                        fetch_session.start()
                else:
                    # Create standalone session
                    fetch_session = FetchSession(
                        file_name=fname,
                        total_size=total_size,
                        save_path=outpath,
                        peer_hostname="",
                        peer_ip=ip,
                        chunk_size=256*1024
                    )
                    fetch_session.start()
                
                # Download in chunks (direct P2P transfer)
                data = rest
                chunk_size = 256*1024  # 256KB network chunks
                
                while len(data) < total_size:
                    chunk = s.recv(min(chunk_size, total_size - len(data)))
                    if not chunk:
                        break
                    
                    # Write chunk
                    fetch_session.write_chunk(chunk)
                    data += chunk
                    
                    # Report progress
                    if progress_callback:
                        progress = fetch_session.get_progress()
                        progress_callback(
                            progress['downloaded_size'],
                            total_size,
                            progress['speed_bps']
                        )
                    
                    # Progress display (every 5%)
                    percent = (len(data) / total_size) * 100
                    if int(percent) % 5 == 0 and len(data) > 0:
                        speed_mbps = fetch_session.progress.speed_bps / (1024*1024)
                        print(f"[FETCH] Progress: {percent:.1f}% - {speed_mbps:.2f} MB/s")
                
                # Complete download - verify size only (P2P, no hashing)
                if fetch_session.complete():
                    print(f"[SUCCESS] P2P fetch complete: {fname}")
                    print(f"[VERIFY] Size verified: {total_size:,} bytes")
                else:
                    print(f"[ERROR] Fetch failed: {fetch_session.progress.error_message}")
                    s.close()
                    if self.adaptive_heartbeat:
                        self.adaptive_heartbeat.end_file_transfer()
                    return None
                
            if not fetch_session:
                # Legacy method for small files
                print(f"[FETCH] Using legacy method for small file")
                data = rest
                chunk_size = 256*1024
                bytes_received = len(data)
                
                with open(outpath, 'wb') as f:
                    if data:
                        f.write(data)
                    
                    while bytes_received < total_size:
                        chunk = s.recv(min(chunk_size, total_size - bytes_received))
                        if not chunk:
                            break
                        f.write(chunk)
                        bytes_received += len(chunk)
                        
                        if progress_callback:
                            progress_callback(bytes_received, total_size, 0)
                
                if bytes_received != total_size:
                    print(f"[ERROR] Size mismatch: expected {total_size}, got {bytes_received}")
                    s.close()
                    if self.adaptive_heartbeat:
                        self.adaptive_heartbeat.end_file_transfer()
                    return None
            
            s.close()
            
            # Get file metadata with cross-platform support
            try:
                meta_dict = get_file_metadata_crossplatform(outpath)
            except Exception as e:
                print(f"[WARN] Failed to read metadata, using fallback: {e}")
                stat = os.stat(outpath)
                meta_dict = {
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'created': stat.st_mtime,
                    'path': outpath
                }
            
            # Update metadata (only as local file, NOT auto-published)
            metadata = FileMetadata(
                name=fname,
                size=meta_dict['size'],
                modified=meta_dict['modified'],
                created=meta_dict['created'],
                path=outpath,
                is_published=False,
                added_at=time.time()
            )
            self.local_files[fname] = metadata
            
            # Save metadata to JSON
            self._save_file_metadata(fname)
            
            print(f"[SUCCESS] Downloaded '{fname}' -> '{outpath}' ({meta_dict['size']:,} bytes)")
            print(f"[INFO] File saved as local only. Use 'publish' command to share with network.")
            
            # End transfer state
            if self.adaptive_heartbeat:
                self.adaptive_heartbeat.end_file_transfer()
            
            return outpath
            
        except Exception as e:
            print(f"[ERROR] P2P fetch failed: {e}")
            import traceback
            traceback.print_exc()
            if self.adaptive_heartbeat:
                self.adaptive_heartbeat.end_file_transfer()
            return None

    def discover(self, hostname):
        with self.central_lock:
            send_json(self.central, {"action":"DISCOVER","data":{"hostname":hostname}})
            r = recv_json(self.central)
        print(r)

    def ping(self, hostname):
        with self.central_lock:
            send_json(self.central, {"action":"PING","data":{"hostname":hostname}})
            r = recv_json(self.central)
        print(r)

    def list_local(self):
        """List all local files (tracked metadata)"""
        print("\n=== YOUR FILES (Local Tracking) ===")
        if not self.local_files:
            print("  (No files tracked)")
        for fname, meta in self.local_files.items():
            pub_status = "✓ Published" if meta.is_published else "  Not published"
            print(f"  [{pub_status}] {fname} - {meta.size} bytes - {datetime.fromtimestamp(meta.modified).strftime('%Y-%m-%d %H:%M:%S')}")
    
    def list_published(self):
        """List only published files"""
        print("\n=== YOUR PUBLISHED FILES ===")
        if not self.published_files:
            print("  (No files published)")
        for fname, meta in self.published_files.items():
            print(f"  {fname} - {meta.size} bytes - Published: {datetime.fromtimestamp(meta.published_at).strftime('%Y-%m-%d %H:%M:%S')}")
    
    def list_network(self):
        """Fetch and display all files available on the network"""
        with self.central_lock:
            send_json(self.central, {"action":"LIST"})
            r = recv_json(self.central)
        
        print("\n=== NETWORK FILES (Available from all clients) ===")
        if r and r.get('status') == 'OK':
            registry = r.get('registry', {})
            if not registry:
                print("  (No clients connected)")
                return
            
            for hostname, info in registry.items():
                files = info.get('files', {})
                display_name = info.get('display_name', hostname)
                if files:
                    print(f"\n  From {display_name} ({hostname}):")
                    for fname, finfo in files.items():
                        size = finfo.get('size', 0)
                        modified = finfo.get('modified', 0)
                        modified_str = datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M:%S')
                        print(f"    • {fname} - {size} bytes - Modified: {modified_str}")
        else:
            print("  (Failed to retrieve network files)")

    def list_registry(self):
        with self.central_lock:
            send_json(self.central, {"action":"LIST"})
            r = recv_json(self.central)
        print(json.dumps(r, indent=2))

    def unregister(self):
        """Unregister from server and close connection"""
        try:
            with self.central_lock:
                send_json(self.central, {"action":"UNREGISTER","data":{"hostname":self.hostname}})
                recv_json(self.central)
        except:
            pass  # Ignore errors if connection already closed
    
    def close(self):
        """Close client and cleanup resources"""
        print(f"[CLIENT] Closing client '{self.hostname}'...")
        self.running = False  # Stop heartbeat thread and peer server
        
        # Stop peer server first (will exit its loop when running=False)
        try:
            if self.peer_server and hasattr(self.peer_server, 'stop'):
                self.peer_server.stop()
                print("[CLIENT] Peer server stopped")
        except Exception as e:
            print(f"[CLIENT] Error stopping peer server: {e}")
        
        # Unregister from central server
        try:
            self.unregister()
            print("[CLIENT] Unregistered from central server")
        except Exception as e:
            print(f"[CLIENT] Error unregistering: {e}")
        
        # Close central server connection
        try:
            self.central.close()
            print("[CLIENT] Central server connection closed")
        except Exception as e:
            print(f"[CLIENT] Error closing central connection: {e}")
        
        print(f"[CLIENT] Client '{self.hostname}' closed successfully")

def cli_loop(client):
    prompt = f"{client.display_name}> "
    print("\nAvailable commands:")
    print("  publish <localpath> <name> - Publish a file to the network")
    print("  unpublish <name>           - Remove a file from the network")
    print("  fetch <name>               - Fetch a file from the network")
    print("  add <filepath>             - Add a file to local tracking (metadata only)")
    print("  local                      - List your local files")
    print("  published                  - List your published files")
    print("  network                    - List all network files")
    print("  discover <host>            - Discover files from a specific host")
    print("  ping <host>                - Check if a host is alive")
    print("  registry                   - Show raw registry data")
    print("  exit                       - Exit the client")
    print()
    
    try:
        while True:
            line = input(prompt).strip()
            if not line:
                continue

            # --- Use shlex to properly handle quoted paths ---
            try:
                parts = shlex.split(line)
            except ValueError as e:
                print(f"[ERROR] Invalid command syntax: {e}")
                continue

            cmd = parts[0].lower()

            if cmd == 'publish' and len(parts) == 3:
                client.publish(parts[1], parts[2])
            
            elif cmd == 'unpublish' and len(parts) == 2:
                client.unpublish(parts[1])

            elif cmd == 'fetch' and len(parts) == 2:
                client.request(parts[1])
            
            elif cmd == 'add' and len(parts) == 2:
                client.add_local_file(parts[1])

            elif cmd == 'discover' and len(parts) == 2:
                client.discover(parts[1])

            elif cmd == 'ping' and len(parts) == 2:
                client.ping(parts[1])

            elif cmd == 'local':
                client.list_local()
            
            elif cmd == 'published':
                client.list_published()
            
            elif cmd == 'network':
                client.list_network()

            elif cmd == 'registry':
                client.list_registry()

            elif cmd == 'exit':
                client.unregister()
                print("bye")
                return

            else:
                print("[ERROR] Unknown command. Type 'help' or see available commands above.")

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt received. Exiting client...")
        client.unregister()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True, help='hostname id for this client')
    parser.add_argument('--port', type=int, required=True, help='listening port for peer connections')
    parser.add_argument('--repo', default='repo', help='local repository folder')
    parser.add_argument('--name', help='display name for this client (default: hostname)')
    parser.add_argument('--server-host', help=f'server IP address (default: {CENTRAL_HOST})')
    parser.add_argument('--server-port', type=int, help=f'server port (default: {CENTRAL_PORT})')
    args = parser.parse_args()
    c = Client(args.host, args.port, args.repo, args.name, args.server_host, args.server_port)
    print(f"\n=== Client '{c.display_name}' started ===")
    print(f"Hostname: {c.hostname}")
    print(f"Repository: {c.repo_dir}")
    print(f"Listening on port: {c.listen_port}")
    print(f"Connected to server: {c.server_host}:{c.server_port}")
    cli_loop(c)
