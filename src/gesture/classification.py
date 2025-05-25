"""
Gesture classification algorithms.

Core gesture detection logic for "hand up at shoulder level with palm facing camera" recognition.
"""

import numpy as np
from typing import List, Any, Dict


class GestureClassifier:
    """
    Classifies hand gestures, specifically "hand up" gestures.
    
    Analyzes hand landmarks and palm orientation to determine if a hand is raised
    at shoulder level with palm facing the camera.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize gesture classifier with configuration.
        
        Args:
            config: Configuration dictionary with thresholds and parameters
            
        Raises:
            ValueError: If configuration values are invalid
        """
        self.shoulder_offset_threshold = config.get('shoulder_offset_threshold', 0.1)
        self.palm_facing_confidence = config.get('palm_facing_confidence', 0.6)
        
        # Validate configuration
        if not 0.0 <= self.shoulder_offset_threshold <= 1.0:
            raise ValueError(f"shoulder_offset_threshold must be between 0.0 and 1.0, got {self.shoulder_offset_threshold}")
        if not 0.0 <= self.palm_facing_confidence <= 1.0:
            raise ValueError(f"palm_facing_confidence must be between 0.0 and 1.0, got {self.palm_facing_confidence}")
    
    def detect_hand_up_gesture(self, hand_landmarks: List[Any], 
                              shoulder_reference_y: float, 
                              palm_normal_vector: np.ndarray) -> bool:
        """
        Detect if the hand is in a "hand up" gesture position.
        
        Criteria:
        1. Hand center must be above shoulder level
        2. Palm must be facing the camera (positive Z normal)
        
        Args:
            hand_landmarks: List of hand landmark objects with x, y, z coordinates
            shoulder_reference_y: Y coordinate of shoulder reference point
            palm_normal_vector: 3D vector indicating palm normal direction
            
        Returns:
            True if hand up gesture detected, False otherwise
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Input validation
        if not hand_landmarks:
            raise ValueError("hand_landmarks cannot be empty")
        if not isinstance(palm_normal_vector, np.ndarray) or palm_normal_vector.size != 3:
            raise ValueError("palm_normal_vector must be a 3D numpy array")
        if not 0.0 <= shoulder_reference_y <= 1.0:
            raise ValueError(f"shoulder_reference_y must be between 0.0 and 1.0, got {shoulder_reference_y}")
        
        # Calculate hand center Y coordinate (using middle finger MCP as reference)
        hand_center_y = self._get_hand_center_y(hand_landmarks)
        
        # Check if hand is above shoulder level
        # In image coordinates, smaller Y means higher position
        is_above_shoulder = hand_center_y < (shoulder_reference_y - self.shoulder_offset_threshold)
        
        # Check if palm is facing camera (positive Z component in normal vector)
        is_palm_facing_camera = palm_normal_vector[2] >= self.palm_facing_confidence
        
        # Both conditions must be met for hand up gesture
        # Convert numpy boolean to Python boolean for consistency
        return bool(is_above_shoulder and is_palm_facing_camera)
    
    def calculate_gesture_confidence(self, hand_landmarks: List[Any], 
                                   shoulder_reference_y: float, 
                                   palm_normal_vector: np.ndarray) -> float:
        """
        Calculate confidence score for gesture detection.
        
        Higher confidence when:
        - Hand is well above shoulder level
        - Palm strongly faces camera
        
        Args:
            hand_landmarks: List of hand landmark objects
            shoulder_reference_y: Y coordinate of shoulder reference
            palm_normal_vector: Palm normal direction vector
            
        Returns:
            Confidence score between 0.0 and 1.0
            
        Raises:
            ValueError: If inputs are invalid
        """
        # Input validation
        if not hand_landmarks:
            raise ValueError("hand_landmarks cannot be empty")
        if not isinstance(palm_normal_vector, np.ndarray) or palm_normal_vector.size != 3:
            raise ValueError("palm_normal_vector must be a 3D numpy array")
        if not 0.0 <= shoulder_reference_y <= 1.0:
            raise ValueError(f"shoulder_reference_y must be between 0.0 and 1.0, got {shoulder_reference_y}")
        
        hand_center_y = self._get_hand_center_y(hand_landmarks)
        
        # Calculate position confidence (how far above shoulder)
        position_offset = shoulder_reference_y - hand_center_y
        position_confidence = min(1.0, max(0.0, position_offset / 0.2))  # Normalize to 0-1
        
        # Calculate palm orientation confidence (how much facing camera)
        palm_z_component = palm_normal_vector[2]
        orientation_confidence = min(1.0, max(0.0, palm_z_component))
        
        # Combined confidence (weighted average)
        total_confidence = (position_confidence * 0.6) + (orientation_confidence * 0.4)
        
        return float(total_confidence)
    
    def _get_hand_center_y(self, hand_landmarks: List[Any]) -> float:
        """
        Get the Y coordinate of the hand center.
        
        Uses middle finger MCP (index 9) as the hand center reference point.
        
        Args:
            hand_landmarks: List of hand landmark objects
            
        Returns:
            Y coordinate of hand center
            
        Raises:
            ValueError: If hand_landmarks is empty
        """
        if not hand_landmarks:
            raise ValueError("hand_landmarks cannot be empty")
        
        # MediaPipe hands landmark 9 is MIDDLE_FINGER_MCP (good hand center reference)
        if len(hand_landmarks) >= 10:
            return float(hand_landmarks[9].y)
        else:
            # Fallback: use average of available landmarks
            return float(sum(landmark.y for landmark in hand_landmarks) / len(hand_landmarks)) 