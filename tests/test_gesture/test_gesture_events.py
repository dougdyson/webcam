"""
Test gesture event integration.

Testing gesture event types, EventPublisher integration, gesture debouncing,
and event data structures for real-time gesture streaming.
Following TDD methodology: Red → Green → Refactor.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

class TestGestureEventIntegration:
    """Test gesture event system integration with EventPublisher and event types."""
    
    def test_gesture_detected_event_type_creation(self):
        """
        RED TEST: Test GESTURE_DETECTED event type exists in EventType enum.
        
        Should add new gesture event types to existing service event system.
        """
        from src.service.events import EventType
        
        # Test that new gesture event types exist
        assert hasattr(EventType, 'GESTURE_DETECTED'), "Should have GESTURE_DETECTED event type"
        assert hasattr(EventType, 'GESTURE_LOST'), "Should have GESTURE_LOST event type"
        assert hasattr(EventType, 'GESTURE_CONFIDENCE_UPDATE'), "Should have GESTURE_CONFIDENCE_UPDATE event type"
        
        # Test event type values
        assert EventType.GESTURE_DETECTED.value == "gesture_detected", "Should have correct value"
        assert EventType.GESTURE_LOST.value == "gesture_lost", "Should have correct value"
        assert EventType.GESTURE_CONFIDENCE_UPDATE.value == "gesture_confidence_update", "Should have correct value"
    
    def test_gesture_event_data_structure_creation(self):
        """
        RED TEST: Test gesture event data structure format.
        
        Should create ServiceEvent with proper gesture data structure.
        """
        from src.service.events import ServiceEvent, EventType
        
        # Test gesture detected event creation
        gesture_data = {
            "gesture_type": "hand_up",
            "confidence": 0.85,
            "hand": "right",
            "position": {
                "hand_x": 0.65,
                "hand_y": 0.25,
                "shoulder_reference_y": 0.45
            },
            "palm_facing_camera": True,
            "duration_ms": 1250.0
        }
        
        event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data=gesture_data
        )
        
        assert event.event_type == EventType.GESTURE_DETECTED, "Should have correct event type"
        assert event.data["gesture_type"] == "hand_up", "Should have gesture type"
        assert event.data["confidence"] == 0.85, "Should have confidence score"
        assert event.data["duration_ms"] == 1250.0, "Should have duration tracking"
    
    def test_gesture_result_to_event_conversion(self):
        """
        RED TEST: Test conversion from GestureResult to ServiceEvent.
        
        Should provide method to convert GestureResult to ServiceEvent for publishing.
        """
        from src.gesture.result import GestureResult
        from src.service.events import ServiceEvent, EventType
        
        # Create test GestureResult
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.78,
            hand="left",
            position={"hand_x": 0.4, "hand_y": 0.3, "shoulder_reference_y": 0.5},
            palm_facing_camera=True,
            duration_ms=800.0
        )
        
        # Test conversion method
        event = gesture_result.to_service_event()
        
        assert isinstance(event, ServiceEvent), "Should return ServiceEvent"
        assert event.event_type == EventType.GESTURE_DETECTED, "Should be GESTURE_DETECTED event"
        assert event.data["gesture_type"] == "hand_up", "Should preserve gesture type"
        assert event.data["confidence"] == 0.78, "Should preserve confidence"
        assert event.data["hand"] == "left", "Should preserve hand information"
    
    def test_gesture_lost_event_creation(self):
        """
        RED TEST: Test gesture lost event when hand goes down.
        
        Should create GESTURE_LOST event when gesture is no longer detected.
        """
        from src.service.events import ServiceEvent, EventType
        
        # Test gesture lost event
        lost_data = {
            "previous_gesture_type": "hand_up",
            "last_confidence": 0.65,
            "gesture_duration_ms": 2500.0,
            "reason": "hand_below_shoulder"
        }
        
        event = ServiceEvent(
            event_type=EventType.GESTURE_LOST,
            data=lost_data
        )
        
        assert event.event_type == EventType.GESTURE_LOST, "Should be GESTURE_LOST event"
        assert event.data["previous_gesture_type"] == "hand_up", "Should track previous gesture"
        assert event.data["gesture_duration_ms"] == 2500.0, "Should track total duration"
        assert event.data["reason"] == "hand_below_shoulder", "Should include reason for loss"
    
    def test_eventpublisher_gesture_subscription(self):
        """
        RED TEST: Test EventPublisher subscription to gesture events.
        
        Should allow subscribers to listen specifically to gesture events.
        """
        from src.service.events import EventPublisher, EventType, ServiceEvent
        
        publisher = EventPublisher()
        gesture_events_received = []
        
        def gesture_event_handler(event):
            """Handler that only processes gesture events."""
            if event.event_type in [EventType.GESTURE_DETECTED, EventType.GESTURE_LOST]:
                gesture_events_received.append(event)
        
        # Subscribe to events
        publisher.subscribe(gesture_event_handler)
        
        # Publish a gesture event
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={"gesture_type": "hand_up", "confidence": 0.9}
        )
        publisher.publish(gesture_event)
        
        # Publish a non-gesture event
        presence_event = ServiceEvent(
            event_type=EventType.PRESENCE_CHANGED,
            data={"human_present": True}
        )
        publisher.publish(presence_event)
        
        # Should only receive gesture events
        assert len(gesture_events_received) == 1, "Should receive gesture event"
        assert gesture_events_received[0].event_type == EventType.GESTURE_DETECTED, "Should be gesture event"
    
    def test_gesture_debouncing_mechanism(self):
        """
        RED TEST: Test gesture debouncing to prevent false triggers.
        
        Should implement debouncing logic to smooth gesture detection.
        """
        from src.gesture.debouncing import GestureDebouncer
        
        # Test debouncer creation
        debouncer = GestureDebouncer(
            debounce_frames=3,  # Require 3 consecutive frames
            confidence_threshold=0.7
        )
        
        # Test that gesture requires multiple confirmations
        assert not debouncer.is_gesture_stable("hand_up", 0.8), "Should not be stable after 1 frame"
        assert not debouncer.update_gesture_state("hand_up", 0.8), "Should not trigger after 1 frame"
        assert not debouncer.update_gesture_state("hand_up", 0.85), "Should not trigger after 2 frames"
        assert debouncer.update_gesture_state("hand_up", 0.9), "Should trigger after 3 frames"
    
    def test_gesture_duration_tracking(self):
        """
        RED TEST: Test gesture duration tracking for events.
        
        Should track how long a gesture has been active.
        """
        from src.gesture.tracking import GestureDurationTracker
        
        tracker = GestureDurationTracker()
        
        # Start tracking a gesture
        start_time = datetime.now()
        tracker.start_gesture("hand_up", start_time)
        
        # Check duration after some time
        later_time = start_time + timedelta(milliseconds=1500)
        duration = tracker.get_gesture_duration("hand_up", later_time)
        
        assert duration >= 1500.0, "Should track duration correctly"
        assert tracker.is_gesture_active("hand_up"), "Should show gesture as active"
        
        # Stop tracking
        tracker.stop_gesture("hand_up", later_time)
        assert not tracker.is_gesture_active("hand_up"), "Should show gesture as inactive"
    
    def test_gesture_confidence_update_events(self):
        """
        RED TEST: Test gesture confidence update events during active gestures.
        
        Should publish confidence updates for ongoing gestures.
        """
        from src.service.events import ServiceEvent, EventType
        
        # Test confidence update event
        confidence_data = {
            "gesture_type": "hand_up",
            "previous_confidence": 0.75,
            "current_confidence": 0.82,
            "confidence_trend": "increasing",
            "duration_ms": 1800.0
        }
        
        event = ServiceEvent(
            event_type=EventType.GESTURE_CONFIDENCE_UPDATE,
            data=confidence_data
        )
        
        assert event.event_type == EventType.GESTURE_CONFIDENCE_UPDATE, "Should be confidence update"
        assert event.data["confidence_trend"] == "increasing", "Should track trend"
        assert event.data["current_confidence"] > event.data["previous_confidence"], "Should show improvement"
    
    def test_gesture_event_serialization_for_sse_streaming(self):
        """
        RED TEST: Test gesture event serialization for SSE streaming.
        
        Should properly serialize gesture events for Server-Sent Events format.
        """
        from src.service.events import ServiceEvent, EventType
        
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up",
                "confidence": 0.88,
                "hand": "right",
                "position": {"hand_x": 0.6, "hand_y": 0.2},
                "duration_ms": 950.0
            }
        )
        
        # Test JSON serialization
        serialized = gesture_event.to_json()
        assert "gesture_detected" in serialized, "Should include event type"
        assert "hand_up" in serialized, "Should include gesture type"
        assert "0.88" in serialized, "Should include confidence"
        
        # Test SSE format
        sse_format = gesture_event.to_sse_format()
        assert sse_format.startswith("data: "), "Should start with SSE data prefix"
        assert "\n\n" in sse_format, "Should end with SSE terminator" 