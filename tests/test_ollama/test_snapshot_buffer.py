"""
Tests for SnapshotBuffer functionality.

Phase 2.1 of TDD Ollama Description Endpoint Feature.
Following TDD methodology - RED phase: Write failing tests first.
"""
import pytest
import numpy as np
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# This import will fail initially - that's the RED phase!
try:
    from src.ollama.snapshot_buffer import (
        SnapshotBuffer, 
        Snapshot,
        SnapshotMetadata
    )
except ImportError:
    # Expected to fail during RED phase
    SnapshotBuffer = None
    Snapshot = None
    SnapshotMetadata = None


class TestSnapshotBufferInitialization:
    """RED TESTS: Test SnapshotBuffer initialization and configuration."""
    
    def test_snapshot_buffer_init_with_default_size(self):
        """
        RED TEST: SnapshotBuffer should initialize with default size limit.
        
        This test will fail because SnapshotBuffer doesn't exist yet.
        Expected behavior:
        - Should create buffer with sensible default size (e.g., 10 snapshots)
        - Should initialize empty buffer
        - Should set up thread safety mechanisms
        """
        buffer = SnapshotBuffer()
        
        # Test default configuration
        assert buffer.max_size == 10  # Reasonable default
        assert buffer.current_size == 0
        assert buffer.is_empty() is True
        assert buffer.is_full() is False
        
    def test_snapshot_buffer_init_with_custom_size(self):
        """
        RED TEST: SnapshotBuffer should accept custom size limit.
        """
        buffer = SnapshotBuffer(max_size=5)
        
        assert buffer.max_size == 5
        assert buffer.current_size == 0
        assert buffer.is_empty() is True
        
    def test_snapshot_buffer_init_size_validation(self):
        """
        RED TEST: SnapshotBuffer should validate size parameter.
        """
        # Should reject invalid sizes
        with pytest.raises(ValueError, match="max_size must be positive"):
            SnapshotBuffer(max_size=0)
            
        with pytest.raises(ValueError, match="max_size must be positive"):
            SnapshotBuffer(max_size=-1)
            
        # Should accept reasonable sizes
        buffer = SnapshotBuffer(max_size=1)
        assert buffer.max_size == 1


class TestSnapshotDataStructure:
    """RED TESTS: Test Snapshot and SnapshotMetadata data structures."""
    
    def test_snapshot_metadata_creation(self):
        """
        RED TEST: SnapshotMetadata should track essential information.
        
        This test will fail because SnapshotMetadata doesn't exist yet.
        Expected behavior:
        - Should store timestamp, confidence, human detection details
        - Should provide serialization capabilities
        - Should validate input parameters
        """
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.85,
            human_present=True,
            detection_source="multimodal"
        )
        
        assert isinstance(metadata.timestamp, datetime)
        assert metadata.confidence == 0.85
        assert metadata.human_present is True
        assert metadata.detection_source == "multimodal"
        
    def test_snapshot_creation_with_frame_and_metadata(self):
        """
        RED TEST: Snapshot should combine frame data with metadata.
        """
        # Create sample frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:200, 100:200] = [255, 0, 0]  # Red square
        
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.92,
            human_present=True
        )
        
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        assert np.array_equal(snapshot.frame, frame)
        assert snapshot.metadata == metadata
        assert snapshot.size_bytes > 0  # Should calculate frame size
        
    def test_snapshot_metadata_validation(self):
        """
        RED TEST: SnapshotMetadata should validate confidence ranges.
        """
        # Valid confidence should work
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.75,
            human_present=True
        )
        assert metadata.confidence == 0.75
        
        # Invalid confidence should fail
        with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
            SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=1.5,  # Invalid
                human_present=True
            )


class TestSnapshotBufferAddOperation:
    """RED TESTS: Test adding snapshots to buffer when human detected."""
    
    def test_add_snapshot_when_human_detected(self):
        """
        RED TEST: Should add snapshot when human is detected.
        
        This test will fail because add_snapshot() doesn't exist yet.
        Expected behavior:
        - Should store snapshot with metadata
        - Should increment current_size
        - Should handle circular buffer overflow
        """
        buffer = SnapshotBuffer(max_size=3)
        
        # Create snapshot
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Add snapshot
        result = buffer.add_snapshot(snapshot)
        
        assert result is True  # Successfully added
        assert buffer.current_size == 1
        assert buffer.is_empty() is False
        
    def test_add_multiple_snapshots_within_limit(self):
        """
        RED TEST: Should handle multiple snapshots within size limit.
        """
        buffer = SnapshotBuffer(max_size=3)
        
        # Add multiple snapshots
        for i in range(3):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame[:, :, 0] = i * 50  # Different red intensities
            
            metadata = SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=0.7 + i * 0.1,
                human_present=True
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            
            result = buffer.add_snapshot(snapshot)
            assert result is True
            
        assert buffer.current_size == 3
        assert buffer.is_full() is True
        
    def test_add_snapshot_circular_buffer_overflow(self):
        """
        RED TEST: Should handle circular buffer overflow (replace oldest).
        """
        buffer = SnapshotBuffer(max_size=2)
        
        # Fill buffer
        snapshots = []
        for i in range(3):  # One more than max_size
            frame = np.zeros((50, 50, 3), dtype=np.uint8)
            frame[:, :, 0] = i * 100  # Different intensities for identification
            
            metadata = SnapshotMetadata(
                timestamp=datetime.now() + timedelta(seconds=i),
                confidence=0.8,
                human_present=True
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            snapshots.append(snapshot)
            
            buffer.add_snapshot(snapshot)
            
        # Should still have max_size, but oldest should be replaced
        assert buffer.current_size == 2
        assert buffer.is_full() is True
        
        # Should contain the two most recent snapshots
        latest = buffer.get_latest()
        assert np.array_equal(latest.frame, snapshots[2].frame)  # Most recent
        
    def test_add_snapshot_thread_safety(self):
        """
        RED TEST: Should handle concurrent add operations safely.
        """
        buffer = SnapshotBuffer(max_size=10)
        results = []
        
        def add_snapshots(thread_id):
            for i in range(5):
                frame = np.zeros((30, 30, 3), dtype=np.uint8)
                frame[:, :, 0] = thread_id * 50 + i * 10
                
                metadata = SnapshotMetadata(
                    timestamp=datetime.now(),
                    confidence=0.8,
                    human_present=True
                )
                snapshot = Snapshot(frame=frame, metadata=metadata)
                
                result = buffer.add_snapshot(snapshot)
                results.append(result)
                
        # Start multiple threads
        threads = []
        for tid in range(3):
            thread = threading.Thread(target=add_snapshots, args=(tid,))
            threads.append(thread)
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join()
            
        # Should have added all snapshots without corruption
        assert buffer.current_size == 10  # Buffer should be full
        assert all(results)  # All additions should succeed


class TestSnapshotBufferRetrievalOperations:
    """RED TESTS: Test retrieving snapshots from buffer."""
    
    def test_get_latest_snapshot_from_populated_buffer(self):
        """
        RED TEST: Should retrieve most recent snapshot.
        
        This test will fail because get_latest() doesn't exist yet.
        Expected behavior:
        - Should return most recently added snapshot
        - Should not modify buffer state
        - Should include complete metadata
        """
        buffer = SnapshotBuffer(max_size=5)
        
        # Add snapshots with different timestamps
        snapshots = []
        for i in range(3):
            frame = np.zeros((60, 60, 3), dtype=np.uint8)
            frame[:, :, 1] = i * 80  # Different green intensities
            
            metadata = SnapshotMetadata(
                timestamp=datetime.now() + timedelta(seconds=i),
                confidence=0.9,
                human_present=True
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            snapshots.append(snapshot)
            buffer.add_snapshot(snapshot)
            
        # Retrieve latest
        latest = buffer.get_latest()
        
        assert latest is not None
        assert np.array_equal(latest.frame, snapshots[2].frame)  # Most recent
        assert latest.metadata.timestamp == snapshots[2].metadata.timestamp
        assert buffer.current_size == 3  # Buffer unchanged
        
    def test_get_latest_from_empty_buffer(self):
        """
        RED TEST: Should handle empty buffer gracefully.
        """
        buffer = SnapshotBuffer(max_size=5)
        
        latest = buffer.get_latest()
        assert latest is None
        
    def test_get_latest_with_validation(self):
        """
        RED TEST: Should validate returned snapshot data.
        """
        buffer = SnapshotBuffer(max_size=3)
        
        # Add snapshot
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.95,
            human_present=True
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        buffer.add_snapshot(snapshot)
        
        # Retrieve and validate
        retrieved = buffer.get_latest()
        
        assert retrieved is not None
        assert retrieved.frame.shape == (100, 100, 3)
        assert retrieved.frame.dtype == np.uint8
        assert retrieved.metadata.confidence == 0.95
        assert retrieved.metadata.human_present is True
        
    def test_get_snapshots_by_timeframe(self):
        """
        RED TEST: Should support time-based snapshot retrieval.
        
        This test will fail because get_snapshots_since() doesn't exist yet.
        Expected behavior:
        - Should return snapshots within specified time window
        - Should handle timezone and datetime edge cases
        - Should return empty list if no matches
        """
        buffer = SnapshotBuffer(max_size=10)
        
        # Add snapshots over time
        base_time = datetime.now()
        for i in range(5):
            frame = np.zeros((40, 40, 3), dtype=np.uint8)
            metadata = SnapshotMetadata(
                timestamp=base_time + timedelta(seconds=i * 2),
                confidence=0.8,
                human_present=True
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            buffer.add_snapshot(snapshot)
            
        # Get snapshots from last 5 seconds (should include snapshots at 6s and 8s)
        cutoff_time = base_time + timedelta(seconds=5)
        recent_snapshots = buffer.get_snapshots_since(cutoff_time)
        
        # Should find snapshots with timestamps >= cutoff_time
        # Snapshots are at: 0s, 2s, 4s, 6s, 8s relative to base_time
        # Cutoff is at 5s, so should find: 6s, 8s = 2 snapshots
        assert len(recent_snapshots) == 2  # Should find 2 recent snapshots (6s and 8s)
        for snapshot in recent_snapshots:
            assert snapshot.metadata.timestamp >= cutoff_time
            
    def test_get_buffer_statistics(self):
        """
        RED TEST: Should provide buffer usage statistics.
        """
        buffer = SnapshotBuffer(max_size=5)
        
        # Add some snapshots
        for i in range(3):
            frame = np.zeros((50, 50, 3), dtype=np.uint8)
            metadata = SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=0.8,
                human_present=True
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            buffer.add_snapshot(snapshot)
            
        stats = buffer.get_statistics()
        
        assert isinstance(stats, dict)
        assert stats['current_size'] == 3
        assert stats['max_size'] == 5
        assert stats['utilization_percent'] == 60.0  # 3/5 * 100
        assert 'oldest_timestamp' in stats
        assert 'newest_timestamp' in stats
        assert 'total_memory_bytes' in stats


# Run the tests to see them fail (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 