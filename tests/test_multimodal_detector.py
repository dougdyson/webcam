"""
Tests for multi-modal human detector implementation.

This module tests the MultiModalDetector class that combines MediaPipe's
pose detection and face detection for enhanced range and reliability.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.detection.multimodal_detector import MultiModalDetector
from src.detection.base import DetectorConfig, DetectorError
from src.detection.result import DetectionResult


class TestMultiModalDetector:
    """Test cases for MultiModalDetector."""
    
    @pytest.fixture
    def detector_config(self):
        """Create test detector configuration."""
        return DetectorConfig(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
    
    @pytest.fixture
    def detector(self, detector_config):
        """Create MultiModalDetector instance."""
        return MultiModalDetector(detector_config)
    
    @pytest.fixture
    def test_frame(self):
        """Create test frame."""
        return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def test_multimodal_detector_creation(self, detector_config):
        """Test MultiModalDetector creation with config."""
        detector = MultiModalDetector(detector_config)
        
        assert detector.config == detector_config
        assert detector._pose_weight == 0.6
        assert detector._face_weight == 0.4
        assert not detector.is_initialized
    
    def test_multimodal_detector_creation_default_config(self):
        """Test MultiModalDetector creation with default config."""
        detector = MultiModalDetector()
        
        assert isinstance(detector.config, DetectorConfig)
        assert not detector.is_initialized
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_initialization(self, mock_face, mock_pose, detector):
        """Test MultiModalDetector initialization."""
        # Mock MediaPipe components
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        detector.initialize()
        
        assert detector.is_initialized
        assert detector._pose_detector == mock_pose_instance
        assert detector._face_detector == mock_face_instance
        
        # Verify MediaPipe initialization calls
        mock_pose.Pose.assert_called_once()
        mock_face.FaceDetection.assert_called_once_with(
            model_selection=1,
            min_detection_confidence=detector.config.min_detection_confidence
        )
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_initialization_failure(self, mock_face, mock_pose, detector):
        """Test MultiModalDetector initialization failure."""
        mock_pose.Pose.side_effect = Exception("MediaPipe pose initialization failed")
        
        with pytest.raises(DetectorError) as exc_info:
            detector.initialize()
        
        assert "Failed to initialize multi-modal detector" in str(exc_info.value)
        assert not detector.is_initialized
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_cleanup(self, mock_face, mock_pose, detector):
        """Test MultiModalDetector cleanup."""
        # Initialize first
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        detector.initialize()
        assert detector.is_initialized
        
        # Cleanup
        detector.cleanup()
        
        assert not detector.is_initialized
        assert detector._pose_detector is None
        assert detector._face_detector is None
        mock_pose_instance.close.assert_called_once()
        mock_face_instance.close.assert_called_once()
    
    def test_multimodal_detector_cleanup_not_initialized(self, detector):
        """Test MultiModalDetector cleanup when not initialized."""
        # Should not raise exception
        detector.cleanup()
        assert not detector.is_initialized
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_cleanup_with_error(self, mock_face, mock_pose, detector):
        """Test MultiModalDetector cleanup with error."""
        # Initialize first
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        detector.initialize()
        
        # Make cleanup fail
        mock_pose_instance.close.side_effect = Exception("Cleanup failed")
        
        # Should not raise exception but log error
        detector.cleanup()
        assert not detector.is_initialized
    
    def test_multimodal_detector_detect_not_initialized(self, detector, test_frame):
        """Test detection without initialization."""
        with pytest.raises(DetectorError) as exc_info:
            detector.detect(test_frame)
        
        assert "Detector not initialized" in str(exc_info.value)
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    @patch('cv2.cvtColor')
    def test_multimodal_detector_detect_pose_only(self, mock_cvt, mock_face, mock_pose, detector, test_frame):
        """Test detection with pose only (no face detected)."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Mock RGB conversion
        rgb_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cvt.return_value = rgb_frame
        
        # Mock pose detection results (human detected)
        mock_landmark = Mock()
        mock_landmark.x = 0.5
        mock_landmark.y = 0.5
        mock_landmark.visibility = 0.8
        
        mock_pose_landmarks = Mock()
        mock_pose_landmarks.landmark = [mock_landmark] * 33  # 33 pose landmarks
        
        mock_pose_results = Mock()
        mock_pose_results.pose_landmarks = mock_pose_landmarks
        mock_pose_instance.process.return_value = mock_pose_results
        
        # Mock face detection results (no face detected)
        mock_face_results = Mock()
        mock_face_results.detections = None
        mock_face_instance.process.return_value = mock_face_results
        
        # Initialize and detect
        detector.initialize()
        result = detector.detect(test_frame)
        
        # Verify result
        assert isinstance(result, DetectionResult)
        assert result.human_present is True
        assert result.confidence > 0.0
        assert result.landmarks is not None
        assert len(result.landmarks) > 0
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    @patch('cv2.cvtColor')
    def test_multimodal_detector_detect_face_only(self, mock_cvt, mock_face, mock_pose, detector, test_frame):
        """Test detection with face only (no pose detected)."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Mock RGB conversion
        rgb_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cvt.return_value = rgb_frame
        
        # Mock pose detection results (no pose detected)
        mock_pose_results = Mock()
        mock_pose_results.pose_landmarks = None
        mock_pose_instance.process.return_value = mock_pose_results
        
        # Mock face detection results (face detected)
        mock_bbox = Mock()
        mock_bbox.xmin = 0.3
        mock_bbox.ymin = 0.2
        mock_bbox.width = 0.4
        mock_bbox.height = 0.5
        
        mock_location_data = Mock()
        mock_location_data.relative_bounding_box = mock_bbox
        
        mock_face_detection = Mock()
        mock_face_detection.score = [0.8]
        mock_face_detection.location_data = mock_location_data
        
        mock_face_results = Mock()
        mock_face_results.detections = [mock_face_detection]
        mock_face_instance.process.return_value = mock_face_results
        
        # Initialize and detect
        detector.initialize()
        result = detector.detect(test_frame)
        
        # Verify result
        assert isinstance(result, DetectionResult)
        assert result.human_present is True
        assert result.confidence == 0.8  # Face confidence
        assert result.bounding_box is not None
        assert result.landmarks is None or len(result.landmarks) == 0
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    @patch('cv2.cvtColor')
    def test_multimodal_detector_detect_both_pose_and_face(self, mock_cvt, mock_face, mock_pose, detector, test_frame):
        """Test detection with both pose and face detected."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Mock RGB conversion
        rgb_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cvt.return_value = rgb_frame
        
        # Mock pose detection results
        mock_landmark = Mock()
        mock_landmark.x = 0.5
        mock_landmark.y = 0.5
        mock_landmark.visibility = 0.9
        
        mock_pose_landmarks = Mock()
        mock_pose_landmarks.landmark = [mock_landmark] * 33
        
        mock_pose_results = Mock()
        mock_pose_results.pose_landmarks = mock_pose_landmarks
        mock_pose_instance.process.return_value = mock_pose_results
        
        # Mock face detection results
        mock_bbox = Mock()
        mock_bbox.xmin = 0.3
        mock_bbox.ymin = 0.2
        mock_bbox.width = 0.4
        mock_bbox.height = 0.5
        
        mock_location_data = Mock()
        mock_location_data.relative_bounding_box = mock_bbox
        
        mock_face_detection = Mock()
        mock_face_detection.score = [0.7]
        mock_face_detection.location_data = mock_location_data
        
        mock_face_results = Mock()
        mock_face_results.detections = [mock_face_detection]
        mock_face_instance.process.return_value = mock_face_results
        
        # Initialize and detect
        detector.initialize()
        result = detector.detect(test_frame)
        
        # Verify result
        assert isinstance(result, DetectionResult)
        assert result.human_present is True
        # Should be weighted average: 0.6 * pose_conf + 0.4 * 0.7
        assert result.confidence > 0.0
        assert result.bounding_box is not None
        assert result.landmarks is not None
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    @patch('cv2.cvtColor')
    def test_multimodal_detector_detect_no_detection(self, mock_cvt, mock_face, mock_pose, detector, test_frame):
        """Test detection with no pose or face detected."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Mock RGB conversion
        rgb_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cvt.return_value = rgb_frame
        
        # Mock no detection results
        mock_pose_results = Mock()
        mock_pose_results.pose_landmarks = None
        mock_pose_instance.process.return_value = mock_pose_results
        
        mock_face_results = Mock()
        mock_face_results.detections = None
        mock_face_instance.process.return_value = mock_face_results
        
        # Initialize and detect
        detector.initialize()
        result = detector.detect(test_frame)
        
        # Verify result
        assert isinstance(result, DetectionResult)
        assert result.human_present is False
        assert result.confidence == 0.0
        assert result.bounding_box is None
        assert result.landmarks is None or len(result.landmarks) == 0
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_detect_invalid_frame_none(self, mock_face, mock_pose, detector):
        """Test detection with None frame."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Initialize detector first
        detector.initialize()
        
        with pytest.raises(DetectorError) as exc_info:
            detector.detect(None)
        
        assert "Invalid frame format: frame is None" in str(exc_info.value)
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_detect_invalid_frame_not_array(self, mock_face, mock_pose, detector):
        """Test detection with non-array frame."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Initialize detector first
        detector.initialize()
        
        with pytest.raises(DetectorError) as exc_info:
            detector.detect("not an array")
        
        assert "Invalid frame format: frame must be numpy array" in str(exc_info.value)
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_detect_invalid_frame_wrong_dimensions(self, mock_face, mock_pose, detector):
        """Test detection with wrong frame dimensions."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Initialize detector first
        detector.initialize()
        
        invalid_frame = np.zeros((480, 640), dtype=np.uint8)  # 2D instead of 3D
        
        with pytest.raises(DetectorError) as exc_info:
            detector.detect(invalid_frame)
        
        assert "Invalid frame format: frame must be 3-dimensional" in str(exc_info.value)
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_detect_invalid_frame_wrong_channels(self, mock_face, mock_pose, detector):
        """Test detection with wrong number of channels."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Initialize detector first
        detector.initialize()
        
        invalid_frame = np.zeros((480, 640, 4), dtype=np.uint8)  # 4 channels instead of 3
        
        with pytest.raises(DetectorError) as exc_info:
            detector.detect(invalid_frame)
        
        assert "Invalid frame format: frame must have 3 channels" in str(exc_info.value)
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_detect_empty_frame(self, mock_face, mock_pose, detector):
        """Test detection with empty frame."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        # Initialize detector first
        detector.initialize()
        
        empty_frame = np.zeros((0, 0, 3), dtype=np.uint8)
        
        with pytest.raises(DetectorError) as exc_info:
            detector.detect(empty_frame)
        
        assert "Invalid frame format: frame is empty" in str(exc_info.value)
    
    @patch('mediapipe.solutions.pose')
    @patch('mediapipe.solutions.face_detection')
    def test_multimodal_detector_context_manager(self, mock_face, mock_pose, detector_config):
        """Test MultiModalDetector as context manager."""
        # Setup mocks
        mock_pose_instance = Mock()
        mock_face_instance = Mock()
        mock_pose.Pose.return_value = mock_pose_instance
        mock_face.FaceDetection.return_value = mock_face_instance
        
        with MultiModalDetector(detector_config) as detector:
            assert detector.is_initialized
            assert detector._pose_detector == mock_pose_instance
            assert detector._face_detector == mock_face_instance
        
        # Should be cleaned up after context
        assert not detector.is_initialized
        mock_pose_instance.close.assert_called_once()
        mock_face_instance.close.assert_called_once()
    
    def test_multimodal_detector_idempotent_initialization(self, detector):
        """Test that multiple initialization calls are safe."""
        with patch('mediapipe.solutions.pose') as mock_pose, \
             patch('mediapipe.solutions.face_detection') as mock_face:
            
            mock_pose_instance = Mock()
            mock_face_instance = Mock()
            mock_pose.Pose.return_value = mock_pose_instance
            mock_face.FaceDetection.return_value = mock_face_instance
            
            # First initialization
            detector.initialize()
            assert detector.is_initialized
            
            # Second initialization should not create new instances
            detector.initialize()
            assert detector.is_initialized
            
            # MediaPipe should only be called once
            mock_pose.Pose.assert_called_once()
            mock_face.FaceDetection.assert_called_once() 