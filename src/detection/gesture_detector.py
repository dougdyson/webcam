"""
Gesture detector implementation.

This module implements gesture detection using MediaPipe hands combined with
gesture classification algorithms. Focused on detecting "hand up at shoulder level
with palm facing camera" gestures.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Optional, Any
import logging

from .base import HumanDetector, DetectorConfig, DetectorError
from ..gesture.result import GestureResult, HandDetectionResult
from ..gesture.classification import GestureClassifier

logger = logging.getLogger(__name__)


class GestureDetector(HumanDetector):
    """
    Gesture detector using MediaPipe hands and gesture classification.
    
    Detects hand gestures, specifically "hand up at shoulder level with palm facing camera".
    Integrates with existing pose detection for shoulder reference points.
    
    Optimized for:
    - Hand landmark detection using MediaPipe hands
    - Palm orientation analysis
    - Integration with pose detection for shoulder reference
    - Performance optimization (only runs when human present)
    """
    
    def __init__(self, config: Optional[DetectorConfig] = None):
        """
        Initialize gesture detector.
        
        Args:
            config: Detector configuration, defaults to DetectorConfig()
        """
        super().__init__(config)
        
        # MediaPipe components
        self._mp_hands = None
        self._hands_detector = None
        self._initialized = False
        
        # Gesture analysis components
        self._gesture_classifier = None
        
        # Configuration for gesture detection
        self._max_num_hands = 2  # Detect up to 2 hands
        self._gesture_config = {
            'shoulder_offset_threshold': 0.1,  # Hand must be 10% above shoulder
            'palm_facing_confidence': 0.6,     # Z component threshold for facing camera
        }
    
    def initialize(self) -> None:
        """
        Initialize MediaPipe hands detection and gesture classification.
        
        Raises:
            DetectorError: If MediaPipe initialization fails
        """
        if self._initialized:
            return  # Idempotent initialization
        
        try:
            # Initialize MediaPipe hands
            self._mp_hands = mp.solutions.hands
            
            # Create hands detection instance
            self._hands_detector = self._mp_hands.Hands(
                static_image_mode=self.config.static_image_mode,
                max_num_hands=self._max_num_hands,
                model_complexity=self.config.model_complexity,
                min_detection_confidence=self.config.min_detection_confidence,
                min_tracking_confidence=self.config.min_tracking_confidence
            )
            
            # Initialize gesture classifier (no need for separate HandDetector)
            self._gesture_classifier = GestureClassifier(self._gesture_config)
            
            self._initialized = True
            logger.info("Gesture detector initialized successfully")
            
        except Exception as e:
            self._initialized = False
            raise DetectorError(
                "Failed to initialize gesture detector",
                original_error=e
            )
    
    def cleanup(self) -> None:
        """
        Clean up MediaPipe and gesture detection resources.
        
        Logs errors but does not raise exceptions to ensure cleanup always completes.
        """
        try:
            if self._hands_detector is not None:
                self._hands_detector.close()
                self._hands_detector = None
            
            self._mp_hands = None
            self._gesture_classifier = None
            self._initialized = False
            
            logger.info("Gesture detector cleaned up successfully")
            
        except Exception as e:
            # Log error but don't raise - cleanup should always complete
            logger.error(f"Error during gesture detector cleanup: {e}")
            self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """
        Check if detector is properly initialized.
        
        Returns:
            True if detector is ready for detection, False otherwise
        """
        return (self._initialized and 
                self._hands_detector is not None and
                self._gesture_classifier is not None)
    
    def detect_gestures(self, frame: np.ndarray, pose_landmarks: Optional[Any] = None) -> GestureResult:
        """
        Detect hand gestures in a frame.
        
        Args:
            frame: Input frame as numpy array (H, W, C) in BGR format
            pose_landmarks: Optional MediaPipe pose landmarks for shoulder reference
            
        Returns:
            GestureResult with gesture detection information
            
        Raises:
            DetectorError: If detection fails or detector not initialized
        """
        if not self.is_initialized:
            raise DetectorError("Detector not initialized. Call initialize() first.")
        
        # Validate frame format
        self._validate_frame(frame)
        
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect hands using MediaPipe
            hands_results = self._hands_detector.process(rgb_frame)
            
            # Process gesture detection
            return self._process_gesture_detection(hands_results, pose_landmarks, frame.shape)
                
        except Exception as e:
            raise DetectorError(
                "Gesture detection processing failed",
                original_error=e
            )
    
    def detect(self, frame: np.ndarray) -> GestureResult:
        """
        Detect gestures - alias for detect_gestures for HumanDetector interface.
        
        Note: This method exists to satisfy the HumanDetector interface,
        but detect_gestures() is the preferred method for gesture detection.
        
        Args:
            frame: Input frame as numpy array (H, W, C) in BGR format
            
        Returns:
            GestureResult with gesture detection information
        """
        return self.detect_gestures(frame)
    
    def _validate_frame(self, frame: np.ndarray) -> None:
        """
        Validate input frame format.
        
        Args:
            frame: Input frame to validate
            
        Raises:
            DetectorError: If frame format is invalid
        """
        if frame is None:
            raise DetectorError("Invalid frame format: frame is None")
        
        if not isinstance(frame, np.ndarray):
            raise DetectorError("Invalid frame format: frame must be numpy array")
        
        if frame.ndim != 3:
            raise DetectorError("Invalid frame format: frame must be 3-dimensional (H, W, C)")
        
        if frame.shape[2] != 3:
            raise DetectorError("Invalid frame format: frame must have 3 color channels")
    
    def _process_gesture_detection(self, hands_results, pose_landmarks, frame_shape) -> GestureResult:
        """
        Process MediaPipe hands results and classify gestures.
        
        Args:
            hands_results: MediaPipe hands detection results
            pose_landmarks: Optional pose landmarks for shoulder reference
            frame_shape: Shape of the input frame (height, width, channels)
            
        Returns:
            GestureResult with gesture classification
        """
        # Default result (no gesture detected)
        gesture_result = GestureResult(
            gesture_detected=False,
            confidence=0.0
        )
        
        # DEBUG: Check if any hands were detected
        if not hands_results.multi_hand_landmarks:
            print("🚫 No hands detected by MediaPipe")
            return gesture_result
        
        print(f"✋ {len(hands_results.multi_hand_landmarks)} hands detected")
        print(f"📍 Pose landmarks provided: {pose_landmarks is not None}")
        
        # Process each detected hand
        for hand_idx, hand_landmarks in enumerate(hands_results.multi_hand_landmarks):
            
            # Calculate palm normal vector for this hand
            palm_normal = self._calculate_palm_normal(hand_landmarks)
            print(f"🌊 Palm normal vector: {palm_normal}")
            
            # Try to detect "hand up" gesture
            gesture_detected = False
            confidence = 0.0
            
            if pose_landmarks is not None:
                # Use pose landmarks for shoulder reference (preferred)
                print("🎯 Using pose landmarks for shoulder reference")
                gesture_detected = self._gesture_classifier.detect_hand_up_gesture_with_pose(
                    hand_landmarks=hand_landmarks.landmark,
                    pose_landmarks=pose_landmarks,
                    palm_normal_vector=palm_normal
                )
                print(f"🔍 Gesture detected (with pose): {gesture_detected}")
                
                if gesture_detected:
                    confidence = self._gesture_classifier.calculate_gesture_confidence(
                        hand_landmarks=hand_landmarks.landmark,
                        shoulder_reference_y=self._gesture_classifier.calculate_shoulder_reference(pose_landmarks),
                        palm_normal_vector=palm_normal
                    )
                    print(f"📊 Confidence: {confidence}")
            else:
                # Fallback: use estimated shoulder position (less accurate)
                print("📐 Using estimated shoulder position (fallback)")
                estimated_shoulder_y = 0.4  # Approximate shoulder level
                gesture_detected = self._gesture_classifier.detect_hand_up_gesture(
                    hand_landmarks=hand_landmarks.landmark,
                    shoulder_reference_y=estimated_shoulder_y,
                    palm_normal_vector=palm_normal
                )
                print(f"🔍 Gesture detected (fallback): {gesture_detected}")
                
                if gesture_detected:
                    confidence = self._gesture_classifier.calculate_gesture_confidence(
                        hand_landmarks=hand_landmarks.landmark,
                        shoulder_reference_y=estimated_shoulder_y,
                        palm_normal_vector=palm_normal
                    )
                    print(f"📊 Confidence: {confidence}")
            
            # If gesture detected, update result
            if gesture_detected:
                # Determine which hand (left/right)
                hand_label = "unknown"
                if hands_results.multi_handedness:
                    hand_info = hands_results.multi_handedness[hand_idx]
                    hand_label = hand_info.classification[0].label.lower()
                
                # Get hand position
                hand_center = self._get_hand_center(hand_landmarks)
                
                gesture_result = GestureResult(
                    gesture_detected=True,
                    gesture_type="hand_up",
                    confidence=confidence,
                    hand=hand_label,
                    position={
                        'hand_x': hand_center[0],
                        'hand_y': hand_center[1],
                        'shoulder_reference_y': self._gesture_classifier.calculate_shoulder_reference(pose_landmarks) if pose_landmarks else 0.4
                    },
                    palm_facing_camera=palm_normal[2] >= self._gesture_config['palm_facing_confidence'],
                    duration_ms=0.0  # TODO: Implement duration tracking in future
                )
                
                # Return first detected gesture (could extend to support multiple hands)
                break
        
        return gesture_result
    
    def _calculate_palm_normal(self, hand_landmarks) -> np.ndarray:
        """
        Calculate palm normal vector from hand landmarks.
        
        Uses cross product of vectors from wrist to index MCP and wrist to pinky MCP.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            
        Returns:
            3D normal vector of palm surface
        """
        try:
            # MediaPipe hand landmark indices:
            # 0 = WRIST, 5 = INDEX_FINGER_MCP, 17 = PINKY_MCP
            wrist = np.array([hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y, hand_landmarks.landmark[0].z])
            index_mcp = np.array([hand_landmarks.landmark[5].x, hand_landmarks.landmark[5].y, hand_landmarks.landmark[5].z])
            pinky_mcp = np.array([hand_landmarks.landmark[17].x, hand_landmarks.landmark[17].y, hand_landmarks.landmark[17].z])
            
            # Calculate vectors
            v1 = index_mcp - wrist
            v2 = pinky_mcp - wrist
            
            # Calculate normal using cross product
            normal = np.cross(v1, v2)
            
            # Normalize the vector
            norm = np.linalg.norm(normal)
            if norm > 0:
                normal = normal / norm
            
            return normal
            
        except (IndexError, AttributeError):
            # Fallback: return default facing-camera normal
            return np.array([0.0, 0.0, 1.0])
    
    def _get_hand_center(self, hand_landmarks) -> tuple:
        """
        Get the center position of the hand.
        
        Uses middle finger MCP as hand center reference.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            
        Returns:
            Tuple of (x, y) coordinates
        """
        try:
            # MediaPipe hand landmark 9 is MIDDLE_FINGER_MCP
            center_landmark = hand_landmarks.landmark[9]
            return (center_landmark.x, center_landmark.y)
        except (IndexError, AttributeError):
            # Fallback: return center of frame
            return (0.5, 0.5) 