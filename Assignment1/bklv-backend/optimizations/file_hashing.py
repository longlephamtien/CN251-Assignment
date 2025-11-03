"""
File Hashing & Deduplication Implementation
Sử dụng SHA256 để identify files và phát hiện duplicates
"""

import hashlib
import os
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

@dataclass
class FileMetadata:
    """Enhanced file metadata với hash"""
    name: str
    size: int
    modified: float
    hash: str  # SHA256 hash
    path: Optional[str] = None
    is_published: bool = False
    published_at: Optional[float] = None
    
    def to_dict(self):
        return asdict(self)


def calculate_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """
    Tính SHA256 hash của file
    
    Args:
        filepath: Đường dẫn đến file
        chunk_size: Kích thước chunk để đọc (mặc định 8KB)
    
    Returns:
        SHA256 hash string (hex)
    
    Performance:
        - 10MB file: ~50ms
        - 100MB file: ~500ms
        - 1GB file: ~5s
    """
    sha256 = hashlib.sha256()
    
    try:
        with open(filepath, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        raise RuntimeError(f"Failed to calculate hash: {e}")


def calculate_quick_hash(filepath: str, sample_size: int = 1024 * 1024) -> str:
    """
    Tính "quick hash" chỉ từ beginning + middle + end của file
    Nhanh hơn nhiều cho files lớn, nhưng có collision risk cao hơn
    
    Args:
        filepath: Đường dẫn đến file
        sample_size: Kích thước mẫu từ mỗi vị trí (mặc định 1MB)
    
    Returns:
        SHA256 hash của samples
    
    Use case: 
        - Quick check trước khi tính full hash
        - Files rất lớn (>1GB)
    """
    sha256 = hashlib.sha256()
    file_size = os.path.getsize(filepath)
    
    # If file nhỏ hơn 3 * sample_size, dùng full hash
    if file_size <= sample_size * 3:
        return calculate_file_hash(filepath)
    
    try:
        with open(filepath, 'rb') as f:
            # Beginning
            f.seek(0)
            sha256.update(f.read(sample_size))
            
            # Middle
            f.seek(file_size // 2)
            sha256.update(f.read(sample_size))
            
            # End
            f.seek(max(0, file_size - sample_size))
            sha256.update(f.read(sample_size))
            
        return sha256.hexdigest()
    except Exception as e:
        raise RuntimeError(f"Failed to calculate quick hash: {e}")


class DuplicateDetector:
    """
    Phát hiện file duplicates dựa trên hash + size
    """
    
    def __init__(self):
        # Index: hash -> list of (hostname, filename, metadata)
        self.hash_index: Dict[str, List[Tuple[str, str, FileMetadata]]] = {}
        
        # Index: (name, size) -> list of (hostname, hash, metadata)
        self.name_size_index: Dict[Tuple[str, int], List[Tuple[str, str, FileMetadata]]] = {}
        
        # Statistics
        self.total_files = 0
        self.unique_hashes = 0
        self.duplicate_files = 0
    
    def add_file(self, hostname: str, filename: str, metadata: FileMetadata):
        """
        Thêm file vào detector
        
        Args:
            hostname: Tên client
            filename: Tên file
            metadata: Metadata của file (bao gồm hash)
        """
        file_hash = metadata.hash
        name_size_key = (filename, metadata.size)
        
        # Add to hash index
        if file_hash not in self.hash_index:
            self.hash_index[file_hash] = []
            self.unique_hashes += 1
        
        self.hash_index[file_hash].append((hostname, filename, metadata))
        
        # Add to name-size index
        if name_size_key not in self.name_size_index:
            self.name_size_index[name_size_key] = []
        
        self.name_size_index[name_size_key].append((hostname, file_hash, metadata))
        
        self.total_files += 1
        
        # Check if duplicate
        if len(self.hash_index[file_hash]) > 1:
            self.duplicate_files += 1
    
    def find_exact_duplicates(self, file_hash: str) -> List[Tuple[str, str, FileMetadata]]:
        """
        Tìm tất cả files có cùng hash (exact duplicates)
        
        Args:
            file_hash: SHA256 hash
        
        Returns:
            List of (hostname, filename, metadata)
        """
        return self.hash_index.get(file_hash, [])
    
    def find_name_size_matches(self, filename: str, size: int) -> List[Tuple[str, str, FileMetadata]]:
        """
        Tìm tất cả files có cùng tên và size (có thể là duplicates)
        
        Args:
            filename: Tên file
            size: Kích thước file
        
        Returns:
            List of (hostname, hash, metadata)
        """
        return self.name_size_index.get((filename, size), [])
    
    def check_duplicate_before_publish(
        self,
        filename: str,
        size: int,
        file_hash: str
    ) -> Dict:
        """
        Kiểm tra duplicate trước khi publish
        
        Returns:
            {
                'is_duplicate': bool,
                'exact_matches': [...],  # Same hash
                'potential_matches': [...],  # Same name+size, different hash
                'recommendation': str
            }
        """
        exact_matches = self.find_exact_duplicates(file_hash)
        name_size_matches = self.find_name_size_matches(filename, size)
        
        # Filter out exact matches from name-size matches
        potential_matches = [
            m for m in name_size_matches
            if m[1] != file_hash  # Different hash
        ]
        
        result = {
            'is_duplicate': len(exact_matches) > 0,
            'exact_matches': [
                {
                    'hostname': h,
                    'filename': f,
                    'size': m.size,
                    'hash': m.hash
                }
                for h, f, m in exact_matches
            ],
            'potential_matches': [
                {
                    'hostname': h,
                    'filename': filename,
                    'size': m.size,
                    'hash': hash_val
                }
                for h, hash_val, m in potential_matches
            ],
            'recommendation': self._get_recommendation(exact_matches, potential_matches)
        }
        
        return result
    
    def _get_recommendation(self, exact_matches, potential_matches) -> str:
        """Generate recommendation message"""
        if len(exact_matches) > 0:
            hosts = ', '.join([h for h, _, _ in exact_matches[:3]])
            return f"⚠️  Exact duplicate found on: {hosts}. Publishing will waste storage."
        elif len(potential_matches) > 0:
            return f"⚠️  {len(potential_matches)} file(s) with same name+size but different content. Verify before publish."
        else:
            return "✅ No duplicates found. Safe to publish."
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        return {
            'total_files': self.total_files,
            'unique_hashes': self.unique_hashes,
            'duplicate_files': self.duplicate_files,
            'duplication_rate': f"{(self.duplicate_files / max(1, self.total_files) * 100):.1f}%",
            'storage_waste_estimate': f"{self.duplicate_files} files"
        }
    
    def remove_file(self, hostname: str, filename: str, file_hash: str):
        """Remove file from detector"""
        # Remove from hash index
        if file_hash in self.hash_index:
            self.hash_index[file_hash] = [
                (h, f, m) for h, f, m in self.hash_index[file_hash]
                if not (h == hostname and f == filename)
            ]
            if not self.hash_index[file_hash]:
                del self.hash_index[file_hash]
                self.unique_hashes -= 1


# ========================================
# INTEGRATION EXAMPLE
# ========================================

class EnhancedClient:
    """
    Example client với file hashing & deduplication
    """
    
    def __init__(self, hostname, listen_port, repo_dir):
        self.hostname = hostname
        self.repo_dir = repo_dir
        
        # File tracking with hashing
        self.local_files: Dict[str, FileMetadata] = {}
        self.published_files: Dict[str, FileMetadata] = {}
        
        # ... other init code ...
    
    def add_file_with_hash(self, filepath: str) -> Optional[FileMetadata]:
        """
        Add file vào local tracking với hash
        
        Args:
            filepath: Đường dẫn đến file
        
        Returns:
            FileMetadata object hoặc None nếu failed
        """
        try:
            filepath = os.path.abspath(os.path.expanduser(filepath))
            if not os.path.isfile(filepath):
                print(f"[ERROR] File not found: {filepath}")
                return None
            
            # Get basic metadata
            stat = os.stat(filepath)
            filename = os.path.basename(filepath)
            
            # Calculate hash (show progress for large files)
            file_size_mb = stat.st_size / (1024 * 1024)
            if file_size_mb > 100:
                print(f"[INFO] Calculating hash for large file ({file_size_mb:.1f} MB)...")
                file_hash = calculate_quick_hash(filepath)
                print(f"[INFO] Quick hash: {file_hash[:16]}...")
            else:
                file_hash = calculate_file_hash(filepath)
            
            # Create metadata
            metadata = FileMetadata(
                name=filename,
                size=stat.st_size,
                modified=stat.st_mtime,
                hash=file_hash,
                path=filepath,
                is_published=False
            )
            
            self.local_files[filename] = metadata
            print(f"[SUCCESS] Added '{filename}' with hash {file_hash[:16]}...")
            
            return metadata
            
        except Exception as e:
            print(f"[ERROR] Failed to add file: {e}")
            return None
    
    def publish_with_duplicate_check(
        self,
        local_path: str,
        fname: str,
        skip_duplicates: bool = True
    ) -> bool:
        """
        Publish file với duplicate checking
        
        Args:
            local_path: Đường dẫn file
            fname: Tên file
            skip_duplicates: Nếu True, skip publish nếu duplicate exists
        
        Returns:
            True nếu published successfully
        """
        try:
            # 1. Calculate hash
            metadata = self.add_file_with_hash(local_path)
            if not metadata:
                return False
            
            # 2. Check duplicates on server
            duplicate_check = self._check_duplicate_on_server(
                fname,
                metadata.size,
                metadata.hash
            )
            
            # 3. Show results
            if duplicate_check['is_duplicate']:
                exact_matches = duplicate_check['exact_matches']
                print(f"\n{duplicate_check['recommendation']}")
                print(f"Exact duplicates found on {len(exact_matches)} host(s):")
                for match in exact_matches:
                    print(f"  • {match['hostname']}: {match['filename']}")
                
                if skip_duplicates:
                    print("\n[INFO] Skipping publish (duplicate exists)")
                    return False
                else:
                    choice = input("\nStill want to publish? (y/n): ").strip().lower()
                    if choice != 'y':
                        print("[INFO] Publish cancelled")
                        return False
            
            # 4. Proceed with publish
            print(f"\n[INFO] Publishing '{fname}'...")
            return self._do_publish(local_path, fname, metadata)
            
        except Exception as e:
            print(f"[ERROR] Publish failed: {e}")
            return False
    
    def _check_duplicate_on_server(self, fname: str, size: int, file_hash: str) -> Dict:
        """
        Query server để check duplicates
        
        In real implementation, gửi request đến server:
        {
            "action": "CHECK_DUPLICATE",
            "data": {
                "filename": fname,
                "size": size,
                "hash": file_hash
            }
        }
        """
        # Placeholder - trong thực tế gọi server API
        return {
            'is_duplicate': False,
            'exact_matches': [],
            'potential_matches': [],
            'recommendation': '✅ No duplicates found.'
        }
    
    def _do_publish(self, local_path: str, fname: str, metadata: FileMetadata) -> bool:
        """Actually publish the file"""
        # ... implementation từ client.py ...
        return True
    
    def verify_downloaded_file(self, filepath: str, expected_hash: str) -> bool:
        """
        Verify file sau khi download bằng cách so sánh hash
        
        Args:
            filepath: Đường dẫn file đã download
            expected_hash: Hash mong đợi
        
        Returns:
            True nếu hash khớp
        """
        try:
            actual_hash = calculate_file_hash(filepath)
            
            if actual_hash == expected_hash:
                print(f"[SUCCESS] File integrity verified ✓")
                return True
            else:
                print(f"[ERROR] File corrupted! Hash mismatch:")
                print(f"  Expected: {expected_hash}")
                print(f"  Actual:   {actual_hash}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Verification failed: {e}")
            return False


# ========================================
# SERVER-SIDE DEDUPLICATION
# ========================================

class ServerWithDeduplication:
    """
    Example server với duplicate detection
    """
    
    def __init__(self):
        # Existing registry
        self.registry = {}
        
        # Duplicate detector
        self.duplicate_detector = DuplicateDetector()
    
    def handle_publish(self, conn, data):
        """
        Handle PUBLISH request với duplicate detection
        """
        hostname = data.get('hostname')
        fname = data.get('fname')
        file_size = data.get('size', 0)
        file_hash = data.get('hash', '')
        
        if not file_hash:
            # Old client without hash support
            print(f"[WARN] Client {hostname} published without hash")
            file_hash = f"no-hash-{time.time()}"
        
        # Create metadata
        metadata = FileMetadata(
            name=fname,
            size=file_size,
            modified=data.get('modified', time.time()),
            hash=file_hash,
            is_published=True,
            published_at=time.time()
        )
        
        # Add to duplicate detector
        self.duplicate_detector.add_file(hostname, fname, metadata)
        
        # Add to registry (existing logic)
        if hostname not in self.registry:
            self.registry[hostname] = {"files": {}}
        
        self.registry[hostname]["files"][fname] = metadata.to_dict()
        
        print(f"[PUBLISH] {hostname} published '{fname}' (hash: {file_hash[:16]}...)")
        
        # Send ACK
        send_json(conn, {"status": "ACK"})
    
    def handle_check_duplicate(self, conn, data):
        """
        Handle CHECK_DUPLICATE request
        """
        fname = data.get('filename')
        size = data.get('size')
        file_hash = data.get('hash')
        
        result = self.duplicate_detector.check_duplicate_before_publish(
            fname, size, file_hash
        )
        
        send_json(conn, {
            "status": "OK",
            **result
        })
    
    def get_dedup_stats(self):
        """Get deduplication statistics"""
        return self.duplicate_detector.get_stats()


# ========================================
# BENCHMARKS & TESTING
# ========================================

def benchmark_hashing():
    """
    Benchmark hash performance với different file sizes
    """
    print("=" * 60)
    print("FILE HASHING BENCHMARK")
    print("=" * 60)
    
    # Create test files
    test_sizes = [
        (1024, "1 KB"),
        (1024 * 1024, "1 MB"),
        (10 * 1024 * 1024, "10 MB"),
        (100 * 1024 * 1024, "100 MB"),
    ]
    
    for size, label in test_sizes:
        # Create test file
        test_file = f"/tmp/test_{size}.bin"
        with open(test_file, 'wb') as f:
            f.write(os.urandom(size))
        
        # Full hash
        start = time.time()
        full_hash = calculate_file_hash(test_file)
        full_time = time.time() - start
        
        # Quick hash
        start = time.time()
        quick_hash = calculate_quick_hash(test_file)
        quick_time = time.time() - start
        
        print(f"\n{label} file:")
        print(f"  Full hash:  {full_time*1000:.2f} ms")
        print(f"  Quick hash: {quick_time*1000:.2f} ms")
        print(f"  Speedup:    {full_time/quick_time:.1f}x")
        
        # Cleanup
        os.remove(test_file)


def send_json(conn, obj):
    """Placeholder"""
    pass


if __name__ == "__main__":
    print("File Hashing & Deduplication Module\n")
    
    # Run benchmark
    try:
        benchmark_hashing()
    except Exception as e:
        print(f"Benchmark failed: {e}")
    
    # Demo duplicate detector
    print("\n" + "=" * 60)
    print("DUPLICATE DETECTOR DEMO")
    print("=" * 60 + "\n")
    
    detector = DuplicateDetector()
    
    # Add some files
    file1 = FileMetadata(
        name="document.pdf",
        size=1024,
        modified=time.time(),
        hash="abc123"
    )
    
    file2 = FileMetadata(
        name="document.pdf",
        size=1024,
        modified=time.time(),
        hash="abc123"  # Same hash = duplicate
    )
    
    file3 = FileMetadata(
        name="document.pdf",
        size=1024,
        modified=time.time(),
        hash="def456"  # Different hash
    )
    
    detector.add_file("client1", "document.pdf", file1)
    detector.add_file("client2", "document.pdf", file2)
    detector.add_file("client3", "document.pdf", file3)
    
    # Check for duplicates
    result = detector.check_duplicate_before_publish("document.pdf", 1024, "abc123")
    
    print("Duplicate check result:")
    print(json.dumps(result, indent=2))
    
    print("\nDetector stats:")
    print(json.dumps(detector.get_stats(), indent=2))
