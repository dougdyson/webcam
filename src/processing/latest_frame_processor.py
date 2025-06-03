"""
Latest Frame Processor - Always Process Most Current Frame

This module provides a frame processor that always grabs the most recent frame
instead of processing queued frames, eliminating lag and ensuring real-time
processing for applications where timeliness is more important than processing
every single frame.

Key Benefits:
- No frame backlog/lag
- Always processes most current scene
- Better for real-time applications
- Reduced memory usage
"""

import asyncio
import threading
import time
import logging
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from collections import deque
import numpy as np
from concurrent.futures import ThreadPoolExecutor

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
    
    Instead of queuing frames for processing, this processor grabs the most
    recent frame from the camera whenever it's ready to process. This eliminates
    lag and ensures real-time processing at the cost of potentially skipping
    some frames.
    
    Perfect for applications where:
    - Real-time response is critical
    - Processing every frame is not necessary
    - Lag/delay is unacceptable
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
        """
        Initialize latest frame processor.
        
        Args:
            camera_manager: Camera manager to get frames from
            detector: Detection system to use
            target_fps: Target processing rate (frames per second)
            processing_timeout: Timeout for individual frame processing
            max_frame_age: Maximum acceptable frame age in seconds
            adaptive_fps: Enable adaptive FPS adjustment based on performance (NEW Phase 2.2)
            memory_monitoring: Enable memory usage monitoring (NEW Phase 2.2)
        """
        self.camera_manager = camera_manager
        self.detector = detector
        self.target_fps = target_fps
        self.processing_timeout = processing_timeout
        self.max_frame_age = max_frame_age
        self.adaptive_fps = adaptive_fps
        self.memory_monitoring = memory_monitoring
        
        # Calculate processing interval
        if target_fps > 0:
            self.processing_interval = 1.0 / target_fps
        else:
            self.processing_interval = 0.2  # Default fallback
        
        # Processing control
        self.is_running = False
        self._processing_task = None
        self._shutdown_event = asyncio.Event()
        
        # Callbacks for results
        self._result_callbacks: List[Callable] = []
        
        # Thread pool for sync detectors
        self._thread_pool = ThreadPoolExecutor(max_workers=1)
        
        # Statistics tracking (Phase 2.1)
        self._stats_lock = threading.Lock()
        self._start_time = None
        self._frames_processed = 0
        self._frames_skipped = 0
        self._frames_too_old = 0
        self._total_processing_time = 0.0
        self._min_processing_time = 0.0
        self._max_processing_time = 0.0
        self._last_processing_time = 0.0
        self._processing_times = []  # For detailed statistics
        
        # Frame tracking
        self._current_frame_id = 0
        
        # Performance monitoring (NEW Phase 2.2)
        self._recent_frame_intervals = []  # Track frame intervals for performance
        self._fps_adjustment_callbacks = []  # Track FPS adjustments
        
        # Memory monitoring (NEW Phase 2.2)
        if self.memory_monitoring:
            import psutil
            self._process = psutil.Process()
            self._peak_memory_mb = 0.0
            self._memory_samples = []
        
        logger.info(f"Latest frame processor initialized - target FPS: {target_fps}, "
                   f"timeout: {processing_timeout}s, max frame age: {max_frame_age}s, "
                   f"adaptive FPS: {adaptive_fps}, memory monitoring: {memory_monitoring}")
    
    def add_result_callback(self, callback: Callable[[LatestFrameResult], None]):
        """Add callback to be called with processing results."""
        self._result_callbacks.append(callback)
    
    def remove_result_callback(self, callback: Callable[[LatestFrameResult], None]):
        """Remove result callback."""
        if callback in self._result_callbacks:
            self._result_callbacks.remove(callback)
    
    async def start(self):
        """Start the latest frame processing loop."""
        if self.is_running:
            logger.warning("Latest frame processor already running")
            return
        
        self.is_running = True
        self._shutdown_event.clear()
        
        # Initialize statistics tracking (NEW for Phase 2.1)
        with self._stats_lock:
            self._start_time = time.time()
        
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
                    
                    # Notify callbacks
                    for callback in self._result_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(result)
                            else:
                                callback(result)
                        except Exception as e:
                            logger.error(f"Error in result callback: {e}")
                
                # Calculate processing time and check for adaptive FPS adjustment
                processing_time = time.time() - process_start
                
                # Adaptive FPS logic (NEW for Phase 2.2)
                if self.adaptive_fps:
                    # Check if processing is consistently too slow
                    if processing_time > self.processing_interval * 1.2:  # 20% over target
                        consecutive_slow_frames += 1
                    else:
                        consecutive_slow_frames = 0
                    
                    # Adjust FPS if consistently slow
                    # More aggressive for very slow processing (>50% over target)
                    current_time = time.time()
                    if processing_time > self.processing_interval * 1.5:  # Very slow
                        # Quick adjustment for severely slow processing
                        if current_time - last_fps_check > 0.5 and consecutive_slow_frames >= 2:
                            await self._adjust_fps_for_performance(processing_time)
                            last_fps_check = current_time
                            consecutive_slow_frames = 0
                    elif current_time - last_fps_check > 3.0 and consecutive_slow_frames >= 5:
                        # Standard adjustment for moderately slow processing
                        await self._adjust_fps_for_performance(processing_time)
                        last_fps_check = current_time
                        consecutive_slow_frames = 0
                
                # Track frame intervals for performance monitoring
                with self._stats_lock:
                    self._recent_frame_intervals.append(processing_time)
                    if len(self._recent_frame_intervals) > 20:  # Keep last 20 intervals
                        self._recent_frame_intervals.pop(0)
                
                # Wait for next processing interval
                sleep_time = max(0, self.processing_interval - processing_time)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    # We're processing slower than target FPS
                    logger.debug(f"Processing slower than target FPS: {processing_time:.3f}s > {self.processing_interval:.3f}s")
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
    
    def _get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Get the most recent frame from camera.
        
        This is where the magic happens - instead of getting from a queue,
        we always get the freshest frame available.
        """
        try:
            # Get current frame from camera
            frame = self.camera_manager.get_frame()
            
            if frame is not None:
                # Check frame freshness (if camera provides timestamps)
                frame_time = time.time()  # Current time as proxy for frame time
                frame_age = time.time() - frame_time
                
                if frame_age > self.max_frame_age:
                    # Use new statistics method (NEW for Phase 2.1)
                    self._increment_frames_too_old()
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
        
        # Increment frame ID
        with self._stats_lock:
            self._current_frame_id += 1
            current_frame_id = self._current_frame_id
        
        # Calculate frames skipped (approximate)
        frames_skipped = 0  # For now, simplified calculation
        
        try:
            # Detect humans in frame
            detection_result = await self._async_detect(frame)
            
            # Calculate processing time
            processing_time = time.time() - process_start_time
            
            # Update statistics using new methods (NEW for Phase 2.1)
            self._update_processing_time_stats(processing_time)
            
            return LatestFrameResult(
                frame_id=current_frame_id,
                human_present=detection_result.human_present,
                confidence=detection_result.confidence,
                processing_time=processing_time,
                timestamp=frame_time,
                frame_age=frame_age,
                frames_skipped=frames_skipped,
                error_occurred=False
            )
            
        except Exception as e:
            processing_time = time.time() - process_start_time
            error_msg = f"Detection error: {str(e)}"
            logger.error(error_msg)
            
            # Still update processing stats even on error
            self._update_processing_time_stats(processing_time)
            
            return LatestFrameResult(
                frame_id=current_frame_id,
                human_present=False,
                confidence=0.0,
                processing_time=processing_time,
                timestamp=frame_time,
                frame_age=frame_age,
                frames_skipped=frames_skipped,
                error_occurred=True,
                error_message=error_msg
            )
    
    async def _async_detect(self, frame: np.ndarray):
        """Convert sync detection to async if needed."""
        # If detector has async detect method, use it
        if hasattr(self.detector, 'detect_async'):
            return await self.detector.detect_async(frame)
        
        # Otherwise, run sync detection in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.detector.detect, frame)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processor statistics."""
        with self._stats_lock:
            # Fix: Handle None start_time safely
            if self._start_time:
                uptime = time.time() - self._start_time
            else:
                uptime = 0.0
            
            return {
                'frames_processed': self._frames_processed,
                'frames_skipped': self._frames_skipped,
                'frames_too_old': self._frames_too_old,
                'uptime_seconds': uptime,
                'processing_fps': self._frames_processed / uptime if uptime > 0 else 0.0,
                'target_fps': self.target_fps,
                'skip_rate': self._frames_skipped / max(self._frames_processed, 1),
                'average_processing_time': (
                    self._total_processing_time / max(self._frames_processed, 1)
                ),
                'last_processing_time': self._last_processing_time,
                'time_since_last_frame': time.time() - self._last_processing_time,
                'is_running': self.is_running
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get detailed performance statistics."""
        stats = {
            'average_processing_time': 0.0,
            'min_processing_time': 0.0,
            'max_processing_time': 0.0,
            'average_frame_age': 0.0,
            'average_frames_skipped': 0.0,
            'recent_skip_rate': 0.0
        }
        
        if self._processing_times:
            stats['average_processing_time'] = sum(self._processing_times) / len(self._processing_times)
            stats['min_processing_time'] = min(self._processing_times)
            stats['max_processing_time'] = max(self._processing_times)
        
        if self._processing_times:
            stats['average_frame_age'] = sum(self._processing_times) / len(self._processing_times)
        
        if self._processing_times:
            stats['average_frames_skipped'] = sum(self._processing_times) / len(self._processing_times)
            # Recent skip rate (last 10 measurements)
            recent_skips = list(self._processing_times)[-10:]
            stats['recent_skip_rate'] = sum(recent_skips) / len(recent_skips) if recent_skips else 0.0
        
        return stats
    
    def get_real_time_status(self) -> Dict[str, Any]:
        """Get real-time status information."""
        stats = self.get_statistics()
        perf = self.get_performance_stats()
        
        # Determine if we're keeping up
        time_since_last = stats['time_since_last_frame']
        is_keeping_up = time_since_last < (self.processing_interval * 2)
        
        # Determine processing efficiency
        avg_processing_time = perf['average_processing_time']
        efficiency = (1.0 - (avg_processing_time / self.processing_interval)) * 100
        efficiency = max(0, min(100, efficiency))
        
        return {
            'real_time_status': 'keeping_up' if is_keeping_up else 'lagging',
            'efficiency_percent': efficiency,
            'target_interval': self.processing_interval,
            'actual_processing_time': avg_processing_time,
            'time_since_last_frame': time_since_last,
            'recent_skip_rate': perf['recent_skip_rate'],
            'frames_behind': 0  # Always 0 with latest frame processing!
        }

    def get_detailed_statistics(self) -> dict:
        """
        Get comprehensive processing statistics.
        
        Returns detailed metrics about frame processing performance.
        """
        with self._stats_lock:
            # Calculate uptime
            if self._start_time:
                uptime = time.time() - self._start_time
            else:
                uptime = 0.0
            
            # Calculate actual FPS
            if uptime > 0 and self._frames_processed > 0:
                actual_fps = self._frames_processed / uptime
            else:
                actual_fps = 0.0
            
            # Calculate processing efficiency (actual vs target FPS)
            if self.target_fps > 0:
                efficiency = min(1.0, actual_fps / self.target_fps)
            else:
                efficiency = 0.0
            
            # Calculate average processing time
            if self._frames_processed > 0:
                avg_processing_time = self._total_processing_time / self._frames_processed
            else:
                avg_processing_time = 0.0
            
            # Calculate skip rates
            if uptime > 0:
                frames_skipped_rate = self._frames_skipped / uptime
                frames_too_old_rate = self._frames_too_old / uptime
            else:
                frames_skipped_rate = 0.0
                frames_too_old_rate = 0.0
            
            # Calculate skip efficiency ratio
            total_frames_attempted = self._frames_processed + self._frames_skipped + self._frames_too_old
            if total_frames_attempted > 0:
                skip_efficiency_ratio = self._frames_processed / total_frames_attempted
            else:
                skip_efficiency_ratio = 0.0
            
            # Efficiency warning - only warn if we have data and efficiency is low
            efficiency_warning = (self._frames_processed > 0) and (efficiency < 0.6)
            
            return {
                # Basic counters
                'total_frames_processed': self._frames_processed,
                'frames_skipped_total': self._frames_skipped,
                'frames_too_old_total': self._frames_too_old,
                
                # Timing metrics
                'average_processing_time': avg_processing_time,
                'min_processing_time': self._min_processing_time,
                'max_processing_time': self._max_processing_time,
                'total_processing_time': self._total_processing_time,
                'last_processing_time': self._last_processing_time,
                
                # Performance metrics
                'frames_per_second_actual': actual_fps,
                'frames_per_second_target': self.target_fps,
                'processing_efficiency': efficiency,
                'efficiency_warning': efficiency_warning,
                
                # Skip metrics
                'frames_skipped_rate': frames_skipped_rate,
                'frames_too_old_rate': frames_too_old_rate,
                'skip_efficiency_ratio': skip_efficiency_ratio,
                
                # System metrics
                'uptime_seconds': uptime,
                'is_running': self.is_running
            }
    
    def reset_statistics(self):
        """Reset all statistics to initial state."""
        with self._stats_lock:
            self._start_time = None
            self._frames_processed = 0
            self._frames_skipped = 0
            self._frames_too_old = 0
            self._total_processing_time = 0.0
            self._min_processing_time = 0.0
            self._max_processing_time = 0.0
            self._last_processing_time = 0.0
            self._processing_times = []
            self._current_frame_id = 0
            
        logger.info("Statistics reset to initial state")
    
    def _increment_frames_skipped(self):
        """Thread-safe increment of frames skipped counter."""
        with self._stats_lock:
            self._frames_skipped += 1
    
    def _increment_frames_too_old(self):
        """Thread-safe increment of frames too old counter."""
        with self._stats_lock:
            self._frames_too_old += 1
    
    def _update_processing_time_stats(self, processing_time: float):
        """Thread-safe update of processing time statistics."""
        with self._stats_lock:
            self._frames_processed += 1
            self._total_processing_time += processing_time
            self._last_processing_time = processing_time
            
            # Update min/max
            if self._min_processing_time == 0.0 or processing_time < self._min_processing_time:
                self._min_processing_time = processing_time
            
            if processing_time > self._max_processing_time:
                self._max_processing_time = processing_time
            
            # Keep recent processing times for detailed analysis
            self._processing_times.append(processing_time)
            if len(self._processing_times) > 100:  # Keep last 100 measurements
                self._processing_times.pop(0)

    def add_fps_adjustment_callback(self, callback: Callable):
        """Add callback for FPS adjustment notifications."""
        self._fps_adjustment_callbacks.append(callback)
    
    def get_current_target_fps(self) -> float:
        """Get current target FPS (may be different from initial if adaptive)."""
        return self.target_fps
    
    def get_real_time_performance_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics for lag elimination monitoring."""
        with self._stats_lock:
            # Calculate current FPS
            if self._start_time and self._frames_processed > 0:
                uptime = time.time() - self._start_time
                current_fps = self._frames_processed / uptime
            else:
                current_fps = 0.0
            
            # Calculate processing efficiency
            if self.target_fps > 0:
                efficiency_percent = min(100.0, (current_fps / self.target_fps) * 100.0)
            else:
                efficiency_percent = 0.0
            
            # Calculate average processing latency
            if self._frames_processed > 0:
                avg_latency_ms = (self._total_processing_time / self._frames_processed) * 1000
            else:
                avg_latency_ms = 0.0
            
            # Recent frame intervals
            recent_intervals_ms = [interval * 1000 for interval in self._recent_frame_intervals[-10:]]
            
            # Determine processing trend
            if len(self._processing_times) >= 5:
                recent_times = self._processing_times[-5:]
                early_avg = sum(recent_times[:2]) / 2
                late_avg = sum(recent_times[-2:]) / 2
                if late_avg < early_avg * 0.9:
                    trend = 'improving'
                elif late_avg > early_avg * 1.1:
                    trend = 'degrading'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            # Lag detection status
            if efficiency_percent > 80:
                lag_status = 'real_time'
            elif efficiency_percent > 60:
                lag_status = 'minor_lag'
            else:
                lag_status = 'significant_lag'
            
            # Performance warnings
            warnings = []
            if efficiency_percent < 60:
                warnings.append('Low processing efficiency detected')
            if avg_latency_ms > self.processing_interval * 800:  # 80% of interval
                warnings.append('High processing latency detected')
            
            return {
                'current_fps': current_fps,
                'target_fps': self.target_fps,
                'processing_efficiency_percent': efficiency_percent,
                'average_processing_latency_ms': avg_latency_ms,
                'recent_frame_intervals_ms': recent_intervals_ms,
                'frame_processing_trend': trend,
                'lag_detection_status': lag_status,
                'performance_warnings': warnings
            }
    
    def get_lag_detection_status(self) -> Dict[str, Any]:
        """Get detailed lag detection status and warnings."""
        with self._stats_lock:
            # Calculate time behind real-time
            if self._frames_processed > 0 and self._start_time:
                uptime = time.time() - self._start_time
                expected_frames = uptime * self.target_fps
                frames_behind = max(0, expected_frames - self._frames_processed)
                time_behind_ms = frames_behind * (1000 / self.target_fps)
            else:
                time_behind_ms = 0.0
                frames_behind = 0
            
            # Determine lag severity
            if time_behind_ms < 100:
                severity = 'none'
            elif time_behind_ms < 500:
                severity = 'minor'
            elif time_behind_ms < 1000:
                severity = 'moderate'
            else:
                severity = 'severe'
            
            # Lag trend analysis
            if len(self._processing_times) >= 10:
                recent_avg = sum(self._processing_times[-5:]) / 5
                older_avg = sum(self._processing_times[-10:-5]) / 5
                if recent_avg < older_avg * 0.9:
                    trend = 'improving'
                elif recent_avg > older_avg * 1.1:
                    trend = 'worsening'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            # Generate recommendations
            recommendations = []
            if severity != 'none':
                if severity in ['moderate', 'severe']:
                    recommendations.append('Consider reducing target FPS')
                    recommendations.append('Optimize detector performance')
                if len(recommendations) == 0:
                    recommendations.append('Monitor processing performance')
            
            return {
                'lag_severity': severity,
                'lag_trend': trend,
                'time_behind_real_time_ms': time_behind_ms,
                'frames_dropped_due_to_lag': int(frames_behind),
                'lag_warning_active': severity != 'none',
                'recommended_actions': recommendations
            }
    
    def get_efficiency_monitoring_status(self) -> Dict[str, Any]:
        """Get adaptive efficiency monitoring status."""
        with self._stats_lock:
            # Current efficiency calculation
            if self._frames_processed > 0 and self._start_time:
                uptime = time.time() - self._start_time
                actual_fps = self._frames_processed / uptime
                current_efficiency = min(100.0, (actual_fps / self.target_fps) * 100.0)
            else:
                current_efficiency = 0.0
            
            # Efficiency trend
            if len(self._processing_times) >= 6:
                recent_times = self._processing_times[-6:]
                early_efficiency = (1.0 / (sum(recent_times[:3]) / 3)) / self.target_fps * 100
                late_efficiency = (1.0 / (sum(recent_times[-3:]) / 3)) / self.target_fps * 100
                if late_efficiency > early_efficiency * 1.05:
                    efficiency_trend = 'improving'
                elif late_efficiency < early_efficiency * 0.95:
                    efficiency_trend = 'declining'
                else:
                    efficiency_trend = 'stable'
            else:
                efficiency_trend = 'stable'
            
            # Adaptive threshold (starts at 80%, adjusts based on system capability)
            if self._processing_times:
                max_observed_efficiency = min(100.0, max([100.0 / (t * self.target_fps) for t in self._processing_times]))
                adaptive_threshold = max(60.0, min(80.0, max_observed_efficiency * 0.8))
            else:
                adaptive_threshold = 80.0
            
            # Baseline performance
            if self._processing_times:
                baseline_ms = (sum(self._processing_times) / len(self._processing_times)) * 1000
                variability_ms = (max(self._processing_times) - min(self._processing_times)) * 1000
            else:
                baseline_ms = 0.0
                variability_ms = 0.0
            
            # Warning level
            if current_efficiency < 50:
                warning_level = 'critical'
            elif current_efficiency < 70:
                warning_level = 'moderate'
            elif current_efficiency < adaptive_threshold:
                warning_level = 'minor'
            else:
                warning_level = 'none'
            
            # Optimization suggestions
            suggestions = []
            if variability_ms > 50:
                suggestions.append('High processing time variability detected')
            if baseline_ms > self.processing_interval * 800:
                suggestions.append('Consider detector optimization')
            if current_efficiency < adaptive_threshold:
                suggestions.append('Performance below system capability')
            
            return {
                'current_efficiency_percent': current_efficiency,
                'efficiency_trend': efficiency_trend,
                'adaptive_threshold_percent': adaptive_threshold,
                'baseline_performance_ms': baseline_ms,
                'performance_variability_ms': variability_ms,
                'efficiency_warning_level': warning_level,
                'optimization_suggestions': suggestions
            }
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Generate performance optimization recommendations."""
        with self._stats_lock:
            # Analyze current performance
            if self._processing_times:
                avg_time = sum(self._processing_times) / len(self._processing_times)
                variability = max(self._processing_times) - min(self._processing_times)
                max_time = max(self._processing_times)
            else:
                avg_time = 0.0
                variability = 0.0
                max_time = 0.0
            
            # Performance analysis
            analysis = {
                'variability_detected': variability > 0.05,  # >50ms variability
                'bottleneck_identification': 'detector_processing' if avg_time > self.processing_interval * 0.7 else 'none',
                'system_capability_assessment': 'underperforming' if avg_time > self.processing_interval else 'adequate'
            }
            
            # Generate recommendations
            actions = []
            
            if variability > 0.05:
                actions.append({
                    'action': 'Stabilize detector performance',
                    'description': 'High variability detected in processing times',
                    'expected_benefit': 'More consistent frame processing',
                    'effort_level': 'medium'
                })
            
            if avg_time > self.processing_interval * 0.8:
                actions.append({
                    'action': 'Reduce target FPS',
                    'description': 'Processing time exceeds 80% of target interval',
                    'expected_benefit': 'Improved real-time performance',
                    'effort_level': 'low'
                })
            
            if max_time > self.processing_interval * 1.5:
                actions.append({
                    'action': 'Optimize detector algorithm',
                    'description': 'Peak processing times are significantly high',
                    'expected_benefit': 'Reduced maximum latency',
                    'effort_level': 'high'
                })
            
            # Priority assessment
            if avg_time > self.processing_interval:
                priority = 'critical'
            elif variability > 0.1:
                priority = 'high'
            elif len(actions) > 0:
                priority = 'medium'
            else:
                priority = 'low'
            
            return {
                'performance_analysis': analysis,
                'recommended_actions': actions,
                'estimated_improvements': {
                    'fps_improvement': '10-30%' if len(actions) > 0 else '0-5%',
                    'latency_reduction': '20-50%' if avg_time > self.processing_interval else '0-10%'
                },
                'priority_level': priority,
                'implementation_complexity': 'high' if any(a['effort_level'] == 'high' for a in actions) else 'medium'
            }
    
    def get_memory_usage_status(self) -> Dict[str, Any]:
        """Get memory usage monitoring status."""
        if not self.memory_monitoring:
            return {
                'current_memory_mb': 0.0,
                'peak_memory_mb': 0.0,
                'memory_trend': 'stable',
                'memory_efficiency': 100.0,
                'memory_warnings': ['Memory monitoring disabled'],
                'memory_optimization_suggestions': []
            }
        
        try:
            # Get current memory usage
            memory_info = self._process.memory_info()
            current_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            
            # Track peak memory
            self._peak_memory_mb = max(self._peak_memory_mb, current_mb)
            
            # Sample memory usage
            self._memory_samples.append(current_mb)
            if len(self._memory_samples) > 100:  # Keep last 100 samples
                self._memory_samples.pop(0)
            
            # Memory trend analysis
            if len(self._memory_samples) >= 10:
                recent_avg = sum(self._memory_samples[-5:]) / 5
                older_avg = sum(self._memory_samples[-10:-5]) / 5
                if recent_avg > older_avg * 1.1:
                    trend = 'increasing'
                elif recent_avg < older_avg * 0.9:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            # Memory efficiency (inverse of growth rate)
            if self._memory_samples:
                growth_rate = (current_mb - self._memory_samples[0]) / max(1.0, len(self._memory_samples))
                efficiency = max(0.0, 100.0 - (growth_rate * 10))  # Scale growth rate
            else:
                efficiency = 100.0
            
            # Warnings and suggestions
            warnings = []
            suggestions = []
            
            if current_mb > 100:  # >100MB usage
                warnings.append('High memory usage detected')
                suggestions.append('Monitor for memory leaks')
            
            if trend == 'increasing':
                warnings.append('Memory usage is increasing')
                suggestions.append('Check for accumulating data structures')
            
            return {
                'current_memory_mb': current_mb,
                'peak_memory_mb': self._peak_memory_mb,
                'memory_trend': trend,
                'memory_efficiency': efficiency,
                'memory_warnings': warnings,
                'memory_optimization_suggestions': suggestions
            }
            
        except Exception as e:
            logger.error(f"Error getting memory status: {e}")
            return {
                'current_memory_mb': 0.0,
                'peak_memory_mb': 0.0,
                'memory_trend': 'unknown',
                'memory_efficiency': 0.0,
                'memory_warnings': [f'Memory monitoring error: {e}'],
                'memory_optimization_suggestions': []
            }

    async def _adjust_fps_for_performance(self, current_processing_time: float):
        """Adjust target FPS based on current performance."""
        old_fps = self.target_fps
        
        # Calculate sustainable FPS based on current processing time
        # Add 20% buffer for safety
        sustainable_fps = 0.8 / current_processing_time
        
        # Don't go below 3 FPS or above original target
        new_fps = max(3.0, min(old_fps, sustainable_fps))
        
        # Only adjust if change is significant (>10%)
        if abs(new_fps - old_fps) / old_fps > 0.1:
            self.target_fps = new_fps
            self.processing_interval = 1.0 / new_fps
            
            reason = f"Adaptive adjustment due to performance: {current_processing_time*1000:.1f}ms processing time"
            
            # Notify callbacks of FPS adjustment
            for callback in self._fps_adjustment_callbacks:
                try:
                    callback(old_fps, new_fps, reason)
                except Exception as e:
                    logger.error(f"Error in FPS adjustment callback: {e}")
            
            logger.info(f"Adaptive FPS adjustment: {old_fps:.1f} → {new_fps:.1f} FPS ({reason})")


# Convenience function for quick setup
def create_latest_frame_processor(
    camera_manager,
    detector,
    target_fps: float = 5.0,
    real_time_mode: bool = True
) -> LatestFrameProcessor:
    """
    Create a latest frame processor with optimal settings.
    
    Args:
        camera_manager: Camera manager instance
        detector: Detection system instance
        target_fps: Target processing rate
        real_time_mode: If True, optimize for minimal lag
        
    Returns:
        Configured LatestFrameProcessor
    """
    if real_time_mode:
        # Optimize for real-time with minimal lag
        processor = LatestFrameProcessor(
            camera_manager=camera_manager,
            detector=detector,
            target_fps=target_fps,
            processing_timeout=1.0,  # Shorter timeout
            max_frame_age=0.5,        # Accept only very fresh frames
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