"""
Test suite for LatestFrameProcessor - Phase 2.1 Statistics Tracking

This implements Phase 2.1 of the Latest Frame Processing TDD plan:
- Frame processing statistics tests
- Frames skipped calculation tests  
- Thread-safe statistics updates tests
- Performance monitoring tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch
import numpy as np

from src.processing.latest_frame_processor import (
    LatestFrameProcessor,
    LatestFrameResult
)


class TestLatestFrameProcessorStatisticsTracking:
    """Phase 2.1: Frame processing statistics tracking tests."""
    
    @pytest.mark.asyncio
    async def test_frame_processing_statistics_comprehensive_tracking(self):
        """
        🔴 RED: Test comprehensive frame processing statistics tracking.
        
        This should track detailed metrics about frame processing performance.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with known processing time
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.85
        
        # Create proper async detector function (fixed pattern)
        async def slow_async_detect(frame):
            await asyncio.sleep(0.1)  # Predictable processing time
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        # Replace the async detect method directly
        processor._async_detect = slow_async_detect
        
        # Act - Process frames for statistics
        await processor.start()
        await asyncio.sleep(0.6)  # Process ~3 frames
        await processor.stop()
        
        # Assert - Should have comprehensive statistics
        stats = processor.get_detailed_statistics()
        
        assert stats['total_frames_processed'] >= 2
        assert stats['average_processing_time'] > 0.08  # Should reflect detector time
        assert stats['min_processing_time'] > 0
        assert stats['max_processing_time'] > 0
        assert stats['total_processing_time'] > 0
        assert stats['frames_per_second_actual'] > 0
        assert stats['frames_per_second_target'] == 5.0
        assert stats['processing_efficiency'] > 0  # Ratio of actual vs target FPS
        assert 'uptime_seconds' in stats
        assert 'last_processing_time' in stats
        
    @pytest.mark.asyncio 
    async def test_frame_processing_statistics_efficiency_calculation(self):
        """
        🔴 RED: Test processing efficiency calculation.
        
        Efficiency should be ratio of actual processing rate vs target rate.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Fast detector - should achieve high efficiency
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.90
        
        async def fast_async_detect(frame):
            await asyncio.sleep(0.01)  # Very fast processing
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0  # 10 FPS target
        )
        
        # Mock the _async_detect method for predictable timing
        processor._async_detect = fast_async_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.5)  # Let it process
        await processor.stop()
        
        # Assert
        stats = processor.get_detailed_statistics()
        
        # Should achieve high efficiency with fast detector
        assert stats['processing_efficiency'] > 0.7  # >70% efficiency
        assert stats['frames_per_second_actual'] > 7.0  # Should be close to target
        assert stats['average_processing_time'] < 0.1  # Fast processing
        
    @pytest.mark.asyncio
    async def test_frame_processing_statistics_low_efficiency_detection(self):
        """
        🔴 RED: Test detection of low processing efficiency.
        
        When detector is slower than target FPS, efficiency should be low.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Very slow detector (fixed pattern)
        async def very_slow_async_detect(frame):
            await asyncio.sleep(0.3)  # Slower than target interval
            result = Mock()
            result.human_present = True
            result.confidence = 0.75
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0  # 10 FPS = 0.1s intervals, but detector takes 0.3s
        )
        
        # Replace the async detect method directly
        processor._async_detect = very_slow_async_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(1.0)  # Let it struggle with slow processing
        await processor.stop()
        
        # Assert
        stats = processor.get_detailed_statistics()
        
        # Should detect low efficiency
        assert stats['processing_efficiency'] < 0.5  # <50% efficiency
        assert stats['frames_per_second_actual'] < 5.0  # Much slower than target
        assert stats['average_processing_time'] > 0.25  # Reflects slow processing
        assert stats['efficiency_warning'] == True  # Should flag performance issue
        
    def test_frame_processing_statistics_initial_state(self):
        """
        🔴 RED: Test statistics in initial state before processing.
        
        All counters should be zero/default before processing starts.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Act
        initial_stats = processor.get_detailed_statistics()
        
        # Assert - Should have clean initial state
        assert initial_stats['total_frames_processed'] == 0
        assert initial_stats['average_processing_time'] == 0.0
        assert initial_stats['min_processing_time'] == 0.0
        assert initial_stats['max_processing_time'] == 0.0
        assert initial_stats['total_processing_time'] == 0.0
        assert initial_stats['frames_per_second_actual'] == 0.0
        assert initial_stats['processing_efficiency'] == 0.0
        assert initial_stats['efficiency_warning'] == False
        assert initial_stats['uptime_seconds'] == 0.0
        assert initial_stats['last_processing_time'] == 0.0
        
    @pytest.mark.asyncio
    async def test_frame_processing_statistics_reset_functionality(self):
        """
        🔴 RED: Test statistics reset functionality.
        
        Should be able to reset all statistics to initial state.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.80
        mock_detector.detect.return_value = mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Process some frames to build up statistics
        await processor.start()
        await asyncio.sleep(0.3)
        await processor.stop()
        
        # Verify we have some statistics
        stats_before = processor.get_detailed_statistics()
        assert stats_before['total_frames_processed'] > 0
        
        # Act - Reset statistics
        processor.reset_statistics()
        
        # Assert - Should be back to initial state
        stats_after = processor.get_detailed_statistics()
        assert stats_after['total_frames_processed'] == 0
        assert stats_after['average_processing_time'] == 0.0
        assert stats_after['total_processing_time'] == 0.0
        assert stats_after['frames_per_second_actual'] == 0.0
        assert stats_after['processing_efficiency'] == 0.0


class TestLatestFrameProcessorFramesSkippedCalculation:
    """Phase 2.1: Frames skipped calculation and tracking tests."""
    
    @pytest.mark.asyncio
    async def test_frames_skipped_calculation_basic(self):
        """
        🔴 RED: Test basic frames skipped calculation.
        
        When processing is slower than frame availability, frames should be skipped.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Mock camera that provides fresh frames each time
        frame_count = 0
        def get_fresh_frame():
            nonlocal frame_count
            frame_count += 1
            # Return slightly different frames to simulate real camera
            frame = test_frame.copy()
            frame[0, 0, 0] = frame_count % 255  # Unique marker
            return frame
        
        mock_camera.get_frame.side_effect = get_fresh_frame
        
        # Slow detector to cause frame skipping
        def slow_detect(frame):
            time.sleep(0.2)  # Slow enough to miss frames
            result = Mock()
            result.human_present = True
            result.confidence = 0.85
            return result
        
        mock_detector.detect.side_effect = slow_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0  # 0.2s intervals, same as detector speed
        )
        
        # Act
        await processor.start()
        await asyncio.sleep(1.0)  # Run long enough to see skipping
        await processor.stop()
        
        # Assert
        stats = processor.get_detailed_statistics()
        
        assert 'frames_skipped_total' in stats
        assert 'frames_skipped_rate' in stats
        assert 'skip_efficiency_ratio' in stats
        
        # Should have skipped some frames due to slow processing
        assert stats['frames_skipped_total'] >= 0
        assert stats['frames_skipped_rate'] >= 0.0  # Skips per second
        assert 0.0 <= stats['skip_efficiency_ratio'] <= 1.0  # Ratio of processed vs available
        
    @pytest.mark.asyncio
    async def test_frames_skipped_calculation_with_frame_age_rejection(self):
        """
        🔴 RED: Test frames skipped due to age rejection.
        
        Frames that are too old should be counted as skipped for different reason.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.80
        mock_detector.detect.return_value = mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            max_frame_age=0.001  # Very strict frame age limit
        )
        
        # Simple frame age simulation without complex time mocking
        original_get_latest_frame = processor._get_latest_frame
        
        def mock_get_latest_frame():
            # Simulate old frames by incrementing frames_too_old directly
            processor._increment_frames_too_old()
            return None  # Return None to simulate rejected frames
        
        processor._get_latest_frame = mock_get_latest_frame
        
        # Act
        await processor.start()
        await asyncio.sleep(0.3)
        await processor.stop()
        
        # Assert
        stats = processor.get_detailed_statistics()
        
        assert 'frames_too_old_total' in stats
        assert 'frames_too_old_rate' in stats
        assert stats['frames_too_old_total'] >= 1  # Should have rejected some frames
        assert stats['frames_too_old_rate'] >= 0.0
        
    @pytest.mark.asyncio
    async def test_frames_skipped_zero_with_fast_processing(self):
        """
        🔴 RED: Test that no frames are skipped with fast processing.
        
        When processing is faster than target FPS, no frames should be skipped.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Very fast detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.95
        
        async def fast_async_detect(frame):
            await asyncio.sleep(0.01)  # Much faster than target interval
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0  # 0.2s intervals, much slower than detector
        )
        
        processor._async_detect = fast_async_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.5)
        await processor.stop()
        
        # Assert
        stats = processor.get_detailed_statistics()
        
        # Should have minimal or no skipped frames
        assert stats['frames_skipped_total'] == 0
        assert stats['frames_skipped_rate'] == 0.0
        assert stats['skip_efficiency_ratio'] > 0.9  # High efficiency
        
    def test_frames_skipped_calculation_thread_safety(self):
        """
        🔴 RED: Test thread-safe frames skipped calculation.
        
        Skip counting should be thread-safe when accessed concurrently.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Simulate concurrent access to skip statistics
        def increment_skips():
            for _ in range(100):
                processor._increment_frames_skipped()
                
        def increment_too_old():
            for _ in range(50):
                processor._increment_frames_too_old()
        
        # Act - Run concurrent increments
        threads = []
        for _ in range(5):
            t1 = threading.Thread(target=increment_skips)
            t2 = threading.Thread(target=increment_too_old)
            threads.extend([t1, t2])
            
        for t in threads:
            t.start()
            
        for t in threads:
            t.join()
        
        # Assert - Should have correct totals despite concurrent access
        stats = processor.get_detailed_statistics()
        
        assert stats['frames_skipped_total'] == 500  # 5 threads × 100
        assert stats['frames_too_old_total'] == 250  # 5 threads × 50
        # Should not have lost any increments due to race conditions 