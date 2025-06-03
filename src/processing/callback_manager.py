"""
Callback management system for frame processing events.

Extracted from LatestFrameProcessor to follow single responsibility principle.
Handles callback registration, execution, error isolation, and statistics.
"""

import asyncio
import logging
from typing import List, Callable, Dict, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class CallbackManager:
    """Manages callbacks for frame processing events with error isolation."""
    
    def __init__(self):
        """Initialize callback manager."""
        # Core callbacks
        self._result_callbacks: List[Callable] = []
        
        # Event publishing callbacks  
        self._event_callbacks: List[Callable] = []
        self._snapshot_callbacks: List[Callable] = []
        
        # Advanced event callbacks
        self._advanced_event_callbacks: List[Callable] = []
        self._confidence_event_callbacks: List[Callable] = []
        self._batch_event_callbacks: List[Callable] = []
        self._scene_change_callbacks: List[Callable] = []
        self._frequency_change_callbacks: List[Callable] = []
        self._quality_assessment_callbacks: List[Callable] = []
        self._performance_metrics_callbacks: List[Callable] = []
        self._filtered_event_callbacks: List[Callable] = []
        
        # Configuration callbacks
        self._configuration_change_callbacks: List[Callable] = []
        self._configuration_validation_callbacks: List[Callable] = []
        
        # Component swap callbacks
        self._component_swap_callbacks: List[Callable] = []
        self._camera_swap_callbacks: List[Callable] = []
        self._health_monitoring_callbacks: List[Callable] = []
        self._automatic_swap_callbacks: List[Callable] = []
        
        # Snapshot configuration
        self._snapshot_enabled = False
        self._snapshot_min_confidence = 0.8
    
    # Core callback management
    def add_result_callback(self, callback: Callable):
        """Add callback to be called with processing results."""
        self._result_callbacks.append(callback)
    
    def remove_result_callback(self, callback: Callable):
        """Remove result callback."""
        if callback in self._result_callbacks:
            self._result_callbacks.remove(callback)
    
    async def invoke_result_callbacks(self, result, statistics):
        """Invoke all result callbacks with error isolation."""
        for callback in self._result_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
                
                statistics.record_callback_success()
                    
            except Exception as e:
                logger.error(f"Error in result callback: {e}")
                statistics.record_callback_error(e, str(callback))
    
    # Event callbacks
    def add_event_callback(self, callback: Callable):
        """Add callback for structured event publishing."""
        self._event_callbacks.append(callback)
    
    def remove_event_callback(self, callback: Callable):
        """Remove event publishing callback."""
        if callback in self._event_callbacks:
            self._event_callbacks.remove(callback)
    
    async def invoke_event_callbacks(self, event_data: Dict[str, Any]):
        """Invoke event callbacks with error isolation."""
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_data)
                else:
                    callback(event_data)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
    
    # Snapshot callbacks
    def add_snapshot_callback(self, callback: Callable):
        """Add callback for snapshot triggering."""
        self._snapshot_callbacks.append(callback)
    
    def remove_snapshot_callback(self, callback: Callable):
        """Remove snapshot callback."""
        if callback in self._snapshot_callbacks:
            self._snapshot_callbacks.remove(callback)
    
    def enable_snapshot_triggering(self, min_confidence: float = 0.8):
        """Enable snapshot triggering for high-confidence detections."""
        self._snapshot_enabled = True
        self._snapshot_min_confidence = min_confidence
    
    def disable_snapshot_triggering(self):
        """Disable snapshot triggering."""
        self._snapshot_enabled = False
    
    async def trigger_snapshots(self, frame: np.ndarray, result, detection_result):
        """Trigger snapshot callbacks if conditions are met."""
        if (self._snapshot_enabled and detection_result.human_present and 
            detection_result.confidence >= self._snapshot_min_confidence):
            
            snapshot_metadata = {
                'frame_id': result.frame_id,
                'confidence': result.confidence,
                'human_present': result.human_present,
                'timestamp': result.timestamp,
                'processing_time': result.processing_time
            }
            
            for callback in self._snapshot_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(frame.copy(), snapshot_metadata)
                    else:
                        callback(frame.copy(), snapshot_metadata)
                except Exception as e:
                    logger.error(f"Error in snapshot callback: {e}")
    
    # Advanced event callbacks
    def add_advanced_event_callback(self, callback: Callable):
        """Add callback for advanced event publishing."""
        self._advanced_event_callbacks.append(callback)
    
    def remove_advanced_event_callback(self, callback: Callable):
        """Remove advanced event callback."""
        if callback in self._advanced_event_callbacks:
            self._advanced_event_callbacks.remove(callback)
    
    async def invoke_advanced_event_callbacks(self, event_data: Dict[str, Any]):
        """Invoke advanced event callbacks."""
        for callback in self._advanced_event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_data)
                else:
                    callback(event_data)
            except Exception as e:
                logger.error(f"Error in advanced event callback: {e}")
    
    # Confidence event callbacks
    def add_confidence_event_callback(self, callback: Callable):
        """Add callback for confidence-based events."""
        self._confidence_event_callbacks.append(callback)
    
    async def invoke_confidence_event_callbacks(self, event_data: Dict[str, Any]):
        """Invoke confidence event callbacks."""
        for callback in self._confidence_event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_data)
                else:
                    callback(event_data)
            except Exception as e:
                logger.error(f"Error in confidence event callback: {e}")
    
    # Batch event callbacks
    def add_batch_event_callback(self, callback: Callable):
        """Add callback for batch events."""
        self._batch_event_callbacks.append(callback)
    
    async def invoke_batch_event_callbacks(self, batch_data: Dict[str, Any]):
        """Invoke batch event callbacks."""
        for callback in self._batch_event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(batch_data)
                else:
                    callback(batch_data)
            except Exception as e:
                logger.error(f"Error in batch event callback: {e}")
    
    # Scene change callbacks
    def add_scene_change_callback(self, callback: Callable):
        """Add callback for scene change events."""
        self._scene_change_callbacks.append(callback)
    
    def invoke_scene_change_callbacks(self, event_data: Dict[str, Any]):
        """Invoke scene change callbacks."""
        for callback in self._scene_change_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in scene change callback: {e}")
    
    # Frequency change callbacks
    def add_frequency_change_callback(self, callback: Callable):
        """Add callback for frequency change events."""
        self._frequency_change_callbacks.append(callback)
    
    def invoke_frequency_change_callbacks(self, event_data: Dict[str, Any]):
        """Invoke frequency change callbacks."""
        for callback in self._frequency_change_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in frequency change callback: {e}")
    
    # Quality assessment callbacks
    def add_quality_assessment_callback(self, callback: Callable):
        """Add callback for quality assessment events."""
        self._quality_assessment_callbacks.append(callback)
    
    # Performance metrics callbacks
    def add_performance_metrics_callback(self, callback: Callable):
        """Add callback for performance metrics."""
        self._performance_metrics_callbacks.append(callback)
    
    async def invoke_performance_metrics_callbacks(self, metrics_data: Dict[str, Any]):
        """Invoke performance metrics callbacks."""
        for callback in self._performance_metrics_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(metrics_data)
                else:
                    callback(metrics_data)
            except Exception as e:
                logger.error(f"Error in performance metrics callback: {e}")
    
    # Filtered event callbacks
    def add_filtered_event_callback(self, callback: Callable):
        """Add callback for filtered events."""
        self._filtered_event_callbacks.append(callback)
    
    def invoke_filtered_event_callbacks(self, event_data: Dict[str, Any]):
        """Invoke filtered event callbacks."""
        for callback in self._filtered_event_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                logger.error(f"Error in filtered event callback: {e}")
    
    # Configuration callbacks
    def add_configuration_change_callback(self, callback: Callable):
        """Add callback for configuration change events."""
        self._configuration_change_callbacks.append(callback)
    
    def remove_configuration_change_callback(self, callback: Callable):
        """Remove configuration change callback."""
        if callback in self._configuration_change_callbacks:
            self._configuration_change_callbacks.remove(callback)
    
    def invoke_configuration_change_callbacks(self, old_config: Dict[str, Any], new_config: Dict[str, Any], reason: str):
        """Invoke configuration change callbacks."""
        for callback in self._configuration_change_callbacks:
            try:
                callback(old_config, new_config, reason)
            except Exception as e:
                logger.error(f"Error in configuration change callback: {e}")
    
    def add_configuration_validation_callback(self, callback: Callable):
        """Add callback for configuration validation events."""
        self._configuration_validation_callbacks.append(callback)
    
    def invoke_configuration_validation_callbacks(self, validation_data: Dict[str, Any]):
        """Invoke configuration validation callbacks."""
        for callback in self._configuration_validation_callbacks:
            try:
                callback(validation_data)
            except Exception as e:
                logger.error(f"Error in validation callback: {e}")
    
    # Component swap callbacks
    def add_component_swap_callback(self, callback: Callable):
        """Add callback for component swap events."""
        self._component_swap_callbacks.append(callback)
    
    def invoke_component_swap_callbacks(self, swap_event: Dict[str, Any]):
        """Invoke component swap callbacks."""
        for callback in self._component_swap_callbacks:
            try:
                callback(swap_event)
            except Exception as e:
                logger.error(f"Error in component swap callback: {e}")
    
    def add_camera_swap_callback(self, callback: Callable):
        """Add callback for camera swap events."""
        self._camera_swap_callbacks.append(callback)
    
    def invoke_camera_swap_callbacks(self, swap_event: Dict[str, Any]):
        """Invoke camera swap callbacks."""
        for callback in self._camera_swap_callbacks:
            try:
                callback(swap_event)
            except Exception as e:
                logger.error(f"Error in camera swap callback: {e}")
    
    def add_health_monitoring_callback(self, callback: Callable):
        """Add callback for health monitoring events."""
        self._health_monitoring_callbacks.append(callback)
    
    def invoke_health_monitoring_callbacks(self, health_event: Dict[str, Any]):
        """Invoke health monitoring callbacks."""
        for callback in self._health_monitoring_callbacks:
            try:
                callback(health_event)
            except Exception as e:
                logger.error(f"Error in health monitoring callback: {e}")
    
    def add_automatic_swap_callback(self, callback: Callable):
        """Add callback for automatic swap events."""
        self._automatic_swap_callbacks.append(callback)
    
    def invoke_automatic_swap_callbacks(self, auto_swap_event: Dict[str, Any]):
        """Invoke automatic swap callbacks."""
        for callback in self._automatic_swap_callbacks:
            try:
                callback(auto_swap_event)
            except Exception as e:
                logger.error(f"Error in automatic swap callback: {e}")
    
    # Dynamic callback management
    async def add_result_callback_dynamic(self, callback: Callable) -> bool:
        """Add result callback dynamically while processor is running."""
        try:
            self._result_callbacks.append(callback)
            return True
        except Exception as e:
            logger.error(f"Error adding dynamic callback: {e}")
            return False
    
    async def remove_result_callback_dynamic(self, callback: Callable) -> bool:
        """Remove result callback dynamically while processor is running."""
        try:
            if callback in self._result_callbacks:
                self._result_callbacks.remove(callback)
            return True
        except Exception as e:
            logger.error(f"Error removing dynamic callback: {e}")
            return False 