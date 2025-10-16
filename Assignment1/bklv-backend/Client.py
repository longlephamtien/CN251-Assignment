import socket
import threading
import json
import sys
import os
import time
import argparse

CENTRAL_HOST = '127.0.0.1'
CENTRAL_PORT = 9000

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
    def __init__(self, hostname, listen_port, repo_dir):
        self.hostname = hostname
        self.listen_port = listen_port
        self.repo_dir = repo_dir
        os.makedirs(self.repo_dir, exist_ok=True)
        self.central = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.central.connect((CENTRAL_HOST, CENTRAL_PORT))
        send_json(self.central, {"action":"REGISTER", "data":{"hostname":self.hostname, "port": self.listen_port}})
        resp = recv_json(self.central)
        if not resp or resp.get('status') != 'OK':
            print("Register failed", resp)
            sys.exit(1)
        self.pub_lock = threading.Lock()
        self.peer_server = PeerServer(self.listen_port, self.repo_dir)
        self.peer_server.start()
        threading.Thread(target=self.heartbeat_thread, daemon=True).start()
        self.local_files = set(os.listdir(self.repo_dir))
        self.central_lock = threading.Lock()

    def heartbeat_thread(self):
        while True:
            try:
                time.sleep(60)
                with self.central_lock:
                    send_json(self.central, {"action": "PING", "data": {"hostname": self.hostname}})
                    recv_json(self.central)
            except Exception as e:
                print("Heartbeat failed:", e)
                break


    def publish(self, local_path, fname):
        if not os.path.isfile(local_path):
            print("local file not found")
            return
        dest = os.path.join(self.repo_dir, fname)
        if local_path != dest:
            try:
                with open(local_path,'rb') as fr, open(dest,'wb') as fw:
                    fw.write(fr.read())
            except Exception as e:
                print("copy error", e)
                return
        self.local_files.add(fname)
        with self.central_lock:
            send_json(self.central, {"action":"PUBLISH","data":{"hostname":self.hostname,"fname":fname}})
            r = recv_json(self.central)
        if r and r.get('status') == 'ACK':
            print("Published", fname)
        else:
            print("Publish failed", r)

    def request(self, fname):
        with self.central_lock:
            send_json(self.central, {"action":"REQUEST","data":{"fname":fname}})
            r = recv_json(self.central)
        if not r:
            print("No response from server")
            return
        if r.get('status') == 'NOTFOUND':
            print("File not found on network")
            return
        hosts = r.get('hosts', [])
        if not hosts:
            print("No hosts returned")
            return
        picked = hosts[0]
        print("Attempting download from", picked['hostname'], picked['ip'], picked['port'])
        threading.Thread(target=self.download_from_peer, args=(picked['ip'], picked['port'], fname), daemon=True).start()

    def download_from_peer(self, ip, port, fname):
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
                    print("connection closed unexpectedly")
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
                        outpath = os.path.join(self.repo_dir, fname)
                        with open(outpath, 'wb') as f:
                            f.write(data[:length])
                        self.local_files.add(fname)
                        print("Downloaded", fname, "->", outpath)
                        s.close()
                        with self.central_lock:
                            send_json(self.central, {"action":"PUBLISH","data":{"hostname":self.hostname,"fname":fname}})
                            recv_json(self.central)
                        return
                    else:
                        print("Peer error:", line.decode().strip())
                        s.close()
                        return
        except Exception as e:
            print("download error", e)

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
        print("Local repo:", list(self.local_files))

    def list_registry(self):
        with self.central_lock:
            send_json(self.central, {"action":"LIST"})
            r = recv_json(self.central)
        print(json.dumps(r, indent=2))

    def unregister(self):
        with self.central_lock:
            send_json(self.central, {"action":"UNREGISTER","data":{"hostname":self.hostname}})
            recv_json(self.central)
        self.central.close()

def cli_loop(client):
    prompt = "p2p> "
    try:
        while True:
            line = input(prompt).strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0].lower()
            if cmd == 'publish' and len(parts) == 3:
                client.publish(parts[1], parts[2])
            elif cmd == 'fetch' and len(parts) == 2:
                client.request(parts[1])
            elif cmd == 'discover' and len(parts) == 2:
                client.discover(parts[1])
            elif cmd == 'ping' and len(parts) == 2:
                client.ping(parts[1])
            elif cmd == 'list':
                client.list_local()
            elif cmd == 'registry':
                client.list_registry()
            elif cmd == 'exit':
                client.unregister()
                print("bye")
                return
            else:
                print("commands: publish <localpath> <name> | fetch <name> | discover <host> | ping <host> | list | registry | exit")
    except KeyboardInterrupt:
        client.unregister()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True, help='hostname id for this client')
    parser.add_argument('--port', type=int, required=True, help='listening port for peer connections')
    parser.add_argument('--repo', default='repo', help='local repository folder')
    args = parser.parse_args()
    c = Client(args.host, args.port, args.repo)
    print("Client started. CLI: publish/fetch/discover/ping/list/registry/exit")
    cli_loop(c)
