"""
Gesture duration tracking and timing mechanisms.

Implements tracking of gesture start/stop times and duration calculations
for gesture event data.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta


class GestureDurationTracker:
    """
    Tracks gesture timing and duration for active gestures.
    
    Manages start/stop times for different gesture types and calculates
    durations for gesture events.
    """
    
    def __init__(self):
        """Initialize the gesture duration tracker."""
        # Track start times for active gestures
        self._gesture_start_times: Dict[str, datetime] = {}
        # Track if gestures are currently active
        self._active_gestures: Dict[str, bool] = {}
    
    def start_gesture(self, gesture_type: str, start_time: Optional[datetime] = None) -> None:
        """
        Start tracking a gesture.
        
        Args:
            gesture_type: Type of gesture to start tracking
            start_time: Explicit start time, defaults to current time
        """
        if start_time is None:
            start_time = datetime.now()
        
        self._gesture_start_times[gesture_type] = start_time
        self._active_gestures[gesture_type] = True
    
    def stop_gesture(self, gesture_type: str, stop_time: Optional[datetime] = None) -> float:
        """
        Stop tracking a gesture and return its duration.
        
        Args:
            gesture_type: Type of gesture to stop tracking
            stop_time: Explicit stop time, defaults to current time
            
        Returns:
            Duration in milliseconds, or 0.0 if gesture wasn't being tracked
        """
        if stop_time is None:
            stop_time = datetime.now()
        
        if gesture_type not in self._gesture_start_times:
            return 0.0
        
        start_time = self._gesture_start_times[gesture_type]
        duration = (stop_time - start_time).total_seconds() * 1000  # Convert to milliseconds
        
        # Clean up tracking
        del self._gesture_start_times[gesture_type]
        self._active_gestures[gesture_type] = False
        
        return duration
    
    def get_gesture_duration(self, gesture_type: str, current_time: Optional[datetime] = None) -> float:
        """
        Get current duration of an active gesture without stopping tracking.
        
        Args:
            gesture_type: Type of gesture to check
            current_time: Current time reference, defaults to datetime.now()
            
        Returns:
            Duration in milliseconds, or 0.0 if gesture isn't active
        """
        if current_time is None:
            current_time = datetime.now()
        
        if gesture_type not in self._gesture_start_times:
            return 0.0
        
        start_time = self._gesture_start_times[gesture_type]
        duration = (current_time - start_time).total_seconds() * 1000  # Convert to milliseconds
        
        return duration
    
    def is_gesture_active(self, gesture_type: str) -> bool:
        """
        Check if a gesture is currently being tracked.
        
        Args:
            gesture_type: Type of gesture to check
            
        Returns:
            True if gesture is active, False otherwise
        """
        return self._active_gestures.get(gesture_type, False)
    
    def get_active_gestures(self) -> list:
        """
        Get list of all currently active gesture types.
        
        Returns:
            List of active gesture type names
        """
        return [gesture_type for gesture_type, active in self._active_gestures.items() if active]
    
    def reset_gesture(self, gesture_type: str) -> None:
        """
        Reset tracking for a specific gesture type.
        
        Args:
            gesture_type: Gesture type to reset
        """
        if gesture_type in self._gesture_start_times:
            del self._gesture_start_times[gesture_type]
        self._active_gestures[gesture_type] = False
    
    def reset_all(self) -> None:
        """Reset all gesture tracking."""
        self._gesture_start_times.clear()
        self._active_gestures.clear() 