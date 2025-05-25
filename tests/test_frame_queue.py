"""
Tests for frame queue functionality.
"""
import pytest
import numpy as np
import time
import threading
from unittest.mock import Mock, patch
from queue import Empty

from src.processing.queue import FrameQueue, FrameQueueError


class TestFrameQueue:
    """Test cases for FrameQueue class."""
    
    def test_frame_queue_initialization_default(self):
        """Should initialize frame queue with default parameters."""
        queue = FrameQueue()
        
        assert queue.max_size == 10  # Default size
        assert queue.size() == 0
        assert queue.is_empty() is True
        assert queue.is_full() is False
    
    def test_frame_queue_initialization_custom_size(self):
        """Should initialize frame queue with custom max size."""
        queue = FrameQueue(max_size=5)
        
        assert queue.max_size == 5
        assert queue.size() == 0
        assert queue.is_empty() is True
        assert queue.is_full() is False
    
    def test_frame_queue_initialization_invalid_size(self):
        """Should handle invalid queue size."""
        with pytest.raises(FrameQueueError, match="Queue size must be positive"):
            FrameQueue(max_size=0)
        
        with pytest.raises(FrameQueueError, match="Queue size must be positive"):
            FrameQueue(max_size=-1)
    
    def test_frame_queue_put_get_basic(self):
        """Should support basic put/get operations."""
        queue = FrameQueue(max_size=3)
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Put frame
        queue.put_frame(test_frame)
        
        assert queue.size() == 1
        assert queue.is_empty() is False
        assert queue.is_full() is False
        
        # Get frame
        retrieved_frame = queue.get_frame()
        
        assert np.array_equal(test_frame, retrieved_frame)
        assert queue.size() == 0
        assert queue.is_empty() is True
    
    def test_frame_queue_get_from_empty_queue(self):
        """Should handle getting from empty queue."""
        queue = FrameQueue()
        
        frame = queue.get_frame()
        assert frame is None
        
        # With timeout
        frame = queue.get_frame(timeout=0.1)
        assert frame is None
    
    def test_frame_queue_put_get_multiple_frames(self):
        """Should handle multiple frames in FIFO order."""
        queue = FrameQueue(max_size=5)
        frames = []
        
        # Create test frames with different values
        for i in range(3):
            frame = np.full((480, 640, 3), i, dtype=np.uint8)
            frames.append(frame)
            queue.put_frame(frame)
        
        assert queue.size() == 3
        
        # Retrieve frames in FIFO order
        for i in range(3):
            retrieved_frame = queue.get_frame()
            assert np.array_equal(frames[i], retrieved_frame)
        
        assert queue.size() == 0
        assert queue.is_empty() is True
    
    def test_frame_queue_overflow_handling_drop_oldest(self):
        """Should handle queue overflow by dropping oldest frames."""
        queue = FrameQueue(max_size=2, overflow_strategy='drop_oldest')
        
        # Create test frames
        frame1 = np.full((480, 640, 3), 1, dtype=np.uint8)
        frame2 = np.full((480, 640, 3), 2, dtype=np.uint8) 
        frame3 = np.full((480, 640, 3), 3, dtype=np.uint8)
        
        # Fill queue to capacity
        queue.put_frame(frame1)
        queue.put_frame(frame2)
        assert queue.size() == 2
        assert queue.is_full() is True
        
        # Add third frame - should drop frame1
        queue.put_frame(frame3)
        assert queue.size() == 2  # Still at capacity
        
        # Verify frame1 was dropped
        retrieved1 = queue.get_frame()
        retrieved2 = queue.get_frame()
        
        assert np.array_equal(retrieved1, frame2)  # frame1 was dropped
        assert np.array_equal(retrieved2, frame3)
    
    def test_frame_queue_overflow_handling_drop_newest(self):
        """Should handle queue overflow by dropping newest frame."""
        queue = FrameQueue(max_size=2, overflow_strategy='drop_newest')
        
        frame1 = np.full((480, 640, 3), 1, dtype=np.uint8)
        frame2 = np.full((480, 640, 3), 2, dtype=np.uint8)
        frame3 = np.full((480, 640, 3), 3, dtype=np.uint8)
        
        queue.put_frame(frame1)
        queue.put_frame(frame2)
        
        # Try to add third frame - should be dropped
        queue.put_frame(frame3)
        assert queue.size() == 2
        
        # Verify frame3 was dropped
        retrieved1 = queue.get_frame()
        retrieved2 = queue.get_frame()
        
        assert np.array_equal(retrieved1, frame1)
        assert np.array_equal(retrieved2, frame2)
    
    def test_frame_queue_overflow_handling_block(self):
        """Should handle queue overflow by blocking (with timeout)."""
        queue = FrameQueue(max_size=2, overflow_strategy='block')
        
        frame1 = np.full((480, 640, 3), 1, dtype=np.uint8)
        frame2 = np.full((480, 640, 3), 2, dtype=np.uint8)
        frame3 = np.full((480, 640, 3), 3, dtype=np.uint8)
        
        queue.put_frame(frame1)
        queue.put_frame(frame2)
        
        # Try to add third frame with timeout - should raise exception
        with pytest.raises(FrameQueueError, match="Queue put operation timed out"):
            queue.put_frame(frame3, timeout=0.1)
    
    def test_frame_queue_frame_validation(self):
        """Should validate frame format."""
        queue = FrameQueue()
        
        # Valid frame
        valid_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        queue.put_frame(valid_frame)  # Should not raise
        
        # Invalid frame types
        with pytest.raises(FrameQueueError, match="Frame must be numpy array"):
            queue.put_frame("not a frame")
        
        with pytest.raises(FrameQueueError, match="Frame must be numpy array"):
            queue.put_frame(None)
        
        # Invalid frame dimensions
        with pytest.raises(FrameQueueError, match="Frame must be 2D or 3D array"):
            queue.put_frame(np.zeros((100,), dtype=np.uint8))  # 1D
        
        with pytest.raises(FrameQueueError, match="Frame must be 2D or 3D array"):
            queue.put_frame(np.zeros((10, 20, 30, 40), dtype=np.uint8))  # 4D
    
    def test_frame_queue_statistics(self):
        """Should track queue statistics."""
        queue = FrameQueue(max_size=3)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Initial stats
        stats = queue.get_statistics()
        assert stats['frames_added'] == 0
        assert stats['frames_removed'] == 0
        assert stats['frames_dropped'] == 0
        assert stats['current_size'] == 0
        
        # Add some frames
        queue.put_frame(frame)
        queue.put_frame(frame)
        
        stats = queue.get_statistics()
        assert stats['frames_added'] == 2
        assert stats['current_size'] == 2
        
        # Remove frame
        queue.get_frame()
        
        stats = queue.get_statistics()
        assert stats['frames_removed'] == 1
        assert stats['current_size'] == 1
    
    def test_frame_queue_statistics_with_drops(self):
        """Should track dropped frame statistics."""
        queue = FrameQueue(max_size=2, overflow_strategy='drop_oldest')
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Fill queue and cause drops
        queue.put_frame(frame)
        queue.put_frame(frame)
        queue.put_frame(frame)  # Should cause 1 drop
        queue.put_frame(frame)  # Should cause another drop
        
        stats = queue.get_statistics()
        assert stats['frames_added'] == 4
        assert stats['frames_dropped'] == 2
        assert stats['current_size'] == 2
    
    def test_frame_queue_clear(self):
        """Should clear all frames from queue."""
        queue = FrameQueue()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add frames
        queue.put_frame(frame)
        queue.put_frame(frame)
        queue.put_frame(frame)
        
        assert queue.size() == 3
        
        # Clear queue
        queue.clear()
        
        assert queue.size() == 0
        assert queue.is_empty() is True
        
        # Stats should reflect cleared frames
        stats = queue.get_statistics()
        assert stats['current_size'] == 0
    
    def test_frame_queue_thread_safety(self):
        """Should be thread-safe for concurrent operations."""
        queue = FrameQueue(max_size=10)
        frames_to_add = 5
        frames_added = []
        frames_retrieved = []
        
        def producer():
            for i in range(frames_to_add):
                frame = np.full((100, 100, 3), i, dtype=np.uint8)
                frames_added.append(i)
                queue.put_frame(frame)
                time.sleep(0.01)  # Small delay
        
        def consumer():
            for _ in range(frames_to_add):
                frame = queue.get_frame(timeout=1.0)
                if frame is not None:
                    frames_retrieved.append(frame[0, 0, 0])  # Get value
                time.sleep(0.01)  # Small delay
        
        # Start producer and consumer threads
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        producer_thread.join()
        consumer_thread.join()
        
        # All frames should be processed
        assert len(frames_added) == frames_to_add
        assert len(frames_retrieved) == frames_to_add
        assert frames_added == frames_retrieved  # FIFO order preserved
    
    def test_frame_queue_performance_monitoring(self):
        """Should monitor queue performance metrics."""
        queue = FrameQueue(max_size=5)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add frames with some timing
        start_time = time.time()
        for _ in range(3):
            queue.put_frame(frame)
            time.sleep(0.01)
        
        elapsed = time.time() - start_time
        
        # Get performance stats
        perf_stats = queue.get_performance_stats()
        
        assert 'average_put_time' in perf_stats
        assert 'average_get_time' in perf_stats
        assert 'peak_size' in perf_stats
        assert perf_stats['peak_size'] == 3
    
    def test_frame_queue_context_manager(self):
        """Should support context manager protocol."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with FrameQueue(max_size=3) as queue:
            queue.put_frame(frame)
            assert queue.size() == 1
        
        # Queue should be cleared after context exit
        # Note: We can't test this easily since queue is out of scope
        # but the cleanup should have been called


class TestFrameQueueError:
    """Test FrameQueueError exception."""
    
    def test_frame_queue_error_creation(self):
        """Should create FrameQueueError with message."""
        error = FrameQueueError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_frame_queue_error_with_original_error(self):
        """Should chain original exception."""
        original = ValueError("Original error")
        error = FrameQueueError("Frame queue error", original)
        
        assert str(error) == "Frame queue error"
        assert error.original_error == original
        assert error.__cause__ == original


class TestFrameQueueIntegration:
    """Integration tests for frame queue."""
    
    def test_frame_queue_with_real_frames(self):
        """Should handle real-world frame data."""
        queue = FrameQueue(max_size=5)
        
        # Create realistic frame data
        height, width = 720, 1280
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        queue.put_frame(frame)
        retrieved_frame = queue.get_frame()
        
        assert np.array_equal(frame, retrieved_frame)
        assert retrieved_frame.shape == (height, width, 3)
        assert retrieved_frame.dtype == np.uint8
    
    def test_frame_queue_high_throughput(self):
        """Should handle high throughput scenarios."""
        queue = FrameQueue(max_size=20, overflow_strategy='drop_oldest')
        frame_count = 100
        
        # Simulate high throughput
        for i in range(frame_count):
            frame = np.full((240, 320, 3), i % 256, dtype=np.uint8)
            queue.put_frame(frame)
        
        # Should have handled all frames (with some drops)
        stats = queue.get_statistics()
        assert stats['frames_added'] == frame_count
        assert stats['frames_dropped'] == frame_count - queue.max_size
        assert stats['current_size'] == queue.max_size 