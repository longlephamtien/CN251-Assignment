# Technical Analysis - P2P File Sharing System

## 1. Metadata Server lưu những gì?

**Location:** `Assignment1/bklv-backend/server.py`

Metadata server lưu trữ trong biến `registry`:

```python
registry = {
  "hostname": {
    "addr": (ip, port),           # IP và port của client để kết nối P2P
    "display_name": "User Name",   # Tên hiển thị
    "files": {
      "filename.txt": {
        "size": 1234,              # Kích thước file (bytes)
        "modified": timestamp,     # Thời gian sửa đổi cuối
        "published_at": timestamp, # Thời gian publish lên network
        "is_published": True       # Trạng thái published/unpublished
      }
    },
    "last_seen": timestamp,        # Lần cuối client gửi heartbeat
    "connected_at": timestamp      # Thời điểm kết nối ban đầu
  }
}
```

**Chú ý quan trọng:**
- Server **CHỈ** lưu metadata (thông tin về file), **KHÔNG** lưu nội dung file
- File thực tế nằm trên máy client tại `path` được lưu trong client
- Khi REGISTER, client gửi metadata của tất cả published files

---

## 2. Làm sao để 2 client connect được với nhau để gửi file qua lại?

**Quy trình P2P connection (Direct Peer-to-Peer):**

### Bước 1: Client yêu cầu file từ server
**Location:** `client.py` - hàm `request()`

```python
# Client gửi REQUEST action đến server
send_json(self.central, {
    "action": "REQUEST",
    "data": {"fname": fname}
})
```

### Bước 2: Server trả về thông tin peer
**Location:** `server.py` - xử lý REQUEST

```python
# Server tìm tất cả clients có file này
hosts = []
for h, info in registry.items():
    if fname in info['files']:
        hosts.append({
            "hostname": h,
            "ip": info['addr'][0],    # IP để kết nối P2P
            "port": info['addr'][1],  # Port để kết nối P2P
            "size": file_info['size']
        })
```

### Bước 3: Client kết nối trực tiếp đến peer
**Location:** `client.py` - hàm `download_from_peer()`

```python
# 1. Mở kết nối TCP đến peer
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))  # Kết nối TRỰC TIẾP đến client khác

# 2. Gửi lệnh GET
s.sendall(f"GET {fname}\n".encode())

# 3. Nhận file từ peer
# ... đọc header LENGTH ...
# ... download file chunks ...
```

### Bước 4: Peer server phục vụ file
**Location:** `client.py` - class `PeerServer`

```python
class PeerServer(threading.Thread):
    def __init__(self, listen_port, client_ref):
        # Mở socket lắng nghe trên port của client
        self.sock.bind(('', self.listen_port))
        self.sock.listen(5)
    
    def handle_peer(self, conn, addr):
        # Nhận lệnh GET
        cmd = line.decode().strip().split(' ',1)
        if cmd[0] == 'GET':
            fname = cmd[1]
            # Đọc file và gửi về
            with open(fpath, 'rb') as f:
                conn.sendall(chunk)
```

**Sơ đồ:**
```
Client A                 Server              Client B
   |                       |                     |
   |--REQUEST(file)------->|                     |
   |                       |                     |
   |<----hosts(B's IP)-----|                     |
   |                                             |
   |----------DIRECT TCP CONNECTION------------->|
   |              (P2P - no server)              |
   |<-----------FILE TRANSFER--------------------|
```

---

## 3. Ví dụ khi FETCH thì gửi thông tin gì?

### A. Client → Server (REQUEST action)
**Location:** `client.py` - dòng 656-670

```python
send_json(self.central, {
    "action": "REQUEST",
    "data": {
        "fname": "example.pdf"  # Chỉ cần tên file
    }
})
```

### B. Server → Client (Response)
**Location:** `server.py` - dòng 116-131

```python
# Nếu tìm thấy file
{
    "status": "FOUND",
    "hosts": [
        {
            "hostname": "user1",
            "display_name": "John Doe",
            "ip": "192.168.1.100",      # IP để kết nối P2P
            "port": 6001,               # Port để kết nối P2P
            "size": 1048576,            # 1MB
            "modified": 1731398400.0,
            "is_published": True
        }
    ]
}

# Nếu không tìm thấy
{
    "status": "NOTFOUND",
    "hosts": []
}
```

### C. Client A → Client B (P2P GET)
**Location:** `client.py` - dòng 704-706

```
Protocol: Plain text over TCP
Message: "GET example.pdf\n"
```

### D. Client B → Client A (Response)
**Location:** `client.py` - PeerServer (dòng 316-341)

```
1. Header: "LENGTH 1048576\n"
2. Binary data: [file chunks...]
```

**Timeline:**
```
1. Client A → Server: REQUEST {fname: "file.pdf"}
2. Server → Client A: {status: "FOUND", hosts: [{ip: "192.168.1.100", port: 6001}]}
3. Client A → Client B (192.168.1.100:6001): "GET file.pdf\n"
4. Client B → Client A: "LENGTH 1048576\n" + [binary data]
5. Client A: Save file to disk
```

---

## 4. Server ping tới client bằng TCP hay UDP? Code ở đâu? Ping liên tục hay gián đoạn? Tại sao?

### A. Protocol: **TCP** (không phải UDP)
- Tái sử dụng kết nối TCP đã mở từ REGISTER
- **Không** phải server ping client
- Mà là **client gửi heartbeat đến server** (ngược lại!)

### B. Code ở đâu?

#### Client-side Heartbeat Thread
**Location:** `client.py` - hàm `heartbeat_thread()` (dòng 610-637)

```python
def heartbeat_thread(self):
    """Client chủ động gửi heartbeat đến server"""
    while self.running:
        # Lấy interval (adaptive hoặc fixed)
        if self.adaptive_heartbeat:
            interval = self.adaptive_heartbeat.get_interval()
        else:
            interval = CLIENT_HEARTBEAT_INTERVAL  # 60s
        
        time.sleep(interval)
        
        # GỬI PING đến server qua TCP
        with self.central_lock:
            send_json(self.central, {
                "action": "PING",
                "data": {"hostname": self.hostname}
            })
            recv_json(self.central)
```

#### Server-side Handler
**Location:** `server.py` - xử lý PING (dòng 139-152)

```python
elif action == 'PING':
    target = data.get('hostname')
    with registry_lock:
        # Cập nhật last_seen timestamp
        if hostname and hostname in registry:
            registry[hostname]["last_seen"] = time.time()
        
        # Kiểm tra peer có tồn tại không
        if target in registry:
            send_json(conn, {"status": "ALIVE"})
        else:
            send_json(conn, {"status": "DEAD"})
```

### C. Ping gián đoạn (Adaptive Intervals)

**Location:** `config.py` và `adaptive_heartbeat.py`

```python
# Default interval
CLIENT_HEARTBEAT_INTERVAL = 60  # seconds

# Với Adaptive Heartbeat:
IDLE_INTERVAL = 300      # 5 phút (client không hoạt động)
ACTIVE_INTERVAL = 60     # 1 phút (client online bình thường)
BUSY_INTERVAL = 30       # 30 giây (đang transfer file)
```

**Automatic State Transitions:**
```python
# adaptive_heartbeat.py - dòng 78-92
def _update_state(self):
    now = time.time()
    idle_time = now - self.last_activity
    
    # Tự động chuyển sang IDLE sau 5 phút không hoạt động
    if idle_time > 300:  # IDLE_THRESHOLD
        if self.state != ClientState.IDLE:
            self._change_state(ClientState.IDLE)
```

### D. Tại sao chọn phương án này?

**1. Tại sao TCP thay vì UDP?**
- ✅ Tái sử dụng kết nối đã có (không cần mở thêm socket)
- ✅ Đảm bảo reliability (heartbeat không bị mất)
- ✅ Đơn giản hơn (không cần xử lý packet loss)
- ❌ UDP tốn thêm resource mở port riêng

**2. Tại sao client ping server (không phải ngược lại)?**
- ✅ **NAT-friendly:** Client sau NAT vẫn ping được server
- ✅ **Scalability:** Server không cần quản lý 100k timers
- ✅ **Bandwidth:** Server không tốn bandwidth gửi đến 100k clients
- ❌ Nếu server ping client: cần 100k outbound connections

**3. Tại sao ping gián đoạn (Adaptive)?**
```
Với 100,000 clients:

Fixed 60s:
- Heartbeats/s = 100,000 / 60 = 1,667 req/s
- Bandwidth = 1,667 * 200 bytes = 333 KB/s

Adaptive (assume 60% idle, 35% active, 5% busy):
- Idle (300s): 60,000 / 300 = 200 req/s
- Active (60s): 35,000 / 60 = 583 req/s
- Busy (30s): 5,000 / 30 = 167 req/s
- Total = 950 req/s (GIẢM 43%)
- Bandwidth = 190 KB/s (GIẢM 43%)
```

**4. Cleanup thread để xóa inactive clients**
**Location:** `server.py` - dòng 165-173

```python
def cleanup_thread():
    while True:
        time.sleep(CLIENT_CLEANUP_INTERVAL)  # 30s
        now = time.time()
        with registry_lock:
            # Xóa clients không gửi heartbeat > 20 phút
            to_remove = [
                h for h, info in registry.items() 
                if now - info["last_seen"] > CLIENT_INACTIVE_TIMEOUT  # 1200s
            ]
```

---

## 5. Client interrupt thì làm sao server biết? Code ở đâu?

### A. Kịch bản 1: Graceful Shutdown (Client đóng đúng cách)

**Location:** `client.py` - hàm `close()` (dòng 885-911)

```python
def close(self):
    """Close client and cleanup resources"""
    self.running = False  # Dừng tất cả threads
    
    # Gửi UNREGISTER đến server
    try:
        with self.central_lock:
            send_json(self.central, {
                "action": "UNREGISTER",
                "data": {"hostname": self.hostname}
            })
            recv_json(self.central)
    except:
        pass  # Ignore nếu kết nối đã đóng
    
    # Đóng tất cả connections
    self.central.close()
```

**Server xử lý UNREGISTER:**
**Location:** `server.py` - dòng 154-161

```python
elif action == 'UNREGISTER':
    hname = data.get('hostname')
    if hname:
        with registry_lock:
            # XÓA client khỏi registry ngay lập tức
            registry.pop(hname, None)
            print(f"[UNREGISTER] {hname} removed from registry")
```

### B. Kịch bản 2: Ungraceful Shutdown (Crash/Đột ngột)

**Phát hiện qua Heartbeat timeout:**

**Location:** `server.py` - cleanup_thread (dòng 165-173)

```python
def cleanup_thread():
    """Background thread xóa inactive clients"""
    while True:
        time.sleep(30)  # Kiểm tra mỗi 30 giây
        now = time.time()
        with registry_lock:
            # Tìm clients không heartbeat > 20 phút
            to_remove = [
                h for h, info in registry.items() 
                if now - info["last_seen"] > 1200  # CLIENT_INACTIVE_TIMEOUT
            ]
            for h in to_remove:
                print(f"[CLEANUP] Removing inactive host {h}")
                registry.pop(h, None)
```

**Cơ chế hoạt động:**
1. Client gửi heartbeat mỗi 60s (hoặc adaptive)
2. Server cập nhật `last_seen` timestamp
3. Cleanup thread chạy mỗi 30s
4. Nếu `now - last_seen > 1200s` (20 phút) → XÓA

**Timeline khi client crash:**
```
T=0:     Client gửi heartbeat cuối → last_seen = 0
T=60:    Client crash (không gửi heartbeat)
T=120:   Cleanup check #1 (0 < 1200) → PASS
T=180:   Cleanup check #2 (60 < 1200) → PASS
...
T=1200:  Cleanup check #40 (1200 >= 1200) → REMOVE CLIENT
```

### C. Kịch bản 3: Network Partition

**Server phát hiện khi handle connection fails:**
**Location:** `server.py` - dòng 194-196

```python
try:
    while True:
        msg = recv_json(conn)
        if not msg:  # Connection closed
            break
except Exception as e:
    print(f"[ERROR] Connection {addr} -> {e}")
finally:
    conn.close()  # Đóng connection
    # Client sẽ bị cleanup sau 20 phút nếu không reconnect
```

### D. Web UI logout (explicit)

**Location:** `client_api.py` - logout endpoint (dòng 702-744)

```python
@app.route('/api/client/logout', methods=['POST'])
def logout():
    # Lấy username từ JWT token
    username = payload.get('username')
    
    with clients_lock:
        if username in client_instances:
            # Đóng client và UNREGISTER
            client.close()
            
            # Xóa khỏi active instances
            del client_instances[username]
```

---

## 6. Client có dùng thread không? Có lock thread không? Lock đến khi nào? Tại sao dùng lock?

### A. Threads được sử dụng

**Location:** `client.py`

#### 1. Heartbeat Thread
**Dòng 633-637:**
```python
threading.Thread(target=self.heartbeat_thread, daemon=True).start()
```
- **Mục đích:** Gửi heartbeat định kỳ đến server
- **Daemon:** True (tự động tắt khi main thread tắt)

#### 2. Peer Server Thread
**Dòng 268-280:**
```python
class PeerServer(threading.Thread):
    def run(self):
        while self.client_ref.running:
            conn, addr = self.sock.accept()
            # Spawn handler thread cho mỗi peer connection
            threading.Thread(
                target=self.handle_peer, 
                args=(conn, addr), 
                daemon=True
            ).start()
```
- **Mục đích:** Lắng nghe P2P connections từ clients khác
- **Spawn thêm threads:** Mỗi peer connection = 1 thread riêng

#### 3. Download Thread
**Dòng 684:**
```python
threading.Thread(
    target=self.download_from_peer, 
    args=(...), 
    daemon=True
).start()
```
- **Mục đích:** Download file từ peer (không block main thread)

#### 4. Background Publish Thread (trong API)
**Location:** `client_api.py` - dòng 450
```python
def publish_task():
    client.publish(dest_path, fname, overwrite=True, interactive=False)

threading.Thread(target=publish_task, daemon=True).start()
```

### B. Locks được sử dụng

#### 1. Central Lock (quan trọng nhất!)
**Location:** `client.py` - khởi tạo dòng 420

```python
self.central_lock = threading.Lock()
self.central = socket.socket(...)  # Kết nối TCP đến server
```

**Sử dụng ở:**

##### A. REGISTER (dòng 457-467)
```python
with self.central_lock:
    send_json(self.central, {
        "action": "REGISTER",
        "data": {...}
    })
    resp = recv_json(self.central)
```

##### B. PUBLISH (dòng 582-592)
```python
with self.central_lock:
    send_json(self.central, {
        "action": "PUBLISH",
        "data": {...}
    })
    r = recv_json(self.central)
```

##### C. REQUEST (dòng 665-667)
```python
with self.central_lock:
    send_json(self.central, {"action": "REQUEST", ...})
    r = recv_json(self.central)
```

##### D. HEARTBEAT (dòng 625-628)
```python
with self.central_lock:
    send_json(self.central, {"action": "PING", ...})
    recv_json(self.central)
```

#### 2. Publish Lock
**Location:** `client.py` - dòng 470
```python
self.pub_lock = threading.Lock()
```
**Chưa được sử dụng trong code hiện tại** (có thể dùng sau)

#### 3. Registry Lock (Server-side)
**Location:** `server.py` - dòng 18
```python
registry_lock = threading.Lock()
registry = {}
```

**Sử dụng ở:**
```python
# Khi update registry
with registry_lock:
    registry[hostname] = {...}

# Khi đọc registry
with registry_lock:
    snapshot = {h: {...} for h, info in registry.items()}
```

#### 4. Clients Lock (API-side)
**Location:** `client_api.py` - dòng 25
```python
clients_lock = threading.Lock()
client_instances = {}
```

**Sử dụng khi:**
```python
# Tạo/xóa client instances
with clients_lock:
    client_instances[username] = Client(...)
    del client_instances[username]
```

### C. Lock đến khi nào?

**Context Manager (`with` statement) tự động release:**

```python
with self.central_lock:
    send_json(...)      # Lock acquired ở đây
    recv_json(...)      
# Lock released TỰ ĐỘNG khi ra khỏi block
```

**Equivalent code:**
```python
self.central_lock.acquire()
try:
    send_json(...)
    recv_json(...)
finally:
    self.central_lock.release()  # LUÔN release, kể cả exception
```

### D. Tại sao dùng lock?

#### 1. Central Lock - BẢO VỆ SOCKET TCP

**Vấn đề nếu KHÔNG có lock:**
```python
# Thread 1 (Heartbeat):
send_json(self.central, {"action": "PING"})    # Gửi "PING\n"
                                    ❌ Thread 2 chen vào!
recv_json(self.central)                        # Nhận "ACK\n" (từ PUBLISH?)

# Thread 2 (Publish):
send_json(self.central, {"action": "PUBLISH"}) # Gửi "PUBLISH\n"
recv_json(self.central)                        # Nhận "OK\n" (từ PING?)
```

**Kết quả:** Response bị lẫn lộn giữa các threads! 🔥

**Với lock:**
```python
# Thread 1 acquire lock trước
with self.central_lock:
    send_json(...)   # "PING\n"
    recv_json(...)   # "OK\n" (đúng!)
# Release lock

# Thread 2 đợi lock
with self.central_lock:  # Block until Thread 1 releases
    send_json(...)   # "PUBLISH\n"
    recv_json(...)   # "ACK\n" (đúng!)
```

#### 2. Registry Lock - BẢO VỆ SHARED DATA

**Race condition ví dụ:**
```python
# Thread A (PUBLISH):
if hostname in registry:        # ✓ Có tồn tại
    registry[hostname]["files"][fname] = ...  
                            ❌ Thread B xóa ở đây!
    
# Thread B (CLEANUP):
if timeout:
    registry.pop(hostname)  # XÓA client
```

**Kết quả:** KeyError! Dictionary bị modify đồng thời

**Với lock:**
```python
# Thread A
with registry_lock:
    if hostname in registry:
        registry[hostname]["files"][fname] = ...
# Atomic operation - không bị interrupt

# Thread B đợi
with registry_lock:
    registry.pop(hostname)
```

#### 3. Clients Lock - BẢO VỆ CLIENT INSTANCES

**Race condition:**
```python
# Thread 1 (logout):
if username in client_instances:
    client = client_instances[username]
    client.close()
    del client_instances[username]  ❌ Thread 2 đang dùng!

# Thread 2 (get_client):
client = client_instances[username]  # KeyError!
```

---

## Summary - Các câu trả lời ngắn gọn

| Câu hỏi | Trả lời |
|---------|---------|
| **Server lưu gì?** | Metadata (IP, port, file info, timestamps) - KHÔNG lưu file content |
| **2 client connect như nào?** | Client A → Server (REQUEST) → Server trả IP/port B → Client A kết nối TRỰC TIẾP đến Client B qua TCP |
| **Fetch gửi gì?** | 1) A→Server: `REQUEST {fname}` <br> 2) Server→A: `{hosts: [{ip, port}]}` <br> 3) A→B: `GET fname\n` <br> 4) B→A: `LENGTH size\n` + binary |
| **Ping dùng gì?** | TCP (tái sử dụng kết nối), CLIENT ping SERVER (không ngược lại), gián đoạn 30-300s (adaptive) |
| **Tại sao chọn TCP?** | Tái sử dụng socket, NAT-friendly, scalable (server không ping 100k clients) |
| **Server biết interrupt?** | 1) Graceful: Client gửi UNREGISTER <br> 2) Crash: Cleanup thread xóa sau 20 phút không heartbeat |
| **Code ở đâu?** | Heartbeat: `client.py:610-637` <br> Cleanup: `server.py:165-173` |
| **Client dùng thread?** | ✓ Heartbeat, ✓ Peer server, ✓ Download, ✓ Background publish |
| **Có lock không?** | ✓ central_lock (bảo vệ TCP socket), ✓ registry_lock (server), ✓ clients_lock (API) |
| **Lock đến khi nào?** | Tự động release khi thoát `with` block (context manager) |
| **Tại sao lock?** | Tránh race condition khi nhiều threads cùng access socket/shared data |
| **Version control?** | ❌ KHÔNG có auto-versioning. Publish cùng tên = overwrite metadata. Workaround: Thêm version vào filename |
| **Fetch → Server biết?** | ❌ KHÔNG tự động. Fetch = local only. Phải PUBLISH thủ công để server biết |
| **Handle thread?** | Daemon threads (auto-terminate), Control flags (`running`), Locks (socket/registry), Timeout (graceful shutdown) |
| **TCP theory?** | Connection-oriented, 3-way handshake, reliable/ordered delivery, `send_json()` dùng newline delimiter, P2P dùng binary chunks |
| **Server handle bao nhiêu clients?** | Lý thuyết: HÀNG TRIỆU (không bị giới hạn port). Server chỉ dùng 1 port. Thực tế: 10k-100k tuỳ RAM/CPU |
| **Client cần port riêng?** | ✅ YES! Mỗi client cần 1 port RIÊNG cho Peer Server (lắng nghe P2P). Đây là giới hạn thực tế! |
| **Max clients trên 1 máy?** | **Default: 1,001 clients** (ports 6000-7000). Extended: ~59,001 (6000-65535). Absolute max: ~64k |
| **100k test thực sự 100k?** | ❌ NO! Peak concurrent = 499. Test chạy 100 waves × 1000 clients. Ports được REUSE! |
| **Solution cho 100k concurrent?** | 1) Multiple machines (1000 clients/máy) <br> 2) Docker containers (isolated ports) <br> 3) Dynamic ports `bind(0)` |
| **Dung lượng file giới hạn?** | ❌ KHÔNG có hard limit. Giới hạn: disk, timeout 30s, network. Chunked streaming → RAM OK |
| **File lớn nhất?** | Test: 1 GB. Code optimize cho > 100 MB (1MB chunks). Lý thuyết: Unlimited (chunked transfer) |
| **Tốc độ transfer?** | Test: 76.12 MB/s (local, không qua network). Thực tế: 1-100 MB/s tuỳ LAN/WAN |

---

## Diagrams

### Architecture Overview
```
┌─────────────┐         TCP          ┌─────────────┐
│  Client A   │────────────────────→│   Server    │
│ (hostname1) │←────────────────────│  (metadata) │
└─────────────┘    Heartbeat/       └─────────────┘
       │           Metadata               ↑
       │                                  │ Heartbeat
       │ P2P (Direct TCP)                 │ Metadata
       │                                  │
       ↓                              ┌─────────────┐
┌─────────────┐                       │  Client B   │
│  Client B   │←──────────────────────│ (hostname2) │
│   File      │    File Transfer      └─────────────┘
└─────────────┘      (No Server)
```

### Thread Architecture
```
Client Process
├── Main Thread (CLI/API)
├── Heartbeat Thread (ping server every 30-300s)
│   └── Uses: central_lock
├── Peer Server Thread
│   └── Spawns: Handler Thread per connection
│       └── Reads files and sends to peers
└── Download Threads (one per fetch)
    └── Connects to peer, downloads file
```

---

## 7. Publish nhiều file thì kiểm soát nhiều phiên bản như thế nào?

### A. Cơ chế Version Control

**Không có version control tự động** - Hệ thống này **KHÔNG** quản lý nhiều phiên bản cùng lúc!

**Location:** `client.py` - FileMetadata structure (dòng 127-172)

```python
class FileMetadata:
    def __init__(self, name, size, modified, path=None, ...):
        self.name = name              # ← Unique key (filename)
        self.size = size
        self.modified = modified      # ← Timestamp từ filesystem
        self.published_at = published_at  # ← Timestamp khi publish
```

**Metadata được lưu:**
- Chỉ có **1 version** của mỗi filename
- `modified`: Thời gian file được sửa đổi cuối (từ OS)
- `published_at`: Thời gian publish lên network
- Không có version number, không có history

### B. Publish file trùng tên (Overwrite)

**Location:** `client.py` - hàm `publish()` (dòng 539-639)

```python
def publish(self, local_path, fname=None, overwrite=True, interactive=True):
    # Kiểm tra file đã publish chưa
    if fname in self.published_files and not overwrite:
        return False, f"File '{fname}' is already published"
    
    # Overwrite = True → Replace metadata cũ
    metadata = FileMetadata(
        name=fname,
        size=file_size,
        modified=file_modified,  # ← NEW timestamp
        published_at=time.time()  # ← NEW publish time
    )
    
    # CẬP NHẬT (không tạo version mới)
    self.local_files[fname] = metadata
    self.published_files[fname] = metadata
    
    # Notify server với metadata mới
    send_json(self.central, {
        "action": "PUBLISH",
        "data": {
            "hostname": self.hostname,
            "fname": fname,
            "size": file_size,        # ← NEW
            "modified": file_modified  # ← NEW
        }
    })
```

**Server-side update:**
**Location:** `server.py` - xử lý PUBLISH (dòng 81-102)

```python
elif action == 'PUBLISH':
    with registry_lock:
        # OVERWRITE metadata cũ
        registry[hostname]["files"][fname] = {
            "size": file_size,          # ← Thay thế size cũ
            "modified": file_modified,  # ← Thay thế timestamp cũ
            "published_at": time.time(),
            "is_published": True
        }
```

### C. Duplicate Detection (Warning Only)

**Location:** `client.py` - hàm `_check_duplicate_on_network()` (dòng 780-834)

```python
def _check_duplicate_on_network(self, fname, size, modified):
    """So sánh metadata để phát hiện trùng lặp"""
    for hostname, info in registry.items():
        if fname in info['files']:
            finfo = info['files'][fname]
            other_size = finfo.get('size', 0)
            other_modified = finfo.get('modified', 0)
            
            # So sánh size + modified time
            size_match = (self.size == other_size)
            time_match = abs(self.modified - other_modified) < 2
            
            if size_match and time_match:
                # EXACT duplicate (cùng file)
                exact_matches.append({...})
            elif size_match or time_match:
                # PARTIAL duplicate (khác version)
                partial_matches.append({...})
```

**Hành động khi phát hiện duplicate:**
```python
# client.py - dòng 656-678
if duplicate_info['has_exact_duplicate']:
    print(f"[WARNING] File '{fname}' already exists on network!")
    print(f"   Available from: {', '.join(hosts)}")
    
    if interactive:
        choice = input("Do you still want to publish? (y/n): ")
        if choice != 'y':
            return False, "Publish cancelled by user"
    else:
        # Non-interactive: Publish anyway (warning only)
        print("[WARNING] Exact duplicate exists. Publishing anyway.")
```

### D. Kịch bản thực tế

#### Scenario 1: Publish file mới
```
1. User: publish report_v1.pdf
   → Server: {report_v1.pdf: {size: 1MB, modified: T1}}

2. User: publish report_v2.pdf
   → Server: {report_v1.pdf: {...}, report_v2.pdf: {size: 1.2MB, modified: T2}}
   ✓ 2 files khác tên → Cả 2 tồn tại
```

#### Scenario 2: Update file (cùng tên)
```
1. User: publish report.pdf (version 1)
   → Server: {report.pdf: {size: 1MB, modified: T1, published_at: T1}}

2. User: chỉnh sửa report.pdf → publish lại
   → Server: {report.pdf: {size: 1.2MB, modified: T2, published_at: T3}}
   ✓ OVERWRITE metadata cũ
   ❌ Version 1 bị mất (không có history)
```

#### Scenario 3: Multiple clients cùng tên file
```
Client A: publish data.txt (100 KB, modified: Nov 1)
Client B: publish data.txt (200 KB, modified: Nov 10)

Registry:
{
  "clientA": {"files": {"data.txt": {size: 100KB, modified: Nov 1}}},
  "clientB": {"files": {"data.txt": {size: 200KB, modified: Nov 10}}}
}

→ Clients REQUEST data.txt:
  Server returns: [
    {hostname: "clientA", size: 100KB},
    {hostname: "clientB", size: 200KB}
  ]
→ User chọn download từ client nào (UI hiển thị cả 2)
```

### E. Workaround cho Version Control

**Nếu muốn giữ nhiều versions:**
```python
# Option 1: Thêm version vào filename
publish("report.pdf", "report_v1.pdf")
publish("report.pdf", "report_v2.pdf")
publish("report.pdf", "report_v3.pdf")

# Option 2: Thêm timestamp
from datetime import datetime
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
publish("report.pdf", f"report_{timestamp}.pdf")
```

### F. Limitations

❌ **Không có:**
- Version history
- Rollback to previous version
- Diff giữa versions
- Automatic versioning

✓ **Có:**
- Metadata comparison (size + modified time)
- Duplicate warnings
- Manual versioning (via filenames)

---

## 8. Nếu client fetch file về, làm sao server biết client có thêm file mới?

### A. TL;DR: Server KHÔNG tự động biết!

**Client fetch về = Local file ONLY, không auto-publish**

**Location:** `client.py` - hàm `download_from_peer()` (dòng 1122-1135)

```python
def download_from_peer(...):
    # ... download file ...
    
    # Lưu file vào repo
    outpath = os.path.join(self.repo_dir, fname)
    
    # Update metadata - CHỈ local, KHÔNG publish
    metadata = FileMetadata(
        name=fname,
        size=meta_dict['size'],
        modified=meta_dict['modified'],
        path=outpath,
        is_published=False,  # ← ĐÂY: Không publish!
        added_at=time.time()
    )
    self.local_files[fname] = metadata
    
    print("[INFO] File saved as local only.")
    print("[INFO] Use 'publish' command to share with network.")
```

### B. Flow chi tiết

#### Step 1: Client fetch file
```python
# Client A fetches file từ Client B
client_a.request("data.pdf")

# Download hoàn tất
# → File saved to: repo_alice/data.pdf
# → Metadata: local_files["data.pdf"] = {is_published: False}
# → Server KHÔNG nhận được thông báo gì!
```

#### Step 2: Server's view (không thay đổi)
```python
# Server registry TRƯỚC khi fetch:
registry = {
  "client_a": {"files": {}},  # Empty
  "client_b": {"files": {"data.pdf": {...}}}
}

# Server registry SAU khi fetch:
registry = {
  "client_a": {"files": {}},  # ← VẪN empty!
  "client_b": {"files": {"data.pdf": {...}}}
}
# → Server không biết client_a đã có file!
```

#### Step 3: Client phải PUBLISH thủ công
```python
# Client A muốn share file đã fetch:
client_a.publish("repo_alice/data.pdf", "data.pdf")

# → Gửi PUBLISH action đến server
send_json(self.central, {
    "action": "PUBLISH",
    "data": {"hostname": "client_a", "fname": "data.pdf", ...}
})

# → Server CẬP NHẬT registry:
registry["client_a"]["files"]["data.pdf"] = {
    "size": 1234,
    "modified": ...,
    "is_published": True
}
```

### C. Tại sao không auto-publish sau fetch?

**Design decision: Tách biệt Local vs Network**

**1. Privacy & Control**
```python
# User có thể fetch file nhạy cảm
fetch("confidential_report.pdf")
# → Chỉ lưu local
# → Không tự động share lại cho network
# → User kiểm soát được việc publish
```

**2. Bandwidth Management**
```python
# User fetch 10 files lớn
fetch("movie1.mkv")  # 4GB
fetch("movie2.mkv")  # 4GB
...
# → Nếu auto-publish: Client trở thành peer cho 10 files
# → Upload bandwidth bị chiếm dụng
# → User KHÔNG mong muốn điều này
```

**3. Storage Separation**
```python
# 3-tier model:
self.local_files = {}      # Tất cả files đang track
self.published_files = {}  # Subset: Files share với network
self.network_files = {}    # Files từ clients khác

# Fetch → Chỉ thêm vào local_files
# Publish → Mới thêm vào published_files + notify server
```

### D. Auto-publish option (trong API)

**Location:** `client_api.py` - upload endpoint (dòng 579-587)

```python
@app.route('/api/client/upload', methods=['POST'])
def upload_file():
    # ... upload file ...
    
    # Optional: Auto publish sau khi upload
    auto_publish = request.form.get('auto_publish', 'false').lower() == 'true'
    
    if auto_publish:
        def publish_task():
            client.publish(dest_path, fname, overwrite=True, interactive=False)
        threading.Thread(target=publish_task, daemon=True).start()
        message = f'File uploaded and publishing...'
    else:
        message = f'File uploaded successfully (local only)'
```

**Lưu ý:** Chỉ có với **upload** (user tải file lên), KHÔNG có với **fetch** (download từ peer)

---

## 9. Cách handle thread trong hệ thống

### A. Thread Types

**Location:** `client.py` và `server.py`

#### 1. Daemon Threads
```python
# Tất cả threads đều dùng daemon=True
threading.Thread(target=func, daemon=True).start()
```

**Daemon thread characteristics:**
- Tự động terminate khi main thread exits
- Không block program shutdown
- Không cần explicit `.join()`

**Sử dụng ở:**
- Heartbeat thread (`client.py:633`)
- Peer server thread (`client.py:214`)
- Download threads (`client.py:684`)
- Server cleanup thread (`server.py:237`)
- Connection handler threads (`server.py:257`)

### B. Thread Lifecycle Management

#### 1. Starting threads
**Pattern chung:**
```python
# Create and start in one line
threading.Thread(target=func, args=(...), daemon=True).start()

# Hoặc với class-based thread:
class PeerServer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
    
    def run(self):
        # Thread logic
        pass

peer = PeerServer()
peer.start()  # Gọi run() trong thread riêng
```

#### 2. Stopping threads (Graceful Shutdown)

**Control flag pattern:**
**Location:** `client.py` (dòng 220-234, 391-392)

```python
class PeerServer(threading.Thread):
    def run(self):
        # Loop kiểm tra running flag
        while self.client_ref.running:  # ← Control flag
            try:
                conn, addr = self.sock.accept()
                # Handle connection...
            except socket.timeout:
                continue  # Timeout allows checking flag
        
        print("[PEER] Server stopped")

# Stopping:
client.running = False  # Set flag
peer_server.stop()      # Close socket
# → Loop exits, thread terminates
```

**Heartbeat thread:**
```python
def heartbeat_thread(self):
    while self.running:  # ← Check flag
        time.sleep(interval)
        
        if not self.running:  # ← Double check
            break
        
        # Send heartbeat...
```

#### 3. Thread cleanup sequence

**Location:** `client.py` - `close()` method (dòng 885-911)

```python
def close(self):
    # Step 1: Stop all threads
    self.running = False  # ← All loops check this
    
    # Step 2: Stop peer server
    if self.peer_server:
        self.peer_server.stop()  # Close listening socket
    
    # Step 3: Unregister from server
    self.unregister()
    
    # Step 4: Close connections
    self.central.close()
    
    # Threads tự terminate (daemon=True)
```

### C. Thread Synchronization

#### 1. Lock types used

**Mutex Locks (threading.Lock):**
```python
# Client-side
self.central_lock = threading.Lock()  # Protect TCP socket
self.pub_lock = threading.Lock()      # (Reserved for future)

# Server-side
registry_lock = threading.Lock()      # Protect shared registry dict

# API-side
clients_lock = threading.Lock()       # Protect client instances dict
```

#### 2. Lock usage patterns

**Context Manager (Recommended):**
```python
with self.central_lock:
    send_json(...)  # Critical section
    recv_json(...)
# Auto-release on exit (even if exception)
```

**Critical sections protected:**

**A. Socket operations (client.py):**
```python
# Multiple threads use same socket → Need lock
with self.central_lock:
    send_json(self.central, {"action": "..."})
    response = recv_json(self.central)
```

**B. Registry updates (server.py):**
```python
# Multiple handlers modify registry → Need lock
with registry_lock:
    registry[hostname]["files"][fname] = {...}
```

**C. Client instances (client_api.py):**
```python
# Multiple API requests access instances → Need lock
with clients_lock:
    client = client_instances[username]
```

#### 3. Timeout pattern (Non-blocking accept)

**Location:** `client.py` - PeerServer (dòng 217-219)

```python
self.sock.settimeout(1.0)  # 1 second timeout

def run(self):
    while self.client_ref.running:
        try:
            conn, addr = self.sock.accept()  # Blocks max 1s
            # Spawn handler...
        except socket.timeout:
            continue  # Timeout → Check running flag → Loop
```

**Why timeout?**
- `accept()` normally blocks forever
- With timeout: Check `running` flag every 1s
- Allows graceful shutdown without forceful termination

### D. Thread Communication

#### 1. Shared State
```python
# Client instance is shared reference
class PeerServer(threading.Thread):
    def __init__(self, listen_port, client_ref):
        self.client_ref = client_ref  # ← Shared reference
    
    def handle_peer(self, conn, addr):
        # Access shared state
        if fname not in self.client_ref.published_files:
            # ...
```

#### 2. Flags for coordination
```python
# Adaptive heartbeat state
if self.adaptive_heartbeat:
    self.adaptive_heartbeat.mark_activity("publish")
    self.adaptive_heartbeat.start_file_transfer()  # Change state
    # ... transfer ...
    self.adaptive_heartbeat.end_file_transfer()    # Restore state
```


### E. Thread Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                 Client Process                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Main Thread (CLI/API Handler)                  │
│      │                                          │
│      ├─→ Heartbeat Thread (daemon)              │
│      │   └─ while running: ping server          │
│      │                                          │
│      ├─→ PeerServer Thread (daemon)             │
│      │   ├─ while running: accept()             │
│      │   │                                      │
│      │   ├─→ Handler Thread 1 (daemon)          │
│      │   │   └─ Serve file to Peer A            │
│      │   │                                      │
│      │   ├─→ Handler Thread 2 (daemon)          │
│      │   │   └─ Serve file to Peer B            │
│      │   │                                      │
│      │   └─→ Handler Thread N...                │
│      │                                          │
│      └─→ Download Thread (daemon)               │
│          └─ Fetch file from peer                │
│                                                 │
│  Shared Resources (protected by locks):         │
│  • self.central (TCP socket) → central_lock     │
│  • self.published_files (dict) → implicit       │
│  • self.running (bool flag) → atomic            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 10. Lý thuyết TCP và ứng dụng trong hệ thống

### A. TCP Basics

**TCP (Transmission Control Protocol)**
- **Layer:** Transport Layer (Layer 4 - OSI Model)
- **Type:** Connection-oriented, reliable, ordered
- **Port range:** 0-65535 (hệ thống dùng 6000-9000)

**Key Features:**
1. **3-way handshake** (thiết lập kết nối)
2. **Reliable delivery** (ACK, retransmission)
3. **Flow control** (sliding window)
4. **Congestion control** (slow start, congestion avoidance)
5. **Ordered delivery** (sequence numbers)
6. **Error checking** (checksums)

### B. TCP trong code (Python socket)

#### 1. Socket creation
**Location:** `client.py` (dòng 421-423), `server.py` (dòng 233)

```python
# Create TCP socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#                 ↑              ↑
#                 IPv4           TCP
```

**Parameters:**
- `AF_INET`: Address Family IPv4
- `SOCK_STREAM`: TCP (vs `SOCK_DGRAM` for UDP)

#### 2. Server-side TCP

**Location:** `server.py` (dòng 233-257)

```python
# 1. Create socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Set socket options
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#            ↑                  ↑
#            Socket level       Allow port reuse (important!)

# 3. Bind to address
s.bind((HOST, PORT))  # HOST='', PORT=9000
#      ↑
#      '' = bind to all interfaces (0.0.0.0)

# 4. Listen for connections
s.listen(10)  # Backlog = 10 pending connections
#        ↑
#        Max queued connections before rejection

# 5. Accept connections (blocking)
conn, addr = s.accept()
#     ↑      ↑
#     Socket Address (ip, port) of client

# 6. Handle connection in separate thread
threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()
```

**3-way handshake happens in `accept()`:**
```
Client                        Server
  |                             |
  |-------SYN------→            | (client initiates)
  |                             |
  |←------SYN-ACK---------------| (server accepts)
  |                             |
  |-------ACK------------------→| (connection established)
  |                             |
  | ← accept() returns here     |
```

#### 3. Client-side TCP

**A. Connect to server (persistent):**
**Location:** `client.py` (dòng 421-427)

```python
# 1. Create socket
self.central = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Connect to server
self.central.connect((self.server_host, self.server_port))
#            ↑
#            Blocking call - waits for 3-way handshake

# 3. Connection persists - reused for all commands
send_json(self.central, {"action": "REGISTER", ...})
send_json(self.central, {"action": "PUBLISH", ...})
send_json(self.central, {"action": "PING", ...})
# ... same connection ...
```

**B. Connect to peer (temporary):**
**Location:** `client.py` (dòng 703-706)

```python
# 1. Create new socket for each download
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 2. Set timeout (important for large files)
s.settimeout(30)  # 30 seconds

# 3. Connect to peer
s.connect((peer_ip, peer_port))

# 4. Send request
s.sendall(f"GET {fname}\n".encode())

# 5. Receive data
data = s.recv(4096)

# 6. Close when done
s.close()
```

### C. TCP Send/Receive Patterns

#### 1. JSON-based protocol (Server ↔ Client)

**Location:** `client.py` và `server.py` (dòng 38-52)

```python
def send_json(conn, obj):
    """Send JSON object over TCP"""
    data = json.dumps(obj) + '\n'  # ← Newline delimiter
    conn.sendall(data.encode())
    #    ↑
    #    Ensures ALL data is sent (may loop internally)

def recv_json(conn):
    """Receive JSON object from TCP"""
    buf = b''
    while True:
        chunk = conn.recv(4096)  # ← Read up to 4KB
        if not chunk:
            return None  # Connection closed
        buf += chunk
        
        # Check for complete message (newline-delimited)
        if b'\n' in buf:
            line, rest = buf.split(b'\n', 1)
            return json.loads(line.decode())
```

**Why newline delimiter?**
```
TCP is stream-based, no message boundaries!

Without delimiter:
Send: {"action":"PING"}{"action":"PUBLISH"}
Recv: {"action":"PI  ← Incomplete! Need to buffer

With newline:
Send: {"action":"PING"}\n{"action":"PUBLISH"}\n
Recv: Read until \n → Complete message
```

#### 2. Binary protocol (P2P file transfer)

**Location:** `client.py` - PeerServer (dòng 316-341)

```python
# Send header (text)
conn.sendall(f"LENGTH {size}\n".encode())

# Send binary data (chunked)
with open(fpath, 'rb') as f:
    while True:
        chunk = f.read(256*1024)  # 256KB chunks
        if not chunk:
            break
        conn.sendall(chunk)  # ← Send raw bytes
#            ↑
#            May block if send buffer full
```

**Receive side:**
```python
# Read header
buf = b''
while b'\n' not in buf:
    chunk = conn.recv(4096)
    buf += chunk
header = buf.split(b'\n')[0].decode()  # "LENGTH 1234567"

# Read binary data
total_size = int(header.split()[1])
received = 0
with open(outpath, 'wb') as f:
    while received < total_size:
        chunk = conn.recv(min(256*1024, total_size - received))
        f.write(chunk)
        received += len(chunk)
```

### D. TCP Socket Options

#### 1. SO_REUSEADDR
**Location:** `server.py` (dòng 234), `client.py` (dòng 211)

```python
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
```

**Purpose:**
- Allow immediate port reuse after program restart
- Without it: "Address already in use" error for ~60s (TIME_WAIT state)

**Why needed?**
```
TCP connection termination:
1. Active close: FIN → FIN-ACK → ACK
2. Socket enters TIME_WAIT state (2*MSL ≈ 60s)
3. Port is blocked during TIME_WAIT
4. SO_REUSEADDR: Skip TIME_WAIT, bind immediately
```

#### 2. Socket Timeout
**Location:** `client.py` (dòng 217, 704)

```python
s.settimeout(1.0)  # Peer server accept
s.settimeout(30)   # P2P download
```

**Behavior:**
```python
# Without timeout:
conn, addr = s.accept()  # Blocks FOREVER

# With timeout:
try:
    conn, addr = s.accept()  # Blocks max 1s
except socket.timeout:
    # Check running flag, continue loop
    pass
```

### E. TCP Connection States

**Tracked in system:**

#### 1. LISTEN (Server)
```python
s.listen(10)  # LISTEN state
# → Waiting for incoming SYN packets
```

#### 2. ESTABLISHED (Both)
```python
# After 3-way handshake completes
conn, addr = s.accept()  # Server
conn.connect((ip, port))  # Client
# → Connection is ESTABLISHED
```

#### 3. CLOSE_WAIT / FIN_WAIT
```python
conn.close()
# → Initiates 4-way termination
# → FIN → FIN-ACK → ACK → CLOSED
```

**Detect connection closed:**
```python
chunk = conn.recv(4096)
if not chunk:  # ← Empty bytes = FIN received
    print("Connection closed by peer")
    break
```

### F. TCP Performance Considerations

#### 1. Nagle's Algorithm
```python
# TCP combines small packets to reduce overhead
# May add latency for interactive apps

# Disable if needed:
s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
# → Send immediately, no buffering
```

#### 2. Send/Receive Buffer Sizes
```python
# Default buffers (OS-dependent):
# Linux: ~87KB send, ~87KB recv

# Increase for large file transfers:
s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send
s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB recv
```

#### 3. Chunking Strategy
**Location:** `client.py` (dòng 330, 797)

```python
# File transfer chunk size
if size > 100*1024*1024:  # > 100MB
    chunk_size = 1024*1024      # 1MB chunks
else:
    chunk_size = 256*1024        # 256KB chunks

# Why larger chunks for big files?
# → Fewer system calls
# → Better throughput
# → Less CPU overhead
```

### G. TCP Error Handling

**Common errors:**

```python
try:
    conn.connect((ip, port))
except socket.timeout:
    # Connection timeout (no response)
    print("Timeout connecting to peer")
except ConnectionRefusedError:
    # Port not listening
    print("Peer not accepting connections")
except socket.error as e:
    # Network unreachable, etc.
    print(f"Socket error: {e}")
```

### H. TCP vs UDP Comparison (Why TCP?)

| Feature | TCP | UDP | Choice |
|---------|-----|-----|--------|
| **Reliability** | ✓ Guaranteed delivery | ✗ May lose packets | TCP (need reliable metadata) |
| **Ordering** | ✓ In-order | ✗ Out-of-order | TCP (JSON protocol needs order) |
| **Connection** | ✓ Stateful | ✗ Stateless | TCP (persistent to server) |
| **Overhead** | Higher (headers, ACKs) | Lower | TCP (reliability > speed) |
| **Use case** | Metadata, file transfer | Video streaming, DNS | TCP for file sharing |

**Why not UDP for heartbeat?**
```python
# UDP would need:
# 1. Separate socket (extra resource)
# 2. Manual reliability (detect lost packets)
# 3. No benefit (1 heartbeat/60s is not high-frequency)

# TCP advantages:
# 1. Reuse existing connection
# 2. Built-in reliability
# 3. Simpler code
```

---

## 11. Giới hạn số lượng clients và hiệu suất thực tế

### A. Server có thể handle bao nhiêu clients đồng thời?

**Giới hạn về số port:**

❌ **MỘT SAI LẦM PHỔ BIẾN:** Nghĩ rằng server bị giới hạn bởi số port (65535)

✅ **SỰ THẬT:** Server có thể handle **HÀNG TRIỆU** connections với CHỈ 1 PORT!

**Giải thích:**

```python
# Server chỉ cần 1 port để listen
s.bind(('', 9000))  # Chỉ dùng port 9000
s.listen(10)        # Backlog = 10 pending connections

# Mỗi client connection tạo một SOCKET riêng (không phải port riêng!)
while True:
    conn, addr = s.accept()  # conn = new socket, addr = (client_ip, client_port)
    # ↑ Socket descriptor, KHÔNG phải port mới
```

**TCP Connection Identity (5-tuple):**
```
Connection = (src_ip, src_port, dst_ip, dst_port, protocol)

Example với 3 clients:
Client 1: (192.168.1.10, 50123, server_ip, 9000, TCP)
Client 2: (192.168.1.11, 50124, server_ip, 9000, TCP)
Client 3: (192.168.1.10, 50125, server_ip, 9000, TCP)  ← Cùng IP nhưng khác port

→ Mỗi connection là UNIQUE nhờ (src_ip, src_port)
→ Server chỉ cần 1 port (9000)
```

**Giới hạn thực tế:**

#### 1. File Descriptors (OS Limit)
```bash
# Linux default: 1024 file descriptors per process
ulimit -n
# → Có thể tăng lên hàng triệu

# Increase limit:
ulimit -n 1048576  # 1 million
```

**Code không có hard limit:**
```python
# server.py - dòng 237
s.listen(10)  # ← Backlog (chờ accept), KHÔNG phải max connections
#        ↑
#        Số connections đang chờ trong queue
#        KHÔNG phải tổng số connections server có thể handle
```

#### 2. Memory (RAM)
```python
# Mỗi connection ~ 4-8 KB RAM (socket buffer)
# Mỗi client trong registry ~ 1-2 KB

# Ví dụ với 100,000 clients:
# - Sockets: 100k × 6 KB = 600 MB
# - Registry: 100k × 1.5 KB = 150 MB
# - Total: ~750 MB RAM
```

**From test results:**
```
100,000 clients:
- Memory: 1937.81 MB avg, 2017.39 MB peak
- CPU: 8.61% avg, 20.90% peak
→ System chạy THOẢI MÁI!
```

#### 3. CPU (Threading overhead)
```python
# server.py - dòng 257
threading.Thread(target=handle_conn, args=(conn, addr), daemon=True).start()
#                ↑
#                Mỗi connection = 1 thread

# Python: GIL (Global Interpreter Lock)
# → Threads không parallel thực sự
# → Có thể handle 10k-100k threads (I/O bound)
```

**From test results:**
```
100,000 clients: CPU 8.61% avg
10,000 clients:  CPU 16.39% avg
1,000 clients:   CPU 16.18% avg

→ 100k clients dùng ÍT CPU HƠN 10k clients?!
   (Sẽ giải thích ở phần B)
```

### B. Tại sao test 100k clients tốt hơn 10k clients?

**PHÁT HIỆN QUAN TRỌNG từ results:**

```
Registry Operations - Average Latency:

REGISTER:
- 1k clients:    80.52 ms
- 10k clients:   61.31 ms
- 100k clients:  15.78 ms  ← TỐT NHẤT!

PUBLISH:
- 1k clients:    65.29 ms
- 10k clients:   64.90 ms
- 100k clients:  16.41 ms  ← TỐT NHẤT!

LIST:
- 1k clients:    502.71 ms
- 10k clients:   800.16 ms
- 100k clients:  55.77 ms  ← TỐT NHẤT!
```

**❌ KẾT QUẢ NÀY KHÔNG HỢP LÝ VỀ MẶT LÝ THUYẾT!**

**Lý do: Test KHÔNG thực sự test 100k concurrent connections!**

### C. Phân tích cách test hoạt động

**Location:** `scalability_test.py` (dòng 491-560)

```python
def run_scalability_test(num_clients, test_files, server_host, server_port,
                         max_concurrent=1000, operations_per_client=10):
    """
    max_concurrent: Maximum concurrent connections
                                          ↑
                    GIỚI HẠN CHỈ 1000 CONCURRENT!
    """
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        #                                   ↑
        #                     CHỈ 1000 threads cùng lúc!
        
        for client_id in range(num_clients):  # 100,000 iterations
            future = executor.submit(run_client_simulation, ...)
            #                  ↑
            #        Nếu đã có 1000 threads → WAIT cho thread hoàn thành
```

**Timeline thực tế:**

```
Test "100k clients":
├─ Wave 1: 1000 clients (concurrent)
│  └─ Mỗi client: 10 operations × 50ms = 500ms
│     → Hoàn thành sau ~500ms
│
├─ Wave 2: 1000 clients (concurrent)
│  └─ Mỗi client: 10 operations × 50ms = 500ms
│     → Hoàn thành sau ~500ms
│
├─ ... (98 waves more)
│
└─ Wave 100: 1000 clients (concurrent)

Total: 100 waves × 500ms = 50 seconds
Peak concurrent connections: 1000 (KHÔNG phải 100k!)
```

**From test results confirmation:**
```
100,000 Clients:
- Peak Concurrent: 499    ← ĐÂY!
- Total: 100000
- Successful: 100000

→ Tại MỖI thời điểm chỉ có ~500 connections
→ KHÔNG phải 100k connections đồng thời!
```

### D. Tại sao latency lại THẤP hơn với "100k clients"?

**Nguyên nhân 1: Ít contention hơn**

```python
# Test 10k clients:
# - Concurrent: 841 clients cùng lúc
# - Mỗi client gửi requests → Server xử lý 841 requests/lúc
# - Lock contention cao!

with registry_lock:  # Nhiều threads đợi lock
    registry[hostname] = {...}

# Test 100k clients:
# - Concurrent: CHỈ 499 clients cùng lúc
# - Server xử lý 499 requests/lúc
# - Lock contention THẤP HƠN!
```

**Nguyên nhân 2: Cache warming**

```python
# LIST operation:
# Test 10k: 9,944 LIST calls với registry có 10k entries
# → Mỗi LIST phải serialize 10k client records

# Test 100k: 66,670 LIST calls với registry có ~500 entries (concurrent)
# → Mỗi LIST chỉ serialize ~500 client records
# → NHANH HƠN nhiều!
```

**Nguyên nhân 3: Test simulation khác thực tế**

```python
# scalability_test.py - dòng 425-487
def run_client_simulation(client_id, ...):
    client = TestClient(...)
    client.register(...)    # REGISTER
    
    for _ in range(operations_per_client):
        # Random operations
        operation = random.choice(['PUBLISH', 'LIST', 'REQUEST', 'PING'])
        # ...
    
    client.unregister()    # UNREGISTER ngay
    client.close()         # Đóng connection
    # ↑ Client tồn tại rất ngắn (~500ms)

# → Registry size không bao giờ đạt 100k
# → Luôn chỉ có ~500-1000 entries
```

### E. Test có SAI không?

**✅ Test ĐÚNG về mặt kỹ thuật** (đo được performance)

**❌ Test SAI về mặt ý nghĩa** (không test concurrent connections)

**Vấn đề:**
1. **Tên gây hiểu lầm:** "100k clients" → Thực tế: "100k client sessions (sequential)"
2. **Không test concurrent:** Peak concurrent chỉ ~500, không phải 100k
3. **Registry không đầy:** Chỉ có ~500 entries vì clients disconnect nhanh

**Cách test ĐÚng concurrent 100k:**

```python
# Pseudocode for TRUE concurrent test:
def true_concurrent_test(num_clients=100000):
    clients = []
    
    # Step 1: Kết nối TẤT CẢ clients TRƯỚC
    for i in range(num_clients):
        client = TestClient(f"client_{i}", ...)
        client.register()
        clients.append(client)
        # KHÔNG close, giữ connection mở!
    
    # Step 2: Khi registry ĐẦY 100k entries
    # → BẮT ĐẦU test operations
    
    # Step 3: Đo latency với 100k CONCURRENT connections
    for client in clients:
        client.list()  # Serialize 100k entries!
        # → Latency sẽ CAO HƠN NHIỀU
    
    # Step 4: Cleanup
    for client in clients:
        client.unregister()
        client.close()
```

**Vấn đề của true concurrent test:**

```
Giới hạn hệ thống:
- File descriptors: Cần 100k FDs (default 1024!)
- Memory: 100k × 6 KB = 600 MB sockets
- Threads: 100k threads (context switching overhead)
- Ports (client-side): Cần 100k ephemeral ports

→ Cần cấu hình OS đặc biệt!
→ Test hiện tại dùng simulation để tránh vấn đề này
```

### F. Giới hạn dung lượng file gửi giữa các client

**❌ KHÔNG CÓ hard limit trong code!**

**Location:** `client.py` - P2P transfer (dòng 703-870)

```python
def download_from_peer(self, ip, port, fname, ...):
    # Không check file size trước khi download
    
    # Read header
    header = buf.split(b'\n')[0].decode()  # "LENGTH 1234567890"
    total_size = int(header.split()[1])
    #            ↑ Có thể là BẤT KỲ số nào (1 byte → terabytes)
    
    # Download chunks
    while received < total_size:  # No limit!
        chunk = conn.recv(min(256*1024, total_size - received))
        f.write(chunk)
        received += len(chunk)
```

**Giới hạn thực tế:**

#### 1. Disk Space
```python
# Client chỉ kiểm tra disk space qua exception
try:
    with open(outpath, 'wb') as f:
        f.write(chunk)
except OSError as e:
    # "No space left on device"
    print(f"Error: {e}")
```

#### 2. Memory (Chunked streaming)
```python
# File KHÔNG load toàn bộ vào RAM
# Đọc/ghi theo chunks:

# Sender (PeerServer):
chunk_size = 1024*1024 if size > 100*1024*1024 else 256*1024
#            ↑ 1MB                                 ↑ 256KB

with open(fpath, 'rb') as f:
    while True:
        chunk = f.read(chunk_size)  # Chỉ đọc 256KB-1MB mỗi lần
        conn.sendall(chunk)         # RAM usage: ~1-2 MB

# Receiver:
while received < total_size:
    chunk = conn.recv(256*1024)  # Nhận 256KB
    f.write(chunk)               # Ghi disk ngay
    # → RAM chỉ cần ~256KB buffer
```

**File size tested:**
```
From test results:
- Small files: < 1 MB
- Large files: Up to 1 GB (from P2P transfer test)

From code:
# client.py - dòng 286
chunk_size = 1024*1024 if size > 100*1024*1024 else 256*1024
#                              ↑
#                    Optimize cho files > 100 MB
```

#### 3. Network timeout
```python
# client.py - dòng 704
s.settimeout(30)  # 30 seconds

# Với file lớn:
# - 100 MB file @ 10 MB/s = 10 seconds ✓ OK
# - 1 GB file @ 10 MB/s = 100 seconds ✗ TIMEOUT!
```

**Timeout có thể gây vấn đề với:**
- File > 300 MB trên kết nối chậm
- Network unstable (packet loss, high latency)

**Workaround:**
```python
# Tăng timeout dựa vào file size
timeout = max(30, total_size / (1024*1024))  # 1s per MB
s.settimeout(timeout)
```

#### 4. TCP Window Size & Bandwidth
```python
# OS buffer size (có thể config):
# Linux default: ~87 KB send buffer, ~87 KB receive buffer

# Throughput limit (BDP - Bandwidth-Delay Product):
# Throughput = Window Size / RTT

# Example:
# - Window: 87 KB
# - RTT: 50 ms (LAN)
# → Max throughput: 87KB / 0.05s = 1.74 MB/s

# For 1 GB file:
# → Time = 1000 MB / 1.74 MB/s = 575 seconds (9.5 phút)
```

**From test results:**
```
Large files (1 GB):
- Average Speed: 76.12 MB/s  ← VERY FAST!
- Duration: 0.00 ms          ← Test file, not real transfer

→ Test sử dụng local files, không thực sự transfer qua network
→ Tốc độ thực tế phụ thuộc vào:
  - Network bandwidth (10 Mbps → 10 Gbps)
  - Latency (1ms LAN → 100ms WAN)
  - TCP window size
```

### G. Recommendations cho Production

**1. Tăng file descriptor limit:**
```bash
# Linux
sudo nano /etc/security/limits.conf
# Add:
* soft nofile 65536
* hard nofile 65536

# Verify:
ulimit -n
```

**2. Tăng TCP buffer sizes:**
```bash
# Linux sysctl
sudo sysctl -w net.core.rmem_max=16777216  # 16 MB
sudo sysctl -w net.core.wmem_max=16777216  # 16 MB
```

**3. Thêm timeout adaptive:**
```python
# client.py - download_from_peer
def download_from_peer(self, ip, port, fname, ...):
    # Calculate timeout based on file size
    if total_size < 10*1024*1024:        # < 10 MB
        timeout = 30
    elif total_size < 100*1024*1024:     # 10-100 MB
        timeout = 60
    else:                                 # > 100 MB
        timeout = max(120, total_size / (1024*1024))  # 1s per MB
    
    s.settimeout(timeout)
```

**4. Thêm progress callback cho large files:**
```python
# Để track tiến độ và detect stalls
def download_with_progress(self, ...):
    last_progress_time = time.time()
    
    while received < total_size:
        chunk = conn.recv(...)
        
        if time.time() - last_progress_time > 10:  # No progress for 10s
            raise TimeoutError("Transfer stalled")
        
        if chunk:
            last_progress_time = time.time()
```

**5. File size limits (Optional):**
```python
# Config
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB

# Check before download
if total_size > MAX_FILE_SIZE:
    print(f"File too large: {total_size / (1024**3):.2f} GB > {MAX_FILE_SIZE / (1024**3):.2f} GB")
    return None
```

### H. Giới hạn QUAN TRỌNG khi test trên cùng một máy

**PHÁT HIỆN CRITICAL:** Mỗi client CẦN 1 port riêng cho Peer Server!

#### 1. Tại sao mỗi client cần một port?

**Architecture:**
```python
# Mỗi client = 2 roles:

# Role 1: Client (outbound connections)
self.central = socket.connect((server_ip, 9000))
#                                          ↑ Server port
# → Không cần port cố định (OS auto-assign ephemeral port)

# Role 2: Peer Server (inbound connections) 
class PeerServer(threading.Thread):
    def __init__(self, listen_port):
        self.sock.bind(('', listen_port))  # ← MUST have unique port!
        self.sock.listen(5)
```

**Vấn đề khi test trên 1 máy:**
```
Client A: Peer server on port 6001
Client B: Peer server on port 6002
Client C: Peer server on port 6003
...
Client 1000: Peer server on port 7000

→ Mỗi client CHIẾM 1 port để lắng nghe P2P requests
→ KHÔNG thể 2 clients cùng port!
```

#### 2. Port range configuration

**Location:** `config.py` (dòng 25-26)
```python
CLIENT_PORT_MIN = 6000
CLIENT_PORT_MAX = 7000
# → Range: 6000-7000 = 1001 ports
```

**Location:** `user_db.py` - `find_available_port()` (dòng 174-185)
```python
def find_available_port(port_min=6000, port_max=7000):
    """Find an available port in the specified range"""
    for port in range(port_min, port_max + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', port))  # Try to bind
            sock.close()
            return port  # ✓ Port available
        except OSError:
            continue  # Port already in use
    return None  # ✗ No ports available!
```

**Location:** `client_api.py` - init endpoint (dòng 186-189)
```python
port = find_available_port()
if not port:
    print("[INIT] ERROR: No available ports")
    return jsonify({'success': False, 'error': 'No available ports'}), 500
```

#### 3. Giới hạn thực tế trên cùng một máy

**Maximum clients = Port range size**

```python
# Default config:
CLIENT_PORT_MIN = 6000
CLIENT_PORT_MAX = 7000

# → Max clients = 7000 - 6000 + 1 = 1001 clients
```

**Timeline khi tạo 1001 clients:**
```
Client 1:    Port 6000 ✓
Client 2:    Port 6001 ✓
Client 3:    Port 6002 ✓
...
Client 1000: Port 6999 ✓
Client 1001: Port 7000 ✓
Client 1002: find_available_port() → None ✗ ERROR!
```

**Error message:**
```json
{
  "success": false,
  "error": "No available ports"
}
```

#### 4. Giải pháp mở rộng port range

**Option 1: Tăng range trong config**

```python
# config.py
CLIENT_PORT_MIN = 6000
CLIENT_PORT_MAX = 65000  # ← Tăng lên!
# → Max clients = 59,001 clients

# Hoặc dùng toàn bộ user ports:
CLIENT_PORT_MIN = 1024   # Sau reserved ports
CLIENT_PORT_MAX = 65535  # Max port number
# → Max clients = 64,512 clients
```

**Pros:**
- ✅ Đơn giản, chỉ thay config
- ✅ Hỗ trợ nhiều clients hơn

**Cons:**
- ❌ Vẫn bị giới hạn 64k clients (1 máy)
- ❌ Ports conflict với services khác
- ❌ Ephemeral port range (32768-60999) bị chiếm

**Option 2: Dynamic port allocation (OS auto-assign)**

```python
# Thay vì:
sock.bind(('', specific_port))

# Dùng:
sock.bind(('', 0))  # ← Port 0 = OS tự chọn!
assigned_port = sock.getsockname()[1]
print(f"Client listening on port {assigned_port}")
```

**Modified code:**
```python
# client.py - PeerServer
class PeerServer(threading.Thread):
    def __init__(self, client_ref):
        super().__init__(daemon=True)
        self.client_ref = client_ref
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Let OS assign port
        self.sock.bind(('', 0))  # ← Dynamic!
        self.listen_port = self.sock.getsockname()[1]
        
        # Update client's advertised port
        self.client_ref.listen_port = self.listen_port
        
        self.sock.listen(5)
```

**Pros:**
- ✅ Không giới hạn bởi port range
- ✅ OS quản lý port conflicts
- ✅ Hỗ trợ ~60k clients (ephemeral ports)

**Cons:**
- ❌ Không control được port numbers
- ❌ Khó debug (ports thay đổi mỗi lần)

**Option 3: Multiple machines (Production approach)**

```
Machine 1:
├─ Server (port 9000)
└─ 0 clients

Machine 2:
├─ Client 1-1000 (ports 6000-6999)
└─ Client API (port 5501)

Machine 3:
├─ Client 1001-2000 (ports 6000-6999)
└─ Client API (port 5501)

...

Machine 102:
└─ Client 100001-101000 (ports 6000-6999)

→ 100k+ clients across 100+ machines
```

**Pros:**
- ✅ Scale lên TRIỆU clients
- ✅ Realistic test (distributed system)
- ✅ Không bị port conflicts

**Cons:**
- ❌ Cần nhiều máy/VMs
- ❌ Phức tạp setup

#### 5. Test current system limitations

**Test script để verify:**
```python
#!/usr/bin/env python3
"""Test maximum concurrent clients on same machine"""
import socket
import time

def test_max_clients(port_min=6000, port_max=7000):
    """Test how many clients can run simultaneously"""
    sockets = []
    
    print(f"Testing port range {port_min}-{port_max}...")
    
    for port in range(port_min, port_max + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', port))
            sock.listen(5)
            sockets.append(sock)
            
            if len(sockets) % 100 == 0:
                print(f"  Created {len(sockets)} sockets...")
        
        except OSError as e:
            print(f"  ✗ Failed at port {port}: {e}")
            break
    
    print(f"\n✓ Successfully created {len(sockets)} concurrent listeners")
    print(f"  Maximum clients on this machine: {len(sockets)}")
    
    # Cleanup
    for sock in sockets:
        sock.close()
    
    return len(sockets)

if __name__ == '__main__':
    # Test default range
    max_clients = test_max_clients(6000, 7000)
    
    # Test extended range
    print("\n" + "="*60)
    max_clients_extended = test_max_clients(6000, 65000)
    
    print(f"\nSummary:")
    print(f"  Default range (6000-7000): {max_clients} clients")
    print(f"  Extended range (6000-65000): {max_clients_extended} clients")
```

**Expected output:**
```
Testing port range 6000-7000...
  Created 100 sockets...
  Created 200 sockets...
  ...
  Created 1000 sockets...

✓ Successfully created 1001 concurrent listeners
  Maximum clients on this machine: 1001

Testing port range 6000-65000...
  Created 10000 sockets...
  Created 20000 sockets...
  ...

✓ Successfully created 59001 concurrent listeners
  Maximum clients on this machine: 59001
```

#### 6. Ephemeral ports conflict

**Warning:** Client outbound connections cũng dùng ports!

```python
# Client connects to server:
self.central = socket.connect(('server', 9000))
#              ↑ OS auto-assign ephemeral port (32768-60999 on Linux)

# → Mỗi client dùng:
#   - 1 listening port (6000-7000)
#   - 1+ ephemeral ports (32768-60999) cho outbound

# Với 1000 clients:
# - Listening: 6000-6999 (1000 ports)
# - Ephemeral: ~1000 ports from 32768-60999
# → Total: ~2000 ports used
```

**Port exhaustion scenario:**
```
Machine với 1000 clients:
├─ Peer listeners: 6000-6999 (1000 ports)
├─ Server connections: 1000 ephemeral ports
├─ P2P connections: Variable ephemeral ports
└─ Other services: SSH, HTTP, etc.

→ Có thể exhaust ephemeral ports (28231 available)
→ Cần monitor với: netstat -an | grep ESTABLISHED | wc -l
```

#### 7. OS limits cần tăng

**File descriptors:**
```bash
# Check current limit
ulimit -n
# → Default: 1024 (TOO LOW!)

# Increase (temporary)
ulimit -n 65536

# Increase (permanent)
sudo nano /etc/security/limits.conf
# Add:
* soft nofile 65536
* hard nofile 65536
```

**Socket buffers:**
```bash
# Increase network buffers for many connections
sudo sysctl -w net.core.somaxconn=4096
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=4096
```

#### 8. Thực tế test 100k clients

**From test results analysis:**
```
100,000 Clients Test:
- Peak Concurrent: 499 (NOT 100k!)
- Method: Sequential waves of 1000 clients
- Port reuse: ✓ Clients connect/disconnect rapidly
- Port range: 6000-7000 (1001 ports) is ENOUGH

Why it works:
- Clients don't stay connected long (~500ms)
- Ports get recycled quickly
- At any moment: only ~500 clients active
→ 1001 ports is sufficient for wave-based testing
```

**For TRUE concurrent 100k:**
```
Option 1: Distributed testing
- 100 machines × 1000 clients each
- Each machine: ports 6000-6999

Option 2: Single machine (impractical)
- Increase port range to 6000-65535
- → Max ~59k clients (still short of 100k!)
- Need OS tuning (file descriptors, buffers)
- High memory usage (~6 GB)

Option 3: Containerization
- 100 Docker containers × 1000 clients
- Each container: isolated port namespace
- Can reuse ports 6000-6999 in each container!
```

### I. Summary (Updated)

| Question | Answer |
|----------|--------|
| **Server handle bao nhiêu clients?** | Lý thuyết: HÀNG TRIỆU (limited by RAM/CPU, không phải port). Thực tế: 10k-100k tuỳ hardware |
| **Client cần port riêng?** | ✅ YES! Mỗi client = 1 Peer Server = cần 1 unique port để listen P2P |
| **Max clients trên 1 máy?** | Default: 1,001 (ports 6000-7000). Extended: ~59,001 (ports 6000-65535). TRUE limit: ~64k |
| **Tại sao 100k tốt hơn 10k?** | Test KHÔNG thực concurrent 100k! Chỉ ~500 concurrent. Registry nhỏ hơn → latency thấp hơn |
| **Test có sai?** | Đúng kỹ thuật, SAI ý nghĩa. Test "100k sessions" không phải "100k concurrent connections" |
| **Ports được reuse?** | ✅ YES trong wave-based testing (clients disconnect nhanh). ❌ NO trong true concurrent |
| **Dung lượng file giới hạn?** | KHÔNG có hard limit. Giới hạn thực tế: disk space, timeout (30s), network bandwidth |
| **File lớn nhất test?** | 1 GB (từ test results). Code support files > 100 MB với 1MB chunks |
| **Tốc độ transfer?** | Test: 76.12 MB/s (local). Thực tế: Phụ thuộc network (10 Mbps - 10 Gbps) |
| **Solution cho 100k concurrent?** | Multiple machines/containers hoặc OS port = 0 (dynamic allocation) |

---

## 12. Một máy tính có bao nhiêu ports? Làm sao kiểm tra?

### A. Lý thuyết về Ports

**Port là gì?**
- Port là một con số 16-bit trong TCP/IP
- Range: **0 - 65535** (2^16 = 65,536 ports)
- Port không phải phần cứng (hardware), là khái niệm phần mềm (software)

**Phân loại ports theo IANA (Internet Assigned Numbers Authority):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    PORT RANGE CLASSIFICATION                     │
├──────────────┬────────────┬─────────┬──────────────────────────┤
│    Range     │  Tên gọi   │ Số ports│       Mục đích           │
├──────────────┼────────────┼─────────┼──────────────────────────┤
│   0-1023     │ Well-Known │  1,024  │ System services, cần     │
│              │ System/    │         │ quyền root/admin để bind │
│              │ Reserved   │         │                          │
├──────────────┼────────────┼─────────┼──────────────────────────┤
│ 1024-49151   │ Registered │ 48,128  │ User applications,       │
│              │ User/App   │         │ không cần root           │
├──────────────┼────────────┼─────────┼──────────────────────────┤
│ 49152-65535  │ Dynamic/   │ 16,384  │ OS tự động cấp phát      │
│              │ Ephemeral  │         │ cho outbound connections │
└──────────────┴────────────┴─────────┴──────────────────────────┘
```

#### 📋 Chi tiết từng loại Port Range

**1️⃣ Well-Known Ports (0-1023) - System Ports**

Đặc điểm:
- Được IANA quản lý nghiêm ngặt
- Chỉ processes có quyền root/admin mới bind được
- Dành cho các dịch vụ chuẩn, phổ biến
- Clients biết trước port để connect

Mục đích:
```
✓ Dịch vụ hệ thống quan trọng
✓ Protocols chuẩn Internet
✓ Dễ nhớ, dễ tìm kiếm
✓ Ổn định, không thay đổi
```

Examples:
```
Port 20/21  : FTP (File Transfer)
Port 22     : SSH (Secure Shell)
Port 23     : Telnet
Port 25     : SMTP (Email gửi đi)
Port 53     : DNS (Domain Name System)
Port 67/68  : DHCP
Port 80     : HTTP (Web)
Port 110    : POP3 (Email nhận)
Port 143    : IMAP (Email)
Port 443    : HTTPS (Secure Web)
Port 3306   : MySQL (popular but technically registered)
```

Ứng dụng trong P2P system:
```python
# ❌ KHÔNG nên dùng:
SERVER_PORT = 80    # Conflict với web server!
SERVER_PORT = 443   # Conflict với HTTPS!
SERVER_PORT = 22    # Conflict với SSH!

# ❌ Cần sudo để chạy:
sudo python3 server.py  # Nếu dùng port < 1024
```

---

**2️⃣ Registered Ports (1024-49151) - User Ports**

Đặc điểm:
- Ứng dụng có thể đăng ký với IANA (không bắt buộc)
- Không cần quyền root/admin để bind
- Semi-standardized - một số được biết đến rộng rãi
- Best choice cho custom applications

Mục đích:
```
✓ Third-party applications
✓ Databases, application servers
✓ Custom services, P2P apps
✓ Development & testing
✓ Microservices
```

Examples:
```
Port 1433   : Microsoft SQL Server
Port 3000   : Node.js/React dev server (convention)
Port 3306   : MySQL
Port 5000   : Flask default
Port 5432   : PostgreSQL
Port 6379   : Redis
Port 8080   : HTTP alternate (Tomcat, proxy)
Port 8443   : HTTPS alternate
Port 9000   : SonarQube, PHP-FPM
Port 27017  : MongoDB
Port 27018  : MongoDB shard
```

Ứng dụng trong P2P system:
```python
# ✓ ĐANG DÙNG (ĐÚNG!):
SERVER_PORT = 9000              # Central metadata server
CLIENT_PORT_MIN = 6000          # PeerServer range
CLIENT_PORT_MAX = 7000          # Total: 1001 ports
FLASK_BACKEND = 5000            # API server
REACT_FRONTEND = 3000           # UI development

# Lý do chọn range này:
→ Không cần sudo để chạy
→ Ít conflict với system services
→ Đủ lớn để allocate nhiều clients (1001 ports)
→ Dễ quản lý và monitor
→ Không overlap với ephemeral ports
```

---

**3️⃣ Dynamic/Ephemeral Ports (49152-65535)**

Đặc điểm:
- Tự động cấp phát bởi Operating System
- Temporary (ephemeral = "short-lived")
- Không được đăng ký cố định cho service nào
- OS automatically chọn port available

Mục đích:
```
✓ Client-side của TCP connections
✓ Outbound connections (browse web, API calls)
✓ Source ports cho requests
✓ Temporary connections
✓ OS quản lý hoàn toàn
```

Cách hoạt động:
```
User Action:
1. Bạn mở Chrome, truy cập https://google.com

OS Automatically:
2. Chrome cần source port để gửi HTTP request
3. OS chọn 1 port AVAILABLE trong ephemeral range
   Example: OS chọn port 52347
   
4. Connection được thiết lập:
   Your PC:     192.168.1.5:52347  (ephemeral port)
      ↓ HTTPS
   Google:      142.250.4.46:443   (well-known port)

5. Khi đóng tab, connection đóng
   → Port 52347 được giải phóng
   → OS có thể dùng lại cho connection khác
```

Ephemeral Range theo OS:
```
Linux (default):   32768 - 60999  (28,232 ports)
macOS (your OS):   49152 - 65535  (16,384 ports) ← BẠN ĐANG DÙNG
Windows:           49152 - 65535  (16,384 ports)
FreeBSD:           10000 - 65535  (55,536 ports)
```

Example thực tế:
```bash
$ lsof -i TCP -s TCP:ESTABLISHED

COMMAND   PID   USER   NAME
Chrome    1234  user   52347u  IPv4  → google.com:443
Chrome    1234  user   52348u  IPv4  → facebook.com:443
Slack     5678  user   52349u  IPv4  → slack.com:443
VSCode    9012  user   52350u  IPv4  → github.com:443
Python    3456  user   52351u  IPv4  → api.openai.com:443

→ Tất cả ports 52347-52351 đều là ephemeral
→ OS tự động cấp phát
→ Sẽ tự động giải phóng khi đóng connection
```

Ứng dụng trong P2P system:
```python
# Client → Server connection
def connect_to_server():
    sock = socket.socket()
    sock.connect(('server_ip', 9000))  # Destination: port 9000
    
    # OS tự động chọn ephemeral port làm source:
    # Local:  192.168.1.5:52341  (ephemeral, OS auto-select)
    # Remote: 10.0.0.1:9000      (server's fixed port)

# ❌ KHÔNG NÊN dùng ephemeral range cho PeerServer:
CLIENT_PORT_MIN = 50000  # Trong ephemeral range của macOS!
CLIENT_PORT_MAX = 60000  # → HIGH RISK of conflicts!

# Vì sao?
# - OS đang dùng range này cho outbound connections
# - App của bạn muốn bind cố định trong range này
# → COLLISION: OS và App tranh giành cùng 1 port!
```

---

#### 🎯 So sánh 3 loại Ports trong P2P System

```
┌─────────────────────────────────────────────────────────────────┐
│                  P2P SYSTEM PORT USAGE                           │
├─────────────────┬────────────────┬───────────────────────────────┤
│  Component      │  Port Number   │  Port Type                    │
├─────────────────┼────────────────┼───────────────────────────────┤
│ Central Server  │  9000 (fixed)  │  Registered Port              │
│                 │                │  - Well-known endpoint        │
│                 │                │  - Clients connect here       │
│                 │                │  - Never changes              │
├─────────────────┼────────────────┼───────────────────────────────┤
│ Client          │  6000-7000     │  Registered Port (allocated)  │
│ PeerServer      │  (allocated)   │  - Each client gets 1 port    │
│                 │                │  - For receiving P2P files    │
│                 │                │  - Fixed during runtime       │
├─────────────────┼────────────────┼───────────────────────────────┤
│ Client→Server   │  ~52000-53000  │  Ephemeral Port (auto)        │
│ Connection      │  (OS auto)     │  - OS automatically assigns   │
│                 │                │  - Source port for outbound   │
│                 │                │  - Temporary, reusable        │
├─────────────────┼────────────────┼───────────────────────────────┤
│ Peer→Peer       │  ~52000-53000  │  Ephemeral Port (downloader)  │
│ Transfer        │  (OS auto)     │  - Downloader uses ephemeral  │
│                 │  → 6000-7000   │  - Uploader uses PeerServer   │
│                 │  (target)      │    port (registered)          │
└─────────────────┴────────────────┴───────────────────────────────┘
```

Example scenario:
```
ClientA wants to download file from ClientB:

1. ClientA → Server (get ClientB info)
   Source:      ClientA:52341 (ephemeral, OS auto)
   Destination: Server:9000   (registered, fixed)
   
2. ClientA → ClientB (P2P file transfer)
   Source:      ClientA:52342 (ephemeral, OS auto)
   Destination: ClientB:6050  (registered, allocated PeerServer)
   
Note:
- ClientA không cần fixed port cho outbound connections
- ClientB CẦN fixed port 6050 để receive incoming connections
- Server CẦN fixed port 9000 để clients biết nơi connect
```

---

#### 💡 Tại sao phải phân chia Port Ranges?

**1. Bảo mật (Security)**

```
Well-Known Ports (0-1023):
╔═══════════════════════════════════════════════════════════╗
║  Cần quyền root/admin để bind                              ║
║  → Ngăn user thường chiếm ports quan trọng                 ║
║  → Prevent port hijacking attacks                          ║
╚═══════════════════════════════════════════════════════════╝

Example:
❌ User không thể chạy fake HTTPS server trên port 443
   → Vì cần sudo → OS verify identity

✓ System services có thể trust ports < 1024
  → Chỉ admin mới bind được
```

```
Registered Ports (1024-49151):
╔═══════════════════════════════════════════════════════════╗
║  User có thể dùng mà không cần sudo                        ║
║  → Cho phép developers tạo apps dễ dàng                    ║
║  → Nhưng vẫn có thể monitor, restrict bằng firewall        ║
╚═══════════════════════════════════════════════════════════╝

Example trong P2P:
✓ Developer có thể test server.py trên port 9000
  → Không cần sudo python3 server.py
  → Dễ dàng debug và develop
```

```
Ephemeral Ports (49152-65535):
╔═══════════════════════════════════════════════════════════╗
║  OS quản lý hoàn toàn                                      ║
║  → Tránh applications conflicts                            ║
║  → Automatic port assignment                               ║
╚═══════════════════════════════════════════════════════════╝

Example:
→ 100 tabs Chrome, mỗi tab connect google.com:443
→ OS tự động cấp 100 ephemeral ports khác nhau
→ Không cần developer làm gì!
```

**2. Quản lý tài nguyên (Resource Management)**

```
Nếu KHÔNG phân chia ranges:
╔════════════════════════════════════════════════════════════╗
║  ❌ Applications tranh giành ports ngẫu nhiên              ║
║  ❌ Khó biết port nào dùng cho gì                          ║
║  ❌ Conflicts không kiểm soát được                         ║
║  ❌ Debugging nightmare                                    ║
╚════════════════════════════════════════════════════════════╝

Example chaos:
- SSH randomly uses port 42531 today, 15892 tomorrow
- MySQL suddenly on port 987 instead of 3306
- Your app can't find server because port changes
```

```
Với phân chia chuẩn:
╔════════════════════════════════════════════════════════════╗
║  ✓ System services: fixed ports, dễ nhớ                   ║
║  ✓ Applications: range rộng để allocate                   ║
║  ✓ Temporary connections: tự động, không cần quan tâm     ║
║  ✓ Easy troubleshooting                                   ║
╚════════════════════════════════════════════════════════════╝

Example organized:
→ SSH luôn port 22    → "ssh user@host" (không cần chỉ định port)
→ Web luôn port 80    → "http://website" (browser biết port 80)
→ P2P server port 9000 → Clients config 1 lần, dùng mãi
```

**3. Khả năng mở rộng (Scalability)**

```
Ví dụ trong P2P system:

Nếu dùng Ephemeral Ports cho PeerServer:
╔════════════════════════════════════════════════════════════╗
║  ❌ OS randomly assigns port mỗi lần start client         ║
║  ❌ Client không biết peer nào ở port nào                  ║
║  ❌ Phải announce port mỗi lần thay đổi                    ║
║  ❌ Registry complex, unreliable                           ║
╚════════════════════════════════════════════════════════════╝

Code nightmare:
ClientA starts → OS gives port 52341
ClientB wants to download → Connect to ClientA:???
  → Need to query registry every time
  → Port might change if ClientA restarts!
```

```
Với Registered Ports (6000-7000):
╔════════════════════════════════════════════════════════════╗
║  ✓ Fixed allocation cho mỗi client                        ║
║  ✓ Peers biết chính xác port để connect                   ║
║  ✓ Registry simple: just IP + allocated port              ║
║  ✓ Easy to manage và monitor                              ║
╚════════════════════════════════════════════════════════════╝

Code simple:
ClientA → Always uses port 6050 (allocated once)
ClientB → Registry says "ClientA at 192.168.1.5:6050"
ClientB → connect(192.168.1.5, 6050)  # Always works!
```

**4. Compatibility & Standards**

```
Standardized ports = Global compatibility
╔════════════════════════════════════════════════════════════╗
║  Mọi browser biết HTTP = port 80                          ║
║  Mọi FTP client biết port 21                              ║
║  Mọi database admin biết MySQL = 3306                     ║
║  → Không cần config, chỉ cần hostname!                    ║
╚════════════════════════════════════════════════════════════╝

Real world benefit:
→ Type "google.com" → Browser automatically uses :80
→ Connect to DB: "mysql://host/db" → Client knows :3306
→ No need to specify port every time!
```

---

#### 🎯 Best Practices cho P2P System

**✅ DO: Chọn Port Range trong Registered (1024-49151)**

```python
# GOOD CHOICE - Current config
SERVER_PORT = 9000              # Clean range, no conflicts
CLIENT_PORT_MIN = 6000          
CLIENT_PORT_MAX = 7000          # 1001 ports available

Why good:
✓ Không cần sudo
✓ Tránh xa well-known ports (không conflict system)
✓ Tránh xa ephemeral range (không conflict OS)
✓ Đủ lớn để scale (1001 concurrent clients)
```

**❌ DON'T: Dùng Well-Known Ports**

```python
# BAD - Conflicts!
SERVER_PORT = 80                # Web server already using!
SERVER_PORT = 443               # HTTPS conflict!
SERVER_PORT = 3306              # MySQL conflict!
SERVER_PORT = 22                # SSH conflict!

Problems:
❌ Cần sudo để chạy
❌ Conflicts với existing services
❌ Security risks
❌ Port already in use errors
```

**❌ DON'T: Overlap với Ephemeral Range**

```python
# BAD - macOS ephemeral: 49152-65535
CLIENT_PORT_MIN = 50000         # TRONG ephemeral range!
CLIENT_PORT_MAX = 60000         

Problems:
❌ OS đang dùng range này cho outbound connections
❌ High risk of port conflicts
❌ "Address already in use" errors
❌ Unreliable binding

Example conflict:
1. Your app tries bind port 52341
2. Meanwhile, Chrome used 52341 for google.com connection
3. bind() fails → "Address already in use"
```

**✅ DO: Reserve đủ ports cho scaling**

```python
# Current limit
CLIENT_PORT_MAX = 7000          # 1001 ports → max 1001 clients

# Để test 10k clients trên 1 máy:
CLIENT_PORT_MAX = 16000         # 10,001 ports
# Still < 49152 → Safe! No overlap with ephemeral

# Để test 20k clients:
CLIENT_PORT_MAX = 26000         # 20,001 ports
# Still in registered range → Good!
```

**✅ DO: Document port usage**

```python
# config.py
# Port Allocation Strategy:
# - Server: 9000 (fixed, well-known for clients)
# - Client PeerServers: 6000-7000 (allocated on connect)
# - Flask Backend API: 5000 (development)
# - React Frontend: 3000 (development)
# 
# Range chosen to avoid:
# - System ports (0-1023)
# - Common apps (3306=MySQL, 5432=PostgreSQL, 8080=proxies)
# - Ephemeral range (49152-65535 on macOS/Windows)

SERVER_PORT = 9000
CLIENT_PORT_MIN = 6000
CLIENT_PORT_MAX = 7000
```

**✅ DO: Check ports before binding**

```python
def find_available_port(start=6000, end=7000):
    """Find available port trong range an toàn"""
    for port in range(start, end + 1):
        with socket.socket() as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue  # Port in use, try next
    raise RuntimeError(f"No available ports in range {start}-{end}")

# Usage
port = find_available_port()  # Safe allocation
```

**✅ DO: Monitor port usage by range**

```bash
# Check your app ports (registered range)
echo "=== P2P Server ==="
lsof -i :9000

echo "=== Client PeerServers (6000-7000) ==="
lsof -i :6000-7000 | wc -l

echo "=== Flask Backend ==="
lsof -i :5000

echo "=== React Frontend ==="
lsof -i :3000

# Check system ports (well-known)
echo "=== Well-Known Ports Usage ==="
sudo lsof -i :1-1023 | wc -l

# Check ephemeral usage
echo "=== Ephemeral Ports Usage ==="
ss -tan state established | wc -l
```

**✅ DO: Set proper system limits**

```bash
# Increase file descriptor limit
ulimit -n 65536                 # Current session

# Permanent (add to ~/.zshrc or ~/.bashrc)
echo "ulimit -n 65536" >> ~/.zshrc

# Check current limit
ulimit -n

# For production (Linux /etc/sysctl.conf):
fs.file-max = 2097152
net.ipv4.ip_local_port_range = 1024 65535
```

---

#### 📊 Port Usage Comparison: Lựa chọn tốt vs tồi

```
╔═══════════════════════════════════════════════════════════════╗
║                    PORT RANGE DECISION TABLE                   ║
╠════════════════╦═══════════════╦════════════╦═════════════════╣
║   Your Choice  ║  Port Range   ║   Result   ║     Reason      ║
╠════════════════╬═══════════════╬════════════╬═════════════════╣
║ SERVER_PORT    ║               ║            ║                 ║
║   = 80         ║  Well-Known   ║     ❌     ║ Need sudo,      ║
║                ║  (0-1023)     ║            ║ HTTP conflict   ║
╠════════════════╬═══════════════╬════════════╬═════════════════╣
║ SERVER_PORT    ║  Registered   ║     ✅     ║ No sudo,        ║
║   = 9000       ║  (1024-49151) ║            ║ clean range     ║
╠════════════════╬═══════════════╬════════════╬═════════════════╣
║ CLIENT_PORT    ║  Registered   ║     ✅     ║ Safe, enough    ║
║   = 6000-7000  ║  (1024-49151) ║            ║ for 1k clients  ║
╠════════════════╬═══════════════╬════════════╬═════════════════╣
║ CLIENT_PORT    ║  Overlaps     ║     ❌     ║ OS conflicts!   ║
║   = 50000-60k  ║  Ephemeral    ║            ║ Unreliable      ║
║                ║  (49152-65535)║            ║                 ║
╠════════════════╬═══════════════╬════════════╬═════════════════╣
║ CLIENT_PORT    ║  Registered   ║     ✅     ║ Enough for      ║
║   = 6000-16000 ║  (1024-49151) ║            ║ 10k clients     ║
╚════════════════╩═══════════════╩════════════╩═════════════════╝
```

---

#### 🔍 Kiểm tra Port Range trên máy bạn

Từ kết quả `check_ports.sh` của bạn:

```
5️⃣  System Limits:
   File Descriptors: 1048575        ← EXCELLENT! (>1M FDs)
   ✓ Good limit
   Ephemeral Ports: 49152-65535     ← macOS default (16,384 ports)

6️⃣  Recommendations:
   Available client ports: 1001     ← Full range available!
   ✓ Good availability for testing

7️⃣  Quick Port Test (sample 5 ports):
   Port 6000: ✓ Available
   Port 6100: ✓ Available
   Port 6500: ✓ Available
   Port 6900: ✓ Available
   Port 7000: ✗ In use              ← CHÚ Ý: Port 7000 đang bị dùng!
```

**Phân tích:**

```
✅ File Descriptors: 1,048,575
   → Đủ để handle hàng ngàn clients
   → Mỗi client cần ~3-5 FDs (sockets)
   → Capacity: ~200k-300k concurrent connections (lý thuyết)

✅ Ephemeral Range: 49152-65535 (16,384 ports)
   → Client PORT_MIN (6000) không overlap
   → Client PORT_MAX (7000) không overlap
   → Safe choice!

⚠️  Port 7000 đang sử dụng
   → Cần check app nào đang dùng:
     lsof -i :7000
   
   → Temporary fix: giảm CLIENT_PORT_MAX = 6999
     CLIENT_PORT_MAX = 6999  # 1000 ports instead of 1001
   
   → Hoặc kill process đang dùng port 7000
```

**Recommendations cho config của bạn:**

```python
# Option 1: Tránh port 7000 (đang dùng)
CLIENT_PORT_MIN = 6000
CLIENT_PORT_MAX = 6999          # 1000 ports

# Option 2: Extend range để có nhiều ports hơn
CLIENT_PORT_MIN = 6000
CLIENT_PORT_MAX = 8000          # 2001 ports, skip conflict

# Option 3: Move to cleaner range
CLIENT_PORT_MIN = 10000
CLIENT_PORT_MAX = 11000         # 1001 ports, very clean range
```

### B. Tổng số ports có thể dùng

**Lý thuyết:**
```
Total ports per protocol = 65,536

TCP ports: 65,536 (0-65535)
UDP ports: 65,536 (0-65535)
          ↑
Total: 131,072 ports (TCP + UDP là RIÊNG BIỆT!)

Note: TCP port 80 ≠ UDP port 80
→ Có thể dùng cùng số port cho cả TCP và UDP!
```

**Thực tế (per IP address):**
```
Mỗi máy có thể có NHIỀU IP addresses:
- Localhost: 127.0.0.1
- LAN: 192.168.1.100
- VPN: 10.0.0.5
- Docker: 172.17.0.2

→ Mỗi IP = 65,536 ports
→ Total = N × 65,536 (N = số IP addresses)
```

### C. Cách kiểm tra ports đang dùng

#### 1. Linux/macOS - Kiểm tra ports đang listen

**Command: netstat**
```bash
# Xem tất cả ports đang LISTEN
netstat -tuln

# Output:
Proto Recv-Q Send-Q Local Address           Foreign Address         State
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN
tcp        0      0 127.0.0.1:3306          0.0.0.0:*               LISTEN
tcp        0      0 0.0.0.0:9000            0.0.0.0:*               LISTEN

# Giải thích:
# -t: TCP ports
# -u: UDP ports
# -l: Listening ports only
# -n: Show numeric addresses (không resolve DNS)
```

**Command: ss (modern alternative)**
```bash
# Tốt hơn netstat (faster, more info)
ss -tuln

# Xem số lượng ports đang dùng
ss -tuln | wc -l

# Xem ports theo state
ss -tan | grep LISTEN
ss -tan | grep ESTABLISHED
```

**Command: lsof**
```bash
# List Open Files (including network sockets)
sudo lsof -i -P -n

# Xem port cụ thể
sudo lsof -i :9000

# Output:
COMMAND  PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
python  1234 user    3u  IPv4  12345      0t0  TCP *:9000 (LISTEN)

# Xem ports của process cụ thể
sudo lsof -i -P -n | grep python
```

#### 2. Windows - Kiểm tra ports

**Command: netstat**
```powershell
# Xem ports đang LISTEN
netstat -an | findstr LISTEN

# Xem port cụ thể
netstat -an | findstr :9000

# Xem với process ID
netstat -ano

# Output:
Proto  Local Address          Foreign Address        State           PID
TCP    0.0.0.0:9000           0.0.0.0:0              LISTENING       1234
```

**PowerShell command:**
```powershell
# Modern way
Get-NetTCPConnection -State Listen

# Filter by port
Get-NetTCPConnection -LocalPort 9000
```

#### 3. Kiểm tra port có available không

**Python script:**
```python
import socket

def is_port_available(port, host='127.0.0.1'):
    """Check if a port is available"""
    try:
        # Try to bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.close()
        return True  # Port is available
    except OSError:
        return False  # Port is in use

# Test
for port in [22, 80, 9000, 12345]:
    status = "Available" if is_port_available(port) else "In Use"
    print(f"Port {port}: {status}")
```

**Using our test script:**
```bash
cd Assignment1/tests/scripts
python test_port_limits.py

# Kiểm tra range cụ thể
python -c "
import socket
available = 0
for port in range(6000, 7001):
    try:
        s = socket.socket()
        s.bind(('', port))
        s.close()
        available += 1
    except:
        pass
print(f'Available: {available}/1001 ports')
"
```

#### 4. Kiểm tra ephemeral port range

**Linux:**
```bash
# Xem ephemeral port range (ports OS dùng cho outbound connections)
cat /proc/sys/net/ipv4/ip_local_port_range
# Output: 32768  60999

# Tính số ports
python3 -c "low, high = 32768, 60999; print(f'Ephemeral ports: {high-low+1}')"
# Output: Ephemeral ports: 28232
```

**macOS:**
```bash
# Xem ephemeral range
sysctl net.inet.ip.portrange.first net.inet.ip.portrange.last
# Output:
# net.inet.ip.portrange.first: 49152
# net.inet.ip.portrange.last: 65535
```

**Windows:**
```powershell
# Xem dynamic port range
netsh int ipv4 show dynamicport tcp

# Output:
Protocol tcp Dynamic Port Range
---------------------------------
Start Port      : 49152
Number of Ports : 16384
```

### D. Đếm số ports đang sử dụng

**Linux/macOS one-liner:**
```bash
# Đếm LISTENING ports
netstat -tuln | grep LISTEN | wc -l

# Đếm ESTABLISHED connections
netstat -tan | grep ESTABLISHED | wc -l

# Đếm tổng tất cả connections
ss -tan | tail -n +2 | wc -l

# Đếm ports theo loại
echo "LISTEN: $(ss -tln | tail -n +2 | wc -l)"
echo "ESTABLISHED: $(ss -tan state established | wc -l)"
echo "TIME_WAIT: $(ss -tan state time-wait | wc -l)"
```

**Chi tiết hơn:**
```bash
# Group by state
ss -tan | awk '{print $1}' | sort | uniq -c

# Output:
#  50 ESTAB
#  10 LISTEN
# 100 TIME-WAIT
#   5 SYN-SENT
```

### E. Giới hạn thực tế

#### 1. Port Exhaustion

**Vấn đề:**
```bash
# Khi tạo quá nhiều outbound connections:
for i in {1..30000}; do
    curl http://example.com &  # Mỗi request = 1 ephemeral port
done

# Error:
# "Cannot assign requested address"
# → Hết ephemeral ports!
```

**Check ports đang dùng:**
```bash
# Xem distribution
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn

# Nếu thấy nhiều TIME_WAIT:
# → Ports đang chờ cleanup (2MSL = 60-120s)
# → Tạm thời không available
```

#### 2. File Descriptor Limits

**Mỗi socket = 1 file descriptor:**
```bash
# Check limit
ulimit -n
# Default: 1024

# Tăng temporary
ulimit -n 65536

# Tăng permanent (Linux)
sudo nano /etc/security/limits.conf
# Add:
* soft nofile 65536
* hard nofile 65536
```

**Impact:**
```
File descriptor limit = 1024
→ Max sockets (listening + connections) = 1024
→ Dù có 65k ports available, chỉ dùng được 1024!
```

### F. Test thực tế với hệ thống P2P

#### 1. Kiểm tra ports system đang dùng

```bash
# Before starting server
netstat -tuln | grep :9000
# (empty)

# Start server
python bklv-backend/server.py &

# Check again
netstat -tuln | grep :9000
# tcp  0  0  0.0.0.0:9000  0.0.0.0:*  LISTEN

# Start 3 clients
python bklv-backend/client.py --host client1 --port 6001 &
python bklv-backend/client.py --host client2 --port 6002 &
python bklv-backend/client.py --host client3 --port 6003 &

# Check client ports
netstat -tuln | grep -E ":(6001|6002|6003)"
# tcp  0  0  0.0.0.0:6001  0.0.0.0:*  LISTEN
# tcp  0  0  0.0.0.0:6002  0.0.0.0:*  LISTEN
# tcp  0  0  0.0.0.0:6003  0.0.0.0:*  LISTEN
```

#### 2. Verify available ports trong range

**Script đã tạo:**
```bash
cd Assignment1/tests/scripts
python test_port_limits.py

# Output sẽ show:
# - Ports 6000-7000: available vs in-use
# - Ephemeral port range
# - File descriptor limits
# - Estimated max clients
```

#### 3. Monitor during test

```bash
# Terminal 1: Run test
cd Assignment1/tests
python test_runner.py --mode quick

# Terminal 2: Monitor ports
watch -n 1 'ss -tln | grep -E ":(6[0-9]{3}|9000)" | wc -l'
# Hiển thị số ports đang LISTEN trong range 6000-6999 và 9000
```

### G. Port Management Best Practices

#### 1. Chọn port range

```python
# ✓ GOOD: Non-overlapping ranges
SYSTEM_PORTS = 1-1023         # Reserved
SERVER_PORT = 9000            # Single port
CLIENT_PORTS = 6000-7000      # Dedicated range
EPHEMERAL = 32768-60999       # OS managed

# ✗ BAD: Overlap với ephemeral
CLIENT_PORTS = 50000-60000    # Conflicts with ephemeral!
```

#### 2. Port cleanup

```bash
# Xem TIME_WAIT connections
ss -tan state time-wait | wc -l

# Giảm TIME_WAIT duration (risky!)
sudo sysctl -w net.ipv4.tcp_fin_timeout=30

# Enable port reuse
# → SO_REUSEADDR trong code (đã có)
```

#### 3. Monitoring

```bash
# Create monitoring script
cat > monitor_ports.sh << 'EOF'
#!/bin/bash
echo "=== Port Usage Monitor ==="
echo "Server (9000): $(ss -tln | grep :9000 | wc -l)"
echo "Clients (6000-7000): $(ss -tln | awk '$4 ~ /:6[0-9]{3}$/' | wc -l)"
echo "Total LISTEN: $(ss -tln | tail -n +2 | wc -l)"
echo "Total ESTABLISHED: $(ss -tan state established | wc -l)"
echo "File descriptors: $(ls -l /proc/$$/fd | wc -l) / $(ulimit -n)"
EOF

chmod +x monitor_ports.sh
watch -n 1 ./monitor_ports.sh
```

### H. Troubleshooting Common Issues

#### Issue 1: "Address already in use"

```bash
# Find what's using the port
sudo lsof -i :9000
# Kill the process
sudo kill -9 <PID>

# Or use SO_REUSEADDR (đã có trong code)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
```

#### Issue 2: "Cannot assign requested address"

```bash
# Check ephemeral ports exhaustion
ss -tan state time-wait | wc -l
# If > 20000: Wait or increase range

# Increase ephemeral range (temporary)
sudo sysctl -w net.ipv4.ip_local_port_range="15000 65000"
```

#### Issue 3: "Too many open files"

```bash
# Check current usage
ls -l /proc/$$/fd | wc -l

# Check limit
ulimit -n

# Increase limit
ulimit -n 65536
```

### I. Quick Reference Commands

```bash
# === Kiểm tra ports ===

# Xem tất cả LISTENING ports
netstat -tuln                    # Old way
ss -tuln                         # Modern way

# Xem port cụ thể
lsof -i :9000                    # Detailed info
ss -tlnp | grep :9000            # Quick check

# Đếm ports đang dùng
ss -tln | tail -n +2 | wc -l     # LISTEN
ss -tan state established | wc -l # ESTABLISHED

# === Kiểm tra availability ===

# Test 1 port
python3 -c "import socket; s=socket.socket(); s.bind(('',9000)); print('Available')"

# Test range
for p in {6000..6010}; do python3 -c "import socket; s=socket.socket(); s.bind(('',${p})); print('Port ${p}: OK')" 2>/dev/null || echo "Port ${p}: In use"; done

# === System limits ===

# File descriptors
ulimit -n

# Ephemeral range (Linux)
cat /proc/sys/net/ipv4/ip_local_port_range

# Connections per state
ss -tan | awk '{print $1}' | sort | uniq -c
```

### J. Summary Table

| Question | Answer |
|----------|--------|
| **Tổng số ports?** | 65,536 ports (0-65535) per protocol (TCP/UDP) |
| **TCP vs UDP?** | RIÊNG BIỆT! TCP port 80 ≠ UDP port 80 → Total 131,072 |
| **Per IP?** | Mỗi IP address = 65,536 ports. Multiple IPs → multiply |
| **Check đang dùng?** | `netstat -tuln` (old) hoặc `ss -tuln` (modern) |
| **Check port cụ thể?** | `lsof -i :9000` hoặc `ss -tlnp \| grep :9000` |
| **Available ports?** | Try `socket.bind(('', port))` - success = available |
| **Ephemeral range?** | Linux: `cat /proc/sys/net/ipv4/ip_local_port_range` |
| **Đếm ports?** | `ss -tln \| tail -n +2 \| wc -l` |
| **Max clients (1 máy)?** | Limited by available ports (6000-7000 = 1001) + FD limit |
| **Port reuse?** | SO_REUSEADDR (trong code) - reuse sau close |

---

*Document created for CN251 Assignment technical review*
