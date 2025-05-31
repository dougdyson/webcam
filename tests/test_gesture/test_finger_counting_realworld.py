"""
Test finger counting with realistic data to reproduce the peace sign bug.

This demonstrates the TDD approach for fixing real-world bugs:
1. Write a test that reproduces the failing behavior
2. Fix the code to make the test pass
3. Verify all other tests still pass
"""

import pytest
import numpy as np
from src.gesture.classification import GestureClassifier, GestureResult
from src.detection.gesture_detector import GestureDetector

class MockMediaPipeLandmark:
    """More realistic mock that matches MediaPipe landmark structure."""
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y 
        self.z = z

class TestRealWorldFingerCounting:
    """Test finger counting against realistic MediaPipe-like data."""
    
    @pytest.fixture
    def classifier(self):
        config = {
            'shoulder_offset_threshold': 0.12,
            'palm_facing_confidence': 0.8,
        }
        return GestureClassifier(config)
    
    def create_realistic_peace_sign_landmarks(self):
        """
        Create landmarks that closely match a real peace sign from MediaPipe.
        
        Based on the bug report: showing 2 fingers but detected as 3.
        """
        # Peace sign: index and middle extended, thumb/ring/pinky folded
        landmarks = []
        
        # Wrist (0)
        landmarks.append(MockMediaPipeLandmark(0.5, 0.7, 0.0))
        
        # Thumb chain (1-4) - FOLDED
        landmarks.extend([
            MockMediaPipeLandmark(0.45, 0.68, -0.02),  # THUMB_CMC
            MockMediaPipeLandmark(0.42, 0.66, -0.01),  # THUMB_MCP
            MockMediaPipeLandmark(0.40, 0.64, 0.01),   # THUMB_IP
            MockMediaPipeLandmark(0.38, 0.62, 0.02)    # THUMB_TIP - folded
        ])
        
        # Index finger (5-8) - EXTENDED  
        landmarks.extend([
            MockMediaPipeLandmark(0.55, 0.65, 0.0),   # INDEX_MCP
            MockMediaPipeLandmark(0.58, 0.55, 0.01),  # INDEX_PIP
            MockMediaPipeLandmark(0.60, 0.45, 0.02),  # INDEX_DIP
            MockMediaPipeLandmark(0.62, 0.35, 0.03)   # INDEX_TIP - extended
        ])
        
        # Middle finger (9-12) - EXTENDED
        landmarks.extend([
            MockMediaPipeLandmark(0.50, 0.65, 0.0),   # MIDDLE_MCP
            MockMediaPipeLandmark(0.50, 0.52, 0.01),  # MIDDLE_PIP
            MockMediaPipeLandmark(0.50, 0.40, 0.02),  # MIDDLE_DIP
            MockMediaPipeLandmark(0.50, 0.28, 0.03)   # MIDDLE_TIP - extended
        ])
        
        # Ring finger (13-16) - FOLDED
        landmarks.extend([
            MockMediaPipeLandmark(0.45, 0.65, 0.0),   # RING_MCP
            MockMediaPipeLandmark(0.42, 0.62, -0.01), # RING_PIP
            MockMediaPipeLandmark(0.40, 0.60, -0.02), # RING_DIP
            MockMediaPipeLandmark(0.38, 0.58, -0.02)  # RING_TIP - folded
        ])
        
        # Pinky finger (17-20) - FOLDED
        landmarks.extend([
            MockMediaPipeLandmark(0.40, 0.65, 0.0),   # PINKY_MCP
            MockMediaPipeLandmark(0.35, 0.63, -0.01), # PINKY_PIP
            MockMediaPipeLandmark(0.32, 0.61, -0.02), # PINKY_DIP
            MockMediaPipeLandmark(0.30, 0.59, -0.02)  # PINKY_TIP - folded
        ])
        
        return landmarks

    def test_peace_sign_bug_reproduction(self, classifier):
        """
        Test: Reproduce the bug where peace sign is counted as 3 fingers.
        
        This test should FAIL initially, then PASS after we fix the algorithm.
        """
        # Create realistic peace sign landmarks
        hand_landmarks = self.create_realistic_peace_sign_landmarks()
        
        # Count fingers
        finger_count = classifier._count_extended_fingers(hand_landmarks)
        
        # This should be 2, but currently returns 3 (the bug)
        assert finger_count == 2, f"Peace sign should have 2 fingers, got {finger_count}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 