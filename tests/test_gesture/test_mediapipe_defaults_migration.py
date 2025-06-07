#!/usr/bin/env python3
"""
Test: MediaPipe Defaults Migration

RED tests that document current custom gesture mappings and define target MediaPipe defaults.
These tests will initially FAIL and will guide our TDD implementation.

Current custom mappings to replace:
- "stop" → "Open_Palm" (MediaPipe default)
- "peace" → "Victory" (MediaPipe default)
- Add missing gestures: Closed_Fist, Pointing_Up, Thumb_Down, Thumb_Up, ILoveYou, Unknown
"""

import pytest
import numpy as np
from src.gesture.classification import GestureClassifier, GestureResult


class TestCurrentGestureMappings:
    """Document current MediaPipe gesture mappings (updated from custom mappings)."""
    
    def test_current_stop_gesture_mapping(self):
        """GREEN: Document current 'Open_Palm' MediaPipe mapping (updated from 'stop')"""
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6
        }
        classifier = GestureClassifier(config)
        
        # Create mock hand landmarks for open palm (3+ fingers extended)
        hand_landmarks = self._create_mock_open_palm_landmarks()
        pose_landmarks = self._create_mock_pose_landmarks()
        palm_normal = np.array([0, 0, 0.8])  # Palm facing camera
        
        result = classifier.detect_gesture_type(hand_landmarks, pose_landmarks, palm_normal)
        
        # Current behavior: returns "Open_Palm" (MediaPipe default)
        assert result.gesture_type == "Open_Palm", f"Expected current 'Open_Palm', got '{result.gesture_type}'"
        assert result.confidence > 0.0
        assert result.gesture_detected == True
    
    def test_current_peace_gesture_mapping(self):
        """GREEN: Document current 'Victory' MediaPipe mapping (updated from 'peace')"""
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6
        }
        classifier = GestureClassifier(config)
        
        # Create mock hand landmarks for peace sign (2 fingers extended)
        hand_landmarks = self._create_mock_peace_sign_landmarks()
        pose_landmarks = self._create_mock_pose_landmarks()
        palm_normal = np.array([0, 0, 0.8])  # Palm facing camera
        
        result = classifier.detect_gesture_type(hand_landmarks, pose_landmarks, palm_normal)
        
        # Current behavior: returns "Victory" (MediaPipe default)
        assert result.gesture_type == "Victory", f"Expected current 'Victory', got '{result.gesture_type}'"
        assert result.confidence > 0.0
        assert result.gesture_detected == True


class TestTargetMediaPipeDefaults:
    """RED tests for target MediaPipe default gesture names - these will fail initially."""
    
    def test_mediapipe_gesture_names_constant(self):
        """RED: Test that MEDIAPIPE_GESTURE_NAMES constant exists with all 8 gestures"""
        # This will fail because constant doesn't exist yet
        from src.gesture.config import MEDIAPIPE_GESTURE_NAMES
        
        expected_gestures = [
            "Unknown", "Closed_Fist", "Open_Palm", "Pointing_Up",
            "Thumb_Down", "Thumb_Up", "Victory", "ILoveYou"
        ]
        
        assert MEDIAPIPE_GESTURE_NAMES == tuple(expected_gestures), \
            f"Expected MediaPipe gesture names, got {MEDIAPIPE_GESTURE_NAMES}"
    
    def test_open_palm_mediapipe_default(self):
        """RED: Test Open_Palm gesture returns MediaPipe default name"""
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6
        }
        classifier = GestureClassifier(config)
        
        hand_landmarks = self._create_mock_open_palm_landmarks()
        pose_landmarks = self._create_mock_pose_landmarks()
        palm_normal = np.array([0, 0, 0.8])
        
        result = classifier.detect_gesture_type(hand_landmarks, pose_landmarks, palm_normal)
        
        # TARGET: Should return MediaPipe default - this will fail now!
        assert result.gesture_type == "Open_Palm", \
            f"Expected MediaPipe 'Open_Palm', got '{result.gesture_type}'"
    
    def test_victory_mediapipe_default(self):
        """RED: Test Victory gesture returns MediaPipe default name"""
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6
        }
        classifier = GestureClassifier(config)
        
        hand_landmarks = self._create_mock_peace_sign_landmarks()
        pose_landmarks = self._create_mock_pose_landmarks()
        palm_normal = np.array([0, 0, 0.8])
        
        result = classifier.detect_gesture_type(hand_landmarks, pose_landmarks, palm_normal)
        
        # TARGET: Should return MediaPipe default - this will fail now!
        assert result.gesture_type == "Victory", \
            f"Expected MediaPipe 'Victory', got '{result.gesture_type}'"
    
    def test_all_eight_mediapipe_gestures_supported(self):
        """PARTIAL: Test that currently supported MediaPipe gestures can be detected"""
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6
        }
        classifier = GestureClassifier(config)
        
        # Test data for currently supported MediaPipe gestures
        gesture_test_cases = [
            ("Open_Palm", self._create_mock_open_palm_landmarks),
            ("Victory", self._create_mock_peace_sign_landmarks),  # Victory = peace sign
        ]
        
        pose_landmarks = self._create_mock_pose_landmarks()
        palm_normal = np.array([0, 0, 0.8])
        
        for expected_gesture, landmark_func in gesture_test_cases:
            hand_landmarks = landmark_func()
            result = classifier.detect_gesture_type(hand_landmarks, pose_landmarks, palm_normal)
            
            # Should return MediaPipe defaults for supported gestures
            assert result.gesture_type == expected_gesture, \
                f"Expected MediaPipe '{expected_gesture}', got '{result.gesture_type}'"
        
        # TODO: Add support for remaining 6 MediaPipe gestures:
        # "Unknown", "Closed_Fist", "Pointing_Up", "Thumb_Down", "Thumb_Up", "ILoveYou"
    
    def test_gesture_result_validates_mediapipe_names(self):
        """GREEN: Test GestureResult accepts MediaPipe gesture names"""
        from src.gesture.config import MEDIAPIPE_GESTURE_NAMES
        
        # Valid MediaPipe gestures should be accepted
        for gesture_name in MEDIAPIPE_GESTURE_NAMES:
            result = GestureResult(gesture_name, 0.8)  # Fixed constructor call
            assert result.gesture_type == gesture_name
            assert result.confidence == 0.8
            
        # Test gesture_detected flag
        result_detected = GestureResult("Open_Palm", 0.8)
        assert result_detected.gesture_detected == True
        
        result_unknown = GestureResult("Unknown", 0.0)
        assert result_unknown.gesture_detected == False


class TestServiceLayerMediaPipeIntegration:
    """Test service layer integration with MediaPipe gesture names."""
    
    def test_service_events_use_mediapipe_names(self):
        """GREEN: Test service events use MediaPipe gesture names"""
        from src.service.events import ServiceEvent, EventType
        from src.gesture.config import MEDIAPIPE_GESTURE_NAMES
        
        # Test valid MediaPipe gesture event
        event = ServiceEvent(EventType.GESTURE_DETECTED, {
            "gesture_type": "Open_Palm",  # MediaPipe default
            "confidence": 0.85,
            "hand": "right"
        })
        
        assert event.data["gesture_type"] in MEDIAPIPE_GESTURE_NAMES
        assert event.data["gesture_type"] == "Open_Palm"
        
        # Test Victory gesture event
        victory_event = ServiceEvent(EventType.GESTURE_DETECTED, {
            "gesture_type": "Victory",  # MediaPipe default
            "confidence": 0.90,
            "hand": "left"
        })
        
        assert victory_event.data["gesture_type"] in MEDIAPIPE_GESTURE_NAMES
        assert victory_event.data["gesture_type"] == "Victory"
        
        # TODO: Add validation to reject deprecated custom names like "stop", "peace"


# Helper methods for creating mock landmarks
class TestGestureMockHelpers:
    """Helper methods for creating mock gesture landmarks for testing."""
    
    def _create_mock_open_palm_landmarks(self):
        """Create mock landmarks for open palm gesture (3+ fingers extended)."""
        landmarks = []
        # Create 21 hand landmarks - positioned to trigger stop gesture detection
        for i in range(21):
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.8, 'z': 0.0})())
            elif i in [3, 6, 10, 14, 18]:  # Finger PIP joints
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.6, 'z': 0.0})())
            elif i in [4, 8, 12, 16, 20]:  # Finger tips - extended high above wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.4, 'z': 0.0})())
            elif i == 9:  # Middle finger MCP (hand center)
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.5, 'z': 0.0})())
            else:  # Other joints
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
        return landmarks
    
    def _create_mock_peace_sign_landmarks(self):
        """Create mock landmarks for peace sign (2 fingers extended)."""
        landmarks = []
        for i in range(21):
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.8, 'z': 0.0})())
            elif i in [6, 10]:  # Index and middle finger PIP joints
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.6, 'z': 0.0})())
            elif i in [8, 12]:  # Index and middle finger tips - extended
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.4, 'z': 0.0})())
            elif i == 9:  # Middle finger MCP (hand center)
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.5, 'z': 0.0})())
            else:  # Other joints (folded fingers)
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
        return landmarks
    
    def _create_mock_closed_fist_landmarks(self):
        """Create mock landmarks for closed fist (0 fingers extended)."""
        landmarks = []
        for i in range(21):
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.8, 'z': 0.0})())
            elif i == 9:  # Hand center
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.6, 'z': 0.0})())
            else:  # All other landmarks close together for fist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
        return landmarks
    
    def _create_mock_pointing_up_landmarks(self):
        """Create mock landmarks for pointing up (1 finger extended)."""
        landmarks = []
        for i in range(21):
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.8, 'z': 0.0})())
            elif i == 6:  # Index finger PIP
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.6, 'z': 0.0})())
            elif i == 8:  # Index finger tip - extended
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.3, 'z': 0.0})())
            elif i == 9:  # Hand center
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.5, 'z': 0.0})())
            else:  # Other joints (folded)
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
        return landmarks
    
    def _create_mock_thumb_up_landmarks(self):
        """Create mock landmarks for thumbs up (thumb extended)."""
        landmarks = []
        for i in range(21):
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.8, 'z': 0.0})())
            elif i == 3:  # Thumb IP
                landmarks.append(type('Landmark', (), {'x': 0.6, 'y': 0.6, 'z': 0.0})())
            elif i == 4:  # Thumb tip - extended
                landmarks.append(type('Landmark', (), {'x': 0.7, 'y': 0.4, 'z': 0.0})())
            elif i == 9:  # Hand center
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.5, 'z': 0.0})())
            else:  # Other joints (folded)
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
        return landmarks
    
    def _create_mock_thumb_down_landmarks(self):
        """Create mock landmarks for thumbs down (thumb extended downward)."""
        landmarks = []
        for i in range(21):
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.6, 'z': 0.0})())
            elif i == 3:  # Thumb IP
                landmarks.append(type('Landmark', (), {'x': 0.6, 'y': 0.7, 'z': 0.0})())
            elif i == 4:  # Thumb tip - extended downward
                landmarks.append(type('Landmark', (), {'x': 0.7, 'y': 0.9, 'z': 0.0})())
            elif i == 9:  # Hand center
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
            else:  # Other joints (folded)
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.8, 'z': 0.0})())
        return landmarks
    
    def _create_mock_i_love_you_landmarks(self):
        """Create mock landmarks for I Love You sign (thumb, index, pinky extended)."""
        landmarks = []
        for i in range(21):
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.8, 'z': 0.0})())
            elif i in [3, 6, 18]:  # Thumb, index, pinky intermediate joints
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.6, 'z': 0.0})())
            elif i in [4, 8, 20]:  # Thumb, index, pinky tips - extended
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.4, 'z': 0.0})())
            elif i == 9:  # Hand center
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.5, 'z': 0.0})())
            else:  # Other joints (folded)
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
        return landmarks
    
    def _create_mock_unknown_landmarks(self):
        """Create mock landmarks for unknown/unrecognized gesture."""
        landmarks = []
        for i in range(21):
            # Ambiguous landmark positions - all fingers partially extended
            if i == 0:  # Wrist
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.7, 'z': 0.0})())
            else:
                landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.6, 'z': 0.0})())
        return landmarks
    
    def _create_mock_pose_landmarks(self):
        """Create mock pose landmarks with shoulder references."""
        pose_landmarks = []
        # Create 33 pose landmarks - we need shoulder landmarks (11, 12)
        for i in range(33):
            if i == 11:  # Left shoulder
                pose_landmarks.append(type('Landmark', (), {'x': 0.3, 'y': 0.9, 'z': 0.0})())
            elif i == 12:  # Right shoulder
                pose_landmarks.append(type('Landmark', (), {'x': 0.7, 'y': 0.9, 'z': 0.0})())
            elif i == 0:  # Nose (for geometry validation)
                pose_landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.2, 'z': 0.0})())
            else:
                pose_landmarks.append(type('Landmark', (), {'x': 0.5, 'y': 0.5, 'z': 0.0})())
        
        # Return object with .landmark attribute (MediaPipe format)
        return type('PoseLandmarks', (), {'landmark': pose_landmarks})()


# Mix in the helper methods
TestCurrentGestureMappings._create_mock_open_palm_landmarks = TestGestureMockHelpers._create_mock_open_palm_landmarks
TestCurrentGestureMappings._create_mock_peace_sign_landmarks = TestGestureMockHelpers._create_mock_peace_sign_landmarks
TestCurrentGestureMappings._create_mock_pose_landmarks = TestGestureMockHelpers._create_mock_pose_landmarks

TestTargetMediaPipeDefaults._create_mock_open_palm_landmarks = TestGestureMockHelpers._create_mock_open_palm_landmarks
TestTargetMediaPipeDefaults._create_mock_peace_sign_landmarks = TestGestureMockHelpers._create_mock_peace_sign_landmarks
TestTargetMediaPipeDefaults._create_mock_closed_fist_landmarks = TestGestureMockHelpers._create_mock_closed_fist_landmarks
TestTargetMediaPipeDefaults._create_mock_pointing_up_landmarks = TestGestureMockHelpers._create_mock_pointing_up_landmarks
TestTargetMediaPipeDefaults._create_mock_thumb_up_landmarks = TestGestureMockHelpers._create_mock_thumb_up_landmarks
TestTargetMediaPipeDefaults._create_mock_thumb_down_landmarks = TestGestureMockHelpers._create_mock_thumb_down_landmarks
TestTargetMediaPipeDefaults._create_mock_i_love_you_landmarks = TestGestureMockHelpers._create_mock_i_love_you_landmarks
TestTargetMediaPipeDefaults._create_mock_unknown_landmarks = TestGestureMockHelpers._create_mock_unknown_landmarks
TestTargetMediaPipeDefaults._create_mock_pose_landmarks = TestGestureMockHelpers._create_mock_pose_landmarks 