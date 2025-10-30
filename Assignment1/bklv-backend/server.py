import socket
import threading
import json
import time
from datetime import datetime
from config import (
    SERVER_HOST, 
    SERVER_PORT,
    CLIENT_CLEANUP_INTERVAL,
    CLIENT_INACTIVE_TIMEOUT
)

HOST = SERVER_HOST if SERVER_HOST != '127.0.0.1' else ''
PORT = SERVER_PORT

registry_lock = threading.Lock()
# Enhanced registry structure:
# {
#   "hostname": {
#     "addr": (ip, port),
#     "display_name": "User Name",
#     "files": {
#       "filename.txt": {
#         "size": 1234,
#         "modified": timestamp,
#         "published_at": timestamp
#       }
#     },
#     "last_seen": timestamp,
#     "connected_at": timestamp
#   }
# }
registry = {}

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

def handle_conn(conn, addr):
    hostname = None
    try:
        while True:
            msg = recv_json(conn)
            if not msg:
                break
            action = msg.get('action')
            data = msg.get('data', {})
            if action == 'REGISTER':
                hostname = data.get('hostname')
                port = data.get('port')
                display_name = data.get('display_name', hostname)
                files_metadata = data.get('files_metadata', {})  # New: get metadata from client
                if hostname and port:
                    with registry_lock:
                        registry[hostname] = {
                            "addr": (addr[0], port),
                            "display_name": display_name,
                            "files": {},
                            "last_seen": time.time(),
                            "connected_at": time.time()
                        }
                        # Restore file metadata (published/unpublished status)
                        for fname, meta in files_metadata.items():
                            registry[hostname]["files"][fname] = {
                                "size": meta.get("size", 0),
                                "modified": meta.get("modified", 0),
                                "published_at": meta.get("published_at", None),
                                "is_published": meta.get("is_published", False)
                            }
                    print(f"[REGISTER] {hostname} ({display_name}) at {addr[0]}:{port} with {len(files_metadata)} files")
                    send_json(conn, {"status": "OK"})
                else:
                    send_json(conn, {"status": "ERROR", "reason": "bad register"})
            elif action == 'PUBLISH':
                hostname = data.get('hostname')
                fname = data.get('fname')
                file_size = data.get('size', 0)
                file_modified = data.get('modified', time.time())
                if not hostname:
                    send_json(conn, {"status": "ERROR", "reason": "missing hostname"})
                    continue
                with registry_lock:
                    if hostname not in registry:
                        print(f"[WARN] Host {hostname} tried to publish before register")
                        registry[hostname] = {
                            "addr": addr, 
                            "display_name": hostname,
                            "files": {}, 
                            "last_seen": time.time(),
                            "connected_at": time.time()
                        }
                    registry[hostname]["files"][fname] = {
                        "size": file_size,
                        "modified": file_modified,
                        "published_at": time.time(),
                        "is_published": True
                    }
                    registry[hostname]["last_seen"] = time.time()
                print(f"[PUBLISH] {hostname} shared file '{fname}' ({file_size} bytes)")
                send_json(conn, {"status": "ACK"})
            elif action == 'UNPUBLISH':
                hostname = data.get('hostname')
                fname = data.get('fname')
                if not hostname or not fname:
                    send_json(conn, {"status": "ERROR", "reason": "missing hostname or fname"})
                    continue
                with registry_lock:
                    if hostname in registry and fname in registry[hostname]["files"]:
                        # Instead of deleting, mark as unpublished
                        registry[hostname]["files"][fname]["is_published"] = False
                        registry[hostname]["files"][fname]["published_at"] = None
                        registry[hostname]["last_seen"] = time.time()
                        print(f"[UNPUBLISH] {hostname} marked file '{fname}' as unpublished")
                        send_json(conn, {"status": "ACK"})
                    else:
                        send_json(conn, {"status": "ERROR", "reason": "file not found"})
            elif action == 'REQUEST':
                fname = data.get('fname')
                if fname:
                    with registry_lock:
                        hosts = []
                        for h, info in registry.items():
                            if fname in info['files']:
                                file_info = info['files'][fname]
                                # Only return if file is published
                                if file_info.get('is_published', False):
                                    hosts.append({
                                        "hostname": h,
                                        "display_name": info.get('display_name', h),
                                        "ip": info['addr'][0],
                                        "port": info['addr'][1],
                                        "size": file_info.get('size', 0),
                                        "modified": file_info.get('modified', 0),
                                        "is_published": True
                                    })
                    print(f"[REQUEST] {addr} requested '{fname}', found {len(hosts)} host(s)")
                    send_json(conn, {"status": "FOUND" if hosts else "NOTFOUND", "hosts": hosts})
                else:
                    send_json(conn, {"status": "ERROR", "reason": "bad request"})
            elif action == 'DISCOVER':
                hname = data.get('hostname')
                with registry_lock:
                    info = registry.get(hname)
                    if info:
                        # Return only published files
                        published_files = {
                            fname: finfo 
                            for fname, finfo in info["files"].items() 
                            if finfo.get('is_published', False)
                        }
                        send_json(conn, {"status": "OK", "files": published_files, "addr": info["addr"]})
                    else:
                        send_json(conn, {"status": "ERROR", "reason": "unknown host"})
            elif action == 'PING':
                target = data.get('hostname')
                with registry_lock:
        # Cập nhật client đang ping (người gửi)
                    if hostname and hostname in registry:
                        registry[hostname]["last_seen"] = time.time()
        # Kiểm tra xem peer được ping còn tồn tại không
                    if target in registry:
                        send_json(conn, {"status": "ALIVE"})
                        print(f"[PING] {hostname} checked {target} -> ALIVE")
                    else:
                        send_json(conn, {"status": "DEAD"})
                        print(f"[PING] {hostname} checked {target} -> DEAD")

            elif action == 'UNREGISTER':
                hname = data.get('hostname')
                if hname:
                    with registry_lock:
                        registry.pop(hname, None)
                        print(f"[UNREGISTER] {hname} removed from registry")
                    send_json(conn, {"status": "OK"})
                else:
                    send_json(conn, {"status": "ERROR", "reason": "bad unregister"})
            elif action == 'LIST':
                with registry_lock:
                    snapshot = {
                        h: {
                            "addr": info["addr"], 
                            "display_name": info.get("display_name", h),
                            # Only include published files
                            "files": {
                                fname: finfo 
                                for fname, finfo in info["files"].items() 
                                if finfo.get('is_published', False)
                            },
                            "last_seen": info["last_seen"],
                            "connected_at": info.get("connected_at", info["last_seen"])
                        } 
                        for h, info in registry.items()
                    }
                send_json(conn, {"status": "OK", "registry": snapshot})
            else:
                send_json(conn, {"status": "ERROR", "reason": f"unknown action {action}"})
    except Exception as e:
        print(f"[ERROR] Connection {addr} -> {e}")
    finally:
        conn.close()

def cleanup_thread():
    """Remove inactive clients based on configured timeout"""
    while True:
        time.sleep(CLIENT_CLEANUP_INTERVAL)
        now = time.time()
        with registry_lock:
            to_remove = [h for h, info in registry.items() if now - info["last_seen"] > CLIENT_INACTIVE_TIMEOUT]
            for h in to_remove:
                print(f"[CLEANUP] Removing inactive host {h} (timeout: {CLIENT_INACTIVE_TIMEOUT}s)")
                registry.pop(h, None)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(10)
    threading.Thread(target=cleanup_thread, daemon=True).start()
    print(f"=== P2P File Sharing Server Started ===")
    print(f"Server running on {HOST or '0.0.0.0'}:{PORT}")
    print(f"Waiting for client connections...")
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user.")
        s.close()

if __name__ == "__main__":
    main()
