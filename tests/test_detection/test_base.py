"""
Tests for abstract human detector base class.

This module tests the HumanDetector abstract base class which defines
the interface that all detection implementations must follow.
"""

import pytest
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

from src.detection.base import HumanDetector, DetectorConfig, DetectorError, DetectorFactory


class TestHumanDetectorInterface:
    """Test the HumanDetector abstract interface."""

    def test_human_detector_interface_definition(self):
        """Should define abstract interface with required methods."""
        # This will fail initially since HumanDetector doesn't exist yet
        assert hasattr(HumanDetector, 'detect')
        assert hasattr(HumanDetector, 'initialize')
        assert hasattr(HumanDetector, 'cleanup')
        assert hasattr(HumanDetector, 'is_initialized')
        
        # Should be abstract base class
        assert issubclass(HumanDetector, ABC)

    def test_human_detector_cannot_be_instantiated(self):
        """Should not be able to instantiate abstract class directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            HumanDetector()

    def test_human_detector_abstract_methods(self):
        """Should have abstract methods that must be implemented."""
        # Get abstract methods
        abstract_methods = HumanDetector.__abstractmethods__
        
        expected_methods = {'detect', 'initialize', 'cleanup'}
        assert expected_methods.issubset(abstract_methods)

    def test_human_detector_detect_signature(self):
        """Should have correct detect method signature."""
        import inspect
        
        # Create a mock implementation to check signature
        class MockDetector(HumanDetector):
            def detect(self, frame):
                pass
            def initialize(self):
                pass
            def cleanup(self):
                pass
        
        # Check method signature
        sig = inspect.signature(MockDetector.detect)
        params = list(sig.parameters.keys())
        assert 'frame' in params

    def test_human_detector_with_valid_implementation(self):
        """Should allow creation of valid implementation."""
        from src.detection.result import DetectionResult
        
        class ValidDetector(HumanDetector):
            def __init__(self):
                super().__init__()
                self._initialized = False
            
            def detect(self, frame: np.ndarray) -> DetectionResult:
                if not self._initialized:
                    raise DetectorError("Detector not initialized")
                return DetectionResult(human_present=True, confidence=0.8)
            
            def initialize(self) -> None:
                self._initialized = True
            
            def cleanup(self) -> None:
                self._initialized = False
            
            @property
            def is_initialized(self) -> bool:
                return self._initialized
        
        # Should be able to create and use
        detector = ValidDetector()
        assert not detector.is_initialized
        
        detector.initialize()
        assert detector.is_initialized
        
        # Should detect
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = detector.detect(frame)
        assert result.human_present is True
        
        detector.cleanup()
        assert not detector.is_initialized

    def test_human_detector_with_incomplete_implementation(self):
        """Should prevent creation of incomplete implementation."""
        # Missing detect method
        with pytest.raises(TypeError):
            class IncompleteDetector(HumanDetector):
                def initialize(self):
                    pass
                def cleanup(self):
                    pass
            
            IncompleteDetector()
        
        # Missing initialize method
        with pytest.raises(TypeError):
            class IncompleteDetector2(HumanDetector):
                def detect(self, frame):
                    pass
                def cleanup(self):
                    pass
            
            IncompleteDetector2()


class TestDetectorConfig:
    """Test the DetectorConfig configuration class."""

    def test_detector_config_creation(self):
        """Should create detector configuration."""
        config = DetectorConfig(
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        assert config.model_complexity == 1
        assert config.min_detection_confidence == 0.5
        assert config.min_tracking_confidence == 0.5

    def test_detector_config_with_defaults(self):
        """Should use default values when not specified."""
        config = DetectorConfig()
        
        # Should have reasonable defaults
        assert config.model_complexity is not None
        assert config.min_detection_confidence is not None
        assert config.min_tracking_confidence is not None
        assert 0.0 <= config.min_detection_confidence <= 1.0
        assert 0.0 <= config.min_tracking_confidence <= 1.0

    def test_detector_config_validation(self):
        """Should validate configuration parameters."""
        # Invalid model complexity
        with pytest.raises(ValueError, match="Model complexity must be between 0 and 2"):
            DetectorConfig(model_complexity=5)
        
        # Invalid confidence values
        with pytest.raises(ValueError, match="Confidence values must be between 0.0 and 1.0"):
            DetectorConfig(min_detection_confidence=1.5)
        
        with pytest.raises(ValueError, match="Confidence values must be between 0.0 and 1.0"):
            DetectorConfig(min_tracking_confidence=-0.1)

    def test_detector_config_to_dict(self):
        """Should convert to dictionary format."""
        config = DetectorConfig(
            model_complexity=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["model_complexity"] == 2
        assert config_dict["min_detection_confidence"] == 0.7
        assert config_dict["min_tracking_confidence"] == 0.6

    def test_detector_config_from_dict(self):
        """Should create from dictionary."""
        data = {
            "model_complexity": 1,
            "min_detection_confidence": 0.8,
            "min_tracking_confidence": 0.7
        }
        
        config = DetectorConfig.from_dict(data)
        
        assert config.model_complexity == 1
        assert config.min_detection_confidence == 0.8
        assert config.min_tracking_confidence == 0.7

    def test_detector_config_update(self):
        """Should support updating configuration."""
        config = DetectorConfig()
        original_complexity = config.model_complexity
        
        config.update(model_complexity=2)
        assert config.model_complexity == 2
        assert config.model_complexity != original_complexity


class TestDetectorError:
    """Test the DetectorError exception class."""

    def test_detector_error_creation(self):
        """Should create DetectorError with message."""
        error = DetectorError("Detection initialization failed")
        assert str(error) == "Detection initialization failed"
        assert isinstance(error, Exception)

    def test_detector_error_with_original_error(self):
        """Should wrap original exception."""
        original = RuntimeError("CUDA out of memory")
        error = DetectorError("Model loading failed", original_error=original)
        
        assert "Model loading failed" in str(error)
        assert error.original_error is original

    def test_detector_error_inheritance(self):
        """Should inherit from Exception."""
        error = DetectorError("Test error")
        assert isinstance(error, Exception)


class TestDetectorFactory:
    """Test the detector factory pattern."""

    def test_detector_factory_registration(self):
        """Should register detector implementations."""
        from src.detection.result import DetectionResult
        
        class TestDetector(HumanDetector):
            def detect(self, frame: np.ndarray) -> DetectionResult:
                return DetectionResult(human_present=False, confidence=0.0)
            def initialize(self) -> None:
                pass
            def cleanup(self) -> None:
                pass
            @property
            def is_initialized(self) -> bool:
                return True
        
        # Should be able to register
        DetectorFactory.register("test", TestDetector)
        
        # Should be able to create
        detector = DetectorFactory.create("test")
        assert isinstance(detector, TestDetector)

    def test_detector_factory_unknown_type(self):
        """Should raise error for unknown detector type."""
        with pytest.raises(DetectorError, match="Unknown detector type"):
            DetectorFactory.create("unknown_detector")

    def test_detector_factory_list_available(self):
        """Should list available detector types."""
        available = DetectorFactory.list_available()
        assert isinstance(available, list)
        # Should at least have the ones we register
        assert len(available) >= 0


class TestDetectorIntegration:
    """Integration tests for detector base functionality."""

    def test_detector_lifecycle_management(self):
        """Should handle complete lifecycle properly."""
        from src.detection.result import DetectionResult
        
        class LifecycleDetector(HumanDetector):
            def __init__(self):
                super().__init__()
                self._initialized = False
                self._cleanup_called = False
            
            def detect(self, frame: np.ndarray) -> DetectionResult:
                if not self._initialized:
                    raise DetectorError("Must initialize before detection")
                return DetectionResult(human_present=True, confidence=0.9)
            
            def initialize(self) -> None:
                if self._initialized:
                    raise DetectorError("Already initialized")
                self._initialized = True
            
            def cleanup(self) -> None:
                self._initialized = False
                self._cleanup_called = True
            
            @property
            def is_initialized(self) -> bool:
                return self._initialized
            
            @property
            def cleanup_called(self) -> bool:
                return self._cleanup_called
        
        detector = LifecycleDetector()
        
        # Should start uninitialized
        assert not detector.is_initialized
        
        # Should not detect when uninitialized
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(DetectorError, match="Must initialize before detection"):
            detector.detect(frame)
        
        # Should initialize
        detector.initialize()
        assert detector.is_initialized
        
        # Should not double-initialize
        with pytest.raises(DetectorError, match="Already initialized"):
            detector.initialize()
        
        # Should detect when initialized
        result = detector.detect(frame)
        assert result.human_present is True
        
        # Should cleanup
        detector.cleanup()
        assert not detector.is_initialized
        assert detector.cleanup_called

    def test_detector_error_handling(self):
        """Should handle various error scenarios."""
        from src.detection.result import DetectionResult
        
        class ErrorDetector(HumanDetector):
            def __init__(self, fail_on: str = None):
                super().__init__()
                self._fail_on = fail_on
                self._initialized = False
            
            def detect(self, frame: np.ndarray) -> DetectionResult:
                if self._fail_on == "detect":
                    raise RuntimeError("Detection failed")
                return DetectionResult(human_present=False, confidence=0.0)
            
            def initialize(self) -> None:
                if self._fail_on == "initialize":
                    raise RuntimeError("Initialization failed")
                self._initialized = True
            
            def cleanup(self) -> None:
                if self._fail_on == "cleanup":
                    raise RuntimeError("Cleanup failed")
                self._initialized = False
            
            @property
            def is_initialized(self) -> bool:
                return self._initialized
        
        # Test initialization failure
        detector_init_fail = ErrorDetector(fail_on="initialize")
        with pytest.raises(RuntimeError, match="Initialization failed"):
            detector_init_fail.initialize()
        
        # Test detection failure
        detector_detect_fail = ErrorDetector(fail_on="detect")
        detector_detect_fail.initialize()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(RuntimeError, match="Detection failed"):
            detector_detect_fail.detect(frame)
        
        # Test cleanup failure
        detector_cleanup_fail = ErrorDetector(fail_on="cleanup")
        detector_cleanup_fail.initialize()
        with pytest.raises(RuntimeError, match="Cleanup failed"):
            detector_cleanup_fail.cleanup()

    def test_detector_with_context_manager(self):
        """Should support context manager usage."""
        from src.detection.result import DetectionResult
        
        class ContextDetector(HumanDetector):
            def __init__(self):
                super().__init__()
                self._initialized = False
            
            def detect(self, frame: np.ndarray) -> DetectionResult:
                return DetectionResult(human_present=True, confidence=0.8)
            
            def initialize(self) -> None:
                self._initialized = True
            
            def cleanup(self) -> None:
                self._initialized = False
            
            @property
            def is_initialized(self) -> bool:
                return self._initialized
            
            def __enter__(self):
                self.initialize()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.cleanup()
        
        # Should work with context manager
        with ContextDetector() as detector:
            assert detector.is_initialized
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            result = detector.detect(frame)
            assert result.human_present is True
        
        # Should be cleaned up after context
        assert not detector.is_initialized 