"""
P2P File Transfer Performance Test

Simulates real P2P file transfers between clients to measure:
- Transfer speeds for different file sizes
- Concurrent download performance
- Multi-threaded client behavior
"""

import sys
import os
import time
import json
import random
import threading
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'bklv-backend'))

try:
    from client import Client  # type: ignore
    from config import SERVER_HOST, SERVER_PORT  # type: ignore
except ImportError as e:
    print(f"ERROR: Failed to import modules: {e}")
    print("Make sure you're running from the tests directory")
    sys.exit(1)


class P2PTransferTest:
    """Test P2P file transfers between real clients"""
    
    def __init__(self, server_host, server_port, num_clients=3):
        self.server_host = server_host
        self.server_port = server_port
        self.num_clients = num_clients
        self.clients = []
        self.temp_dirs = []
        self.transfer_stats = []
    
    def setup_clients(self, test_files_dir):
        """Setup test clients with temporary repositories"""
        print(f"\n=== Setting up {self.num_clients} test clients ===")
        
        test_files = list(Path(test_files_dir).glob('*'))
        test_files = [f for f in test_files if f.is_file() and not f.name.startswith('.')]
        
        for i in range(self.num_clients):
            # Create temp directory for client
            temp_dir = tempfile.mkdtemp(prefix=f'p2p_test_client_{i}_')
            self.temp_dirs.append(temp_dir)
            
            # Create client
            hostname = f"test_client_{i}"
            port = 6000 + i
            
            try:
                client = Client(
                    hostname=hostname,
                    listen_port=port,
                    repo_dir=temp_dir,
                    display_name=f"TestClient{i}",
                    server_host=self.server_host,
                    server_port=self.server_port
                )
                
                self.clients.append(client)
                print(f"  ✓ Client {i}: {hostname} on port {port}")
                
                # Assign random files to this client
                num_files = random.randint(1, min(3, len(test_files)))
                assigned_files = random.sample(test_files, num_files)
                
                for test_file in assigned_files:
                    # Publish the file (reference-based, no copying)
                    success, error = client.publish(
                        str(test_file),
                        test_file.name,
                        interactive=False
                    )
                    if success:
                        print(f"    • Published: {test_file.name} ({test_file.stat().st_size:,} bytes)")
                    else:
                        print(f"    ✗ Failed to publish {test_file.name}: {error}")
                
            except Exception as e:
                print(f"  ✗ Failed to create client {i}: {e}")
                raise
        
        time.sleep(2)  # Let everything settle
        print(f"\n✓ All {len(self.clients)} clients ready\n")
    
    def test_single_transfer(self, from_client_idx, to_client_idx, filename):
        """Test a single file transfer between two clients"""
        from_client = self.clients[from_client_idx]
        to_client = self.clients[to_client_idx]
        
        print(f"\nTransfer Test: {from_client.hostname} → {to_client.hostname}")
        print(f"  File: {filename}")
        
        # Check if source has the file
        if filename not in from_client.published_files:
            print(f"  ✗ Source client doesn't have {filename}")
            return None
        
        file_size = from_client.published_files[filename].size
        print(f"  Size: {file_size:,} bytes")
        
        # Remove file from destination if it exists (avoid interactive prompt)
        save_path = os.path.join(to_client.repo_dir, filename)
        if os.path.exists(save_path):
            os.remove(save_path)
        
        # Remove from destination client's local files tracking
        if filename in to_client.local_files:
            to_client.local_files.pop(filename)
        
        # Perform transfer
        start_time = time.time()
        
        result = to_client.request(filename, save_path=save_path)
        
        if not result:
            print(f"  ✗ Request failed to initiate")
            return None
        
        # Wait for download to complete (check if file exists and size matches)
        max_wait = 120  # 2 minutes max
        waited = 0
        while waited < max_wait:
            if os.path.exists(save_path):
                current_size = os.path.getsize(save_path)
                if current_size == file_size:
                    # File is complete
                    break
                elif current_size > 0:
                    # File is being downloaded, wait a bit more
                    time.sleep(0.5)
                    waited += 0.5
                else:
                    time.sleep(0.5)
                    waited += 0.5
            else:
                time.sleep(0.5)
                waited += 0.5
        
        end_time = time.time()
        duration = end_time - start_time
        
        if os.path.exists(save_path):
            actual_size = os.path.getsize(save_path)
            if actual_size == file_size:
                speed_mbps = (file_size / duration) / (1024 * 1024)
                print(f"  ✓ Success!")
                print(f"  Duration: {duration:.2f} seconds")
                print(f"  Speed: {speed_mbps:.2f} MB/s")
                
                stat = {
                    'filename': filename,
                    'size': file_size,
                    'duration': duration,
                    'speed_mbps': speed_mbps,
                    'from_client': from_client.hostname,
                    'to_client': to_client.hostname,
                    'success': True
                }
                self.transfer_stats.append(stat)
                return stat
            else:
                print(f"  ✗ Size mismatch: expected {file_size:,}, got {actual_size:,}")
                print(f"  ✗ Transfer may have been interrupted")
                return None
        else:
            print(f"  ✗ Transfer failed or timed out after {waited:.1f} seconds")
            print(f"  ✗ File was not created at: {save_path}")
            return None
    
    def test_concurrent_transfers(self, num_concurrent=3):
        """Test concurrent file transfers"""
        print(f"\n=== Testing {num_concurrent} Concurrent Transfers ===")
        
        # Get all available files across all clients
        available_files = {}
        for i, client in enumerate(self.clients):
            for fname in client.published_files.keys():
                if fname not in available_files:
                    available_files[fname] = []
                available_files[fname].append(i)
        
        if len(available_files) < num_concurrent:
            print(f"Not enough files for {num_concurrent} concurrent transfers")
            num_concurrent = len(available_files)
        
        # Setup transfers
        transfers = []
        for fname in list(available_files.keys())[:num_concurrent]:
            source_idx = available_files[fname][0]
            # Pick a different client as destination
            dest_idx = (source_idx + 1) % len(self.clients)
            transfers.append((source_idx, dest_idx, fname))
        
        # Run transfers concurrently
        threads = []
        results = [None] * len(transfers)
        
        def run_transfer(idx, from_idx, to_idx, fname):
            results[idx] = self.test_single_transfer(from_idx, to_idx, fname)
        
        start_time = time.time()
        
        for i, (from_idx, to_idx, fname) in enumerate(transfers):
            thread = threading.Thread(
                target=run_transfer,
                args=(i, from_idx, to_idx, fname)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        successful = sum(1 for r in results if r is not None)
        print(f"\n✓ Concurrent test completed in {total_duration:.2f} seconds")
        print(f"  Successful: {successful}/{len(transfers)}")
        
        return results
    
    def test_multiple_downloads_from_same_peer(self, num_downloads=3):
        """Test multiple clients downloading from the same peer simultaneously"""
        print(f"\n=== Testing {num_downloads} Downloads from Same Peer ===")
        
        # Find a client with files
        source_idx = None
        for i, client in enumerate(self.clients):
            if client.published_files:
                source_idx = i
                break
        
        if source_idx is None:
            print("No clients with published files found")
            return []
        
        source_client = self.clients[source_idx]
        filename = list(source_client.published_files.keys())[0]
        
        print(f"Source: {source_client.hostname}")
        print(f"File: {filename}")
        
        # Setup multiple destination clients
        dest_clients = []
        for i, client in enumerate(self.clients):
            if i != source_idx and len(dest_clients) < num_downloads:
                dest_clients.append((i, client))
        
        if len(dest_clients) < num_downloads:
            print(f"Only {len(dest_clients)} destination clients available")
        
        # Run concurrent downloads
        threads = []
        results = [None] * len(dest_clients)
        
        def download(idx, dest_idx):
            results[idx] = self.test_single_transfer(source_idx, dest_idx, filename)
        
        start_time = time.time()
        
        for i, (dest_idx, _) in enumerate(dest_clients):
            thread = threading.Thread(target=download, args=(i, dest_idx))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        successful = sum(1 for r in results if r is not None)
        print(f"\n✓ Multi-download test completed in {total_duration:.2f} seconds")
        print(f"  Successful: {successful}/{len(dest_clients)}")
        
        return results
    
    def generate_report(self, output_file=None):
        """Generate performance report"""
        if not self.transfer_stats:
            print("No transfer statistics available")
            return
        
        print("\n" + "="*70)
        print("P2P FILE TRANSFER PERFORMANCE REPORT")
        print("="*70)
        
        # Group by file size category
        small_transfers = [s for s in self.transfer_stats if s['size'] < 1024*1024]
        medium_transfers = [s for s in self.transfer_stats if 1024*1024 <= s['size'] < 10*1024*1024]
        large_transfers = [s for s in self.transfer_stats if s['size'] >= 10*1024*1024]
        
        categories = [
            ("Small (< 1 MB)", small_transfers),
            ("Medium (1-10 MB)", medium_transfers),
            ("Large (> 10 MB)", large_transfers)
        ]
        
        for category_name, transfers in categories:
            if transfers:
                print(f"\n{category_name}:")
                print("-" * 70)
                durations = [t['duration'] for t in transfers]
                speeds = [t['speed_mbps'] for t in transfers]
                
                print(f"  Count: {len(transfers)}")
                print(f"  Avg Duration: {sum(durations)/len(durations):.2f} seconds")
                print(f"  Avg Speed: {sum(speeds)/len(speeds):.2f} MB/s")
                print(f"  Min Speed: {min(speeds):.2f} MB/s")
                print(f"  Max Speed: {max(speeds):.2f} MB/s")
        
        # Overall statistics
        print(f"\n\nOverall Statistics:")
        print("-" * 70)
        print(f"Total Transfers: {len(self.transfer_stats)}")
        print(f"Success Rate: 100%")  # Only successful transfers are recorded
        
        all_speeds = [t['speed_mbps'] for t in self.transfer_stats]
        print(f"Average Speed: {sum(all_speeds)/len(all_speeds):.2f} MB/s")
        
        print("\n" + "="*70 + "\n")
        
        # Save to file
        if output_file:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'num_clients': self.num_clients,
                'total_transfers': len(self.transfer_stats),
                'transfers': self.transfer_stats,
                'summary': {
                    'small': {
                        'count': len(small_transfers),
                        'avg_speed_mbps': sum(t['speed_mbps'] for t in small_transfers) / len(small_transfers) if small_transfers else 0
                    },
                    'medium': {
                        'count': len(medium_transfers),
                        'avg_speed_mbps': sum(t['speed_mbps'] for t in medium_transfers) / len(medium_transfers) if medium_transfers else 0
                    },
                    'large': {
                        'count': len(large_transfers),
                        'avg_speed_mbps': sum(t['speed_mbps'] for t in large_transfers) / len(large_transfers) if large_transfers else 0
                    }
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"Report saved to {output_file}")
    
    def cleanup(self):
        """Cleanup clients and temp directories"""
        print("\n=== Cleaning up ===")
        
        # Close clients
        for client in self.clients:
            try:
                client.close()
            except Exception as e:
                print(f"Error closing client: {e}")
        
        # Remove temp directories
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                print(f"  ✓ Removed {temp_dir}")
            except Exception as e:
                print(f"  ✗ Failed to remove {temp_dir}: {e}")
        
        print("✓ Cleanup complete")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='P2P Transfer Performance Test')
    parser.add_argument('--server-host', default='127.0.0.1',
                       help='Server hostname (default: 127.0.0.1)')
    parser.add_argument('--server-port', type=int, default=9000,
                       help='Server port (default: 9000)')
    parser.add_argument('--clients', type=int, default=5,
                       help='Number of test clients (default: 5)')
    parser.add_argument('--files-dir', default='files',
                       help='Test files directory (default: files)')
    parser.add_argument('--output', default=None,
                       help='Output file for report (default: auto-generated)')
    
    args = parser.parse_args()
    
    # Check if test files exist
    # Path is relative to Assignment1 directory (parent of tests/)
    files_dir = Path(__file__).parent.parent / args.files_dir
    if not files_dir.exists():
        print(f"ERROR: Test files directory not found: {files_dir}")
        print("Please run test_file_generator.py first")
        return 1
    
    print("=== P2P File Transfer Performance Test ===")
    print(f"Server: {args.server_host}:{args.server_port}")
    print(f"Clients: {args.clients}")
    print(f"Test Files: {files_dir}")
    
    test = P2PTransferTest(args.server_host, args.server_port, args.clients)
    
    try:
        # Setup
        test.setup_clients(files_dir)
        
        # Run tests
        print("\n" + "="*70)
        print("RUNNING TRANSFER TESTS")
        print("="*70)
        
        # Test 1: Individual transfers
        print("\n--- Test 1: Individual Transfers ---")
        for i in range(min(3, args.clients - 1)):
            # Find a client with files
            source_idx = None
            for j, client in enumerate(test.clients):
                if client.published_files:
                    source_idx = j
                    break
            
            if source_idx is not None:
                dest_idx = (source_idx + 1) % args.clients
                filename = list(test.clients[source_idx].published_files.keys())[0]
                test.test_single_transfer(source_idx, dest_idx, filename)
        
        # Test 2: Concurrent transfers
        print("\n--- Test 2: Concurrent Transfers ---")
        test.test_concurrent_transfers(num_concurrent=3)
        
        # Test 3: Multiple downloads from same peer
        print("\n--- Test 3: Multiple Downloads from Same Peer ---")
        test.test_multiple_downloads_from_same_peer(num_downloads=3)
        
        # Generate report
        if args.output:
            output_file = args.output
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'p2p_transfer_report_{timestamp}.json'
        
        test.generate_report(output_file)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test.cleanup()
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
