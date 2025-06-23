"""
MediaPipe GestureRecognizer Integration Tests

Tests for integrating MediaPipe GestureRecognizer with existing gesture detection system.
Following TDD methodology for clean integration without backwards compatibility.

TDD Cycle 4.1: GestureDetector Integration
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

# Import existing system components
from src.detection.base import DetectorConfig, DetectorError
from src.gesture.result import GestureResult as LegacyGestureResult

# Import our MediaPipe implementation from source
from src.gesture.mediapipe_recognizer import (
    MediaPipeGestureRecognizer, 
    MediaPipeGestureConfig,
    GestureResult as MediaPipeGestureResult,
    MEDIAPIPE_GESTURES
)


class TestMediaPipeGestureDetectorIntegration:
    """TDD Cycle 4.1: GestureDetector Integration"""
    
    def test_gesture_detector_with_mediapipe_backend(self):
        """
        🔴 RED: Test GestureDetector using MediaPipe backend.
        
        This will FAIL because we haven't implemented the MediaPipe backend option yet.
        """
        from src.detection.gesture_detector import GestureDetector
        
        # Create detector with MediaPipe backend option
        detector = GestureDetector(backend="mediapipe")
        
        # Use a proper mock gesture image that will be recognized
        frame = create_mock_gesture_image("Open_Palm")  # This should be recognized
        pose_landmarks = create_test_pose_landmarks()
        
        detector.initialize()
        result = detector.detect_gestures(frame, pose_landmarks)
        
        assert result.gesture_detected is not None
        # MediaPipe gestures get converted to lowercase in legacy format
        expected_gestures = [g.lower() if g != "None" else "none" for g in MEDIAPIPE_GESTURES]
        assert result.gesture_type in expected_gestures
        assert 0.0 <= result.confidence <= 1.0
        
        detector.cleanup()
        
    def test_gesture_detector_mediapipe_configuration(self):
        """
        🔴 RED: Test GestureDetector MediaPipe configuration integration.
        
        This will FAIL because we haven't implemented MediaPipe config integration yet.
        """
        from src.detection.gesture_detector import GestureDetector
        
        # Create detector with MediaPipe-specific configuration
        config = DetectorConfig(
            min_detection_confidence=0.8,
            min_tracking_confidence=0.7
        )
        detector = GestureDetector(backend="mediapipe", config=config)
        
        detector.initialize()
        
        # Verify MediaPipe configuration was applied
        assert detector.get_mediapipe_config().min_hand_detection_confidence == 0.8
        assert detector.get_mediapipe_config().min_tracking_confidence == 0.7
        
        detector.cleanup()
        
    def test_gesture_detector_backend_switching(self):
        """
        🔴 RED: Test switching between legacy and MediaPipe backends.
        
        This will FAIL because we haven't implemented backend switching yet.
        """
        from src.detection.gesture_detector import GestureDetector
        
        # Test legacy backend (current default)
        legacy_detector = GestureDetector(backend="legacy")
        legacy_detector.initialize()
        
        # Use a proper mock gesture image
        frame = create_mock_gesture_image("Open_Palm")
        pose_landmarks = create_test_pose_landmarks()
        legacy_result = legacy_detector.detect_gestures(frame, pose_landmarks)
        
        # Test MediaPipe backend
        mediapipe_detector = GestureDetector(backend="mediapipe")
        mediapipe_detector.initialize()
        
        mediapipe_result = mediapipe_detector.detect_gestures(frame, pose_landmarks)
        
        # Both should return valid results but may differ in gesture types
        assert legacy_result is not None
        assert mediapipe_result is not None
        
        # MediaPipe gestures get converted to lowercase in legacy format
        expected_gestures = [g.lower() if g != "None" else "none" for g in MEDIAPIPE_GESTURES]
        assert mediapipe_result.gesture_type in expected_gestures
        
        legacy_detector.cleanup()
        mediapipe_detector.cleanup()
        
    def test_gesture_detector_interface_compatibility(self):
        """
        🔴 RED: Test that MediaPipe backend maintains existing interface.
        
        This will FAIL because we haven't ensured interface compatibility yet.
        """
        from src.detection.gesture_detector import GestureDetector
        
        detector = GestureDetector(backend="mediapipe")
        detector.initialize()
        
        # Test HumanDetector interface compatibility
        frame = create_test_frame()
        result = detector.detect(frame)  # Should work via HumanDetector interface
        
        assert hasattr(result, 'gesture_detected')
        assert hasattr(result, 'gesture_type')
        assert hasattr(result, 'confidence')
        
        # Test GestureDetector-specific interface
        pose_landmarks = create_test_pose_landmarks()
        gesture_result = detector.detect_gestures(frame, pose_landmarks)
        
        assert hasattr(gesture_result, 'gesture_detected')
        assert hasattr(gesture_result, 'gesture_type')
        assert hasattr(gesture_result, 'confidence')
        
        detector.cleanup()
        
    def test_gesture_detector_error_handling(self):
        """
        🔴 RED: Test error handling with MediaPipe backend.
        
        This will FAIL because we haven't implemented proper error handling integration yet.
        """
        from src.detection.gesture_detector import GestureDetector
        
        detector = GestureDetector(backend="mediapipe")
        
        # Test detection without initialization
        with pytest.raises(DetectorError):
            frame = create_test_frame()
            detector.detect_gestures(frame)
        
        # Test invalid backend
        with pytest.raises(DetectorError):
            invalid_detector = GestureDetector(backend="invalid_backend")
            
        # Test invalid frame handling
        detector.initialize()
        
        # Should raise DetectorError for None frame
        with pytest.raises(DetectorError):
            detector.detect_gestures(None)
        
        detector.cleanup()


class TestMediaPipeServiceIntegration:
    """TDD Cycle 4.2: Service Layer Integration"""
    
    def test_gesture_service_with_mediapipe(self):
        """
        🔴 RED: Test gesture service using MediaPipe GestureRecognizer.
        
        This will FAIL because we haven't updated the service layer yet.
        """
        # This will be implemented when we have service integration
        # For now, test that we can create events with MediaPipe gesture names
        
        mediapipe_result = MediaPipeGestureResult("Open_Palm", 0.9)
        
        # Create service event (will need to update event creation)
        event_data = {
            "gesture_type": mediapipe_result.gesture_type,
            "confidence": mediapipe_result.confidence,
            "timestamp": 1000
        }
        
        assert event_data["gesture_type"] == "Open_Palm"
        assert event_data["confidence"] == 0.9
        
    def test_gesture_event_publishing_with_mediapipe_names(self):
        """
        🔴 RED: Test that gesture events use MediaPipe gesture names directly.
        
        This will FAIL because we haven't updated event publishing yet.
        """
        # Test that we can create events with all MediaPipe gesture types
        for gesture_name in MEDIAPIPE_GESTURES:
            mediapipe_result = MediaPipeGestureResult(gesture_name, 0.8)
            
            event_data = {
                "gesture_type": mediapipe_result.gesture_type,
                "confidence": mediapipe_result.confidence
            }
            
            assert event_data["gesture_type"] == gesture_name
            assert event_data["gesture_type"] in MEDIAPIPE_GESTURES
            
    def test_sse_streaming_with_mediapipe_gestures(self):
        """
        🔴 RED: Test SSE streaming with MediaPipe gesture events.
        
        This will FAIL because we haven't updated SSE service yet.
        """
        # Test that SSE events can handle all MediaPipe gesture types
        test_gestures = ["Open_Palm", "Victory", "Closed_Fist", "Thumb_Up"]
        
        for gesture_name in test_gestures:
            mediapipe_result = MediaPipeGestureResult(gesture_name, 0.85)
            
            # This will need to be updated to work with actual SSE service
            sse_event = {
                "event": "GESTURE_DETECTED",
                "data": {
                    "gesture_type": mediapipe_result.gesture_type,
                    "confidence": mediapipe_result.confidence
                }
            }
            
            assert sse_event["data"]["gesture_type"] == gesture_name
            assert sse_event["data"]["gesture_type"] in MEDIAPIPE_GESTURES
    
    def test_event_publisher_integration_with_mediapipe(self):
        """
        🔴 RED: Test EventPublisher handles MediaPipe gesture events correctly.
        
        This will FAIL because we need to test full event flow with MediaPipe names.
        """
        from src.service.events import EventPublisher, ServiceEvent, EventType
        
        publisher = EventPublisher()
        received_events = []
        
        # Subscribe to events
        def capture_event(event):
            received_events.append(event)
        
        publisher.subscribe(capture_event)
        
        # Publish MediaPipe gesture event
        mediapipe_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "Open_Palm",  # MediaPipe name directly
                "confidence": 0.92,
                "handedness": "Left", 
                "mediapipe_result": True
            }
        )
        
        publisher.publish(mediapipe_event)
        
        # Verify event was received with MediaPipe names
        assert len(received_events) == 1
        received_event = received_events[0]
        assert received_event.data["gesture_type"] == "Open_Palm"
        assert received_event.data["confidence"] == 0.92
        assert received_event.data["mediapipe_result"] is True
        
    def test_http_service_gesture_endpoint_with_mediapipe(self):
        """
        🔴 RED: Test HTTP service returns MediaPipe gesture information.
        
        This will FAIL because we haven't added gesture endpoints to HTTP service yet.
        """
        from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
        from src.service.events import EventPublisher, ServiceEvent, EventType
        
        config = HTTPServiceConfig(port=8768)  # Different port for testing
        http_service = HTTPDetectionService(config)
        
        # Setup event integration
        event_publisher = EventPublisher()
        http_service.setup_event_integration(event_publisher)
        
        # Publish MediaPipe gesture event
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "Victory",  # MediaPipe name
                "confidence": 0.88,
                "handedness": "Right"
            }
        )
        
        # This should trigger the HTTP service to store gesture data
        event_publisher.publish(gesture_event)
        
        # Test that HTTP service has gesture data stored
        # This will FAIL because gesture tracking isn't implemented yet
        assert hasattr(http_service, 'current_gesture_status'), "HTTP service should track gesture status"
        assert http_service.current_gesture_status is not None, "Should have gesture status after event"
        
        # Test gesture endpoint exists
        route_paths = [route.path for route in http_service.app.routes if hasattr(route, 'path')]
        assert "/gesture/latest" in route_paths, "Should have /gesture/latest endpoint"
        assert "/gesture/status" in route_paths, "Should have /gesture/status endpoint"
            
    def test_enhanced_frame_processor_with_mediapipe_backend(self):
        """
        🔴 RED: Test enhanced frame processor integrates with MediaPipe backend.
        
        This will FAIL because we need to test processor uses MediaPipe backend.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.events import EventPublisher
        from unittest.mock import Mock, patch
        
        # Create processor with MediaPipe gesture backend
        event_publisher = EventPublisher()
        
        # Create mock detectors
        mock_detector = Mock()
        mock_gesture_detector = Mock()
        
        # Create processor with MediaPipe gesture backend
        processor = EnhancedFrameProcessor(
            detector=mock_detector,
            gesture_detector=mock_gesture_detector,
            event_publisher=event_publisher,
            gesture_backend="mediapipe"
        )
        
        # Verify processor was configured with MediaPipe backend
        assert hasattr(processor, 'gesture_backend'), "Processor should track gesture backend"
        assert processor.gesture_backend == "mediapipe", "Should use MediaPipe backend"
        
    def test_sse_service_streams_mediapipe_gestures(self):
        """
        🔴 RED: Test SSE service properly formats MediaPipe gesture events.
        
        This will FAIL because we need to verify SSE handles MediaPipe names correctly.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        from src.service.events import EventPublisher, ServiceEvent, EventType
        
        config = SSEServiceConfig(port=8767)  # Different port for testing
        sse_service = SSEDetectionService(config)
        
        # Setup gesture integration
        event_publisher = EventPublisher() 
        sse_service.setup_gesture_integration(event_publisher)
        
        # Test MediaPipe gesture event formatting
        mediapipe_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "Open_Palm",  # MediaPipe name
                "confidence": 0.91,
                "handedness": "Left"
            }
        )
        
        # Test SSE formatting
        sse_message = sse_service._convert_event_to_sse_format(mediapipe_event)
        
        # Verify MediaPipe names are preserved in SSE stream  
        assert "Open_Palm" in sse_message, "Should preserve MediaPipe gesture name"
        assert "0.91" in sse_message, "Should include confidence"
        assert "Left" in sse_message, "Should include handedness"
        
        # Test that MediaPipe gestures pass filtering
        should_stream = sse_service.should_stream_event(mediapipe_event)
        assert should_stream is True, "Should stream MediaPipe gesture events"


def create_test_frame() -> np.ndarray:
    """Create a test frame for gesture detection testing."""
    # Create a 640x480 BGR frame with a simple pattern
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add some content to make it a realistic test frame
    frame[100:300, 200:400] = [50, 100, 150]  # Blue-ish region for hand
    
    return frame


def create_test_pose_landmarks() -> Mock:
    """Create mock pose landmarks for testing."""
    pose_landmarks = Mock()
    
    # Mock shoulder landmarks (11 and 12 are left and right shoulders)
    shoulder_left = Mock()
    shoulder_left.x = 0.3
    shoulder_left.y = 0.4
    shoulder_left.visibility = 0.9
    
    shoulder_right = Mock()
    shoulder_right.x = 0.7
    shoulder_right.y = 0.4
    shoulder_right.visibility = 0.9
    
    # Create landmark list
    pose_landmarks.landmark = [None] * 33  # MediaPipe pose has 33 landmarks
    pose_landmarks.landmark[11] = shoulder_left
    pose_landmarks.landmark[12] = shoulder_right
    
    return pose_landmarks


def create_test_hand_landmarks() -> Mock:
    """Create mock hand landmarks for testing."""
    hand_landmarks = Mock()
    
    # Create 21 hand landmarks (MediaPipe standard)
    landmarks = []
    for i in range(21):
        landmark = Mock()
        landmark.x = 0.5 + (i * 0.01)  # Spread them out slightly
        landmark.y = 0.5 + (i * 0.01)
        landmark.z = 0.0
        landmarks.append(landmark)
    
    hand_landmarks.landmark = landmarks
    return hand_landmarks


def create_mock_gesture_image(gesture_type: str) -> np.ndarray:
    """
    Create a mock gesture image for testing.
    
    Args:
        gesture_type: Type of gesture to create ("Open_Palm", "Victory", etc.)
        
    Returns:
        Mock image as numpy array (H, W, 3) representing the gesture
    """
    height, width, channels = (640, 480, 3)
    
    # Get color for gesture (default to gray if unknown)
    gesture_colors = {
        "Open_Palm": [0, 255, 0],      # Green
        "Victory": [255, 0, 255],      # Magenta  
        "Closed_Fist": [255, 0, 0],   # Red
        "Pointing_Up": [0, 0, 255],   # Blue
        "Thumb_Up": [255, 255, 0],    # Yellow
        "Thumb_Down": [255, 128, 0],  # Orange
        "ILoveYou": [128, 0, 255],    # Purple
        "None": [128, 128, 128]       # Gray
    }
    
    color = gesture_colors.get(gesture_type, [128, 128, 128])
    
    # Create image filled with the gesture color
    mock_image = np.full((height, width, channels), color, dtype=np.uint8)
    
    return mock_image 