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
    
    def test_shoulder_reference_calculation_from_pose_landmarks(self):
        """
        RED TEST: Test shoulder reference point calculation from MediaPipe pose landmarks.
        
        This integrates with existing pose detection to get shoulder Y coordinate.
        Should calculate average of left and right shoulder landmarks from pose data.
        """
        from src.gesture.classification import GestureClassifier
        
        classifier = GestureClassifier({})
        
        # Mock MediaPipe pose landmarks (33 landmarks total)
        pose_landmarks = self._create_mock_pose_landmarks(
            left_shoulder_y=0.35,   # Left shoulder
            right_shoulder_y=0.37   # Right shoulder  
        )
        
        # Calculate shoulder reference point
        shoulder_y = classifier.calculate_shoulder_reference(pose_landmarks)
        
        assert isinstance(shoulder_y, float), "Shoulder reference should be float"
        assert 0.0 <= shoulder_y <= 1.0, "Shoulder Y should be normalized coordinate"
        
        # Should be average of left and right shoulders
        expected_y = (0.35 + 0.37) / 2  # = 0.36
        assert abs(shoulder_y - expected_y) < 0.01, f"Expected {expected_y}, got {shoulder_y}"
    
    def test_shoulder_reference_with_missing_pose_landmarks(self):
        """
        RED TEST: Test shoulder reference calculation when pose landmarks are missing.
        
        Should handle cases where pose detection failed or landmarks are incomplete.
        """
        from src.gesture.classification import GestureClassifier
        
        classifier = GestureClassifier({})
        
        # Test with None pose landmarks
        shoulder_y = classifier.calculate_shoulder_reference(None)
        assert shoulder_y is None, "Should return None when pose landmarks missing"
        
        # Test with incomplete pose landmarks (less than 33)
        incomplete_landmarks = self._create_mock_pose_landmarks_incomplete()
        shoulder_y = classifier.calculate_shoulder_reference(incomplete_landmarks)
        assert shoulder_y is None, "Should return None when landmarks incomplete"
    
    def test_palm_orientation_facing_camera_detection(self):
        """
        RED TEST: Test palm orientation analysis for "facing camera" detection.
        
        Should use palm normal vector to determine if palm is facing camera.
        Positive Z component indicates facing camera.
        """
        from src.gesture.classification import GestureClassifier
        
        config = {'palm_facing_confidence': 0.6}
        classifier = GestureClassifier(config)
        
        # Test case: Palm clearly facing camera
        palm_normal_facing = np.array([0.1, 0.1, 0.8])  # Strong positive Z
        is_facing = classifier.is_palm_facing_camera(palm_normal_facing)
        assert is_facing == True, "Should detect palm facing camera"
        
        # Test case: Palm facing away from camera  
        palm_normal_away = np.array([0.1, 0.1, -0.8])  # Strong negative Z
        is_facing = classifier.is_palm_facing_camera(palm_normal_away)
        assert is_facing == False, "Should detect palm facing away"
        
        # Test case: Palm perpendicular (borderline)
        palm_normal_side = np.array([0.8, 0.1, 0.1])  # Mostly X component
        is_facing = classifier.is_palm_facing_camera(palm_normal_side)
        assert is_facing == False, "Should reject palm facing sideways"
    
    def test_palm_orientation_confidence_threshold(self):
        """
        RED TEST: Test palm orientation confidence threshold handling.
        
        Should respect the palm_facing_confidence threshold configuration.
        """
        from src.gesture.classification import GestureClassifier
        
        # Test with strict threshold
        strict_config = {'palm_facing_confidence': 0.8}
        strict_classifier = GestureClassifier(strict_config)
        
        # Moderate Z component (below strict threshold)
        palm_normal_moderate = np.array([0.3, 0.3, 0.7])  # Z=0.7 < 0.8
        is_facing = strict_classifier.is_palm_facing_camera(palm_normal_moderate)
        assert is_facing == False, "Should reject moderate Z with strict threshold"
        
        # Test with lenient threshold
        lenient_config = {'palm_facing_confidence': 0.5}
        lenient_classifier = GestureClassifier(lenient_config)
        
        # Same moderate Z component (above lenient threshold)
        is_facing = lenient_classifier.is_palm_facing_camera(palm_normal_moderate)
        assert is_facing == True, "Should accept moderate Z with lenient threshold"
    
    def test_integrated_gesture_detection_with_pose_data(self):
        """
        RED TEST: Test complete gesture detection using pose landmarks for shoulder reference.
        
        This tests the full integration: pose landmarks → shoulder reference → gesture detection.
        """
        from src.gesture.classification import GestureClassifier
        
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6,
        }
        classifier = GestureClassifier(config)
        
        # Setup: Hand above calculated shoulder reference with palm facing camera
        pose_landmarks = self._create_mock_pose_landmarks(
            left_shoulder_y=0.4,    # Shoulders at Y=0.4
            right_shoulder_y=0.4
        )
        
        hand_landmarks = self._create_mock_hand_landmarks(center_y=0.2)  # Hand above shoulders
        palm_normal = np.array([0.1, 0.1, 0.8])  # Palm facing camera
        
        # Test integrated detection
        is_gesture = classifier.detect_hand_up_gesture_with_pose(
            hand_landmarks=hand_landmarks,
            pose_landmarks=pose_landmarks,
            palm_normal_vector=palm_normal
        )
        
        assert is_gesture == True, "Should detect hand up gesture with integrated pose data"
    
    def test_integrated_gesture_detection_no_pose_data(self):
        """
        RED TEST: Test gesture detection fallback when pose data is unavailable.
        
        Should gracefully handle missing pose landmarks.
        """
        from src.gesture.classification import GestureClassifier
        
        classifier = GestureClassifier({})
        
        hand_landmarks = self._create_mock_hand_landmarks()
        palm_normal = np.array([0.1, 0.1, 0.8])
        
        # Test with missing pose landmarks
        is_gesture = classifier.detect_hand_up_gesture_with_pose(
            hand_landmarks=hand_landmarks,
            pose_landmarks=None,  # No pose data available
            palm_normal_vector=palm_normal
        )
        
        assert is_gesture == False, "Should return False when pose data unavailable"

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
    
    def _create_mock_pose_landmarks(self, left_shoulder_y=0.35, right_shoulder_y=0.37):
        """Helper to create mock MediaPipe pose landmarks for testing."""
        landmarks = []
        
        # Create 33 pose landmarks (MediaPipe pose standard)
        for i in range(33):
            landmark = Mock()
            landmark.x = 0.5  # Default X position
            landmark.y = 0.5  # Default Y position  
            landmark.z = 0.0  # Default Z position
            landmark.visibility = 0.9
            landmarks.append(landmark)
        
        # Set specific shoulder landmarks (MediaPipe pose indices)
        landmarks[11].y = left_shoulder_y   # LEFT_SHOULDER
        landmarks[12].y = right_shoulder_y  # RIGHT_SHOULDER
        
        # Mock the container object that MediaPipe returns
        mock_pose = Mock()
        mock_pose.landmark = landmarks
        
        return mock_pose
    
    def _create_mock_pose_landmarks_incomplete(self):
        """Helper to create incomplete pose landmarks for error testing."""
        landmarks = []
        
        # Create only 10 landmarks (less than required 33)
        for i in range(10):
            landmark = Mock()
            landmark.x = 0.5
            landmark.y = 0.5
            landmark.z = 0.0
            landmarks.append(landmark)
        
        mock_pose = Mock()
        mock_pose.landmark = landmarks
        
        return mock_pose 