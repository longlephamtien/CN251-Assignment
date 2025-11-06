#!/usr/bin/env python3
"""
P2P Performance Test Runner - Unified test suite
Chạy tất cả các test performance cho P2P file sharing system

Usage:
    python test_runner.py --mode quick       # Quick test (~10 phút)
    python test_runner.py --mode standard    # Standard test (~30 phút)
    python test_runner.py --mode full        # Full test (2-3 giờ)
"""

import sys
import os
import subprocess
import time
import json
import argparse
from pathlib import Path
from datetime import datetime


class PerformanceTestRunner:
    """Test runner thống nhất cho tất cả các test"""
    
    def __init__(self, server_host='127.0.0.1', server_port=9000, mode='standard'):
        self.server_host = server_host
        self.server_port = server_port
        self.mode = mode
        self.test_dir = Path(__file__).parent
        self.results_dir = self.test_dir / 'results'
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.all_results = {}
        
        # Configure tests based on mode
        self.test_config = self._get_test_config()
        
    def _get_test_config(self):
        """Cấu hình test theo mode"""
        configs = {
            'quick': {
                'description': 'Quick validation test',
                'scalability_tests': ['1k'],
                'p2p_clients': 5,
                'run_heartbeat': False,
                'run_duplicate': False,
                'timeout_multiplier': 1
            },
            'standard': {
                'description': 'Standard performance test',
                'scalability_tests': ['1k', '10k'],
                'p2p_clients': 20,
                'run_heartbeat': True,
                'run_duplicate': True,
                'timeout_multiplier': 2
            },
            'full': {
                'description': 'Complete performance test suite',
                'scalability_tests': ['1k', '10k', '100k'],
                'p2p_clients': 20,
                'run_heartbeat': True,
                'run_duplicate': True,
                'timeout_multiplier': 3
            }
        }
        return configs.get(self.mode, configs['standard'])
    
    def print_header(self, title):
        """In header đẹp"""
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    
    def check_server(self):
        """Kiểm tra server có đang chạy không"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.server_host, self.server_port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def run_command(self, command, description, timeout=600):
        """Chạy command và capture output"""
        self.print_header(description)
        print(f"Command: {' '.join(command)}")
        print(f"Timeout: {timeout}s\n")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            print(f"\nDuration: {duration:.2f}s")
            
            success = result.returncode == 0
            status = "✓ SUCCESS" if success else "✗ FAILED"
            print(f"\n{status}")
            
            return success, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"✗ TIMEOUT after {duration:.2f}s")
            return False, "", "Timeout"
        except Exception as e:
            print(f"✗ ERROR: {e}")
            return False, "", str(e)
    
    def generate_test_files(self):
        """Tạo test files nếu chưa có"""
        files_dir = self.test_dir.parent / 'files'
        
        # Kiểm tra xem đã có files chưa
        if files_dir.exists() and len(list(files_dir.glob('*.txt'))) > 10:
            print(f"✓ Test files already exist ({len(list(files_dir.glob('*.txt')))} files)")
            return True
        
        self.print_header("Generating Test Files")
        
        success, stdout, stderr = self.run_command(
            [sys.executable, str(self.test_dir / 'scripts' / 'test_file_generator.py')],
            "Generating test files",
            timeout=300
        )
        
        return success
    
    def run_scalability_test(self, preset='1k'):
        """Chạy scalability test"""
        output_file = self.results_dir / f'scalability_{preset}_{self.timestamp}.json'
        
        timeout_base = {'1k': 600, '10k': 1800, '100k': 7200}
        timeout = timeout_base.get(preset, 600) * self.test_config['timeout_multiplier']
        
        success, stdout, stderr = self.run_command(
            [
                sys.executable,
                str(self.test_dir / 'test_suites' / 'scalability_test.py'),
                '--preset', preset,
                '--server-host', self.server_host,
                '--server-port', str(self.server_port),
                '--output', str(output_file)
            ],
            f"Scalability Test - {preset.upper()} Clients",
            timeout=timeout
        )
        
        if success and output_file.exists():
            with open(output_file) as f:
                self.all_results[f'scalability_{preset}'] = json.load(f)
        
        return success
    
    def run_p2p_transfer_test(self):
        """Chạy P2P transfer test"""
        num_clients = self.test_config['p2p_clients']
        output_file = self.results_dir / f'p2p_transfer_{self.timestamp}.json'
        
        timeout = 1800 * self.test_config['timeout_multiplier']
        
        success, stdout, stderr = self.run_command(
            [
                sys.executable,
                str(self.test_dir / 'test_suites' / 'p2p_transfer_test.py'),
                '--server-host', self.server_host,
                '--server-port', str(self.server_port),
                '--clients', str(num_clients),
                '--output', str(output_file)
            ],
            f"P2P File Transfer Test - {num_clients} Clients",
            timeout=timeout
        )
        
        if success and output_file.exists():
            with open(output_file) as f:
                self.all_results['p2p_transfer'] = json.load(f)
        
        return success
    
    def run_heartbeat_comparison(self):
        """Chạy heartbeat comparison test"""
        output_file = self.results_dir / f'heartbeat_comparison_{self.timestamp}.json'
        
        success, stdout, stderr = self.run_command(
            [
                sys.executable,
                str(self.test_dir / 'test_suites' / 'heartbeat_comparison_test.py'),
                '--clients', '100000',
                '--duration', '3600',
                '--output', str(output_file)
            ],
            "Heartbeat Optimization Test - 100k Clients",
            timeout=3700
        )
        
        if success and output_file.exists():
            with open(output_file) as f:
                self.all_results['heartbeat_comparison'] = json.load(f)
        
        return success
    
    def run_duplicate_detection_test(self):
        """Chạy duplicate detection test"""
        output_file = self.results_dir / f'duplicate_detection_{self.timestamp}.json'
        
        # Tạo inline test script
        test_script = f"""
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'bklv-backend'))

from optimizations.file_hashing import DuplicateDetector, FileMetadata

print("Testing Duplicate Detection with 10,000 files...")

detector = DuplicateDetector()
num_files = 10000
start_time = time.time()

for i in range(num_files):
    metadata = FileMetadata(
        name=f"file_{{i}}.bin",
        size=1024 * (i % 100 + 1),
        modified=time.time(),
        hash=f"hash_{{i % 1000}}"
    )
    detector.add_file(f"client_{{i % 100}}", f"file_{{i}}.bin", metadata)
    
    if (i + 1) % 1000 == 0:
        print(f"  Added {{i+1}}/{{num_files}} files...")

duration = time.time() - start_time
stats = detector.get_stats()

print(f"\\nTotal files: {{stats['total_files']}}")
print(f"Unique hashes: {{stats['unique_hashes']}}")
print(f"Duplicate files: {{stats['duplicate_files']}}")
print(f"Duration: {{duration:.2f}}s")
print(f"Average time per file: {{duration/num_files*1000:.2f}}ms")

results = {{
    'num_files': num_files,
    'duration_seconds': duration,
    'avg_time_per_file_ms': duration/num_files*1000,
    'statistics': stats,
    'performance': {{
        'files_per_second': num_files / duration,
        'memory_usage_estimate_mb': num_files * 0.001
    }}
}}

with open('{output_file}', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\\nResults saved to {output_file.name}")
"""
        
        test_file = self.test_dir / f'_temp_duplicate_test_{self.timestamp}.py'
        test_file.write_text(test_script)
        
        success, stdout, stderr = self.run_command(
            [sys.executable, str(test_file)],
            "Duplicate Detection Performance Test",
            timeout=300
        )
        
        # Cleanup
        if test_file.exists():
            test_file.unlink()
        
        if success and output_file.exists():
            with open(output_file) as f:
                self.all_results['duplicate_detection'] = json.load(f)
        
        return success
    
    def generate_report(self):
        """Tạo báo cáo kết quả"""
        self.print_header("Generating Report")
        
        report_file = self.results_dir / f'test_report_{self.mode}_{self.timestamp}.json'
        markdown_file = self.results_dir / f'TEST_RESULTS_{self.mode.upper()}_{self.timestamp}.md'
        
        # Save JSON report
        report_data = {
            'timestamp': self.timestamp,
            'test_date': datetime.now().isoformat(),
            'mode': self.mode,
            'config': self.test_config,
            'server': {
                'host': self.server_host,
                'port': self.server_port
            },
            'results': self.all_results
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"✓ JSON report: {report_file}")
        
        # Generate markdown report
        self._generate_markdown_report(markdown_file, report_data)
        print(f"✓ Markdown report: {markdown_file}")
    
    def _generate_markdown_report(self, output_file, data):
        """Tạo báo cáo markdown"""
        with open(output_file, 'w') as f:
            f.write(f"# P2P Performance Test Results - {self.mode.upper()} Mode\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Server:** {self.server_host}:{self.server_port}\n\n")
            f.write(f"**Mode:** {self.mode} - {self.test_config['description']}\n\n")
            
            f.write("---\n\n")
            
            # Scalability tests
            if any(k.startswith('scalability') for k in self.all_results.keys()):
                f.write("## Scalability Tests\n\n")
                
                for preset in self.test_config['scalability_tests']:
                    key = f'scalability_{preset}'
                    if key in self.all_results:
                        data = self.all_results[key]
                        summary = data.get('summary', {})
                        
                        clients = preset.replace('k', ',000')
                        f.write(f"### {clients} Clients\n\n")
                        
                        # Registry operations
                        reg_ops = summary.get('registry_operations', {})
                        if reg_ops:
                            f.write("**Registry Operations:**\n\n")
                            for op, stats in reg_ops.items():
                                f.write(f"- **{op}:**\n")
                                f.write(f"  - Average: {stats.get('avg_ms', 0):.2f} ms\n")
                                f.write(f"  - P95: {stats.get('p95_ms', 0):.2f} ms\n")
                                f.write(f"  - P99: {stats.get('p99_ms', 0):.2f} ms\n\n")
                        
                        # Resources
                        resources = summary.get('resource_usage', {})
                        if resources:
                            f.write("**Resource Usage:**\n\n")
                            f.write(f"- CPU: {resources.get('avg_cpu_percent', 0):.2f}% avg, {resources.get('max_cpu_percent', 0):.2f}% peak\n")
                            f.write(f"- Memory: {resources.get('avg_memory_mb', 0):.2f} MB avg, {resources.get('max_memory_mb', 0):.2f} MB peak\n\n")
            
            # P2P Transfer
            if 'p2p_transfer' in self.all_results:
                f.write("## P2P File Transfer Performance\n\n")
                
                data = self.all_results['p2p_transfer']
                summary = data.get('summary', {})
                
                for category in ['small', 'medium', 'large']:
                    cat_data = summary.get(category, {})
                    if cat_data and cat_data.get('count', 0) > 0:
                        f.write(f"**{category.capitalize()} files:**\n")
                        f.write(f"- Count: {cat_data['count']}\n")
                        f.write(f"- Average Speed: {cat_data.get('avg_speed_mbps', 0):.2f} MB/s\n\n")
            
            # Heartbeat
            if 'heartbeat_comparison' in self.all_results:
                f.write("## Heartbeat Optimization\n\n")
                
                data = self.all_results['heartbeat_comparison']
                comparison = data.get('comparison', {})
                
                total_hb = comparison.get('total_heartbeats', {})
                f.write(f"**Baseline (Fixed):** {total_hb.get('fixed', 0):,} requests\n\n")
                f.write(f"**Optimized (Adaptive):** {total_hb.get('adaptive', 0):,} requests\n\n")
                f.write(f"**Reduction:** {total_hb.get('reduction_percent', 0):.1f}%\n\n")
            
            # Duplicate Detection
            if 'duplicate_detection' in self.all_results:
                f.write("## Duplicate Detection\n\n")
                
                data = self.all_results['duplicate_detection']
                f.write(f"**Files tested:** {data.get('num_files', 0):,}\n\n")
                f.write(f"**Average time per file:** {data.get('avg_time_per_file_ms', 0):.2f} ms\n\n")
                
                stats = data.get('statistics', {})
                if stats:
                    f.write(f"**Duplicates found:** {stats.get('duplicate_files', 0):,}\n\n")
            
            f.write("---\n\n")
            f.write(f"*Generated by P2P Performance Test Runner ({self.mode} mode)*\n")
    
    def run_all(self):
        """Chạy tất cả các test"""
        self.print_header(f"P2P PERFORMANCE TEST RUNNER - {self.mode.upper()} MODE")
        
        print(f"Mode: {self.test_config['description']}")
        print(f"Server: {self.server_host}:{self.server_port}")
        print(f"Timestamp: {self.timestamp}\n")
        
        # Check server
        print("Checking server...")
        if not self.check_server():
            print(f"✗ Server not available at {self.server_host}:{self.server_port}")
            print("\nPlease start the server first:")
            print("  cd Assignment1")
            print("  python bklv-backend/server.py")
            return False
        print("✓ Server is running\n")
        
        # Generate test files
        if not self.generate_test_files():
            print("✗ Failed to generate test files")
            return False
        
        # Track results
        test_results = {}
        
        # Run scalability tests
        self.print_header("SCALABILITY TESTS")
        for preset in self.test_config['scalability_tests']:
            test_results[f'scalability_{preset}'] = self.run_scalability_test(preset)
        
        # Run P2P transfer test
        self.print_header("P2P FILE TRANSFER TEST")
        test_results['p2p_transfer'] = self.run_p2p_transfer_test()
        
        # Run heartbeat test (if enabled)
        if self.test_config['run_heartbeat']:
            self.print_header("HEARTBEAT OPTIMIZATION TEST")
            test_results['heartbeat'] = self.run_heartbeat_comparison()
        
        # Run duplicate detection test (if enabled)
        if self.test_config['run_duplicate']:
            self.print_header("DUPLICATE DETECTION TEST")
            test_results['duplicate'] = self.run_duplicate_detection_test()
        
        # Generate report
        self.generate_report()
        
        # Summary
        self.print_header("TEST SUMMARY")
        
        passed = sum(1 for v in test_results.values() if v)
        total = len(test_results)
        
        for test_name, success in test_results.items():
            status = "✓ PASSED" if success else "✗ FAILED"
            print(f"{test_name}: {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        print(f"Results: {self.results_dir}\n")
        
        return passed == total


def main():
    parser = argparse.ArgumentParser(
        description='P2P Performance Test Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Modes:
  quick     - Quick validation (~10 minutes)
              - Scalability: 1k clients
              - P2P: 5 clients
              
  standard  - Standard performance test (~30 minutes)
              - Scalability: 1k, 10k clients  
              - P2P: 20 clients
              - Heartbeat comparison
              - Duplicate detection
              
  full      - Complete test suite (2-3 hours)
              - Scalability: 1k, 10k, 100k clients
              - P2P: 20 clients
              - Heartbeat comparison
              - Duplicate detection

Examples:
  python test_runner.py --mode quick
  python test_runner.py --mode standard
  python test_runner.py --mode full --server-host p2p-server
        """
    )
    
    parser.add_argument('--mode', 
                       choices=['quick', 'standard', 'full'],
                       default='standard',
                       help='Test mode (default: standard)')
    parser.add_argument('--server-host', 
                       default='127.0.0.1',
                       help='Server hostname (default: 127.0.0.1)')
    parser.add_argument('--server-port', 
                       type=int, 
                       default=9000,
                       help='Server port (default: 9000)')
    
    args = parser.parse_args()
    
    runner = PerformanceTestRunner(
        server_host=args.server_host,
        server_port=args.server_port,
        mode=args.mode
    )
    
    success = runner.run_all()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
