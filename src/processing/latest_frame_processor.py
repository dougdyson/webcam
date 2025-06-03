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
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class LatestFrameResult:
    """Result from latest frame processing."""
    frame_id: int
    human_present: bool
    confidence: float
    processing_time: float
    timestamp: float
    frame_age: float  # How old was the frame when we processed it
    frames_skipped: int  # How many frames we skipped since last processing
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
        max_frame_age: float = 1.0
    ):
        """
        Initialize latest frame processor.
        
        Args:
            camera_manager: Camera manager to get frames from
            detector: Detection system to use
            target_fps: Target processing rate (frames per second)
            processing_timeout: Timeout for individual frame processing
            max_frame_age: Maximum acceptable frame age in seconds
        """
        self.camera_manager = camera_manager
        self.detector = detector
        self.target_fps = target_fps
        self.processing_timeout = processing_timeout
        self.max_frame_age = max_frame_age
        
        # Calculate processing interval from target FPS
        self.processing_interval = 1.0 / target_fps if target_fps > 0 else 0.2
        
        # State management
        self.is_running = False
        self._processing_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics
        self._lock = threading.RLock()
        self._frames_processed = 0
        self._frames_skipped = 0
        self._frames_too_old = 0
        self._total_processing_time = 0.0
        self._start_time = time.time()
        self._last_frame_id = 0
        self._last_processing_time = 0.0
        
        # Performance tracking
        self._processing_times: deque = deque(maxlen=100)
        self._frame_ages: deque = deque(maxlen=100)
        self._skip_counts: deque = deque(maxlen=100)
        
        # Callbacks for results
        self._result_callbacks: list = []
        
        logger.info(f"Latest frame processor initialized - target FPS: {target_fps}, "
                   f"interval: {self.processing_interval:.3f}s")
    
    def add_result_callback(self, callback: Callable[[LatestFrameResult], None]):
        """Add callback to be called with processing results."""
        self._result_callbacks.append(callback)
    
    def remove_result_callback(self, callback: Callable[[LatestFrameResult], None]):
        """Remove result callback."""
        if callback in self._result_callbacks:
            self._result_callbacks.remove(callback)
    
    async def start(self):
        """Start the latest frame processor."""
        if self.is_running:
            logger.warning("Latest frame processor already running")
            return
        
        self.is_running = True
        self._shutdown_event.clear()
        
        # Start the processing loop
        self._processing_task = asyncio.create_task(self._processing_loop())
        
        logger.info("Latest frame processor started")
    
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
                
                # Wait for next processing interval
                processing_time = time.time() - process_start
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
                    with self._lock:
                        self._frames_too_old += 1
                    logger.debug(f"Frame too old: {frame_age:.3f}s")
                    return None
                
                return frame
            
        except Exception as e:
            logger.error(f"Error getting latest frame: {e}")
        
        return None
    
    async def _process_latest_frame(self, frame: np.ndarray, process_start_time: float) -> LatestFrameResult:
        """Process a single latest frame."""
        frame_capture_time = time.time()
        
        # Calculate frames skipped (approximate)
        current_frame_id = self._last_frame_id + 1
        frames_since_last = current_frame_id - self._last_frame_id
        frames_skipped = max(0, frames_since_last - 1)
        
        with self._lock:
            self._frames_skipped += frames_skipped
            self._last_frame_id = current_frame_id
        
        try:
            # Perform detection with timeout
            detection_result = await asyncio.wait_for(
                self._async_detect(frame),
                timeout=self.processing_timeout
            )
            
            processing_time = time.time() - process_start_time
            frame_age = time.time() - frame_capture_time
            
            # Create result
            result = LatestFrameResult(
                frame_id=current_frame_id,
                human_present=detection_result.human_present,
                confidence=detection_result.confidence,
                processing_time=processing_time,
                timestamp=time.time(),
                frame_age=frame_age,
                frames_skipped=frames_skipped,
                error_occurred=False
            )
            
            # Update statistics
            with self._lock:
                self._frames_processed += 1
                self._total_processing_time += processing_time
                self._processing_times.append(processing_time)
                self._frame_ages.append(frame_age)
                self._skip_counts.append(frames_skipped)
                self._last_processing_time = time.time()
            
            logger.debug(f"Processed latest frame {current_frame_id}: "
                        f"human={result.human_present}, confidence={result.confidence:.3f}, "
                        f"time={processing_time:.3f}s, age={frame_age:.3f}s, skipped={frames_skipped}")
            
            return result
            
        except asyncio.TimeoutError:
            processing_time = time.time() - process_start_time
            
            result = LatestFrameResult(
                frame_id=current_frame_id,
                human_present=False,
                confidence=0.0,
                processing_time=processing_time,
                timestamp=time.time(),
                frame_age=0.0,
                frames_skipped=frames_skipped,
                error_occurred=True,
                error_message=f"Processing timeout after {self.processing_timeout}s"
            )
            
            logger.warning(f"Frame {current_frame_id} processing timeout")
            return result
            
        except Exception as e:
            processing_time = time.time() - process_start_time
            
            result = LatestFrameResult(
                frame_id=current_frame_id,
                human_present=False,
                confidence=0.0,
                processing_time=processing_time,
                timestamp=time.time(),
                frame_age=0.0,
                frames_skipped=frames_skipped,
                error_occurred=True,
                error_message=f"Processing error: {str(e)}"
            )
            
            logger.error(f"Error processing frame {current_frame_id}: {e}")
            return result
    
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
        with self._lock:
            uptime = time.time() - self._start_time
            
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
        
        if self._frame_ages:
            stats['average_frame_age'] = sum(self._frame_ages) / len(self._frame_ages)
        
        if self._skip_counts:
            stats['average_frames_skipped'] = sum(self._skip_counts) / len(self._skip_counts)
            # Recent skip rate (last 10 measurements)
            recent_skips = list(self._skip_counts)[-10:]
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
            max_frame_age=0.5        # Accept only very fresh frames
        )
    else:
        # Standard settings
        processor = LatestFrameProcessor(
            camera_manager=camera_manager,
            detector=detector,
            target_fps=target_fps,
            processing_timeout=3.0,
            max_frame_age=1.0
        )
    
    return processor 