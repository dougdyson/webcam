"""
Snapshot trigger system for triggering snapshots when humans are detected.

This module provides intelligent triggering logic that integrates with the 
detection pipeline to capture snapshots only when humans are present with
sufficient confidence. Includes debouncing and performance optimization.

Key Features:
- Conditional snapshot triggering based on human detection
- Confidence threshold filtering
- Debouncing to prevent rapid triggers
- Performance optimization (avoid unnecessary processing)
- Integration with existing detection pipeline
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .snapshot_buffer import SnapshotBuffer, Snapshot, SnapshotMetadata
from src.detection.result import DetectionResult

logger = logging.getLogger(__name__)


@dataclass
class SnapshotTriggerConfig:
    """
    Configuration for snapshot triggering logic.
    
    Controls when and how snapshots are triggered based on 
    human detection events and confidence thresholds.
    """
    min_confidence_threshold: float = 0.7
    trigger_on_human_detected: bool = True
    trigger_on_human_lost: bool = False  # Future feature
    buffer_max_size: int = 10
    debounce_frames: int = 3
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not (0.0 <= self.min_confidence_threshold <= 1.0):
            raise ValueError("min_confidence_threshold must be between 0 and 1")
        if self.buffer_max_size <= 0:
            raise ValueError("buffer_max_size must be positive")


class TriggerCondition:
    """Helper class for evaluating trigger conditions."""
    
    @staticmethod
    def should_trigger(detection_result: DetectionResult, config: SnapshotTriggerConfig) -> bool:
        """
        Evaluate if a snapshot should be triggered based on detection result.
        
        Args:
            detection_result: Detection result from human detector
            config: Trigger configuration
            
        Returns:
            True if snapshot should be triggered
        """
        # Must have human present
        if not detection_result.human_present:
            return False
            
        # Must meet confidence threshold
        if detection_result.confidence < config.min_confidence_threshold:
            return False
            
        # Must be enabled for human detection events
        if not config.trigger_on_human_detected:
            return False
            
        return True


class SnapshotTrigger:
    """
    Main snapshot trigger system that processes detection events.
    
    Integrates with the detection pipeline to intelligently trigger
    snapshots when humans are detected with sufficient confidence.
    Includes debouncing and performance optimization.
    """
    
    def __init__(self, config: Optional[SnapshotTriggerConfig] = None):
        """
        Initialize snapshot trigger with configuration.
        
        Args:
            config: Trigger configuration, uses defaults if None
        """
        self.config = config or SnapshotTriggerConfig()
        self.buffer = SnapshotBuffer(max_size=self.config.buffer_max_size)
        
        # Debouncing state
        self._debounce_counter = 0
        self._last_human_detected = False
        
        # Statistics
        self._stats = {
            'total_processed': 0,
            'total_triggered': 0,
            'total_debounced': 0
        }
        
        logger.debug(f"SnapshotTrigger initialized with config: {self.config}")
    
    def process_detection(self, frame, detection_result: DetectionResult) -> bool:
        """
        Process a detection event and potentially trigger a snapshot.
        
        Args:
            frame: Webcam frame (numpy array)
            detection_result: Detection result from human detector
            
        Returns:
            True if snapshot was triggered and added
        """
        self._stats['total_processed'] += 1
        
        # Check if we should trigger
        should_trigger = TriggerCondition.should_trigger(detection_result, self.config)
        
        # Handle debouncing logic
        if should_trigger:
            # Apply debouncing for human detection events
            if self._should_debounce():
                self._stats['total_debounced'] += 1
                return False
                
            # Create and add snapshot
            snapshot = self._create_snapshot(frame, detection_result)
            success = self.buffer.add_snapshot(snapshot)
            
            if success:
                self._stats['total_triggered'] += 1
                logger.debug(f"Snapshot triggered: confidence={detection_result.confidence:.2f}")
                
            self._last_human_detected = True
            return success
            
        else:
            # Reset debounce when no human detected
            if not detection_result.human_present:
                # Always reset debounce when no human present
                self._reset_debounce()
                self._last_human_detected = False
                
            return False
    
    def _should_debounce(self) -> bool:
        """Check if current trigger should be debounced."""
        if self.config.debounce_frames <= 0:
            return False
            
        self._debounce_counter += 1
        
        # If we haven't reached the debounce threshold, debounce (don't trigger)
        if self._debounce_counter < self.config.debounce_frames:
            return True
            
        # Reset counter after successful trigger period
        self._debounce_counter = 0
        return False
    
    def _reset_debounce(self):
        """Reset debounce counter."""
        self._debounce_counter = 0
        logger.debug("Debounce counter reset")
    
    def _create_snapshot(self, frame, detection_result: DetectionResult) -> Snapshot:
        """Create snapshot from frame and detection result."""
        metadata = self._create_snapshot_metadata(detection_result)
        return Snapshot(frame=frame, metadata=metadata)
    
    def _create_snapshot_metadata(self, detection_result: DetectionResult) -> SnapshotMetadata:
        """Create snapshot metadata from detection result."""
        return SnapshotMetadata(
            timestamp=detection_result.timestamp or datetime.now(),
            confidence=detection_result.confidence,
            human_present=detection_result.human_present,
            detection_source="multimodal"  # Default, could be configurable
        )
    
    def get_latest_snapshot(self) -> Optional[Snapshot]:
        """
        Get the most recent snapshot for Ollama processing.
        
        Returns:
            Latest snapshot or None if buffer is empty
        """
        return self.buffer.get_latest()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get trigger statistics for monitoring.
        
        Returns:
            Dictionary with trigger statistics
        """
        stats = self._stats.copy()
        
        # Calculate derived statistics
        if stats['total_processed'] > 0:
            stats['trigger_rate'] = stats['total_triggered'] / stats['total_processed']
            stats['debounce_rate'] = stats['total_debounced'] / stats['total_processed']
        else:
            stats['trigger_rate'] = 0.0
            stats['debounce_rate'] = 0.0
            
        # Include buffer statistics
        stats['buffer_stats'] = self.buffer.get_statistics()
        
        return stats
    
    def clear_buffer(self):
        """Clear all snapshots from buffer."""
        self.buffer.clear()
        logger.debug("Snapshot trigger buffer cleared")
    
    def __repr__(self) -> str:
        """String representation of trigger state."""
        return (f"SnapshotTrigger(buffer_size={self.buffer.current_size}, "
                f"triggered={self._stats['total_triggered']}, "
                f"processed={self._stats['total_processed']})") 