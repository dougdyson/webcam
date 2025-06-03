"""
Tests for snapshot trigger logic functionality.

Phase 2.2 of TDD Ollama Description Endpoint Feature.
Following TDD methodology - RED phase: Write failing tests first.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# This import will fail initially - that's the RED phase!
try:
    from src.ollama.snapshot_trigger import (
        SnapshotTrigger,
        SnapshotTriggerConfig,
        TriggerCondition
    )
    from src.ollama.snapshot_buffer import SnapshotBuffer, Snapshot, SnapshotMetadata
    from src.detection.result import DetectionResult
except ImportError:
    # Expected to fail during RED phase
    SnapshotTrigger = None
    SnapshotTriggerConfig = None
    TriggerCondition = None
    SnapshotBuffer = None
    Snapshot = None
    SnapshotMetadata = None
    DetectionResult = None


class TestSnapshotTriggerConfiguration:
    """RED TESTS: Test SnapshotTriggerConfig for trigger logic setup."""
    
    def test_snapshot_trigger_config_defaults(self):
        """
        RED TEST: SnapshotTriggerConfig should have sensible defaults.
        
        This test will fail because SnapshotTriggerConfig doesn't exist yet.
        Expected behavior:
        - Should have default confidence threshold (e.g., 0.7)
        - Should enable human detection trigger by default
        - Should have reasonable buffer size defaults
        """
        config = SnapshotTriggerConfig()
        
        # Test default values
        assert config.min_confidence_threshold == 0.7
        assert config.trigger_on_human_detected is True
        assert config.trigger_on_human_lost is False  # Optional feature
        assert config.buffer_max_size == 10
        assert config.debounce_frames == 3  # Prevent rapid triggering
        
    def test_snapshot_trigger_config_custom_values(self):
        """
        RED TEST: SnapshotTriggerConfig should accept custom values.
        """
        config = SnapshotTriggerConfig(
            min_confidence_threshold=0.8,
            trigger_on_human_detected=True,
            buffer_max_size=5,
            debounce_frames=5
        )
        
        assert config.min_confidence_threshold == 0.8
        assert config.trigger_on_human_detected is True
        assert config.buffer_max_size == 5
        assert config.debounce_frames == 5
        
    def test_snapshot_trigger_config_validation(self):
        """
        RED TEST: SnapshotTriggerConfig should validate parameters.
        """
        # Valid configuration should work
        config = SnapshotTriggerConfig(min_confidence_threshold=0.8)
        assert config.min_confidence_threshold == 0.8
        
        # Invalid confidence should fail
        with pytest.raises(ValueError, match="min_confidence_threshold must be between 0 and 1"):
            SnapshotTriggerConfig(min_confidence_threshold=1.5)
            
        # Invalid buffer size should fail
        with pytest.raises(ValueError, match="buffer_max_size must be positive"):
            SnapshotTriggerConfig(buffer_max_size=0)


class TestSnapshotTriggerWhenHumanDetected:
    """RED TESTS: Test snapshot trigger when human_present=True."""
    
    def test_trigger_snapshot_when_human_detected(self):
        """
        RED TEST: Should trigger snapshot when human is detected.
        
        This test will fail because SnapshotTrigger doesn't exist yet.
        Expected behavior:
        - Should add snapshot to buffer when human_present=True
        - Should include detection metadata in snapshot
        - Should respect confidence threshold
        """
        config = SnapshotTriggerConfig(min_confidence_threshold=0.7, debounce_frames=0)  # Disable debouncing
        trigger = SnapshotTrigger(config)
        
        # Create frame and detection result
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:200, 100:200] = [255, 0, 0]  # Red square
        
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.85,
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        # Process detection event
        triggered = trigger.process_detection(frame, detection_result)
        
        assert triggered is True
        assert trigger.buffer.current_size == 1
        
        # Verify snapshot content
        latest = trigger.buffer.get_latest()
        assert latest is not None
        assert np.array_equal(latest.frame, frame)
        assert latest.metadata.confidence == 0.85
        assert latest.metadata.human_present is True
        
    def test_trigger_snapshot_above_confidence_threshold(self):
        """
        RED TEST: Should only trigger when confidence meets threshold.
        """
        config = SnapshotTriggerConfig(min_confidence_threshold=0.8, debounce_frames=0)  # Disable debouncing
        trigger = SnapshotTrigger(config)
        
        frame = np.zeros((320, 240, 3), dtype=np.uint8)
        
        # High confidence should trigger
        high_confidence_result = DetectionResult(
            human_present=True,
            confidence=0.9,  # Above threshold
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        triggered = trigger.process_detection(frame, high_confidence_result)
        assert triggered is True
        assert trigger.buffer.current_size == 1
        
    def test_no_trigger_below_confidence_threshold(self):
        """
        RED TEST: Should NOT trigger when confidence below threshold.
        """
        config = SnapshotTriggerConfig(min_confidence_threshold=0.8)
        trigger = SnapshotTrigger(config)
        
        frame = np.zeros((320, 240, 3), dtype=np.uint8)
        
        # Low confidence should not trigger
        low_confidence_result = DetectionResult(
            human_present=True,
            confidence=0.6,  # Below threshold
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        triggered = trigger.process_detection(frame, low_confidence_result)
        assert triggered is False
        assert trigger.buffer.current_size == 0
        
    def test_trigger_snapshot_with_detection_metadata(self):
        """
        RED TEST: Should include detection source and timing in metadata.
        """
        config = SnapshotTriggerConfig(debounce_frames=0)  # Disable debouncing
        trigger = SnapshotTrigger(config)
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        detection_time = datetime.now()
        
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.88,
            landmarks=None,
            bounding_box=None,
            timestamp=detection_time
        )
        
        triggered = trigger.process_detection(frame, detection_result)
        
        assert triggered is True
        latest = trigger.buffer.get_latest()
        assert latest.metadata.timestamp == detection_time
        assert latest.metadata.detection_source == "multimodal"  # Default


class TestSnapshotTriggerWhenNoHuman:
    """RED TESTS: Test NO snapshot when human_present=False."""
    
    def test_no_trigger_when_no_human_detected(self):
        """
        RED TEST: Should NOT trigger snapshot when human_present=False.
        
        This test will fail because conditional logic doesn't exist yet.
        Expected behavior:
        - Should not add snapshot when human_present=False
        - Should preserve buffer state
        - Should return False for triggered status
        """
        config = SnapshotTriggerConfig()
        trigger = SnapshotTrigger(config)
        
        frame = np.zeros((320, 240, 3), dtype=np.uint8)
        
        # No human detected
        no_human_result = DetectionResult(
            human_present=False,
            confidence=0.2,
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        triggered = trigger.process_detection(frame, no_human_result)
        
        assert triggered is False
        assert trigger.buffer.current_size == 0
        assert trigger.buffer.is_empty() is True
        
    def test_no_trigger_preserves_existing_snapshots(self):
        """
        RED TEST: Should preserve existing snapshots when no trigger.
        """
        config = SnapshotTriggerConfig(debounce_frames=0)  # Disable debouncing
        trigger = SnapshotTrigger(config)
        
        # Add a snapshot first
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame1[:, :, 0] = 255  # Red frame
        
        human_result = DetectionResult(
            human_present=True,
            confidence=0.9,
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        trigger.process_detection(frame1, human_result)
        assert trigger.buffer.current_size == 1
        
        # Now process no-human detection
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2[:, :, 1] = 255  # Green frame
        
        no_human_result = DetectionResult(
            human_present=False,
            confidence=0.1,
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        triggered = trigger.process_detection(frame2, no_human_result)
        
        # Should not trigger, and should preserve existing snapshot
        assert triggered is False
        assert trigger.buffer.current_size == 1
        
        # Verify original snapshot is still there
        latest = trigger.buffer.get_latest()
        assert np.array_equal(latest.frame, frame1)  # Original red frame
        
    def test_no_trigger_multiple_no_human_events(self):
        """
        RED TEST: Should handle multiple consecutive no-human events.
        """
        config = SnapshotTriggerConfig()
        trigger = SnapshotTrigger(config)
        
        frame = np.zeros((50, 50, 3), dtype=np.uint8)
        
        # Process multiple no-human detections
        for i in range(5):
            no_human_result = DetectionResult(
                human_present=False,
                confidence=0.1 + i * 0.05,  # Varying low confidence
                landmarks=None,
                bounding_box=None,
                timestamp=datetime.now()
            )
            
            triggered = trigger.process_detection(frame, no_human_result)
            assert triggered is False
            
        # Buffer should remain empty
        assert trigger.buffer.current_size == 0


class TestSnapshotTriggerDebouncing:
    """RED TESTS: Test debouncing and performance optimization."""
    
    def test_debounce_rapid_human_detection_events(self):
        """
        RED TEST: Should debounce rapid detection events.
        
        This test will fail because debouncing logic doesn't exist yet.
        Expected behavior:
        - Should not trigger snapshot for every single frame
        - Should implement debounce delay (e.g., 3 frames)
        - Should prevent buffer overflow from rapid triggers
        """
        config = SnapshotTriggerConfig(debounce_frames=3)
        trigger = SnapshotTrigger(config)
        
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        
        # Rapid human detection events
        for i in range(10):
            detection_result = DetectionResult(
                human_present=True,
                confidence=0.8,
                landmarks=None,
                bounding_box=None,
                timestamp=datetime.now()
            )
            
            triggered = trigger.process_detection(frame, detection_result)
            
            # Should not trigger every frame due to debouncing
            # Pattern: debounce_frames=3 means trigger on frames 2, 5, 8, etc.
            # (frames 0,1 are debounced, frame 2 triggers, frames 3,4 are debounced, frame 5 triggers, etc.)
            if i % 3 == 2:  # Frames 2, 5, 8 should trigger
                assert triggered is True
            else:  # Frames 0, 1, 3, 4, 6, 7, 9 should be debounced
                assert triggered is False
                
    def test_debounce_reset_after_no_human(self):
        """
        RED TEST: Should reset debounce counter when no human detected.
        """
        config = SnapshotTriggerConfig(debounce_frames=3)
        trigger = SnapshotTrigger(config)
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Start debounce cycle
        human_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        # Process 2 frames (below debounce threshold)
        trigger.process_detection(frame, human_result)
        trigger.process_detection(frame, human_result)
        
        # No human detected - should reset debounce
        no_human_result = DetectionResult(
            human_present=False,
            confidence=0.2,
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        trigger.process_detection(frame, no_human_result)
        
        # Next human detection should restart debounce cycle
        triggered = trigger.process_detection(frame, human_result)
        assert triggered is False  # Should be debounced (frame 0 of new cycle)
        
    def test_performance_avoid_unnecessary_processing(self):
        """
        RED TEST: Should optimize performance by avoiding unnecessary work.
        """
        config = SnapshotTriggerConfig()
        trigger = SnapshotTrigger(config)
        
        # Mock expensive operations to verify they're not called
        with patch.object(trigger, '_create_snapshot_metadata') as mock_metadata:
            frame = np.zeros((50, 50, 3), dtype=np.uint8)
            
            no_human_result = DetectionResult(
                human_present=False,
                confidence=0.1,
                landmarks=None,
                bounding_box=None,
                timestamp=datetime.now()
            )
            
            trigger.process_detection(frame, no_human_result)
            
            # Should not create metadata for non-triggering events
            mock_metadata.assert_not_called()


class TestSnapshotTriggerIntegration:
    """RED TESTS: Test integration with existing detection pipeline."""
    
    def test_trigger_integration_with_multimodal_detector(self):
        """
        RED TEST: Should integrate with existing MultiModalDetector results.
        
        This test will fail because integration doesn't exist yet.
        Expected behavior:
        - Should accept DetectionResult from existing detectors
        - Should work with multimodal detector output format
        - Should preserve detection metadata and timing
        """
        config = SnapshotTriggerConfig(debounce_frames=0)  # Disable debouncing
        trigger = SnapshotTrigger(config)
        
        # Simulate multimodal detector result
        frame = np.random.randint(0, 255, (640, 480, 3), dtype=np.uint8)
        
        # Realistic multimodal detection result (use None for landmarks to avoid validation)
        multimodal_result = DetectionResult(
            human_present=True,
            confidence=0.82,
            landmarks=None,  # Use None to avoid landmarks validation
            bounding_box=(100, 150, 200, 300),
            timestamp=datetime.now()
        )
        
        triggered = trigger.process_detection(frame, multimodal_result)
        
        assert triggered is True
        assert trigger.buffer.current_size == 1
        
        latest = trigger.buffer.get_latest()
        assert latest.metadata.confidence == 0.82
        assert latest.metadata.human_present is True
        
    def test_trigger_get_latest_snapshot_for_ollama(self):
        """
        RED TEST: Should provide latest snapshot for Ollama processing.
        """
        config = SnapshotTriggerConfig(debounce_frames=0)  # Disable debouncing
        trigger = SnapshotTrigger(config)
        
        # Add snapshot
        frame = np.zeros((512, 512, 3), dtype=np.uint8)
        frame[100:400, 100:400] = [128, 64, 255]  # Purple square
        
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.95,
            landmarks=None,
            bounding_box=None,
            timestamp=datetime.now()
        )
        
        trigger.process_detection(frame, detection_result)
        
        # Should be able to get latest for Ollama processing
        latest_snapshot = trigger.get_latest_snapshot()
        
        assert latest_snapshot is not None
        assert np.array_equal(latest_snapshot.frame, frame)
        assert latest_snapshot.metadata.confidence == 0.95
        
    def test_trigger_statistics_and_monitoring(self):
        """
        RED TEST: Should provide statistics for monitoring.
        """
        config = SnapshotTriggerConfig()
        trigger = SnapshotTrigger(config)
        
        # Process multiple detection events
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        
        for i in range(5):
            detection_result = DetectionResult(
                human_present=i % 2 == 0,  # Alternate human/no-human
                confidence=0.7 + i * 0.05,
                landmarks=None,
                bounding_box=None,
                timestamp=datetime.now()
            )
            
            trigger.process_detection(frame, detection_result)
            
        stats = trigger.get_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_processed' in stats
        assert 'total_triggered' in stats
        assert 'trigger_rate' in stats
        assert 'buffer_stats' in stats
        assert stats['total_processed'] == 5


# Run the tests to see them fail (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 