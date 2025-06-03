"""
Test suite for LatestFrameProcessor - Phase 1.2 Async Processing Loop

This implements Phase 1.2 of the Latest Frame Processing TDD plan:
- Async processing loop lifecycle tests
- Continuous frame processing tests
- FPS timing and performance tests
- Error recovery tests
- Callback management tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock
import numpy as np

from src.processing.latest_frame_processor import (
    LatestFrameProcessor,
    LatestFrameResult
)


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
        
        # Create proper async slow detector function
        async def slow_async_detect(frame):
            await asyncio.sleep(0.15)  # Simulate slow processing
            result = Mock()
            result.human_present = True
            result.confidence = 0.70
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0  # 10 FPS = 0.1s intervals (faster than detector)
        )
        
        # Replace the async detect method directly (working pattern)
        processor._async_detect = slow_async_detect
        
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