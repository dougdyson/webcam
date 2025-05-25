"""
Abstract base class for human detection implementations.

This module defines the interface that all human detection providers
must implement, supporting the provider pattern for multiple backends.
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Type, ClassVar

from .result import DetectionResult


class DetectorError(Exception):
    """Exception raised for detector-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize detector error.
        
        Args:
            message: Error description
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Include original error in message if provided
        if original_error:
            self.args = (f"{message} (caused by: {str(original_error)})",)


@dataclass
class DetectorConfig:
    """
    Configuration for human detection models.
    
    This dataclass standardizes configuration parameters across
    different detection backends (MediaPipe, TensorFlow, etc.).
    """
    
    model_complexity: int = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    enable_segmentation: bool = False
    static_image_mode: bool = False
    
    def __post_init__(self):
        """Validate configuration parameters."""
        # Validate model complexity (MediaPipe standard)
        if not 0 <= self.model_complexity <= 2:
            raise ValueError("Model complexity must be between 0 and 2")
        
        # Validate confidence values
        if not 0.0 <= self.min_detection_confidence <= 1.0:
            raise ValueError("Confidence values must be between 0.0 and 1.0")
        
        if not 0.0 <= self.min_tracking_confidence <= 1.0:
            raise ValueError("Confidence values must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectorConfig':
        """Create DetectorConfig from dictionary."""
        return cls(**data)
    
    def update(self, **kwargs) -> None:
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")
        
        # Re-validate after update
        self.__post_init__()


class HumanDetector(ABC):
    """
    Abstract base class for human detection implementations.
    
    This class defines the interface that all detection backends must
    implement, enabling the provider pattern for different detection
    technologies (MediaPipe, TensorFlow, PyTorch, etc.).
    """
    
    def __init__(self, config: Optional[DetectorConfig] = None):
        """
        Initialize detector with configuration.
        
        Args:
            config: Detector configuration, defaults to DetectorConfig()
        """
        self.config = config or DetectorConfig()
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Detect human presence in a frame.
        
        Args:
            frame: Input frame as numpy array (H, W, C) in BGR format
            
        Returns:
            DetectionResult with human presence information
            
        Raises:
            DetectorError: If detection fails or detector not initialized
        """
        pass
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the detection model and resources.
        
        Raises:
            DetectorError: If initialization fails
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up detector resources and close connections.
        
        Raises:
            DetectorError: If cleanup fails
        """
        pass
    
    @property
    @abstractmethod
    def is_initialized(self) -> bool:
        """
        Check if detector is properly initialized.
        
        Returns:
            True if detector is ready for detection, False otherwise
        """
        pass
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class DetectorFactory:
    """
    Factory class for creating detector instances.
    
    This implements the provider pattern, allowing registration and
    creation of different detector implementations.
    """
    
    _detectors: ClassVar[Dict[str, Type[HumanDetector]]] = {}
    
    @classmethod
    def register(cls, name: str, detector_class: Type[HumanDetector]) -> None:
        """
        Register a detector implementation.
        
        Args:
            name: Unique name for the detector (e.g., 'mediapipe', 'tensorflow')
            detector_class: Detector class that implements HumanDetector
            
        Raises:
            DetectorError: If detector_class doesn't implement HumanDetector
        """
        if not issubclass(detector_class, HumanDetector):
            raise DetectorError(
                f"Detector class {detector_class.__name__} must inherit from HumanDetector"
            )
        
        cls._detectors[name] = detector_class
    
    @classmethod
    def create(cls, name: str, config: Optional[DetectorConfig] = None) -> HumanDetector:
        """
        Create a detector instance by name.
        
        Args:
            name: Name of the detector to create
            config: Optional configuration for the detector
            
        Returns:
            Detector instance
            
        Raises:
            DetectorError: If detector name is not registered
        """
        if name not in cls._detectors:
            available = ', '.join(cls._detectors.keys())
            raise DetectorError(
                f"Unknown detector type '{name}'. Available: {available}"
            )
        
        detector_class = cls._detectors[name]
        return detector_class(config)
    
    @classmethod
    def list_available(cls) -> list[str]:
        """
        List all available detector names.
        
        Returns:
            List of registered detector names
        """
        return list(cls._detectors.keys())
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered detectors (mainly for testing)."""
        cls._detectors.clear()


# Convenience function for creating detectors
def create_detector(name: str, config: Optional[DetectorConfig] = None) -> HumanDetector:
    """
    Convenience function to create a detector.
    
    Args:
        name: Name of the detector to create
        config: Optional configuration
        
    Returns:
        Detector instance
    """
    return DetectorFactory.create(name, config) 