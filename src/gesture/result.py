"""
Gesture recognition result dataclasses.

Result objects for gesture detection and hand detection operations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from datetime import datetime
import time


@dataclass
class HandDetectionResult:
    """
    Result of hand detection operation using MediaPipe hands.
    
    Contains information about detected hands, their landmarks, and metadata.
    """
    hands_detected: bool
    num_hands: int
    hand_landmarks: List[Any] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Validate the result after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.num_hands < 0:
            raise ValueError("Number of hands cannot be negative")
        if self.hands_detected and self.num_hands == 0:
            raise ValueError("If hands_detected is True, num_hands must be greater than 0")
        if len(self.hand_landmarks) != self.num_hands:
            raise ValueError("Length of hand_landmarks must match num_hands")


@dataclass
class GestureResult:
    """
    Result of gesture classification and detection.
    
    Contains information about detected gestures, confidence, and metadata.
    """
    gesture_detected: bool
    gesture_type: Optional[str] = None
    confidence: float = 0.0
    hand: Optional[str] = None  # "left", "right", "both"
    position: Optional[Dict[str, float]] = None
    palm_facing_camera: bool = False
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate the result after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.gesture_detected and self.gesture_type is None:
            raise ValueError("If gesture_detected is True, gesture_type must be specified")
        if self.hand is not None and self.hand not in ["left", "right", "both"]:
            raise ValueError("Hand must be 'left', 'right', 'both', or None")
        if self.duration_ms < 0:
            raise ValueError("Duration cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            'gesture_detected': self.gesture_detected,
            'gesture_type': self.gesture_type,
            'confidence': self.confidence,
            'hand': self.hand,
            'position': self.position,
            'palm_facing_camera': self.palm_facing_camera,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_service_event(self) -> 'ServiceEvent':
        """
        Convert GestureResult to ServiceEvent for event publishing.
        
        Returns:
            ServiceEvent with GESTURE_DETECTED type and gesture data
        """
        from ..service.events import ServiceEvent, EventType
        
        return ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data=self.to_dict(),
            timestamp=self.timestamp
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GestureResult':
        """Create GestureResult from dictionary."""
        # Parse timestamp if it's a string
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            gesture_detected=data['gesture_detected'],
            gesture_type=data.get('gesture_type'),
            confidence=data.get('confidence', 0.0),
            hand=data.get('hand'),
            position=data.get('position'),
            palm_facing_camera=data.get('palm_facing_camera', False),
            duration_ms=data.get('duration_ms', 0.0),
            timestamp=timestamp
        ) 