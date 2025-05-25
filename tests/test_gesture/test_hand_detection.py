"""
Test MediaPipe hands integration and landmark extraction.

Testing the integration with MediaPipe hands solution for detecting hand landmarks
and extracting relevant information for gesture classification.
Following TDD methodology: Red → Green → Refactor.
"""

import pytest
import numpy as np
import cv2
from unittest.mock import Mock, patch


class TestHandDetection:
    """Test MediaPipe hands integration for gesture recognition."""
    
    def test_hand_detector_initialization(self):
        """
        RED TEST: Test HandDetector initialization with MediaPipe hands solution.
        
        This test should FAIL initially since we haven't created HandDetector yet!
        """
        from src.gesture.hand_detection import HandDetector
        
        config = {
            'max_num_hands': 2,
            'min_detection_confidence': 0.7,
            'min_tracking_confidence': 0.5,
            'model_complexity': 1
        }
        
        detector = HandDetector(config)
        
        assert detector is not None
        assert detector.max_num_hands == 2
        assert detector.min_detection_confidence == 0.7
        assert detector.min_tracking_confidence == 0.5
        assert detector.model_complexity == 1
    
    def test_detect_hands_with_valid_frame(self):
        """
        RED TEST: Test hand detection on a valid frame.
        
        Should return HandDetectionResult with detected hands when hands are present.
        """
        from src.gesture.hand_detection import HandDetector
        
        detector = HandDetector({})
        
        # Create a sample frame (640x480 RGB)
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # This should return a result object
        result = detector.detect_hands(test_frame)
        
        assert result is not None
        assert hasattr(result, 'hands_detected')
        assert hasattr(result, 'num_hands')
        assert hasattr(result, 'hand_landmarks')
        assert isinstance(result.hands_detected, bool)
        assert isinstance(result.num_hands, int)
        assert result.num_hands >= 0
    
    def test_detect_hands_no_hands_present(self):
        """
        RED TEST: Test hand detection when no hands are present.
        
        Should return result with hands_detected=False and empty landmarks.
        """
        from src.gesture.hand_detection import HandDetector
        
        detector = HandDetector({})
        
        # Empty frame (no hands)
        empty_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        result = detector.detect_hands(empty_frame)
        
        assert result.hands_detected == False
        assert result.num_hands == 0
        assert len(result.hand_landmarks) == 0
    
    def test_extract_hand_landmarks_format(self):
        """
        RED TEST: Test that extracted hand landmarks follow MediaPipe format.
        
        Should return 21 landmarks per hand with x, y, z coordinates.
        """
        from src.gesture.hand_detection import HandDetector
        
        detector = HandDetector({})
        
        # Mock MediaPipe hand landmarks
        mock_hand_landmarks = self._create_mock_mediapipe_hand_landmarks()
        
        extracted = detector.extract_landmarks(mock_hand_landmarks)
        
        assert len(extracted) == 21, "Should have 21 landmarks per hand (MediaPipe standard)"
        
        # Check each landmark has required attributes
        for i, landmark in enumerate(extracted):
            assert hasattr(landmark, 'x'), f"Landmark {i} missing x coordinate"
            assert hasattr(landmark, 'y'), f"Landmark {i} missing y coordinate"
            assert hasattr(landmark, 'z'), f"Landmark {i} missing z coordinate"
            assert 0.0 <= landmark.x <= 1.0, f"Landmark {i} x coordinate should be normalized"
            assert 0.0 <= landmark.y <= 1.0, f"Landmark {i} y coordinate should be normalized"
    
    def test_calculate_palm_normal_vector(self):
        """
        RED TEST: Test palm normal vector calculation for orientation detection.
        
        Should calculate a 3D normal vector indicating palm orientation.
        """
        from src.gesture.hand_detection import HandDetector
        
        detector = HandDetector({})
        
        # Mock hand landmarks for palm normal calculation
        mock_landmarks = self._create_mock_mediapipe_hand_landmarks()
        
        palm_normal = detector.calculate_palm_normal(mock_landmarks)
        
        assert isinstance(palm_normal, np.ndarray), "Palm normal should be numpy array"
        assert palm_normal.shape == (3,), "Palm normal should be 3D vector"
        
        # Check if it's a unit vector (approximately)
        magnitude = np.linalg.norm(palm_normal)
        assert abs(magnitude - 1.0) < 0.1, "Palm normal should be approximately unit vector"
    
    def test_hand_center_calculation(self):
        """
        RED TEST: Test hand center calculation using middle finger MCP.
        
        Should return (x, y) coordinates of hand center.
        """
        from src.gesture.hand_detection import HandDetector
        
        detector = HandDetector({})
        
        mock_landmarks = self._create_mock_mediapipe_hand_landmarks()
        
        hand_center = detector.get_hand_center(mock_landmarks)
        
        assert isinstance(hand_center, tuple), "Hand center should be tuple"
        assert len(hand_center) == 2, "Hand center should be (x, y) coordinates"
        
        x, y = hand_center
        assert 0.0 <= x <= 1.0, "Hand center X should be normalized"
        assert 0.0 <= y <= 1.0, "Hand center Y should be normalized"
    
    def test_hand_detector_cleanup(self):
        """
        RED TEST: Test proper resource cleanup for MediaPipe.
        
        Should release MediaPipe resources when cleanup is called.
        """
        from src.gesture.hand_detection import HandDetector
        
        detector = HandDetector({})
        
        # Detector should be initialized
        assert detector._is_initialized() == True
        
        # Cleanup should release resources
        detector.cleanup()
        
        # After cleanup, detector should not be usable
        assert detector._is_initialized() == False
    
    def test_invalid_frame_handling(self):
        """
        RED TEST: Test error handling for invalid frame inputs.
        
        Should raise appropriate exceptions for invalid inputs.
        """
        from src.gesture.hand_detection import HandDetector
        
        detector = HandDetector({})
        
        # Test None frame
        with pytest.raises(ValueError, match="Frame cannot be None"):
            detector.detect_hands(None)
        
        # Test empty frame
        with pytest.raises(ValueError, match="Frame cannot be empty"):
            detector.detect_hands(np.array([]))
        
        # Test wrong shape
        with pytest.raises(ValueError, match="Frame must be 3-channel RGB"):
            detector.detect_hands(np.random.randint(0, 255, (480, 640), dtype=np.uint8))  # 2D instead of 3D
    
    def test_configuration_validation(self):
        """
        RED TEST: Test configuration validation for HandDetector.
        
        Should validate configuration parameters and raise errors for invalid values.
        """
        from src.gesture.hand_detection import HandDetector
        
        # Test invalid max_num_hands
        with pytest.raises(ValueError, match="max_num_hands must be positive"):
            HandDetector({'max_num_hands': 0})
        
        with pytest.raises(ValueError, match="max_num_hands must be positive"):
            HandDetector({'max_num_hands': -1})
        
        # Test invalid confidence values
        with pytest.raises(ValueError, match="min_detection_confidence must be between 0.0 and 1.0"):
            HandDetector({'min_detection_confidence': -0.1})
        
        with pytest.raises(ValueError, match="min_detection_confidence must be between 0.0 and 1.0"):
            HandDetector({'min_detection_confidence': 1.5})
        
        # Test invalid model complexity
        with pytest.raises(ValueError, match="model_complexity must be 0, 1, or 2"):
            HandDetector({'model_complexity': 3})
    
    # Helper methods for creating test data
    def _create_mock_mediapipe_hand_landmarks(self):
        """Helper to create mock MediaPipe hand landmarks for testing."""
        landmarks = []
        
        # Create 21 landmarks (MediaPipe hands standard)
        for i in range(21):
            landmark = Mock()
            landmark.x = 0.5 + np.random.uniform(-0.2, 0.2)
            landmark.y = 0.5 + np.random.uniform(-0.2, 0.2) 
            landmark.z = 0.1 + np.random.uniform(-0.05, 0.05)
            landmark.visibility = 0.9
            landmarks.append(landmark)
        
        # Set specific key landmarks for realistic positioning
        landmarks[0].x, landmarks[0].y = 0.5, 0.7   # WRIST (bottom center)
        landmarks[9].x, landmarks[9].y = 0.5, 0.4   # MIDDLE_FINGER_MCP (hand center)
        landmarks[12].x, landmarks[12].y = 0.5, 0.2  # MIDDLE_FINGER_TIP (top)
        
        # Mock the container object that MediaPipe returns
        mock_hand = Mock()
        mock_hand.landmark = landmarks
        
        return mock_hand 