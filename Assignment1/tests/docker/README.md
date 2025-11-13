# 🚀 Scalability Testing - Complete Guide

## TL;DR

Bạn có **3 cách** để test mà **KHÔNG cần thay đổi code**:

```bash
# 1. Original: < 1k clients
python client.py --host test1 --port 6000 --repo repo1

# 2. Single Container: 1k - 64k clients (ENV override)
./run-single-container-tests.sh 10k

# 3. Multi-Container: 10k+ clients (Docker scale)
./run-scalability-tests.sh medium
```

---

## 📚 Documentation

### Main Guides
1. **[TESTING_STRATEGIES.md](TESTING_STRATEGIES.md)** - So sánh chi tiết 3 strategies
2. **[SCALABILITY_TESTING.md](SCALABILITY_TESTING.md)** - Multi-container strategy
3. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Commands cheatsheet

### Quick Links
- [Single Container Setup](#single-container-env-override)
- [Multi-Container Setup](#multi-container-docker-scale)
- [Port Configuration](#port-configuration)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Vấn đề cần giải quyết

### Original Code Limit
```python
# config.py
CLIENT_PORT_MIN = 6000
CLIENT_PORT_MAX = 7000
# → 1,001 ports → max 1,001 clients ❌
```

### Requirement
```
✅ Test 1,000 clients
✅ Test 10,000 clients
✅ Test 100,000 clients
❌ KHÔNG được thay đổi code client.py/server.py
```

---

## 💡 Solutions

### Solution 1: Single Container (ENV Override)

**Idea:** Override port range qua environment variables

```bash
# Container được start với ENV:
docker run \
  -e CLIENT_PORT_MIN=1024 \
  -e CLIENT_PORT_MAX=65535 \
  myimage

# Code đọc từ ENV:
CLIENT_PORT_MIN = int(os.getenv('CLIENT_PORT_MIN', 6000))
CLIENT_PORT_MAX = int(os.getenv('CLIENT_PORT_MAX', 7000))
# → Code KHÔNG đổi, chỉ đọc ENV!
```

**Result:**
- ✅ Không thay đổi code
- ✅ Max ~64k clients (ports 1024-65535)
- ✅ Simple setup (1 container)

**Usage:**
```bash
cd tests/docker

# 10k clients test
./run-single-container-tests.sh 10k

# Custom: 25k clients
./run-single-container-tests.sh custom 25000
```

---

### Solution 2: Multi-Container (Network Isolation)

**Idea:** Mỗi container = isolated network namespace

```
Container 1: ports 6000-7000 (namespace 1) → 1k clients
Container 2: ports 6000-7000 (namespace 2) → 1k clients
Container N: ports 6000-7000 (namespace N) → 1k clients

Total: N × 1,000 clients
```

**Result:**
- ✅ Không thay đổi code
- ✅ Không cần ENV override
- ✅ Unlimited clients (scale containers)
- ✅ True isolation

**Usage:**
```bash
cd tests/docker

# 10k clients = 10 containers
./run-scalability-tests.sh medium

# 100k clients = 100 containers
./run-scalability-tests.sh custom 100000
```

---

## 🚀 Quick Start

### 1. Single Container (Recommended for < 64k)

```bash
cd /Users/longlephamtien/Documents/CODE/CN251-Assignment/Assignment1/tests/docker

# Test 10k clients
./run-single-container-tests.sh 10k

# Monitor
./run-single-container-tests.sh status
./run-single-container-tests.sh logs

# Results
./run-single-container-tests.sh results

# Cleanup
./run-single-container-tests.sh cleanup
```

### 2. Multi-Container (Recommended for 10k+)

```bash
cd /Users/longlephamtien/Documents/CODE/CN251-Assignment/Assignment1/tests/docker

# Test 10k clients (10 containers)
./run-scalability-tests.sh medium

# Monitor
./run-scalability-tests.sh status
./run-scalability-tests.sh logs server

# Results
./run-scalability-tests.sh results

# Cleanup
./run-scalability-tests.sh cleanup
```

---

## 📊 Comparison

### Single Container vs Multi-Container

| Feature | Single Container | Multi-Container |
|---------|------------------|-----------------|
| **Setup** | ⭐⭐⭐ Easy | ⭐⭐ Medium |
| **Max Clients** | ~64,000 | Unlimited |
| **Resources** | 1 container | N containers |
| **Isolation** | ⚠️ Partial | ✅ Full |
| **Port Range** | 1024-65535 | 6000-7000 (per container) |
| **Best For** | 1k-64k tests | 10k+ tests |

### Port Configuration

**Single Container:**
```bash
# .env.single
TARGET_CLIENTS=10000
CLIENT_PORT_MIN=1024
CLIENT_PORT_MAX=11024
# → 1 container, 10k ports
```

**Multi-Container:**
```bash
# docker-compose scale
docker-compose up --scale client-container=10
# → 10 containers × 1k ports = 10k clients
```

---

## 🔧 Port Calculation

### Single Container Formula
```python
# Needed ports
needed_ports = target_clients + 100  # +100 buffer

# Port range
CLIENT_PORT_MIN = 1024
CLIENT_PORT_MAX = CLIENT_PORT_MIN + needed_ports

# Example: 25k clients
CLIENT_PORT_MIN = 1024
CLIENT_PORT_MAX = 1024 + 25100 = 26124
```

### Multi-Container Formula
```python
# Needed containers
containers = (target_clients + 999) // 1000

# Example: 25k clients
containers = (25000 + 999) // 1000 = 25 containers

# Each container uses: ports 6000-7000 (1k ports)
# Total capacity: 25 × 1,000 = 25,000 clients
```

---

## 📈 Resource Requirements

### Single Container

| Clients | RAM | CPUs | Ports | Time |
|---------|-----|------|-------|------|
| 1k | 3GB | 1-2 | 1024-2024 | 5min |
| 10k | 20GB | 8 | 1024-11024 | 30min |
| 50k | 100GB | 32 | 1024-51024 | 2h |
| 64k (max) | 128GB | 64 | 1024-65535 | 3h |

### Multi-Container

| Clients | Containers | RAM | CPUs | Time |
|---------|-----------|-----|------|------|
| 1k | 1 | 3GB | 1 | 5min |
| 10k | 10 | 30GB | 10 | 30min |
| 50k | 50 | 150GB | 50 | 2h |
| 100k | 100 | 300GB | 100 | 4h |

---

## 🎯 Test Examples

### Example 1: Quick Test (1k clients)
```bash
# Single container with original ports
./run-single-container-tests.sh 1k

# Result:
# - 1 container
# - Ports: 6000-7000
# - Time: ~5 minutes
# - RAM: ~3GB
```

### Example 2: Medium Test (10k clients)

**Option A: Single Container**
```bash
./run-single-container-tests.sh 10k

# Result:
# - 1 container
# - Ports: 1024-11024
# - Time: ~30 minutes
# - RAM: ~20GB
```

**Option B: Multi-Container**
```bash
./run-scalability-tests.sh medium

# Result:
# - 10 containers
# - Ports: 6000-7000 (each)
# - Time: ~30 minutes
# - RAM: ~30GB
```

### Example 3: Large Test (100k clients)
```bash
# Multi-container only (single container can't handle)
./run-scalability-tests.sh custom 100000

# Result:
# - 100 containers
# - Ports: 6000-7000 (each)
# - Time: ~4 hours
# - RAM: ~300GB
```

---

## 🐛 Troubleshooting

### Problem: Port exhausted in single container

```bash
# Error
ERROR: bind() failed: Address already in use

# Solution 1: Increase port range
vim .env.single
# CLIENT_PORT_MAX=11024 → CLIENT_PORT_MAX=21024

# Solution 2: Use multi-container instead
./run-scalability-tests.sh medium
```

### Problem: Out of memory

```bash
# Check Docker resources
docker info | grep Memory

# Increase in Docker Desktop
# Settings → Resources → Memory → 32GB+

# Or reduce test size
./run-single-container-tests.sh custom 5000
```

### Problem: Container won't start

```bash
# Check logs
docker logs p2p-client-allinone
docker logs p2p-server-single

# Check if port 9000 is free
lsof -i :9000

# If in use, kill process
kill -9 $(lsof -ti :9000)
```

---

## 📂 File Structure

```
tests/docker/
├── README.md                              ← This file
├── TESTING_STRATEGIES.md                  ← Strategy comparison
├── SCALABILITY_TESTING.md                 ← Multi-container guide
├── QUICK_REFERENCE.md                     ← Command cheatsheet
│
├── docker-compose.single-container.yml    ← Single container config
├── docker-compose.scalability.yml         ← Multi-container config
│
├── run-single-container-tests.sh          ← Single container runner
├── run-scalability-tests.sh               ← Multi-container runner
│
├── Dockerfile                             ← Base image
├── Dockerfile.client                      ← Client container image
│
└── .env.single                            ← Single container ENV
```

---

## ✅ Checklist

### Before Running Tests

- [ ] Docker installed and running
- [ ] Sufficient RAM (see requirements table)
- [ ] Sufficient CPUs (see requirements table)
- [ ] Port 9000 is free
- [ ] Docker resources configured (Settings → Resources)

### For Single Container Tests

- [ ] `.env.single` file created
- [ ] `CLIENT_PORT_MIN` and `CLIENT_PORT_MAX` set correctly
- [ ] Port range sufficient for target clients

### For Multi-Container Tests

- [ ] `docker-compose.scalability.yml` exists
- [ ] Sufficient system resources for N containers
- [ ] Understanding of network isolation concept

---

## 🎓 Learning Resources

### Key Concepts

1. **Environment Variables Override**
   - Code reads from `os.getenv()`
   - Docker sets via `-e` or `environment:` in compose
   - No code changes needed

2. **Docker Network Namespaces**
   - Each container has isolated network stack
   - Same port number can be used in different containers
   - No conflicts!

3. **Port Range Calculation**
   - Single container: linear (more clients = more ports)
   - Multi-container: multiplicative (more clients = more containers)

### Further Reading

- Docker networking: https://docs.docker.com/network/
- Docker Compose: https://docs.docker.com/compose/
- Network namespaces: https://man7.org/linux/man-pages/man7/network_namespaces.7.html

---

## 🤝 Contributing

### Adding New Test Modes

1. Single container: Edit `.env.single`
2. Multi-container: Edit `docker-compose.scalability.yml`
3. Update documentation

### Reporting Issues

Include:
- Test command used
- Error messages
- System resources (RAM, CPUs)
- Docker version
- OS version

---

## 📞 Support

- Documentation: See `TESTING_STRATEGIES.md`
- Quick help: See `QUICK_REFERENCE.md`
- Technical details: See `SCALABILITY_TESTING.md`

---

**Happy Testing! 🚀**
