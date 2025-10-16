import socket
import threading
import json
import time

HOST = '' 
PORT = 9000

registry_lock = threading.Lock()
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
                if hostname and port:
                    with registry_lock:
                        registry[hostname] = {
                            "addr": (addr[0], port),
                            "files": set(),
                            "last_seen": time.time()
                        }
                    print(f"[REGISTER] {hostname} at {addr[0]}:{port}")
                    send_json(conn, {"status": "OK"})
                else:
                    send_json(conn, {"status": "ERROR", "reason": "bad register"})
            elif action == 'PUBLISH':
                hostname = data.get('hostname')
                fname = data.get('fname')
                if not hostname:
                    send_json(conn, {"status": "ERROR", "reason": "missing hostname"})
                    continue
                with registry_lock:
                    if hostname not in registry:
                        print(f"[WARN] Host {hostname} tried to publish before register")
                        # tự động thêm vào nếu client chưa từng register
                        registry[hostname] = {"addr": addr, "files": set(), "last_seen": time.time()}
                    registry[hostname]["files"].add(fname)
                    registry[hostname]["last_seen"] = time.time()
                print(f"[PUBLISH] {hostname} shared file '{fname}'")
                send_json(conn, {"status": "ACK"})
            elif action == 'REQUEST':
                fname = data.get('fname')
                if fname:
                    with registry_lock:
                        hosts = []
                        for h, info in registry.items():
                            if fname in info['files']:
                                hosts.append({
                                    "hostname": h,
                                    "ip": info['addr'][0],
                                    "port": info['addr'][1]
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
                        send_json(conn, {"status": "OK", "files": list(info["files"]), "addr": info["addr"]})
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
                    snapshot = {h: {"addr": info["addr"], "files": list(info["files"])} for h, info in registry.items()}
                send_json(conn, {"status": "OK", "registry": snapshot})
            else:
                send_json(conn, {"status": "ERROR", "reason": f"unknown action {action}"})
    except Exception as e:
        print(f"[ERROR] Connection {addr} -> {e}")
    finally:
        conn.close()

def cleanup_thread():
    while True:
        time.sleep(30)
        now = time.time()
        with registry_lock:
            to_remove = [h for h, info in registry.items() if now - info["last_seen"] > 120]
            for h in to_remove:
                print(f"[CLEANUP] Removing inactive host {h}")
                registry.pop(h, None)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(10)
    threading.Thread(target=cleanup_thread, daemon=True).start()
    print("Server running on port", PORT)
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Server stopped.")
        s.close()

if __name__ == "__main__":
    main()
