#!/bin/bash
# Quick Port Checker for P2P System
# Usage: ./check_ports.sh

echo "======================================"
echo "  P2P System - Port Usage Checker"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if server port is in use
echo "1️⃣  Server Port (9000):"
if lsof -i :9000 >/dev/null 2>&1 || ss -tln | grep -q :9000 2>/dev/null; then
    echo -e "   ${RED}✗ Port 9000 is IN USE${NC}"
    if command -v lsof &> /dev/null; then
        lsof -i :9000 2>/dev/null | tail -n +2
    fi
else
    echo -e "   ${GREEN}✓ Port 9000 is AVAILABLE${NC}"
fi
echo ""

# 2. Check client port range (6000-7000)
echo "2️⃣  Client Port Range (6000-7000):"
if command -v ss &> /dev/null; then
    used_ports=$(ss -tln | awk '$4 ~ /:6[0-9]{3}$/' | wc -l)
    echo -e "   Used: ${YELLOW}${used_ports}${NC} / 1001 ports"
    
    if [ $used_ports -gt 0 ]; then
        echo "   Ports in use:"
        ss -tlnp | awk '$4 ~ /:6[0-9]{3}$/ {print "   - " $4}' | head -5
        if [ $used_ports -gt 5 ]; then
            echo "   ... and $((used_ports - 5)) more"
        fi
    fi
elif command -v netstat &> /dev/null; then
    used_ports=$(netstat -tuln | grep -E ":(6[0-9]{3})" | wc -l)
    echo -e "   Used: ${YELLOW}${used_ports}${NC} / 1001 ports"
else
    echo "   ${RED}Cannot check (no ss or netstat)${NC}"
fi
echo ""

# 3. Total listening ports
echo "3️⃣  Total Listening Ports:"
if command -v ss &> /dev/null; then
    total_listen=$(ss -tln | tail -n +2 | wc -l)
    echo "   TCP LISTEN: ${total_listen}"
elif command -v netstat &> /dev/null; then
    total_listen=$(netstat -tuln | grep LISTEN | wc -l)
    echo "   TCP LISTEN: ${total_listen}"
fi
echo ""

# 4. Established connections
echo "4️⃣  Active Connections:"
if command -v ss &> /dev/null; then
    established=$(ss -tan state established | wc -l)
    time_wait=$(ss -tan state time-wait | wc -l)
    echo "   ESTABLISHED: ${established}"
    echo "   TIME_WAIT: ${time_wait}"
    
    if [ $time_wait -gt 1000 ]; then
        echo -e "   ${YELLOW}⚠️  High TIME_WAIT count - ports may be temporarily unavailable${NC}"
    fi
elif command -v netstat &> /dev/null; then
    established=$(netstat -tan | grep ESTABLISHED | wc -l)
    time_wait=$(netstat -tan | grep TIME_WAIT | wc -l)
    echo "   ESTABLISHED: ${established}"
    echo "   TIME_WAIT: ${time_wait}"
fi
echo ""

# 5. System limits
echo "5️⃣  System Limits:"

# File descriptors
if command -v ulimit &> /dev/null; then
    fd_limit=$(ulimit -n)
    echo "   File Descriptors: ${fd_limit}"
    
    if [ $fd_limit -lt 10000 ]; then
        echo -e "   ${YELLOW}⚠️  Low limit! Recommend: ulimit -n 65536${NC}"
    else
        echo -e "   ${GREEN}✓ Good limit${NC}"
    fi
fi

# Ephemeral port range
if [ -f /proc/sys/net/ipv4/ip_local_port_range ]; then
    ephemeral=$(cat /proc/sys/net/ipv4/ip_local_port_range)
    low=$(echo $ephemeral | awk '{print $1}')
    high=$(echo $ephemeral | awk '{print $2}')
    count=$((high - low + 1))
    echo "   Ephemeral Ports: ${low}-${high} (${count} ports)"
elif command -v sysctl &> /dev/null 2>&1; then
    # macOS
    low=$(sysctl -n net.inet.ip.portrange.first 2>/dev/null || echo "49152")
    high=$(sysctl -n net.inet.ip.portrange.last 2>/dev/null || echo "65535")
    count=$((high - low + 1))
    echo "   Ephemeral Ports: ${low}-${high} (${count} ports)"
fi
echo ""

# 6. Recommendations
echo "6️⃣  Recommendations:"

available_client_ports=$((1001 - used_ports))
echo "   Available client ports: ${available_client_ports}"

if [ $available_client_ports -lt 100 ]; then
    echo -e "   ${RED}✗ Low available ports!${NC}"
    echo "   → Stop unused clients or increase CLIENT_PORT_MAX"
elif [ $available_client_ports -lt 500 ]; then
    echo -e "   ${YELLOW}⚠️  Moderate available ports${NC}"
    echo "   → Monitor usage if running more clients"
else
    echo -e "   ${GREEN}✓ Good availability for testing${NC}"
fi
echo ""

# 7. Quick test - try to bind to a few ports
echo "7️⃣  Quick Port Test (sample 5 ports):"
test_ports=(6000 6100 6500 6900 7000)

for port in "${test_ports[@]}"; do
    if python3 -c "import socket; s=socket.socket(); s.bind(('',${port})); s.close()" 2>/dev/null; then
        echo -e "   Port ${port}: ${GREEN}✓ Available${NC}"
    else
        echo -e "   Port ${port}: ${RED}✗ In use${NC}"
    fi
done
echo ""

echo "======================================"
echo "  Detailed Commands:"
echo "======================================"
echo "  View all listening ports:"
echo "    ss -tuln                 (modern)"
echo "    netstat -tuln            (traditional)"
echo ""
echo "  Check specific port:"
echo "    lsof -i :9000"
echo "    ss -tlnp | grep :9000"
echo ""
echo "  Monitor in real-time:"
echo "    watch -n 1 'ss -tln | grep -E \":(6[0-9]{3}|9000)\" | wc -l'"
echo ""
echo "======================================"
