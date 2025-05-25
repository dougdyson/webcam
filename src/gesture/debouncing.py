"""
Gesture debouncing and smoothing mechanisms.

Implements logic to prevent false gesture triggers and provide stable
gesture detection through frame-based debouncing.
"""

from typing import Dict, List, Optional
from collections import deque
import time


class GestureDebouncer:
    """
    Gesture debouncing mechanism to prevent false triggers.
    
    Requires multiple consecutive frames of gesture detection before
    confirming a stable gesture state.
    """
    
    def __init__(self, debounce_frames: int = 3, confidence_threshold: float = 0.7):
        """
        Initialize gesture debouncer.
        
        Args:
            debounce_frames: Number of consecutive frames required for stable gesture
            confidence_threshold: Minimum confidence required for gesture consideration
        """
        self.debounce_frames = debounce_frames
        self.confidence_threshold = confidence_threshold
        
        # Track recent gesture detections per gesture type
        self._gesture_history: Dict[str, deque] = {}
        self._gesture_confirmed: Dict[str, bool] = {}
    
    def update_gesture_state(self, gesture_type: str, confidence: float) -> bool:
        """
        Update gesture state and check if gesture should be triggered.
        
        Args:
            gesture_type: Type of gesture detected
            confidence: Confidence score of detection
            
        Returns:
            True if gesture should be triggered (stable), False otherwise
        """
        # Initialize history for new gesture types
        if gesture_type not in self._gesture_history:
            self._gesture_history[gesture_type] = deque(maxlen=self.debounce_frames)
            self._gesture_confirmed[gesture_type] = False
        
        history = self._gesture_history[gesture_type]
        
        # Add current detection to history
        detection_valid = confidence >= self.confidence_threshold
        history.append(detection_valid)
        
        # Check if we have enough consecutive valid detections
        if len(history) == self.debounce_frames and all(history):
            # Gesture is stable - trigger if not already confirmed
            if not self._gesture_confirmed[gesture_type]:
                self._gesture_confirmed[gesture_type] = True
                return True
        else:
            # Gesture not stable - reset confirmation
            self._gesture_confirmed[gesture_type] = False
        
        return False
    
    def is_gesture_stable(self, gesture_type: str, confidence: float) -> bool:
        """
        Check if gesture is currently stable without updating state.
        
        Args:
            gesture_type: Type of gesture to check
            confidence: Current confidence score
            
        Returns:
            True if gesture is stable, False otherwise
        """
        if gesture_type not in self._gesture_history:
            return False
        
        history = self._gesture_history[gesture_type]
        detection_valid = confidence >= self.confidence_threshold
        
        # Check if adding this detection would make gesture stable
        temp_history = list(history) + [detection_valid]
        if len(temp_history) >= self.debounce_frames:
            return all(temp_history[-self.debounce_frames:])
        
        return False
    
    def reset_gesture(self, gesture_type: str) -> None:
        """
        Reset debouncing state for specific gesture type.
        
        Args:
            gesture_type: Gesture type to reset
        """
        if gesture_type in self._gesture_history:
            self._gesture_history[gesture_type].clear()
            self._gesture_confirmed[gesture_type] = False
    
    def reset_all(self) -> None:
        """Reset all gesture debouncing states."""
        self._gesture_history.clear()
        self._gesture_confirmed.clear()
    
    def is_gesture_confirmed(self, gesture_type: str) -> bool:
        """
        Check if gesture is currently confirmed/active.
        
        Args:
            gesture_type: Gesture type to check
            
        Returns:
            True if gesture is confirmed, False otherwise
        """
        return self._gesture_confirmed.get(gesture_type, False) 