"""
Test for proper gesture naming - TDD approach.

This ensures we use specific, descriptive names for gestures.
"""

import pytest
import numpy as np
from src.gesture.classification import GestureClassifier, GestureResult

class MockLandmark:
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y 
        self.z = z

class TestGestureNaming:
    """Test that gestures use specific, descriptive names."""
    
    @pytest.fixture
    def classifier(self):
        config = {
            'shoulder_offset_threshold': 0.12,
            'palm_facing_confidence': 0.8,
        }
        return GestureClassifier(config)
    
    def create_stop_gesture_landmarks(self):
        """Create landmarks for an open palm stop gesture (4-5 fingers)."""
        landmarks = []
        
        # Wrist - at lower Y position to be below hand center
        landmarks.append(MockLandmark(0.5, 0.8))
        
        # All fingers extended for stop gesture
        # Thumb extended
        landmarks.extend([
            MockLandmark(0.4, 0.75), MockLandmark(0.35, 0.7), 
            MockLandmark(0.3, 0.65), MockLandmark(0.2, 0.55)
        ])
        # Index extended  
        landmarks.extend([
            MockLandmark(0.55, 0.75), MockLandmark(0.58, 0.7),
            MockLandmark(0.6, 0.65), MockLandmark(0.62, 0.4)  # Tip well above PIP
        ])
        # Middle extended
        landmarks.extend([
            MockLandmark(0.5, 0.75), MockLandmark(0.5, 0.7),
            MockLandmark(0.5, 0.65), MockLandmark(0.5, 0.35)  # Tip well above PIP
        ])
        # Ring extended
        landmarks.extend([
            MockLandmark(0.45, 0.75), MockLandmark(0.42, 0.7),
            MockLandmark(0.4, 0.65), MockLandmark(0.38, 0.4)  # Tip well above PIP
        ])
        # Pinky extended
        landmarks.extend([
            MockLandmark(0.4, 0.75), MockLandmark(0.35, 0.7),
            MockLandmark(0.32, 0.65), MockLandmark(0.3, 0.45)  # Tip well above PIP
        ])
        
        return landmarks

    def create_mock_pose_landmarks(self):
        """Create mock pose landmarks with proper shoulder positions."""
        return type('MockPose', (), {
            'landmark': [
                MockLandmark(0.5, 0.4, 0.0),   # NOSE - above hand
                *[MockLandmark(0.4, 0.5, 0.0) for _ in range(10)],  # Other landmarks
                MockLandmark(0.3, 0.9, 0.0),   # LEFT_SHOULDER - below hand  
                MockLandmark(0.7, 0.9, 0.0),   # RIGHT_SHOULDER - below hand
                *[MockLandmark(0.5, 1.0, 0.0) for _ in range(20)]   # More landmarks
            ]
        })()

    def test_open_palm_should_be_stop_not_hand_up(self, classifier):
        """
        Test: Open palm gestures should be classified as 'stop', not 'hand_up'.
        
        This is a naming convention test - ensures we use specific terminology.
        """
        hand_landmarks = self.create_stop_gesture_landmarks()
        pose_landmarks = self.create_mock_pose_landmarks()
        palm_normal = np.array([0.0, 0.0, 0.9])  # Facing camera
        
        result = classifier.detect_gesture_type(hand_landmarks, pose_landmarks, palm_normal)
        
        # Should be 'stop', never 'hand_up'
        assert result.gesture_type == "stop", f"Expected 'stop', got '{result.gesture_type}'"
        assert result.gesture_type != "hand_up", "Should not use generic 'hand_up' terminology"
        assert result.gesture_detected == True
        
    def test_supported_gesture_types_are_specific(self, classifier):
        """Test: All supported gesture types should be specific, not generic."""
        # This test documents our supported gesture vocabulary
        supported_types = ["stop", "peace", "none"]
        
        # Test that we don't return generic names
        forbidden_types = ["hand_up", "gesture", "detected", "unknown"]
        
        # Create different gestures and verify naming
        hand_landmarks = self.create_stop_gesture_landmarks()
        pose_landmarks = self.create_mock_pose_landmarks()  
        palm_normal = np.array([0.0, 0.0, 0.9])
        
        result = classifier.detect_gesture_type(hand_landmarks, pose_landmarks, palm_normal)
        
        assert result.gesture_type in supported_types, f"Gesture type '{result.gesture_type}' not in supported list"
        assert result.gesture_type not in forbidden_types, f"Should not use generic name '{result.gesture_type}'"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 