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
        
        # Performance optimization settings - REMOVED for maximum speed
        self._max_num_hands = 1  # Still efficient - detect one hand
        self._frame_skip_count = 0
        self._gesture_detection_interval = 1  # EVERY FRAME - no skipping like debug script
        self._last_detection_time = 0
        
        # Configuration for gesture detection - MUCH MORE SENSITIVE
        self._gesture_config = {
            'shoulder_offset_threshold': 0.12,  # Hand must be 12% above shoulder
            'palm_facing_confidence': 0.1,     # VERY LOW - much easier palm detection
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
            
            # Create hands detection instance with OPTIMIZED SETTINGS for EASIER DETECTION
            self._hands_detector = self._mp_hands.Hands(
                static_image_mode=False,  # Dynamic tracking for video
                max_num_hands=self._max_num_hands,
                model_complexity=0,  # REDUCED from 1 - much faster, good enough accuracy
                min_detection_confidence=0.1,  # VERY LOW - much easier/faster detection
                min_tracking_confidence=0.1    # VERY LOW - much easier tracking
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
        Detect hand gestures in a frame - NO THROTTLING for maximum speed like debug script.
        
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
        
        # REMOVED: Frame skipping for maximum speed (like debug script)
        # Process EVERY frame for best responsiveness
        
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
        
        SIMPLIFIED: Just detect open palm facing camera (no shoulder reference needed).
        
        Args:
            hands_results: MediaPipe hands detection results
            pose_landmarks: Optional pose landmarks (not used in simplified approach)
            frame_shape: Shape of the input frame (height, width, channels)
            
        Returns:
            GestureResult with gesture classification
        """
        gesture_result = GestureResult(gesture_detected=False, confidence=0.0)
        
        if not hands_results.multi_hand_landmarks:
            return gesture_result
        
        for hand_idx, hand_landmarks_mp in enumerate(hands_results.multi_hand_landmarks):
            hand_label = "unknown"
            if hands_results.multi_handedness and hand_idx < len(hands_results.multi_handedness):
                hand_info = hands_results.multi_handedness[hand_idx]
                hand_label = hand_info.classification[0].label.lower()
            
            # Calculate palm normal vector
            palm_normal = self._calculate_palm_normal(hand_landmarks_mp, hand_label)
            
            # SIMPLIFIED: Just check if palm is facing camera (no shoulder reference)
            gesture_detected_for_this_hand = self._gesture_classifier.detect_open_palm_gesture(
                hand_landmarks=hand_landmarks_mp.landmark,
                palm_normal_vector=palm_normal
            )
            
            if gesture_detected_for_this_hand:
                # Calculate confidence based purely on palm orientation
                confidence_for_this_hand = self._gesture_classifier.calculate_open_palm_confidence(
                    hand_landmarks=hand_landmarks_mp.landmark,
                    palm_normal_vector=palm_normal
                )
                
                hand_center = self._get_hand_center(hand_landmarks_mp)
                gesture_result = GestureResult(
                    gesture_detected=True,
                    gesture_type="hand_up",  # Keep original name for API compatibility
                    confidence=confidence_for_this_hand,
                    hand=hand_label,
                    position={
                        'hand_x': hand_center[0],
                        'hand_y': hand_center[1],
                        'palm_z_component': palm_normal[2]  # Show palm orientation instead of shoulder ref
                    },
                    palm_facing_camera=palm_normal[2] >= self._gesture_config['palm_facing_confidence']
                )
                break # Process first detected gesture
        
        return gesture_result
    
    def _calculate_palm_normal(self, hand_landmarks, hand_label: str = "unknown") -> np.ndarray:
        """
        Calculate palm normal vector from hand landmarks.
        Uses cross product of vectors from wrist to index MCP and wrist to pinky MCP.
        If hand_label is 'left', the normal is inverted.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            hand_label: The detected hand label ('left', 'right', or 'unknown').
            
        Returns:
            3D normal vector of palm surface
        """
        try:
            wrist = np.array([hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y, hand_landmarks.landmark[0].z])
            index_mcp = np.array([hand_landmarks.landmark[5].x, hand_landmarks.landmark[5].y, hand_landmarks.landmark[5].z])
            pinky_mcp = np.array([hand_landmarks.landmark[17].x, hand_landmarks.landmark[17].y, hand_landmarks.landmark[17].z])
            
            v1 = index_mcp - wrist
            v2 = pinky_mcp - wrist
            normal = np.cross(v1, v2)
            
            norm_val = np.linalg.norm(normal)
            if norm_val > 0:
                normal = normal / norm_val
            
            # Invert normal for 'left' hand as its coordinate system seems to be mirrored
            if hand_label == 'left':
                normal = -normal
                # print(f"[DEBUG _calculate_palm_normal] Inverted normal for left hand. New Z: {normal[2]}")
            
            return normal
            
        except (IndexError, AttributeError):
            return np.array([0.0, 0.0, 1.0]) # Default facing-camera normal
    
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