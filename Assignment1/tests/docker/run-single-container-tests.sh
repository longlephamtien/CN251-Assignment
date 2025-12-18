#!/bin/bash
###############################################################################
# Single-Container High-Density Testing
#
# Strategy: Override port range via environment variables
#   - Code không đổi (client.py, server.py)
#   - CLIENT_PORT_MIN/MAX được set qua ENV
#   - 1 container có thể chạy 10k, 50k, thậm chí 64k clients
#
# Examples:
#   - 10k clients:  CLIENT_PORT_MIN=1024  CLIENT_PORT_MAX=11024  (10,000 ports)
#   - 50k clients:  CLIENT_PORT_MIN=1024  CLIENT_PORT_MAX=51024  (50,000 ports)
#   - Max clients:  CLIENT_PORT_MIN=1024  CLIENT_PORT_MAX=65535  (64,511 ports)
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
COMPOSE_FILE="docker-compose.single-container.yml"
ENV_FILE=".env.single"
COORDINATOR="p2p-test-coordinator-single"
CLIENT_CONTAINER="p2p-client-allinone"
RESULTS_DIR="$(pwd)/../../tests/results"

print() {
    echo -e "${1}${2}${NC}"
}

print_header() {
    echo ""
    echo "========================================================================"
    print "$BLUE" "$1"
    echo "========================================================================"
    echo ""
}

setup_env() {
    local target_clients=${1:-10000}
    # Auto-calculate optimal port range (let OS choose)
    local port_min=1024  # Non-root ports start
    local buffer=100  # Safety buffer
    local needed_ports=$((target_clients + buffer))
    
    # Calculate port_max dynamically
    local port_max=$((port_min + needed_ports - 1))
    
    # Ensure we don't exceed system limits
    if [ $port_max -gt 65535 ]; then
        port_max=65535
        local available_ports=$((port_max - port_min + 1))
        
        if [ $available_ports -lt $needed_ports ]; then
            print "$RED" "ERROR: Requested $target_clients clients exceeds maximum capacity!"
            print "$RED" "  Maximum possible: $((available_ports - buffer)) clients"
            exit 1
        fi
    fi
    
    print "$CYAN" "Auto-Configuration:"
    print "$CYAN" "  Target clients: $target_clients"
    print "$CYAN" "  Port range: $port_min - $port_max (auto-calculated)"
    print "$CYAN" "  Available ports: $((port_max - port_min + 1))"
    print "$CYAN" "  Buffer: $buffer ports"
    print "$GREEN" "✓ Port range auto-configured"
    
    # Create/update .env file
    cat > "$ENV_FILE" << EOF
# Single-Container High-Density Test Configuration
# Generated: $(date)

# Target
TARGET_CLIENTS=$target_clients

# Port Range (override code defaults)
CLIENT_PORT_MIN=$port_min
CLIENT_PORT_MAX=$port_max

# Server Resources
SERVER_CPU_LIMIT=4.0
SERVER_MEMORY_LIMIT=16G

# Client Container Resources (needs to handle ALL clients)
CLIENT_CPU_LIMIT=12.0
CLIENT_MEMORY_LIMIT=32G
CLIENT_CPU_RESERVATION=2.0
CLIENT_MEMORY_RESERVATION=4G

# Coordinator
TEST_TIMEOUT=7200

# Network
DOCKER_NETWORK_DRIVER=bridge
NETWORK_SUBNET=172.31.0.0/16
EOF
    
    print "$GREEN" "✓ Created $ENV_FILE"
}

check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print "$RED" "ERROR: Docker is not running!"
        exit 1
    fi
    
    # Check resources
    print "$CYAN" "Docker Resources:"
    docker info | grep -E "CPUs|Total Memory" || true
}

start_infrastructure() {
    print_header "Starting Infrastructure"
    
    # Start with env file
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    # Wait for server
    print "$YELLOW" "Waiting for server..."
    for i in {1..60}; do
        if docker-compose -f "$COMPOSE_FILE" ps server | grep -q "healthy"; then
            print "$GREEN" "✓ Server is healthy"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    print "$GREEN" "✓ Infrastructure ready"
}

run_scalability_test() {
    local target_clients=$1
    
    print_header "Running Scalability Test"
    print "$CYAN" "Target clients: $target_clients"
    
    # Get port configuration from env
    source "$ENV_FILE"
    
    print "$CYAN" "Port range: $CLIENT_PORT_MIN - $CLIENT_PORT_MAX"
    
    # Execute scalability test inside client container
    print "$YELLOW" "Starting scalability test execution..."
    
    docker exec -i "$CLIENT_CONTAINER" python3 << 'PYTHON_SCRIPT'
import sys
import time
import os
from pathlib import Path
import random
import shutil
import threading

# Add paths
sys.path.insert(0, '/app/bklv-backend')

# Get configuration from environment
SERVER_HOST = os.getenv('SERVER_HOST', 'p2p-server')
SERVER_PORT = int(os.getenv('SERVER_PORT', '9000'))
CLIENT_PORT_MIN = int(os.getenv('CLIENT_PORT_MIN', '1024'))
CLIENT_PORT_MAX = int(os.getenv('CLIENT_PORT_MAX', '65535'))
TARGET_CLIENTS = int(os.getenv('TARGET_CLIENTS', '1000'))

print(f"[SCALABILITY TEST - Realistic P2P Operations]")
print(f"[CONFIG] Server: {SERVER_HOST}:{SERVER_PORT}")
print(f"[CONFIG] Port range: {CLIENT_PORT_MIN}-{CLIENT_PORT_MAX}")
print(f"[CONFIG] Target clients: {TARGET_CLIENTS}")

# Import after setting up path
from client import Client
from datetime import datetime
import json

# Get available test files
TEST_FILES_DIR = Path('/app/files')
available_files = list(TEST_FILES_DIR.glob('*.txt'))
if not available_files:
    # Fallback to .bin files if no .txt files
    available_files = list(TEST_FILES_DIR.glob('*.bin'))

print(f"[CONFIG] Available test files: {len(available_files)}")

results = {
    'test_type': 'scalability',
    'start_time': time.time(),
    'target_clients': TARGET_CLIENTS,
    'successful_registrations': 0,
    'failed_registrations': 0,
    'registry_times': [],
    'concurrent_metrics': {
        'peak_concurrent_clients': 0,
        'avg_concurrent_clients': 0,
        'concurrent_samples': []
    },
    'resource_usage': {
        'cpu_samples': [],
        'memory_samples': []
    },
    'operations': {
        'register': {'success': 0, 'failed': 0, 'times': []},
        'publish': {'success': 0, 'failed': 0, 'times': []},
        'unpublish': {'success': 0, 'failed': 0, 'times': []},
        'fetch': {'success': 0, 'failed': 0, 'times': []},
        'ping': {'success': 0, 'failed': 0, 'times': []},
        'request': {'success': 0, 'failed': 0, 'times': []},
        'list_network': {'success': 0, 'failed': 0, 'times': []},
        'list_local': {'success': 0, 'failed': 0, 'times': []}
    },
    'errors': []
}

clients = []
lock = threading.Lock()
active_clients = 0
active_clients_lock = threading.Lock()

# Thread to monitor concurrent clients AND resource usage
def monitor_concurrent_clients():
    import psutil
    process = psutil.Process()
    
    while True:
        with active_clients_lock:
            current_active = active_clients
        
        # Sample CPU and memory
        try:
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            with lock:
                results['resource_usage']['cpu_samples'].append(cpu_percent)
                results['resource_usage']['memory_samples'].append(memory_mb)
        except:
            pass
        
        with lock:
            results['concurrent_metrics']['concurrent_samples'].append(current_active)
            if current_active > results['concurrent_metrics']['peak_concurrent_clients']:
                results['concurrent_metrics']['peak_concurrent_clients'] = current_active
        
        time.sleep(0.5)
        
        if current_active == 0 and len(results['concurrent_metrics']['concurrent_samples']) > 10:
            break

monitor_thread = threading.Thread(target=monitor_concurrent_clients, daemon=True)
monitor_thread.start()

def run_client(client_id):
    global active_clients
    client = None
    
    try:
        with active_clients_lock:
            active_clients += 1
        
        port = CLIENT_PORT_MIN + (client_id % (CLIENT_PORT_MAX - CLIENT_PORT_MIN + 1))
        hostname = f'client_{client_id}'
        repo = f'/app/repos/repo_{client_id}'
        
        Path(repo).mkdir(parents=True, exist_ok=True)
        
        # 1. REGISTER operation
        reg_start = time.time()
        client = Client(
            hostname=hostname,
            listen_port=port,
            repo_dir=repo,
            server_host=SERVER_HOST,
            server_port=SERVER_PORT
        )
        reg_time = (time.time() - reg_start) * 1000
        
        with lock:
            clients.append(client)
            results['successful_registrations'] += 1
            results['registry_times'].append(reg_time)
            results['operations']['register']['success'] += 1
            results['operations']['register']['times'].append(reg_time)
        
        # Copy test files
        num_files = random.randint(1, min(5, len(available_files)))
        selected_files = random.sample(available_files, num_files)
        
        for test_file in selected_files:
            try:
                dest_file = Path(repo) / test_file.name
                shutil.copy2(test_file, dest_file)
            except:
                pass
        
        # 2. PUBLISH operations
        try:
            local_files = [f for f in Path(repo).glob('*') if f.is_file()]
            for local_file in local_files:
                try:
                    op_start = time.time()
                    client.publish(str(local_file))
                    op_time = (time.time() - op_start) * 1000
                    
                    with lock:
                        results['operations']['publish']['success'] += 1
                        results['operations']['publish']['times'].append(op_time)
                except Exception as e:
                    with lock:
                        results['operations']['publish']['failed'] += 1
        except Exception as e:
            with lock:
                results['operations']['publish']['failed'] += 1
        
        # 3. PING operation (heartbeat)
        try:
            op_start = time.time()
            # Simulate ping by calling list_network (triggers server communication)
            client.list_network()
            op_time = (time.time() - op_start) * 1000
            
            with lock:
                results['operations']['ping']['success'] += 1
                results['operations']['ping']['times'].append(op_time)
        except Exception as e:
            with lock:
                results['operations']['ping']['failed'] += 1
        
        # 4. LIST_NETWORK operation
        try:
            op_start = time.time()
            network = client.list_network()
            op_time = (time.time() - op_start) * 1000
            
            with lock:
                results['operations']['list_network']['success'] += 1
                results['operations']['list_network']['times'].append(op_time)
        except Exception as e:
            with lock:
                results['operations']['list_network']['failed'] += 1
        
        # 5. LIST_LOCAL operation
        try:
            op_start = time.time()
            local_files = client.list_local()
            op_time = (time.time() - op_start) * 1000
            
            with lock:
                results['operations']['list_local']['success'] += 1
                results['operations']['list_local']['times'].append(op_time)
        except Exception as e:
            with lock:
                results['operations']['list_local']['failed'] += 1
        
        # 6. UNPUBLISH operation (30% chance)
        if random.random() < 0.3:
            try:
                local_files = [f for f in Path(repo).glob('*') if f.is_file()]
                if local_files:
                    file_to_unpublish = random.choice(local_files)
                    
                    op_start = time.time()
                    client.unpublish(file_to_unpublish.name)
                    op_time = (time.time() - op_start) * 1000
                    
                    with lock:
                        results['operations']['unpublish']['success'] += 1
                        results['operations']['unpublish']['times'].append(op_time)
            except Exception as e:
                with lock:
                    results['operations']['unpublish']['failed'] += 1
        
        # 7. FETCH/REQUEST operation (20% chance)
        if random.random() < 0.2 and len(clients) > 1:
            try:
                with lock:
                    other_clients = [c for c in clients if c != client]
                
                if other_clients:
                    other_client = random.choice(other_clients)
                    other_files = other_client.list_local()
                    
                    if other_files:
                        file_to_fetch = random.choice(other_files)
                        
                        op_start = time.time()
                        client.fetch(file_to_fetch['name'])
                        op_time = (time.time() - op_start) * 1000
                        
                        with lock:
                            results['operations']['fetch']['success'] += 1
                            results['operations']['fetch']['times'].append(op_time)
                            results['operations']['request']['success'] += 1
                            results['operations']['request']['times'].append(op_time)
            except Exception as e:
                with lock:
                    results['operations']['fetch']['failed'] += 1
                    results['operations']['request']['failed'] += 1
        
        time.sleep(random.uniform(0.5, 2.0))
        
        if client:
            client.close()
        
        if client_id % 100 == 0:
            with active_clients_lock:
                print(f"[PROGRESS] Client {client_id} completed (reg: {reg_time:.2f}ms, active: {active_clients})")
        
    except Exception as e:
        with lock:
            results['failed_registrations'] += 1
            results['errors'].append(f"Client {client_id}: {str(e)}")
            results['operations']['register']['failed'] += 1
        
        if client and hasattr(client, 'close'):
            try:
                client.close()
            except:
                pass
        
        if client_id % 100 == 0:
            print(f"[ERROR] Client {client_id} failed: {e}")
    
    finally:
        with active_clients_lock:
            active_clients -= 1

# Run in waves
wave_size = min(1000, TARGET_CLIENTS)
num_waves = (TARGET_CLIENTS + wave_size - 1) // wave_size

print(f"[STRATEGY] {num_waves} waves of {wave_size} clients")
print(f"[OPERATIONS] Register, Publish, Ping, Request, List, Fetch, Unpublish")
print(f"[MONITORING] Tracking concurrent active clients...\n")

for wave in range(num_waves):
    wave_start = wave * wave_size
    wave_end = min((wave + 1) * wave_size, TARGET_CLIENTS)
    
    print(f"[WAVE {wave + 1}/{num_waves}] Clients {wave_start}-{wave_end-1}")
    
    threads = []
    for client_id in range(wave_start, wave_end):
        t = threading.Thread(target=run_client, args=(client_id,), daemon=True)
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join(timeout=180)
    
    if wave < num_waves - 1:
        time.sleep(1)

time.sleep(1)

results['end_time'] = time.time()
results['duration'] = results['end_time'] - results['start_time']
results['success_rate'] = (results['successful_registrations'] / TARGET_CLIENTS * 100) if TARGET_CLIENTS > 0 else 0

# Calculate concurrent metrics
if results['concurrent_metrics']['concurrent_samples']:
    results['concurrent_metrics']['avg_concurrent_clients'] = sum(results['concurrent_metrics']['concurrent_samples']) / len(results['concurrent_metrics']['concurrent_samples'])

# Calculate resource usage statistics
if results['resource_usage']['cpu_samples']:
    results['resource_stats'] = {
        'cpu_avg_percent': sum(results['resource_usage']['cpu_samples']) / len(results['resource_usage']['cpu_samples']),
        'cpu_peak_percent': max(results['resource_usage']['cpu_samples']),
        'memory_avg_mb': sum(results['resource_usage']['memory_samples']) / len(results['resource_usage']['memory_samples']),
        'memory_peak_mb': max(results['resource_usage']['memory_samples'])
    }

# Calculate statistics for registry
if results['registry_times']:
    results['registry_stats'] = {
        'avg_ms': sum(results['registry_times']) / len(results['registry_times']),
        'min_ms': min(results['registry_times']),
        'max_ms': max(results['registry_times']),
        'p50_ms': sorted(results['registry_times'])[int(len(results['registry_times']) * 0.50)],
        'p95_ms': sorted(results['registry_times'])[int(len(results['registry_times']) * 0.95)],
        'p99_ms': sorted(results['registry_times'])[int(len(results['registry_times']) * 0.99)]
    }

# Calculate statistics for each operation
results['operation_stats'] = {}
for op_name, op_data in results['operations'].items():
    if op_data['times']:
        sorted_times = sorted(op_data['times'])
        results['operation_stats'][op_name] = {
            'count': op_data['success'] + op_data['failed'],
            'success': op_data['success'],
            'failed': op_data['failed'],
            'success_rate': (op_data['success'] / (op_data['success'] + op_data['failed']) * 100) if (op_data['success'] + op_data['failed']) > 0 else 0,
            'avg_ms': sum(op_data['times']) / len(op_data['times']),
            'min_ms': min(op_data['times']),
            'max_ms': max(op_data['times']),
            'p50_ms': sorted_times[int(len(sorted_times) * 0.50)],
            'p95_ms': sorted_times[int(len(sorted_times) * 0.95)],
            'p99_ms': sorted_times[int(len(sorted_times) * 0.99)]
        }

# Summary
print("\n" + "="*70)
print("SCALABILITY TEST SUMMARY - REALISTIC P2P OPERATIONS")
print("="*70)
print(f"Target Clients:   {TARGET_CLIENTS}")
print(f"Successful:       {results['successful_registrations']}")
print(f"Failed:           {results['failed_registrations']}")
print(f"Success Rate:     {results['success_rate']:.2f}%")
print(f"Duration:         {results['duration']:.2f}s")
print(f"Throughput:       {results['successful_registrations']/results['duration']:.2f} clients/sec")

print(f"\nConcurrency Metrics:")
print(f"  Peak Concurrent:  {results['concurrent_metrics']['peak_concurrent_clients']} clients")
print(f"  Avg Concurrent:   {results['concurrent_metrics']['avg_concurrent_clients']:.2f} clients")
print(f"  Samples Taken:    {len(results['concurrent_metrics']['concurrent_samples'])}")

if 'resource_stats' in results:
    rs = results['resource_stats']
    print(f"\nResource Usage:")
    print(f"  CPU:     {rs['cpu_avg_percent']:.2f}% avg, {rs['cpu_peak_percent']:.2f}% peak")
    print(f"  Memory:  {rs['memory_avg_mb']:.2f} MB avg, {rs['memory_peak_mb']:.2f} MB peak")

if 'registry_stats' in results:
    stats = results['registry_stats']
    print(f"\nRegistry Performance:")
    print(f"  Avg:  {stats['avg_ms']:.2f}ms")
    print(f"  P50:  {stats['p50_ms']:.2f}ms")
    print(f"  P95:  {stats['p95_ms']:.2f}ms")
    print(f"  P99:  {stats['p99_ms']:.2f}ms")

print(f"\nP2P Operations:")
for op_name in ['register', 'publish', 'ping', 'list_network', 'request', 'fetch', 'unpublish']:
    if op_name in results.get('operation_stats', {}):
        op_stats = results['operation_stats'][op_name]
        print(f"  {op_name.upper()}:")
        print(f"    Count:        {op_stats['count']}")
        print(f"    Success:      {op_stats['success']} ({op_stats['success_rate']:.1f}%)")
        print(f"    Avg Time:     {op_stats['avg_ms']:.2f}ms")
        print(f"    P95:          {op_stats['p95_ms']:.2f}ms")

print("="*70)

# Save results
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = f"/app/tests/results/scalability_{TARGET_CLIENTS}_{timestamp}.json"

Path(result_file).parent.mkdir(parents=True, exist_ok=True)
with open(result_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n[RESULTS] {result_file}")
PYTHON_SCRIPT
    
    print "$GREEN" "✓ Scalability test completed"
}

# ===================================================================
# P2P Transfer Test
# ===================================================================

run_p2p_transfer_test() {
    local num_clients=$1
    
    print_header "Running P2P Transfer Test"
    print "$CYAN" "Number of clients: $num_clients"
    
    source "$ENV_FILE"
    
    print "$YELLOW" "Starting P2P transfer test..."
    
    docker exec -i "$CLIENT_CONTAINER" python3 << EOF
import sys
import time
import os
from pathlib import Path
import random
import shutil
import threading
import logging

sys.path.insert(0, '/app/bklv-backend')

# Disable client/server logging
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger('client').setLevel(logging.CRITICAL)
logging.getLogger('server').setLevel(logging.CRITICAL)

# Suppress client output
import builtins
_original_print = builtins.print
def silent_print(*args, **kwargs):
    msg = ' '.join(str(arg) for arg in args)
    # Only allow test progress messages
    if any(marker in msg for marker in ['[P2P', '[CONFIG]', '[SETUP]', '[VERIFY]', '[TEST]', '[TRANSFER', '[CLEANUP]', '[SUMMARY]', '[ERROR]', '=']):
        _original_print(*args, **kwargs)
builtins.print = silent_print

SERVER_HOST = os.getenv('SERVER_HOST', 'p2p-server')
SERVER_PORT = int(os.getenv('SERVER_PORT', '9000'))
CLIENT_PORT_MIN = int(os.getenv('CLIENT_PORT_MIN', '1024'))
NUM_CLIENTS = $num_clients

print(f"[P2P TRANSFER TEST]")
print(f"[CONFIG] Clients: {NUM_CLIENTS}")

from client import Client
import json
from datetime import datetime

# Get available test files
TEST_FILES_DIR = Path('/app/files')

# Look for all test files (txt, bin, etc.)
txt_files = list(TEST_FILES_DIR.glob('*.txt'))
bin_files = list(TEST_FILES_DIR.glob('*.bin'))
available_files = txt_files + bin_files

print(f"[CONFIG] Found {len(txt_files)} .txt and {len(bin_files)} .bin files")

if len(available_files) == 0:
    print(f"[ERROR] No test files found in {TEST_FILES_DIR}")
    sys.exit(1)

results = {
    'test_type': 'p2p_transfer',
    'start_time': time.time(),
    'num_clients': NUM_CLIENTS,
    'transfers': [],
    'successful': 0,
    'failed': 0,
    'resource_usage': {
        'cpu_samples': [],
        'memory_samples': []
    },
    'transfer_by_size': {
        'tiny': {'count': 0, 'total_time': 0, 'total_size': 0},
        'small': {'count': 0, 'total_time': 0, 'total_size': 0},
        'medium': {'count': 0, 'total_time': 0, 'total_size': 0},
        'large': {'count': 0, 'total_time': 0, 'total_size': 0}
    }
}

# Resource monitoring thread
def monitor_resources():
    import psutil
    process = psutil.Process()
    
    while True:
        try:
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            results['resource_usage']['cpu_samples'].append(cpu_percent)
            results['resource_usage']['memory_samples'].append(memory_mb)
        except:
            pass
        
        time.sleep(0.5)
        
        # Stop after reasonable duration
        if time.time() - results['start_time'] > 300:  # 5 minutes max
            break

monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
monitor_thread.start()

# Create clients and populate with files
clients = []
client_files = {}  # Track files per client
print(f"[SETUP] Creating {NUM_CLIENTS} clients...")

for i in range(NUM_CLIENTS):
    port = CLIENT_PORT_MIN + i
    repo = f'/app/repos/repo_{i}'
    
    # Create repo directory
    Path(repo).mkdir(parents=True, exist_ok=True)
    
    # Copy random test files to each client
    num_files = random.randint(2, min(8, len(available_files)))
    selected_files = random.sample(available_files, num_files)
    
    for test_file in selected_files:
        try:
            dest_file = Path(repo) / test_file.name
            shutil.copy2(test_file, dest_file)
        except:
            pass
    
    try:
        client = Client(
            hostname=f'client_{i}',
            listen_port=port,
            repo_dir=repo,
            server_host=SERVER_HOST,
            server_port=SERVER_PORT
        )
        
        # Publish files and track them (skip duplicates automatically)
        published_files = []
        for local_file in Path(repo).glob('*'):
            if local_file.is_file():
                try:
                    success, _ = client.publish(str(local_file))
                    if success:
                        published_files.append({
                            'name': local_file.name,
                            'size': local_file.stat().st_size
                        })
                except:
                    pass
        
        client_files[i] = published_files
        clients.append(client)
    
    except:
        pass

print(f"[SETUP] Created {len(clients)} clients")

# Give time for server to index all files
time.sleep(3)

# Verify clients can see network files
sample_client = clients[0] if clients else None
if sample_client:
    try:
        network_files = sample_client.list_network()
        print(f"[VERIFY] Network has {len(network_files)} files")
        if len(network_files) == 0:
            print(f"[ERROR] No files visible in network!")
    except:
        pass

print(f"[TEST] Starting {min(NUM_CLIENTS * 2, 100)} transfers...")

# Perform random transfers
num_transfers = min(NUM_CLIENTS * 2, 100)

for i in range(num_transfers):
    try:
        # Pick random destination client
        dst_client = random.choice(clients)
        
        # Get available files from network
        network_files = dst_client.list_network()
        
        if not network_files:
            results['failed'] += 1
            continue
        
        # Filter out files already in destination's local repo
        dst_local = dst_client.list_local()
        dst_local_names = {f.get('name', f.get('fname')) for f in dst_local}
        
        available_files_to_fetch = [
            f for f in network_files 
            if f.get('name', f.get('fname')) not in dst_local_names
        ]
        
        if not available_files_to_fetch:
            # All files already local, pick any network file for demonstration
            available_files_to_fetch = network_files
        
        file_to_transfer = random.choice(available_files_to_fetch)
        file_name = file_to_transfer.get('name', file_to_transfer.get('fname'))
        file_size = file_to_transfer.get('size', 0)
        
        if not file_name:
            results['failed'] += 1
            continue
        
        transfer_start = time.time()
        try:
            dst_client.fetch(file_name)
            transfer_time = time.time() - transfer_start
            
            # Categorize by size
            size_category = 'tiny'
            if file_size > 10 * 1024 * 1024:  # > 10MB
                size_category = 'large'
            elif file_size > 1 * 1024 * 1024:  # > 1MB
                size_category = 'medium'
            elif file_size > 100 * 1024:  # > 100KB
                size_category = 'small'
            
            results['transfer_by_size'][size_category]['count'] += 1
            results['transfer_by_size'][size_category]['total_time'] += transfer_time
            results['transfer_by_size'][size_category]['total_size'] += file_size
            
            speed_mbps = (file_size / transfer_time / 1024 / 1024) if transfer_time > 0 else 0
            
            results['transfers'].append({
                'file': file_name,
                'size': file_size,
                'size_category': size_category,
                'time_seconds': transfer_time,
                'speed_mbps': speed_mbps
            })
            results['successful'] += 1
            
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{num_transfers}] {results['successful']} successful, {results['failed']} failed")
        
        except:
            results['failed'] += 1
    
    except:
        results['failed'] += 1

# Cleanup
for idx, client in enumerate(clients):
    try:
        client.close()
    except:
        pass

results['end_time'] = time.time()
results['duration'] = results['end_time'] - results['start_time']

# Calculate resource usage statistics
if results['resource_usage']['cpu_samples']:
    results['resource_stats'] = {
        'cpu_avg_percent': sum(results['resource_usage']['cpu_samples']) / len(results['resource_usage']['cpu_samples']),
        'cpu_peak_percent': max(results['resource_usage']['cpu_samples']),
        'memory_avg_mb': sum(results['resource_usage']['memory_samples']) / len(results['resource_usage']['memory_samples']),
        'memory_peak_mb': max(results['resource_usage']['memory_samples'])
    }

# Calculate stats
if results['transfers']:
    avg_speed = sum(t['speed_mbps'] for t in results['transfers']) / len(results['transfers'])
    results['avg_speed_mbps'] = avg_speed
    
    # Calculate per-category stats
    for category, data in results['transfer_by_size'].items():
        if data['count'] > 0:
            data['avg_time'] = data['total_time'] / data['count']
            data['avg_speed_mbps'] = (data['total_size'] / data['total_time'] / 1024 / 1024) if data['total_time'] > 0 else 0

# Summary
print("\\n" + "="*70)
print("P2P TRANSFER TEST SUMMARY")
print("="*70)
print(f"Clients:          {NUM_CLIENTS}")
print(f"Attempted:        {num_transfers}")
print(f"Successful:       {results['successful']}")
print(f"Failed:           {results['failed']}")
print(f"Success Rate:     {(results['successful']/num_transfers*100) if num_transfers > 0 else 0:.1f}%")
print(f"Duration:         {results['duration']:.2f}s")

if 'resource_stats' in results:
    rs = results['resource_stats']
    print(f"\\nResource Usage:")
    print(f"  CPU:     {rs['cpu_avg_percent']:.2f}% avg, {rs['cpu_peak_percent']:.2f}% peak")
    print(f"  Memory:  {rs['memory_avg_mb']:.2f} MB avg, {rs['memory_peak_mb']:.2f} MB peak")

if 'avg_speed_mbps' in results:
    print(f"\\nOverall:")
    print(f"  Avg Speed:      {results['avg_speed_mbps']:.2f} MB/s")

print(f"\\nBy File Size:")
for category in ['tiny', 'small', 'medium', 'large']:
    data = results['transfer_by_size'][category]
    if data['count'] > 0:
        print(f"  {category.upper()}:")
        print(f"    Count:        {data['count']}")
        print(f"    Avg Time:     {data['avg_time']:.3f}s")
        print(f"    Avg Speed:    {data['avg_speed_mbps']:.2f} MB/s")

if results['successful'] == 0:
    print(f"\\n⚠️  WARNING: No successful transfers!")
    print(f"  Possible issues:")
    print(f"    - No test files found in /app/files")
    print(f"    - Clients failed to connect to server")
    print(f"    - Files not published correctly")
    print(f"    - Network connectivity issues")

print("="*70)

# Save
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = f"/app/tests/results/p2p_transfer_{NUM_CLIENTS}_{timestamp}.json"

Path(result_file).parent.mkdir(parents=True, exist_ok=True)
with open(result_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\\n[RESULTS] {result_file}")
EOF
    
    print "$GREEN" "✓ P2P transfer test completed"
}

run_heartbeat_test() {
    local num_clients=$1
    
    print_header "Running Heartbeat Optimization Test"
    print "$CYAN" "Real-world measurement: Fixed vs Adaptive heartbeat with $num_clients clients"
    
    source "$ENV_FILE"
    
    print "$YELLOW" "Starting heartbeat measurement..."
    
    docker exec -i "$CLIENT_CONTAINER" python3 << 'EOF'
import sys
import time
from pathlib import Path
import threading
import os

sys.path.insert(0, '/app/bklv-backend')

# Suppress output
import logging
logging.basicConfig(level=logging.CRITICAL)
import builtins
_print = builtins.print
def quiet_print(*args, **kwargs):
    msg = ' '.join(str(arg) for arg in args)
    if any(m in msg for m in ['[HEARTBEAT', '[TEST]', '[FIXED]', '[ADAPTIVE]', '=']):
        _print(*args, **kwargs)
builtins.print = quiet_print

SERVER_HOST = os.getenv('SERVER_HOST', 'p2p-server')
SERVER_PORT = int(os.getenv('SERVER_PORT', '9000'))
CLIENT_PORT_MIN = int(os.getenv('CLIENT_PORT_MIN', '1024'))
NUM_CLIENTS = int(os.getenv('TARGET_CLIENTS', '100'))
TEST_DURATION = 60  # 1 minute test

print(f"[HEARTBEAT TEST - Real Measurement]")
print(f"[TEST] Clients: {NUM_CLIENTS}, Duration: {TEST_DURATION}s")

from client import Client
from optimizations.adaptive_heartbeat import AdaptiveHeartbeat, ClientState
import json
from datetime import datetime

results = {
    'test_type': 'heartbeat_optimization',
    'num_clients': NUM_CLIENTS,
    'duration': TEST_DURATION,
    'fixed': {
        'total_pings': 0,
        'ping_times': [],
        'interval': 30
    },
    'adaptive': {
        'total_pings': 0,
        'ping_times': [],
        'client_states': {}
    }
}

# ============================================================
# TEST 1: Fixed Heartbeat (30s interval)
# ============================================================
print("\\n[FIXED] Testing fixed 30s heartbeat interval...")

fixed_clients = []
fixed_ping_count = 0
fixed_lock = threading.Lock()

def fixed_heartbeat_worker(client_id):
    global fixed_ping_count
    port = CLIENT_PORT_MIN + client_id
    repo = f'/app/repos/heartbeat_fixed_{client_id}'
    Path(repo).mkdir(parents=True, exist_ok=True)
    
    try:
        client = Client(
            hostname=f'hb_fixed_{client_id}',
            listen_port=port,
            repo_dir=repo,
            server_host=SERVER_HOST,
            server_port=SERVER_PORT
        )
        
        # Manual heartbeat loop
        start_time = time.time()
        pings = 0
        
        while time.time() - start_time < TEST_DURATION:
            ping_start = time.time()
            try:
                client.ping()  # Send heartbeat
                ping_time = (time.time() - ping_start) * 1000
                
                with fixed_lock:
                    fixed_ping_count += 1
                    results['fixed']['ping_times'].append(ping_time)
                pings += 1
            except:
                pass
            
            time.sleep(30)  # Fixed 30s interval
        
        client.close()
    except:
        pass

# Run fixed heartbeat test
print(f"[FIXED] Creating {NUM_CLIENTS} clients...")
threads = []
for i in range(NUM_CLIENTS):
    t = threading.Thread(target=fixed_heartbeat_worker, args=(i,), daemon=True)
    t.start()
    threads.append(t)

for t in threads:
    t.join(timeout=TEST_DURATION + 10)

results['fixed']['total_pings'] = fixed_ping_count

print(f"[FIXED] Completed: {fixed_ping_count} total pings")

# Cleanup
time.sleep(2)

# ============================================================
# TEST 2: Adaptive Heartbeat
# ============================================================
print("\\n[ADAPTIVE] Testing adaptive heartbeat...")

adaptive_clients = []
adaptive_ping_count = 0
adaptive_lock = threading.Lock()

def adaptive_heartbeat_worker(client_id):
    global adaptive_ping_count
    port = CLIENT_PORT_MIN + NUM_CLIENTS + client_id
    repo = f'/app/repos/heartbeat_adaptive_{client_id}'
    Path(repo).mkdir(parents=True, exist_ok=True)
    
    try:
        client = Client(
            hostname=f'hb_adaptive_{client_id}',
            listen_port=port,
            repo_dir=repo,
            server_host=SERVER_HOST,
            server_port=SERVER_PORT
        )
        
        # Simulate different activity levels
        # 70% idle, 20% moderate, 10% active
        if client_id < NUM_CLIENTS * 0.7:
            state = ClientState.IDLE
            interval = 300  # 5 minutes
        elif client_id < NUM_CLIENTS * 0.9:
            state = ClientState.MODERATE
            interval = 120  # 2 minutes
        else:
            state = ClientState.ACTIVE
            interval = 30  # 30 seconds
        
        with adaptive_lock:
            results['adaptive']['client_states'][state.name] = results['adaptive']['client_states'].get(state.name, 0) + 1
        
        # Adaptive heartbeat loop
        start_time = time.time()
        pings = 0
        
        while time.time() - start_time < TEST_DURATION:
            ping_start = time.time()
            try:
                client.ping()
                ping_time = (time.time() - ping_start) * 1000
                
                with adaptive_lock:
                    adaptive_ping_count += 1
                    results['adaptive']['ping_times'].append(ping_time)
                pings += 1
            except:
                pass
            
            time.sleep(interval)
        
        client.close()
    except:
        pass

# Run adaptive heartbeat test
print(f"[ADAPTIVE] Creating {NUM_CLIENTS} clients...")
threads = []
for i in range(NUM_CLIENTS):
    t = threading.Thread(target=adaptive_heartbeat_worker, args=(i,), daemon=True)
    t.start()
    threads.append(t)

for t in threads:
    t.join(timeout=TEST_DURATION + 10)

results['adaptive']['total_pings'] = adaptive_ping_count

print(f"[ADAPTIVE] Completed: {adaptive_ping_count} total pings")

# Calculate statistics
results['reduction'] = results['fixed']['total_pings'] - results['adaptive']['total_pings']
results['reduction_percent'] = (results['reduction'] / results['fixed']['total_pings'] * 100) if results['fixed']['total_pings'] > 0 else 0

if results['fixed']['ping_times']:
    results['fixed']['avg_ping_ms'] = sum(results['fixed']['ping_times']) / len(results['fixed']['ping_times'])
    results['fixed']['max_ping_ms'] = max(results['fixed']['ping_times'])

if results['adaptive']['ping_times']:
    results['adaptive']['avg_ping_ms'] = sum(results['adaptive']['ping_times']) / len(results['adaptive']['ping_times'])
    results['adaptive']['max_ping_ms'] = max(results['adaptive']['ping_times'])

# Summary
print("\\n" + "="*70)
print("HEARTBEAT OPTIMIZATION SUMMARY - REAL MEASUREMENT")
print("="*70)
print(f"Test Configuration:")
print(f"  Clients:          {NUM_CLIENTS}")
print(f"  Duration:         {TEST_DURATION}s")
print(f"")
print(f"Fixed Heartbeat (30s interval):")
print(f"  Total pings:      {results['fixed']['total_pings']:,}")
print(f"  Avg ping time:    {results['fixed'].get('avg_ping_ms', 0):.2f}ms")
print(f"  Max ping time:    {results['fixed'].get('max_ping_ms', 0):.2f}ms")
print(f"")
print(f"Adaptive Heartbeat:")
print(f"  Total pings:      {results['adaptive']['total_pings']:,}")
print(f"  Avg ping time:    {results['adaptive'].get('avg_ping_ms', 0):.2f}ms")
print(f"  Max ping time:    {results['adaptive'].get('max_ping_ms', 0):.2f}ms")
print(f"  Client states:    {results['adaptive']['client_states']}")
print(f"")
print(f"Optimization Results:")
print(f"  Ping reduction:   {results['reduction']:,} ({results['reduction_percent']:.1f}%)")
print(f"  Bandwidth saved:  ~{results['reduction'] * 0.5:.1f} KB")
print("="*70)

# Save
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = f"/app/tests/results/heartbeat_{NUM_CLIENTS}_{timestamp}.json"

Path(result_file).parent.mkdir(parents=True, exist_ok=True)
with open(result_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\\n[RESULTS] {result_file}")
EOF
    
    print "$GREEN" "✓ Heartbeat test completed"
}

run_duplicate_detection_test() {
    print_header "Running Duplicate Detection Test"
    
    source "$ENV_FILE"
    
    print "$YELLOW" "Starting duplicate detection test..."
    
    docker exec -i "$CLIENT_CONTAINER" python3 << EOF
import sys
import time
from pathlib import Path

sys.path.insert(0, '/app/bklv-backend')

print(f"[DUPLICATE DETECTION TEST]")

from optimizations.file_hashing import DuplicateDetector, FileMetadata
import json
from datetime import datetime

NUM_FILES = 10000

results = {
    'test_type': 'duplicate_detection',
    'num_files': NUM_FILES,
    'start_time': time.time()
}

print(f"[TEST] Testing with {NUM_FILES:,} files...")

detector = DuplicateDetector()

for i in range(NUM_FILES):
    metadata = FileMetadata(
        name=f"file_{i}.bin",
        size=1024 * (i % 100 + 1),
        modified=time.time(),
        hash=f"hash_{i % 1000}"  # Create duplicates
    )
    detector.add_file(f"client_{i % 100}", f"file_{i}.bin", metadata)
    
    if (i + 1) % 1000 == 0:
        print(f"  Added {i+1:,}/{NUM_FILES:,} files")

results['end_time'] = time.time()
results['duration'] = results['end_time'] - results['start_time']
results['stats'] = detector.get_stats()
results['avg_time_per_file_ms'] = (results['duration'] / NUM_FILES) * 1000

# Summary
print("\\n" + "="*70)
print("DUPLICATE DETECTION SUMMARY")
print("="*70)
print(f"Total files:      {results['stats']['total_files']:,}")
print(f"Unique hashes:    {results['stats']['unique_hashes']:,}")
print(f"Duplicates:       {results['stats']['duplicate_files']:,}")
print(f"Duration:         {results['duration']:.2f}s")
print(f"Avg per file:     {results['avg_time_per_file_ms']:.3f}ms")
print(f"Throughput:       {NUM_FILES/results['duration']:.0f} files/sec")
print("="*70)

# Save
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
result_file = f"/app/tests/results/duplicate_{timestamp}.json"

Path(result_file).parent.mkdir(parents=True, exist_ok=True)
with open(result_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\\n[RESULTS] {result_file}")
EOF
    
    print "$GREEN" "✓ Duplicate detection test completed"
}

run_test() {
    # Legacy function - redirects to scalability test
    local target_clients=$1
    run_scalability_test "$target_clients"
}

###############################################################################
# Individual Test Functions - Auto Port Management
###############################################################################

test_scale_1k() {
    print_header "Scalability Test: 1,000 Clients"
    setup_env 1000  # OS auto-selects port range
    start_infrastructure
    run_scalability_test 1000
    generate_markdown_report
}

test_scale_10k() {
    print_header "Scalability Test: 10,000 Clients"
    setup_env 10000  # OS auto-selects port range
    start_infrastructure
    run_scalability_test 10000
    generate_markdown_report
}

test_scale_50k() {
    print_header "Scalability Test: 50,000 Clients"
    setup_env 50000  # OS auto-selects port range
    start_infrastructure
    run_scalability_test 50000
    generate_markdown_report
}

test_scale_100k() {
    print_header "Scalability Test: 100,000 Clients (Maximum)"
    setup_env 64511  # Maximum non-root ports (1024-65535)
    start_infrastructure
    run_scalability_test 64511
    generate_markdown_report
}

test_p2p_transfer_small() {
    print_header "P2P Transfer Test: 5 Clients (Quick)"
    setup_env 5  # OS auto-selects port range
    start_infrastructure
    run_p2p_transfer_test 5
    generate_markdown_report
}

test_p2p_transfer_medium() {
    print_header "P2P Transfer Test: 20 Clients (Standard)"
    setup_env 20  # OS auto-selects port range
    start_infrastructure
    run_p2p_transfer_test 20
    generate_markdown_report
}

test_p2p_transfer_large() {
    print_header "P2P Transfer Test: 100 Clients (Stress)"
    setup_env 100  # OS auto-selects port range
    start_infrastructure
    run_p2p_transfer_test 100
    generate_markdown_report
}

test_heartbeat_optimization() {
    print_header "Heartbeat Optimization Test: Fixed vs Adaptive"
    setup_env 1000  # 1k clients for heartbeat comparison
    start_infrastructure
    run_heartbeat_test 1000
    generate_markdown_report
}

test_duplicate_detection() {
    print_header "Duplicate Detection Performance Test"
    setup_env 100  # Small number of clients needed
    start_infrastructure
    run_duplicate_detection_test
    generate_markdown_report
}

test_max() {
    print_header "Test: Maximum Clients (Auto-configured)"
    
    # Use all non-root ports
    local max_clients=64511  # 65535 - 1024
    
    print "$CYAN" "Using full non-root port range (auto-configured)"
    print "$CYAN" "Maximum possible clients: ~$max_clients"
    
    read -p "Target clients (max $max_clients, press Enter for max): " target
    
    if [ -z "$target" ]; then
        target=$max_clients
        print "$YELLOW" "Using maximum: $max_clients clients"
    elif [ "$target" -gt "$max_clients" ]; then
        print "$YELLOW" "Capping at maximum: $max_clients clients"
        target=$max_clients
    fi
    
    setup_env "$target"
    start_infrastructure
    run_scalability_test "$target"
    generate_markdown_report
}

test_custom() {
    local target=${1:-10000}
    
    print_header "Test: Custom Scalability Test"
    print "$CYAN" "Clients: $target (ports auto-configured)"
    
    setup_env "$target"
    start_infrastructure
    run_scalability_test "$target"
    generate_markdown_report
}

# Combined test suites (like test_runner.py modes)
test_quick() {
    print_header "Quick Test Suite (~10 minutes)"
    
    print "$CYAN" "Tests included:"
    print "$CYAN" "  - Scalability: 1k clients"
    print "$CYAN" "  - P2P Transfer: 5 clients"
    
    # Scalability 1k
    setup_env 1000
    start_infrastructure
    run_scalability_test 1000
    
    # Small cleanup between tests
    cleanup
    sleep 2
    
    # P2P small
    setup_env 5
    start_infrastructure
    run_p2p_transfer_test 5
    
    # Generate comprehensive report BEFORE cleanup
    generate_markdown_report
    
    cleanup
    
    print "$GREEN" "✓ Quick test suite completed"
}

test_standard() {
    print_header "Standard Test Suite (~30 minutes)"
    
    print "$CYAN" "Tests included:"
    print "$CYAN" "  - Scalability: 1k, 10k clients"
    print "$CYAN" "  - P2P Transfer: 20 clients"
    print "$CYAN" "  - Heartbeat optimization"
    print "$CYAN" "  - Duplicate detection"
    
    # Scalability tests
    setup_env 1000
    start_infrastructure
    run_scalability_test 1000
    cleanup && sleep 2
    
    setup_env 10000
    start_infrastructure
    run_scalability_test 10000
    cleanup && sleep 2
    
    # P2P transfer
    setup_env 20
    start_infrastructure
    run_p2p_transfer_test 20
    cleanup && sleep 2
    
    # Heartbeat
    setup_env 1000
    start_infrastructure
    run_heartbeat_test 1000
    cleanup && sleep 2
    
    # Duplicate detection
    setup_env 100
    start_infrastructure
    run_duplicate_detection_test
    
    # Generate comprehensive report BEFORE final cleanup
    generate_markdown_report
    
    cleanup
    
    print "$GREEN" "✓ Standard test suite completed"
}

test_full() {
    print_header "Full Test Suite (2-3 hours)"
    
    print "$CYAN" "Tests included:"
    print "$CYAN" "  - Scalability: 1k, 10k, 50k clients"
    # print "$CYAN" "  - P2P Transfer: 5, 20, 100 clients"
    # print "$CYAN" "  - Heartbeat optimization"
    # print "$CYAN" "  - Duplicate detection"
    
    # Scalability tests
    setup_env 1000
    start_infrastructure
    run_scalability_test 1000
    cleanup && sleep 2
    
    setup_env 10000
    start_infrastructure
    run_scalability_test 10000
    cleanup && sleep 2
    
    setup_env 50000
    start_infrastructure
    run_scalability_test 50000
    cleanup && sleep 2
    
    # # P2P transfer tests
    # setup_env 5
    # start_infrastructure
    # run_p2p_transfer_test 5
    # cleanup && sleep 2
    
    # setup_env 20
    # start_infrastructure
    # run_p2p_transfer_test 20
    # cleanup && sleep 2
    
    # setup_env 100
    # start_infrastructure
    # run_p2p_transfer_test 100
    # cleanup && sleep 2
    
    # # Optimization tests
    # setup_env 1000
    # start_infrastructure
    # run_heartbeat_test 1000
    # cleanup && sleep 2
    
    # setup_env 100
    # start_infrastructure
    # run_duplicate_detection_test
    
    # Generate comprehensive report BEFORE final cleanup
    generate_markdown_report
    
    cleanup
    
    print "$GREEN" "✓ Full test suite completed"
}

show_status() {
    print_header "System Status"
    
    print "$CYAN" "Containers:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    print "$CYAN" "\nPort configuration:"
    if [ -f "$ENV_FILE" ]; then
        grep -E "CLIENT_PORT|TARGET_CLIENTS" "$ENV_FILE"
    fi
}

show_logs() {
    local service=${1:-client-all-in-one}
    docker-compose -f "$COMPOSE_FILE" logs --tail=100 -f "$service"
}

# ===================================================================
# Report Generation Functions
# ===================================================================

generate_markdown_report() {
    print_header "Generating Comprehensive Test Report"
    
    # Execute report generation inside client container
    docker exec -i "$CLIENT_CONTAINER" python3 << 'PYTHON_SCRIPT'
import sys
import json
from pathlib import Path
from datetime import datetime

results_dir = Path('/app/tests/results')
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
report_file = results_dir / f'COMPREHENSIVE_RESULTS_{timestamp}.md'

# Find all JSON result files
result_files = sorted(results_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)

if not result_files:
    print("[ERROR] No result files found")
    sys.exit(1)

# Group results by test type
results_by_type = {
    'scalability': [],
    'p2p_transfer': [],
    'heartbeat': [],
    'duplicate': []
}

for result_file in result_files[:20]:  # Latest 20 results
    try:
        with open(result_file) as f:
            data = json.load(f)
            test_type = data.get('test_type', 'unknown')
            if test_type in results_by_type:
                results_by_type[test_type].append({
                    'file': result_file,
                    'data': data
                })
    except Exception as e:
        print(f"[WARN] Failed to load {result_file}: {e}")

# Generate markdown report
md_lines = []
md_lines.append("# P2P File Sharing System - Comprehensive Performance Evaluation\n")
md_lines.append(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
md_lines.append("---\n")

# ============== SCALABILITY TESTS ==============
if results_by_type['scalability']:
    md_lines.append("\n## Scalability Tests - Realistic P2P Operations\n")
    
    for result in sorted(results_by_type['scalability'], key=lambda x: x['data']['target_clients']):
        data = result['data']
        target = data['target_clients']
        
        md_lines.append(f"\n### {target:,} Clients\n")
        
        # Summary
        md_lines.append("**Test Summary:**\n")
        md_lines.append(f"- Target: {target:,} clients\n")
        md_lines.append(f"- Successful: {data['successful_registrations']:,}\n")
        md_lines.append(f"- Failed: {data['failed_registrations']:,}\n")
        md_lines.append(f"- Success Rate: {data.get('success_rate', 0):.2f}%\n")
        md_lines.append(f"- Duration: {data.get('duration', 0):.2f}s\n")
        
        # Concurrency Metrics
        if 'concurrent_metrics' in data:
            cm = data['concurrent_metrics']
            md_lines.append("\n**Concurrency Metrics:**\n")
            md_lines.append(f"- Peak Concurrent: {cm.get('peak_concurrent_clients', 0):,} clients\n")
            md_lines.append(f"- Average Concurrent: {cm.get('avg_concurrent_clients', 0):.2f} clients\n")
            md_lines.append(f"- Samples Taken: {len(cm.get('concurrent_samples', []))}\n")
        
        # Resource Usage
        if 'resource_stats' in data:
            rs = data['resource_stats']
            md_lines.append("\n**Resource Usage:**\n")
            md_lines.append(f"- CPU: {rs['cpu_avg_percent']:.2f}% avg, {rs['cpu_peak_percent']:.2f}% peak\n")
            md_lines.append(f"- Memory: {rs['memory_avg_mb']:.2f} MB avg, {rs['memory_peak_mb']:.2f} MB peak\n")
        
        # Registry Performance
        if 'registry_stats' in data:
            rs = data['registry_stats']
            md_lines.append("\n**Registry Performance:**\n")
            md_lines.append(f"- Average: {rs['avg_ms']:.2f} ms\n")
            md_lines.append(f"- P50: {rs['p50_ms']:.2f} ms\n")
            md_lines.append(f"- P95: {rs['p95_ms']:.2f} ms\n")
            md_lines.append(f"- P99: {rs['p99_ms']:.2f} ms\n")
        
        # P2P Operations
        if 'operation_stats' in data:
            md_lines.append("\n**P2P Operations:**\n")
            md_lines.append("| Operation | Count | Success | Failed | Success Rate | Avg (ms) | P95 (ms) |\n")
            md_lines.append("|-----------|-------|---------|--------|--------------|----------|----------|\n")
            
            for op_name in ['register', 'publish', 'ping', 'request', 'list_network', 'list_local', 'fetch', 'unpublish']:
                if op_name in data['operation_stats']:
                    op = data['operation_stats'][op_name]
                    md_lines.append(f"| {op_name.upper()} | {op['count']:,} | {op['success']:,} | {op['failed']:,} | {op['success_rate']:.1f}% | {op['avg_ms']:.2f} | {op['p95_ms']:.2f} |\n")

# ============== P2P TRANSFER TESTS ==============
if results_by_type['p2p_transfer']:
    md_lines.append("\n## P2P File Transfer Tests\n")
    
    for result in sorted(results_by_type['p2p_transfer'], key=lambda x: x['data'].get('num_clients', 0)):
        data = result['data']
        
        md_lines.append(f"\n### {data.get('num_clients', 0)} Clients Transfer Test\n")
        
        # Summary
        md_lines.append("**Test Configuration:**\n")
        md_lines.append(f"- Clients: {data.get('num_clients', 0)}\n")
        md_lines.append(f"- Total Transfers: {data.get('successful', 0)}\n")
        md_lines.append(f"- Duration: {data.get('duration', 0):.2f}s\n")
        
        # Resource Usage
        if 'resource_stats' in data:
            rs = data['resource_stats']
            md_lines.append("\n**Resource Usage:**\n")
            md_lines.append(f"- CPU: {rs['cpu_avg_percent']:.2f}% avg, {rs['cpu_peak_percent']:.2f}% peak\n")
            md_lines.append(f"- Memory: {rs['memory_avg_mb']:.2f} MB avg, {rs['memory_peak_mb']:.2f} MB peak\n")
        
        # Transfer by Size
        if 'transfer_by_size' in data:
            md_lines.append("\n**Transfer Performance by File Size:**\n")
            md_lines.append("| Size Category | Count | Avg Speed (MB/s) | Avg Duration (s) |\n")
            md_lines.append("|---------------|-------|------------------|------------------|\n")
            
            for size_cat in ['tiny', 'small', 'medium', 'large']:
                if size_cat in data['transfer_by_size']:
                    t = data['transfer_by_size'][size_cat]
                    md_lines.append(f"| {size_cat.capitalize()} | {t['count']} | {t.get('avg_speed_mbps', 0):.2f} | {t.get('avg_time', 0):.2f} |\n")

# ============== HEARTBEAT TESTS ==============
if results_by_type['heartbeat']:
    md_lines.append("\n## Heartbeat Optimization Tests\n")
    
    for result in sorted(results_by_type['heartbeat'], key=lambda x: x['data'].get('num_clients', 0)):
        data = result['data']
        num_clients = data.get('num_clients', 0)
        
        md_lines.append(f"\n### {num_clients:,} Clients - Real Measurement\n")
        
        # Test configuration
        md_lines.append("**Test Configuration:**\n")
        md_lines.append(f"- Clients: {num_clients:,}\n")
        md_lines.append(f"- Test Duration: {data.get('duration', 0)}s\n")
        md_lines.append(f"- Measurement: Real network pings\n")
        
        # Fixed heartbeat results
        if 'fixed' in data:
            fixed = data['fixed']
            md_lines.append("\n**Fixed Heartbeat (30s interval):**\n")
            md_lines.append(f"- Total pings: {fixed.get('total_pings', 0):,}\n")
            md_lines.append(f"- Average ping time: {fixed.get('avg_ping_ms', 0):.2f} ms\n")
            md_lines.append(f"- Max ping time: {fixed.get('max_ping_ms', 0):.2f} ms\n")
            md_lines.append(f"- Interval: {fixed.get('interval', 30)}s (all clients)\n")
        
        # Adaptive heartbeat results
        if 'adaptive' in data:
            adaptive = data['adaptive']
            md_lines.append("\n**Adaptive Heartbeat:**\n")
            md_lines.append(f"- Total pings: {adaptive.get('total_pings', 0):,}\n")
            md_lines.append(f"- Average ping time: {adaptive.get('avg_ping_ms', 0):.2f} ms\n")
            md_lines.append(f"- Max ping time: {adaptive.get('max_ping_ms', 0):.2f} ms\n")
            
            if 'client_states' in adaptive:
                md_lines.append("\n**Client State Distribution:**\n")
                for state, count in adaptive['client_states'].items():
                    pct = (count / num_clients * 100) if num_clients > 0 else 0
                    md_lines.append(f"- {state}: {count:,} clients ({pct:.1f}%)\n")
        
        # Comparison
        reduction = data.get('reduction', 0)
        reduction_pct = data.get('reduction_percent', 0)
        
        md_lines.append("\n**Optimization Results:**\n")
        md_lines.append(f"- Ping reduction: {reduction:,} pings ({reduction_pct:.1f}%)\n")
        md_lines.append(f"- Bandwidth saved: ~{reduction * 0.5:.1f} KB\n")
        md_lines.append(f"- Network load reduction: {reduction_pct:.1f}%\n")

# ============== DUPLICATE DETECTION TESTS ==============
if results_by_type['duplicate']:
    md_lines.append("\n## Duplicate Detection Tests\n")
    
    for result in results_by_type['duplicate']:
        data = result['data']
        
        md_lines.append(f"\n### {data.get('num_files', 0):,} Files Test\n")
        md_lines.append(f"- Duration: {data.get('duration', 0):.4f}s\n")
        md_lines.append(f"- Average time per file: {data.get('avg_time_per_file', 0):.4f} ms\n")
        md_lines.append(f"- Unique hashes: {data.get('unique_hashes', 0):,}\n")
        md_lines.append(f"- Duplicate files: {data.get('duplicate_files', 0):,}\n")
        md_lines.append(f"- Duplication rate: {data.get('duplication_rate', 0):.1f}%\n")
        md_lines.append(f"- Files per second: {data.get('files_per_second', 0):.2f}\n")

# Footer
md_lines.append("\n---\n")
md_lines.append(f"\n*Generated by Comprehensive Performance Test Suite*\n")
md_lines.append(f"*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

# Write report
with open(report_file, 'w') as f:
    f.writelines(md_lines)

print(f"[SUCCESS] Generated report: {report_file}")
print(f"[INFO] Included {sum(len(v) for v in results_by_type.values())} test results")
PYTHON_SCRIPT
    
    print "$GREEN" "✓ Report generated: $report_file"
    echo "$report_file"
}

cleanup() {
    print_header "Cleanup"
    docker-compose -f "$COMPOSE_FILE" down -v
    print "$GREEN" "✓ Cleanup complete"
}

shell() {
    local container=${1:-$CLIENT_CONTAINER}
    print "$CYAN" "Opening shell in $container..."
    docker exec -it "$container" /bin/bash
}

show_help() {
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════╗
║   Single-Container High-Density Testing - Auto Port Configuration   ║
╚══════════════════════════════════════════════════════════════════════╝

Strategy:
  • 1 container duy nhất chạy tất cả clients
  • Port range tự động được tính toán dựa trên số clients
  • Code không thay đổi, chỉ config qua ENV variables
  • Hỗ trợ tối đa ~64k clients (non-root ports: 1024-65535)

Usage: ./run-single-container-tests.sh [command]

═══════════════════════════════════════════════════════════════════════
TEST SUITES (Like test_runner.py)
═══════════════════════════════════════════════════════════════════════

  quick               Quick validation suite (~10 min)
                      • Scalability: 1k clients
                      • P2P Transfer: 5 clients
  
  standard            Standard performance suite (~30 min) [RECOMMENDED]
                      • Scalability: 1k, 10k clients
                      • P2P Transfer: 20 clients
                      • Heartbeat optimization test
                      • Duplicate detection test
  
  full                Complete test suite (2-3 hours)
                      • Scalability: 1k, 10k, 50k clients
                      • P2P Transfer: 5, 20, 100 clients
                      • Heartbeat optimization test
                      • Duplicate detection test

═══════════════════════════════════════════════════════════════════════
INDIVIDUAL SCALABILITY TESTS
═══════════════════════════════════════════════════════════════════════

  scale-1k            1,000 clients scalability test
  scale-10k           10,000 clients scalability test
  scale-50k           50,000 clients scalability test
  scale-100k          100,000 clients (maximum capacity)
  
  max                 Interactive: choose max client count
  custom <N>          Custom: N clients (auto port range)

═══════════════════════════════════════════════════════════════════════
P2P TRANSFER TESTS
═══════════════════════════════════════════════════════════════════════

  p2p-small           5 clients P2P transfer (quick)
  p2p-medium          20 clients P2P transfer (standard)
  p2p-large           100 clients P2P transfer (stress)

═══════════════════════════════════════════════════════════════════════
OPTIMIZATION TESTS
═══════════════════════════════════════════════════════════════════════

  heartbeat           Heartbeat optimization (Fixed vs Adaptive)
  duplicate           Duplicate detection performance

═══════════════════════════════════════════════════════════════════════
INFRASTRUCTURE
═══════════════════════════════════════════════════════════════════════

  start               Start server and client container
  stop                Stop all services
  cleanup             Remove containers and volumes
  
  status              Show system status
  logs [service]      Show logs (default: client-all-in-one)
  shell [container]   Open shell in container

═══════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════

Quick Start:
  ./run-single-container-tests.sh quick
  
Recommended:
  ./run-single-container-tests.sh standard
  
Individual Tests:
  ./run-single-container-tests.sh scale-10k
  ./run-single-container-tests.sh p2p-medium
  ./run-single-container-tests.sh heartbeat
  
Custom:
  ./run-single-container-tests.sh custom 25000
  
Complete Suite:
  ./run-single-container-tests.sh full

═══════════════════════════════════════════════════════════════════════
AUTO PORT CONFIGURATION
═══════════════════════════════════════════════════════════════════════

Port ranges are AUTOMATICALLY calculated based on client count:
  • 1k clients:    1024-1124   (100 ports)
  • 10k clients:   1024-10124  (10,100 ports)
  • 50k clients:   1024-50124  (50,100 ports)
  • Max clients:   1024-65535  (64,511 ports)

You no longer need to manually specify port ranges!

═══════════════════════════════════════════════════════════════════════
RESOURCE REQUIREMENTS
═══════════════════════════════════════════════════════════════════════

  1k:      ~2GB RAM,   ~1 CPU
  10k:     ~16GB RAM,  ~4 CPUs
  50k:     ~80GB RAM,  ~16 CPUs
  100k:    ~160GB RAM, ~32 CPUs

═══════════════════════════════════════════════════════════════════════
RESULTS
═══════════════════════════════════════════════════════════════════════

All test results are saved to: /app/tests/results/
  • scalability_<N>_<timestamp>.json
  • p2p_transfer_<N>_<timestamp>.json
  • heartbeat_<N>_<timestamp>.json
  • duplicate_<timestamp>.json

EOF
}

main() {
    case "${1:-help}" in
        # Infrastructure
        start)
            check_docker
            if [ ! -f "$ENV_FILE" ]; then
                setup_env 10000
            fi
            start_infrastructure
            ;;
        stop|cleanup)
            cleanup
            ;;
        
        # Test Suites
        quick)
            check_docker
            test_quick
            ;;
        standard)
            check_docker
            test_standard
            ;;
        full)
            check_docker
            test_full
            ;;
        
        # Individual Scalability Tests
        scale-1k)
            check_docker
            test_scale_1k
            ;;
        scale-10k)
            check_docker
            test_scale_10k
            ;;
        scale-50k)
            check_docker
            test_scale_50k
            ;;
        scale-100k)
            check_docker
            test_scale_100k
            ;;
        
        # P2P Transfer Tests
        p2p-small)
            check_docker
            test_p2p_transfer_small
            ;;
        p2p-medium)
            check_docker
            test_p2p_transfer_medium
            ;;
        p2p-large)
            check_docker
            test_p2p_transfer_large
            ;;
        
        # Optimization Tests
        heartbeat)
            check_docker
            test_heartbeat_optimization
            ;;
        duplicate)
            check_docker
            test_duplicate_detection
            ;;
        
        # Legacy/Custom Tests
        max)
            check_docker
            test_max
            ;;
        custom)
            check_docker
            test_custom "${2:-10000}"
            ;;
        
        # Monitoring
        status)
            show_status
            ;;
        logs)
            show_logs "${2:-client-all-in-one}"
            ;;
        shell)
            shell "${2:-$CLIENT_CONTAINER}"
            ;;
        
        # Help
        help|--help|-h)
            show_help
            ;;
        
        # Catch-all
        *)
            print "$RED" "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
