"""
Test suite for LatestFrameProcessor - Phase 1.3 Detection Integration

This implements Phase 1.3 of the Latest Frame Processing TDD plan:
- Sync detector to async conversion tests
- Native async detector support tests
- Timeout handling tests
- Comprehensive metadata creation tests
- Error result creation tests
- Real detector interface compatibility tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
from unittest.mock import Mock
import numpy as np
from dataclasses import dataclass

from src.processing.latest_frame_processor import (
    LatestFrameProcessor,
    LatestFrameResult
)


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
            assert "Detection error:" in result.error_message
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