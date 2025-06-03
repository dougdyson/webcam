"""
Frame processing statistics tracking and analysis.

Extracted from LatestFrameProcessor to follow single responsibility principle
and keep the main processor focused on frame processing logic.
"""

import time
import threading
from typing import Dict, Any, List


class FrameStatistics:
    """Manages frame processing statistics and performance metrics."""
    
    def __init__(self):
        """Initialize statistics tracking."""
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
        self._current_frame_id = 0
        
        # Performance monitoring
        self._recent_frame_intervals = []
        
        # Callback error tracking
        self._callback_error_count = 0
        self._callback_error_types = {}
        self._callbacks_with_errors = set()
        self._successful_callback_invocations = 0
    
    def start_tracking(self):
        """Start statistics tracking."""
        with self._stats_lock:
            self._start_time = time.time()
    
    def get_next_frame_id(self) -> int:
        """Get next frame ID and increment counter."""
        with self._stats_lock:
            self._current_frame_id += 1
            return self._current_frame_id
    
    def increment_frames_skipped(self):
        """Thread-safe increment of frames skipped counter."""
        with self._stats_lock:
            self._frames_skipped += 1
    
    def increment_frames_too_old(self):
        """Thread-safe increment of frames too old counter."""
        with self._stats_lock:
            self._frames_too_old += 1
    
    def update_processing_time_stats(self, processing_time: float):
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
    
    def update_frame_intervals(self, processing_time: float):
        """Track frame intervals for performance monitoring."""
        with self._stats_lock:
            self._recent_frame_intervals.append(processing_time)
            if len(self._recent_frame_intervals) > 20:  # Keep last 20 intervals
                self._recent_frame_intervals.pop(0)
    
    def record_callback_success(self):
        """Record successful callback invocation."""
        with self._stats_lock:
            self._successful_callback_invocations += 1
    
    def record_callback_error(self, error: Exception, callback_str: str):
        """Record callback error with details."""
        with self._stats_lock:
            self._callback_error_count += 1
            error_type = type(error).__name__
            self._callback_error_types[error_type] = self._callback_error_types.get(error_type, 0) + 1
            self._callbacks_with_errors.add(callback_str)
    
    def get_statistics(self, target_fps: float, is_running: bool) -> Dict[str, Any]:
        """Get comprehensive processor statistics."""
        with self._stats_lock:
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
                'target_fps': target_fps,
                'skip_rate': self._frames_skipped / max(self._frames_processed, 1),
                'average_processing_time': (
                    self._total_processing_time / max(self._frames_processed, 1)
                ),
                'last_processing_time': self._last_processing_time,
                'time_since_last_frame': time.time() - self._last_processing_time,
                'is_running': is_running
            }
    
    def get_detailed_statistics(self, target_fps: float, is_running: bool) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        with self._stats_lock:
            if self._start_time:
                uptime = time.time() - self._start_time
            else:
                uptime = 0.0
            
            if uptime > 0 and self._frames_processed > 0:
                actual_fps = self._frames_processed / uptime
            else:
                actual_fps = 0.0
            
            if target_fps > 0:
                efficiency = min(1.0, actual_fps / target_fps)
            else:
                efficiency = 0.0
            
            if self._frames_processed > 0:
                avg_processing_time = self._total_processing_time / self._frames_processed
            else:
                avg_processing_time = 0.0
            
            if uptime > 0:
                frames_skipped_rate = self._frames_skipped / uptime
                frames_too_old_rate = self._frames_too_old / uptime
            else:
                frames_skipped_rate = 0.0
                frames_too_old_rate = 0.0
            
            total_frames_attempted = self._frames_processed + self._frames_skipped + self._frames_too_old
            if total_frames_attempted > 0:
                skip_efficiency_ratio = self._frames_processed / total_frames_attempted
            else:
                skip_efficiency_ratio = 0.0
            
            efficiency_warning = (self._frames_processed > 0) and (efficiency < 0.6)
            
            return {
                'total_frames_processed': self._frames_processed,
                'frames_skipped_total': self._frames_skipped,
                'frames_too_old_total': self._frames_too_old,
                'average_processing_time': avg_processing_time,
                'min_processing_time': self._min_processing_time,
                'max_processing_time': self._max_processing_time,
                'total_processing_time': self._total_processing_time,
                'last_processing_time': self._last_processing_time,
                'frames_per_second_actual': actual_fps,
                'frames_per_second_target': target_fps,
                'processing_efficiency': efficiency,
                'efficiency_warning': efficiency_warning,
                'frames_skipped_rate': frames_skipped_rate,
                'frames_too_old_rate': frames_too_old_rate,
                'skip_efficiency_ratio': skip_efficiency_ratio,
                'uptime_seconds': uptime,
                'is_running': is_running
            }
    
    def get_callback_error_statistics(self) -> Dict[str, Any]:
        """Get callback error statistics for monitoring and debugging."""
        with self._stats_lock:
            return {
                'total_callback_errors': self._callback_error_count,
                'error_types': dict(self._callback_error_types),
                'callbacks_with_errors': len(self._callbacks_with_errors),
                'successful_callback_invocations': self._successful_callback_invocations,
                'callback_error_rate': (
                    self._callback_error_count / 
                    max(1, self._callback_error_count + self._successful_callback_invocations)
                ),
                'total_callback_invocations': self._callback_error_count + self._successful_callback_invocations
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
            self._recent_frame_intervals = []
            self._callback_error_count = 0
            self._callback_error_types = {}
            self._callbacks_with_errors = set()
            self._successful_callback_invocations = 0 