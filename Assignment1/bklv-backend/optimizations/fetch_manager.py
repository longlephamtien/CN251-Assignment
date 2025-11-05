"""
Fetch Manager for P2P File Transfers (up to 128GB)

This module handles direct peer-to-peer file transfers with progress tracking.
The central server only tracks metadata - actual file data is transferred directly
between clients without server intervention.

Features:
- Chunked streaming for memory efficiency
- Real-time progress tracking
- Size-based integrity verification (no hashing - server doesn't handle file bits)
- Support for very large files (up to 128GB)
- Multi-threaded to support concurrent transfers
"""

import os
import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum


class FetchStatus(Enum):
    """Fetch status states for P2P file transfers"""
    PENDING = "pending"
    CONNECTING = "connecting"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FetchProgress:
    """Progress tracking for a P2P file fetch"""
    file_name: str
    total_size: int
    downloaded_size: int
    status: FetchStatus
    speed_bps: float = 0.0  # Bytes per second
    start_time: float = 0.0
    elapsed_time: float = 0.0
    eta_seconds: float = 0.0
    peer_hostname: str = ""
    peer_ip: str = ""
    error_message: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        if self.total_size == 0:
            return 0.0
        return (self.downloaded_size / self.total_size) * 100.0
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'file_name': self.file_name,
            'total_size': self.total_size,
            'downloaded_size': self.downloaded_size,
            'progress_percent': self.progress_percent,
            'status': self.status.value,
            'speed_bps': self.speed_bps,
            'elapsed_time': self.elapsed_time,
            'eta_seconds': self.eta_seconds,
            'peer_hostname': self.peer_hostname,
            'peer_ip': self.peer_ip,
            'error_message': self.error_message
        }


class FetchSession:
    """Manages a single P2P file fetch session with progress tracking"""
    
    def __init__(self, file_name: str, total_size: int, save_path: str,
                 peer_hostname: str = "", peer_ip: str = "",
                 chunk_size: int = 256*1024):  # 256KB chunks for network transfer
        """
        Initialize fetch session for P2P transfer
        
        Args:
            file_name: Name of the file being fetched
            total_size: Total file size in bytes (from server metadata)
            save_path: Path where file will be saved
            peer_hostname: Hostname of the peer we're fetching from
            peer_ip: IP address of the peer
            chunk_size: Size of chunks for network transfer (default 256KB)
        """
        self.file_name = file_name
        self.total_size = total_size
        self.save_path = save_path
        self.chunk_size = chunk_size
        
        # Progress tracking
        self.progress = FetchProgress(
            file_name=file_name,
            total_size=total_size,
            downloaded_size=0,
            status=FetchStatus.PENDING,
            peer_hostname=peer_hostname,
            peer_ip=peer_ip
        )
        
        # Speed calculation
        self.last_update_time = 0.0
        self.last_update_bytes = 0
        
        # File handle
        self.file_handle = None
        self.lock = threading.Lock()
    
    def start(self):
        """Start the fetch session"""
        with self.lock:
            self.file_handle = open(self.save_path, 'wb')
            self.progress.status = FetchStatus.DOWNLOADING
            self.progress.start_time = time.time()
            self.last_update_time = time.time()
            self.last_update_bytes = 0
    
    def write_chunk(self, data: bytes) -> int:
        """
        Write a data chunk and update progress
        
        Args:
            data: Chunk of data to write
        
        Returns:
            Number of bytes written
        """
        with self.lock:
            if self.file_handle is None:
                raise RuntimeError("Fetch session not started")
            
            # Write to file
            self.file_handle.write(data)
            bytes_written = len(data)
            
            # Update progress
            self.progress.downloaded_size += bytes_written
            
            # Calculate speed and ETA
            current_time = time.time()
            time_delta = current_time - self.last_update_time
            
            if time_delta >= 0.5:  # Update speed every 0.5 seconds
                bytes_delta = self.progress.downloaded_size - self.last_update_bytes
                self.progress.speed_bps = bytes_delta / time_delta if time_delta > 0 else 0
                
                # Calculate ETA
                remaining_bytes = self.total_size - self.progress.downloaded_size
                if self.progress.speed_bps > 0:
                    self.progress.eta_seconds = remaining_bytes / self.progress.speed_bps
                else:
                    self.progress.eta_seconds = 0
                
                # Update tracking variables
                self.last_update_time = current_time
                self.last_update_bytes = self.progress.downloaded_size
            
            # Update elapsed time
            self.progress.elapsed_time = current_time - self.progress.start_time
            
            return bytes_written
    
    def complete(self) -> bool:
        """
        Complete the fetch and verify size integrity
        
        In P2P architecture, we only verify size (not hash) since the server
        doesn't handle file bits - only metadata.
        
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None
            
            # Verify size matches what server reported
            if self.progress.downloaded_size != self.total_size:
                self.progress.status = FetchStatus.FAILED
                self.progress.error_message = (
                    f"Size mismatch: expected {self.total_size:,} bytes, "
                    f"got {self.progress.downloaded_size:,} bytes"
                )
                return False
            
            self.progress.status = FetchStatus.COMPLETED
            return True
    
    def fail(self, error_message: str):
        """Mark fetch as failed"""
        with self.lock:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None
            
            self.progress.status = FetchStatus.FAILED
            self.progress.error_message = error_message
    
    def get_progress(self) -> dict:
        """Get current progress as dictionary"""
        with self.lock:
            return self.progress.to_dict()
    
    def cleanup(self):
        """Cleanup resources"""
        with self.lock:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None


class FetchManager:
    """Manages multiple P2P fetch sessions"""
    
    def __init__(self):
        self.sessions = {}  # fetch_id -> FetchSession
        self.lock = threading.Lock()
    
    def create_session(self, fetch_id: str, file_name: str, 
                      total_size: int, save_path: str,
                      peer_hostname: str = "", peer_ip: str = "") -> FetchSession:
        """
        Create a new P2P fetch session
        
        Args:
            fetch_id: Unique identifier for this fetch
            file_name: Name of the file
            total_size: Total file size (from server metadata)
            save_path: Where to save the file
            peer_hostname: Hostname of peer we're fetching from
            peer_ip: IP address of peer
        
        Returns:
            FetchSession instance
        """
        with self.lock:
            session = FetchSession(
                file_name=file_name,
                total_size=total_size,
                save_path=save_path,
                peer_hostname=peer_hostname,
                peer_ip=peer_ip
            )
            self.sessions[fetch_id] = session
            return session
    
    def get_session(self, fetch_id: str) -> Optional[FetchSession]:
        """Get a fetch session by ID"""
        with self.lock:
            return self.sessions.get(fetch_id)
    
    def remove_session(self, fetch_id: str):
        """Remove a fetch session"""
        with self.lock:
            session = self.sessions.pop(fetch_id, None)
            if session:
                session.cleanup()
    
    def get_all_progress(self) -> dict:
        """Get progress for all active fetches"""
        with self.lock:
            return {
                fetch_id: session.get_progress()
                for fetch_id, session in self.sessions.items()
            }


# Global fetch manager instance
fetch_manager = FetchManager()
