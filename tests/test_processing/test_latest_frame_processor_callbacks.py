"""
Test suite for LatestFrameProcessor - Phase 2.3 Callback System

This implements Phase 2.3 of the Latest Frame Processing TDD plan:
- Result callback registration tests
- Callback management system tests
- Async callback support and error handling tests
- Callback error isolation tests
- Callback performance monitoring tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, AsyncMock
import numpy as np

from src.processing.latest_frame_processor import (
    LatestFrameProcessor,
    LatestFrameResult
)


class TestLatestFrameProcessorCallbackRegistration:
    """Phase 2.3: Result callback registration and management tests."""
    
    @pytest.mark.asyncio
    async def test_callback_registration_basic_functionality(self):
        """
        🔴 RED: Test basic callback registration and invocation.
        
        Callbacks should be properly registered and called with processing results.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.88
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track callback invocations
        callback_results = []
        
        def test_callback(result):
            callback_results.append(result)
        
        # Act - Register callback and process frames
        processor.add_result_callback(test_callback)
        
        await processor.start()
        await asyncio.sleep(0.3)  # Process a few frames
        await processor.stop()
        
        # Assert - Callback should have been called
        assert len(callback_results) >= 1
        assert all(isinstance(r, LatestFrameResult) for r in callback_results)
        assert all(r.human_present == True for r in callback_results)
        assert all(r.confidence == 0.88 for r in callback_results)
        
    @pytest.mark.asyncio
    async def test_multiple_callback_registration(self):
        """
        🔴 RED: Test registration and invocation of multiple callbacks.
        
        All registered callbacks should receive processing results.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = False
        mock_detection_result.confidence = 0.23
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=6.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track multiple callback invocations
        callback1_results = []
        callback2_results = []
        callback3_results = []
        
        def callback1(result):
            callback1_results.append(('callback1', result))
        
        def callback2(result):
            callback2_results.append(('callback2', result))
        
        def callback3(result):
            callback3_results.append(('callback3', result))
        
        # Act - Register multiple callbacks
        processor.add_result_callback(callback1)
        processor.add_result_callback(callback2)
        processor.add_result_callback(callback3)
        
        await processor.start()
        await asyncio.sleep(0.4)  # Process multiple frames
        await processor.stop()
        
        # Assert - All callbacks should have been called
        assert len(callback1_results) >= 1
        assert len(callback2_results) >= 1
        assert len(callback3_results) >= 1
        
        # All callbacks should have received the same number of results
        assert len(callback1_results) == len(callback2_results)
        assert len(callback2_results) == len(callback3_results)
        
        # Verify results are consistent across callbacks
        for i in range(len(callback1_results)):
            assert callback1_results[i][1].frame_id == callback2_results[i][1].frame_id
            assert callback2_results[i][1].frame_id == callback3_results[i][1].frame_id
    
    @pytest.mark.asyncio
    async def test_callback_removal_functionality(self):
        """
        🔴 RED: Test callback removal and selective invocation.
        
        Removed callbacks should no longer receive processing results.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.76
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track callback invocations
        persistent_callback_results = []
        removable_callback_results = []
        
        def persistent_callback(result):
            persistent_callback_results.append(result)
        
        def removable_callback(result):
            removable_callback_results.append(result)
        
        # Act - Register both callbacks
        processor.add_result_callback(persistent_callback)
        processor.add_result_callback(removable_callback)
        
        await processor.start()
        await asyncio.sleep(0.2)  # Process initial frames
        
        # Remove one callback
        processor.remove_result_callback(removable_callback)
        
        await asyncio.sleep(0.2)  # Process more frames
        await processor.stop()
        
        # Assert - Persistent callback should have more results
        assert len(persistent_callback_results) >= 2
        assert len(removable_callback_results) >= 1
        assert len(persistent_callback_results) > len(removable_callback_results)
        
    def test_callback_removal_nonexistent_callback(self):
        """
        🔴 RED: Test removal of non-existent callback graceful handling.
        
        Removing a callback that wasn't registered should not cause errors.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        def dummy_callback(result):
            pass
        
        # Act - Try to remove callback that was never added
        # This should not raise an exception
        processor.remove_result_callback(dummy_callback)
        
        # Assert - Should handle gracefully (no exception)
        assert True  # If we get here, no exception was raised


class TestLatestFrameProcessorAsyncCallbackSupport:
    """Phase 2.3: Async callback support and advanced callback features."""
    
    @pytest.mark.asyncio
    async def test_async_callback_support(self):
        """
        🔴 RED: Test support for async callbacks alongside sync callbacks.
        
        Both sync and async callbacks should be supported and properly invoked.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.94
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=7.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track sync and async callback invocations
        sync_callback_results = []
        async_callback_results = []
        
        def sync_callback(result):
            sync_callback_results.append(('sync', result))
        
        async def async_callback(result):
            async_callback_results.append(('async', result))
        
        # Act - Register both sync and async callbacks
        processor.add_result_callback(sync_callback)
        processor.add_result_callback(async_callback)
        
        await processor.start()
        await asyncio.sleep(0.4)  # Process multiple frames
        await processor.stop()
        
        # Assert - Both callback types should have been called
        assert len(sync_callback_results) >= 1
        assert len(async_callback_results) >= 1
        
        # Should have received same number of results
        assert len(sync_callback_results) == len(async_callback_results)
        
        # Verify result consistency
        for i in range(len(sync_callback_results)):
            sync_result = sync_callback_results[i][1]
            async_result = async_callback_results[i][1]
            assert sync_result.frame_id == async_result.frame_id
            assert sync_result.confidence == async_result.confidence
    
    @pytest.mark.asyncio
    async def test_callback_with_processing_delay(self):
        """
        🔴 RED: Test callbacks with processing delays don't block main loop.
        
        Slow callbacks should not impact main processing performance.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock fast detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.82
        
        async def mock_async_detect(frame):
            await asyncio.sleep(0.01)  # Fast detector
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0  # 125ms intervals
        )
        
        processor._async_detect = mock_async_detect
        
        # Track timing
        fast_callback_results = []
        slow_callback_results = []
        
        def fast_callback(result):
            fast_callback_results.append(result)
        
        async def slow_callback(result):
            await asyncio.sleep(0.1)  # Slow callback (100ms)
            slow_callback_results.append(result)
        
        # Act - Register fast and slow callbacks
        processor.add_result_callback(fast_callback)
        processor.add_result_callback(slow_callback)
        
        start_time = time.time()
        await processor.start()
        await asyncio.sleep(0.5)  # Process for 500ms
        await processor.stop()
        elapsed = time.time() - start_time
        
        # Assert - Should complete reasonably quickly despite slow callback
        assert elapsed < 0.8  # Should not be significantly delayed by slow callback
        assert len(fast_callback_results) >= 2  # Should have processed multiple frames
        assert len(slow_callback_results) >= 1  # Slow callback should still be called
    
    @pytest.mark.asyncio
    async def test_callback_order_preservation(self):
        """
        🔴 RED: Test that callbacks are invoked in registration order.
        
        Callbacks should be called in the order they were registered.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.67
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=6.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track callback execution order
        callback_execution_order = []
        execution_lock = threading.Lock()
        
        def callback_a(result):
            with execution_lock:
                callback_execution_order.append(('A', result.frame_id))
        
        def callback_b(result):
            with execution_lock:
                callback_execution_order.append(('B', result.frame_id))
        
        def callback_c(result):
            with execution_lock:
                callback_execution_order.append(('C', result.frame_id))
        
        # Act - Register callbacks in specific order
        processor.add_result_callback(callback_a)
        processor.add_result_callback(callback_b)
        processor.add_result_callback(callback_c)
        
        await processor.start()
        await asyncio.sleep(0.3)  # Process frames
        await processor.stop()
        
        # Assert - Callbacks should be executed in registration order
        assert len(callback_execution_order) >= 3  # At least one full set
        
        # Group by frame_id and check order within each frame
        frames = {}
        for callback_name, frame_id in callback_execution_order:
            if frame_id not in frames:
                frames[frame_id] = []
            frames[frame_id].append(callback_name)
        
        # Each frame should have callbacks executed in order A, B, C
        for frame_id, callbacks in frames.items():
            if len(callbacks) == 3:  # Complete set
                assert callbacks == ['A', 'B', 'C'], f"Frame {frame_id} callbacks not in order: {callbacks}"


class TestLatestFrameProcessorCallbackErrorHandling:
    """Phase 2.3: Callback error isolation and robust error handling."""
    
    @pytest.mark.asyncio
    async def test_callback_error_isolation(self):
        """
        🔴 RED: Test that callback errors don't crash processing or affect other callbacks.
        
        One failing callback should not prevent other callbacks from running.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.91
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track successful and failing callbacks
        successful_callback_results = []
        after_error_callback_results = []
        
        def successful_callback(result):
            successful_callback_results.append(result)
        
        def failing_callback(result):
            raise RuntimeError("Callback intentionally failed")
        
        def after_error_callback(result):
            after_error_callback_results.append(result)
        
        # Act - Register callbacks with failing one in middle
        processor.add_result_callback(successful_callback)
        processor.add_result_callback(failing_callback)  # This will fail
        processor.add_result_callback(after_error_callback)
        
        await processor.start()
        await asyncio.sleep(0.4)  # Process frames with error
        await processor.stop()
        
        # Assert - Processing should continue despite failing callback
        assert len(successful_callback_results) >= 1
        assert len(after_error_callback_results) >= 1
        
        # Both successful callbacks should have same results
        assert len(successful_callback_results) == len(after_error_callback_results)
        
        # Processor should still be functional
        assert processor.is_running == False  # Stopped properly
        
    @pytest.mark.asyncio
    async def test_async_callback_error_isolation(self):
        """
        🔴 RED: Test that async callback errors don't crash processing.
        
        Failing async callbacks should be isolated like sync callbacks.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = False
        mock_detection_result.confidence = 0.15
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=6.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track successful callbacks around failing async callback
        sync_callback_results = []
        async_success_callback_results = []
        
        def sync_callback(result):
            sync_callback_results.append(result)
        
        async def failing_async_callback(result):
            raise ValueError("Async callback failed")
        
        async def successful_async_callback(result):
            async_success_callback_results.append(result)
        
        # Act - Register callbacks with failing async one
        processor.add_result_callback(sync_callback)
        processor.add_result_callback(failing_async_callback)  # Will fail
        processor.add_result_callback(successful_async_callback)
        
        await processor.start()
        await asyncio.sleep(0.5)  # Process frames with async error
        await processor.stop()
        
        # Assert - Processing should continue despite failing async callback
        assert len(sync_callback_results) >= 1
        assert len(async_success_callback_results) >= 1
        
        # Results should be consistent
        assert len(sync_callback_results) == len(async_success_callback_results)
    
    @pytest.mark.asyncio
    async def test_callback_error_logging_and_monitoring(self):
        """
        🔴 RED: Test that callback errors are properly logged and monitored.
        
        Callback errors should be tracked for monitoring and debugging.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.78
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track successful callback
        successful_results = []
        
        def successful_callback(result):
            successful_results.append(result)
        
        def error_callback_1(result):
            raise TypeError("Type error in callback")
        
        def error_callback_2(result):
            raise ValueError("Value error in callback")
        
        # Act - Register callbacks with different error types
        processor.add_result_callback(successful_callback)
        processor.add_result_callback(error_callback_1)
        processor.add_result_callback(error_callback_2)
        
        await processor.start()
        await asyncio.sleep(0.4)  # Process frames with errors
        await processor.stop()
        
        # Assert - Should have callback error monitoring
        callback_stats = processor.get_callback_error_statistics()
        
        assert 'total_callback_errors' in callback_stats
        assert 'error_types' in callback_stats
        assert 'callbacks_with_errors' in callback_stats
        assert 'successful_callback_invocations' in callback_stats
        
        # Should have tracked multiple errors
        assert callback_stats['total_callback_errors'] >= 2
        assert len(callback_stats['error_types']) >= 2
        assert 'TypeError' in callback_stats['error_types']
        assert 'ValueError' in callback_stats['error_types']
        
        # Should still have successful invocations
        assert callback_stats['successful_callback_invocations'] >= 1
        assert len(successful_results) >= 1 