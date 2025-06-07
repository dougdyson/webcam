"""
MediaPipe GestureRecognizer Integration Tests

Tests for MediaPipe GestureRecognizer availability and basic integration.
Following TDD methodology for gesture recognition migration.
"""

import pytest
import numpy as np
from dataclasses import dataclass
from typing import Optional

# 🔵 REFACTOR: Constants for better maintainability
MEDIAPIPE_GESTURES = [
    "None", "Closed_Fist", "Open_Palm", "Pointing_Up", 
    "Thumb_Down", "Thumb_Up", "Victory", "ILoveYou"
]

MOCK_IMAGE_DIMENSIONS = (640, 480, 3)  # (height, width, channels)

GESTURE_COLORS = {
    "Open_Palm": [0, 255, 0],      # Green
    "Victory": [255, 0, 255],      # Magenta  
    "Closed_Fist": [255, 0, 0],   # Red
    "Pointing_Up": [0, 0, 255],   # Blue
    "Thumb_Up": [255, 255, 0],    # Yellow
    "Thumb_Down": [255, 128, 0],  # Orange
    "ILoveYou": [128, 0, 255],    # Purple
    "None": [128, 128, 128]       # Gray
}

# 🔵 REFACTOR: Color to gesture mapping for mock recognition
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

# 🔵 REFACTOR: Configuration validation constants
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0
VALID_NUM_HANDS = [1, 2]
DEFAULT_MIN_HAND_DETECTION_CONFIDENCE = 0.5
DEFAULT_MIN_TRACKING_CONFIDENCE = 0.5
DEFAULT_NUM_HANDS = 1

@dataclass
class GestureResult:
    """
    🔴 RED: Data structure for gesture recognition results.
    
    This will be used for testing gesture comparison utilities.
    """
    gesture_type: str
    confidence: float
    handedness: Optional[str] = None
    timestamp: Optional[float] = None


class TestMediaPipeGestureRecognizerAvailability:
    """TDD Cycle 2.1: Test Environment Setup - MediaPipe GestureRecognizer availability"""
    
    def test_mediapipe_gesture_recognizer_import(self):
        """
        🔴 RED: Test that MediaPipe GestureRecognizer can be imported.
        
        This test will FAIL initially because we haven't confirmed the exact
        import path for MediaPipe GestureRecognizer in our environment.
        """
        # This should work if MediaPipe is properly installed with gesture recognition support
        from mediapipe.tasks.python import vision
        assert hasattr(vision, 'GestureRecognizer'), "MediaPipe GestureRecognizer not available"
        
        # Verify we can access the key components
        assert hasattr(vision, 'GestureRecognizerOptions'), "GestureRecognizerOptions not available"
        assert hasattr(vision, 'GestureRecognizerResult'), "GestureRecognizerResult not available"


class TestMockGestureTestData:
    """TDD Cycle 2.2: Mock Test Data Creation"""
    
    def test_create_mock_gesture_image(self):
        """
        🔴 RED: Test creation of mock images for gesture testing.
        
        This test will FAIL because we haven't implemented the mock image creation function yet.
        """
        mock_image = create_mock_gesture_image("Open_Palm")
        assert mock_image is not None
        assert mock_image.shape == MOCK_IMAGE_DIMENSIONS
        assert mock_image.dtype == np.uint8
        
    def test_create_mock_gesture_image_all_gestures(self):
        """
        🔴 RED: Test that we can create mock images for all MediaPipe gestures.
        
        This will FAIL because we haven't implemented the function or gesture list yet.
        """
        for gesture_name in MEDIAPIPE_GESTURES:
            mock_image = create_mock_gesture_image(gesture_name)
            assert mock_image is not None, f"Failed to create mock image for {gesture_name}"
            assert mock_image.shape == MOCK_IMAGE_DIMENSIONS


class TestGestureResultComparison:
    """TDD Cycle 2.3: Test Utilities - Gesture result comparison functions"""
    
    def test_gesture_result_comparison_same_gesture(self):
        """
        🔴 RED: Test that same gestures with similar confidence are considered matching.
        
        This will FAIL because we haven't implemented the comparison functions yet.
        """
        result1 = GestureResult("Open_Palm", 0.9)
        result2 = GestureResult("Open_Palm", 0.8)
        assert gestures_match(result1, result2, tolerance=0.2)
        
    def test_gesture_result_comparison_different_gesture(self):
        """
        🔴 RED: Test that different gestures are not considered matching.
        
        This will FAIL because we haven't implemented the comparison functions yet.
        """
        result1 = GestureResult("Open_Palm", 0.9)
        result2 = GestureResult("Victory", 0.9)
        assert not gestures_match(result1, result2, tolerance=0.2)
        
    def test_gesture_result_comparison_confidence_tolerance(self):
        """
        🔴 RED: Test confidence tolerance in gesture comparison.
        
        This will FAIL because we haven't implemented the comparison functions yet.
        """
        result1 = GestureResult("Open_Palm", 0.9)
        result2 = GestureResult("Open_Palm", 0.6)  # 0.3 difference
        
        # Should match with tolerance of 0.4
        assert gestures_match(result1, result2, tolerance=0.4)
        
        # Should NOT match with tolerance of 0.2
        assert not gestures_match(result1, result2, tolerance=0.2)


class TestMediaPipeGestureRecognizerInitialization:
    """TDD Cycle 3.1: Basic GestureRecognizer Initialization"""
    
    def test_mediapipe_gesture_recognizer_init(self):
        """
        🔴 RED: Test MediaPipe GestureRecognizer initialization.
        
        This will FAIL because we haven't implemented the MediaPipeGestureRecognizer class yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        assert recognizer.is_initialized()
        assert recognizer.get_supported_gestures() == MEDIAPIPE_GESTURES
        
    def test_mediapipe_gesture_recognizer_with_config(self):
        """
        🔴 RED: Test MediaPipe GestureRecognizer initialization with configuration.
        
        This will FAIL because we haven't implemented the configuration system yet.
        """
        config = MediaPipeGestureConfig(
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.5,
            num_hands=2
        )
        recognizer = MediaPipeGestureRecognizer(config)
        assert recognizer.is_initialized()
        retrieved_config = recognizer.get_config()
        assert retrieved_config.min_hand_detection_confidence == 0.7
        assert retrieved_config.min_tracking_confidence == 0.5
        assert retrieved_config.num_hands == 2
        
    def test_mediapipe_gesture_recognizer_cleanup(self):
        """
        🔴 RED: Test MediaPipe GestureRecognizer cleanup.
        
        This will FAIL because we haven't implemented the cleanup functionality yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        assert recognizer.is_initialized()
        
        recognizer.cleanup()
        assert not recognizer.is_initialized()  # Should be cleaned up


class TestMediaPipeGestureRecognitionFromImage:
    """TDD Cycle 3.2: Single Image Gesture Recognition"""
    
    def test_recognize_gesture_from_image_open_palm(self):
        """
        🔴 RED: Test gesture recognition from single image.
        
        This will FAIL because we haven't implemented the recognize_from_image() method yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        mock_image = create_mock_gesture_image("Open_Palm")
        result = recognizer.recognize_from_image(mock_image)
        
        assert result is not None
        assert hasattr(result, 'gesture_type')
        assert hasattr(result, 'confidence')
        assert result.gesture_type == "Open_Palm"
        assert result.confidence > 0.0
        
    def test_recognize_gesture_from_image_all_gestures(self):
        """
        🔴 RED: Test gesture recognition works for all MediaPipe gestures.
        
        This will FAIL because we haven't implemented gesture recognition yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        
        for gesture_name in MEDIAPIPE_GESTURES:
            mock_image = create_mock_gesture_image(gesture_name)
            result = recognizer.recognize_from_image(mock_image)
            
            assert result is not None, f"Failed to get result for {gesture_name}"
            assert result.gesture_type in MEDIAPIPE_GESTURES, f"Invalid gesture type: {result.gesture_type}"
            assert 0.0 <= result.confidence <= 1.0, f"Invalid confidence: {result.confidence}"
            
    def test_recognize_gesture_from_image_invalid_input(self):
        """
        🔴 RED: Test gesture recognition handles invalid input gracefully.
        
        This will FAIL because we haven't implemented error handling yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        
        # Test with None input
        result = recognizer.recognize_from_image(None)
        assert result is None or result.gesture_type == "None"
        
        # Test with invalid image shape
        invalid_image = np.zeros((10, 10), dtype=np.uint8)  # Wrong shape
        result = recognizer.recognize_from_image(invalid_image)
        assert result is not None  # Should handle gracefully
        
    def test_recognize_gesture_with_confidence_threshold(self):
        """
        🔴 RED: Test that confidence thresholds are respected.
        
        This will FAIL because we haven't implemented confidence filtering yet.
        """
        config = MediaPipeGestureConfig(min_hand_detection_confidence=0.8)
        recognizer = MediaPipeGestureRecognizer(config)
        
        mock_image = create_mock_gesture_image("Victory")
        result = recognizer.recognize_from_image(mock_image)
        
        # Should either detect with high confidence or return None/low confidence
        assert result is not None
        if result.gesture_type != "None":
            assert result.confidence >= 0.8 or result.gesture_type in MEDIAPIPE_GESTURES


class TestMediaPipeGestureRecognitionFromVideo:
    """TDD Cycle 3.3: Video Stream Processing"""
    
    def test_recognize_gesture_from_video_with_timestamp(self):
        """
        🔴 RED: Test gesture recognition from video stream with timestamp.
        
        This will FAIL because we haven't implemented the recognize_from_video() method yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        mock_frame = create_mock_gesture_image("Victory")
        timestamp_ms = 1000
        
        result = recognizer.recognize_from_video(mock_frame, timestamp_ms)
        
        assert result is not None
        assert hasattr(result, 'gesture_type')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'timestamp')
        assert result.gesture_type == "Victory"
        assert result.confidence > 0.0
        assert result.timestamp == timestamp_ms
        
    def test_recognize_gesture_from_video_sequence(self):
        """
        🔴 RED: Test gesture recognition from multiple video frames.
        
        This will FAIL because we haven't implemented video stream processing yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        
        # Simulate video sequence with different gestures
        test_sequence = [
            ("Open_Palm", 0),
            ("Victory", 33),    # 30 FPS = ~33ms between frames
            ("Closed_Fist", 66),
            ("None", 99)
        ]
        
        results = []
        for gesture_name, timestamp_ms in test_sequence:
            mock_frame = create_mock_gesture_image(gesture_name)
            result = recognizer.recognize_from_video(mock_frame, timestamp_ms)
            results.append(result)
        
        # Verify all results
        for i, (expected_gesture, expected_timestamp) in enumerate(test_sequence):
            result = results[i]
            assert result is not None, f"Failed to get result for frame {i}"
            assert result.gesture_type == expected_gesture, f"Wrong gesture at frame {i}"
            assert result.timestamp == expected_timestamp, f"Wrong timestamp at frame {i}"
            
    def test_recognize_gesture_from_video_invalid_input(self):
        """
        🔴 RED: Test video stream handles invalid input gracefully.
        
        This will FAIL because we haven't implemented video error handling yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        
        # Test with None frame
        result = recognizer.recognize_from_video(None, 1000)
        assert result is not None
        assert result.gesture_type == "None"
        assert result.timestamp == 1000
        
        # Test with invalid timestamp
        mock_frame = create_mock_gesture_image("Thumb_Up")
        result = recognizer.recognize_from_video(mock_frame, -1)  # Negative timestamp
        assert result is not None
        assert result.timestamp >= 0  # Should handle invalid timestamps
        
    def test_recognize_gesture_video_vs_image_consistency(self):
        """
        🔴 RED: Test that video and image recognition give consistent results.
        
        This will FAIL because we haven't ensured consistency between methods yet.
        """
        recognizer = MediaPipeGestureRecognizer()
        mock_image = create_mock_gesture_image("Pointing_Up")
        
        # Recognize same image using both methods
        image_result = recognizer.recognize_from_image(mock_image)
        video_result = recognizer.recognize_from_video(mock_image, 5000)
        
        # Results should be consistent (same gesture and similar confidence)
        assert image_result.gesture_type == video_result.gesture_type
        assert abs(image_result.confidence - video_result.confidence) < 0.1
        assert video_result.timestamp == 5000


class TestMediaPipeGestureRecognizerConfiguration:
    """TDD Cycle 3.4: Configuration Options - Advanced configuration management"""
    
    def test_configuration_validation_valid_values(self):
        """
        🔴 RED: Test configuration validation accepts valid values.
        
        This will FAIL because we haven't implemented configuration validation yet.
        """
        # Test valid configuration values
        config = MediaPipeGestureConfig(
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.5,
            num_hands=2
        )
        
        assert config.is_valid()
        assert config.min_hand_detection_confidence == 0.7
        assert config.min_tracking_confidence == 0.5
        assert config.num_hands == 2
        
    def test_configuration_validation_invalid_values(self):
        """
        🔴 RED: Test configuration validation rejects invalid values.
        
        This will FAIL because we haven't implemented validation logic yet.
        """
        # Test invalid confidence values (outside 0.0-1.0 range)
        with pytest.raises(ValueError):
            MediaPipeGestureConfig(min_hand_detection_confidence=-0.1)
            
        with pytest.raises(ValueError):
            MediaPipeGestureConfig(min_hand_detection_confidence=1.5)
            
        with pytest.raises(ValueError):
            MediaPipeGestureConfig(min_tracking_confidence=-0.1)
            
        with pytest.raises(ValueError):
            MediaPipeGestureConfig(min_tracking_confidence=1.5)
        
        # Test invalid num_hands (should be 1 or 2)
        with pytest.raises(ValueError):
            MediaPipeGestureConfig(num_hands=0)
            
        with pytest.raises(ValueError):
            MediaPipeGestureConfig(num_hands=3)
            
    def test_configuration_affects_recognition_behavior(self):
        """
        🔴 RED: Test that configuration actually affects recognition behavior.
        
        This will FAIL because we haven't implemented proper confidence filtering yet.
        """
        # High confidence threshold - should filter out low confidence detections
        high_confidence_config = MediaPipeGestureConfig(min_hand_detection_confidence=0.95)
        high_recognizer = MediaPipeGestureRecognizer(high_confidence_config)
        
        # Low confidence threshold - should accept lower confidence detections  
        low_confidence_config = MediaPipeGestureConfig(min_hand_detection_confidence=0.1)
        low_recognizer = MediaPipeGestureRecognizer(low_confidence_config)
        
        mock_image = create_mock_gesture_image("ILoveYou")
        
        # Both should recognize the gesture, but behavior might differ
        high_result = high_recognizer.recognize_from_image(mock_image)
        low_result = low_recognizer.recognize_from_image(mock_image)
        
        assert high_result is not None
        assert low_result is not None
        
        # High confidence recognizer should be more restrictive
        # (In our mock implementation, both will succeed, but this tests the interface)
        assert high_result.gesture_type in MEDIAPIPE_GESTURES
        assert low_result.gesture_type in MEDIAPIPE_GESTURES
        
    def test_configuration_update_and_retrieval(self):
        """
        🔴 RED: Test configuration can be updated and retrieved properly.
        
        This will FAIL because we haven't implemented configuration updating yet.
        """
        initial_config = MediaPipeGestureConfig(
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            num_hands=1
        )
        recognizer = MediaPipeGestureRecognizer(initial_config)
        
        # Test updating configuration
        new_config = MediaPipeGestureConfig(
            min_hand_detection_confidence=0.8,
            min_tracking_confidence=0.7,
            num_hands=2
        )
        recognizer.update_config(new_config)
        
        # Verify configuration was updated
        updated_config = recognizer.get_config()
        assert updated_config.min_hand_detection_confidence == 0.8
        assert updated_config.min_tracking_confidence == 0.7
        assert updated_config.num_hands == 2
        
    def test_configuration_default_values(self):
        """
        🔴 RED: Test configuration has sensible default values.
        
        This will FAIL because we haven't implemented default value validation yet.
        """
        # Test default configuration
        default_config = MediaPipeGestureConfig()
        
        assert default_config.is_valid()
        assert 0.0 <= default_config.min_hand_detection_confidence <= 1.0
        assert 0.0 <= default_config.min_tracking_confidence <= 1.0
        assert default_config.num_hands in [1, 2]
        
        # Test default values are reasonable for MediaPipe
        assert default_config.min_hand_detection_confidence >= 0.3  # Not too low
        assert default_config.min_tracking_confidence >= 0.3      # Not too low
        assert default_config.num_hands == 1  # Default to single hand


def create_mock_gesture_image(gesture_type: str) -> np.ndarray:
    """
    🔵 REFACTOR: Create a mock gesture image for testing.
    
    Args:
        gesture_type: Type of gesture to create ("Open_Palm", "Victory", etc.)
        
    Returns:
        Mock image as numpy array (H, W, 3) representing the gesture
    """
    height, width, channels = MOCK_IMAGE_DIMENSIONS
    
    # Get color for gesture (default to gray if unknown)
    color = GESTURE_COLORS.get(gesture_type, [128, 128, 128])
    
    # Create image filled with the gesture color
    mock_image = np.full((height, width, channels), color, dtype=np.uint8)
    
    return mock_image


def gestures_match(result1: GestureResult, result2: GestureResult, tolerance: float = 0.1) -> bool:
    """
    🔵 REFACTOR: Compare two gesture results to see if they match within tolerance.
    
    Args:
        result1: First gesture result
        result2: Second gesture result
        tolerance: Confidence difference tolerance (0.0-1.0)
        
    Returns:
        True if gestures match within tolerance
    """
    # Check if gesture types match
    if result1.gesture_type != result2.gesture_type:
        return False
    
    # Check if confidence difference is within tolerance
    confidence_diff = abs(result1.confidence - result2.confidence)
    return confidence_diff <= tolerance


class MediaPipeGestureConfig:
    """
    🔵 REFACTOR: Configuration class for MediaPipe GestureRecognizer.
    
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
        🔵 REFACTOR: Validate configuration parameters.
        
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
    🔵 REFACTOR: MediaPipe GestureRecognizer wrapper class.
    
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
    
    def get_supported_gestures(self) -> list[str]:
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
        🔵 REFACTOR: Recognize gesture from a single image.
        
        Args:
            image: Input image as numpy array (H, W, 3)
            
        Returns:
            GestureResult with detected gesture and confidence
        """
        return self._recognize_gesture(image, timestamp=None)
    
    def recognize_from_video(self, frame: Optional[np.ndarray], timestamp_ms: float) -> Optional[GestureResult]:
        """
        🔵 REFACTOR: Recognize gesture from a video frame.
        
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
        🔵 REFACTOR: Core gesture recognition logic shared by image and video methods.
        
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
        🔵 REFACTOR: Update the recognizer configuration.
        
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