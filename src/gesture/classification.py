"""
Gesture classification algorithms.

Core gesture detection logic for "hand up at shoulder level with palm facing camera" recognition.
"""

import numpy as np
from typing import List, Any, Dict, Optional


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
    
    def calculate_shoulder_reference(self, pose_landmarks) -> Optional[float]:
        """
        Calculate shoulder reference Y coordinate from MediaPipe pose landmarks.
        
        Uses the average of left and right shoulder landmarks to determine shoulder level.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks object (33 landmarks) or a list of landmarks.
                          The list can contain landmark objects or tuples (x,y).
            
        Returns:
            Average Y coordinate of shoulders, or None if landmarks unavailable
        """
        if pose_landmarks is None:
            return None
        
        landmarks_list = None
        if hasattr(pose_landmarks, 'landmark'): # MediaPipe SolutionOutputs object
            landmarks_list = pose_landmarks.landmark
        elif isinstance(pose_landmarks, list):
            landmarks_list = pose_landmarks
        else:
            return None # Unknown type

        if not landmarks_list:
            return None
            
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
            
        try:
            if len(landmarks_list) > max(LEFT_SHOULDER, RIGHT_SHOULDER):
                left_shoulder_data = landmarks_list[LEFT_SHOULDER]
                right_shoulder_data = landmarks_list[RIGHT_SHOULDER]

                left_y, right_y = None, None

                # Handle landmark objects with .y attribute
                if hasattr(left_shoulder_data, 'y'):
                    left_y = left_shoulder_data.y
                # Handle tuples (x,y)
                elif isinstance(left_shoulder_data, tuple) and len(left_shoulder_data) >= 2:
                    left_y = left_shoulder_data[1] # Assuming y is the second element
                # Handle dictionaries with 'y' key
                elif isinstance(left_shoulder_data, dict) and 'y' in left_shoulder_data:
                    left_y = left_shoulder_data['y']
                
                if hasattr(right_shoulder_data, 'y'):
                    right_y = right_shoulder_data.y
                elif isinstance(right_shoulder_data, tuple) and len(right_shoulder_data) >= 2:
                    right_y = right_shoulder_data[1] # Assuming y is the second element
                elif isinstance(right_shoulder_data, dict) and 'y' in right_shoulder_data:
                    right_y = right_shoulder_data['y']

                if left_y is not None and right_y is not None:
                    shoulder_y = (float(left_y) + float(right_y)) / 2.0
                    return shoulder_y
                else:
                    return None # Could not extract y-coordinates
            else:
                return None # landmarks_list not long enough
        except Exception as e:
            # Log or handle other exceptions if necessary
            # print(f"Exception in calculate_shoulder_reference: {e}")
            return None
    
    def is_palm_facing_camera(self, palm_normal_vector: np.ndarray) -> bool:
        """
        Determine if palm is facing the camera based on normal vector.
        
        Palm faces camera when the Z component of the normal vector is positive
        and above the confidence threshold.
        
        Args:
            palm_normal_vector: 3D normal vector of palm surface
            
        Returns:
            True if palm is facing camera, False otherwise
        """
        if not isinstance(palm_normal_vector, np.ndarray) or palm_normal_vector.size != 3:
            return False
        
        # Palm faces camera when Z component is positive and above threshold
        z_component = palm_normal_vector[2]
        return float(z_component) >= self.palm_facing_confidence
    
    def detect_hand_up_gesture_with_pose(self, hand_landmarks: List[Any], 
                                        pose_landmarks, 
                                        palm_normal_vector: np.ndarray) -> bool:
        """
        Detect hand up gesture using pose landmarks for shoulder reference.
        
        This integrates with existing pose detection to automatically calculate
        shoulder reference point.
        
        Args:
            hand_landmarks: List of hand landmark objects
            pose_landmarks: MediaPipe pose landmarks object
            palm_normal_vector: Palm normal direction vector
            
        Returns:
            True if hand up gesture detected, False otherwise
        """
        # Calculate shoulder reference from pose data
        shoulder_reference_y = self.calculate_shoulder_reference(pose_landmarks)
        
        # If no pose data available, cannot detect gesture
        if shoulder_reference_y is None:
            return False
        
        # Use existing gesture detection logic
        result = self.detect_hand_up_gesture(
            hand_landmarks=hand_landmarks,
            shoulder_reference_y=shoulder_reference_y,
            palm_normal_vector=palm_normal_vector
        )
        
        return result
    
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
            # FIXED: More lenient validation to handle edge cases
            if shoulder_reference_y < -0.1 or shoulder_reference_y > 1.1:
                raise ValueError(f"shoulder_reference_y significantly out of range, got {shoulder_reference_y}")
            # Clamp to valid range for slight variations
            shoulder_reference_y = max(0.0, min(1.0, shoulder_reference_y))
        
        # Calculate hand center Y coordinate (using middle finger MCP as reference)
        hand_center_y = self._get_hand_center_y(hand_landmarks)
        
        # Check if hand is above shoulder level
        # In image coordinates, smaller Y means higher position
        is_above_shoulder = hand_center_y < (shoulder_reference_y - self.shoulder_offset_threshold)
        
        # Check if palm is facing camera (positive Z component in normal vector)
        palm_z_component = palm_normal_vector[2]
        is_palm_facing_camera = palm_z_component >= self.palm_facing_confidence
        
        # Both conditions must be met for hand up gesture
        gesture_detected = bool(is_above_shoulder and is_palm_facing_camera)
        
        return gesture_detected
    
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
            # FIXED: More lenient validation to handle edge cases
            if shoulder_reference_y < -0.1 or shoulder_reference_y > 1.1:
                raise ValueError(f"shoulder_reference_y significantly out of range, got {shoulder_reference_y}")
            # Clamp to valid range for slight variations
            shoulder_reference_y = max(0.0, min(1.0, shoulder_reference_y))
        
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
    
    def detect_open_palm_gesture(self, hand_landmarks: List[Any], 
                                 palm_normal_vector: np.ndarray) -> bool:
        """
        Detect open palm facing camera gesture (simplified approach).
        
        No shoulder reference needed - just check if palm is clearly facing camera.
        Much more reliable than position-based detection.
        
        Args:
            hand_landmarks: List of hand landmark objects
            palm_normal_vector: 3D vector indicating palm normal direction
            
        Returns:
            True if open palm facing camera detected, False otherwise
        """
        # Input validation
        if not hand_landmarks:
            return False
        if not isinstance(palm_normal_vector, np.ndarray) or palm_normal_vector.size != 3:
            return False
        
        # Check if palm is clearly facing camera (positive Z component)
        palm_z_component = palm_normal_vector[2]
        is_palm_facing_camera = palm_z_component >= self.palm_facing_confidence
        
        return is_palm_facing_camera
    
    def calculate_open_palm_confidence(self, hand_landmarks: List[Any], 
                                      palm_normal_vector: np.ndarray) -> float:
        """
        Calculate confidence for open palm gesture.
        
        Based purely on palm orientation quality.
        
        Args:
            hand_landmarks: List of hand landmark objects
            palm_normal_vector: 3D vector indicating palm normal direction
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not hand_landmarks or not isinstance(palm_normal_vector, np.ndarray):
            return 0.0
        
        # Base confidence on how strongly the palm faces camera
        palm_z_component = palm_normal_vector[2]
        
        # Normalize Z component to confidence (0.8+ becomes 0.8-1.0 confidence)
        if palm_z_component >= self.palm_facing_confidence:
            # Map from palm_facing_confidence to 1.0 -> 0.8 to 1.0 confidence
            confidence = 0.8 + (palm_z_component - self.palm_facing_confidence) * 0.2 / (1.0 - self.palm_facing_confidence)
            return min(1.0, max(0.0, confidence))
        else:
            return 0.0 