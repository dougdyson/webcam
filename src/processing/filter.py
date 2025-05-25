"""
Presence filtering and smoothing functionality.

This module implements the PresenceFilter class which provides debouncing 
and smoothing algorithms to deliver stable human presence detection
results from potentially noisy detection data.
"""

import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import deque

from ..detection.result import DetectionResult


logger = logging.getLogger(__name__)


class PresenceFilterError(Exception):
    """Exception raised by presence filtering operations."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        if original_error:
            super().__init__(f"{message} (caused by: {original_error})")
        else:
            super().__init__(message)


@dataclass
class PresenceFilterConfig:
    """Configuration for presence filtering and smoothing."""
    
    smoothing_window: int = 5
    debounce_frames: int = 3
    min_confidence_threshold: float = 0.7
    enable_smoothing: bool = True
    enable_debouncing: bool = True
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.smoothing_window <= 0:
            raise ValueError("Smoothing window must be positive")
        if self.debounce_frames < 0:
            raise ValueError("Debounce frames must be non-negative")
        if not 0.0 <= self.min_confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")


class PresenceFilter:
    """
    Presence filtering with smoothing and debouncing capabilities.
    
    Provides stable human presence detection by:
    - Smoothing detection results over a sliding window
    - Debouncing state changes to prevent rapid fluctuations
    - Filtering low-confidence detections
    - Tracking statistics and performance metrics
    """
    
    def __init__(self, config: Optional[PresenceFilterConfig] = None):
        """
        Initialize presence filter.
        
        Args:
            config: Filter configuration, defaults to PresenceFilterConfig()
        """
        self.config = config or PresenceFilterConfig()
        
        # State tracking
        self.current_state = False
        self.detection_history: deque = deque(maxlen=self.config.smoothing_window)
        
        # Debouncing state
        self._consecutive_frames = 0
        self._pending_state = False
        
        # Statistics tracking
        self._detection_count = 0
        self._state_change_count = 0
        self._confidence_sum = 0.0
        self._confidence_min = float('inf')
        self._confidence_max = float('-inf')
        
        logger.info(f"PresenceFilter initialized with config: {self.config}")
    
    def add_result(self, result: DetectionResult) -> None:
        """
        Add a detection result to the filter.
        
        Args:
            result: Detection result to process
        """
        try:
            self._detection_count += 1
            
            # Apply confidence thresholding for positive detections
            effective_human_present = self._apply_confidence_threshold(result)
            
            # Create effective result for processing
            effective_result = DetectionResult(
                human_present=effective_human_present,
                confidence=result.confidence,
                bounding_box=result.bounding_box,
                landmarks=result.landmarks,
                timestamp=result.timestamp
            )
            
            # Add to history
            self.detection_history.append(effective_result)
            
            # Update confidence statistics
            self._update_confidence_statistics(result.confidence)
            
            # Update current state based on filtering strategy
            self._update_filtered_state()
            
        except Exception as e:
            raise PresenceFilterError(
                "Failed to process detection result",
                original_error=e
            )
    
    def get_filtered_presence(self) -> bool:
        """
        Get the current filtered presence state.
        
        Returns:
            True if human presence is detected after filtering, False otherwise
        """
        return self.current_state
    
    def get_detection_count(self) -> int:
        """
        Get the total number of detections processed.
        
        Returns:
            Total detection count
        """
        return self._detection_count
    
    def get_state_change_count(self) -> int:
        """
        Get the number of presence state changes.
        
        Returns:
            Number of state changes
        """
        return self._state_change_count
    
    def get_confidence_statistics(self) -> Dict[str, float]:
        """
        Get statistics about confidence scores.
        
        Returns:
            Dictionary with confidence statistics
        """
        if self._detection_count == 0:
            return {
                'count': 0,
                'mean': 0.0,
                'min': 0.0,
                'max': 0.0
            }
        
        return {
            'count': self._detection_count,
            'mean': self._confidence_sum / self._detection_count,
            'min': self._confidence_min,
            'max': self._confidence_max
        }
    
    def get_detection_history(self) -> List[DetectionResult]:
        """
        Get the recent detection history.
        
        Returns:
            List of recent detection results
        """
        return list(self.detection_history)
    
    def _apply_confidence_threshold(self, result: DetectionResult) -> bool:
        """
        Apply confidence thresholding to detection result.
        
        Args:
            result: Detection result to threshold
            
        Returns:
            Effective human presence after thresholding
        """
        # For positive detections, require confidence above threshold
        if result.human_present:
            return result.confidence >= self.config.min_confidence_threshold
        
        # For negative detections, accept regardless of confidence
        # (confidence represents detection quality, not presence/absence certainty)
        return False
    
    def _update_filtered_state(self) -> None:
        """Update the filtered presence state based on current configuration."""
        # Calculate smoothed state
        smoothed_state = self._calculate_smoothed_state()
        
        # Apply debouncing if enabled
        if self.config.enable_debouncing and self.config.debounce_frames > 0:
            new_state = self._apply_debouncing(smoothed_state)
        else:
            new_state = smoothed_state
        
        # Update state and track changes
        if new_state != self.current_state:
            self.current_state = new_state
            self._state_change_count += 1
            logger.debug(f"Presence state changed to: {new_state}")
    
    def _calculate_smoothed_state(self) -> bool:
        """
        Calculate smoothed presence state from detection history.
        
        Returns:
            Smoothed presence state
        """
        if not self.detection_history:
            return False
        
        # If smoothing is disabled, use most recent result
        if not self.config.enable_smoothing:
            return self.detection_history[-1].human_present
        
        # Special case: single detection should pass through
        if len(self.detection_history) == 1:
            return self.detection_history[0].human_present
        
        # Convert deque to list for slice operations
        history_list = list(self.detection_history)
        
        # If debounce_frames is 1, use weighted voting that's more responsive to recent changes
        if self.config.debounce_frames == 1:
            # For short sequences (<=3), be more responsive to recent changes
            if len(history_list) <= 3:
                # Give recent detection double weight
                recent_weight = 2.0
                total_weight = (len(history_list) - 1) + recent_weight
                positive_weight = sum(1 for result in history_list[:-1] if result.human_present)
                if history_list[-1].human_present:
                    positive_weight += recent_weight
                
                return positive_weight > (total_weight / 2)
            else:
                # For longer sequences, use standard majority voting
                positive_count = sum(1 for result in history_list if result.human_present)
                total_count = len(history_list)
                return positive_count > (total_count / 2)
        
        # Use majority voting for smoothed state
        positive_count = sum(1 for result in self.detection_history if result.human_present)
        total_count = len(self.detection_history)
        return positive_count > (total_count / 2)
    
    def _apply_debouncing(self, target_state: bool) -> bool:
        """
        Apply debouncing to prevent rapid state changes.
        
        Args:
            target_state: Desired state from smoothing
            
        Returns:
            Debounced state
        """
        # Special case: if debounce is disabled (0 frames), change immediately
        if self.config.debounce_frames == 0:
            return target_state
        
        # Special case: if debounce_frames is 1, allow immediate state changes
        # (1 frame means "change after 1 frame", which is immediate)
        if self.config.debounce_frames == 1:
            return target_state
        
        # Special case: for initial detection (going from False to True with no history),
        # be more permissive and allow single frame to trigger, but only if smoothing is enabled
        if (target_state is True and 
            self.current_state is False and 
            self._detection_count == 1 and
            self.config.enable_smoothing):
            return target_state
        
        # If target state matches current state, reset debounce counter
        if target_state == self.current_state:
            self._consecutive_frames = 0
            self._pending_state = target_state
            return self.current_state
        
        # If target state matches pending state, increment counter
        if target_state == self._pending_state:
            self._consecutive_frames += 1
        else:
            # New pending state, reset counter
            self._pending_state = target_state
            self._consecutive_frames = 1
        
        # Change state if we have enough consecutive frames
        if self._consecutive_frames >= self.config.debounce_frames:
            self._consecutive_frames = 0
            return self._pending_state
        
        # Not enough consecutive frames, maintain current state
        return self.current_state
    
    def _update_confidence_statistics(self, confidence: float) -> None:
        """
        Update confidence statistics with new value.
        
        Args:
            confidence: New confidence value
        """
        self._confidence_sum += confidence
        self._confidence_min = min(self._confidence_min, confidence)
        self._confidence_max = max(self._confidence_max, confidence)
    
    def reset(self) -> None:
        """Reset filter state and statistics."""
        self.current_state = False
        self.detection_history.clear()
        self._consecutive_frames = 0
        self._pending_state = False
        self._detection_count = 0
        self._state_change_count = 0
        self._confidence_sum = 0.0
        self._confidence_min = float('inf')
        self._confidence_max = float('-inf')
        
        logger.info("PresenceFilter reset")
    
    def __str__(self) -> str:
        """String representation of filter state."""
        return (
            f"PresenceFilter(state={self.current_state}, "
            f"detections={self._detection_count}, "
            f"changes={self._state_change_count})"
        )
    
    def __repr__(self) -> str:
        """Detailed representation of filter."""
        return (
            f"PresenceFilter(config={self.config}, "
            f"current_state={self.current_state}, "
            f"detection_count={self._detection_count}, "
            f"state_changes={self._state_change_count})"
        )