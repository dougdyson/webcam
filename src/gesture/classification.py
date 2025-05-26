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
            pose_landmarks: MediaPipe pose landmarks object (33 landmarks)
            
        Returns:
            Average Y coordinate of shoulders, or None if landmarks unavailable
        """
        # DEBUG: Check pose landmarks step by step
        print(f"🏃 SHOULDER DEBUG: pose_landmarks = {pose_landmarks}")
        print(f"🏃 SHOULDER DEBUG: pose_landmarks is None = {pose_landmarks is None}")
        
        if pose_landmarks is None:
            print("🏃 SHOULDER DEBUG: Returning None - pose_landmarks is None")
            return None
        
        # Check if this is a MediaPipe landmarks object with .landmark attribute
        print(f"🏃 SHOULDER DEBUG: pose_landmarks type = {type(pose_landmarks)}")
        print(f"🏃 SHOULDER DEBUG: has landmark attr = {hasattr(pose_landmarks, 'landmark')}")
        
        if hasattr(pose_landmarks, 'landmark'):
            # This is the correct MediaPipe landmarks object
            landmarks = pose_landmarks.landmark
            print(f"🏃 SHOULDER DEBUG: Found .landmark attribute with {len(landmarks)} landmarks")
            
            # MediaPipe pose landmark indices for shoulders
            LEFT_SHOULDER = 11
            RIGHT_SHOULDER = 12
            
            try:
                if len(landmarks) > max(LEFT_SHOULDER, RIGHT_SHOULDER):
                    left_shoulder = landmarks[LEFT_SHOULDER]
                    right_shoulder = landmarks[RIGHT_SHOULDER]
                    
                    # Calculate average Y coordinate of shoulders
                    shoulder_y = (left_shoulder.y + right_shoulder.y) / 2.0
                    print(f"🏃 SHOULDER DEBUG: Calculated shoulder Y = {shoulder_y}")
                    return float(shoulder_y)
                else:
                    print(f"🏃 SHOULDER DEBUG: Not enough landmarks: {len(landmarks)}")
                    return None
            except Exception as e:
                print(f"🏃 SHOULDER DEBUG: Error accessing landmarks: {e}")
                return None
        else:
            # This might be the old tuple list format - return None to indicate it's wrong
            print("🏃 SHOULDER DEBUG: Returning None - invalid landmark structure")
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
        
        # DEBUG: Print shoulder calculation details
        print(f"🏃 POSE DEBUG: Shoulder reference Y = {shoulder_reference_y}")
        
        # If no pose data available, cannot detect gesture
        if shoulder_reference_y is None:
            print("❌ No shoulder reference available from pose landmarks")
            return False
        
        # Use existing gesture detection logic
        result = self.detect_hand_up_gesture(
            hand_landmarks=hand_landmarks,
            shoulder_reference_y=shoulder_reference_y,
            palm_normal_vector=palm_normal_vector
        )
        
        print(f"🎯 Final gesture result from pose-based detection: {result}")
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
            raise ValueError(f"shoulder_reference_y must be between 0.0 and 1.0, got {shoulder_reference_y}")
        
        # Calculate hand center Y coordinate (using middle finger MCP as reference)
        hand_center_y = self._get_hand_center_y(hand_landmarks)
        
        # DEBUG: Print the actual values being compared
        print(f"🔍 GESTURE DEBUG:")
        print(f"   Hand center Y: {hand_center_y:.3f}")
        print(f"   Shoulder ref Y: {shoulder_reference_y:.3f}")
        print(f"   Threshold offset: {self.shoulder_offset_threshold:.3f}")
        print(f"   Required Y for 'above': < {shoulder_reference_y - self.shoulder_offset_threshold:.3f}")
        
        # Check if hand is above shoulder level
        # In image coordinates, smaller Y means higher position
        is_above_shoulder = hand_center_y < (shoulder_reference_y - self.shoulder_offset_threshold)
        print(f"   Is above shoulder: {is_above_shoulder}")
        
        # Check if palm is facing camera (positive Z component in normal vector)
        palm_z_component = palm_normal_vector[2]
        is_palm_facing_camera = palm_z_component >= self.palm_facing_confidence
        print(f"   Palm Z component: {palm_z_component:.3f}")
        print(f"   Palm facing threshold: {self.palm_facing_confidence:.3f}")
        print(f"   Is palm facing camera: {is_palm_facing_camera}")
        
        # Both conditions must be met for hand up gesture
        gesture_detected = bool(is_above_shoulder and is_palm_facing_camera)
        print(f"   FINAL GESTURE RESULT: {gesture_detected}")
        
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