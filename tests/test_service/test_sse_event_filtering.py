"""
Test SSE Event Filtering and Integration.

Testing gesture-specific event filtering and real-time streaming integration
with the EventPublisher system. Phase 15.2: SSE Event Filtering and Integration.
Following TDD methodology: Red → Green → Refactor.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.service.sse_service import SSEDetectionService, SSEServiceConfig
from src.service.events import EventPublisher, ServiceEvent, EventType


class TestSSEEventFiltering:
    """Test SSE event filtering for gesture-specific streaming."""
    
    def test_gesture_event_filter_configuration(self):
        """
        RED TEST: Test gesture event filtering configuration.
        
        Should filter events to only stream gesture-related events via SSE.
        """
        from src.service.sse_service import SSEDetectionService
        
        # Create SSE service with gesture event filtering
        config = SSEServiceConfig(gesture_events_only=True)
        service = SSEDetectionService(config=config)
        
        # Test gesture event filter configuration
        assert service.config.gesture_events_only, "Should filter only gesture events"
        
        # Test gesture event types are included
        gesture_event_types = service.get_filtered_event_types()
        expected_gesture_types = [
            EventType.GESTURE_DETECTED,
            EventType.GESTURE_LOST, 
            EventType.GESTURE_CONFIDENCE_UPDATE
        ]
        
        for event_type in expected_gesture_types:
            assert event_type in gesture_event_types, f"Should include {event_type} in filter"
        
        # Test non-gesture events are excluded
        non_gesture_types = [EventType.PRESENCE_CHANGED, EventType.DETECTION_UPDATE]
        for event_type in non_gesture_types:
            assert event_type not in gesture_event_types, f"Should exclude {event_type} from filter"
    
    @pytest.mark.asyncio
    async def test_event_publisher_integration_subscription(self):
        """
        RED TEST: Test EventPublisher integration and subscription.
        
        Should subscribe to EventPublisher and receive gesture events.
        """
        from src.service.sse_service import SSEDetectionService
        from src.service.events import EventPublisher, ServiceEvent, EventType
        
        service = SSEDetectionService()
        event_publisher = EventPublisher()
        
        # Test EventPublisher subscription setup
        subscription_id = await service.subscribe_to_events(event_publisher)
        
        assert subscription_id is not None, "Should return subscription ID"
        assert service.is_subscribed_to_events(), "Should be subscribed to events"
        
        # Add a client connection so events can be processed
        await service.add_client_connection("test_client")
        
        # Test gesture event reception
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={"gesture_type": "hand_up", "confidence": 0.85}
        )
        
        # Verify client queue is empty before event
        client_queue = service.active_connections["test_client"]
        initial_queue_size = client_queue.qsize()
        assert initial_queue_size == 0, "Queue should be empty initially"
        
        # Publish gesture event
        await event_publisher.publish_async(gesture_event)
        
        # Give a small delay for event processing
        await asyncio.sleep(0.1)
        
        # Verify event was queued for the client
        final_queue_size = client_queue.qsize()
        assert final_queue_size > initial_queue_size, "Should have queued event for client"
        
        # Verify the event content
        if not client_queue.empty():
            event_message = await client_queue.get()
            assert "gesture_detected" in event_message, "Should contain gesture_detected event"
            assert "hand_up" in event_message, "Should contain gesture data"
    
    @pytest.mark.asyncio
    async def test_gesture_event_streaming_to_clients(self):
        """
        RED TEST: Test real-time gesture event streaming to clients.
        
        Should stream gesture events to all connected SSE clients in real-time.
        """
        from src.service.sse_service import SSEDetectionService
        from src.service.events import ServiceEvent, EventType
        
        service = SSEDetectionService()
        
        # Add test clients
        client_ids = ["client1", "client2", "client3"]
        for client_id in client_ids:
            await service.add_client_connection(client_id)
        
        # Create gesture event
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up",
                "confidence": 0.92,
                "hand": "right",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Stream event to clients
        await service.stream_gesture_event_to_clients(gesture_event)
        
        # Verify all clients received the event
        for client_id in client_ids:
            client_queue = service.active_connections[client_id]
            assert not client_queue.empty(), f"Client {client_id} should have received event"
            
            # Verify event format
            event_message = await client_queue.get()
            assert "event: gesture_detected" in event_message, "Should have correct event type"
            assert "hand_up" in event_message, "Should contain gesture data"
            assert "0.92" in event_message, "Should contain confidence value"
    
    @pytest.mark.asyncio
    async def test_event_queue_management_for_multiple_clients(self):
        """
        RED TEST: Test event queue management for multiple clients.
        
        Should manage separate event queues for each client without interference.
        """
        from src.service.sse_service import SSEDetectionService
        from src.service.events import ServiceEvent, EventType
        
        service = SSEDetectionService()
        
        # Add clients
        await service.add_client_connection("fast_client")
        await service.add_client_connection("slow_client")
        
        # Send multiple events
        events = []
        for i in range(5):
            event = ServiceEvent(
                event_type=EventType.GESTURE_CONFIDENCE_UPDATE,
                data={"confidence": 0.8 + (i * 0.02), "sequence": i}
            )
            events.append(event)
            await service.stream_gesture_event_to_clients(event)
        
        # Verify fast client can process all events
        fast_queue = service.active_connections["fast_client"]
        fast_events_received = []
        
        while not fast_queue.empty():
            message = await fast_queue.get()
            fast_events_received.append(message)
        
        assert len(fast_events_received) == 5, "Fast client should receive all events"
        
        # Verify slow client has same events (independent queue)
        slow_queue = service.active_connections["slow_client"]
        slow_events_received = []
        
        while not slow_queue.empty():
            message = await slow_queue.get()
            slow_events_received.append(message)
        
        assert len(slow_events_received) == 5, "Slow client should receive all events independently"
        
        # Verify queue independence
        for i, (fast_msg, slow_msg) in enumerate(zip(fast_events_received, slow_events_received)):
            assert fast_msg == slow_msg, f"Event {i} should be identical for both clients"
    
    @pytest.mark.asyncio
    async def test_performance_multiple_clients_simultaneous_events(self):
        """
        RED TEST: Test performance with multiple clients receiving simultaneous events.
        
        Should handle high-frequency events to multiple clients efficiently.
        """
        from src.service.sse_service import SSEDetectionService
        from src.service.events import ServiceEvent, EventType
        import time
        
        service = SSEDetectionService()
        
        # Add multiple clients (simulating dashboard, mobile, web)
        client_count = 10
        for i in range(client_count):
            await service.add_client_connection(f"client_{i}")
        
        # Performance test: Send 20 events rapidly
        start_time = time.time()
        event_count = 20
        
        for i in range(event_count):
            event = ServiceEvent(
                event_type=EventType.GESTURE_DETECTED,
                data={"gesture_type": "hand_up", "sequence": i, "timestamp": time.time()}
            )
            await service.stream_gesture_event_to_clients(event)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 2.0, f"Should stream {event_count} events to {client_count} clients in <2s"
        
        # Verify all clients received all events
        for i in range(client_count):
            client_queue = service.active_connections[f"client_{i}"]
            received_count = client_queue.qsize()
            assert received_count == event_count, f"Client {i} should receive all {event_count} events"
        
        # Calculate throughput
        events_per_second = (event_count * client_count) / total_time
        assert events_per_second > 50, f"Should achieve >50 events/sec throughput (got {events_per_second:.1f})"
    
    @pytest.mark.asyncio
    async def test_error_isolation_sse_failures_dont_affect_detection(self):
        """
        RED TEST: Test error isolation - SSE failures don't affect core detection.
        
        Should isolate SSE streaming errors without impacting detection pipeline.
        """
        from src.service.sse_service import SSEDetectionService
        from src.service.events import EventPublisher, ServiceEvent, EventType
        
        service = SSEDetectionService()
        event_publisher = EventPublisher()
        
        # Subscribe SSE service to events
        await service.subscribe_to_events(event_publisher)
        
        # Add a problematic client (simulate network issues)
        await service.add_client_connection("problematic_client")
        
        # Mock client queue to raise exception
        problematic_queue = service.active_connections["problematic_client"]
        original_put = problematic_queue.put_nowait
        
        def failing_put(item):
            raise ConnectionError("Client connection lost")
        
        problematic_queue.put_nowait = failing_put
        
        # Test that event publishing still works despite SSE client failure
        detection_events_processed = []
        
        def track_events(event):
            detection_events_processed.append(event)
        
        event_publisher.subscribe(track_events)
        
        # Publish gesture event
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={"gesture_type": "hand_up"}
        )
        
        # This should not raise an exception despite SSE client failure
        await event_publisher.publish_async(gesture_event)
        
        # Verify event was still processed by other subscribers
        assert len(detection_events_processed) == 1, "Detection pipeline should still process events"
        assert detection_events_processed[0].event_type == EventType.GESTURE_DETECTED
        
        # Verify SSE service is still operational for other clients
        await service.add_client_connection("healthy_client")
        healthy_queue = service.active_connections["healthy_client"]
        
        # Should be able to stream to healthy client
        await service.stream_gesture_event_to_clients(gesture_event)
        assert not healthy_queue.empty(), "Healthy client should still receive events"
    
    def test_sse_service_configuration_with_filtering_options(self):
        """
        RED TEST: Test SSE service configuration with filtering options.
        
        Should support configuration for gesture-only filtering and other options.
        """
        from src.service.sse_service import SSEServiceConfig
        
        # Test gesture-only filtering configuration
        config = SSEServiceConfig(
            gesture_events_only=True,
            include_confidence_updates=False,
            min_gesture_confidence=0.7
        )
        
        assert config.gesture_events_only, "Should enable gesture-only filtering"
        assert not config.include_confidence_updates, "Should exclude confidence updates"
        assert config.min_gesture_confidence == 0.7, "Should set minimum confidence threshold"
        
        # Test filter configuration validation
        with pytest.raises(ValueError):
            SSEServiceConfig(min_gesture_confidence=1.5)  # Invalid confidence
        
        with pytest.raises(ValueError):
            SSEServiceConfig(min_gesture_confidence=-0.1)  # Invalid confidence
        
        # Test configuration defaults
        default_config = SSEServiceConfig()
        assert default_config.gesture_events_only, "Should default to gesture events only"
        assert default_config.include_confidence_updates, "Should default to include confidence updates"
        assert default_config.min_gesture_confidence == 0.6, "Should have default confidence threshold"
    
    @pytest.mark.asyncio
    async def test_gesture_confidence_filtering(self):
        """
        RED TEST: Test gesture confidence filtering.
        
        Should filter gesture events based on minimum confidence threshold.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        from src.service.events import ServiceEvent, EventType
        
        # Configure service with confidence filtering
        config = SSEServiceConfig(min_gesture_confidence=0.8)
        service = SSEDetectionService(config=config)
        
        await service.add_client_connection("test_client")
        
        # Test high confidence event (should pass filter)
        high_confidence_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={"gesture_type": "hand_up", "confidence": 0.85}
        )
        
        should_stream = service.should_stream_event(high_confidence_event)
        assert should_stream, "Should stream high confidence events"
        
        # Test low confidence event (should be filtered out)
        low_confidence_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={"gesture_type": "hand_up", "confidence": 0.75}
        )
        
        should_stream = service.should_stream_event(low_confidence_event)
        assert not should_stream, "Should filter out low confidence events"
        
        # Test streaming behavior
        await service.stream_gesture_event_to_clients(high_confidence_event)
        await service.stream_gesture_event_to_clients(low_confidence_event)
        
        # Verify only high confidence event was queued
        client_queue = service.active_connections["test_client"]
        assert client_queue.qsize() == 1, "Should only queue high confidence events"
        
        event_message = await client_queue.get()
        assert "0.85" in event_message, "Should contain high confidence value"
        assert "0.75" not in event_message, "Should not contain low confidence value" 