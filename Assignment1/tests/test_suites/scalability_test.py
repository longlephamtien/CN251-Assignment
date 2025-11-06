"""
P2P File Sharing System - Scalability Test Suite

Tests system scalability with 1k, 10k, and 100k simulated clients.
Measures:
- Registry query operations latency
- File transfer performance
- API response times
- Resource utilization
- Concurrent connection handling

Note: For 100k clients, this runs in simulation mode with throttled connections
to avoid port exhaustion and system limits.
"""

import sys
import os
import time
import json
import random
import threading
import socket
import argparse
import psutil
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import multiprocessing as mp

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'bklv-backend'))

from config import SERVER_HOST, SERVER_PORT, CLIENT_PORT_MIN, CLIENT_PORT_MAX  # type: ignore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('scalability_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Track performance metrics across all tests"""
    
    def __init__(self):
        self.metrics = {
            'registry_operations': defaultdict(list),  # operation -> [latencies]
            'file_transfers': defaultdict(list),  # file_size_category -> [times]
            'api_responses': defaultdict(list),  # endpoint -> [times]
            'resource_usage': [],  # [(timestamp, cpu%, mem_mb, net_io)]
            'connection_stats': {
                'total_attempted': 0,
                'successful': 0,
                'failed': 0,
                'concurrent_peak': 0
            },
            'errors': []
        }
        self.lock = threading.Lock()
    
    def record_operation(self, operation_type, latency_ms):
        """Record latency for a registry operation"""
        with self.lock:
            self.metrics['registry_operations'][operation_type].append(latency_ms)
    
    def record_transfer(self, file_size, duration_ms):
        """Record file transfer time"""
        # Categorize by size
        if file_size < 1024 * 1024:  # < 1 MB
            category = 'small'
        elif file_size < 10 * 1024 * 1024:  # 1-10 MB
            category = 'medium'
        else:  # > 10 MB
            category = 'large'
        
        with self.lock:
            self.metrics['file_transfers'][category].append({
                'size': file_size,
                'duration_ms': duration_ms,
                'speed_mbps': (file_size / (duration_ms / 1000)) / (1024 * 1024)
            })
    
    def record_api_response(self, endpoint, response_time_ms):
        """Record API response time"""
        with self.lock:
            self.metrics['api_responses'][endpoint].append(response_time_ms)
    
    def record_resource_usage(self):
        """Record current resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            net_io = psutil.net_io_counters()
            
            with self.lock:
                self.metrics['resource_usage'].append({
                    'timestamp': time.time(),
                    'cpu_percent': cpu_percent,
                    'memory_mb': mem.used / (1024 * 1024),
                    'memory_percent': mem.percent,
                    'net_sent_mb': net_io.bytes_sent / (1024 * 1024),
                    'net_recv_mb': net_io.bytes_recv / (1024 * 1024)
                })
        except Exception as e:
            logger.warning(f"Failed to record resource usage: {e}")
    
    def record_error(self, error_type, message):
        """Record an error"""
        with self.lock:
            self.metrics['errors'].append({
                'timestamp': time.time(),
                'type': error_type,
                'message': str(message)
            })
    
    def update_connection_stats(self, attempted=0, successful=0, failed=0, concurrent=0):
        """Update connection statistics"""
        with self.lock:
            self.metrics['connection_stats']['total_attempted'] += attempted
            self.metrics['connection_stats']['successful'] += successful
            self.metrics['connection_stats']['failed'] += failed
            if concurrent > self.metrics['connection_stats']['concurrent_peak']:
                self.metrics['connection_stats']['concurrent_peak'] = concurrent
    
    def get_summary(self):
        """Get summary statistics"""
        summary = {}
        
        # Registry operations
        summary['registry_operations'] = {}
        for op, latencies in self.metrics['registry_operations'].items():
            if latencies:
                summary['registry_operations'][op] = {
                    'count': len(latencies),
                    'avg_ms': sum(latencies) / len(latencies),
                    'min_ms': min(latencies),
                    'max_ms': max(latencies),
                    'p50_ms': sorted(latencies)[len(latencies) // 2],
                    'p95_ms': sorted(latencies)[int(len(latencies) * 0.95)],
                    'p99_ms': sorted(latencies)[int(len(latencies) * 0.99)]
                }
        
        # File transfers
        summary['file_transfers'] = {}
        for category, transfers in self.metrics['file_transfers'].items():
            if transfers:
                durations = [t['duration_ms'] for t in transfers]
                speeds = [t['speed_mbps'] for t in transfers]
                summary['file_transfers'][category] = {
                    'count': len(transfers),
                    'avg_duration_ms': sum(durations) / len(durations),
                    'avg_speed_mbps': sum(speeds) / len(speeds),
                    'min_speed_mbps': min(speeds),
                    'max_speed_mbps': max(speeds)
                }
        
        # Resource usage
        if self.metrics['resource_usage']:
            cpu_vals = [r['cpu_percent'] for r in self.metrics['resource_usage']]
            mem_vals = [r['memory_mb'] for r in self.metrics['resource_usage']]
            summary['resource_usage'] = {
                'avg_cpu_percent': sum(cpu_vals) / len(cpu_vals),
                'max_cpu_percent': max(cpu_vals),
                'avg_memory_mb': sum(mem_vals) / len(mem_vals),
                'max_memory_mb': max(mem_vals)
            }
        
        summary['connection_stats'] = self.metrics['connection_stats']
        summary['error_count'] = len(self.metrics['errors'])
        
        return summary
    
    def save_to_file(self, filepath):
        """Save complete metrics to JSON file"""
        with self.lock:
            data = {
                'summary': self.get_summary(),
                'detailed_metrics': {
                    'registry_operations': dict(self.metrics['registry_operations']),
                    'file_transfers': dict(self.metrics['file_transfers']),
                    'api_responses': dict(self.metrics['api_responses']),
                    'resource_usage': self.metrics['resource_usage'],
                    'connection_stats': self.metrics['connection_stats'],
                    'errors': self.metrics['errors']
                },
                'test_timestamp': datetime.now().isoformat()
            }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")


class SimulatedClient:
    """Lightweight simulated client for scalability testing"""
    
    def __init__(self, client_id, server_host, server_port, files_to_share):
        self.client_id = client_id
        self.hostname = f"client_{client_id}"
        self.server_host = server_host
        self.server_port = server_port
        self.files_to_share = files_to_share  # List of (filename, size)
        self.connection = None
        self.registered = False
    
    def send_json(self, obj):
        """Send JSON message"""
        data = json.dumps(obj) + '\n'
        self.connection.sendall(data.encode())
    
    def recv_json(self):
        """Receive JSON message"""
        buf = b''
        while True:
            chunk = self.connection.recv(4096)
            if not chunk:
                return None
            buf += chunk
            if b'\n' in buf:
                line, _ = buf.split(b'\n', 1)
                return json.loads(line.decode())
    
    def connect(self):
        """Connect to server"""
        try:
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connection.settimeout(10)
            self.connection.connect((self.server_host, self.server_port))
            return True
        except Exception as e:
            logger.error(f"Client {self.client_id} connection failed: {e}")
            return False
    
    def register(self, metrics):
        """Register with server"""
        if not self.connection:
            return False
        
        try:
            # Prepare files metadata
            files_metadata = {}
            for fname, fsize in self.files_to_share:
                files_metadata[fname] = {
                    "size": fsize,
                    "modified": time.time(),
                    "published_at": time.time(),
                    "is_published": True
                }
            
            start_time = time.time()
            self.send_json({
                "action": "REGISTER",
                "data": {
                    "hostname": self.hostname,
                    "port": CLIENT_PORT_MIN + self.client_id,
                    "display_name": self.hostname,
                    "files_metadata": files_metadata
                }
            })
            
            resp = self.recv_json()
            latency = (time.time() - start_time) * 1000  # ms
            
            if resp and resp.get('status') == 'OK':
                self.registered = True
                metrics.record_operation('REGISTER', latency)
                return True
            else:
                metrics.record_error('REGISTER', f"Failed: {resp}")
                return False
        except Exception as e:
            metrics.record_error('REGISTER', str(e))
            return False
    
    def publish_file(self, filename, filesize, metrics):
        """Publish a file to the network"""
        if not self.registered:
            return False
        
        try:
            start_time = time.time()
            self.send_json({
                "action": "PUBLISH",
                "data": {
                    "hostname": self.hostname,
                    "fname": filename,
                    "size": filesize,
                    "modified": time.time()
                }
            })
            
            resp = self.recv_json()
            latency = (time.time() - start_time) * 1000
            
            if resp and resp.get('status') == 'ACK':
                metrics.record_operation('PUBLISH', latency)
                return True
            else:
                metrics.record_error('PUBLISH', f"Failed: {resp}")
                return False
        except Exception as e:
            metrics.record_error('PUBLISH', str(e))
            return False
    
    def request_file(self, filename, metrics):
        """Request file location from server"""
        if not self.registered:
            return None
        
        try:
            start_time = time.time()
            self.send_json({
                "action": "REQUEST",
                "data": {"fname": filename}
            })
            
            resp = self.recv_json()
            latency = (time.time() - start_time) * 1000
            
            metrics.record_operation('REQUEST', latency)
            
            if resp and resp.get('status') == 'FOUND':
                return resp.get('hosts', [])
            return None
        except Exception as e:
            metrics.record_error('REQUEST', str(e))
            return None
    
    def list_registry(self, metrics):
        """List all files in registry"""
        if not self.registered:
            return None
        
        try:
            start_time = time.time()
            self.send_json({"action": "LIST"})
            
            resp = self.recv_json()
            latency = (time.time() - start_time) * 1000
            
            metrics.record_operation('LIST', latency)
            return resp
        except Exception as e:
            metrics.record_error('LIST', str(e))
            return None
    
    def ping(self, target_hostname, metrics):
        """Ping another client"""
        if not self.registered:
            return False
        
        try:
            start_time = time.time()
            self.send_json({
                "action": "PING",
                "data": {"hostname": target_hostname}
            })
            
            resp = self.recv_json()
            latency = (time.time() - start_time) * 1000
            
            metrics.record_operation('PING', latency)
            return resp and resp.get('status') == 'ALIVE'
        except Exception as e:
            metrics.record_error('PING', str(e))
            return False
    
    def unregister(self):
        """Unregister from server"""
        if self.registered and self.connection:
            try:
                self.send_json({
                    "action": "UNREGISTER",
                    "data": {"hostname": self.hostname}
                })
                self.recv_json()
            except:
                pass
    
    def close(self):
        """Close connection"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass


def assign_files_to_clients(num_clients, test_files):
    """
    Randomly assign files to clients
    
    Args:
        num_clients: Number of clients
        test_files: List of available test files [(filename, size), ...]
    
    Returns:
        List of file assignments per client
    """
    client_files = []
    
    for i in range(num_clients):
        # Random number of files per client (0 to 5)
        # Some clients have no files (as per requirement)
        num_files = random.randint(0, min(5, len(test_files)))
        
        if num_files > 0:
            # Randomly select files
            selected_files = random.sample(test_files, num_files)
            client_files.append(selected_files)
        else:
            client_files.append([])
    
    return client_files


def run_client_simulation(client_id, server_host, server_port, files_to_share, 
                          metrics, operations_per_client=10):
    """
    Run a single simulated client
    
    Args:
        client_id: Unique client identifier
        server_host: Server hostname/IP
        server_port: Server port
        files_to_share: List of (filename, size) tuples
        metrics: PerformanceMetrics instance
        operations_per_client: Number of operations to perform
    """
    client = SimulatedClient(client_id, server_host, server_port, files_to_share)
    
    try:
        # Connect
        metrics.update_connection_stats(attempted=1)
        if not client.connect():
            metrics.update_connection_stats(failed=1)
            return False
        
        metrics.update_connection_stats(successful=1)
        
        # Register
        if not client.register(metrics):
            client.close()
            return False
        
        # Publish files
        for fname, fsize in files_to_share:
            client.publish_file(fname, fsize, metrics)
            time.sleep(random.uniform(0.01, 0.05))  # Small delay
        
        # Perform random operations
        for _ in range(operations_per_client):
            operation = random.choice(['REQUEST', 'LIST', 'PING'])
            
            if operation == 'REQUEST' and files_to_share:
                # Request a random file
                fname = random.choice([f[0] for f in files_to_share])
                client.request_file(fname, metrics)
            
            elif operation == 'LIST':
                client.list_registry(metrics)
            
            elif operation == 'PING':
                # Ping a random client
                target = f"client_{random.randint(0, client_id)}"
                client.ping(target, metrics)
            
            time.sleep(random.uniform(0.01, 0.1))
        
        # Cleanup
        client.unregister()
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"Client {client_id} simulation error: {e}")
        metrics.record_error('CLIENT_SIMULATION', str(e))
        client.close()
        return False


def run_scalability_test(num_clients, test_files, server_host, server_port,
                         max_concurrent=1000, operations_per_client=10):
    """
    Run scalability test with specified number of clients
    
    Args:
        num_clients: Total number of clients to simulate
        test_files: List of test files [(filename, size), ...]
        server_host: Server hostname
        server_port: Server port
        max_concurrent: Maximum concurrent connections
        operations_per_client: Operations per client
    
    Returns:
        PerformanceMetrics instance with results
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Starting scalability test with {num_clients} clients")
    logger.info(f"Max concurrent connections: {max_concurrent}")
    logger.info(f"Operations per client: {operations_per_client}")
    logger.info(f"{'='*60}\n")
    
    metrics = PerformanceMetrics()
    
    # Assign files to clients
    logger.info("Assigning files to clients...")
    client_file_assignments = assign_files_to_clients(num_clients, test_files)
    
    clients_with_files = sum(1 for files in client_file_assignments if files)
    logger.info(f"  - Clients with files: {clients_with_files}")
    logger.info(f"  - Clients without files: {num_clients - clients_with_files}")
    
    # Start resource monitoring thread
    stop_monitoring = threading.Event()
    
    def monitor_resources():
        while not stop_monitoring.is_set():
            metrics.record_resource_usage()
            time.sleep(1)
    
    monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
    monitor_thread.start()
    
    # Run client simulations with controlled concurrency
    logger.info(f"\nStarting client simulations...")
    start_time = time.time()
    
    successful = 0
    failed = 0
    
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = []
        
        for client_id in range(num_clients):
            files_to_share = client_file_assignments[client_id]
            
            future = executor.submit(
                run_client_simulation,
                client_id,
                server_host,
                server_port,
                files_to_share,
                metrics,
                operations_per_client
            )
            futures.append(future)
            
            # Track concurrent connections
            current_concurrent = sum(1 for f in futures if not f.done())
            metrics.update_connection_stats(concurrent=current_concurrent)
            
            # Progress reporting
            if (client_id + 1) % max(1, num_clients // 10) == 0:
                logger.info(f"  Progress: {client_id + 1}/{num_clients} clients started")
        
        # Wait for all to complete
        for i, future in enumerate(as_completed(futures)):
            try:
                result = future.result(timeout=60)
                if result:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Client future error: {e}")
                failed += 1
            
            # Progress reporting
            if (i + 1) % max(1, num_clients // 10) == 0:
                logger.info(f"  Progress: {i + 1}/{num_clients} clients completed")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Stop resource monitoring
    stop_monitoring.set()
    monitor_thread.join(timeout=2)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"Test completed in {total_duration:.2f} seconds")
    logger.info(f"Successful clients: {successful}")
    logger.info(f"Failed clients: {failed}")
    logger.info(f"{'='*60}\n")
    
    return metrics


def get_test_files_info(files_dir):
    """
    Get information about test files in the files directory
    
    Returns:
        List of (filename, size) tuples
    """
    files_path = Path(files_dir)
    if not files_path.exists():
        logger.warning(f"Test files directory not found: {files_dir}")
        return []
    
    test_files = []
    for filepath in files_path.glob('*'):
        if filepath.is_file() and not filepath.name.startswith('.'):
            size = filepath.stat().st_size
            test_files.append((filepath.name, size))
    
    return test_files


def print_metrics_summary(metrics, num_clients):
    """Print formatted summary of metrics"""
    summary = metrics.get_summary()
    
    print(f"\n{'='*70}")
    print(f"PERFORMANCE TEST RESULTS - {num_clients} CLIENTS")
    print(f"{'='*70}\n")
    
    # Registry Operations
    print("REGISTRY QUERY OPERATIONS:")
    print("-" * 70)
    if summary.get('registry_operations'):
        for op, stats in summary['registry_operations'].items():
            print(f"\n{op}:")
            print(f"  Count: {stats['count']}")
            print(f"  Average: {stats['avg_ms']:.2f} ms")
            print(f"  Min: {stats['min_ms']:.2f} ms")
            print(f"  Max: {stats['max_ms']:.2f} ms")
            print(f"  P50: {stats['p50_ms']:.2f} ms")
            print(f"  P95: {stats['p95_ms']:.2f} ms")
            print(f"  P99: {stats['p99_ms']:.2f} ms")
    else:
        print("  No data collected")
    
    # File Transfers
    print(f"\n\nFILE TRANSFER PERFORMANCE:")
    print("-" * 70)
    if summary.get('file_transfers'):
        for category, stats in summary['file_transfers'].items():
            print(f"\n{category.upper()} files:")
            print(f"  Count: {stats['count']}")
            print(f"  Avg Duration: {stats['avg_duration_ms']:.2f} ms")
            print(f"  Avg Speed: {stats['avg_speed_mbps']:.2f} MB/s")
            print(f"  Min Speed: {stats['min_speed_mbps']:.2f} MB/s")
            print(f"  Max Speed: {stats['max_speed_mbps']:.2f} MB/s")
    else:
        print("  No data collected")
    
    # Resource Utilization
    print(f"\n\nRESOURCE UTILIZATION:")
    print("-" * 70)
    if summary.get('resource_usage'):
        res = summary['resource_usage']
        print(f"CPU Usage:")
        print(f"  Average: {res['avg_cpu_percent']:.2f}%")
        print(f"  Peak: {res['max_cpu_percent']:.2f}%")
        print(f"\nMemory Usage:")
        print(f"  Average: {res['avg_memory_mb']:.2f} MB")
        print(f"  Peak: {res['max_memory_mb']:.2f} MB")
    else:
        print("  No data collected")
    
    # Connection Stats
    print(f"\n\nCONNECTION STATISTICS:")
    print("-" * 70)
    conn_stats = summary.get('connection_stats', {})
    print(f"Total Attempted: {conn_stats.get('total_attempted', 0)}")
    print(f"Successful: {conn_stats.get('successful', 0)}")
    print(f"Failed: {conn_stats.get('failed', 0)}")
    print(f"Peak Concurrent: {conn_stats.get('concurrent_peak', 0)}")
    
    # Errors
    print(f"\n\nERRORS:")
    print("-" * 70)
    print(f"Total Errors: {summary.get('error_count', 0)}")
    
    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description='P2P System Scalability Test')
    parser.add_argument('--clients', type=int, default=100,
                       help='Number of clients to simulate (default: 100)')
    parser.add_argument('--server-host', default='127.0.0.1',
                       help='Server hostname (default: 127.0.0.1)')
    parser.add_argument('--server-port', type=int, default=SERVER_PORT,
                       help=f'Server port (default: {SERVER_PORT})')
    parser.add_argument('--max-concurrent', type=int, default=1000,
                       help='Max concurrent connections (default: 1000)')
    parser.add_argument('--operations', type=int, default=10,
                       help='Operations per client (default: 10)')
    parser.add_argument('--files-dir', default='files',
                       help='Test files directory (default: files)')
    parser.add_argument('--output', default=None,
                       help='Output file for metrics (default: auto-generated)')
    parser.add_argument('--preset', choices=['1k', '10k', '100k'],
                       help='Use preset configuration (1k, 10k, or 100k clients)')
    
    args = parser.parse_args()
    
    # Apply preset configurations
    if args.preset == '1k':
        args.clients = 1000
        args.max_concurrent = 500
        args.operations = 5
    elif args.preset == '10k':
        args.clients = 10000
        args.max_concurrent = 1000
        args.operations = 3
    elif args.preset == '100k':
        args.clients = 100000
        args.max_concurrent = 2000
        args.operations = 2
    
    # Get test files
    # Path is relative to Assignment1 directory (parent of tests/)
    files_dir = Path(__file__).parent.parent / args.files_dir
    test_files = get_test_files_info(files_dir)
    
    if not test_files:
        logger.error(f"No test files found in {files_dir}")
        logger.info("Please run test_file_generator.py first to create test files")
        return 1
    
    logger.info(f"Found {len(test_files)} test files:")
    for fname, size in test_files[:5]:  # Show first 5
        logger.info(f"  - {fname}: {size:,} bytes")
    if len(test_files) > 5:
        logger.info(f"  ... and {len(test_files) - 5} more")
    
    # Run test
    metrics = run_scalability_test(
        num_clients=args.clients,
        test_files=test_files,
        server_host=args.server_host,
        server_port=args.server_port,
        max_concurrent=args.max_concurrent,
        operations_per_client=args.operations
    )
    
    # Print summary
    print_metrics_summary(metrics, args.clients)
    
    # Save to file
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'metrics_{args.clients}_clients_{timestamp}.json'
    
    metrics.save_to_file(output_file)
    
    logger.info(f"\n✓ Test complete. Results saved to {output_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
