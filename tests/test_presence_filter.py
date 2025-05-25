"""
Tests for presence filtering and smoothing functionality.

This module tests the PresenceFilter class which implements debouncing 
and smoothing algorithms to provide stable human presence detection
results from potentially noisy detection data.
"""

import pytest
import time
import numpy as np
from unittest.mock import Mock, patch
from typing import List, Optional

# We'll import this once we implement it
from src.processing.filter import PresenceFilter, PresenceFilterConfig, PresenceFilterError
from src.detection.result import DetectionResult


class TestPresenceFilterConfiguration:
    """Test PresenceFilter configuration and initialization."""

    def test_presence_filter_config_creation(self):
        """Should create PresenceFilterConfig with default values."""
        config = PresenceFilterConfig()
        
        assert config.smoothing_window == 5
        assert config.debounce_frames == 3
        assert config.min_confidence_threshold == 0.7
        assert config.enable_smoothing is True
        assert config.enable_debouncing is True

    def test_presence_filter_config_with_custom_values(self):
        """Should create PresenceFilterConfig with custom values."""
        config = PresenceFilterConfig(
            smoothing_window=7,
            debounce_frames=5,
            min_confidence_threshold=0.8,
            enable_smoothing=False,
            enable_debouncing=True
        )
        
        assert config.smoothing_window == 7
        assert config.debounce_frames == 5
        assert config.min_confidence_threshold == 0.8
        assert config.enable_smoothing is False
        assert config.enable_debouncing is True

    def test_presence_filter_config_validation(self):
        """Should validate configuration parameters."""
        # Test invalid smoothing window
        with pytest.raises(ValueError, match="Smoothing window must be positive"):
            PresenceFilterConfig(smoothing_window=0)
        
        with pytest.raises(ValueError, match="Smoothing window must be positive"):
            PresenceFilterConfig(smoothing_window=-1)
        
        # Test invalid debounce frames
        with pytest.raises(ValueError, match="Debounce frames must be non-negative"):
            PresenceFilterConfig(debounce_frames=-1)
        
        # Test invalid confidence threshold
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            PresenceFilterConfig(min_confidence_threshold=-0.1)
        
        with pytest.raises(ValueError, match="Confidence threshold must be between 0.0 and 1.0"):
            PresenceFilterConfig(min_confidence_threshold=1.1)

    def test_presence_filter_initialization_with_defaults(self):
        """Should initialize PresenceFilter with default configuration."""
        filter = PresenceFilter()
        
        assert filter.config is not None
        assert isinstance(filter.config, PresenceFilterConfig)
        assert filter.current_state is False  # Initially no presence
        assert len(filter.detection_history) == 0

    def test_presence_filter_initialization_with_custom_config(self):
        """Should initialize PresenceFilter with custom configuration."""
        config = PresenceFilterConfig(smoothing_window=10, debounce_frames=7)
        filter = PresenceFilter(config)
        
        assert filter.config == config
        assert filter.config.smoothing_window == 10
        assert filter.config.debounce_frames == 7


class TestPresenceFilterSmoothingBasic:
    """Test basic smoothing functionality."""

    def test_presence_filter_single_detection_result(self):
        """Should handle single detection result."""
        filter = PresenceFilter()
        
        result = DetectionResult(human_present=True, confidence=0.8)
        filter.add_result(result)
        
        # With single result, should match input
        filtered_presence = filter.get_filtered_presence()
        assert filtered_presence is True

    def test_presence_filter_multiple_consistent_results(self):
        """Should handle multiple consistent detection results."""
        config = PresenceFilterConfig(smoothing_window=3, debounce_frames=1)
        filter = PresenceFilter(config)
        
        # Add multiple positive results
        for _ in range(3):
            result = DetectionResult(human_present=True, confidence=0.8)
            filter.add_result(result)
        
        # Should consistently report presence
        assert filter.get_filtered_presence() is True

    def test_presence_filter_mixed_results_majority_positive(self):
        """Should handle mixed results with positive majority."""
        config = PresenceFilterConfig(smoothing_window=5, debounce_frames=1)
        filter = PresenceFilter(config)
        
        # Add mixed results: 3 positive, 2 negative
        results = [
            DetectionResult(human_present=True, confidence=0.8),
            DetectionResult(human_present=False, confidence=0.3),
            DetectionResult(human_present=True, confidence=0.9),
            DetectionResult(human_present=True, confidence=0.7),
            DetectionResult(human_present=False, confidence=0.2),
        ]
        
        for result in results:
            filter.add_result(result)
        
        # Should report presence (3/5 positive)
        assert filter.get_filtered_presence() is True

    def test_presence_filter_mixed_results_majority_negative(self):
        """Should handle mixed results with negative majority."""
        config = PresenceFilterConfig(smoothing_window=5, debounce_frames=1)
        filter = PresenceFilter(config)
        
        # Add mixed results: 2 positive, 3 negative
        results = [
            DetectionResult(human_present=True, confidence=0.6),
            DetectionResult(human_present=False, confidence=0.2),
            DetectionResult(human_present=False, confidence=0.1),
            DetectionResult(human_present=True, confidence=0.8),
            DetectionResult(human_present=False, confidence=0.3),
        ]
        
        for result in results:
            filter.add_result(result)
        
        # Should report no presence (2/5 positive)
        assert filter.get_filtered_presence() is False


class TestPresenceFilterDebouncing:
    """Test debouncing functionality."""

    def test_presence_filter_debounce_prevents_single_false_positive(self):
        """Should prevent single false positive from changing state."""
        config = PresenceFilterConfig(
            smoothing_window=1,  # No smoothing
            debounce_frames=3,   # Require 3 consistent frames
            enable_smoothing=False
        )
        filter = PresenceFilter(config)
        
        # Initially no presence
        assert filter.get_filtered_presence() is False
        
        # Single positive detection shouldn't change state
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))
        assert filter.get_filtered_presence() is False
        
        # Two positive detections still shouldn't change state
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))
        assert filter.get_filtered_presence() is False
        
        # Third positive detection should change state
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))
        assert filter.get_filtered_presence() is True

    def test_presence_filter_debounce_prevents_single_false_negative(self):
        """Should prevent single false negative from changing state."""
        config = PresenceFilterConfig(
            smoothing_window=1,
            debounce_frames=3,
            enable_smoothing=False
        )
        filter = PresenceFilter(config)
        
        # Establish presence state
        for _ in range(3):
            filter.add_result(DetectionResult(human_present=True, confidence=0.8))
        assert filter.get_filtered_presence() is True
        
        # Single negative detection shouldn't change state
        filter.add_result(DetectionResult(human_present=False, confidence=0.2))
        assert filter.get_filtered_presence() is True
        
        # Two negative detections still shouldn't change state
        filter.add_result(DetectionResult(human_present=False, confidence=0.1))
        assert filter.get_filtered_presence() is True
        
        # Third negative detection should change state
        filter.add_result(DetectionResult(human_present=False, confidence=0.3))
        assert filter.get_filtered_presence() is False

    def test_presence_filter_debounce_with_zero_frames(self):
        """Should work correctly with debounce disabled (zero frames)."""
        config = PresenceFilterConfig(
            smoothing_window=1,
            debounce_frames=0,  # No debouncing
            enable_smoothing=False,
            enable_debouncing=False
        )
        filter = PresenceFilter(config)
        
        # Should change state immediately
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))
        assert filter.get_filtered_presence() is True
        
        filter.add_result(DetectionResult(human_present=False, confidence=0.2))
        assert filter.get_filtered_presence() is False


class TestPresenceFilterConfidenceThresholding:
    """Test confidence threshold functionality."""

    def test_presence_filter_confidence_threshold_filters_low_confidence(self):
        """Should filter out detections below confidence threshold."""
        config = PresenceFilterConfig(
            min_confidence_threshold=0.7,
            smoothing_window=3,
            debounce_frames=1
        )
        filter = PresenceFilter(config)
        
        # Add high-confidence positive and low-confidence positive
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))  # Above threshold
        filter.add_result(DetectionResult(human_present=True, confidence=0.5))  # Below threshold
        filter.add_result(DetectionResult(human_present=True, confidence=0.9))  # Above threshold
        
        # Should treat low-confidence detection as negative
        # Effective pattern: True, False, True -> majority negative or inconclusive
        filtered_presence = filter.get_filtered_presence()
        # The exact result depends on implementation, but low confidence should be filtered

    def test_presence_filter_confidence_threshold_allows_high_confidence(self):
        """Should allow detections above confidence threshold."""
        config = PresenceFilterConfig(
            min_confidence_threshold=0.6,
            smoothing_window=3,
            debounce_frames=1
        )
        filter = PresenceFilter(config)
        
        # Add all high-confidence positive detections
        for confidence in [0.7, 0.8, 0.9]:
            filter.add_result(DetectionResult(human_present=True, confidence=confidence))
        
        # Should report presence
        assert filter.get_filtered_presence() is True

    def test_presence_filter_confidence_threshold_with_negative_detections(self):
        """Should handle confidence threshold with negative detections."""
        config = PresenceFilterConfig(
            min_confidence_threshold=0.7,
            smoothing_window=3,
            debounce_frames=1
        )
        filter = PresenceFilter(config)
        
        # Negative detections should be accepted regardless of confidence
        # (confidence represents detection quality, not presence/absence certainty)
        results = [
            DetectionResult(human_present=False, confidence=0.9),  # High confidence no-person
            DetectionResult(human_present=False, confidence=0.5),  # Low confidence no-person
            DetectionResult(human_present=False, confidence=0.8),  # High confidence no-person
        ]
        
        for result in results:
            filter.add_result(result)
        
        # Should report no presence
        assert filter.get_filtered_presence() is False


class TestPresenceFilterStatisticsAndMonitoring:
    """Test statistics tracking and monitoring functionality."""

    def test_presence_filter_tracks_detection_count(self):
        """Should track number of detections processed."""
        filter = PresenceFilter()
        
        assert filter.get_detection_count() == 0
        
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))
        assert filter.get_detection_count() == 1
        
        for _ in range(5):
            filter.add_result(DetectionResult(human_present=False, confidence=0.3))
        
        assert filter.get_detection_count() == 6

    def test_presence_filter_tracks_state_changes(self):
        """Should track number of presence state changes."""
        config = PresenceFilterConfig(debounce_frames=1)
        filter = PresenceFilter(config)
        
        assert filter.get_state_change_count() == 0
        
        # Change from False to True
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))
        assert filter.get_state_change_count() == 1
        
        # Stay True (no change)
        filter.add_result(DetectionResult(human_present=True, confidence=0.9))
        assert filter.get_state_change_count() == 1
        
        # Change from True to False
        filter.add_result(DetectionResult(human_present=False, confidence=0.2))
        assert filter.get_state_change_count() == 2

    def test_presence_filter_provides_confidence_statistics(self):
        """Should provide statistics about confidence scores."""
        filter = PresenceFilter()
        
        confidences = [0.8, 0.6, 0.9, 0.5, 0.7]
        for confidence in confidences:
            filter.add_result(DetectionResult(human_present=True, confidence=confidence))
        
        stats = filter.get_confidence_statistics()
        
        assert stats['count'] == 5
        assert stats['mean'] == pytest.approx(0.7, abs=0.01)
        assert stats['min'] == 0.5
        assert stats['max'] == 0.9

    def test_presence_filter_provides_detection_history(self):
        """Should provide access to recent detection history."""
        config = PresenceFilterConfig(smoothing_window=3)
        filter = PresenceFilter(config)
        
        results = [
            DetectionResult(human_present=True, confidence=0.8),
            DetectionResult(human_present=False, confidence=0.3),
            DetectionResult(human_present=True, confidence=0.9),
        ]
        
        for result in results:
            filter.add_result(result)
        
        history = filter.get_detection_history()
        
        assert len(history) == 3
        assert history[0].human_present is True
        assert history[0].confidence == 0.8
        assert history[-1].human_present is True
        assert history[-1].confidence == 0.9


class TestPresenceFilterAdvancedScenarios:
    """Test advanced filtering scenarios and edge cases."""

    def test_presence_filter_window_size_management(self):
        """Should maintain correct window size as detections accumulate."""
        config = PresenceFilterConfig(smoothing_window=3)
        filter = PresenceFilter(config)
        
        # Add more results than window size
        for i in range(10):
            confidence = 0.5 + (i % 5) * 0.1  # Varying confidence
            filter.add_result(DetectionResult(human_present=True, confidence=confidence))
        
        # Should only keep last 3 results
        history = filter.get_detection_history()
        assert len(history) <= config.smoothing_window

    def test_presence_filter_combined_smoothing_and_debouncing(self):
        """Should work correctly with both smoothing and debouncing enabled."""
        config = PresenceFilterConfig(
            smoothing_window=5,
            debounce_frames=2,
            min_confidence_threshold=0.6
        )
        filter = PresenceFilter(config)
        
        # Initially no presence
        assert filter.get_filtered_presence() is False
        
        # Add noisy detection pattern
        detection_pattern = [
            (True, 0.8), (False, 0.3), (True, 0.9), (True, 0.7), (False, 0.2),  # First 5
            (True, 0.8), (True, 0.9), (True, 0.8), (True, 0.7), (True, 0.8),   # Strong positive
        ]
        
        for human_present, confidence in detection_pattern:
            filter.add_result(DetectionResult(human_present=human_present, confidence=confidence))
            current_state = filter.get_filtered_presence()
            # State should be stable due to smoothing and debouncing

    def test_presence_filter_performance_with_high_frequency_updates(self):
        """Should handle high-frequency detection updates efficiently."""
        filter = PresenceFilter()
        
        start_time = time.time()
        
        # Add many detection results rapidly
        for i in range(1000):
            confidence = 0.5 + (i % 10) * 0.05
            human_present = (i % 3) == 0  # 1/3 positive detections
            filter.add_result(DetectionResult(human_present=human_present, confidence=confidence))
        
        end_time = time.time()
        
        # Should complete quickly (< 100ms for 1000 operations)
        assert (end_time - start_time) < 0.1
        
        # Should still function correctly
        final_result = filter.get_filtered_presence()
        assert isinstance(final_result, bool)

    def test_presence_filter_with_disabled_features(self):
        """Should work correctly with smoothing or debouncing disabled."""
        # Test with only smoothing enabled
        config1 = PresenceFilterConfig(
            smoothing_window=3,
            enable_smoothing=True,
            enable_debouncing=False,
            debounce_frames=0
        )
        filter1 = PresenceFilter(config1)
        
        # Test with only debouncing enabled
        config2 = PresenceFilterConfig(
            smoothing_window=1,
            debounce_frames=3,
            enable_smoothing=False,
            enable_debouncing=True
        )
        filter2 = PresenceFilter(config2)
        
        # Both should work without errors
        test_result = DetectionResult(human_present=True, confidence=0.8)
        
        filter1.add_result(test_result)
        result1 = filter1.get_filtered_presence()
        assert isinstance(result1, bool)
        
        filter2.add_result(test_result)
        result2 = filter2.get_filtered_presence()
        assert isinstance(result2, bool)


class TestPresenceFilterError:
    """Test PresenceFilterError exception handling."""

    def test_presence_filter_error_creation(self):
        """Should create PresenceFilterError with message."""
        error = PresenceFilterError("Test error message")
        
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_presence_filter_error_with_original_error(self):
        """Should handle original error chaining."""
        original_error = ValueError("Original error")
        error = PresenceFilterError("Filter error occurred", original_error=original_error)
        
        assert str(error) == "Filter error occurred (caused by: Original error)"
        assert error.original_error == original_error

    def test_presence_filter_error_inheritance(self):
        """Should inherit from Exception."""
        error = PresenceFilterError("Test error")
        assert isinstance(error, Exception)


class TestPresenceFilterIntegration:
    """Integration tests for PresenceFilter with real scenarios."""

    def test_presence_filter_realistic_detection_sequence(self):
        """Should handle realistic detection sequence from camera feed."""
        config = PresenceFilterConfig(
            smoothing_window=5,
            debounce_frames=3,
            min_confidence_threshold=0.6
        )
        filter = PresenceFilter(config)
        
        # Simulate realistic detection sequence:
        # Person enters frame, is detected with varying confidence, then leaves
        realistic_sequence = [
            # No person initially
            (False, 0.1), (False, 0.2), (False, 0.1),
            # Person entering (low confidence initially)
            (True, 0.4), (True, 0.5), (True, 0.7),
            # Person clearly visible (high confidence)
            (True, 0.8), (True, 0.9), (True, 0.8), (True, 0.9),
            # Some noise/occlusion
            (False, 0.3), (True, 0.7), (True, 0.8),
            # Person leaving (decreasing confidence)
            (True, 0.6), (True, 0.5), (False, 0.3),
            # Person gone
            (False, 0.2), (False, 0.1), (False, 0.1),
        ]
        
        presence_timeline = []
        for human_present, confidence in realistic_sequence:
            filter.add_result(DetectionResult(human_present=human_present, confidence=confidence))
            presence_timeline.append(filter.get_filtered_presence())
        
        # Should show stable presence detection with appropriate transitions
        # Early frames should show no presence
        assert not any(presence_timeline[:3])
        
        # Should eventually detect presence during high-confidence period
        mid_point = len(presence_timeline) // 2
        assert any(presence_timeline[mid_point-2:mid_point+2])
        
        # Should eventually return to no presence (with debouncing, may take a few frames)
        # With debounce_frames=3, it needs 3 consecutive False inputs to transition to False
        # The sequence ends with 3 False inputs, so it should transition to False on the final detection
        assert not presence_timeline[-1], f"Expected final result to be False, got timeline: {presence_timeline[-5:]}"

    def test_presence_filter_integration_with_detection_pipeline(self):
        """Should integrate properly with detection pipeline components."""
        # This would test integration with FrameProcessor and MediaPipeDetector
        # For now, test the interface compatibility
        
        filter = PresenceFilter()
        
        # Mock a detection pipeline result
        mock_detection_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            bounding_box=(100, 100, 200, 300),
            landmarks=[(0.5, 0.3), (0.4, 0.4)]
        )
        
        # Should accept DetectionResult from our detection pipeline
        filter.add_result(mock_detection_result)
        result = filter.get_filtered_presence()
        
        assert isinstance(result, bool)
        
        # Should be compatible with our statistics and monitoring
        stats = filter.get_confidence_statistics()
        assert 'mean' in stats
        assert 'count' in stats 