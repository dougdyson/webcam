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
from ..gesture.result import HandDetectionResult
from ..gesture.classification import GestureClassifier, GestureResult

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
    
    def __init__(self, config: Optional[DetectorConfig] = None, backend: str = "legacy"):
        """
        Initialize gesture detector.
        
        Args:
            config: Detector configuration, defaults to DetectorConfig()
            backend: Gesture detection backend ("legacy" or "mediapipe")
        """
        super().__init__(config)
        
        # 🟢 GREEN: Add backend selection
        self._backend = backend
        if backend not in ["legacy", "mediapipe"]:
            from .base import DetectorError
            raise DetectorError(f"Unknown backend: {backend}. Supported backends: 'legacy', 'mediapipe'")
        
        # Backend-specific initialization
        if backend == "mediapipe":
            self._init_mediapipe_backend()
        else:
            self._init_legacy_backend()
    
    def _init_legacy_backend(self) -> None:
        """Initialize legacy gesture detection backend."""
        # MediaPipe components
        self._mp_hands = None
        self._hands_detector = None
        self._initialized = False
        
        # Gesture analysis components
        self._gesture_classifier = None
        
        # Performance optimization settings - SIMPLE like debug script
        self._max_num_hands = 1
        self._frame_skip_count = 0
        self._gesture_detection_interval = 1  # NO SKIPPING - like debug script
        self._last_detection_time = 0
        
        # Configuration for gesture detection - STRICT for proper "STOP" gesture
        self._gesture_config = {
            'shoulder_offset_threshold': 0.12,  # Hand must be 12% above shoulder
            'palm_facing_confidence': 0.8,     # STRICT: Palm must clearly face camera (80% confidence)
        }
    
    def _init_mediapipe_backend(self) -> None:
        """Initialize MediaPipe gesture detection backend."""
        from ..gesture.mediapipe_recognizer import MediaPipeGestureRecognizer, MediaPipeGestureConfig
        
        # Create MediaPipe configuration from DetectorConfig
        mediapipe_config = MediaPipeGestureConfig(
            min_hand_detection_confidence=self.config.min_detection_confidence,
            min_tracking_confidence=self.config.min_tracking_confidence,
            num_hands=2  # Default to 2 hands for MediaPipe
        )
        
        # Initialize MediaPipe recognizer
        self._mediapipe_recognizer = MediaPipeGestureRecognizer(mediapipe_config)
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize MediaPipe hands detection and gesture classification.
        
        Raises:
            DetectorError: If MediaPipe initialization fails
        """
        if self._initialized:
            return  # Idempotent initialization
        
        if self._backend == "mediapipe":
            self._initialize_mediapipe()
        else:
            self._initialize_legacy()
    
    def _initialize_legacy(self) -> None:
        """Initialize legacy backend."""
        try:
            # Initialize MediaPipe hands
            self._mp_hands = mp.solutions.hands
            
            # Create hands detection instance - SIMPLE like debug script
            self._hands_detector = self._mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self._max_num_hands,
                model_complexity=1,  # Good accuracy
                min_detection_confidence=0.5,  # SIMPLE threshold like debug script
                min_tracking_confidence=0.5    # SIMPLE threshold like debug script
            )
            
            # Initialize gesture classifier (no need for separate HandDetector)
            self._gesture_classifier = GestureClassifier(self._gesture_config)
            
            self._initialized = True
            logger.info("Legacy gesture detector initialized successfully")
            
        except Exception as e:
            self._initialized = False
            raise DetectorError(
                "Failed to initialize legacy gesture detector",
                original_error=e
            )
    
    def _initialize_mediapipe(self) -> None:
        """Initialize MediaPipe backend."""
        try:
            # MediaPipe GestureRecognizer is already initialized in constructor
            self._initialized = True
            logger.info("MediaPipe gesture detector initialized successfully")
            
        except Exception as e:
            self._initialized = False
            raise DetectorError(
                "Failed to initialize MediaPipe gesture detector",
                original_error=e
            )
    
    def cleanup(self) -> None:
        """
        Clean up MediaPipe and gesture detection resources.
        
        Logs errors but does not raise exceptions to ensure cleanup always completes.
        """
        try:
            if self._backend == "mediapipe":
                if hasattr(self, '_mediapipe_recognizer'):
                    self._mediapipe_recognizer.cleanup()
                    self._mediapipe_recognizer = None
            else:
                if self._hands_detector is not None:
                    self._hands_detector.close()
                    self._hands_detector = None
                
                self._mp_hands = None
                self._gesture_classifier = None
            
            self._initialized = False
            logger.info(f"{self._backend.capitalize()} gesture detector cleaned up successfully")
            
        except Exception as e:
            # Log error but don't raise - cleanup should always complete
            logger.error(f"Error during {self._backend} gesture detector cleanup: {e}")
            self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """
        Check if detector is properly initialized.
        
        Returns:
            True if detector is ready for detection, False otherwise
        """
        if self._backend == "mediapipe":
            return (self._initialized and 
                    hasattr(self, '_mediapipe_recognizer') and
                    self._mediapipe_recognizer is not None and
                    self._mediapipe_recognizer.is_initialized())
        else:
            return (self._initialized and 
                    self._hands_detector is not None and
                    self._gesture_classifier is not None)
    
    def detect_gestures(self, frame: np.ndarray, pose_landmarks: Optional[Any] = None) -> GestureResult:
        """
        Detect hand gestures in a frame - SIMPLE like debug script.
        
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
        
        if self._backend == "mediapipe":
            return self._detect_gestures_mediapipe(frame, pose_landmarks)
        else:
            return self._detect_gestures_legacy(frame, pose_landmarks)
    
    def _detect_gestures_legacy(self, frame: np.ndarray, pose_landmarks: Optional[Any] = None) -> GestureResult:
        """Legacy gesture detection implementation."""
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect hands using MediaPipe
            hands_results = self._hands_detector.process(rgb_frame)
            
            # Process gesture detection
            return self._process_gesture_detection(hands_results, pose_landmarks, frame.shape)
                
        except Exception as e:
            raise DetectorError(
                "Legacy gesture detection processing failed",
                original_error=e
            )
    
    def _detect_gestures_mediapipe(self, frame: np.ndarray, pose_landmarks: Optional[Any] = None) -> GestureResult:
        """MediaPipe gesture detection implementation."""
        try:
            # Use MediaPipe GestureRecognizer
            mediapipe_result = self._mediapipe_recognizer.recognize_from_image(frame)
            
            if mediapipe_result is None:
                from ..gesture.result import GestureResult as LegacyGestureResult
                return LegacyGestureResult(False, "none", 0.0)
            
            # Convert MediaPipe result to legacy GestureResult format
            return self._convert_mediapipe_result(mediapipe_result)
                
        except Exception as e:
            raise DetectorError(
                "MediaPipe gesture detection processing failed",
                original_error=e
            )
    
    def _convert_mediapipe_result(self, mediapipe_result) -> GestureResult:
        """Convert MediaPipe GestureResult to legacy GestureResult format."""
        from ..gesture.result import GestureResult as LegacyGestureResult
        
        # Convert gesture type
        gesture_detected = mediapipe_result.gesture_type != "None"
        gesture_type = mediapipe_result.gesture_type.lower() if mediapipe_result.gesture_type != "None" else "none"
        
        # Create legacy result
        return LegacyGestureResult(
            gesture_detected=gesture_detected,
            gesture_type=gesture_type,
            confidence=mediapipe_result.confidence,
            hand=mediapipe_result.handedness
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
    
    def get_mediapipe_config(self):
        """
        Get MediaPipe configuration (only available for MediaPipe backend).
        
        Returns:
            MediaPipe configuration object
            
        Raises:
            DetectorError: If backend is not MediaPipe
        """
        if self._backend != "mediapipe":
            raise DetectorError("MediaPipe configuration only available for MediaPipe backend")
        
        return self._mediapipe_recognizer.get_config()
    
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
        
        Uses the new gesture type classification to distinguish between different gestures.
        
        Args:
            hands_results: MediaPipe hands detection results
            pose_landmarks: Optional pose landmarks for shoulder reference
            frame_shape: Shape of the input frame (height, width, channels)
            
        Returns:
            GestureResult with gesture classification
        """
        if not hands_results.multi_hand_landmarks:
            return GestureResult("none", 0.0)
        
        for hand_idx, hand_landmarks_mp in enumerate(hands_results.multi_hand_landmarks):
            hand_label = "unknown"
            if hands_results.multi_handedness and hand_idx < len(hands_results.multi_handedness):
                hand_info = hands_results.multi_handedness[hand_idx]
                hand_label = hand_info.classification[0].label.lower()
            
            # Calculate palm normal vector
            palm_normal = self._calculate_palm_normal(hand_landmarks_mp, hand_label)
            
            # Use new gesture type detection
            gesture_result = self._gesture_classifier.detect_gesture_type(
                hand_landmarks=hand_landmarks_mp.landmark,
                pose_landmarks=pose_landmarks,
                palm_normal_vector=palm_normal
            )
            
            if gesture_result.gesture_detected:
                # Add hand info and palm normal data
                gesture_result.hand = hand_label
                gesture_result.position['palm_z_component'] = palm_normal[2]
                
                return gesture_result  # Return first detected gesture
        
        # No gestures detected
        return GestureResult("none", 0.0)
    
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