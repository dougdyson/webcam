"""
Tests for async frame processor functionality.
"""
import pytest
import asyncio
import numpy as np
import time
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.processing.processor import FrameProcessor, FrameProcessorError, ProcessingResult
from src.processing.queue import FrameQueue, FrameMetadata, QueuedFrame


@dataclass
class MockDetectionResult:
    """Mock detection result for testing."""
    human_present: bool
    confidence: float = 0.8
    timestamp: float = 0.0
    processing_time: float = 0.0


# Global fixtures for all test classes
@pytest.fixture
def mock_detector():
    """Create mock detector for testing."""
    detector = AsyncMock()
    detector.detect.return_value = MockDetectionResult(
        human_present=True,
        confidence=0.85,
        timestamp=time.time(),
        processing_time=0.05
    )
    return detector

@pytest.fixture
def frame_queue():
    """Create frame queue for testing."""
    return FrameQueue(max_size=5)

@pytest.fixture
def test_frame():
    """Create test frame."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


class TestFrameProcessor:
    """Test cases for FrameProcessor class."""
    
    def test_frame_processor_initialization_success(self, frame_queue, mock_detector):
        """Should initialize frame processor with valid parameters."""
        processor = FrameProcessor(
            frame_queue=frame_queue,
            detector=mock_detector,
            max_concurrent=2,
            processing_timeout=1.0
        )
        
        assert processor.frame_queue == frame_queue
        assert processor.detector == mock_detector
        assert processor.max_concurrent == 2
        assert processor.processing_timeout == 1.0
        assert processor.is_running is False
    
    def test_frame_processor_initialization_invalid_parameters(self, frame_queue, mock_detector):
        """Should validate initialization parameters."""
        # Invalid max_concurrent
        with pytest.raises(FrameProcessorError, match="max_concurrent must be positive"):
            FrameProcessor(frame_queue, mock_detector, max_concurrent=0)
        
        # Invalid timeout
        with pytest.raises(FrameProcessorError, match="processing_timeout must be positive"):
            FrameProcessor(frame_queue, mock_detector, processing_timeout=-1.0)
        
        # Missing frame_queue
        with pytest.raises(FrameProcessorError, match="frame_queue is required"):
            FrameProcessor(None, mock_detector)
        
        # Missing detector
        with pytest.raises(FrameProcessorError, match="detector is required"):
            FrameProcessor(frame_queue, None)
    
    @pytest.mark.asyncio
    async def test_frame_processor_processes_single_frame(self, frame_queue, mock_detector, test_frame):
        """Should process single frame from queue."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Add frame to queue
        frame_queue.put_frame(test_frame, source="test")
        
        # Process frame
        result = await processor.process_next_frame()
        
        assert result is not None
        assert isinstance(result, ProcessingResult)
        assert result.human_present is True
        assert result.confidence == 0.85
        assert result.frame_id is not None
        
        # Detector should have been called
        mock_detector.detect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_frame_processor_handles_empty_queue(self, frame_queue, mock_detector):
        """Should handle empty queue gracefully."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Queue is empty
        result = await processor.process_next_frame(timeout=0.1)
        
        assert result is None
        mock_detector.detect.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_frame_processor_handles_detection_error(self, frame_queue, mock_detector, test_frame):
        """Should handle detector errors gracefully."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Configure detector to raise exception
        mock_detector.detect.side_effect = Exception("Detection failed")
        
        # Add frame to queue
        frame_queue.put_frame(test_frame, source="test")
        
        # Process frame - should handle error
        result = await processor.process_next_frame()
        
        assert result is not None
        assert result.error_occurred is True
        assert "Detection failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_frame_processor_timeout_handling(self, frame_queue, mock_detector, test_frame):
        """Should handle processing timeouts."""
        processor = FrameProcessor(frame_queue, mock_detector, processing_timeout=0.01)
        
        # Configure detector to be slow
        async def slow_detect(frame):
            await asyncio.sleep(0.1)  # Longer than timeout
            return MockDetectionResult(human_present=True)
        
        mock_detector.detect = slow_detect
        
        # Add frame to queue
        frame_queue.put_frame(test_frame, source="test")
        
        # Process frame - should timeout
        result = await processor.process_next_frame()
        
        assert result is not None
        assert result.error_occurred is True
        assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_frame_processor_continuous_processing(self, frame_queue, mock_detector, test_frame):
        """Should process frames continuously."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Add multiple frames
        for i in range(3):
            frame = np.full((100, 100, 3), i, dtype=np.uint8)
            frame_queue.put_frame(frame, source=f"test_{i}")
        
        results = []
        
        # Process all frames
        async def process_all():
            for _ in range(3):
                result = await processor.process_next_frame()
                if result:
                    results.append(result)
        
        await process_all()
        
        assert len(results) == 3
        assert all(r.human_present for r in results)
        assert mock_detector.detect.call_count == 3
    
    @pytest.mark.asyncio
    async def test_frame_processor_concurrent_processing(self, frame_queue, mock_detector, test_frame):
        """Should handle concurrent frame processing."""
        processor = FrameProcessor(frame_queue, mock_detector, max_concurrent=2)
        
        # Add frames to queue
        for i in range(4):
            frame = np.full((100, 100, 3), i, dtype=np.uint8)
            frame_queue.put_frame(frame, source=f"test_{i}")
        
        # Start processor and let it run the continuous processing
        await processor.start()
        
        # Start the continuous processing task
        processing_task = asyncio.create_task(processor.process_frames_continuously())
        
        # Let it process for a short time
        await asyncio.sleep(0.3)
        
        # Stop processor
        await processor.stop()
        
        # Cancel the processing task
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass
        
        # Check statistics
        stats = processor.get_statistics()
        assert stats['frames_processed'] > 0
        assert stats['average_processing_time'] > 0
    
    @pytest.mark.asyncio
    async def test_frame_processor_start_stop_lifecycle(self, frame_queue, mock_detector):
        """Should handle start/stop lifecycle properly."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Initially not running
        assert processor.is_running is False
        
        # Start processor
        await processor.start()
        assert processor.is_running is True
        
        # Stop processor
        await processor.stop()
        assert processor.is_running is False
        
        # Should be able to restart
        await processor.start()
        assert processor.is_running is True
        
        await processor.stop()
    
    @pytest.mark.asyncio
    async def test_frame_processor_statistics_tracking(self, frame_queue, mock_detector, test_frame):
        """Should track processing statistics."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Initial stats
        stats = processor.get_statistics()
        assert stats['frames_processed'] == 0
        assert stats['frames_failed'] == 0
        assert stats['average_processing_time'] == 0.0
        
        # Add and process frame
        frame_queue.put_frame(test_frame, source="test")
        result = await processor.process_next_frame()
        
        # Updated stats
        stats = processor.get_statistics()
        assert stats['frames_processed'] == 1
        assert stats['frames_failed'] == 0
        assert stats['average_processing_time'] > 0
        
        # Process failed frame - reset mock and configure for error
        mock_detector.reset_mock()
        mock_detector.detect.side_effect = Exception("Test error")
        frame_queue.put_frame(test_frame, source="test")
        result = await processor.process_next_frame()
        
        stats = processor.get_statistics()
        assert stats['frames_processed'] == 1  # Failed frames don't increment processed count
        assert stats['frames_failed'] == 1
    
    @pytest.mark.asyncio
    async def test_frame_processor_performance_monitoring(self, frame_queue, mock_detector, test_frame):
        """Should monitor performance metrics."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Process some frames
        for i in range(5):
            frame_queue.put_frame(test_frame, source=f"test_{i}")
            await processor.process_next_frame()
        
        # Get performance stats
        perf_stats = processor.get_performance_stats()
        
        assert 'frames_per_second' in perf_stats
        assert 'average_queue_wait_time' in perf_stats
        assert 'peak_concurrent_tasks' in perf_stats
        assert perf_stats['frames_per_second'] > 0
    
    @pytest.mark.asyncio
    async def test_frame_processor_cleanup_on_shutdown(self, frame_queue, mock_detector):
        """Should clean up resources on shutdown."""
        processor = FrameProcessor(frame_queue, mock_detector)
        
        await processor.start()
        
        # Add some frames
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame_queue.put_frame(test_frame, source="test")
        
        # Stop and verify cleanup
        await processor.stop()
        
        assert processor.is_running is False
        # Should have cleaned up any pending tasks
        assert len(processor._active_tasks) == 0


class TestProcessingResult:
    """Test ProcessingResult data structure."""
    
    def test_processing_result_creation_success(self):
        """Should create processing result for successful detection."""
        result = ProcessingResult(
            frame_id=123,
            human_present=True,
            confidence=0.95,
            processing_time=0.05,
            timestamp=time.time(),
            source="camera",
            error_occurred=False
        )
        
        assert result.frame_id == 123
        assert result.human_present is True
        assert result.confidence == 0.95
        assert result.processing_time == 0.05
        assert result.error_occurred is False
        assert result.error_message is None
    
    def test_processing_result_creation_error(self):
        """Should create processing result for failed detection."""
        result = ProcessingResult(
            frame_id=456,
            human_present=False,
            confidence=0.0,
            processing_time=0.0,
            timestamp=time.time(),
            source="camera",
            error_occurred=True,
            error_message="Detection timeout"
        )
        
        assert result.frame_id == 456
        assert result.error_occurred is True
        assert result.error_message == "Detection timeout"
    
    def test_processing_result_validation(self):
        """Should validate processing result parameters."""
        # Invalid confidence
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            ProcessingResult(
                frame_id=1,
                confidence=1.5,
                human_present=True,
                processing_time=0.1,
                timestamp=time.time(),
                source="test"
            )
        
        # Negative processing time
        with pytest.raises(ValueError, match="Processing time must be non-negative"):
            ProcessingResult(
                frame_id=1,
                confidence=0.8,
                human_present=True,
                processing_time=-0.1,
                timestamp=time.time(),
                source="test"
            )


class TestFrameProcessorError:
    """Test FrameProcessorError exception."""
    
    def test_frame_processor_error_creation(self):
        """Should create FrameProcessorError with message."""
        error = FrameProcessorError("Test processor error")
        assert str(error) == "Test processor error"
        assert isinstance(error, Exception)
    
    def test_frame_processor_error_with_original_error(self):
        """Should chain original exception."""
        original = RuntimeError("Original error")
        error = FrameProcessorError("Processor error", original)
        
        assert str(error) == "Processor error"
        assert error.original_error == original
        assert error.__cause__ == original


class TestFrameProcessorIntegration:
    """Integration tests for frame processor."""
    
    @pytest.mark.asyncio
    async def test_frame_processor_with_real_queue_integration(self, mock_detector):
        """Should integrate properly with FrameQueue."""
        frame_queue = FrameQueue(max_size=3, auto_cleanup=False)
        processor = FrameProcessor(frame_queue, mock_detector)
        
        # Create realistic test scenario
        frames = [
            np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
            np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8),
            np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        ]
        
        # Add frames with metadata
        for i, frame in enumerate(frames):
            metadata = FrameMetadata(frame_id=i, source="integration_test")
            frame_queue.put_frame(frame, metadata=metadata)
        
        # Process all frames
        results = []
        for _ in range(3):
            result = await processor.process_next_frame()
            if result:
                results.append(result)
        
        assert len(results) == 3
        assert all(r.frame_id is not None for r in results)
        assert all(r.source == "integration_test" for r in results)
    
    @pytest.mark.asyncio
    async def test_frame_processor_high_throughput(self, mock_detector):
        """Should handle high throughput processing."""
        frame_queue = FrameQueue(max_size=20, overflow_strategy='drop_oldest')
        processor = FrameProcessor(frame_queue, mock_detector, max_concurrent=4)
        
        # Configure fast mock detector
        mock_detector.detect.return_value = MockDetectionResult(
            human_present=True,
            confidence=0.8,
            processing_time=0.01
        )
        
        # Add many frames quickly
        frame_count = 50
        for i in range(frame_count):
            frame = np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)
            frame_queue.put_frame(frame, source=f"throughput_{i}")
        
        # Start processing
        await processor.start()
        
        # Start the continuous processing task
        processing_task = asyncio.create_task(processor.process_frames_continuously())
        
        # Let it process for a reasonable time
        await asyncio.sleep(1.0)
        
        # Stop and check results
        await processor.stop()
        
        # Cancel the processing task
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass
        
        stats = processor.get_statistics()
        assert stats['frames_processed'] > 10  # Should have processed multiple frames
        
        perf_stats = processor.get_performance_stats()
        assert perf_stats['frames_per_second'] > 5  # Reasonable throughput 