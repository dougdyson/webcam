"""
Test suite for LatestFrameProcessor - Phase 1.1 Basic Functionality

This implements Phase 1.1 of the Latest Frame Processing TDD plan:
- Basic LatestFrameProcessor initialization tests
- Frame retrieval from camera manager tests
- Error handling and validation tests
- Factory function tests
- LatestFrameResult data structure tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import time
from unittest.mock import Mock, patch
import numpy as np

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