"""
Test gesture classification algorithms.

Testing the core gesture detection algorithm for "hand up at shoulder level with palm facing camera".
Following TDD methodology: Red → Green → Refactor.
"""

import pytest
import numpy as np
from unittest.mock import Mock


class TestGestureClassification:
    """Test gesture classification algorithms - starting with hand up detection."""
    
    def test_hand_up_gesture_specification_basic(self):
        """
        Test the basic specification for 'hand up at shoulder level with palm facing camera'.
        
        This test defines what we want to implement:
        1. Hand center Y coordinate should be above shoulder Y coordinate
        2. Palm normal vector should indicate facing camera (positive Z component)
        3. Should return True when both conditions are met
        """
        from src.gesture.classification import GestureClassifier
        
        # Setup test configuration
        config = {
            'shoulder_offset_threshold': 0.1,  # Hand must be 10% above shoulder
            'palm_facing_confidence': 0.6,     # Z component threshold for "facing camera"
        }
        
        classifier = GestureClassifier(config)
        
        # Test case: Hand above shoulder, palm facing camera
        shoulder_y = 0.4  # Shoulder level in normalized coordinates
        hand_center_y = 0.2  # Hand above shoulder (smaller Y = higher in image)
        palm_normal = np.array([0.1, 0.1, 0.8])  # Strong positive Z = facing camera
        
        # Mock hand landmarks
        mock_hand_landmarks = self._create_mock_hand_landmarks(center_y=hand_center_y)
        
        # This should detect a hand up gesture
        is_gesture = classifier.detect_hand_up_gesture(
            hand_landmarks=mock_hand_landmarks,
            shoulder_reference_y=shoulder_y,
            palm_normal_vector=palm_normal
        )
        
        assert is_gesture == True, f"Should detect hand up gesture when hand is above shoulder with palm facing camera. Got: {is_gesture}"
    
    def test_hand_not_up_when_below_shoulder(self):
        """
        Test that hand below shoulder level is NOT detected as hand up gesture.
        
        This test ensures our algorithm correctly rejects hands that are below shoulder level.
        """
        from src.gesture.classification import GestureClassifier
        
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6,
        }
        
        classifier = GestureClassifier(config)
        
        # Test case: Hand below shoulder, but palm facing camera
        shoulder_y = 0.4
        hand_center_y = 0.6  # Hand below shoulder (larger Y = lower in image)
        palm_normal = np.array([0.1, 0.1, 0.8])  # Palm facing camera
        
        mock_hand_landmarks = self._create_mock_hand_landmarks(center_y=hand_center_y)
        
        # This should NOT detect a hand up gesture (hand too low)
        is_gesture = classifier.detect_hand_up_gesture(
            hand_landmarks=mock_hand_landmarks,
            shoulder_reference_y=shoulder_y,
            palm_normal_vector=palm_normal
        )
        
        assert is_gesture == False, "Should NOT detect hand up gesture when hand is below shoulder level"
    
    def test_hand_not_up_when_palm_not_facing_camera(self):
        """
        Test that hand above shoulder but palm NOT facing camera is NOT detected.
        
        This test ensures palm orientation is correctly validated.
        """
        from src.gesture.classification import GestureClassifier
        
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6,
        }
        
        classifier = GestureClassifier(config)
        
        # Test case: Hand above shoulder, but palm facing away from camera
        shoulder_y = 0.4
        hand_center_y = 0.2  # Hand above shoulder
        palm_normal = np.array([0.1, 0.1, -0.8])  # Negative Z = palm facing away
        
        mock_hand_landmarks = self._create_mock_hand_landmarks(center_y=hand_center_y)
        
        # This should NOT detect a hand up gesture (wrong palm orientation)
        is_gesture = classifier.detect_hand_up_gesture(
            hand_landmarks=mock_hand_landmarks,
            shoulder_reference_y=shoulder_y,
            palm_normal_vector=palm_normal
        )
        
        assert is_gesture == False, "Should NOT detect hand up gesture when palm is not facing camera"
    
    def test_gesture_confidence_calculation(self):
        """
        Test confidence calculation for gesture detection.
        
        Confidence should be based on how clearly the criteria are met.
        """
        from src.gesture.classification import GestureClassifier
        
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6,
        }
        
        classifier = GestureClassifier(config)
        
        # Test case: Clear hand up gesture with high confidence
        shoulder_y = 0.4
        hand_center_y = 0.1  # Well above shoulder
        palm_normal = np.array([0.0, 0.0, 1.0])  # Perfect palm facing camera
        
        mock_hand_landmarks = self._create_mock_hand_landmarks(center_y=hand_center_y)
        
        confidence = classifier.calculate_gesture_confidence(
            hand_landmarks=mock_hand_landmarks,
            shoulder_reference_y=shoulder_y,
            palm_normal_vector=palm_normal
        )
        
        assert isinstance(confidence, float), "Confidence should be a float"
        assert 0.0 <= confidence <= 1.0, "Confidence should be between 0.0 and 1.0"
        assert confidence > 0.8, "High-quality gesture should have high confidence"

    # Input validation tests
    def test_invalid_configuration_values(self):
        """Test that invalid configuration values raise ValueError."""
        from src.gesture.classification import GestureClassifier
        
        # Test invalid shoulder_offset_threshold
        with pytest.raises(ValueError, match="shoulder_offset_threshold must be between 0.0 and 1.0"):
            GestureClassifier({'shoulder_offset_threshold': -0.1})
        
        with pytest.raises(ValueError, match="shoulder_offset_threshold must be between 0.0 and 1.0"):
            GestureClassifier({'shoulder_offset_threshold': 1.5})
        
        # Test invalid palm_facing_confidence
        with pytest.raises(ValueError, match="palm_facing_confidence must be between 0.0 and 1.0"):
            GestureClassifier({'palm_facing_confidence': -0.5})
        
        with pytest.raises(ValueError, match="palm_facing_confidence must be between 0.0 and 1.0"):
            GestureClassifier({'palm_facing_confidence': 2.0})
    
    def test_empty_hand_landmarks_raises_error(self):
        """Test that empty hand landmarks raise ValueError."""
        from src.gesture.classification import GestureClassifier
        
        classifier = GestureClassifier({})
        palm_normal = np.array([0.1, 0.1, 0.8])
        
        with pytest.raises(ValueError, match="hand_landmarks cannot be empty"):
            classifier.detect_hand_up_gesture(
                hand_landmarks=[],
                shoulder_reference_y=0.4,
                palm_normal_vector=palm_normal
            )
    
    def test_invalid_palm_normal_vector_raises_error(self):
        """Test that invalid palm normal vectors raise ValueError."""
        from src.gesture.classification import GestureClassifier
        
        classifier = GestureClassifier({})
        mock_landmarks = self._create_mock_hand_landmarks()
        
        # Test non-numpy array
        with pytest.raises(ValueError, match="palm_normal_vector must be a 3D numpy array"):
            classifier.detect_hand_up_gesture(
                hand_landmarks=mock_landmarks,
                shoulder_reference_y=0.4,
                palm_normal_vector=[0.1, 0.1, 0.8]  # List instead of numpy array
            )
        
        # Test wrong size array
        with pytest.raises(ValueError, match="palm_normal_vector must be a 3D numpy array"):
            classifier.detect_hand_up_gesture(
                hand_landmarks=mock_landmarks,
                shoulder_reference_y=0.4,
                palm_normal_vector=np.array([0.1, 0.1])  # Only 2D
            )
    
    def test_invalid_shoulder_reference_y_raises_error(self):
        """Test that invalid shoulder reference Y values raise ValueError."""
        from src.gesture.classification import GestureClassifier
        
        classifier = GestureClassifier({})
        mock_landmarks = self._create_mock_hand_landmarks()
        palm_normal = np.array([0.1, 0.1, 0.8])
        
        # Test negative value
        with pytest.raises(ValueError, match="shoulder_reference_y must be between 0.0 and 1.0"):
            classifier.detect_hand_up_gesture(
                hand_landmarks=mock_landmarks,
                shoulder_reference_y=-0.1,
                palm_normal_vector=palm_normal
            )
        
        # Test value too large
        with pytest.raises(ValueError, match="shoulder_reference_y must be between 0.0 and 1.0"):
            classifier.detect_hand_up_gesture(
                hand_landmarks=mock_landmarks,
                shoulder_reference_y=1.5,
                palm_normal_vector=palm_normal
            )
    
    # Helper methods for testing
    def _create_mock_hand_landmarks(self, center_y=0.4):
        """Helper to create mock hand landmarks for testing."""
        landmarks = []
        
        # Create 21 hand landmarks (MediaPipe standard) with FIXED positions
        for i in range(21):
            landmark = Mock()
            landmark.x = 0.5  # Fixed X position
            landmark.y = center_y  # Base Y position
            landmark.z = 0.1  # Fixed Z position
            landmark.visibility = 0.9
            landmarks.append(landmark)
        
        # Set specific key landmarks
        landmarks[0].y = center_y + 0.15  # WRIST (below hand center)
        landmarks[9].y = center_y        # MIDDLE_FINGER_MCP (hand center reference)
        landmarks[17].y = center_y       # PINKY_MCP
        
        return landmarks 