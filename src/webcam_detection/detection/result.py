"""
Detection result data structures.

This module defines the standardized format for human detection results
and related exceptions.
"""

import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple, Dict, Any


class DetectionError(Exception):
    """Exception raised for detection-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize detection error.
        
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
class DetectionResult:
    """
    Standardized detection result format.
    
    This dataclass represents the output of human detection algorithms,
    providing a consistent interface across different detection backends.
    """
    
    human_present: bool
    confidence: float
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    landmarks: Optional[List[Tuple[float, float]]] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        """Validate fields after initialization."""
        # Set timestamp if not provided
        if self.timestamp is None:
            self.timestamp = time.time()
        
        # Validate confidence range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        
        # Validate bounding box format
        if self.bounding_box is not None:
            self._validate_bounding_box(self.bounding_box)
        
        # Validate landmarks format
        if self.landmarks is not None:
            self._validate_landmarks(self.landmarks)
    
    def _validate_bounding_box(self, bbox: Tuple[int, int, int, int]) -> None:
        """Validate bounding box format and values."""
        if not isinstance(bbox, tuple) or len(bbox) != 4:
            raise ValueError("Bounding box must be a tuple of 4 integers")
        
        x, y, w, h = bbox
        if any(val < 0 for val in bbox):
            raise ValueError("Bounding box coordinates must be non-negative")
        
        if not all(isinstance(val, int) for val in bbox):
            # Convert to int if possible
            try:
                self.bounding_box = tuple(int(val) for val in bbox)
            except (ValueError, TypeError):
                raise ValueError("Bounding box must be a tuple of 4 integers")
    
    def _validate_landmarks(self, landmarks: List[Tuple[float, float]]) -> None:
        """Validate landmarks format and coordinate ranges."""
        if not isinstance(landmarks, list):
            raise ValueError("Landmarks must be a list of coordinate tuples")
        
        for i, landmark in enumerate(landmarks):
            if not isinstance(landmark, tuple) or len(landmark) != 2:
                raise ValueError("Landmarks must be a list of coordinate tuples")
            
            x, y = landmark
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError("Landmark coordinates must be between 0.0 and 1.0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectionResult':
        """Create DetectionResult from dictionary."""
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation of detection result."""
        return (
            f"DetectionResult(human_present={self.human_present}, "
            f"confidence={self.confidence:.3f}, "
            f"bounding_box={self.bounding_box}, "
            f"landmarks_count={len(self.landmarks) if self.landmarks else 0})"
        ) 