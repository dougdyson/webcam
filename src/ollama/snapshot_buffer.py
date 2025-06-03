"""
Snapshot buffer system for storing webcam frames when humans are detected.

This module provides a circular buffer for efficiently managing webcam snapshots
with metadata, optimized for Ollama description processing. Supports thread-safe
operations and memory management.

Key Features:
- Circular buffer with configurable size limits
- Thread-safe concurrent access
- Metadata tracking (timestamp, confidence, detection info)
- Memory usage optimization
- Time-based snapshot retrieval
"""
import threading
import logging
from collections import deque
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SnapshotMetadata:
    """
    Metadata for webcam snapshots when humans are detected.
    
    Tracks essential information about the detection event and 
    provides validation for confidence values.
    """
    timestamp: datetime
    confidence: float
    human_present: bool
    detection_source: str = "multimodal"
    
    def __post_init__(self):
        """Validate metadata parameters."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0 and 1")


@dataclass
class Snapshot:
    """
    Complete snapshot containing frame data and metadata.
    
    Combines the webcam frame with detection metadata for
    efficient storage and retrieval in the snapshot buffer.
    """
    frame: np.ndarray
    metadata: SnapshotMetadata
    
    @property
    def size_bytes(self) -> int:
        """Calculate memory size of the snapshot in bytes."""
        return self.frame.nbytes


class SnapshotBuffer:
    """
    Thread-safe circular buffer for storing webcam snapshots.
    
    Manages a fixed-size buffer of snapshots with automatic cleanup
    of oldest entries when the buffer is full. Optimized for concurrent
    access and memory efficiency.
    """
    
    def __init__(self, max_size: int = 10):
        """
        Initialize snapshot buffer with size limit.
        
        Args:
            max_size: Maximum number of snapshots to store
            
        Raises:
            ValueError: If max_size is not positive
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")
            
        self.max_size = max_size
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        
        logger.debug(f"SnapshotBuffer initialized with max_size={max_size}")
    
    @property
    def current_size(self) -> int:
        """Get current number of snapshots in buffer."""
        with self._lock:
            return len(self._buffer)
    
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        with self._lock:
            return len(self._buffer) == 0
    
    def is_full(self) -> bool:
        """Check if buffer is at maximum capacity."""
        with self._lock:
            return len(self._buffer) == self.max_size
    
    def add_snapshot(self, snapshot: Snapshot) -> bool:
        """
        Add snapshot to buffer (circular, replaces oldest when full).
        
        Args:
            snapshot: Snapshot to add to buffer
            
        Returns:
            True if successfully added
            
        Note:
            When buffer is full, oldest snapshot is automatically removed.
        """
        try:
            with self._lock:
                # deque with maxlen automatically handles circular buffer behavior
                self._buffer.append(snapshot)
                
                logger.debug(f"Added snapshot to buffer. Size: {len(self._buffer)}/{self.max_size}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to add snapshot to buffer: {e}")
            return False
    
    def get_latest(self) -> Optional[Snapshot]:
        """
        Get the most recently added snapshot.
        
        Returns:
            Most recent snapshot or None if buffer is empty
        """
        with self._lock:
            if len(self._buffer) == 0:
                return None
            return self._buffer[-1]  # Last added (most recent)
    
    def get_snapshots_since(self, cutoff_time: datetime) -> List[Snapshot]:
        """
        Get all snapshots newer than the specified time.
        
        Args:
            cutoff_time: Only return snapshots after this time
            
        Returns:
            List of snapshots matching the time criteria
        """
        with self._lock:
            matching_snapshots = []
            for snapshot in self._buffer:
                if snapshot.metadata.timestamp >= cutoff_time:
                    matching_snapshots.append(snapshot)
            return matching_snapshots
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get buffer usage and memory statistics.
        
        Returns:
            Dictionary with buffer statistics
        """
        with self._lock:
            if len(self._buffer) == 0:
                return {
                    'current_size': 0,
                    'max_size': self.max_size,
                    'utilization_percent': 0.0,
                    'oldest_timestamp': None,
                    'newest_timestamp': None,
                    'total_memory_bytes': 0
                }
            
            # Calculate statistics
            timestamps = [s.metadata.timestamp for s in self._buffer]
            total_memory = sum(s.size_bytes for s in self._buffer)
            
            stats = {
                'current_size': len(self._buffer),
                'max_size': self.max_size,
                'utilization_percent': (len(self._buffer) / self.max_size) * 100.0,
                'oldest_timestamp': min(timestamps),
                'newest_timestamp': max(timestamps),
                'total_memory_bytes': total_memory
            }
            
            return stats
    
    def clear(self) -> None:
        """Clear all snapshots from buffer."""
        with self._lock:
            self._buffer.clear()
            logger.debug("SnapshotBuffer cleared")
    
    def __len__(self) -> int:
        """Get current buffer size."""
        return self.current_size
    
    def __repr__(self) -> str:
        """String representation of buffer state."""
        with self._lock:
            return f"SnapshotBuffer(size={len(self._buffer)}/{self.max_size})" 