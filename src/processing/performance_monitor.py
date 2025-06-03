"""
Performance monitoring and adaptive optimization for frame processing.

Extracted from LatestFrameProcessor to follow single responsibility principle.
Handles real-time performance analysis, lag detection, and optimization recommendations.
"""

import time
import logging
from typing import Dict, Any, List, Callable, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitors frame processing performance and provides optimization recommendations."""
    
    def __init__(self, enable_memory_monitoring: bool = False):
        """Initialize performance monitor."""
        self.enable_memory_monitoring = enable_memory_monitoring
        
        # FPS adjustment tracking
        self._fps_adjustment_callbacks: List[Callable] = []
        
        # Memory monitoring
        if self.enable_memory_monitoring and PSUTIL_AVAILABLE:
            self._process = psutil.Process()
            self._peak_memory_mb = 0.0
            self._memory_samples = []
        else:
            self._process = None
            self._peak_memory_mb = 0.0
            self._memory_samples = []
    
    def add_fps_adjustment_callback(self, callback: Callable):
        """Add callback for FPS adjustment notifications."""
        self._fps_adjustment_callbacks.append(callback)
    
    async def adjust_fps_for_performance(
        self, 
        current_processing_time: float, 
        current_fps: float,
        processing_interval: float
    ) -> Optional[float]:
        """
        Adjust target FPS based on current performance.
        Returns new FPS if adjustment was made, None otherwise.
        """
        old_fps = current_fps
        
        # Calculate sustainable FPS based on current processing time
        # Add 20% buffer for safety
        sustainable_fps = 0.8 / current_processing_time
        
        # Don't go below 3 FPS or above original target
        new_fps = max(3.0, min(old_fps, sustainable_fps))
        
        # Only adjust if change is significant (>10%)
        if abs(new_fps - old_fps) / old_fps > 0.1:
            reason = f"Adaptive adjustment due to performance: {current_processing_time*1000:.1f}ms processing time"
            
            # Notify callbacks of FPS adjustment
            for callback in self._fps_adjustment_callbacks:
                try:
                    callback(old_fps, new_fps, reason)
                except Exception as e:
                    logger.error(f"Error in FPS adjustment callback: {e}")
            
            logger.info(f"Adaptive FPS adjustment: {old_fps:.1f} → {new_fps:.1f} FPS ({reason})")
            return new_fps
        
        return None
    
    def get_real_time_performance_metrics(
        self, 
        processing_times: List[float],
        target_fps: float,
        frames_processed: int,
        start_time: Optional[float],
        recent_frame_intervals: List[float]
    ) -> Dict[str, Any]:
        """Get real-time performance metrics for lag elimination monitoring."""
        # Calculate current FPS
        if start_time and frames_processed > 0:
            uptime = time.time() - start_time
            current_fps = frames_processed / uptime
        else:
            current_fps = 0.0
        
        # Calculate processing efficiency
        if target_fps > 0:
            efficiency_percent = min(100.0, (current_fps / target_fps) * 100.0)
        else:
            efficiency_percent = 0.0
        
        # Calculate average processing latency
        if processing_times:
            avg_latency_ms = (sum(processing_times) / len(processing_times)) * 1000
        else:
            avg_latency_ms = 0.0
        
        # Recent frame intervals
        recent_intervals_ms = [interval * 1000 for interval in recent_frame_intervals[-10:]]
        
        # Determine processing trend
        if len(processing_times) >= 5:
            recent_times = processing_times[-5:]
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
        processing_interval = 1.0 / target_fps if target_fps > 0 else 1.0
        if avg_latency_ms > processing_interval * 800:  # 80% of interval
            warnings.append('High processing latency detected')
        
        return {
            'current_fps': current_fps,
            'target_fps': target_fps,
            'processing_efficiency_percent': efficiency_percent,
            'average_processing_latency_ms': avg_latency_ms,
            'recent_frame_intervals_ms': recent_intervals_ms,
            'frame_processing_trend': trend,
            'lag_detection_status': lag_status,
            'performance_warnings': warnings
        }
    
    def get_lag_detection_status(
        self,
        processing_times: List[float],
        target_fps: float,
        frames_processed: int,
        start_time: Optional[float]
    ) -> Dict[str, Any]:
        """Get detailed lag detection status and warnings."""
        # Calculate time behind real-time
        if frames_processed > 0 and start_time:
            uptime = time.time() - start_time
            expected_frames = uptime * target_fps
            frames_behind = max(0, expected_frames - frames_processed)
            time_behind_ms = frames_behind * (1000 / target_fps) if target_fps > 0 else 0.0
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
        if len(processing_times) >= 10:
            recent_avg = sum(processing_times[-5:]) / 5
            older_avg = sum(processing_times[-10:-5]) / 5
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
    
    def get_efficiency_monitoring_status(
        self,
        processing_times: List[float],
        target_fps: float,
        frames_processed: int,
        start_time: Optional[float]
    ) -> Dict[str, Any]:
        """Get adaptive efficiency monitoring status."""
        # Current efficiency calculation
        if frames_processed > 0 and start_time:
            uptime = time.time() - start_time
            actual_fps = frames_processed / uptime
            current_efficiency = min(100.0, (actual_fps / target_fps) * 100.0) if target_fps > 0 else 0.0
        else:
            current_efficiency = 0.0
        
        # Efficiency trend
        if len(processing_times) >= 6:
            recent_times = processing_times[-6:]
            early_efficiency = (1.0 / (sum(recent_times[:3]) / 3)) / target_fps * 100 if target_fps > 0 else 0.0
            late_efficiency = (1.0 / (sum(recent_times[-3:]) / 3)) / target_fps * 100 if target_fps > 0 else 0.0
            if late_efficiency > early_efficiency * 1.05:
                efficiency_trend = 'improving'
            elif late_efficiency < early_efficiency * 0.95:
                efficiency_trend = 'declining'
            else:
                efficiency_trend = 'stable'
        else:
            efficiency_trend = 'stable'
        
        # Adaptive threshold (starts at 80%, adjusts based on system capability)
        if processing_times and target_fps > 0:
            max_observed_efficiency = min(100.0, max([100.0 / (t * target_fps) for t in processing_times]))
            adaptive_threshold = max(60.0, min(80.0, max_observed_efficiency * 0.8))
        else:
            adaptive_threshold = 80.0
        
        # Baseline performance
        if processing_times:
            baseline_ms = (sum(processing_times) / len(processing_times)) * 1000
            variability_ms = (max(processing_times) - min(processing_times)) * 1000
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
        processing_interval = 1.0 / target_fps if target_fps > 0 else 1.0
        if baseline_ms > processing_interval * 800:
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
    
    def get_optimization_recommendations(
        self,
        processing_times: List[float],
        target_fps: float
    ) -> Dict[str, Any]:
        """Generate performance optimization recommendations."""
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            variability = max(processing_times) - min(processing_times)
            max_time = max(processing_times)
        else:
            avg_time = 0.0
            variability = 0.0
            max_time = 0.0
        
        processing_interval = 1.0 / target_fps if target_fps > 0 else 1.0
        
        # Performance analysis
        analysis = {
            'variability_detected': variability > 0.05,  # >50ms variability
            'bottleneck_identification': 'detector_processing' if avg_time > processing_interval * 0.7 else 'none',
            'system_capability_assessment': 'underperforming' if avg_time > processing_interval else 'adequate'
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
        
        if avg_time > processing_interval * 0.8:
            actions.append({
                'action': 'Reduce target FPS',
                'description': 'Processing time exceeds 80% of target interval',
                'expected_benefit': 'Improved real-time performance',
                'effort_level': 'low'
            })
        
        if max_time > processing_interval * 1.5:
            actions.append({
                'action': 'Optimize detector algorithm',
                'description': 'Peak processing times are significantly high',
                'expected_benefit': 'Reduced maximum latency',
                'effort_level': 'high'
            })
        
        # Priority assessment
        if avg_time > processing_interval:
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
                'latency_reduction': '20-50%' if avg_time > processing_interval else '0-10%'
            },
            'priority_level': priority,
            'implementation_complexity': 'high' if any(a['effort_level'] == 'high' for a in actions) else 'medium'
        }
    
    def get_memory_usage_status(self) -> Dict[str, Any]:
        """Get memory usage monitoring status."""
        if not self.enable_memory_monitoring or not PSUTIL_AVAILABLE:
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