"""
Test GestureDetector implementation.

Testing the main gesture detector class that integrates hand detection,
gesture classification, and follows the factory pattern.
Following TDD methodology: Red → Green → Refactor.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

class TestGestureDetector:
    """Test the main GestureDetector class following existing detector patterns."""
    
    def test_gesture_detector_class_creation_with_config(self):
        """
        RED TEST: Test GestureDetector class creation with configuration.
        
        Should follow the same pattern as MultiModalDetector and MediaPipeDetector.
        """
        from src.detection.gesture_detector import GestureDetector
        from src.detection.base import DetectorConfig
        
        # Test with default configuration
        config = DetectorConfig()
        detector = GestureDetector(config)
        
        assert detector is not None, "Should create GestureDetector instance"
        assert detector.config == config, "Should store provided configuration"
        assert not detector.is_initialized, "Should not be initialized by default"
    
    def test_gesture_detector_initialization_and_cleanup(self):
        """
        RED TEST: Test gesture detector initialization and cleanup.
        
        Should properly initialize MediaPipe hands and cleanup resources.
        """
        from src.detection.gesture_detector import GestureDetector
        
        detector = GestureDetector()
        
        # Test initialization
        detector.initialize()
        assert detector.is_initialized, "Should be initialized after initialize()"
        
        # Test cleanup
        detector.cleanup()
        assert not detector.is_initialized, "Should not be initialized after cleanup()"
    
    def test_gesture_detector_context_manager_support(self):
        """
        RED TEST: Test context manager support following existing pattern.
        
        Should support 'with' statement for automatic resource management.
        """
        from src.detection.gesture_detector import GestureDetector
        
        # Test context manager pattern
        with GestureDetector() as detector:
            assert detector.is_initialized, "Should be initialized in context"
        
        # After context, should be cleaned up
        assert not detector.is_initialized, "Should be cleaned up after context"
    
    def test_detect_gestures_method_with_gesture_result_return(self):
        """
        RED TEST: Test detect_gestures() method returns GestureResult.
        
        Should process frame and return GestureResult with gesture information.
        """
        from src.detection.gesture_detector import GestureDetector
        from src.gesture.result import GestureResult
        
        detector = GestureDetector()
        detector.initialize()
        
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test gesture detection
        result = detector.detect_gestures(test_frame)
        
        assert isinstance(result, GestureResult), "Should return GestureResult"
        assert hasattr(result, 'gesture_detected'), "Should have gesture_detected attribute"
        assert hasattr(result, 'confidence'), "Should have confidence attribute"
        
        detector.cleanup()
    
    @patch('mediapipe.solutions.hands')
    def test_mediapipe_hands_integration(self, mock_mp_hands):
        """
        RED TEST: Test integration with MediaPipe hands solution.
        
        Should use MediaPipe hands for hand landmark detection.
        """
        from src.detection.gesture_detector import GestureDetector
        
        # Mock MediaPipe hands
        mock_hands_detector = Mock()
        mock_mp_hands.Hands.return_value = mock_hands_detector
        
        detector = GestureDetector()
        detector.initialize()
        
        # Verify MediaPipe hands was initialized with correct parameters
        mock_mp_hands.Hands.assert_called_once()
        call_args = mock_mp_hands.Hands.call_args[1]
        
        assert 'min_detection_confidence' in call_args, "Should pass detection confidence"
        assert 'min_tracking_confidence' in call_args, "Should pass tracking confidence"
        assert 'max_num_hands' in call_args, "Should pass max number of hands"
        
        detector.cleanup()
    
    def test_gesture_detector_with_hand_landmarks_and_pose_data(self):
        """
        RED TEST: Test gesture detection with hand landmarks and pose data.
        
        Should integrate hand detection with pose landmarks for shoulder reference.
        """
        from src.detection.gesture_detector import GestureDetector
        
        detector = GestureDetector()
        detector.initialize()
        
        # Create test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock pose landmarks (for shoulder reference)
        mock_pose_landmarks = self._create_mock_pose_landmarks()
        
        # Test gesture detection with pose data
        result = detector.detect_gestures(test_frame, pose_landmarks=mock_pose_landmarks)
        
        assert result is not None, "Should return result with pose data"
        assert hasattr(result, 'gesture_detected'), "Should have gesture detection results"
        
        detector.cleanup()
    
    def test_gesture_detector_error_handling_for_invalid_frames(self):
        """
        RED TEST: Test error handling for invalid frame inputs.
        
        Should handle None frames, wrong dimensions, and invalid data types.
        """
        from src.detection.gesture_detector import GestureDetector
        from src.detection.base import DetectorError
        
        detector = GestureDetector()
        detector.initialize()
        
        # Test None frame
        with pytest.raises(DetectorError, match="Invalid frame"):
            detector.detect_gestures(None)
        
        # Test wrong dimensions
        invalid_frame = np.zeros((480, 640), dtype=np.uint8)  # Missing color channel
        with pytest.raises(DetectorError, match="Invalid frame"):
            detector.detect_gestures(invalid_frame)
        
        # Test invalid data type
        with pytest.raises(DetectorError, match="Invalid frame"):
            detector.detect_gestures("not_a_frame")
        
        detector.cleanup()
    
    def test_gesture_detector_error_handling_when_not_initialized(self):
        """
        RED TEST: Test error handling when detector is not initialized.
        
        Should raise DetectorError when trying to detect without initialization.
        """
        from src.detection.gesture_detector import GestureDetector
        from src.detection.base import DetectorError
        
        detector = GestureDetector()
        # Don't initialize
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with pytest.raises(DetectorError, match="not initialized"):
            detector.detect_gestures(test_frame)
    
    def test_gesture_detector_resource_management_and_mediapipe_cleanup(self):
        """
        RED TEST: Test proper MediaPipe resource management and cleanup.
        
        Should properly close MediaPipe resources to prevent memory leaks.
        """
        from src.detection.gesture_detector import GestureDetector
        
        detector = GestureDetector()
        
        # Initialize and verify resources are created
        detector.initialize()
        assert detector.is_initialized, "Should be initialized"
        
        # Cleanup and verify resources are properly released
        detector.cleanup()
        assert not detector.is_initialized, "Should be cleaned up"
        
        # Should be safe to cleanup multiple times
        detector.cleanup()  # Should not raise error
        assert not detector.is_initialized, "Should still be cleaned up"
    
    def test_gesture_detector_configuration_validation(self):
        """
        RED TEST: Test gesture detector configuration handling.
        
        Should properly handle and validate gesture-specific configuration.
        """
        from src.detection.gesture_detector import GestureDetector
        from src.detection.base import DetectorConfig
        
        # Test with custom configuration
        config = DetectorConfig(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6,
            model_complexity=1
        )
        
        detector = GestureDetector(config)
        assert detector.config.min_detection_confidence == 0.7, "Should use custom confidence"
        assert detector.config.min_tracking_confidence == 0.6, "Should use custom tracking"
        assert detector.config.model_complexity == 1, "Should use custom complexity"
    
    def test_gesture_detector_integration_with_classification_algorithm(self):
        """
        RED TEST: Test integration with gesture classification algorithm.
        
        Should use GestureClassifier for analyzing hand gestures.
        """
        from src.detection.gesture_detector import GestureDetector
        
        detector = GestureDetector()
        detector.initialize()
        
        # Create test frame with mock gesture scenario
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_pose_landmarks = self._create_mock_pose_landmarks()
        
        # Test that classification is performed
        result = detector.detect_gestures(test_frame, pose_landmarks=mock_pose_landmarks)
        
        # Should have gesture analysis results
        assert hasattr(result, 'gesture_type'), "Should have gesture type"
        assert hasattr(result, 'palm_facing_camera'), "Should have palm orientation"
        
        detector.cleanup()
    
    def test_gesture_detector_performance_optimization_conditionals(self):
        """
        RED TEST: Test performance optimization features.
        
        Should include optimizations like conditional processing and resource sharing.
        """
        from src.detection.gesture_detector import GestureDetector
        
        detector = GestureDetector()
        detector.initialize()
        
        # Test that detector can handle optimization scenarios
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Should handle cases with and without pose data
        result_without_pose = detector.detect_gestures(test_frame)
        result_with_pose = detector.detect_gestures(test_frame, pose_landmarks=None)
        
        assert result_without_pose is not None, "Should handle case without pose data"
        assert result_with_pose is not None, "Should handle case with None pose data"
        
        detector.cleanup()
    
    # Helper methods for testing
    def _create_mock_pose_landmarks(self):
        """Helper to create mock pose landmarks for testing."""
        landmarks = []
        
        # Create 33 pose landmarks (MediaPipe pose standard)
        for i in range(33):
            landmark = Mock()
            landmark.x = 0.5
            landmark.y = 0.5 if i not in [11, 12] else 0.4  # Shoulders at Y=0.4
            landmark.z = 0.0
            landmark.visibility = 0.9
            landmarks.append(landmark)
        
        # Mock the container object that MediaPipe returns
        mock_pose = Mock()
        mock_pose.landmark = landmarks
        
        return mock_pose 