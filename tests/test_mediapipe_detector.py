"""
Tests for MediaPipe human detector implementation.

This module tests the MediaPipeDetector class which implements the
HumanDetector interface using MediaPipe's pose detection solutions.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
from typing import Optional, List, Tuple

# We'll import this once we implement it
from src.detection.mediapipe_detector import MediaPipeDetector
from src.detection.base import HumanDetector, DetectorConfig, DetectorError
from src.detection.result import DetectionResult


class TestMediaPipeDetectorInterface:
    """Test MediaPipeDetector implements HumanDetector interface."""

    def test_mediapipe_detector_inherits_from_human_detector(self):
        """Should inherit from HumanDetector abstract base class."""
        # This will fail initially since MediaPipeDetector doesn't exist yet
        assert issubclass(MediaPipeDetector, HumanDetector)

    def test_mediapipe_detector_implements_required_methods(self):
        """Should implement all required abstract methods."""
        required_methods = ['detect', 'initialize', 'cleanup']
        required_properties = ['is_initialized']
        
        for method in required_methods:
            assert hasattr(MediaPipeDetector, method)
            assert callable(getattr(MediaPipeDetector, method))
        
        for prop in required_properties:
            assert hasattr(MediaPipeDetector, prop)
            # Property should be a property descriptor, not callable
            assert isinstance(getattr(MediaPipeDetector, prop), property)

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_initialization_success(self, mock_pose):
        """Should initialize with default MediaPipe configuration."""
        config = DetectorConfig(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        detector = MediaPipeDetector(config)
        assert detector.config == config
        assert not detector.is_initialized  # Should start uninitialized

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_initialization_with_defaults(self, mock_pose):
        """Should initialize with default config when none provided."""
        detector = MediaPipeDetector()
        assert detector.config is not None
        assert isinstance(detector.config, DetectorConfig)
        assert not detector.is_initialized


class TestMediaPipeDetectorInitialization:
    """Test MediaPipe detector initialization and cleanup."""

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_initialize_success(self, mock_pose):
        """Should successfully initialize MediaPipe pose model."""
        mock_pose_instance = Mock()
        mock_pose.return_value = mock_pose_instance
        
        config = DetectorConfig(model_complexity=2)
        detector = MediaPipeDetector(config)
        
        detector.initialize()
        
        # Should create MediaPipe pose instance with correct config
        mock_pose.assert_called_once_with(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        assert detector.is_initialized is True

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_initialize_failure(self, mock_pose):
        """Should handle MediaPipe initialization failure."""
        mock_pose.side_effect = RuntimeError("MediaPipe initialization failed")
        
        detector = MediaPipeDetector()
        
        with pytest.raises(DetectorError, match="Failed to initialize MediaPipe"):
            detector.initialize()
        
        assert detector.is_initialized is False

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_double_initialization(self, mock_pose):
        """Should handle double initialization gracefully."""
        detector = MediaPipeDetector()
        detector.initialize()
        
        # Second initialization should be idempotent
        detector.initialize()
        assert detector.is_initialized is True

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_cleanup_success(self, mock_pose):
        """Should successfully cleanup MediaPipe resources."""
        mock_pose_instance = Mock()
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        detector.cleanup()
        
        # Should close MediaPipe instance
        mock_pose_instance.close.assert_called_once()
        assert detector.is_initialized is False

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_cleanup_when_not_initialized(self, mock_pose):
        """Should handle cleanup when not initialized."""
        detector = MediaPipeDetector()
        
        # Should not raise error
        detector.cleanup()
        assert detector.is_initialized is False

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_cleanup_failure(self, mock_pose):
        """Should handle MediaPipe cleanup failure."""
        mock_pose_instance = Mock()
        mock_pose_instance.close.side_effect = RuntimeError("Cleanup failed")
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        # Should log error but not raise exception
        detector.cleanup()
        assert detector.is_initialized is False


class TestMediaPipeDetectorDetection:
    """Test MediaPipe detection functionality."""

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_detects_human_present(self, mock_pose):
        """Should detect human when pose landmarks are found."""
        # Setup mock MediaPipe response with landmarks
        mock_results = Mock()
        mock_results.pose_landmarks = Mock()
        mock_results.pose_landmarks.landmark = [
            Mock(x=0.5, y=0.3, z=0.1, visibility=0.9),  # Nose
            Mock(x=0.4, y=0.4, z=0.1, visibility=0.8),  # Left shoulder
            Mock(x=0.6, y=0.4, z=0.1, visibility=0.8),  # Right shoulder
        ]
        
        mock_pose_instance = Mock()
        mock_pose_instance.process.return_value = mock_results
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        # Create test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        result = detector.detect(frame)
        
        assert isinstance(result, DetectionResult)
        assert result.human_present is True
        assert result.confidence > 0.0
        assert result.landmarks is not None
        assert len(result.landmarks) > 0

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_no_human_detected(self, mock_pose):
        """Should return no detection when no landmarks found."""
        # Setup mock MediaPipe response without landmarks
        mock_results = Mock()
        mock_results.pose_landmarks = None
        
        mock_pose_instance = Mock()
        mock_pose_instance.process.return_value = mock_results
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        result = detector.detect(frame)
        
        assert isinstance(result, DetectionResult)
        assert result.human_present is False
        assert result.confidence == 0.0
        assert result.landmarks is None or len(result.landmarks) == 0
        assert result.bounding_box is None

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_detection_without_initialization(self, mock_pose):
        """Should raise error when detecting without initialization."""
        detector = MediaPipeDetector()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        with pytest.raises(DetectorError, match="Detector not initialized"):
            detector.detect(frame)

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_handles_invalid_frame(self, mock_pose):
        """Should handle invalid frame input gracefully."""
        detector = MediaPipeDetector()
        detector.initialize()
        
        # Test with invalid frame types
        invalid_frames = [
            None,
            np.array([]),  # Empty array
            np.random.randint(0, 255, (100,), dtype=np.uint8),  # 1D array
            np.random.randint(0, 255, (100, 100), dtype=np.uint8),  # 2D array
            "not_an_array",  # String
        ]
        
        for invalid_frame in invalid_frames:
            with pytest.raises(DetectorError, match="Invalid frame format"):
                detector.detect(invalid_frame)

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_handles_processing_error(self, mock_pose):
        """Should handle MediaPipe processing errors."""
        mock_pose_instance = Mock()
        mock_pose_instance.process.side_effect = RuntimeError("Processing failed")
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        with pytest.raises(DetectorError, match="Detection processing failed"):
            detector.detect(frame)


class TestMediaPipeDetectorLandmarkProcessing:
    """Test landmark extraction and processing."""

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_extracts_landmarks(self, mock_pose):
        """Should correctly extract and normalize landmarks."""
        # Setup mock landmarks
        mock_landmarks = [
            Mock(x=0.5, y=0.3, z=0.1, visibility=0.9),  # High visibility
            Mock(x=0.4, y=0.4, z=0.1, visibility=0.8),  # High visibility
            Mock(x=0.6, y=0.4, z=0.1, visibility=0.3),  # Low visibility
        ]
        
        mock_results = Mock()
        mock_results.pose_landmarks = Mock()
        mock_results.pose_landmarks.landmark = mock_landmarks
        
        mock_pose_instance = Mock()
        mock_pose_instance.process.return_value = mock_results
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = detector.detect(frame)
        
        # Should extract landmarks with sufficient visibility
        assert result.landmarks is not None
        for x, y in result.landmarks:
            assert 0.0 <= x <= 1.0
            assert 0.0 <= y <= 1.0

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_calculates_bounding_box(self, mock_pose):
        """Should calculate bounding box from landmarks."""
        # Setup mock landmarks spread across frame
        mock_landmarks = [
            Mock(x=0.2, y=0.1, z=0.1, visibility=0.9),  # Top-left area
            Mock(x=0.8, y=0.9, z=0.1, visibility=0.9),  # Bottom-right area
            Mock(x=0.5, y=0.5, z=0.1, visibility=0.9),  # Center
        ]
        
        mock_results = Mock()
        mock_results.pose_landmarks = Mock()
        mock_results.pose_landmarks.landmark = mock_landmarks
        
        mock_pose_instance = Mock()
        mock_pose_instance.process.return_value = mock_results
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = detector.detect(frame)
        
        # Should calculate bounding box
        assert result.bounding_box is not None
        x, y, w, h = result.bounding_box
        assert x >= 0 and y >= 0
        assert w > 0 and h > 0
        assert x + w <= 640  # Frame width
        assert y + h <= 480  # Frame height

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_calculates_confidence(self, mock_pose):
        """Should calculate confidence based on landmark visibility."""
        # Test high confidence scenario
        high_visibility_landmarks = [
            Mock(x=0.5, y=0.3, z=0.1, visibility=0.95),
            Mock(x=0.4, y=0.4, z=0.1, visibility=0.9),
            Mock(x=0.6, y=0.4, z=0.1, visibility=0.85),
        ]
        
        mock_results = Mock()
        mock_results.pose_landmarks = Mock()
        mock_results.pose_landmarks.landmark = high_visibility_landmarks
        
        mock_pose_instance = Mock()
        mock_pose_instance.process.return_value = mock_results
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = detector.detect(frame)
        
        # Should have high confidence
        assert result.confidence > 0.8


class TestMediaPipeDetectorContextManager:
    """Test MediaPipe detector context manager functionality."""

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_context_manager_success(self, mock_pose):
        """Should work properly as context manager."""
        mock_pose_instance = Mock()
        mock_pose.return_value = mock_pose_instance
        
        config = DetectorConfig()
        
        with MediaPipeDetector(config) as detector:
            assert detector.is_initialized is True
            
            # Should be able to detect
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            result = detector.detect(frame)
            assert isinstance(result, DetectionResult)
        
        # Should be cleaned up after context
        mock_pose_instance.close.assert_called_once()

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_context_manager_with_exception(self, mock_pose):
        """Should cleanup properly even when exception occurs."""
        mock_pose_instance = Mock()
        mock_pose.return_value = mock_pose_instance
        
        try:
            with MediaPipeDetector() as detector:
                assert detector.is_initialized is True
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # Should still cleanup
        mock_pose_instance.close.assert_called_once()


class TestMediaPipeDetectorIntegration:
    """Integration tests for MediaPipe detector."""

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_multiple_detections(self, mock_pose):
        """Should handle multiple consecutive detections."""
        # Simulate different detection scenarios
        detection_scenarios = [
            # Frame 1: Human present
            Mock(pose_landmarks=Mock(landmark=[
                Mock(x=0.5, y=0.3, visibility=0.9),
                Mock(x=0.4, y=0.4, visibility=0.8),
            ])),
            # Frame 2: No human
            Mock(pose_landmarks=None),
            # Frame 3: Human present again
            Mock(pose_landmarks=Mock(landmark=[
                Mock(x=0.6, y=0.2, visibility=0.95),
                Mock(x=0.3, y=0.5, visibility=0.9),
            ])),
        ]
        
        mock_pose_instance = Mock()
        mock_pose_instance.process.side_effect = detection_scenarios
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        results = []
        for i in range(3):
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            result = detector.detect(frame)
            results.append(result.human_present)
        
        # Should match expected pattern: True, False, True
        assert results == [True, False, True]

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_performance_monitoring(self, mock_pose):
        """Should handle high-frequency detection calls."""
        mock_results = Mock()
        mock_results.pose_landmarks = Mock()
        mock_results.pose_landmarks.landmark = [
            Mock(x=0.5, y=0.3, visibility=0.9)
        ]
        
        mock_pose_instance = Mock()
        mock_pose_instance.process.return_value = mock_results
        mock_pose.return_value = mock_pose_instance
        
        detector = MediaPipeDetector()
        detector.initialize()
        
        # Perform many detections
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        for i in range(100):
            result = detector.detect(frame)
            assert isinstance(result, DetectionResult)
            assert result.human_present is True
        
        # Should have called process many times
        assert mock_pose_instance.process.call_count == 100

    @patch('mediapipe.solutions.pose.Pose')
    def test_mediapipe_detector_with_factory_registration(self, mock_pose):
        """Should work with detector factory registration."""
        from src.detection.base import DetectorFactory
        
        # Register MediaPipe detector
        DetectorFactory.register("mediapipe", MediaPipeDetector)
        
        # Create through factory
        detector = DetectorFactory.create("mediapipe")
        assert isinstance(detector, MediaPipeDetector)
        assert isinstance(detector, HumanDetector)
        
        # Should work normally
        detector.initialize()
        assert detector.is_initialized is True
        
        detector.cleanup()
        assert detector.is_initialized is False
        
        # Clean up factory for other tests
        DetectorFactory.clear_registry() 