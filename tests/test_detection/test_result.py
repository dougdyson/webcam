"""
Tests for detection result data structure.

This module tests the DetectionResult dataclass which standardizes
the output format from human detection algorithms.
"""

import pytest
import time
from dataclasses import FrozenInstanceError
from typing import List, Tuple, Optional

from src.detection.result import DetectionResult, DetectionError


class TestDetectionResult:
    """Test the DetectionResult dataclass."""

    def test_detection_result_creation_basic(self):
        """Should create valid detection result with basic parameters."""
        # This will fail initially since DetectionResult doesn't exist yet
        result = DetectionResult(
            human_present=True,
            confidence=0.85
        )
        
        assert result.human_present is True
        assert result.confidence == 0.85
        assert result.timestamp is not None
        assert result.bounding_box is None
        assert result.landmarks is None

    def test_detection_result_creation_complete(self):
        """Should create detection result with all parameters."""
        landmarks = [(0.5, 0.6), (0.7, 0.8), (0.3, 0.4)]
        bounding_box = (100, 200, 150, 250)
        timestamp = time.time()
        
        result = DetectionResult(
            human_present=True,
            confidence=0.92,
            bounding_box=bounding_box,
            landmarks=landmarks,
            timestamp=timestamp
        )
        
        assert result.human_present is True
        assert result.confidence == 0.92
        assert result.bounding_box == bounding_box
        assert result.landmarks == landmarks
        assert result.timestamp == timestamp

    def test_detection_result_negative_case(self):
        """Should handle negative detection case."""
        result = DetectionResult(
            human_present=False,
            confidence=0.0
        )
        
        assert result.human_present is False
        assert result.confidence == 0.0
        assert result.bounding_box is None
        assert result.landmarks is None

    def test_detection_result_auto_timestamp(self):
        """Should automatically set timestamp if not provided."""
        start_time = time.time()
        result = DetectionResult(human_present=True, confidence=0.7)
        end_time = time.time()
        
        assert start_time <= result.timestamp <= end_time

    def test_detection_result_validates_confidence_range(self):
        """Should validate confidence is between 0.0 and 1.0."""
        # Test confidence too low
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DetectionResult(human_present=True, confidence=-0.1)
        
        # Test confidence too high
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DetectionResult(human_present=True, confidence=1.5)

    def test_detection_result_validates_confidence_edge_cases(self):
        """Should accept confidence values at valid boundaries."""
        # Test minimum valid confidence
        result_min = DetectionResult(human_present=False, confidence=0.0)
        assert result_min.confidence == 0.0
        
        # Test maximum valid confidence
        result_max = DetectionResult(human_present=True, confidence=1.0)
        assert result_max.confidence == 1.0

    def test_detection_result_validates_bounding_box_format(self):
        """Should validate bounding box format (x, y, w, h)."""
        # Valid bounding box
        result = DetectionResult(
            human_present=True, 
            confidence=0.8,
            bounding_box=(10, 20, 100, 200)
        )
        assert result.bounding_box == (10, 20, 100, 200)
        
        # Invalid bounding box - wrong length
        with pytest.raises(ValueError, match="Bounding box must be a tuple of 4 integers"):
            DetectionResult(
                human_present=True,
                confidence=0.8,
                bounding_box=(10, 20, 100)  # Missing height
            )
        
        # Invalid bounding box - negative values
        with pytest.raises(ValueError, match="Bounding box coordinates must be non-negative"):
            DetectionResult(
                human_present=True,
                confidence=0.8,
                bounding_box=(-10, 20, 100, 200)
            )

    def test_detection_result_validates_landmarks_format(self):
        """Should validate landmarks format as list of coordinate tuples."""
        # Valid landmarks
        landmarks = [(0.1, 0.2), (0.5, 0.6), (0.8, 0.9)]
        result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=landmarks
        )
        assert result.landmarks == landmarks
        
        # Invalid landmarks - wrong coordinate format
        with pytest.raises(ValueError, match="Landmarks must be a list of coordinate tuples"):
            DetectionResult(
                human_present=True,
                confidence=0.8,
                landmarks=[(0.1, 0.2), (0.5,)]  # Incomplete coordinate
            )
        
        # Invalid landmarks - coordinates out of range
        with pytest.raises(ValueError, match="Landmark coordinates must be between 0.0 and 1.0"):
            DetectionResult(
                human_present=True,
                confidence=0.8,
                landmarks=[(0.1, 0.2), (1.5, 0.6)]  # x > 1.0
            )

    def test_detection_result_empty_landmarks_list(self):
        """Should handle empty landmarks list."""
        result = DetectionResult(
            human_present=True,
            confidence=0.8,
            landmarks=[]
        )
        assert result.landmarks == []

    def test_detection_result_equality(self):
        """Should support equality comparison."""
        result1 = DetectionResult(human_present=True, confidence=0.8)
        result2 = DetectionResult(human_present=True, confidence=0.8)
        result3 = DetectionResult(human_present=False, confidence=0.3)
        
        # Same values should be equal (ignoring timestamp differences)
        assert result1.human_present == result2.human_present
        assert result1.confidence == result2.confidence
        
        # Different values should not be equal
        assert result1.human_present != result3.human_present
        assert result1.confidence != result3.confidence

    def test_detection_result_string_representation(self):
        """Should provide meaningful string representation."""
        result = DetectionResult(
            human_present=True,
            confidence=0.857,
            bounding_box=(10, 20, 100, 200)
        )
        
        str_repr = str(result)
        assert "human_present=True" in str_repr
        assert "confidence=0.857" in str_repr
        assert "bounding_box=(10, 20, 100, 200)" in str_repr

    def test_detection_result_to_dict(self):
        """Should convert to dictionary format."""
        landmarks = [(0.1, 0.2), (0.5, 0.6)]
        result = DetectionResult(
            human_present=True,
            confidence=0.9,
            bounding_box=(50, 75, 200, 300),
            landmarks=landmarks
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["human_present"] is True
        assert result_dict["confidence"] == 0.9
        assert result_dict["bounding_box"] == (50, 75, 200, 300)
        assert result_dict["landmarks"] == landmarks
        assert "timestamp" in result_dict

    def test_detection_result_from_dict(self):
        """Should create DetectionResult from dictionary."""
        data = {
            "human_present": False,
            "confidence": 0.2,
            "bounding_box": None,
            "landmarks": None,
            "timestamp": 1234567890.0
        }
        
        result = DetectionResult.from_dict(data)
        
        assert result.human_present is False
        assert result.confidence == 0.2
        assert result.bounding_box is None
        assert result.landmarks is None
        assert result.timestamp == 1234567890.0

    def test_detection_result_serialization_roundtrip(self):
        """Should maintain data integrity through serialization roundtrip."""
        original = DetectionResult(
            human_present=True,
            confidence=0.875,
            bounding_box=(25, 50, 150, 200),
            landmarks=[(0.3, 0.4), (0.7, 0.8)]
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = DetectionResult.from_dict(data)
        
        assert restored.human_present == original.human_present
        assert restored.confidence == original.confidence
        assert restored.bounding_box == original.bounding_box
        assert restored.landmarks == original.landmarks
        assert restored.timestamp == original.timestamp


class TestDetectionError:
    """Test the DetectionError exception class."""

    def test_detection_error_creation(self):
        """Should create DetectionError with message."""
        error = DetectionError("Invalid detection parameters")
        assert str(error) == "Invalid detection parameters"
        assert isinstance(error, Exception)

    def test_detection_error_with_original_error(self):
        """Should wrap original exception."""
        original = ValueError("Original error")
        error = DetectionError("Detection failed", original_error=original)
        
        assert "Detection failed" in str(error)
        assert error.original_error is original

    def test_detection_error_inheritance(self):
        """Should inherit from Exception."""
        error = DetectionError("Test error")
        assert isinstance(error, Exception)


class TestDetectionResultIntegration:
    """Integration tests for DetectionResult."""

    def test_detection_result_with_real_data_patterns(self):
        """Should handle realistic detection data patterns."""
        # High confidence detection with full data
        high_conf_result = DetectionResult(
            human_present=True,
            confidence=0.92,
            bounding_box=(120, 80, 200, 400),
            landmarks=[
                (0.5, 0.1),   # Head
                (0.4, 0.3),   # Left shoulder
                (0.6, 0.3),   # Right shoulder
                (0.45, 0.7),  # Left hip
                (0.55, 0.7),  # Right hip
            ]
        )
        
        assert high_conf_result.human_present is True
        assert high_conf_result.confidence > 0.9
        assert len(high_conf_result.landmarks) == 5

    def test_detection_result_performance_monitoring(self):
        """Should support performance monitoring use cases."""
        results = []
        
        # Simulate multiple detections
        for i in range(10):
            confidence = 0.5 + (i * 0.05)  # Increasing confidence
            result = DetectionResult(
                human_present=confidence >= 0.7,
                confidence=confidence
            )
            results.append(result)
        
        # Verify pattern
        positive_detections = [r for r in results if r.human_present]
        assert len(positive_detections) == 6  # Last 6 should be positive
        
        # Verify timestamp ordering
        timestamps = [r.timestamp for r in results]
        assert timestamps == sorted(timestamps)  # Should be chronological

    def test_detection_result_error_scenarios(self):
        """Should handle various error scenarios gracefully."""
        # Test with edge case values
        edge_cases = [
            (True, 0.0),      # Present but zero confidence
            (False, 1.0),     # Not present but high confidence (unusual)
            (True, 0.0001),   # Very low but valid confidence
            (False, 0.9999),  # Very high but valid confidence
        ]
        
        for human_present, confidence in edge_cases:
            result = DetectionResult(
                human_present=human_present,
                confidence=confidence
            )
            assert result.human_present == human_present
            assert result.confidence == confidence 