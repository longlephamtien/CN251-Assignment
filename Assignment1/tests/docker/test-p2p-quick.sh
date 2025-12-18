#!/bin/bash
###############################################################################
# Quick P2P Transfer Test - Diagnostic Mode
# Tests basic P2P functionality with verbose output
###############################################################################

set -e

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Quick P2P Transfer Diagnostic Test${NC}"
echo -e "${BLUE}========================================${NC}"

# Use the single-container setup
COMPOSE_FILE="docker-compose.single-container.yml"
ENV_FILE=".env.single"

# Create minimal environment
cat > "$ENV_FILE" << EOF
TARGET_CLIENTS=5
CLIENT_PORT_MIN=10000
CLIENT_PORT_MAX=10100
SERVER_CPU_LIMIT=2.0
SERVER_MEMORY_LIMIT=4G
CLIENT_CPU_LIMIT=4.0
CLIENT_MEMORY_LIMIT=8G
CLIENT_CPU_RESERVATION=1.0
CLIENT_MEMORY_RESERVATION=2G
TEST_TIMEOUT=300
EOF

echo -e "${GREEN}✓ Created environment file${NC}"

# Start services
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

# Wait for server
echo -e "${YELLOW}Waiting for server...${NC}"
sleep 5

# Run diagnostic test
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running P2P Transfer Test${NC}"
echo -e "${BLUE}========================================${NC}"

docker exec -i p2p-client-allinone python3 << 'PYTHON_TEST'
import sys
import time
from pathlib import Path
import shutil

sys.path.insert(0, '/app/bklv-backend')

print("\n[DIAGNOSTIC] P2P Transfer Test")
print("="*70)

from client import Client

# Check test files
TEST_FILES_DIR = Path('/app/files')
print(f"\n[CHECK] Test files directory: {TEST_FILES_DIR}")
print(f"[CHECK] Directory exists: {TEST_FILES_DIR.exists()}")

if TEST_FILES_DIR.exists():
    all_files = list(TEST_FILES_DIR.glob('*'))
    txt_files = list(TEST_FILES_DIR.glob('*.txt'))
    bin_files = list(TEST_FILES_DIR.glob('*.bin'))
    
    print(f"[CHECK] Total files: {len(all_files)}")
    print(f"[CHECK] .txt files: {len(txt_files)}")
    print(f"[CHECK] .bin files: {len(bin_files)}")
    print(f"[CHECK] Sample files: {[f.name for f in all_files[:10]]}")
    
    test_files = txt_files + bin_files
else:
    print("[ERROR] Test files directory does not exist!")
    sys.exit(1)

if not test_files:
    print("[ERROR] No test files found!")
    sys.exit(1)

# Create 2 clients
print("\n[SETUP] Creating 2 test clients...")

# Client 1 - Publisher
repo1 = '/app/repos/test_repo_1'
Path(repo1).mkdir(parents=True, exist_ok=True)

# Copy a small test file to client 1
test_file = test_files[0]
shutil.copy2(test_file, Path(repo1) / test_file.name)
print(f"[SETUP] Copied {test_file.name} to client 1")

client1 = Client(
    hostname='test_client_1',
    listen_port=10001,
    repo_dir=repo1,
    server_host='p2p-server',
    server_port=9000
)
print("[SETUP] ✓ Client 1 created and registered")

# Publish file
client1.publish(str(Path(repo1) / test_file.name))
print(f"[SETUP] ✓ Client 1 published {test_file.name}")

# Client 2 - Receiver
repo2 = '/app/repos/test_repo_2'
Path(repo2).mkdir(parents=True, exist_ok=True)

client2 = Client(
    hostname='test_client_2',
    listen_port=10002,
    repo_dir=repo2,
    server_host='p2p-server',
    server_port=9000
)
print("[SETUP] ✓ Client 2 created and registered")

# Wait a moment for server to index
print("\n[WAIT] Waiting 2 seconds for server to index files...")
time.sleep(2)

# Check if client 2 can see the file
print("\n[TEST] Checking network visibility...")
network_files = client2.list_network()
print(f"[TEST] Client 2 sees {len(network_files)} files in network")

if network_files:
    print("[TEST] Files in network:")
    for f in network_files:
        fname = f.get('name', f.get('fname', 'unknown'))
        fsize = f.get('size', 0)
        print(f"  - {fname} ({fsize} bytes)")
else:
    print("[ERROR] No files visible in network!")

# Try to fetch the file
print(f"\n[TRANSFER] Attempting to fetch {test_file.name}...")
try:
    start_time = time.time()
    client2.fetch(test_file.name)
    transfer_time = time.time() - start_time
    
    # Verify file was received
    received_file = Path(repo2) / test_file.name
    if received_file.exists():
        original_size = test_file.stat().st_size
        received_size = received_file.stat().st_size
        
        print(f"[SUCCESS] ✓ File transfer completed!")
        print(f"  Original size: {original_size} bytes")
        print(f"  Received size: {received_size} bytes")
        print(f"  Transfer time: {transfer_time:.2f} seconds")
        print(f"  Speed: {(original_size/transfer_time/1024/1024):.2f} MB/s")
        
        if original_size == received_size:
            print(f"[SUCCESS] ✓ File size matches!")
        else:
            print(f"[WARNING] File sizes don't match!")
    else:
        print(f"[ERROR] File was not saved to {received_file}")
        
except Exception as e:
    print(f"[ERROR] Transfer failed: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
client1.close()
client2.close()

print("\n" + "="*70)
print("[COMPLETE] Diagnostic test finished")
print("="*70)
PYTHON_TEST

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Stopping Services${NC}"
echo -e "${BLUE}========================================${NC}"
docker-compose -f "$COMPOSE_FILE" down

echo -e "${GREEN}✓ Test complete${NC}"
