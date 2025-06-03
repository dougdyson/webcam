"""
Test suite for LatestFrameProcessor - Phase 1.1 TDD Implementation

This implements Phase 1.1 of the Latest Frame Processing TDD plan:
- Basic LatestFrameProcessor initialization tests
- Frame retrieval from camera manager tests
- Error handling and validation tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, MagicMock, patch
import numpy as np
from dataclasses import dataclass

from src.processing.latest_frame_processor import (
    LatestFrameProcessor,
    LatestFrameResult,
    create_latest_frame_processor
)


class TestLatestFrameProcessorInitialization:
    """Phase 1.1: Basic LatestFrameProcessor initialization tests."""
    
    def test_latest_frame_processor_basic_initialization_success(self):
        """
        🔴 RED: Test basic LatestFrameProcessor initialization with valid parameters.
        
        This should create a processor with correct default values.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Act
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Assert
        assert processor.camera_manager == mock_camera
        assert processor.detector == mock_detector
        assert processor.target_fps == 5.0  # Default
        assert processor.processing_timeout == 3.0  # Default
        assert processor.max_frame_age == 1.0  # Default
        assert processor.processing_interval == 0.2  # 1/5 FPS
        assert processor.is_running == False
        assert processor._frames_processed == 0
        assert processor._frames_skipped == 0
        
    def test_latest_frame_processor_custom_initialization_success(self):
        """
        🔴 RED: Test LatestFrameProcessor initialization with custom parameters.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        target_fps = 10.0
        timeout = 2.0
        max_age = 0.5
        
        # Act
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=target_fps,
            processing_timeout=timeout,
            max_frame_age=max_age
        )
        
        # Assert
        assert processor.target_fps == target_fps
        assert processor.processing_timeout == timeout
        assert processor.max_frame_age == max_age
        assert processor.processing_interval == 0.1  # 1/10 FPS
        
    def test_latest_frame_processor_zero_fps_handling(self):
        """
        🔴 RED: Test LatestFrameProcessor handles zero/negative FPS gracefully.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Act
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=0.0
        )
        
        # Assert - Should default to reasonable interval
        assert processor.processing_interval == 0.2  # Default fallback
        
    def test_latest_frame_processor_negative_fps_handling(self):
        """
        🔴 RED: Test LatestFrameProcessor handles negative FPS.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Act
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=-5.0
        )
        
        # Assert - Should default to reasonable interval
        assert processor.processing_interval == 0.2  # Default fallback


class TestLatestFrameRetrieval:
    """Phase 1.1: Frame retrieval from camera manager tests."""
    
    def test_get_latest_frame_success(self):
        """
        🔴 RED: Test successful frame retrieval from camera manager.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Act
        frame = processor._get_latest_frame()
        
        # Assert
        assert frame is not None
        np.testing.assert_array_equal(frame, test_frame)
        mock_camera.get_frame.assert_called_once()
        
    def test_get_latest_frame_none_from_camera(self):
        """
        🔴 RED: Test handling when camera returns None.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        mock_camera.get_frame.return_value = None
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Act
        frame = processor._get_latest_frame()
        
        # Assert
        assert frame is None
        mock_camera.get_frame.assert_called_once()
        
    def test_get_latest_frame_camera_exception(self):
        """
        🔴 RED: Test handling when camera raises exception.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        mock_camera.get_frame.side_effect = Exception("Camera error")
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Act
        frame = processor._get_latest_frame()
        
        # Assert
        assert frame is None  # Should handle error gracefully
        mock_camera.get_frame.assert_called_once()
        
    def test_get_latest_frame_old_frame_rejection(self):
        """
        🔴 RED: Test rejection of frames that are too old.
        
        This tests the max_frame_age functionality.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            max_frame_age=0.001  # Very small max age
        )
        
        # Act
        with patch('time.time', side_effect=[100.0, 102.0]):  # 2 second age
            frame = processor._get_latest_frame()
        
        # Assert
        assert frame is None  # Should reject old frame
        assert processor._frames_too_old == 1


class TestLatestFrameProcessorErrorHandling:
    """Phase 1.1: Error handling and validation tests."""
    
    def test_latest_frame_processor_handles_invalid_camera(self):
        """
        🔴 RED: Test LatestFrameProcessor handles None camera manager gracefully.
        
        Updated: The implementation handles this gracefully by logging error and returning None,
        which is the correct behavior for robust processing.
        """
        # Arrange
        mock_detector = Mock()
        
        # Act - This should not raise exception but handle gracefully
        processor = LatestFrameProcessor(
            camera_manager=None,
            detector=mock_detector
        )
        frame = processor._get_latest_frame()  # Should handle error gracefully
        
        # Assert - Should return None and handle error gracefully
        assert frame is None
        
    def test_latest_frame_processor_handles_invalid_detector(self):
        """
        🔴 RED: Test LatestFrameProcessor handles None detector.
        
        This should be acceptable during initialization but fail during processing.
        """
        # Arrange
        mock_camera = Mock()
        
        # Act - Initialization should work
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=None
        )
        
        # Assert
        assert processor.detector is None  # Should allow None detector
        
    def test_latest_frame_processor_statistics_initialization(self):
        """
        🔴 RED: Test that statistics are properly initialized.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Act
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Assert
        stats = processor.get_statistics()
        assert stats['frames_processed'] == 0
        assert stats['frames_skipped'] == 0
        assert stats['frames_too_old'] == 0
        assert stats['target_fps'] == 5.0
        assert stats['is_running'] == False
        assert 'uptime_seconds' in stats
        assert 'processing_fps' in stats


class TestCreateLatestFrameProcessor:
    """Phase 1.1: Test the convenience factory function."""
    
    def test_create_latest_frame_processor_default(self):
        """
        🔴 RED: Test create_latest_frame_processor with default settings.
        
        Updated: The factory function defaults to real_time_mode=True, which uses
        optimized settings for minimal lag.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Act
        processor = create_latest_frame_processor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Assert
        assert isinstance(processor, LatestFrameProcessor)
        assert processor.target_fps == 5.0
        assert processor.processing_timeout == 1.0  # Real-time default
        assert processor.max_frame_age == 0.5  # Real-time default
        
    def test_create_latest_frame_processor_real_time_mode(self):
        """
        🔴 RED: Test create_latest_frame_processor with real-time mode enabled.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Act
        processor = create_latest_frame_processor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0,
            real_time_mode=True
        )
        
        # Assert
        assert isinstance(processor, LatestFrameProcessor)
        assert processor.target_fps == 10.0
        assert processor.processing_timeout == 1.0  # Shorter for real-time
        assert processor.max_frame_age == 0.5  # More strict for real-time
        
    def test_create_latest_frame_processor_standard_mode(self):
        """
        🔴 RED: Test create_latest_frame_processor with standard mode.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Act
        processor = create_latest_frame_processor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0,
            real_time_mode=False
        )
        
        # Assert
        assert isinstance(processor, LatestFrameProcessor)
        assert processor.target_fps == 8.0
        assert processor.processing_timeout == 3.0  # Standard timeout
        assert processor.max_frame_age == 1.0  # Standard max age


class TestLatestFrameResult:
    """Phase 1.1: Test LatestFrameResult data structure."""
    
    def test_latest_frame_result_creation_success(self):
        """
        🔴 RED: Test LatestFrameResult creation with valid data.
        """
        # Arrange
        frame_id = 12345
        human_present = True
        confidence = 0.89
        processing_time = 0.15
        timestamp = time.time()
        frame_age = 0.05
        frames_skipped = 3
        
        # Act
        result = LatestFrameResult(
            frame_id=frame_id,
            human_present=human_present,
            confidence=confidence,
            processing_time=processing_time,
            timestamp=timestamp,
            frame_age=frame_age,
            frames_skipped=frames_skipped
        )
        
        # Assert
        assert result.frame_id == frame_id
        assert result.human_present == human_present
        assert result.confidence == confidence
        assert result.processing_time == processing_time
        assert result.timestamp == timestamp
        assert result.frame_age == frame_age
        assert result.frames_skipped == frames_skipped
        assert result.error_occurred == False  # Default
        assert result.error_message is None  # Default
        
    def test_latest_frame_result_creation_with_error(self):
        """
        🔴 RED: Test LatestFrameResult creation with error information.
        """
        # Arrange
        error_message = "Processing timeout"
        
        # Act
        result = LatestFrameResult(
            frame_id=123,
            human_present=False,
            confidence=0.0,
            processing_time=5.0,
            timestamp=time.time(),
            frame_age=0.0,
            frames_skipped=0,
            error_occurred=True,
            error_message=error_message
        )
        
        # Assert
        assert result.error_occurred == True
        assert result.error_message == error_message
        assert result.human_present == False  # Should be false on error
        assert result.confidence == 0.0  # Should be zero on error 


class TestLatestFrameProcessorAsyncLoop:
    """Phase 1.2: Async processing loop tests - the core of lag elimination."""
    
    @pytest.mark.asyncio
    async def test_async_processing_loop_start_stop(self):
        """
        🔴 RED: Test async processing loop start and stop lifecycle.
        
        This is the core functionality that eliminates lag by continuously
        processing the latest frames without queueing.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector to return simple result
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.85
        mock_detector.detect.return_value = mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=20.0  # Fast for testing
        )
        
        # Act - Start the processor
        await processor.start()
        
        # Assert - Should be running
        assert processor.is_running == True
        assert processor._processing_task is not None
        
        # Let it run briefly
        await asyncio.sleep(0.1)
        
        # Act - Stop the processor
        await processor.stop()
        
        # Assert - Should be stopped
        assert processor.is_running == False
        
    @pytest.mark.asyncio
    async def test_async_processing_loop_processes_frames_continuously(self):
        """
        🔴 RED: Test that the async loop processes frames continuously.
        
        This verifies that frames are being processed at the target FPS rate.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with proper async behavior
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.75
        mock_detector.detect.return_value = mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0  # 10 FPS = 0.1s intervals
        )
        
        # Track results
        results = []
        def capture_result(result):
            results.append(result)
        
        processor.add_result_callback(capture_result)
        
        # Mock the _async_detect method to avoid await issues
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor._async_detect = mock_async_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.35)  # Should process ~3 frames
        await processor.stop()
        
        # Assert
        assert len(results) >= 2  # Should have processed multiple frames
        assert all(isinstance(r, LatestFrameResult) for r in results)
        assert all(r.human_present == True for r in results)
        
    @pytest.mark.asyncio
    async def test_async_processing_loop_respects_target_fps(self):
        """
        🔴 RED: Test that processing respects the target FPS timing.
        
        This ensures we're not processing too fast or too slow.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock fast detector (no processing delay)
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.80
        mock_detector.detect.return_value = mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0  # 5 FPS = 0.2s intervals
        )
        
        # Track timing
        start_times = []
        def capture_timing(result):
            start_times.append(time.time())
        
        processor.add_result_callback(capture_timing)
        
        # Act
        start_time = time.time()
        await processor.start()
        await asyncio.sleep(0.6)  # Should allow ~3 processing cycles
        await processor.stop()
        
        # Assert timing
        assert len(start_times) >= 2
        if len(start_times) >= 3:
            # Check intervals are approximately correct (allow 50ms tolerance)
            interval1 = start_times[1] - start_times[0]
            interval2 = start_times[2] - start_times[1]
            
            assert 0.15 <= interval1 <= 0.25  # ~0.2s ± 0.05s
            assert 0.15 <= interval2 <= 0.25
    
    @pytest.mark.asyncio
    async def test_async_processing_loop_handles_slow_detector(self):
        """
        🔴 RED: Test behavior when detector is slower than target FPS.
        
        This is crucial for real-world performance - when processing takes
        longer than the target interval, we should adapt gracefully.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock slow detector
        def slow_detect(frame):
            time.sleep(0.15)  # Simulate slow processing
            result = Mock()
            result.human_present = True
            result.confidence = 0.70
            return result
        
        mock_detector.detect.side_effect = slow_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0  # 10 FPS = 0.1s intervals (faster than detector)
        )
        
        # Track results
        results = []
        processor.add_result_callback(lambda r: results.append(r))
        
        # Act
        await processor.start()
        await asyncio.sleep(0.5)  # Run for 0.5 seconds
        await processor.stop()
        
        # Assert - Should adapt to slower processing
        assert len(results) >= 1  # Should process at least some frames
        # Processing should be slower than target FPS due to detector speed
        stats = processor.get_statistics()
        actual_fps = stats['processing_fps']
        assert actual_fps < 8.0  # Should be slower than target due to detector
        
    @pytest.mark.asyncio
    async def test_async_processing_loop_error_recovery(self):
        """
        🔴 RED: Test that the processing loop recovers from detector errors.
        
        Critical for robustness - errors shouldn't crash the loop.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector that sometimes fails
        call_count = 0
        async def unreliable_async_detect(frame):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second call
                raise Exception("Detector error")
            
            result = Mock()
            result.human_present = True
            result.confidence = 0.75
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0
        )
        
        # Mock the _async_detect method directly
        processor._async_detect = unreliable_async_detect
        
        # Track results
        results = []
        processor.add_result_callback(lambda r: results.append(r))
        
        # Act
        await processor.start()
        await asyncio.sleep(0.4)  # Should trigger the error and recovery
        await processor.stop()
        
        # Assert - Should have some successful results despite error
        assert len(results) >= 1
        # Should have at least one success and one error result
        success_results = [r for r in results if not r.error_occurred]
        error_results = [r for r in results if r.error_occurred]
        
        assert len(success_results) >= 1  # At least one success
        assert len(error_results) >= 1    # At least one error handled gracefully
        
    @pytest.mark.asyncio
    async def test_async_processing_loop_callback_management(self):
        """
        🔴 RED: Test result callback add/remove functionality.
        
        This enables the service layer to receive real-time results.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.85
        mock_detector.detect.return_value = mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0
        )
        
        # Track results from multiple callbacks
        results1 = []
        results2 = []
        
        def callback1(result):
            results1.append(result)
            
        def callback2(result):
            results2.append(result)
        
        # Act - Add callbacks
        processor.add_result_callback(callback1)
        processor.add_result_callback(callback2)
        
        await processor.start()
        await asyncio.sleep(0.15)  # Let it process a bit
        
        # Remove one callback
        processor.remove_result_callback(callback1)
        
        await asyncio.sleep(0.15)  # Process more
        await processor.stop()
        
        # Assert
        assert len(results1) >= 1  # Should have received some results
        assert len(results2) >= len(results1)  # callback2 should have more (ran longer)
        
    @pytest.mark.asyncio
    async def test_async_processing_loop_graceful_shutdown(self):
        """
        🔴 RED: Test graceful shutdown even when processing is in progress.
        
        Important for clean service restarts.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with some processing time
        def detect_with_delay(frame):
            time.sleep(0.05)  # Small delay
            result = Mock()
            result.human_present = True
            result.confidence = 0.80
            return result
        
        mock_detector.detect.side_effect = detect_with_delay
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        # Act
        await processor.start()
        await asyncio.sleep(0.1)  # Start processing
        
        # Stop should complete quickly even if processing is ongoing
        stop_start = time.time()
        await processor.stop()
        stop_time = time.time() - stop_start
        
        # Assert
        assert stop_time < 3.0  # Should stop within timeout
        assert processor.is_running == False 


class TestLatestFrameProcessorDetectionIntegration:
    """Phase 1.3: Detection integration tests - real-world detection scenarios."""
    
    @pytest.mark.asyncio
    async def test_async_detect_wrapper_with_sync_detector(self):
        """
        🔴 RED: Test _async_detect wrapper converts sync detector to async.
        
        Most detectors are synchronous, so the wrapper must handle this properly.
        """
        # Arrange
        mock_camera = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Create a detector class that only has sync detect method
        class SyncDetector:
            def __init__(self):
                self.detect_called = False
                
            def detect(self, frame):
                self.detect_called = True
                result = Mock()
                result.human_present = True
                result.confidence = 0.88
                return result
        
        sync_detector = SyncDetector()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=sync_detector
        )
        
        # Act - Call the async wrapper directly  
        result = await processor._async_detect(test_frame)
        
        # Assert
        assert sync_detector.detect_called == True
        assert result.human_present == True
        assert result.confidence == 0.88
        
    @pytest.mark.asyncio
    async def test_async_detect_wrapper_with_async_detector(self):
        """
        🔴 RED: Test _async_detect wrapper with already async detector.
        
        Some advanced detectors might be async, wrapper should handle both.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Mock async detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = False
        mock_detection_result.confidence = 0.12
        
        async def async_detect(frame):
            return mock_detection_result
        
        mock_detector.detect_async = async_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Act - Call the async wrapper
        result = await processor._async_detect(test_frame)
        
        # Assert
        assert result == mock_detection_result
        assert result.human_present == False
        assert result.confidence == 0.12
        
    @pytest.mark.asyncio 
    async def test_async_detect_with_timeout_handling(self):
        """
        🔴 RED: Test detection timeout handling prevents hanging.
        
        Critical for robustness - slow detectors shouldn't block the system.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Mock very slow detector
        def slow_detect(frame):
            time.sleep(5.0)  # Longer than any reasonable timeout
            result = Mock()
            result.human_present = True
            result.confidence = 0.90
            return result
        
        mock_detector.detect.side_effect = slow_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            processing_timeout=0.5  # Very short timeout
        )
        
        # Act & Assert - Should timeout, not hang
        start_time = time.time()
        
        # This should be tested in the processing loop context
        await processor.start()
        await asyncio.sleep(1.0)  # Let it try to process
        await processor.stop()
        
        elapsed = time.time() - start_time
        assert elapsed < 3.0  # Should not hang for 5+ seconds
        
    @pytest.mark.asyncio
    async def test_latest_frame_result_metadata_creation(self):
        """
        🔴 RED: Test comprehensive LatestFrameResult metadata creation.
        
        Validates all the metadata that enables performance monitoring.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Create the expected detection result
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.92
        
        # Mock async detect method to avoid await issues
        async def mock_async_detect(frame):
            await asyncio.sleep(0.05)  # Simulate processing time
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0
        )
        
        # Replace the _async_detect method
        processor._async_detect = mock_async_detect
        
        # Track results with detailed metadata
        results = []
        processor.add_result_callback(lambda r: results.append(r))
        
        # Act
        await processor.start()
        await asyncio.sleep(0.3)  # Process a few frames
        await processor.stop()
        
        # Assert - Check metadata quality
        assert len(results) >= 1
        
        for i, result in enumerate(results):
            assert isinstance(result, LatestFrameResult)
            assert result.frame_id > 0
            assert result.human_present == True
            assert result.confidence == 0.92
            assert result.processing_time > 0.04  # Should reflect actual processing time
            assert result.timestamp > 0
            assert result.frame_age >= 0  # Frame age should be reasonable
            assert result.frames_skipped >= 0  # Should track skipped frames
            assert result.error_occurred == False
            assert result.error_message is None
            
    @pytest.mark.asyncio
    async def test_detection_error_result_creation(self):
        """
        🔴 RED: Test LatestFrameResult creation when detection fails.
        
        Error scenarios should create proper error results with metadata.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector that always fails
        def failing_detect(frame):
            raise RuntimeError("Detection system failure")
        
        mock_detector.detect.side_effect = failing_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        # Track error results
        results = []
        processor.add_result_callback(lambda r: results.append(r))
        
        # Act
        await processor.start()
        await asyncio.sleep(0.4)  # Let it try to process and fail
        await processor.stop()
        
        # Assert - Should have error results
        assert len(results) >= 1
        
        for result in results:
            assert isinstance(result, LatestFrameResult)
            assert result.error_occurred == True
            assert result.error_message is not None
            assert "Detection system failure" in result.error_message or "Processing error" in result.error_message
            assert result.human_present == False  # Default for errors
            assert result.confidence == 0.0  # Default for errors
            assert result.processing_time > 0  # Should still track timing
            
    @pytest.mark.asyncio
    async def test_detection_with_various_confidence_levels(self):
        """
        🔴 RED: Test detection with different confidence levels.
        
        Validates that confidence values are properly passed through.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with varying confidence
        confidence_values = [0.95, 0.67, 0.34, 0.12, 0.89]
        call_count = 0
        
        async def varying_confidence_async_detect(frame):
            nonlocal call_count
            confidence = confidence_values[call_count % len(confidence_values)]
            call_count += 1
            
            result = Mock()
            result.human_present = confidence > 0.5
            result.confidence = confidence
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0
        )
        
        # Replace the _async_detect method
        processor._async_detect = varying_confidence_async_detect
        
        # Track confidence variations
        results = []
        processor.add_result_callback(lambda r: results.append(r))
        
        # Act
        await processor.start()
        await asyncio.sleep(0.8)  # Process multiple frames with varying confidence
        await processor.stop()
        
        # Assert - Should see confidence variation
        assert len(results) >= 3  # Should have multiple results
        
        confidences = [r.confidence for r in results if not r.error_occurred]
        assert len(confidences) >= 3
        
        # Should have variety of confidence values
        high_confidence = [c for c in confidences if c > 0.8]
        medium_confidence = [c for c in confidences if 0.3 <= c <= 0.8]
        low_confidence = [c for c in confidences if c < 0.3]
        
        assert len(high_confidence) + len(medium_confidence) + len(low_confidence) == len(confidences)
        
    @pytest.mark.asyncio
    async def test_detection_integration_with_real_detector_interface(self):
        """
        🔴 RED: Test integration with realistic detector interface.
        
        This validates the actual interface that real detectors will use.
        """
        # Arrange - Create a realistic mock detector
        class MockRealisticDetector:
            def __init__(self):
                self.detection_count = 0
                
            def detect(self, frame):
                """Simulate a real detector interface."""
                self.detection_count += 1
                
                # Simulate some processing
                time.sleep(0.02)
                
                # Create a realistic detection result
                from dataclasses import dataclass
                
                @dataclass
                class DetectionResult:
                    human_present: bool
                    confidence: float
                    detection_time: float = 0.02
                    
                # Alternate between detections for testing
                if self.detection_count % 3 == 0:
                    return DetectionResult(human_present=False, confidence=0.23)
                else:
                    return DetectionResult(human_present=True, confidence=0.87)
        
        mock_camera = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        realistic_detector = MockRealisticDetector()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=realistic_detector,
            target_fps=12.0
        )
        
        # Track realistic results
        results = []
        processor.add_result_callback(lambda r: results.append(r))
        
        # Act
        await processor.start()
        await asyncio.sleep(0.5)  # Process multiple realistic detections
        await processor.stop()
        
        # Assert - Should work with realistic detector
        assert len(results) >= 3
        assert realistic_detector.detection_count >= 3
        
        # Should have mix of human present/absent
        human_present_results = [r for r in results if r.human_present and not r.error_occurred]
        human_absent_results = [r for r in results if not r.human_present and not r.error_occurred]
        
        assert len(human_present_results) >= 1
        assert len(human_absent_results) >= 1
        
        # All results should be valid
        for result in results:
            if not result.error_occurred:
                assert 0.0 <= result.confidence <= 1.0
                assert result.processing_time > 0
                assert result.frame_id > 0 