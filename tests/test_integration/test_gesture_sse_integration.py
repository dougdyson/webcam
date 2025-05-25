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