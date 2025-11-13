#!/usr/bin/env python3
"""
Test Port Limitations for P2P System
Verifies maximum concurrent clients on a single machine

Usage:
    python test_port_limits.py
"""

import socket
import sys
import time
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'bklv-backend'))

# Try to load a local config module at runtime; fall back to defaults if unavailable.
try:
    import importlib.util
    import importlib

    spec = importlib.util.find_spec("config")
    if spec is not None:
        config = importlib.import_module("config")
        CLIENT_PORT_MIN = getattr(config, "CLIENT_PORT_MIN", 6000)
        CLIENT_PORT_MAX = getattr(config, "CLIENT_PORT_MAX", 7000)
    else:
        CLIENT_PORT_MIN = 6000
        CLIENT_PORT_MAX = 7000
except Exception:
    CLIENT_PORT_MIN = 6000
    CLIENT_PORT_MAX = 7000


def test_port_availability(port_min, port_max, verbose=True):
    """
    Test how many ports are available for client peer servers
    
    Args:
        port_min: Minimum port number
        port_max: Maximum port number
        verbose: Print progress
    
    Returns:
        (available_count, used_ports, failed_ports)
    """
    sockets = []
    used_ports = []
    failed_ports = []
    
    if verbose:
        print(f"\nTesting port range {port_min}-{port_max}...")
        print(f"Range size: {port_max - port_min + 1} ports")
        print("-" * 60)
    
    for port in range(port_min, port_max + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', port))
            sock.listen(5)
            sockets.append(sock)
            used_ports.append(port)
            
            if verbose and len(sockets) % 100 == 0:
                print(f"  ✓ Created {len(sockets)} listeners...")
        
        except OSError as e:
            failed_ports.append((port, str(e)))
            if verbose:
                print(f"  ✗ Port {port} unavailable: {e}")
    
    if verbose:
        print("-" * 60)
        print(f"\n✓ Results:")
        print(f"  Available: {len(sockets)} ports")
        print(f"  Failed: {len(failed_ports)} ports")
        print(f"  Success rate: {len(sockets)/(port_max-port_min+1)*100:.1f}%")
    
    # Keep sockets open for now
    return len(sockets), sockets, failed_ports


def test_concurrent_listeners(num_listeners=1000):
    """
    Test if we can create specified number of concurrent listeners
    using dynamic port allocation
    
    Args:
        num_listeners: Number of concurrent listeners to create
    
    Returns:
        (success, actual_count, ports_used)
    """
    print(f"\nTesting {num_listeners} concurrent listeners with dynamic ports...")
    print("-" * 60)
    
    sockets = []
    ports_used = []
    
    try:
        for i in range(num_listeners):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Let OS assign port (bind to port 0)
            sock.bind(('', 0))
            assigned_port = sock.getsockname()[1]
            sock.listen(5)
            
            sockets.append(sock)
            ports_used.append(assigned_port)
            
            if (i + 1) % 100 == 0:
                print(f"  ✓ Created {i + 1} listeners...")
        
        print("-" * 60)
        print(f"\n✓ Successfully created {len(sockets)} concurrent listeners")
        print(f"  Port range used: {min(ports_used)} - {max(ports_used)}")
        
        return True, len(sockets), ports_used
    
    except Exception as e:
        print(f"\n✗ Failed after {len(sockets)} listeners: {e}")
        return False, len(sockets), ports_used
    
    finally:
        # Cleanup
        for sock in sockets:
            sock.close()


def check_system_limits():
    """Check OS limits that affect client capacity"""
    print("\nSystem Limits:")
    print("-" * 60)
    
    # File descriptor limit
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"  File descriptors (soft): {soft}")
        print(f"  File descriptors (hard): {hard}")
        
        if soft < 10000:
            print(f"  ⚠️  WARNING: Soft limit is low! Recommend: ulimit -n 65536")
    except:
        print("  File descriptor limits: N/A (Windows?)")
    
    # Ephemeral port range
    try:
        with open('/proc/sys/net/ipv4/ip_local_port_range', 'r') as f:
            port_range = f.read().strip()
            low, high = map(int, port_range.split())
            print(f"  Ephemeral port range: {low}-{high} ({high-low+1} ports)")
            
            if high - low < 20000:
                print(f"  ⚠️  WARNING: Ephemeral range may be too small for many clients")
    except:
        print("  Ephemeral port range: N/A (not Linux)")
    
    # Max connections
    try:
        with open('/proc/sys/net/core/somaxconn', 'r') as f:
            somaxconn = int(f.read().strip())
            print(f"  Max socket backlog: {somaxconn}")
            
            if somaxconn < 1024:
                print(f"  ℹ️  INFO: Consider increasing with: sysctl -w net.core.somaxconn=4096")
    except:
        print("  Max socket backlog: N/A")


def estimate_max_clients(available_ports, file_descriptor_limit):
    """
    Estimate maximum concurrent clients based on limits
    
    Args:
        available_ports: Number of available ports for peer servers
        file_descriptor_limit: OS file descriptor limit
    
    Returns:
        Estimated maximum clients
    """
    print("\nEstimated Maximum Concurrent Clients:")
    print("-" * 60)
    
    # Each client needs:
    # - 1 FD for peer server listen socket
    # - 1 FD for connection to central server
    # - N FDs for P2P connections (variable)
    # Conservative estimate: 5 FDs per client
    
    fds_per_client = 5
    max_by_fds = file_descriptor_limit // fds_per_client
    max_by_ports = available_ports
    
    print(f"  Available ports: {available_ports}")
    print(f"  File descriptor limit: {file_descriptor_limit}")
    print(f"  FDs per client (estimate): {fds_per_client}")
    print(f"  ")
    print(f"  Max by ports: {max_by_ports} clients")
    print(f"  Max by FDs: {max_by_fds} clients")
    print(f"  ")
    print(f"  ▶ ESTIMATED MAX: {min(max_by_ports, max_by_fds)} clients")
    
    return min(max_by_ports, max_by_fds)


def main():
    """Run all port limitation tests"""
    print("="*60)
    print("  P2P System - Port Limitation Tests")
    print("="*60)
    
    # Check system limits
    check_system_limits()
    
    # Test 1: Default port range
    print("\n" + "="*60)
    print("  TEST 1: Default Port Range")
    print("="*60)
    
    available, sockets, failed = test_port_availability(
        CLIENT_PORT_MIN, 
        CLIENT_PORT_MAX,
        verbose=True
    )
    
    # Cleanup
    for sock in sockets:
        sock.close()
    
    # Test 2: Extended port range
    print("\n" + "="*60)
    print("  TEST 2: Extended Port Range (6000-10000)")
    print("="*60)
    
    available_ext, sockets_ext, failed_ext = test_port_availability(
        6000, 
        10000,
        verbose=True
    )
    
    # Cleanup
    for sock in sockets_ext:
        sock.close()
    
    # Test 3: Dynamic port allocation
    print("\n" + "="*60)
    print("  TEST 3: Dynamic Port Allocation")
    print("="*60)
    
    test_concurrent_listeners(1000)
    
    # Test 4: Estimate maximum
    print("\n" + "="*60)
    print("  TEST 4: Maximum Capacity Estimation")
    print("="*60)
    
    try:
        import resource
        soft_limit, _ = resource.getrlimit(resource.RLIMIT_NOFILE)
    except:
        soft_limit = 1024
    
    estimated_max = estimate_max_clients(available, soft_limit)
    
    # Summary
    print("\n" + "="*60)
    print("  SUMMARY")
    print("="*60)
    print(f"\n  Default range ({CLIENT_PORT_MIN}-{CLIENT_PORT_MAX}):")
    print(f"    Available ports: {available}")
    print(f"    Failed ports: {len(failed)}")
    print(f"    → Max clients: {available}")
    
    print(f"\n  Extended range (6000-10000):")
    print(f"    Available ports: {available_ext}")
    print(f"    Failed ports: {len(failed_ext)}")
    print(f"    → Max clients: {available_ext}")
    
    print(f"\n  System-wide estimate:")
    print(f"    → Max concurrent clients: {estimated_max}")
    
    print(f"\n  Recommendations:")
    if available < 1000:
        print(f"    ⚠️  Increase CLIENT_PORT_MAX in config.py")
        print(f"       Suggested: CLIENT_PORT_MAX = 10000 (or higher)")
    
    if soft_limit < 10000:
        print(f"    ⚠️  Increase file descriptor limit:")
        print(f"       ulimit -n 65536")
    
    if available >= 1000 and soft_limit >= 10000:
        print(f"    ✓ System is well-configured for testing!")
    
    print("\n" + "="*60 + "\n")
    
    return estimated_max


if __name__ == '__main__':
    max_clients = main()
    sys.exit(0)
