"""
Gesture classification algorithms.

Core gesture detection logic for "hand up at shoulder level with palm facing camera" recognition.
"""

import numpy as np
from typing import List, Any, Dict, Optional


class GestureResult:
    """Result of gesture detection with type and confidence."""
    
    def __init__(self, gesture_type: str, confidence: float, position: Optional[Dict] = None):
        self.gesture_type = gesture_type
        self.confidence = confidence
        self.position = position or {}
        self.gesture_detected = gesture_type != "Unknown"  # Updated from "none"
        
        # Updated legacy compatibility for MediaPipe defaults
        self.palm_facing_camera = gesture_type in ["Open_Palm", "Victory"]

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
        shoulder reference point and validates proper stop gesture arm geometry.
        
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
        
        # NEW: Validate that hand is in open palm configuration (not peace sign, etc.)
        is_open_palm = self._validate_open_palm_shape(hand_landmarks)
        if not is_open_palm:
            return False  # Reject peace signs, pointing, etc.
        
        # NEW: Validate proper stop gesture arm geometry
        is_proper_arm_extension = self._validate_stop_gesture_arm_geometry(
            hand_landmarks, pose_landmarks
        )
        
        if not is_proper_arm_extension:
            return False  # Reject hands behind head, awkward positions
        
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
    
    def _validate_open_palm_shape(self, hand_landmarks: List[Any]) -> bool:
        """
        Validate that the hand is in an open palm configuration for a stop gesture.
        
        Checks that multiple fingers are extended, not just 2 fingers (peace sign)
        or 1 finger (pointing). A proper stop gesture should show an open palm.
        
        Args:
            hand_landmarks: List of hand landmark objects (MediaPipe format)
            
        Returns:
            True if hand shows open palm shape, False otherwise
        """
        if not hand_landmarks or len(hand_landmarks) < 21:
            return False
        
        try:
            # MediaPipe hand landmark indices for fingertips and joints
            # Thumb: 4 (tip), 3 (ip), 2 (mcp)
            # Index: 8 (tip), 7 (dip), 6 (pip), 5 (mcp)
            # Middle: 12 (tip), 11 (dip), 10 (pip), 9 (mcp)
            # Ring: 16 (tip), 15 (dip), 14 (pip), 13 (mcp)
            # Pinky: 20 (tip), 19 (dip), 18 (pip), 17 (mcp)
            
            extended_fingers = 0
            
            # Check thumb extension (special case - compare distances from wrist)
            thumb_tip = hand_landmarks[4]
            thumb_ip = hand_landmarks[3]
            wrist = hand_landmarks[0]
            
            thumb_distance_tip = ((thumb_tip.x - wrist.x) ** 2 + (thumb_tip.y - wrist.y) ** 2) ** 0.5
            thumb_distance_ip = ((thumb_ip.x - wrist.x) ** 2 + (thumb_ip.y - wrist.y) ** 2) ** 0.5
            
            if thumb_distance_tip > thumb_distance_ip * 1.1:  # 10% tolerance
                extended_fingers += 1
            
            # Check other fingers (compare Y coordinates - tip should be higher than PIP joint)
            finger_data = [
                (8, 6),   # Index: tip vs PIP
                (12, 10), # Middle: tip vs PIP  
                (16, 14), # Ring: tip vs PIP
                (20, 18)  # Pinky: tip vs PIP
            ]
            
            for tip_idx, pip_idx in finger_data:
                tip = hand_landmarks[tip_idx]
                pip = hand_landmarks[pip_idx]
                
                # Finger is extended if tip is higher (lower Y value) than PIP joint
                if tip.y < pip.y - 0.02:  # Small threshold for noise tolerance
                    extended_fingers += 1
            
            # For a stop gesture, we need at least 3-4 fingers extended
            # This rejects peace signs (2 fingers), pointing (1 finger), fists (0 fingers)
            return extended_fingers >= 3
            
        except (IndexError, AttributeError, TypeError):
            # If any landmark access fails, reject the gesture
            return False
    
    def _validate_stop_gesture_arm_geometry(self, hand_landmarks: List[Any], pose_landmarks) -> bool:
        """
        Validate that the arm geometry represents a proper "stop" gesture.
        
        Checks:
        1. Hand is in front of body (not behind head)
        2. Proper arm extension (not bent backward)
        3. Hand position relative to shoulder suggests forward extension
        
        Args:
            hand_landmarks: List of hand landmark objects
            pose_landmarks: MediaPipe pose landmarks object
            
        Returns:
            True if arm geometry indicates proper stop gesture, False otherwise
        """
        if not hand_landmarks or pose_landmarks is None:
            return False
        
        try:
            # Get key landmarks
            wrist = hand_landmarks[0]  # WRIST landmark
            hand_center = hand_landmarks[9]  # MIDDLE_FINGER_MCP
            
            # Get pose landmarks
            landmarks_list = None
            if hasattr(pose_landmarks, 'landmark'):
                landmarks_list = pose_landmarks.landmark
            elif isinstance(pose_landmarks, list):
                landmarks_list = pose_landmarks
            else:
                return False
            
            if not landmarks_list or len(landmarks_list) < 16:
                return False
            
            # MediaPipe pose landmark indices
            LEFT_SHOULDER = 11
            RIGHT_SHOULDER = 12
            NOSE = 0
            
            # Get shoulder and nose positions
            left_shoulder = landmarks_list[LEFT_SHOULDER]
            right_shoulder = landmarks_list[RIGHT_SHOULDER]
            nose = landmarks_list[NOSE]
            
            # Calculate body center (between shoulders)
            body_center_x = (self._get_landmark_x(left_shoulder) + self._get_landmark_x(right_shoulder)) / 2
            body_center_y = (self._get_landmark_y(left_shoulder) + self._get_landmark_y(right_shoulder)) / 2
            
            # Get hand and wrist positions
            hand_x = hand_center.x
            hand_y = hand_center.y
            wrist_x = wrist.x
            wrist_y = wrist.y
            nose_x = self._get_landmark_x(nose)
            nose_y = self._get_landmark_y(nose)
            
            # Check 1: Hand should not be too close to face/head
            # If hand is very close to nose position, likely behind head
            distance_to_nose = ((hand_x - nose_x) ** 2 + (hand_y - nose_y) ** 2) ** 0.5
            if distance_to_nose < 0.25:  # Too close to face - increased back to 0.25
                return False
            
            # Check 1b: Hand should not be significantly higher than head
            # If hand is much higher than nose, likely behind head
            if hand_y < nose_y - 0.08:  # Hand more than 8% above nose level
                return False
            
            # Check 2: Removed "too far to the side" check - unnecessary for webcam FOV
            
            # Check 3: Arm extension direction - hand should be forward from shoulder
            # Calculate which shoulder is closer to the hand
            distance_to_left = ((hand_x - self._get_landmark_x(left_shoulder)) ** 2 + 
                              (hand_y - self._get_landmark_y(left_shoulder)) ** 2) ** 0.5
            distance_to_right = ((hand_x - self._get_landmark_x(right_shoulder)) ** 2 + 
                               (hand_y - self._get_landmark_y(right_shoulder)) ** 2) ** 0.5
            
            # Use closer shoulder as reference
            if distance_to_left < distance_to_right:
                shoulder_x = self._get_landmark_x(left_shoulder)
                shoulder_y = self._get_landmark_y(left_shoulder)
            else:
                shoulder_x = self._get_landmark_x(right_shoulder)
                shoulder_y = self._get_landmark_y(right_shoulder)
            
            # Check 4: Wrist-to-hand vector should indicate proper extension
            wrist_to_hand_x = hand_x - wrist_x
            wrist_to_hand_y = hand_y - wrist_y
            
            # For a stop gesture, hand should be extended from wrist (positive distance)
            wrist_to_hand_distance = (wrist_to_hand_x ** 2 + wrist_to_hand_y ** 2) ** 0.5
            if wrist_to_hand_distance < 0.05:  # Hand too close to wrist (not extended)
                return False
            
            # Check 5: Overall arm position - shoulder to hand vector
            shoulder_to_hand_x = hand_x - shoulder_x
            shoulder_to_hand_y = hand_y - shoulder_y
            
            # For stop gesture, hand should be reasonably extended from shoulder
            shoulder_to_hand_distance = (shoulder_to_hand_x ** 2 + shoulder_to_hand_y ** 2) ** 0.5
            if shoulder_to_hand_distance < 0.2:  # Too close to shoulder
                return False
            
            # All checks passed - this looks like proper stop gesture arm geometry
            return True
            
        except (IndexError, AttributeError, TypeError):
            # If any landmark access fails, reject the gesture
            return False
    
    def _get_landmark_x(self, landmark) -> float:
        """Get X coordinate from landmark (handles different landmark types)."""
        if hasattr(landmark, 'x'):
            return float(landmark.x)
        elif isinstance(landmark, tuple) and len(landmark) >= 2:
            return float(landmark[0])
        elif isinstance(landmark, dict) and 'x' in landmark:
            return float(landmark['x'])
        else:
            return 0.0
    
    def _get_landmark_y(self, landmark) -> float:
        """Get Y coordinate from landmark (handles different landmark types)."""
        if hasattr(landmark, 'y'):
            return float(landmark.y)
        elif isinstance(landmark, tuple) and len(landmark) >= 2:
            return float(landmark[1])
        elif isinstance(landmark, dict) and 'y' in landmark:
            return float(landmark['y'])
        else:
            return 0.0
    
    def detect_gesture_type(self, hand_landmarks: List[Any], 
                           pose_landmarks, 
                           palm_normal_vector: np.ndarray) -> GestureResult:
        """
        Comprehensive gesture detection that classifies ALL 8 MediaPipe gesture types.
        
        Returns MediaPipe default gesture names:
        - "Open_Palm": Open palm gesture (3+ fingers, above shoulders, proper position)
        - "Victory": Victory/Peace sign (exactly 2 fingers extended: index + middle)
        - "Closed_Fist": Closed fist (0 fingers extended)
        - "Pointing_Up": Index finger pointing up (1 finger extended: index)
        - "Thumb_Up": Thumbs up (1 finger extended: thumb)
        - "Thumb_Down": Thumbs down (1 finger extended: thumb, palm away)
        - "ILoveYou": ASL I Love You (3 fingers: thumb + index + pinky)
        - "Unknown": No recognized gesture
        
        Args:
            hand_landmarks: List of hand landmark objects
            pose_landmarks: MediaPipe pose landmarks object  
            palm_normal_vector: Palm normal direction vector
            
        Returns:
            GestureResult with MediaPipe default gesture type, confidence, and position info
        """
        if not hand_landmarks or pose_landmarks is None:
            return GestureResult("Unknown", 0.0)
        
        # Calculate shoulder reference from pose data
        shoulder_reference_y = self.calculate_shoulder_reference(pose_landmarks)
        if shoulder_reference_y is None:
            return GestureResult("Unknown", 0.0)
        
        # Get hand center position
        hand_center_y = self._get_hand_center_y(hand_landmarks)
        hand_center_x = hand_landmarks[9].x if len(hand_landmarks) > 9 else 0.5
        
        # Check basic position requirements for most gestures
        is_above_shoulder = hand_center_y < (shoulder_reference_y - self.shoulder_offset_threshold)
        palm_z_component = palm_normal_vector[2] if isinstance(palm_normal_vector, np.ndarray) and palm_normal_vector.size == 3 else 0
        is_palm_facing_camera = palm_z_component >= self.palm_facing_confidence
        
        position_info = {
            "hand_x": hand_center_x,
            "hand_y": hand_center_y,
            "palm_z": palm_z_component
        }
        
        # Get detailed finger analysis
        finger_analysis = self._analyze_finger_pattern(hand_landmarks)
        position_info.update(finger_analysis)
        
        # GESTURE CLASSIFICATION - Enhanced for all 8 MediaPipe gestures
        
        # 1. CLOSED_FIST: No fingers extended
        if finger_analysis["extended_fingers"] == 0:
            # Closed fist doesn't need palm facing camera or high position
            confidence = 0.9 if is_above_shoulder else 0.7
            return GestureResult("Closed_Fist", confidence, position_info)
        
        # 2. POINTING_UP: Only index finger extended
        elif (finger_analysis["extended_fingers"] == 1 and 
              finger_analysis["fingers"]["index"] and 
              is_above_shoulder):
            confidence = 0.9 if is_palm_facing_camera else 0.7
            return GestureResult("Pointing_Up", confidence, position_info)
        
        # 3. THUMB_UP: Only thumb extended, palm facing AWAY (showing back of hand)
        elif (finger_analysis["extended_fingers"] == 1 and 
              finger_analysis["fingers"]["thumb"] and 
              not is_palm_facing_camera):
            confidence = 0.9
            return GestureResult("Thumb_Up", confidence, position_info)
        
        # 4. THUMB_DOWN: Only thumb extended, palm facing TOWARDS camera (showing palm)
        elif (finger_analysis["extended_fingers"] == 1 and 
              finger_analysis["fingers"]["thumb"] and 
              is_palm_facing_camera):
            confidence = 0.8
            return GestureResult("Thumb_Down", confidence, position_info)
        
        # 5. VICTORY: Index + middle fingers extended
        elif (finger_analysis["extended_fingers"] == 2 and
              finger_analysis["fingers"]["index"] and 
              finger_analysis["fingers"]["middle"] and
              is_above_shoulder and is_palm_facing_camera):
            confidence = min(0.9, max(0.6, palm_z_component))
            return GestureResult("Victory", confidence, position_info)
        
        # 6. ILOVEYOU: Thumb + index + pinky extended (ASL I Love You)
        elif (finger_analysis["extended_fingers"] == 3 and
              finger_analysis["fingers"]["thumb"] and 
              finger_analysis["fingers"]["index"] and 
              finger_analysis["fingers"]["pinky"] and
              not finger_analysis["fingers"]["middle"] and
              not finger_analysis["fingers"]["ring"]):
            confidence = 0.9 if (is_above_shoulder and is_palm_facing_camera) else 0.7
            return GestureResult("ILoveYou", confidence, position_info)
        
        # 7. OPEN_PALM: 3+ fingers extended (but not ILoveYou pattern)
        elif (finger_analysis["extended_fingers"] >= 3 and
              is_above_shoulder and is_palm_facing_camera):
            # Check arm geometry for open palm
            is_proper_arm_geometry = self._validate_stop_gesture_arm_geometry(hand_landmarks, pose_landmarks)
            if is_proper_arm_geometry:
                confidence = self.calculate_gesture_confidence(hand_landmarks, shoulder_reference_y, palm_normal_vector)
                return GestureResult("Open_Palm", confidence, position_info)
        
        # 8. UNKNOWN: No recognized pattern
        return GestureResult("Unknown", 0.0, position_info)

    def _analyze_finger_pattern(self, hand_landmarks: List[Any]) -> Dict:
        """
        Analyze detailed finger extension patterns for accurate gesture classification.
        
        Returns:
            Dict with finger analysis including individual finger states
        """
        if not hand_landmarks or len(hand_landmarks) < 21:
            return {
                "extended_fingers": 0,
                "fingers": {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
            }
        
        try:
            fingers = {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
            
            # THUMB: Special case - compare distances from wrist (lateral extension)
            thumb_tip = hand_landmarks[4]
            thumb_ip = hand_landmarks[3]
            wrist = hand_landmarks[0]
            
            thumb_distance_tip = ((thumb_tip.x - wrist.x) ** 2 + (thumb_tip.y - wrist.y) ** 2) ** 0.5
            thumb_distance_ip = ((thumb_ip.x - wrist.x) ** 2 + (thumb_ip.y - wrist.y) ** 2) ** 0.5
            
            if thumb_distance_tip > thumb_distance_ip * 1.2:  # 20% tolerance for thumb
                fingers["thumb"] = True
            
            # INDEX FINGER: tip vs PIP joint
            if hand_landmarks[8].y < hand_landmarks[6].y - 0.06:  # 6% threshold
                fingers["index"] = True
            
            # MIDDLE FINGER: tip vs PIP joint
            if hand_landmarks[12].y < hand_landmarks[10].y - 0.06:
                fingers["middle"] = True
            
            # RING FINGER: tip vs PIP joint
            if hand_landmarks[16].y < hand_landmarks[14].y - 0.06:
                fingers["ring"] = True
            
            # PINKY: tip vs PIP joint
            if hand_landmarks[20].y < hand_landmarks[18].y - 0.06:
                fingers["pinky"] = True
            
            extended_count = sum(fingers.values())
            
            return {
                "extended_fingers": extended_count,
                "fingers": fingers
            }
            
        except (IndexError, AttributeError, TypeError):
            return {
                "extended_fingers": 0,
                "fingers": {"thumb": False, "index": False, "middle": False, "ring": False, "pinky": False}
            } 