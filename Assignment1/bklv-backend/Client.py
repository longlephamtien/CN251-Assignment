import socket
import threading
import json
import shutil
import sys
import os
import shlex
import time
import argparse
from datetime import datetime

try:
    from config import SERVER_HOST, SERVER_PORT
    CENTRAL_HOST = SERVER_HOST
    CENTRAL_PORT = SERVER_PORT
except:
    CENTRAL_HOST = '127.0.0.1'
    CENTRAL_PORT = 9000

class FileMetadata:
    """Tracks file metadata for local, published, and network files"""
    def __init__(self, name, size, modified, path=None, is_published=False):
        self.name = name
        self.size = size
        self.modified = modified
        self.path = path
        self.is_published = is_published
        self.published_at = time.time() if is_published else None
    
    def to_dict(self):
        return {
            'name': self.name,
            'size': self.size,
            'modified': self.modified,
            'path': self.path,
            'is_published': self.is_published,
            'published_at': self.published_at
        }

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
    def __init__(self, listen_port, repo_dir):
        super().__init__(daemon=True)
        self.listen_port = listen_port
        self.repo_dir = repo_dir
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', self.listen_port))
        self.sock.listen(5)

    def run(self):
        while True:
            conn, addr = self.sock.accept()
            threading.Thread(target=self.handle_peer, args=(conn, addr), daemon=True).start()

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
                fpath = os.path.join(self.repo_dir, fname)
                if os.path.isfile(fpath):
                    size = os.path.getsize(fpath)
                    conn.sendall(f"LENGTH {size}\n".encode())
                    with open(fpath, 'rb') as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            conn.sendall(chunk)
                else:
                    conn.sendall(b"ERROR notfound\n")
        except:
            pass
        finally:
            conn.close()

class Client:
    def __init__(self, hostname, listen_port, repo_dir, display_name=None):
        self.hostname = hostname
        self.display_name = display_name or hostname
        self.listen_port = listen_port
        self.repo_dir = repo_dir
        os.makedirs(self.repo_dir, exist_ok=True)
        
        # Three-tier file management
        self.local_files = {}  # All files tracked by client (metadata only)
        self.published_files = {}  # Files published to network (subset of local)
        self.network_files = {}  # Files available from other clients
        
        # State file to persist published status
        self.state_file = os.path.join(self.repo_dir, '.client_state.json')
        
        # Control flag for threads
        self.running = True
        
        # IMPORTANT: Scan repo directory FIRST to get current files
        self._scan_repo_directory()
        
        # Load state from local file (if exists)
        self._load_state()
        
        # Then connect and register
        self.central_lock = threading.Lock()
        self.central = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.central.connect((CENTRAL_HOST, CENTRAL_PORT))
        
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
            print("Register failed", resp)
            sys.exit(1)
        
        self.pub_lock = threading.Lock()
        self.peer_server = PeerServer(self.listen_port, self.repo_dir)
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
        """Scan repository directory and build local file metadata"""
        try:
            for fname in os.listdir(self.repo_dir):
                # Skip hidden files and internal state files
                if fname.startswith('.'):
                    continue
                    
                fpath = os.path.join(self.repo_dir, fname)
                if os.path.isfile(fpath):
                    stat = os.stat(fpath)
                    self.local_files[fname] = FileMetadata(
                        name=fname,
                        size=stat.st_size,
                        modified=stat.st_mtime,
                        path=fpath,
                        is_published=False
                    )
            print(f"[INFO] Scanned {len(self.local_files)} files from repository")
        except Exception as e:
            print(f"[ERROR] Failed to scan repository: {e}")
    
    def add_local_file(self, filepath):
        """Add a file to local tracking (without copying or publishing)"""
        filepath = os.path.abspath(os.path.expanduser(filepath))
        if not os.path.isfile(filepath):
            print(f"[ERROR] File not found: {filepath}")
            return False
        
        fname = os.path.basename(filepath)
        stat = os.stat(filepath)
        self.local_files[fname] = FileMetadata(
            name=fname,
            size=stat.st_size,
            modified=stat.st_mtime,
            path=filepath,
            is_published=False
        )
        print(f"[INFO] Added '{fname}' to local tracking")
        return True
    
    def heartbeat_thread(self):
        while self.running:
            try:
                time.sleep(60)
                if not self.running:
                    break
                with self.central_lock:
                    send_json(self.central, {"action": "PING", "data": {"hostname": self.hostname}})
                    recv_json(self.central)
            except Exception as e:
                if self.running:  # Only log if we're supposed to be running
                    print("Heartbeat failed:", e)
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

    def publish(self, local_path, fname, overwrite=True, interactive=True):
        """Publish a file from anywhere into the local repo and notify the central server.
        
        Args:
            local_path: Path to the local file
            fname: Name to give the file in the repository
            overwrite: If True, automatically overwrite existing files (default: True)
            interactive: If True, prompt user for confirmation (default: True, CLI mode)
        """
        try:
            # Normalize path (expand ~ and make absolute)
            local_path = os.path.expanduser(local_path)
            local_path = os.path.abspath(local_path)

            # Check if file exists
            if not os.path.isfile(local_path):
                print(f"[ERROR] Local file not found: {local_path}")
                return False

            # Ensure repo directory exists
            os.makedirs(self.repo_dir, exist_ok=True)
            dest = os.path.join(self.repo_dir, fname)
            dest = os.path.abspath(dest)  # Normalize destination path too

            # Check if source and destination are the same file
            same_file = False
            if os.path.exists(dest):
                try:
                    same_file = os.path.samefile(local_path, dest)
                except (OSError, ValueError):
                    # Fallback to string comparison if samefile fails
                    same_file = (local_path == dest)
            
            if same_file:
                # File is already in the correct location, just update metadata and publish
                print(f"[INFO] File '{fname}' already in repository, updating metadata...")
            else:
                # Check if file already exists (different file with same name)
                if os.path.exists(dest):
                    if interactive:
                        # Interactive mode (CLI): Ask user
                        try:
                            print(f"[WARNING] A file named '{fname}' already exists in repo.")
                            choice = input("Overwrite it? (y/n): ").strip().lower()
                            if choice != 'y':
                                print("[INFO] Publish cancelled.")
                                return False
                        except (EOFError, OSError):
                            # No terminal available, use overwrite parameter
                            if not overwrite:
                                print(f"[ERROR] File '{fname}' already exists and overwrite=False")
                                return False
                            print(f"[INFO] No terminal available, auto-overwriting '{fname}'")
                    else:
                        # Non-interactive mode (API): Use overwrite parameter
                        if not overwrite:
                            print(f"[ERROR] File '{fname}' already exists and overwrite=False")
                            return False
                        print(f"[INFO] Overwriting existing file '{fname}'")

                # Copy file into repository
                try:
                    shutil.copy2(local_path, dest)
                    print(f"[INFO] Copied '{local_path}' → '{dest}'")
                except Exception as e:
                    print(f"[ERROR] Failed to copy file: {e}")
                    return False
            
            # Get file metadata
            stat = os.stat(dest)
            file_size = stat.st_size
            file_modified = stat.st_mtime

            # Update local tracking
            metadata = FileMetadata(
                name=fname,
                size=file_size,
                modified=file_modified,
                path=dest,
                is_published=True
            )
            self.local_files[fname] = metadata
            self.published_files[fname] = metadata

            # Notify central server with metadata
            with self.central_lock:
                send_json(self.central, {
                    "action": "PUBLISH",
                    "data": {
                        "hostname": self.hostname, 
                        "fname": fname,
                        "size": file_size,
                        "modified": file_modified
                    }
                })
                r = recv_json(self.central)

            if r and r.get('status') == 'ACK':
                print(f"[SUCCESS] Published '{fname}' to network ({file_size} bytes).")
                # Save state to persist across reconnects
                self._save_state()
                return True
            else:
                print(f"[ERROR] Publish failed: {r}")
                return False

        except Exception as e:
            print(f"[ERROR] Exception during publish: {e}")
            return False
    
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
        Request a file from the network
        
        Args:
            fname: Name of the file to download
            save_path: Optional custom save path. If None, saves to repo directory
        """
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

    def download_from_peer(self, ip, port, fname, save_path=None):
        """
        Download a file from a peer
        
        Args:
            ip: Peer IP address
            port: Peer port
            fname: Filename to download
            save_path: Optional custom save path. If None, saves to repo directory
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((ip, port))
            s.sendall(f"GET {fname}\n".encode())
            buf = b''
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    s.close()
                    print("[ERROR] Connection closed unexpectedly")
                    return
                buf += chunk
                if b'\n' in buf:
                    line, rest = buf.split(b'\n', 1)
                    header = line.decode().strip().split(' ',1)
                    if header[0] == 'LENGTH':
                        length = int(header[1])
                        data = rest
                        while len(data) < length:
                            more = s.recv(8192)
                            if not more:
                                break
                            data += more
                        
                        # Determine save location
                        if save_path:
                            # Use custom save path
                            outpath = os.path.abspath(os.path.expanduser(save_path))
                            # If save_path is a directory, append filename
                            if os.path.isdir(outpath):
                                outpath = os.path.join(outpath, fname)
                            os.makedirs(os.path.dirname(outpath), exist_ok=True)
                        else:
                            # Default to repo directory
                            outpath = os.path.join(self.repo_dir, fname)
                        
                        # Write file
                        with open(outpath, 'wb') as f:
                            f.write(data[:length])
                        
                        # Update metadata (only as local file, NOT auto-published)
                        stat = os.stat(outpath)
                        metadata = FileMetadata(
                            name=fname,
                            size=stat.st_size,
                            modified=stat.st_mtime,
                            path=outpath,
                            is_published=False  # Downloaded files are NOT auto-published
                        )
                        self.local_files[fname] = metadata
                        
                        print(f"[SUCCESS] Downloaded '{fname}' -> '{outpath}' ({stat.st_size} bytes)")
                        print(f"[INFO] File saved as local only. Use 'publish' command to share with network.")
                        s.close()
                        return
                    else:
                        print("[ERROR] Peer error:", line.decode().strip())
                        s.close()
                        return
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")

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
        self.running = False  # Stop heartbeat thread
        try:
            self.unregister()
        except:
            pass
        try:
            self.central.close()
        except:
            pass
        try:
            # Stop peer server if it has a stop method
            if hasattr(self.peer_server, 'stop'):
                self.peer_server.stop()
        except:
            pass

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
    args = parser.parse_args()
    c = Client(args.host, args.port, args.repo, args.name)
    print(f"\n=== Client '{c.display_name}' started ===")
    print(f"Hostname: {c.hostname}")
    print(f"Repository: {c.repo_dir}")
    print(f"Listening on port: {c.listen_port}")
    cli_loop(c)
