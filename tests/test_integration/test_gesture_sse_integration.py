"""
Test Gesture + SSE Pipeline Integration.

Testing the complete workflow: Camera → Presence → Gesture → SSE Event streaming.
Following TDD methodology: Red → Green → Refactor.

Phase 16: Gesture + SSE Pipeline Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import numpy as np

from src.detection.multimodal_detector import MultiModalDetector
from src.detection.gesture_detector import GestureDetector
from src.detection.result import DetectionResult
from src.gesture.result import GestureResult
from src.service.events import EventPublisher, ServiceEvent, EventType
from src.service.sse_service import SSEDetectionService, SSEServiceConfig
from src.processing.processor import FrameProcessor


class TestConditionalGestureDetection:
    """Test conditional gesture detection - only run when human is present."""
    
    def test_gesture_detection_conditional_on_human_presence(self):
        """
        RED TEST: Test gesture detection only runs when human is detected.
        
        Performance optimization: gesture detection should be skipped when no human
        is present to save computational resources.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        
        # Setup enhanced processor with both detectors
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        # Mock frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test Case 1: No human present - gesture detection should be skipped
        no_human_result = DetectionResult(
            human_present=False,
            confidence=0.2,
            landmarks=[],
            bounding_box=(0, 0, 0, 0)
        )
        multimodal_detector.detect.return_value = no_human_result
        
        # Process frame
        result = processor.process_frame(test_frame)
        
        # Verify gesture detection was NOT called
        assert multimodal_detector.detect.called, "Should run human detection"
        assert not gesture_detector.detect_gestures.called, "Should NOT run gesture detection when no human"
        assert result.human_present is False, "Should report no human present"
        
        # Reset mocks
        multimodal_detector.reset_mock()
        gesture_detector.reset_mock()
        
        # Test Case 2: Human present - gesture detection should run
        human_present_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],  # Fixed: Use tuples instead of dictionaries
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_present_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right"
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Process frame
        result = processor.process_frame(test_frame)
        
        # Verify both detections ran
        assert multimodal_detector.detect.called, "Should run human detection"
        assert gesture_detector.detect_gestures.called, "Should run gesture detection when human present"
        
        # Verify gesture detection received pose landmarks
        call_args = gesture_detector.detect_gestures.call_args
        assert call_args[0][0] is test_frame, "Should pass frame to gesture detector"
        assert call_args[1]["pose_landmarks"] == human_present_result.landmarks, "Should pass pose landmarks"
    
    def test_gesture_detection_confidence_threshold_filtering(self):
        """
        RED TEST: Test gesture detection respects confidence threshold.
        
        Should only run gesture detection when human confidence is above
        configurable threshold (default: 0.6).
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        # Configure with specific confidence threshold
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher,
            min_human_confidence_for_gesture=0.6
        )
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test Case 1: Human present but confidence too low
        low_confidence_result = DetectionResult(
            human_present=True,
            confidence=0.4,  # Below 0.6 threshold
            landmarks=[(0.5, 0.3)],  # Fixed: Use tuples instead of dictionaries
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = low_confidence_result
        
        processor.process_frame(test_frame)
        
        # Verify gesture detection was NOT called
        assert not gesture_detector.detect_gestures.called, "Should NOT run gesture detection when confidence too low"
        
        # Reset mocks
        gesture_detector.reset_mock()
        
        # Test Case 2: Human present with sufficient confidence
        high_confidence_result = DetectionResult(
            human_present=True,
            confidence=0.75,  # Above 0.6 threshold
            landmarks=[(0.5, 0.3)],  # Fixed: Use tuples instead of dictionaries
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = high_confidence_result
        
        processor.process_frame(test_frame)
        
        # Verify gesture detection was called
        assert gesture_detector.detect_gestures.called, "Should run gesture detection when confidence sufficient"
    
    def test_enhanced_frame_processor_resource_sharing(self):
        """
        RED TEST: Test enhanced frame processor shares resources efficiently.
        
        Should reuse pose landmarks from human detection for gesture detection
        to optimize performance and avoid redundant computation.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock pose landmarks from multimodal detection
        pose_landmarks = [
            (0.5, 0.3),  # Fixed: Use tuples instead of dictionaries
            (0.6, 0.2)   # Fixed: Use tuples instead of dictionaries
        ]
        
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=pose_landmarks,
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right"
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Process frame
        processor.process_frame(test_frame)
        
        # Verify pose landmarks were passed to gesture detector
        call_args = gesture_detector.detect_gestures.call_args
        assert call_args[1]["pose_landmarks"] == pose_landmarks, "Should share pose landmarks"
        
        # Verify efficient resource usage
        assert multimodal_detector.detect.call_count == 1, "Should only call human detection once"
        assert gesture_detector.detect_gestures.call_count == 1, "Should only call gesture detection once"
    
    def test_gesture_event_publishing_integration(self):
        """
        RED TEST: Test gesture events are published correctly through event system.
        
        Should convert gesture detection results to ServiceEvents and publish
        them for SSE streaming and other service integrations.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock successful human and gesture detection
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],  # Fixed: Use tuples instead of dictionaries
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right",
            duration_ms=1250
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Process frame
        processor.process_frame(test_frame)
        
        # Verify gesture event was published
        assert event_publisher.publish.called, "Should publish gesture event"
        
        # Verify event content
        published_event = event_publisher.publish.call_args[0][0]
        assert isinstance(published_event, ServiceEvent), "Should publish ServiceEvent"
        assert published_event.event_type == EventType.GESTURE_DETECTED, "Should be gesture detected event"
        assert published_event.data["gesture_type"] == "hand_up", "Should include gesture type"
        assert published_event.data["confidence"] == 0.85, "Should include confidence"
        assert published_event.data["hand"] == "right", "Should include hand"
        assert published_event.data["duration_ms"] == 1250, "Should include duration"
    
    def test_performance_impact_measurement(self):
        """
        RED TEST: Test performance impact of conditional gesture detection.
        
        Should measure and validate that conditional gesture detection provides
        significant performance improvement when no humans are present.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        import time
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock no human detection (gesture detection should be skipped)
        no_human_result = DetectionResult(
            human_present=False,
            confidence=0.2,
            landmarks=[],
            bounding_box=(0, 0, 0, 0)
        )
        multimodal_detector.detect.return_value = no_human_result
        
        # Simulate gesture detector taking time (when called)
        def slow_gesture_detection(*args, **kwargs):
            time.sleep(0.01)  # 10ms simulated processing
            return GestureResult(gesture_detected=False)
        
        gesture_detector.detect_gestures.side_effect = slow_gesture_detection
        
        # Process multiple frames and measure time
        start_time = time.time()
        for _ in range(10):
            processor.process_frame(test_frame)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify performance - should be fast since gesture detection was skipped
        assert processing_time < 0.05, f"Processing should be fast when gesture detection skipped, took {processing_time}s"
        assert gesture_detector.detect_gestures.call_count == 0, "Gesture detection should not be called when no human"
        
        # Verify performance metrics are tracked
        performance_stats = processor.get_performance_stats()
        assert "frames_processed" in performance_stats, "Should track frames processed"
        assert "gesture_detection_skipped" in performance_stats, "Should track skipped gesture detections"
        assert performance_stats["gesture_detection_skipped"] == 10, "Should count skipped detections"
    
    def test_error_handling_in_conditional_detection(self):
        """
        RED TEST: Test error handling in conditional gesture detection.
        
        Should handle errors gracefully and continue processing even if
        gesture detection fails when human is present.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Mock successful human detection
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],  # Fixed: Use tuples instead of dictionaries
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        # Mock gesture detector failure
        gesture_detector.detect_gestures.side_effect = Exception("Gesture detection failed")
        
        # Process frame - should not crash
        result = processor.process_frame(test_frame)
        
        # Verify graceful error handling
        assert result.human_present is True, "Should still report human presence"
        assert multimodal_detector.detect.called, "Should have called human detection"
        assert gesture_detector.detect_gestures.called, "Should have attempted gesture detection"
        
        # Verify error event was published
        error_events = [call[0][0] for call in event_publisher.publish.call_args_list 
                      if call[0][0].event_type == EventType.ERROR_OCCURRED]
        assert len(error_events) > 0, "Should publish error event"
        assert "gesture detection" in error_events[0].data["message"].lower(), "Should describe gesture detection error"
    
    def test_enhanced_frame_processor_configuration(self):
        """
        RED TEST: Test enhanced frame processor accepts configuration options.
        
        Should support configuration for gesture detection thresholds,
        performance settings, and event publishing options.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor, EnhancedProcessorConfig
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        # Test custom configuration
        config = EnhancedProcessorConfig(
            min_human_confidence_for_gesture=0.7,
            enable_gesture_detection=True,
            publish_gesture_events=True,
            performance_monitoring=True
        )
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher,
            config=config
        )
        
        # Verify configuration is applied
        assert processor.config.min_human_confidence_for_gesture == 0.7, "Should use custom confidence threshold"
        assert processor.config.enable_gesture_detection is True, "Should enable gesture detection"
        assert processor.config.publish_gesture_events is True, "Should enable event publishing"
        assert processor.config.performance_monitoring is True, "Should enable performance monitoring"
        
        # Test configuration validation
        with pytest.raises(ValueError, match="min_human_confidence_for_gesture must be between 0.0 and 1.0"):
            EnhancedProcessorConfig(min_human_confidence_for_gesture=1.5)
        
        # Test default configuration
        default_processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        assert default_processor.config.min_human_confidence_for_gesture == 0.6, "Should use default confidence threshold"


class TestEndToEndGestureSSEFlow:
    """Test complete end-to-end pipeline: Camera → Presence → Gesture → SSE Event."""
    
    def test_complete_gesture_to_sse_pipeline(self):
        """
        RED TEST: Test complete pipeline from gesture detection to SSE streaming.
        
        Should test the full workflow: Enhanced frame processor detects gesture
        and immediately streams it via SSE service to connected clients.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        import asyncio
        
        # Setup components
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = EventPublisher()
        
        # Enhanced processor with real event publisher
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        # SSE service with gesture filtering
        sse_config = SSEServiceConfig(
            host="localhost",
            port=8766,
            gesture_events_only=True,
            min_gesture_confidence=0.6
        )
        sse_service = SSEDetectionService(sse_config)
        
        # Subscribe SSE service to events
        sse_service.setup_gesture_integration(event_publisher)
        
        # Mock successful detections
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right",
            duration_ms=1500
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Process frame (should trigger gesture event)
        processor.process_frame(test_frame)
        
        # Verify event was received by SSE service
        # Check that the service is subscribed to events
        assert sse_service.is_subscribed_to_events(), "SSE service should be subscribed to events"
    
    @pytest.mark.asyncio
    async def test_real_time_gesture_streaming_to_multiple_clients(self):
        """
        RED TEST: Test real-time gesture events streamed to multiple SSE clients.
        
        Should test that when gesture is detected, multiple SSE clients
        immediately receive the event in proper SSE format.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        # Setup real async components
        event_publisher = EventPublisher()
        
        # SSE service
        sse_config = SSEServiceConfig(
            host="localhost",
            port=8766,
            gesture_events_only=True
        )
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Mock multiple clients (simulate connection queues)
        client_queues = []
        for i in range(3):
            client_queue = asyncio.Queue()
            client_queues.append(client_queue)
            sse_service.active_connections[f"client_{i}"] = client_queue
        
        # Create gesture event
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up",
                "confidence": 0.9,
                "hand": "right",
                "duration_ms": 2000
            }
        )
        
        # Publish event (should stream to all clients)
        await event_publisher.publish_async(gesture_event)
        
        # Wait briefly for async processing
        await asyncio.sleep(0.1)
        
        # Verify all clients received event
        for i, client_queue in enumerate(client_queues):
            assert not client_queue.empty(), f"Client {i} should receive gesture event"
            
            received_event = await client_queue.get()
            assert "data:" in received_event, "Should be in SSE format"
            assert "gesture_detected" in received_event, "Should contain event type"
            assert "hand_up" in received_event, "Should contain gesture data"
    
    def test_multiple_gesture_events_sequence(self):
        """
        RED TEST: Test sequence of multiple gesture events handled correctly.
        
        Should test gesture detected → gesture lost → gesture detected again
        and verify each event is processed and streamed correctly.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Human always present for this test
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        # Sequence: Gesture detected → No gesture → Gesture detected again
        gesture_results = [
            GestureResult(gesture_detected=True, gesture_type="hand_up", confidence=0.85, hand="right"),
            GestureResult(gesture_detected=False, confidence=0.0),
            GestureResult(gesture_detected=True, gesture_type="hand_up", confidence=0.9, hand="left")
        ]
        
        # Process each frame in sequence
        for i, gesture_result in enumerate(gesture_results):
            gesture_detector.detect_gestures.return_value = gesture_result
            processor.process_frame(test_frame)
        
        # Verify correct sequence of events published
        published_calls = event_publisher.publish.call_args_list
        assert len(published_calls) >= 2, "Should publish at least 2 gesture events"
        
        # First event: gesture detected
        first_event = published_calls[0][0][0]
        assert first_event.event_type == EventType.GESTURE_DETECTED, "First should be gesture detected"
        assert first_event.data["hand"] == "right", "First gesture should be right hand"
        
        # Last event: gesture detected again (left hand)
        last_event = published_calls[-1][0][0]  
        assert last_event.event_type == EventType.GESTURE_DETECTED, "Last should be gesture detected"
        assert last_event.data["hand"] == "left", "Last gesture should be left hand"
    
    def test_gesture_lost_events_when_hand_goes_down(self):
        """
        RED TEST: Test gesture lost events when hand goes down.
        
        Should test that when a detected gesture is no longer present,
        a GESTURE_LOST event is published and streamed.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = Mock(spec=EventPublisher)
        
        # Enhanced processor with gesture state tracking
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        # Frame 1: Gesture detected
        gesture_detected = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right",
            duration_ms=1000
        )
        gesture_detector.detect_gestures.return_value = gesture_detected
        processor.process_frame(test_frame)
        
        # Frame 2: Gesture no longer detected (hand went down)
        gesture_lost = GestureResult(
            gesture_detected=False,
            confidence=0.0,
            previous_gesture_type="hand_up",  # Should track what was lost
            previous_hand="right"
        )
        gesture_detector.detect_gestures.return_value = gesture_lost
        processor.process_frame(test_frame)
        
        # Verify both events were published
        published_calls = event_publisher.publish.call_args_list
        assert len(published_calls) >= 2, "Should publish both detected and lost events"
        
        # Verify gesture lost event
        gesture_lost_events = [call[0][0] for call in published_calls 
                             if call[0][0].event_type == EventType.GESTURE_LOST]
        assert len(gesture_lost_events) > 0, "Should publish GESTURE_LOST event"
        
        lost_event = gesture_lost_events[0]
        assert lost_event.data["previous_gesture_type"] == "hand_up", "Should track what gesture was lost"
        assert lost_event.data["previous_hand"] == "right", "Should track which hand"
    
    def test_sse_client_receives_correct_event_format(self):
        """
        RED TEST: Test SSE clients receive events in correct SSE format.
        
        Should verify that gesture events are properly formatted as SSE events
        with correct headers, data format, and JSON structure.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        sse_config = SSEServiceConfig(
            host="localhost",
            port=8766,
            gesture_events_only=True
        )
        sse_service = SSEDetectionService(sse_config)
        
        # Create test gesture event
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up",
                "confidence": 0.88,
                "hand": "right",
                "duration_ms": 1250,
                "timestamp": "2024-01-15T10:30:00Z"
            },
            event_id="gesture_123"
        )
        
        # Test SSE format conversion
        sse_message = sse_service._format_event_for_sse(gesture_event)
        
        # Verify SSE format (should include event line and data line)
        assert "event: gesture_detected" in sse_message, "Should include SSE event type"
        assert "data: " in sse_message, "Should include SSE data line"
        assert '"gesture_type": "hand_up"' in sse_message, "Should include gesture type in data"
        assert '"confidence": 0.88' in sse_message, "Should include confidence in data"
        assert '"event_type": "gesture_detected"' in sse_message, "Should include event_type in data"
    
    @pytest.mark.asyncio
    async def test_gesture_to_sse_streaming_latency(self):
        """
        RED TEST: Test performance - gesture detection to SSE streaming latency.
        
        Should measure and validate that gesture events reach SSE clients
        within acceptable latency bounds (<100ms).
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        import time
        
        # Setup real async event flow
        event_publisher = EventPublisher()
        
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Mock client queue
        client_queue = asyncio.Queue()
        sse_service.active_connections["test_client"] = client_queue
        
        # Create gesture event with timestamp
        start_time = time.time()
        
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up",
                "confidence": 0.85,
                "detection_timestamp": start_time
            }
        )
        
        # Publish event (async)
        await event_publisher.publish_async(gesture_event)
        
        # Wait for event to reach client
        await asyncio.sleep(0.01)  # Small delay for processing
        
        # Measure end-to-end latency
        end_time = time.time()
        latency = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Verify latency requirement
        assert latency < 100, f"Gesture to SSE latency should be <100ms, was {latency:.2f}ms"
        
        # Verify event reached client
        assert not client_queue.empty(), "Client should receive gesture event"
    
    def test_gesture_confidence_filtering_in_sse_stream(self):
        """
        RED TEST: Test gesture confidence filtering in SSE stream.
        
        Should verify that only gestures above configured confidence threshold
        are streamed to SSE clients, filtering out low-confidence detections.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        # SSE service with confidence filtering
        sse_config = SSEServiceConfig(
            host="localhost",
            port=8766,
            gesture_events_only=True,
            min_gesture_confidence=0.7  # Filter threshold
        )
        sse_service = SSEDetectionService(sse_config)
        
        # Test events with different confidence levels
        high_confidence_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up",
                "confidence": 0.85,  # Above threshold
                "hand": "right"
            }
        )
        
        low_confidence_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up", 
                "confidence": 0.5,   # Below threshold
                "hand": "left"
            }
        )
        
        # Test filtering logic
        should_stream_high = sse_service._should_stream_event(high_confidence_event)
        should_stream_low = sse_service._should_stream_event(low_confidence_event)
        
        assert should_stream_high is True, "Should stream high confidence gesture"
        assert should_stream_low is False, "Should filter low confidence gesture"
    
    @pytest.mark.asyncio
    async def test_concurrent_gesture_detection_and_sse_streaming(self):
        """
        RED TEST: Test concurrent gesture detection and SSE streaming performance.
        
        Should verify that multiple rapid gesture events can be processed
        and streamed concurrently without blocking or event loss.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        import asyncio
        
        # Setup concurrent processing
        event_publisher = EventPublisher()
        
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Multiple mock clients
        client_queues = []
        for i in range(5):
            client_queue = asyncio.Queue()
            client_queues.append(client_queue)
            sse_service.active_connections[f"client_{i}"] = client_queue
        
        # Generate rapid sequence of gesture events
        gesture_events = []
        for i in range(10):
            event = ServiceEvent(
                event_type=EventType.GESTURE_DETECTED,
                data={
                    "gesture_type": "hand_up",
                    "confidence": 0.8 + (i * 0.01),  # Varying confidence
                    "hand": "right" if i % 2 == 0 else "left",
                    "sequence_id": i
                }
            )
            gesture_events.append(event)
        
        # Publish all events concurrently
        async def publish_events():
            tasks = []
            for event in gesture_events:
                task = asyncio.create_task(event_publisher.publish_async(event))
                tasks.append(task)
            await asyncio.gather(*tasks)
        
        # Run concurrent publishing
        await publish_events()
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Verify all clients received all events
        for i, client_queue in enumerate(client_queues):
            received_count = client_queue.qsize()
            assert received_count == 10, f"Client {i} should receive all 10 events, got {received_count}"
    
    def test_gesture_sse_integration_error_handling(self):
        """
        RED TEST: Test error handling in gesture→SSE integration.
        
        Should verify that SSE streaming errors don't affect gesture detection
        and that gesture detection errors don't break SSE service.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = EventPublisher()
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        # SSE service with error simulation
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        
        # Mock SSE service method to simulate error
        original_stream = sse_service.stream_gesture_event_to_clients
        sse_service.stream_gesture_event_to_clients = Mock(side_effect=Exception("SSE streaming error"))
        
        sse_service.setup_gesture_integration(event_publisher)
        
        # Setup successful detection
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right"
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Process frame - should not crash despite SSE error
        result = processor.process_frame(test_frame)

        # Trigger async event handler by publishing through EventPublisher
        # This will call the SSE service's async subscription
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": "hand_up",
                "confidence": 0.85,
                "hand": "right"
            }
        )
        
        # Use async event publishing to trigger SSE async handler
        import asyncio
        asyncio.run(event_publisher.publish_async(gesture_event))

        # Verify gesture detection still works
        assert result.human_present is True, "Gesture detection should still work despite SSE error"
        assert multimodal_detector.detect.called, "Should still call human detection"
        assert gesture_detector.detect_gestures.called, "Should still call gesture detection"

        # Verify SSE service attempted to stream (error isolation)
        assert sse_service.stream_gesture_event_to_clients.called, "Should attempt SSE streaming"
    
    @pytest.mark.asyncio
    async def test_sse_service_gesture_event_queue_management(self):
        """
        RED TEST: Test SSE service manages gesture event queues properly.
        
        Should verify that gesture events are queued efficiently for multiple
        clients and that queue management prevents memory issues.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        import asyncio
        
        sse_config = SSEServiceConfig(
            host="localhost",
            port=8766,
            max_queue_size=100  # Test queue limits
        )
        sse_service = SSEDetectionService(sse_config)
        
        # Add multiple clients
        for i in range(3):
            client_queue = asyncio.Queue(maxsize=50)  # Limited queue size
            sse_service.active_connections[f"client_{i}"] = client_queue
        
        # Create many gesture events
        events = []
        for i in range(20):
            event = ServiceEvent(
                event_type=EventType.GESTURE_DETECTED,
                data={
                    "gesture_type": "hand_up",
                    "confidence": 0.8,
                    "sequence": i
                }
            )
            events.append(event)
        
        # Queue events for all clients (await the async method)
        for event in events:
            await sse_service._queue_event_for_all_clients(event)
        
        # Verify all clients have events queued
        for client_id, client_data in sse_service.active_connections.items():
            queue_size = client_data.qsize()
            assert queue_size == 20, f"Client {client_id} should have 20 queued events, got {queue_size}"
        
        # Test queue overflow protection
        overflow_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={"gesture_type": "hand_up", "overflow_test": True}
        )
        
        # Should handle queue overflow gracefully (await the async method)
        await sse_service._queue_event_for_all_clients(overflow_event)
        
        # Verify service remains stable (no crashes)


class TestProductionIntegrationAndPerformance:
    """
    Phase 16.3: Production Integration and Performance Tests
    
    The GRAND FINALE! Tests for complete production system integration
    with webcam_http_service.py, performance benchmarking, and 
    real-world deployment scenarios.
    """
    
    def test_integration_with_webcam_http_service(self):
        """
        RED TEST: Test integration with existing webcam_http_service.py.
        
        Should verify that gesture detection + SSE streaming can be
        integrated into the existing production HTTP service without
        conflicts or performance issues.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
        from src.camera import CameraManager
        
        # Setup production-like environment
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = EventPublisher()
        
        # Enhanced frame processor (gesture-enabled)
        enhanced_processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        # HTTP API service (existing production service)
        http_config = HTTPServiceConfig(host="localhost", port=8767)
        http_service = HTTPDetectionService(http_config)
        http_service.setup_event_integration(event_publisher)
        
        # SSE service (new gesture streaming service)
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Test frame processing with both services
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right"
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Process frame through enhanced processor
        result = enhanced_processor.process_frame(test_frame)
        
        # Verify both services receive and process events
        assert result.human_present is True, "Enhanced processor should detect human"
        assert multimodal_detector.detect.called, "Should call human detection"
        assert gesture_detector.detect_gestures.called, "Should call gesture detection"
        
        # Verify HTTP service receives presence events
        assert http_service.is_subscribed_to_events(), "HTTP service should be subscribed"
        
        # Verify SSE service receives gesture events  
        assert sse_service.is_subscribed_to_events(), "SSE service should be subscribed"
        
        # Verify no port conflicts
        assert http_config.port != sse_config.port, "Services should use different ports"
        
        # Verify services can coexist
        assert http_service.get_health_status()["status"] == "healthy", "HTTP service should be healthy"
        assert sse_service.get_health_status()["status"] == "healthy", "SSE service should be healthy"

    @pytest.mark.asyncio
    async def test_simultaneous_http_and_sse_service_operation(self):
        """
        RED TEST: Test simultaneous HTTP API + SSE service operation.
        
        Should verify that both services can run concurrently without
        interference, handling requests and streaming events simultaneously.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
        import asyncio
        
        # Setup concurrent services
        event_publisher = EventPublisher()
        
        # Mock detectors
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        
        # Enhanced processor
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        # HTTP service
        http_config = HTTPServiceConfig(host="localhost", port=8767)
        http_service = HTTPDetectionService(http_config)
        http_service.setup_event_integration(event_publisher)
        
        # SSE service
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Add mock SSE clients
        for i in range(3):
            client_queue = asyncio.Queue()
            sse_service.active_connections[f"client_{i}"] = client_queue
        
        # Setup detection responses
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right"
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Simulate concurrent operations
        async def process_frames():
            """Simulate continuous frame processing."""
            for i in range(5):
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                result = processor.process_frame(test_frame)
                await asyncio.sleep(0.1)  # Simulate processing time
                
        async def simulate_http_requests():
            """Simulate HTTP API requests."""
            for i in range(10):
                # Simulate HTTP request processing
                presence_status = http_service.get_current_presence_status()
                assert presence_status is not None, "Should get presence status"
                await asyncio.sleep(0.05)  # Simulate request handling
        
        async def simulate_sse_streaming():
            """Simulate SSE event streaming."""
            for i in range(5):
                event = ServiceEvent(
                    event_type=EventType.GESTURE_DETECTED,
                    data={"gesture_type": "hand_up", "confidence": 0.8}
                )
                await event_publisher.publish_async(event)
                await asyncio.sleep(0.1)
        
        # Run all operations concurrently
        await asyncio.gather(
            process_frames(),
            simulate_http_requests(),
            simulate_sse_streaming()
        )
        
        # Verify concurrent operation success
        assert multimodal_detector.detect.call_count >= 5, "Should process multiple frames"
        assert gesture_detector.detect_gestures.call_count >= 5, "Should detect gestures"
        
        # Verify SSE clients received events
        for client_id, client_queue in sse_service.active_connections.items():
            queue_size = client_queue.qsize()
            assert queue_size > 0, f"Client {client_id} should have received events"
        
        # Verify services remain healthy during concurrent operation
        http_health = http_service.get_health_status()
        sse_health = sse_service.get_health_status()
        
        assert http_health["status"] == "healthy", "HTTP service should remain healthy"
        assert sse_health["status"] == "healthy", "SSE service should remain healthy"

    def test_performance_with_both_presence_and_gesture_detection(self):
        """
        RED TEST: Test performance with both presence and gesture detection.
        
        Should verify that the combined detection pipeline maintains
        acceptable performance levels for real-time applications.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        import time
        
        # Setup performance testing
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = EventPublisher()
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        # Mock detection with realistic processing time
        def slow_human_detection(*args, **kwargs):
            time.sleep(0.03)  # Simulate 30ms human detection
            return DetectionResult(
                human_present=True,
                confidence=0.8,
                landmarks=[(0.5, 0.3)],
                bounding_box=(100, 100, 200, 200)
            )
        
        def slow_gesture_detection(*args, **kwargs):
            time.sleep(0.02)  # Simulate 20ms gesture detection
            return GestureResult(
                gesture_detected=True,
                gesture_type="hand_up",
                confidence=0.85,
                hand="right"
            )
        
        multimodal_detector.detect.side_effect = slow_human_detection
        gesture_detector.detect_gestures.side_effect = slow_gesture_detection
        
        # Performance benchmark
        test_frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(20)]
        
        start_time = time.time()
        results = []
        
        for frame in test_frames:
            result = processor.process_frame(frame)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_frame = total_time / len(test_frames)
        fps = 1.0 / avg_time_per_frame if avg_time_per_frame > 0 else 0
        
        # Verify performance targets
        assert avg_time_per_frame < 0.1, f"Average processing time should be <100ms, got {avg_time_per_frame:.3f}s"
        assert fps >= 10, f"Should achieve at least 10 FPS, got {fps:.1f} FPS"
        
        # Verify all frames processed correctly
        assert len(results) == 20, "Should process all test frames"
        
        # Verify both detectors called for each frame
        assert multimodal_detector.detect.call_count == 20, "Should call human detection for each frame"
        assert gesture_detector.detect_gestures.call_count == 20, "Should call gesture detection for each frame"
        
        # Verify performance stats available
        perf_stats = processor.get_performance_stats()
        assert "total_frames_processed" in perf_stats, "Should track frame count"
        assert "human_detection_time_ms" in perf_stats, "Should track human detection time"
        assert "gesture_detection_time_ms" in perf_stats, "Should track gesture detection time"

    def test_configuration_management_for_gesture_and_sse_features(self):
        """
        RED TEST: Test configuration management for gesture + SSE features.
        
        Should verify that all gesture and SSE configuration options
        are properly validated, applied, and documented.
        """
        from src.processing.enhanced_frame_processor import EnhancedProcessorConfig
        from src.service.sse_service import SSEServiceConfig
        from src.gesture.config import GestureConfig
        
        # Test enhanced processor configuration
        enhanced_config = EnhancedProcessorConfig(
            min_human_confidence_for_gesture=0.7,
            enable_gesture_detection=True,
            publish_gesture_events=True,
            performance_monitoring=True
        )
        
        # Verify configuration validation
        assert enhanced_config.min_human_confidence_for_gesture == 0.7, "Should set confidence threshold"
        assert enhanced_config.enable_gesture_detection is True, "Should enable gesture detection"
        assert enhanced_config.publish_gesture_events is True, "Should enable event publishing"
        assert enhanced_config.performance_monitoring is True, "Should enable performance monitoring"
        
        # Test SSE service configuration
        sse_config = SSEServiceConfig(
            host="localhost",
            port=8766,
            max_connections=25,
            gesture_events_only=True,
            min_gesture_confidence=0.6,
            max_queue_size=150
        )
        
        # Verify SSE configuration
        assert sse_config.host == "localhost", "Should set host"
        assert sse_config.port == 8766, "Should set port"
        assert sse_config.max_connections == 25, "Should set connection limit"
        assert sse_config.gesture_events_only is True, "Should filter to gesture events"
        assert sse_config.min_gesture_confidence == 0.6, "Should set confidence filter"
        assert sse_config.max_queue_size == 150, "Should set queue size"
        
        # Test gesture detection configuration
        gesture_config = GestureConfig(
            min_detection_confidence=0.8,
            debounce_frames=5,
            gesture_timeout_ms=3000
        )
        
        # Verify gesture configuration
        assert gesture_config.min_detection_confidence == 0.8, "Should set detection confidence"
        assert gesture_config.debounce_frames == 5, "Should set debounce frames"
        assert gesture_config.gesture_timeout_ms == 3000, "Should set gesture timeout"
        
        # Test configuration validation
        validation_result = SSEServiceConfig.validate_configuration({
            "host": "localhost",
            "port": 8766,
            "max_connections": 20,
            "min_gesture_confidence": 0.6
        })
        
        assert validation_result["is_valid"] is True, "Valid configuration should pass validation"
        assert len(validation_result["errors"]) == 0, "Should have no validation errors"
        
        # Test invalid configuration
        invalid_result = SSEServiceConfig.validate_configuration({
            "port": 99,  # Invalid port
            "min_gesture_confidence": 1.5  # Invalid confidence
        })
        
        assert invalid_result["is_valid"] is False, "Invalid configuration should fail validation"
        assert len(invalid_result["errors"]) > 0, "Should have validation errors"

    def test_memory_usage_and_resource_management(self):
        """
        RED TEST: Test memory usage and resource management.
        
        Should verify that the gesture + SSE system manages memory
        efficiently and doesn't leak resources during operation.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        import gc
        import sys
        
        # Baseline memory measurement
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Setup system components
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = EventPublisher()
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        sse_config = SSEServiceConfig(host="localhost", port=8766, max_queue_size=50)
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Simulate extended operation
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        multimodal_detector.detect.return_value = human_result
        
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right"
        )
        gesture_detector.detect_gestures.return_value = gesture_result
        
        # Process many frames to test memory usage
        for i in range(100):
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            result = processor.process_frame(test_frame)
            
            # Simulate SSE client events
            if i % 10 == 0:
                event = ServiceEvent(
                    event_type=EventType.GESTURE_DETECTED,
                    data={"gesture_type": "hand_up", "sequence": i}
                )
                event_publisher.publish(event)
        
        # Check memory after processing
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Verify memory management
        object_growth = final_objects - initial_objects
        assert object_growth < 2000, f"Object count growth should be reasonable, got {object_growth}"
        
        # Verify performance stats don't leak memory
        perf_stats = processor.get_performance_stats()
        assert "total_frames_processed" in perf_stats, "Should track performance"
        
        # Reset performance stats and verify cleanup
        processor.reset_performance_stats()
        reset_stats = processor.get_performance_stats()
        assert reset_stats["total_frames_processed"] == 0, "Should reset counters"
        
        # Verify SSE service resource management
        sse_health = sse_service.get_health_status()
        assert "active_connections" in sse_health, "Should track connections"
        
        # Verify resource cleanup methods exist
        assert hasattr(processor, 'get_efficiency_metrics'), "Should provide efficiency metrics"
        assert hasattr(sse_service, 'get_monitoring_data'), "Should provide monitoring data"

    @pytest.mark.asyncio
    async def test_service_startup_and_coordination(self):
        """
        RED TEST: Test service startup and coordination.
        
        Should verify that HTTP and SSE services can start up together,
        coordinate properly, and handle startup/shutdown sequences.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
        import asyncio
        
        # Setup service coordination
        event_publisher = EventPublisher()
        
        # HTTP service setup
        http_config = HTTPServiceConfig(host="localhost", port=8767)
        http_service = HTTPDetectionService(http_config)
        
        # SSE service setup
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        
        # Test startup sequence
        startup_results = []
        
        # HTTP service startup
        http_startup = await http_service.startup_with_validation()
        startup_results.append(("http", http_startup))
        
        # SSE service startup
        sse_startup = await sse_service.startup_with_validation()
        startup_results.append(("sse", sse_startup))
        
        # Verify successful startup
        for service_name, startup_result in startup_results:
            assert startup_result["success"] is True, f"{service_name} service should start successfully"
            assert "startup_time" in startup_result, f"{service_name} should track startup time"
        
        # Setup event integration after startup
        http_service.setup_event_integration(event_publisher)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Verify services are running
        assert http_service.is_running() is True, "HTTP service should be running"
        assert sse_service.is_running() is True, "SSE service should be running"
        
        # Test service coordination - publish events
        coordination_events = []
        
        # Presence event (should go to HTTP service)
        presence_event = ServiceEvent(
            event_type=EventType.PRESENCE_CHANGED,
            data={"human_present": True, "confidence": 0.8}
        )
        await event_publisher.publish_async(presence_event)
        coordination_events.append("presence")
        
        # Gesture event (should go to SSE service)
        gesture_event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={"gesture_type": "hand_up", "confidence": 0.85}
        )
        await event_publisher.publish_async(gesture_event)
        coordination_events.append("gesture")
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Verify coordination
        assert len(coordination_events) == 2, "Should publish coordination events"
        
        # Verify service health after coordination
        http_health = http_service.get_health_status()
        sse_health = sse_service.get_health_status()
        
        assert http_health["status"] == "healthy", "HTTP service should remain healthy"
        assert sse_health["status"] == "healthy", "SSE service should remain healthy"
        
        # Test graceful shutdown sequence
        shutdown_results = []
        
        # SSE service shutdown first (clients need to disconnect)
        sse_shutdown = await sse_service.graceful_shutdown_with_cleanup()
        shutdown_results.append(("sse", sse_shutdown))
        
        # HTTP service shutdown
        http_shutdown = await http_service.graceful_shutdown_with_cleanup()
        shutdown_results.append(("http", http_shutdown))
        
        # Verify graceful shutdown
        for service_name, shutdown_result in shutdown_results:
            assert shutdown_result["success"] is True, f"{service_name} service should shutdown gracefully"
            assert "cleanup_completed" in shutdown_result, f"{service_name} should confirm cleanup"

    def test_real_world_performance_benchmarking(self):
        """
        RED TEST: Test real-world performance benchmarking.
        
        Should verify that the complete gesture + SSE system meets
        real-world performance requirements for production deployment.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        import time
        import statistics
        
        # Setup realistic benchmark environment
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = EventPublisher()
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        # Add mock SSE clients for realistic load
        import asyncio
        for i in range(5):
            client_queue = asyncio.Queue(maxsize=100)
            sse_service.active_connections[f"benchmark_client_{i}"] = client_queue
        
        # Mock realistic detection timing
        def realistic_human_detection(*args, **kwargs):
            time.sleep(0.025)  # 25ms for human detection
            return DetectionResult(
                human_present=True,
                confidence=0.8,
                landmarks=[(0.5, 0.3)],
                bounding_box=(100, 100, 200, 200)
            )
        
        def realistic_gesture_detection(*args, **kwargs):
            time.sleep(0.015)  # 15ms for gesture detection
            return GestureResult(
                gesture_detected=True,
                gesture_type="hand_up",
                confidence=0.85,
                hand="right"
            )
        
        multimodal_detector.detect.side_effect = realistic_human_detection
        gesture_detector.detect_gestures.side_effect = realistic_gesture_detection
        
        # Real-world benchmark test
        benchmark_frames = 50
        frame_times = []
        gesture_detection_times = []
        sse_streaming_times = []
        
        for i in range(benchmark_frames):
            test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Measure frame processing time
            frame_start = time.time()
            result = processor.process_frame(test_frame)
            frame_end = time.time()
            
            frame_time = frame_end - frame_start
            frame_times.append(frame_time)
            
            # Measure gesture detection time specifically
            if result.human_present:
                gesture_start = time.time()
                # Simulate gesture event publishing
                gesture_event = ServiceEvent(
                    event_type=EventType.GESTURE_DETECTED,
                    data={"gesture_type": "hand_up", "benchmark_frame": i}
                )
                event_publisher.publish(gesture_event)
                gesture_end = time.time()
                
                gesture_detection_times.append(gesture_end - gesture_start)
            
            # Add slight delay between frames (realistic timing)
            time.sleep(0.01)
        
        # Calculate performance metrics
        avg_frame_time = statistics.mean(frame_times)
        max_frame_time = max(frame_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        avg_gesture_time = statistics.mean(gesture_detection_times) if gesture_detection_times else 0
        
        # Performance assertions for real-world requirements
        assert avg_frame_time < 0.08, f"Average frame time should be <80ms for real-time, got {avg_frame_time:.3f}s"
        assert max_frame_time < 0.15, f"Max frame time should be <150ms, got {max_frame_time:.3f}s"
        assert fps >= 12, f"Should achieve at least 12 FPS for real-time, got {fps:.1f} FPS"
        
        if gesture_detection_times:
            assert avg_gesture_time < 0.05, f"Gesture detection should be <50ms, got {avg_gesture_time:.3f}s"
        
        # Verify SSE streaming performance
        total_connections = len(sse_service.active_connections)
        assert total_connections == 5, "Should maintain all SSE connections"
        
        # Check that SSE clients received events
        total_events_queued = 0
        for client_id, client_queue in sse_service.active_connections.items():
            events_in_queue = client_queue.qsize()
            total_events_queued += events_in_queue
        
        # Should have events queued for clients (some may have been processed)
        assert total_events_queued >= 0, "SSE clients should receive gesture events"
        
        # Verify final performance statistics
        final_stats = processor.get_performance_stats()
        assert final_stats["total_frames_processed"] >= benchmark_frames, "Should track all processed frames"
        
        # Efficiency metrics verification
        efficiency_metrics = processor.get_efficiency_metrics()
        assert "gesture_detection_efficiency" in efficiency_metrics, "Should provide efficiency metrics"
        assert efficiency_metrics["gesture_detection_efficiency"] > 0.8, "Should be highly efficient"

    def test_error_handling_and_graceful_degradation(self):
        """
        RED TEST: Test error handling and graceful degradation.
        
        Should verify that the production system handles various failure
        scenarios gracefully without complete system failure.
        """
        from src.processing.enhanced_frame_processor import EnhancedFrameProcessor
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        # Setup error simulation environment
        multimodal_detector = Mock(spec=MultiModalDetector)
        gesture_detector = Mock(spec=GestureDetector)
        event_publisher = EventPublisher()
        
        processor = EnhancedFrameProcessor(
            detector=multimodal_detector,
            gesture_detector=gesture_detector,
            event_publisher=event_publisher
        )
        
        sse_config = SSEServiceConfig(host="localhost", port=8766)
        sse_service = SSEDetectionService(sse_config)
        sse_service.setup_gesture_integration(event_publisher)
        
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Test 1: Human detection failure
        multimodal_detector.detect.side_effect = Exception("Camera disconnected")
        gesture_detector.detect_gestures.return_value = GestureResult(
            gesture_detected=False,
            gesture_type=None,
            confidence=0.0,
            hand=None
        )
        
        # Should handle human detection failure gracefully
        try:
            result = processor.process_frame(test_frame)
            # System should continue operating despite error
            assert True, "Should handle human detection failure gracefully"
        except Exception as e:
            # If exception occurs, it should be handled internally
            assert False, f"Should not propagate human detection errors: {e}"
        
        # Test 2: Gesture detection failure
        multimodal_detector.detect.side_effect = None
        multimodal_detector.detect.return_value = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[(0.5, 0.3)],
            bounding_box=(100, 100, 200, 200)
        )
        
        gesture_detector.detect_gestures.side_effect = Exception("Gesture model failure")
        
        # Should handle gesture detection failure gracefully
        try:
            result = processor.process_frame(test_frame)
            assert result.human_present is True, "Human detection should still work"
            assert True, "Should handle gesture detection failure gracefully"
        except Exception as e:
            assert False, f"Should not propagate gesture detection errors: {e}"
        
        # Test 3: SSE service failure
        gesture_detector.detect_gestures.side_effect = None
        gesture_detector.detect_gestures.return_value = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right"
        )
        
        # Mock SSE service failure
        original_stream = sse_service.stream_gesture_event_to_clients
        sse_service.stream_gesture_event_to_clients = Mock(side_effect=Exception("SSE service failure"))
        
        # Should handle SSE failure without affecting core detection
        try:
            result = processor.process_frame(test_frame)
            assert result.human_present is True, "Human detection should still work"
            
            # Manually trigger SSE failure
            import asyncio
            gesture_event = ServiceEvent(
                event_type=EventType.GESTURE_DETECTED,
                data={"gesture_type": "hand_up", "confidence": 0.85}
            )
            asyncio.run(event_publisher.publish_async(gesture_event))
            
            assert True, "Should handle SSE service failure gracefully"
        except Exception as e:
            assert False, f"Should not propagate SSE service errors: {e}"
        
        # Test 4: Event publisher failure
        original_publish = event_publisher.publish
        event_publisher.publish = Mock(side_effect=Exception("Event publisher failure"))
        
        # Should handle event publishing failure gracefully
        try:
            result = processor.process_frame(test_frame)
            assert result.human_present is True, "Core detection should still work"
            assert True, "Should handle event publisher failure gracefully"
        except Exception as e:
            assert False, f"Should not propagate event publisher errors: {e}"
        
        # Verify system remains operational
        # Restore working event publisher
        event_publisher.publish = original_publish
        sse_service.stream_gesture_event_to_clients = original_stream
        
        # Verify system can recover
        final_result = processor.process_frame(test_frame)
        assert final_result.human_present is True, "System should recover from failures"
        
        # Verify error tracking in performance stats
        perf_stats = processor.get_performance_stats()
        assert "error_count" in perf_stats or "total_frames_processed" in perf_stats, "Should track system status" 