"""
Gesture detection configuration management.

Provides configuration classes and validation for gesture detection parameters.
"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class GestureConfig:
    """Configuration for gesture detection."""
    
    # Detection parameters
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.5
    model_complexity: int = 1
    max_num_hands: int = 2
    
    # Hand up gesture specific
    shoulder_offset_threshold: float = 0.1  # Hand must be 10% above shoulder
    palm_facing_confidence: float = 0.7
    
    # Debouncing and timing
    debounce_frames: int = 3
    gesture_timeout_ms: int = 5000
    
    # Performance
    enable_performance_monitoring: bool = True
    
    def __post_init__(self):
        """Validate configuration values."""
        if not 0.0 <= self.min_detection_confidence <= 1.0:
            raise ValueError("min_detection_confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= self.min_tracking_confidence <= 1.0:
            raise ValueError("min_tracking_confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= self.palm_facing_confidence <= 1.0:
            raise ValueError("palm_facing_confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= self.shoulder_offset_threshold <= 1.0:
            raise ValueError("shoulder_offset_threshold must be between 0.0 and 1.0")
        
        if self.model_complexity not in [0, 1, 2]:
            raise ValueError("model_complexity must be 0, 1, or 2")
        
        if self.max_num_hands < 1:
            raise ValueError("max_num_hands must be at least 1")
        
        if self.debounce_frames < 0:
            raise ValueError("debounce_frames must be non-negative")
        
        if self.gesture_timeout_ms <= 0:
            raise ValueError("gesture_timeout_ms must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "min_detection_confidence": self.min_detection_confidence,
            "min_tracking_confidence": self.min_tracking_confidence,
            "model_complexity": self.model_complexity,
            "max_num_hands": self.max_num_hands,
            "shoulder_offset_threshold": self.shoulder_offset_threshold,
            "palm_facing_confidence": self.palm_facing_confidence,
            "debounce_frames": self.debounce_frames,
            "gesture_timeout_ms": self.gesture_timeout_ms,
            "enable_performance_monitoring": self.enable_performance_monitoring
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'GestureConfig':
        """Create config from dictionary."""
        return cls(**config_dict)
    
    @classmethod
    def validate_configuration(cls, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dictionary and return validation result."""
        errors = []
        
        try:
            # Try to create config to trigger validation
            cls.from_dict(config_dict)
            return {"is_valid": True, "errors": []}
        except (ValueError, TypeError) as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
        
        return {"is_valid": False, "errors": errors}


# Default configurations for different use cases
DEFAULT_CONFIGS = {
    "high_accuracy": GestureConfig(
        min_detection_confidence=0.8,
        min_tracking_confidence=0.7,
        model_complexity=2,
        debounce_frames=5,
        palm_facing_confidence=0.8
    ),
    
    "balanced": GestureConfig(
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
        model_complexity=1,
        debounce_frames=3,
        palm_facing_confidence=0.7
    ),
    
    "fast_response": GestureConfig(
        min_detection_confidence=0.6,
        min_tracking_confidence=0.4,
        model_complexity=0,
        debounce_frames=1,
        palm_facing_confidence=0.6
    )
}


def get_default_config(profile: str = "balanced") -> GestureConfig:
    """Get a default configuration profile."""
    if profile not in DEFAULT_CONFIGS:
        available = ", ".join(DEFAULT_CONFIGS.keys())
        raise ValueError(f"Unknown profile '{profile}'. Available: {available}")
    
    return DEFAULT_CONFIGS[profile] 