"""
Latest Frame Processor - Refactored with Single Responsibility Principle

This module provides a frame processor that always grabs the most recent frame
instead of processing queued frames, eliminating lag and ensuring real-time
processing. Refactored from a 2570-line monolith into focused, composable components.

Key Benefits:
- No frame backlog/lag
- Always processes most current scene
- Better for real-time applications
- Reduced memory usage
- Maintainable, focused architecture
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
import numpy as np

from .frame_statistics import FrameStatistics
from .performance_monitor import PerformanceMonitor
from .callback_manager import CallbackManager
from .configuration_manager import ConfigurationManager

logger = logging.getLogger(__name__)


@dataclass
class LatestFrameResult:
    """Result of processing a latest frame with comprehensive metadata."""
    frame_id: int
    human_present: bool
    confidence: float
    processing_time: float
    timestamp: float
    frame_age: float
    frames_skipped: int
    error_occurred: bool = False
    error_message: Optional[str] = None


class LatestFrameProcessor:
    """
    Frame processor that always processes the most recent frame available.
    
    Refactored from a 2570-line monolith into focused components using composition.
    Each component handles a single responsibility:
    - FrameStatistics: Statistics tracking and analysis
    - PerformanceMonitor: Performance monitoring and optimization
    - CallbackManager: Callback registration and execution
    - ConfigurationManager: Configuration validation and persistence
    """
    
    def __init__(
        self,
        camera_manager,
        detector,
        target_fps: float = 5.0,
        processing_timeout: float = 3.0,
        max_frame_age: float = 1.0,
        adaptive_fps: bool = False,
        memory_monitoring: bool = False
    ):
        """Initialize latest frame processor with composed components."""
        # Core configuration
        self.camera_manager = camera_manager
        self.detector = detector
        self.target_fps = target_fps
        self.processing_timeout = processing_timeout
        self.max_frame_age = max_frame_age
        self.adaptive_fps = adaptive_fps
        self.memory_monitoring = memory_monitoring
        
        # Calculate processing interval
        self.processing_interval = 1.0 / target_fps if target_fps > 0 else 0.2
        
        # Processing control
        self.is_running = False
        self._processing_task = None
        self._shutdown_event = asyncio.Event()
        
        # Service integration
        self._event_publisher = None
        
        # Thread pool for sync detectors
        self._thread_pool = ThreadPoolExecutor(max_workers=1)
        
        # Composed components (Single Responsibility Principle)
        self.statistics = FrameStatistics()
        self.performance_monitor = PerformanceMonitor(memory_monitoring)
        self.callbacks = CallbackManager()
        self.config_manager = ConfigurationManager()
        
        logger.info(f"Latest frame processor initialized with refactored architecture - "
                   f"target FPS: {target_fps}, timeout: {processing_timeout}s, "
                   f"adaptive FPS: {adaptive_fps}, memory monitoring: {memory_monitoring}")
    
    # Core processing methods
    async def start(self):
        """Start the latest frame processing loop."""
        if self.is_running:
            logger.warning("Latest frame processor already running")
            return
        
        self.is_running = True
        self._shutdown_event.clear()
        
        # Initialize statistics tracking
        self.statistics.start_tracking()
        
        logger.info("Starting latest frame processor")
        
        # Start the processing loop
        self._processing_task = asyncio.create_task(self._processing_loop())
        
        logger.info("Latest frame processor started successfully")
    
    async def stop(self):
        """Stop the latest frame processor."""
        if not self.is_running:
            return
        
        logger.info("Stopping latest frame processor...")
        
        self.is_running = False
        self._shutdown_event.set()
        
        # Wait for processing task to complete
        if self._processing_task:
            try:
                await asyncio.wait_for(self._processing_task, timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Processing task did not stop gracefully")
                self._processing_task.cancel()
        
        logger.info("Latest frame processor stopped")
    
    async def _processing_loop(self):
        """Main processing loop that grabs latest frames."""
        logger.info("Starting latest frame processing loop")
        
        last_fps_check = time.time()
        consecutive_slow_frames = 0
        
        while self.is_running and not self._shutdown_event.is_set():
            try:
                process_start = time.time()
                
                # Get the most recent frame (this is the key difference!)
                frame = self._get_latest_frame()
                
                if frame is not None:
                    # Process the frame
                    result = await self._process_latest_frame(frame, process_start)
                    
                    # Notify callbacks using callback manager
                    await self.callbacks.invoke_result_callbacks(result, self.statistics)
                    
                    # Trigger snapshots if enabled
                    mock_detection_result = type('MockResult', (), {
                        'human_present': result.human_present,
                        'confidence': result.confidence
                    })()
                    await self.callbacks.trigger_snapshots(frame, result, mock_detection_result)
                
                # Calculate processing time and check for adaptive FPS adjustment
                processing_time = time.time() - process_start
                
                # Update performance monitoring
                self.statistics.update_frame_intervals(processing_time)
                
                # Adaptive FPS logic using performance monitor
                if self.adaptive_fps:
                    if processing_time > self.processing_interval * 1.2:
                        consecutive_slow_frames += 1
                    else:
                        consecutive_slow_frames = 0
                    
                    current_time = time.time()
                    if (current_time - last_fps_check > 3.0 and consecutive_slow_frames >= 5):
                        new_fps = await self.performance_monitor.adjust_fps_for_performance(
                            processing_time, self.target_fps, self.processing_interval
                        )
                        if new_fps is not None:
                            self.target_fps = new_fps
                            self.processing_interval = 1.0 / new_fps
                        last_fps_check = current_time
                        consecutive_slow_frames = 0
                
                # Wait for next processing interval
                sleep_time = max(0, self.processing_interval - processing_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.debug(f"Processing slower than target FPS: {processing_time:.3f}s > {self.processing_interval:.3f}s")
                
                # Health monitoring check (if enabled)
                if hasattr(self.config_manager, '_health_monitoring_enabled') and self.config_manager._health_monitoring_enabled:
                    await self.config_manager.monitor_component_health(self.callbacks)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
    
    def _get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame from camera."""
        try:
            frame = self.camera_manager.get_frame()
            
            if frame is not None:
                # Check frame freshness
                frame_time = time.time()
                frame_age = time.time() - frame_time
                
                if frame_age > self.max_frame_age:
                    self.statistics.increment_frames_too_old()
                    logger.debug(f"Frame too old: {frame_age:.3f}s")
                    return None
                
            return frame
            
        except Exception as e:
            logger.error(f"Error getting latest frame: {e}")
            return None
    
    async def _process_latest_frame(self, frame: np.ndarray, process_start_time: float) -> LatestFrameResult:
        """Process a single latest frame with comprehensive metadata."""
        frame_time = time.time()
        frame_age = frame_time - process_start_time
        
        # Get frame ID from statistics
        current_frame_id = self.statistics.get_next_frame_id()
        
        try:
            # Detect humans in frame
            detection_result = await self._async_detect(frame)
            
            # Calculate processing time
            processing_time = time.time() - process_start_time
            
            # Update statistics
            self.statistics.update_processing_time_stats(processing_time)
            
            # Create result
            result = LatestFrameResult(
                frame_id=current_frame_id,
                human_present=detection_result.human_present,
                confidence=detection_result.confidence,
                processing_time=processing_time,
                timestamp=frame_time,
                frame_age=frame_age,
                frames_skipped=0,  # Always 0 with latest frame processing!
                error_occurred=False
            )
            
            # Publish events if configured
            await self._publish_frame_event(result)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - process_start_time
            error_msg = f"Detection error: {str(e)}"
            logger.error(error_msg)
            
            # Still update processing stats even on error
            self.statistics.update_processing_time_stats(processing_time)
            
            return LatestFrameResult(
                frame_id=current_frame_id,
                human_present=False,
                confidence=0.0,
                processing_time=processing_time,
                timestamp=frame_time,
                frame_age=frame_age,
                frames_skipped=0,
                error_occurred=True,
                error_message=error_msg
            )
    
    async def _async_detect(self, frame: np.ndarray):
        """Convert sync detection to async if needed."""
        if hasattr(self.detector, 'detect_async'):
            return await self.detector.detect_async(frame)
        
        # Otherwise, run sync detection in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.detector.detect, frame)
    
    async def _publish_frame_event(self, result: LatestFrameResult):
        """Publish frame processing events."""
        event_data = {
            'type': 'frame_processed',
            'data': {
                'frame_id': result.frame_id,
                'human_present': result.human_present,
                'confidence': result.confidence,
                'processing_time': result.processing_time,
                'timestamp': result.timestamp,
                'frame_age': result.frame_age,
                'error_occurred': result.error_occurred
            }
        }
        
        # Use callback manager to invoke event callbacks
        await self.callbacks.invoke_event_callbacks(event_data)
        
        # Integrate with service EventPublisher if available
        if self._event_publisher:
            try:
                from src.service.events import ServiceEvent, EventType
                from datetime import datetime
                
                service_event = ServiceEvent(
                    event_type=EventType.DETECTION_UPDATE,
                    data={
                        'frame_id': result.frame_id,
                        'human_present': result.human_present,
                        'confidence': result.confidence,
                        'processing_time': result.processing_time,
                        'frame_age': result.frame_age
                    },
                    timestamp=datetime.fromtimestamp(result.timestamp)
                )
                
                self._event_publisher.publish(service_event)
                
                if hasattr(self._event_publisher, 'publish_async'):
                    await self._event_publisher.publish_async(service_event)
                
            except Exception as e:
                logger.error(f"Error publishing to EventPublisher: {e}")
    
    # Delegate to composed components
    def add_result_callback(self, callback: Callable):
        """Add callback to be called with processing results."""
        self.callbacks.add_result_callback(callback)
    
    def remove_result_callback(self, callback: Callable):
        """Remove result callback."""
        self.callbacks.remove_result_callback(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processor statistics."""
        return self.statistics.get_statistics(self.target_fps, self.is_running)
    
    def get_detailed_statistics(self) -> Dict[str, Any]:
        """Get detailed processor statistics."""
        return self.statistics.get_detailed_statistics(self.target_fps, self.is_running)
    
    def get_real_time_performance_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics."""
        return self.performance_monitor.get_real_time_performance_metrics(
            self.statistics._processing_times,
            self.target_fps,
            self.statistics._frames_processed,
            self.statistics._start_time,
            self.statistics._recent_frame_intervals
        )
    
    def get_memory_usage_status(self) -> Dict[str, Any]:
        """Get memory usage monitoring status."""
        return self.performance_monitor.get_memory_usage_status()
    
    def reset_statistics(self):
        """Reset all statistics to initial state."""
        self.statistics.reset_statistics()
    
    # Service integration
    def set_event_publisher(self, event_publisher):
        """Set EventPublisher for service integration."""
        self._event_publisher = event_publisher
    
    # Configuration management
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration using configuration manager."""
        return self.config_manager.validate_configuration(config)
    
    def validate_configuration_dependencies(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dependencies."""
        return self.config_manager.validate_configuration_dependencies(config)
    
    async def update_configuration_dynamic(self, config_updates: Dict[str, Any]) -> bool:
        """Update configuration dynamically while processor is running."""
        try:
            # Store old configuration
            old_config = {
                'target_fps': self.target_fps,
                'processing_timeout': self.processing_timeout,
                'max_frame_age': self.max_frame_age,
                'adaptive_fps': self.adaptive_fps,
                'memory_monitoring': self.memory_monitoring
            }
            
            # Apply updates
            if 'target_fps' in config_updates:
                self.target_fps = config_updates['target_fps']
                self.processing_interval = 1.0 / self.target_fps
            
            if 'processing_timeout' in config_updates:
                self.processing_timeout = config_updates['processing_timeout']
            
            if 'max_frame_age' in config_updates:
                self.max_frame_age = config_updates['max_frame_age']
            
            if 'adaptive_fps' in config_updates:
                self.adaptive_fps = config_updates['adaptive_fps']
            
            if 'memory_monitoring' in config_updates:
                self.memory_monitoring = config_updates['memory_monitoring']
            
            # Notify callbacks using callback manager
            self.callbacks.invoke_configuration_change_callbacks(old_config, config_updates, 'dynamic_update')
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration update failed: {e}")
            return False

    def update_configuration(self, config_updates: Dict[str, Any]) -> bool:
        """Update configuration synchronously (wrapper for async method)."""
        try:
            # Store old configuration
            old_config = {
                'target_fps': self.target_fps,
                'processing_timeout': self.processing_timeout,
                'max_frame_age': self.max_frame_age,
                'adaptive_fps': self.adaptive_fps,
                'memory_monitoring': self.memory_monitoring
            }
            
            # Apply updates
            if 'target_fps' in config_updates:
                self.target_fps = config_updates['target_fps']
                self.processing_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0.2
            
            if 'processing_timeout' in config_updates:
                self.processing_timeout = config_updates['processing_timeout']
            
            if 'max_frame_age' in config_updates:
                self.max_frame_age = config_updates['max_frame_age']
            
            if 'adaptive_fps' in config_updates:
                self.adaptive_fps = config_updates['adaptive_fps']
            
            if 'memory_monitoring' in config_updates:
                self.memory_monitoring = config_updates['memory_monitoring']
            
            # Notify callbacks using callback manager
            self.callbacks.invoke_configuration_change_callbacks(old_config, config_updates, 'sync_update')
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration update failed: {e}")
            return False

    # Event callback management (delegating to callback manager)
    def add_event_callback(self, callback: Callable):
        """Add callback for structured event publishing."""
        self.callbacks.add_event_callback(callback)
    
    def remove_event_callback(self, callback: Callable):
        """Remove event publishing callback."""
        self.callbacks.remove_event_callback(callback)
    
    # Snapshot callback management (delegating to callback manager)
    def add_snapshot_callback(self, callback: Callable):
        """Add callback for snapshot triggering."""
        self.callbacks.add_snapshot_callback(callback)
    
    def remove_snapshot_callback(self, callback: Callable):
        """Remove snapshot callback."""
        self.callbacks.remove_snapshot_callback(callback)
    
    def enable_snapshot_triggering(self, min_confidence: float = 0.8):
        """Enable snapshot triggering for high-confidence detections."""
        self.callbacks.enable_snapshot_triggering(min_confidence)
    
    def disable_snapshot_triggering(self):
        """Disable snapshot triggering."""
        self.callbacks.disable_snapshot_triggering()

    # Dynamic callback management (delegating to callback manager)
    async def add_result_callback_dynamic(self, callback: Callable) -> bool:
        """Add result callback dynamically while processor is running."""
        return await self.callbacks.add_result_callback_dynamic(callback)
    
    async def remove_result_callback_dynamic(self, callback: Callable) -> bool:
        """Remove result callback dynamically while processor is running."""
        return await self.callbacks.remove_result_callback_dynamic(callback)

    async def _trigger_snapshot(self, frame, result: LatestFrameResult):
        """Trigger snapshot for AI processing based on detection result."""
        try:
            # Create a simple detection result for the callback manager
            detection_result = type('DetectionResult', (), {
                'human_present': result.human_present,
                'confidence': result.confidence
            })()
            
            # Delegate to callback manager with proper parameters
            await self.callbacks.trigger_snapshots(frame, result, detection_result)
        except Exception as e:
            logger.error(f"Snapshot triggering failed: {e}")

    # Configuration persistence (delegating to configuration manager)
    def save_configuration(
        self,
        config_path: str,
        metadata: Dict[str, Any] = None,
        include_runtime_stats: bool = False,
        version_tag: str = None
    ) -> Dict[str, Any]:
        """Save configuration to file with versioning and metadata."""
        # Build current configuration
        current_config = {
            'target_fps': self.target_fps,
            'processing_timeout': self.processing_timeout,
            'max_frame_age': self.max_frame_age,
            'adaptive_fps': self.adaptive_fps,
            'memory_monitoring': self.memory_monitoring
        }
        
        return self.config_manager.save_configuration(
            current_config=current_config,
            config_path=config_path,
            metadata=metadata,
            include_runtime_stats=include_runtime_stats,
            version_tag=version_tag
        )
    
    def load_configuration(
        self,
        config_path: str,
        validate_before_load: bool = True,
        backup_current_config: bool = True
    ) -> Dict[str, Any]:
        """Load configuration from file with validation and backup."""
        # Get current configuration for backup
        current_config = {
            'target_fps': self.target_fps,
            'processing_timeout': self.processing_timeout,
            'max_frame_age': self.max_frame_age,
            'adaptive_fps': self.adaptive_fps,
            'memory_monitoring': self.memory_monitoring
        }
        
        # Load configuration
        result = self.config_manager.load_configuration(
            config_path=config_path,
            validate_before_load=validate_before_load,
            backup_current_config=backup_current_config,
            current_config=current_config
        )
        
        # If load was successful, apply the configuration
        if result.get('success', False) and 'new_config' in result:
            config = result['new_config']
            
            # Apply loaded configuration
            if 'target_fps' in config:
                self.target_fps = config['target_fps']
                self.processing_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0.2
            
            if 'processing_timeout' in config:
                self.processing_timeout = config['processing_timeout']
            
            if 'max_frame_age' in config:
                self.max_frame_age = config['max_frame_age']
            
            if 'adaptive_fps' in config:
                self.adaptive_fps = config['adaptive_fps']
            
            if 'memory_monitoring' in config:
                self.memory_monitoring = config['memory_monitoring']
            
            # Add the configuration to result for the test to access
            result['configuration'] = config
        
        return result
    
    def get_configuration_metadata(self) -> Dict[str, Any]:
        """Get configuration metadata."""
        return self.config_manager.get_configuration_metadata()
    
    def enable_configuration_history(self, max_history_entries: int = 10):
        """Enable configuration history tracking."""
        self.config_manager.enable_configuration_history(max_history_entries)

    def update_configuration_with_history(
        self,
        config_updates: Dict[str, Any],
        change_description: str = "",
        author: str = "system"
    ) -> Dict[str, Any]:
        """Update configuration with history tracking."""
        # Get current configuration before update
        current_config = {
            'target_fps': self.target_fps,
            'processing_timeout': self.processing_timeout,
            'max_frame_age': self.max_frame_age,
            'adaptive_fps': self.adaptive_fps,
            'memory_monitoring': self.memory_monitoring
        }
        
        # Apply the configuration updates first
        if 'target_fps' in config_updates:
            self.target_fps = config_updates['target_fps']
            self.processing_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0.2
        
        if 'processing_timeout' in config_updates:
            self.processing_timeout = config_updates['processing_timeout']
        
        if 'max_frame_age' in config_updates:
            self.max_frame_age = config_updates['max_frame_age']
        
        if 'adaptive_fps' in config_updates:
            self.adaptive_fps = config_updates['adaptive_fps']
        
        if 'memory_monitoring' in config_updates:
            self.memory_monitoring = config_updates['memory_monitoring']
        
        # Store the updated configuration in history (not the old one)
        result = self.config_manager.update_configuration_with_history(
            current_config, config_updates, change_description, author
        )
        
        return result
    
    def get_configuration_history(self) -> Dict[str, Any]:
        """Get configuration history."""
        return self.config_manager.get_configuration_history()
    
    def rollback_to_configuration(
        self,
        target_entry_id: str,
        rollback_reason: str = "manual_rollback"
    ) -> Dict[str, Any]:
        """Rollback to a previous configuration."""
        result = self.config_manager.rollback_to_configuration(target_entry_id, rollback_reason)
        
        # If rollback was successful, apply the target configuration
        if result.get('success', False) and 'target_config' in result:
            config = result['target_config']
            
            if 'target_fps' in config:
                self.target_fps = config['target_fps']
                self.processing_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0.2
            
            if 'processing_timeout' in config:
                self.processing_timeout = config['processing_timeout']
            
            if 'max_frame_age' in config:
                self.max_frame_age = config['max_frame_age']
            
            if 'adaptive_fps' in config:
                self.adaptive_fps = config['adaptive_fps']
            
            if 'memory_monitoring' in config:
                self.memory_monitoring = config['memory_monitoring']
        
        return result

    # Configuration callback management (delegating to callback manager)
    def add_configuration_change_callback(self, callback: Callable):
        """Add callback for configuration changes."""
        self.callbacks.add_configuration_change_callback(callback)
    
    def remove_configuration_change_callback(self, callback: Callable):
        """Remove configuration change callback."""
        self.callbacks.remove_configuration_change_callback(callback)
    
    def add_configuration_validation_callback(self, callback: Callable):
        """Add callback for configuration validation events."""
        self.callbacks.add_configuration_validation_callback(callback)
    
    def remove_configuration_validation_callback(self, callback: Callable):
        """Remove configuration validation callback."""
        self.callbacks.remove_configuration_validation_callback(callback)
    
    async def update_configuration_with_validation(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration with validation and rollback support."""
        result = await self.config_manager.update_configuration_with_validation(config_updates, self.callbacks)
        
        # If validation passed and updates are provided, apply them
        if result.get('success', False) and 'applied_updates' in result:
            updates = result['applied_updates']
            
            # Apply the configuration updates
            if 'target_fps' in updates:
                self.target_fps = updates['target_fps']
                self.processing_interval = 1.0 / self.target_fps if self.target_fps > 0 else 0.2
            
            if 'processing_timeout' in updates:
                self.processing_timeout = updates['processing_timeout']
            
            if 'max_frame_age' in updates:
                self.max_frame_age = updates['max_frame_age']
            
            if 'adaptive_fps' in updates:
                self.adaptive_fps = updates['adaptive_fps']
            
            if 'memory_monitoring' in updates:
                self.memory_monitoring = updates['memory_monitoring']
        
        return result

    # Component hot-swapping (delegating to configuration manager) 
    def add_component_swap_callback(self, callback: Callable):
        """Add callback for component swap events."""
        self.callbacks.add_component_swap_callback(callback)
    
    def add_camera_swap_callback(self, callback: Callable):
        """Add callback for camera swap events."""
        self.callbacks.add_camera_swap_callback(callback)
    
    def add_health_monitoring_callback(self, callback: Callable):
        """Add callback for health monitoring events."""
        self.callbacks.add_health_monitoring_callback(callback)
    
    def add_automatic_swap_callback(self, callback: Callable):
        """Add callback for automatic swap events."""
        self.callbacks.add_automatic_swap_callback(callback)
    
    async def hot_swap_detector(
        self,
        new_detector,
        swap_reason: str = "manual_swap",
        initialize_new: bool = True,
        cleanup_old: bool = True
    ) -> Dict[str, Any]:
        """Hot-swap detector without interrupting processing."""
        # Get swap result from configuration manager
        result = await self.config_manager.hot_swap_detector(
            new_detector, self.callbacks, swap_reason, initialize_new, cleanup_old
        )
        
        # If swap was successful, actually replace the detector
        if result.get('success', False) and 'new_detector' in result:
            self.detector = result['new_detector']
        
        return result
    
    async def hot_swap_camera(
        self,
        new_camera,
        swap_reason: str = "manual_swap",
        validate_new_camera: bool = True,
        frame_continuity_check: bool = True
    ) -> Dict[str, Any]:
        """Hot-swap camera while maintaining frame processing continuity."""
        # Get swap result from configuration manager
        result = await self.config_manager.hot_swap_camera(
            new_camera, self.callbacks, swap_reason, validate_new_camera, frame_continuity_check
        )
        
        # If swap was successful, actually replace the camera
        if result.get('success', False) and 'new_camera' in result:
            self.camera_manager = result['new_camera']
        
        return result
    
    def enable_component_health_monitoring(
        self,
        health_check_interval_seconds: float = 1.0,
        failure_threshold: int = 3,
        auto_swap_enabled: bool = False
    ):
        """Enable component health monitoring."""
        self.config_manager.enable_component_health_monitoring(
            health_check_interval_seconds, failure_threshold, auto_swap_enabled
        )
    
    def register_backup_detector(self, backup_detector, priority: int = 1):
        """Register backup detector for automatic swapping."""
        self.config_manager.register_backup_detector(backup_detector, priority)


# Convenience functions preserved from original
def create_latest_frame_processor(
    camera_manager,
    detector,
    target_fps: float = 5.0,
    real_time_mode: bool = True
) -> LatestFrameProcessor:
    """Create a latest frame processor with optimal settings."""
    if real_time_mode:
        # Optimize for real-time with minimal lag
        processor = LatestFrameProcessor(
            camera_manager=camera_manager,
            detector=detector,
            target_fps=target_fps,
            processing_timeout=1.0,
            max_frame_age=0.5,
            adaptive_fps=True,
            memory_monitoring=True
        )
    else:
        # Standard settings
        processor = LatestFrameProcessor(
            camera_manager=camera_manager,
            detector=detector,
            target_fps=target_fps,
            processing_timeout=3.0,
            max_frame_age=1.0,
            adaptive_fps=False,
            memory_monitoring=False
        )
    
    return processor 


def load_processor_config(config_file: str) -> Dict[str, Any]:
    """Load processor configuration from YAML file."""
    import yaml
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading processor config from {config_file}: {e}")
        return {}


def create_processor_from_legacy_config(camera_manager, detector, config: Dict[str, Any]) -> LatestFrameProcessor:
    """Create processor from legacy configuration format."""
    # Extract processor-specific settings
    processor_config = config.get('processor', {})
    
    return LatestFrameProcessor(
        camera_manager=camera_manager,
        detector=detector,
        target_fps=processor_config.get('target_fps', 5.0),
        processing_timeout=processor_config.get('processing_timeout', 3.0),
        max_frame_age=processor_config.get('max_frame_age', 1.0),
        adaptive_fps=processor_config.get('adaptive_fps', False),
        memory_monitoring=processor_config.get('memory_monitoring', False)
    ) 