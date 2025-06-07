"""
Test finger counting functionality - TDD approach.

This file demonstrates how we should have developed the finger counting feature:
1. Write tests first
2. Run tests (they fail)
3. Write minimal code to pass
4. Refactor
5. Repeat
"""

import pytest
import numpy as np
from unittest.mock import Mock
from src.gesture.classification import GestureClassifier

class MockLandmark:
    """Mock MediaPipe landmark for testing."""
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y 
        self.z = z

class TestFingerCounting:
    """Test cases for finger counting - what we should have written first."""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier for testing."""
        config = {
            'shoulder_offset_threshold': 0.12,
            'palm_facing_confidence': 0.8,
        }
        return GestureClassifier(config)
    
    def create_hand_landmarks(self, finger_states):
        """
        Create mock hand landmarks based on finger states.
        
        Args:
            finger_states: Dict like {'thumb': True, 'index': True, 'middle': False, ...}
            
        Returns:
            List of 21 mock landmarks representing a hand
        """
        # Base hand pose - all landmarks at neutral positions
        landmarks = []
        
        # Wrist (landmark 0)
        landmarks.append(MockLandmark(0.5, 0.7))  # Center-bottom of frame
        
        # Thumb chain (landmarks 1-4)
        thumb_extended = finger_states.get('thumb', False)
        landmarks.extend([
            MockLandmark(0.4, 0.65),  # THUMB_CMC
            MockLandmark(0.35, 0.6),  # THUMB_MCP  
            MockLandmark(0.3, 0.55),  # THUMB_IP
            MockLandmark(0.2 if thumb_extended else 0.32, 0.45 if thumb_extended else 0.57)  # THUMB_TIP - more distance when extended
        ])
        
        # Index finger (landmarks 5-8)
        index_extended = finger_states.get('index', False)
        landmarks.extend([
            MockLandmark(0.55, 0.65), # INDEX_MCP
            MockLandmark(0.58, 0.6),  # INDEX_PIP
            MockLandmark(0.6, 0.55),  # INDEX_DIP
            MockLandmark(0.62, 0.35 if index_extended else 0.65)  # INDEX_TIP - bigger difference
        ])
        
        # Middle finger (landmarks 9-12)
        middle_extended = finger_states.get('middle', False)
        landmarks.extend([
            MockLandmark(0.5, 0.65),  # MIDDLE_MCP
            MockLandmark(0.5, 0.6),   # MIDDLE_PIP
            MockLandmark(0.5, 0.55),  # MIDDLE_DIP
            MockLandmark(0.5, 0.3 if middle_extended else 0.65)  # MIDDLE_TIP - bigger difference
        ])
        
        # Ring finger (landmarks 13-16)
        ring_extended = finger_states.get('ring', False)
        landmarks.extend([
            MockLandmark(0.45, 0.65), # RING_MCP
            MockLandmark(0.42, 0.6),  # RING_PIP
            MockLandmark(0.4, 0.55),  # RING_DIP
            MockLandmark(0.38, 0.35 if ring_extended else 0.65)  # RING_TIP - bigger difference
        ])
        
        # Pinky finger (landmarks 17-20)
        pinky_extended = finger_states.get('pinky', False)
        landmarks.extend([
            MockLandmark(0.4, 0.65),  # PINKY_MCP
            MockLandmark(0.35, 0.6),  # PINKY_PIP
            MockLandmark(0.32, 0.55), # PINKY_DIP
            MockLandmark(0.3, 0.4 if pinky_extended else 0.65)  # PINKY_TIP - bigger difference
        ])
        
        return landmarks

    def test_fist_has_zero_fingers(self, classifier):
        """Test: Closed fist should count as 0 fingers extended."""
        hand_landmarks = self.create_hand_landmarks({
            'thumb': False, 'index': False, 'middle': False, 'ring': False, 'pinky': False
        })
        
        result = classifier._analyze_finger_pattern(hand_landmarks)
        assert result["extended_fingers"] == 0
        assert not any(result["fingers"].values())

    def test_peace_sign_has_two_fingers(self, classifier):
        """Test: Peace sign should count as 2 fingers extended."""
        hand_landmarks = self.create_hand_landmarks({
            'thumb': False, 'index': True, 'middle': True, 'ring': False, 'pinky': False
        })
        
        result = classifier._analyze_finger_pattern(hand_landmarks)
        assert result["extended_fingers"] == 2
        assert result["fingers"]["index"] == True
        assert result["fingers"]["middle"] == True

    def test_open_palm_has_five_fingers(self, classifier):
        """Test: Open palm should count as 5 fingers extended."""
        hand_landmarks = self.create_hand_landmarks({
            'thumb': True, 'index': True, 'middle': True, 'ring': True, 'pinky': True
        })
        
        result = classifier._analyze_finger_pattern(hand_landmarks)
        assert result["extended_fingers"] == 5
        assert all(result["fingers"].values())

    def test_pointing_has_one_finger(self, classifier):
        """Test: Pointing gesture should count as 1 finger extended."""
        hand_landmarks = self.create_hand_landmarks({
            'thumb': False, 'index': True, 'middle': False, 'ring': False, 'pinky': False
        })
        
        result = classifier._analyze_finger_pattern(hand_landmarks)
        assert result["extended_fingers"] == 1
        assert result["fingers"]["index"] == True

    def test_stop_gesture_has_four_fingers(self, classifier):
        """Test: Stop gesture should count as 4 fingers extended."""
        hand_landmarks = self.create_hand_landmarks({
            'thumb': False, 'index': True, 'middle': True, 'ring': True, 'pinky': True
        })
        
        result = classifier._analyze_finger_pattern(hand_landmarks)
        assert result["extended_fingers"] == 4

    def test_empty_landmarks_returns_zero(self, classifier):
        """Test: Empty landmarks should return 0 fingers."""
        result = classifier._analyze_finger_pattern([])
        assert result["extended_fingers"] == 0
        assert not any(result["fingers"].values())

    def test_insufficient_landmarks_returns_zero(self, classifier):
        """Test: Insufficient landmarks (< 21) should return 0 fingers."""
        incomplete_landmarks = [MockLandmark(0.5, 0.5) for _ in range(10)]  # Only 10 landmarks
        result = classifier._analyze_finger_pattern(incomplete_landmarks)
        assert result["extended_fingers"] == 0
        assert not any(result["fingers"].values())

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 