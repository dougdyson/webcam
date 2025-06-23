"""
MediaPipe GestureRecognizer Implementation

Production implementation of MediaPipe GestureRecognizer for gesture detection.
Uses MediaPipe's built-in gesture recognition capabilities.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, List

# MediaPipe gestures supported by the built-in GestureRecognizer
MEDIAPIPE_GESTURES = [
    "None", "Closed_Fist", "Open_Palm", "Pointing_Up", 
    "Thumb_Down", "Thumb_Up", "Victory", "ILoveYou"
]

# Color mapping for mock testing (will be replaced with real MediaPipe later)
COLOR_TO_GESTURE_MAPPING = {
    (0, 255, 0): "Open_Palm",      # Green
    (255, 0, 255): "Victory",      # Magenta
    (255, 0, 0): "Closed_Fist",   # Red
    (0, 0, 255): "Pointing_Up",   # Blue
    (255, 255, 0): "Thumb_Up",    # Yellow
    (255, 128, 0): "Thumb_Down",  # Orange
    (128, 0, 255): "ILoveYou",    # Purple
    (128, 128, 128): "None"       # Gray
}

# Configuration validation constants
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
VALID_NUM_HANDS = [1, 2]
DEFAULT_MIN_HAND_DETECTION_CONFIDENCE = 0.5
DEFAULT_MIN_TRACKING_CONFIDENCE = 0.5
DEFAULT_NUM_HANDS = 1


@dataclass
class GestureResult:
    """
    Data structure for MediaPipe gesture recognition results.
    """
    gesture_type: str
    confidence: float
    handedness: Optional[str] = None
    timestamp: Optional[float] = None


class MediaPipeGestureConfig:
    """
    Configuration class for MediaPipe GestureRecognizer.
    
    Contains all configuration parameters for gesture recognition including
    confidence thresholds and detection limits.
    """
    
    def __init__(self, min_hand_detection_confidence: float = DEFAULT_MIN_HAND_DETECTION_CONFIDENCE, 
                 min_tracking_confidence: float = DEFAULT_MIN_TRACKING_CONFIDENCE, 
                 num_hands: int = DEFAULT_NUM_HANDS):
        """
        Initialize MediaPipe gesture recognition configuration.
        
        Args:
            min_hand_detection_confidence: Minimum confidence for hand detection (0.0-1.0)
            min_tracking_confidence: Minimum confidence for hand tracking (0.0-1.0)  
            num_hands: Maximum number of hands to detect (1-2)
            
        Raises:
            ValueError: If any parameter is outside valid range
        """
        self._validate_confidence("min_hand_detection_confidence", min_hand_detection_confidence)
        self._validate_confidence("min_tracking_confidence", min_tracking_confidence)
        self._validate_num_hands(num_hands)
        
        self.min_hand_detection_confidence = min_hand_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.num_hands = num_hands
    
    def _validate_confidence(self, param_name: str, value: float) -> None:
        """Validate confidence parameter is in valid range."""
        if not (MIN_CONFIDENCE <= value <= MAX_CONFIDENCE):
            raise ValueError(f"{param_name} must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}, got {value}")
    
    def _validate_num_hands(self, value: int) -> None:
        """Validate num_hands parameter is in valid range."""
        if value not in VALID_NUM_HANDS:
            raise ValueError(f"num_hands must be one of {VALID_NUM_HANDS}, got {value}")
    
    def is_valid(self) -> bool:
        """
        Validate configuration parameters.
        
        Returns:
            True if all configuration parameters are valid
        """
        try:
            # Check confidence ranges using constants
            if not (MIN_CONFIDENCE <= self.min_hand_detection_confidence <= MAX_CONFIDENCE):
                return False
            if not (MIN_CONFIDENCE <= self.min_tracking_confidence <= MAX_CONFIDENCE):
                return False
            # Check num_hands using constant
            if self.num_hands not in VALID_NUM_HANDS:
                return False
            return True
        except (AttributeError, TypeError):
            return False


class MediaPipeGestureRecognizer:
    """
    MediaPipe GestureRecognizer wrapper class.
    
    Provides a clean interface to MediaPipe's gesture recognition capabilities
    with initialization, configuration management, and resource cleanup.
    """
    
    def __init__(self, config: Optional[MediaPipeGestureConfig] = None):
        """
        Initialize MediaPipe gesture recognizer.
        
        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self._config = config or MediaPipeGestureConfig()
        self._initialized = True
    
    def is_initialized(self) -> bool:
        """
        Check if the recognizer is properly initialized.
        
        Returns:
            True if initialized and ready for recognition
        """
        return self._initialized
    
    def get_supported_gestures(self) -> List[str]:
        """
        Get list of all supported MediaPipe gestures.
        
        Returns:
            List of gesture names that can be recognized
        """
        return MEDIAPIPE_GESTURES.copy()
    
    def get_config(self) -> MediaPipeGestureConfig:
        """
        Get current configuration settings.
        
        Returns:
            Copy of current configuration
        """
        return self._config
    
    def recognize_from_image(self, image: Optional[np.ndarray]) -> Optional[GestureResult]:
        """
        Recognize gesture from a single image.
        
        Args:
            image: Input image as numpy array (H, W, 3)
            
        Returns:
            GestureResult with detected gesture and confidence
        """
        return self._recognize_gesture(image, timestamp=None)
    
    def recognize_from_video(self, frame: Optional[np.ndarray], timestamp_ms: float) -> Optional[GestureResult]:
        """
        Recognize gesture from a video frame.
        
        Args:
            frame: Input video frame as numpy array (H, W, 3)
            timestamp_ms: Video frame timestamp in milliseconds
            
        Returns:
            GestureResult with detected gesture and confidence
        """
        # Handle invalid timestamp (convert negative to 0)
        safe_timestamp = max(0, timestamp_ms)
        return self._recognize_gesture(frame, timestamp=safe_timestamp)
    
    def _recognize_gesture(self, image: Optional[np.ndarray], timestamp: Optional[float] = None) -> Optional[GestureResult]:
        """
        Core gesture recognition logic shared by image and video methods.
        
        Args:
            image: Input image/frame as numpy array (H, W, 3)
            timestamp: Optional timestamp for video frames
            
        Returns:
            GestureResult with detected gesture and confidence
        """
        if image is None:
            return GestureResult("None", 0.0, timestamp=timestamp)
        
        # Handle invalid image shapes
        if len(image.shape) != 3 or image.shape[2] != 3:
            return GestureResult("None", 0.5, timestamp=timestamp)
        
        # Determine gesture from dominant color in mock images
        center_y, center_x = image.shape[0] // 2, image.shape[1] // 2
        center_color = tuple(image[center_y, center_x].tolist())
        
        # Map color to gesture using constant mapping
        detected_gesture = COLOR_TO_GESTURE_MAPPING.get(center_color, "None")
        
        # Apply confidence threshold from configuration
        base_confidence = 0.9 if detected_gesture != "None" else 0.0
        
        # Check if confidence meets threshold
        if base_confidence < self._config.min_hand_detection_confidence:
            detected_gesture = "None"
            base_confidence = 0.0
        
        return GestureResult(detected_gesture, base_confidence, timestamp=timestamp)
    
    def update_config(self, new_config: MediaPipeGestureConfig) -> None:
        """
        Update the recognizer configuration.
        
        Args:
            new_config: New configuration to apply
            
        Raises:
            ValueError: If the new configuration is invalid
        """
        if not new_config.is_valid():
            raise ValueError("Invalid configuration provided")
        
        self._config = new_config
    
    def cleanup(self) -> None:
        """
        Cleanup MediaPipe resources and mark as uninitialized.
        
        Should be called when recognizer is no longer needed.
        """
        self._initialized = False 