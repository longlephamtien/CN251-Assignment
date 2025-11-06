# P2P File Sharing - Test Suite

---

## Table of Contents

- [Test Overview](#-test-overview)
- [Quick Start](#-quick-start)
- [System Requirements](#-system-requirements)
- [Test Modes](#-test-modes)
- [Running Tests](#-running-tests)
- [Viewing Results](#-viewing-results)
- [Troubleshooting](#-troubleshooting)

---

## Test Overview

### Test Suite Components

**Test 1: Scalability Testing**
- 1,000 / 10,000 / 100,000 clients
- Measures: Latency, CPU, Memory, Network I/O
- Duration: 5 mins / 20 mins / 2+ hours

**Test 2: P2P File Transfer Performance**
- 5-20 clients, multiple file sizes (1KB to 1GB)
- Measures: Transfer speed, throughput, concurrent handling
- Duration: ~10-15 minutes

**Test 3: Heartbeat Optimization Impact**
- Fixed vs Adaptive heartbeat (100k clients simulation)
- Measures: Request reduction, CPU/Memory savings
- Duration: ~5 minutes

**Test 4: Duplicate Detection Performance**
- 10,000 files with SHA256 hashing
- Measures: Hash computation time, detection accuracy
- Duration: ~2 minutes

---

## Quick Start

### Prerequisites
```bash
# Check Docker installation
docker --version
docker-compose --version

# Verify Docker is running
docker ps
```

### Run Tests (Single Command!)
```bash
# Navigate to docker directory
cd Assignment1/tests/docker

# Quick validation test (~10 minutes)
./run-tests.sh quick

# Standard performance test (~30 minutes)
./run-tests.sh standard

# Full test suite (2-3 hours)
./run-tests.sh full

# View results
./run-tests.sh results
```

---

## System Requirements

### Software
- Docker Desktop (latest version)
- Docker Compose (included with Docker Desktop)

### Hardware (Recommended)
- **CPU:** 4+ cores
- **RAM:** 8 GB allocated to Docker
- **Disk:** 10 GB free space
- **OS:** macOS, Linux, or Windows with WSL2

### Docker Configuration
Go to Docker Desktop → Settings → Resources:
- **CPUs:** 4
- **Memory:** 8 GB
- **Swap:** 2 GB

---

## Running Tests

### Step-by-Step Guide

**1. Navigate to docker directory**
```bash
cd Assignment1/tests/docker
```

**2. Start services (automatic)**
```bash
# Services start automatically when you run tests
# Or start manually:
./run-tests.sh start
```

**3. Run your chosen test mode**
```bash
# Quick validation
./run-tests.sh quick

# Standard test (recommended)
./run-tests.sh standard

# Full test suite
./run-tests.sh full
```

**4. View results**
```bash
./run-tests.sh results
```

**5. Stop services**
```bash
./run-tests.sh stop
```

### All Available Commands

```bash
./run-tests.sh start        # Start all services
./run-tests.sh stop         # Stop all services
./run-tests.sh quick        # Quick test mode
./run-tests.sh standard     # Standard test mode
./run-tests.sh full         # Full test mode
./run-tests.sh logs         # View all logs
./run-tests.sh logs server  # View specific service logs
./run-tests.sh results      # Show test results
./run-tests.sh shell        # Open debug shell
./run-tests.sh clean        # Clean up everything
./run-tests.sh help         # Show help
```

### Manual Testing

If you want to run tests manually:

```bash
# Open shell in test container
./run-tests.sh shell

# Inside container, run specific tests:
python test_runner.py --mode quick
python test_runner.py --mode standard --server-host p2p-server
python test_suites/scalability_test.py --preset 1k
python test_suites/p2p_transfer_test.py --clients 20

# Exit container
exit
```

---

## Viewing Results

### Quick View

```bash
# View latest results
./run-tests.sh results

# View specific markdown report
cd ../results
ls -lt TEST_RESULTS_*.md | head -1 | xargs cat
```

### Result Files Location
```
tests/results/
├── test_report_quick_TIMESTAMP.json
├── test_report_standard_TIMESTAMP.json
├── test_report_full_TIMESTAMP.json
├── TEST_RESULTS_QUICK_TIMESTAMP.md
├── TEST_RESULTS_STANDARD_TIMESTAMP.md
├── TEST_RESULTS_FULL_TIMESTAMP.md
├── scalability_*_TIMESTAMP.json
├── p2p_transfer_TIMESTAMP.json
├── heartbeat_comparison_TIMESTAMP.json
└── duplicate_detection_TIMESTAMP.json
```

### Key Metrics in Results

**1. Registry Operations Latency**
- REGISTER, PUBLISH, REQUEST, LIST, DISCOVER, PING
- Average, P50, P95, P99 latencies

**2. File Transfer Performance**
- Small/Medium/Large file speeds (MB/s)
- Transfer duration
- Concurrent transfer handling

**3. Resource Utilization**
- CPU: Average/Peak usage (%)
- Memory: Average/Peak usage (MB)
- Network I/O

**4. Heartbeat Optimization**
- Total requests: Fixed vs Adaptive
- Request reduction percentage
- Resource savings estimate

**5. Duplicate Detection**
- Hash computation time per file (ms)
- Detection accuracy
- Files per second processed

### Export Results

```bash
# Copy results to Desktop
cp -r results ~/Desktop/P2P_Test_Results_$(date +%Y%m%d)

# View as JSON
cat results/test_report_standard_*.json | python -m json.tool

# View markdown
less results/TEST_RESULTS_STANDARD_*.md
```

---

## 🔧 Troubleshooting

### Docker not running
```bash
# Start Docker Desktop (macOS)
open -a Docker

# Wait 30 seconds, then verify
docker ps
```

### Services won't start
```bash
# Check what's running
docker ps -a

# View logs
./run-tests.sh logs

# Clean restart
./run-tests.sh stop
./run-tests.sh start
```

### Port already in use
```bash
# Find what's using the port
lsof -i :9000

# Kill the process
kill -9 <PID>

# Or use different port in docker-compose.yml
```

### Out of memory
```bash
# Increase Docker RAM: Docker Desktop → Settings → Resources → Memory: 8GB+

# Or run lighter test
./run-tests.sh quick
```

### Test timeout or hanging
```bash
# Check logs
./run-tests.sh logs test-runner

# Restart services
./run-tests.sh stop
./run-tests.sh start

# Try again
./run-tests.sh quick
```

### Clean Everything and Start Over
```bash
# Nuclear option - clean everything
./run-tests.sh clean

# Remove all Docker data
docker system prune -a --volumes -f

# Start fresh
./run-tests.sh start
./run-tests.sh quick
```

### Permission Issues
```bash
# Fix file permissions
sudo chown -R $(whoami) ../results ../logs
chmod -R 755 ../results ../logs
```

### Get Help
```bash
# Show all available commands
./run-tests.sh help

# Open debug shell
./run-tests.sh shell
```

---
