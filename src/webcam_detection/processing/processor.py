"""
Async frame processor functionality for webcam human detection application.

This module provides asynchronous frame processing capabilities that integrate
with the frame queue and detection systems to enable concurrent processing
of video frames.
"""
import asyncio
import logging
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Set
from concurrent.futures import CancelledError
import numpy as np

from .queue import FrameQueue, QueuedFrame


# Set up module logger
logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of frame processing operation."""
    frame_id: Optional[int]
    human_present: bool
    confidence: float
    processing_time: float
    timestamp: float
    source: str
    error_occurred: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate processing result after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        
        if self.processing_time < 0:
            raise ValueError("Processing time must be non-negative")


class FrameProcessorError(Exception):
    """Exception raised for frame processor-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize FrameProcessorError.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Chain exceptions for better debugging
        if original_error:
            self.__cause__ = original_error


class FrameProcessor:
    """
    Asynchronous frame processor for human detection pipeline.
    
    This class manages the asynchronous processing of frames from a queue,
    coordinates with detection systems, and provides performance monitoring
    and error handling capabilities.
    
    Features:
    - Asynchronous frame processing with configurable concurrency
    - Integration with FrameQueue for frame retrieval
    - Error handling and recovery mechanisms
    - Performance statistics and monitoring
    - Graceful start/stop lifecycle management
    """
    
    def __init__(
        self,
        frame_queue: FrameQueue,
        detector,  # Will be typed properly when detection module exists
        max_concurrent: int = 2,
        processing_timeout: float = 5.0,
        queue_timeout: float = 1.0
    ):
        """
        Initialize frame processor.
        
        Args:
            frame_queue: Queue to retrieve frames from
            detector: Detection system to use for processing frames
            max_concurrent: Maximum number of concurrent processing tasks
            processing_timeout: Timeout for individual frame processing
            queue_timeout: Timeout for queue operations
            
        Raises:
            FrameProcessorError: If parameters are invalid
        """
        # Validate parameters
        if frame_queue is None:
            raise FrameProcessorError("frame_queue is required")
        
        if detector is None:
            raise FrameProcessorError("detector is required")
        
        if max_concurrent <= 0:
            raise FrameProcessorError("max_concurrent must be positive")
        
        if processing_timeout <= 0:
            raise FrameProcessorError("processing_timeout must be positive")
        
        self.frame_queue = frame_queue
        self.detector = detector
        self.max_concurrent = max_concurrent
        self.processing_timeout = processing_timeout
        self.queue_timeout = queue_timeout
        
        # State management
        self.is_running = False
        self._active_tasks: Set[asyncio.Task] = set()
        self._processing_tasks: Set[asyncio.Task] = set()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._shutdown_event = asyncio.Event()
        
        # Statistics tracking
        self._lock = threading.RLock()
        self._frames_processed = 0
        self._frames_failed = 0
        self._total_processing_time = 0.0
        self._total_queue_wait_time = 0.0
        self._peak_concurrent_tasks = 0
        self._start_time = time.time()
        
        # Performance tracking
        self._processing_times: deque = deque(maxlen=100)
        self._queue_wait_times: deque = deque(maxlen=100)
        self._frame_timestamps: deque = deque(maxlen=100)
        
        logger.info(f"Frame processor initialized with max_concurrent={max_concurrent}, "
                   f"timeout={processing_timeout}s")
    
    async def start(self) -> None:
        """Start the frame processor."""
        if self.is_running:
            logger.warning("Frame processor is already running")
            return
        
        self.is_running = True
        self._shutdown_event.clear()
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        
        logger.info("Frame processor started")
    
    async def stop(self) -> None:
        """Stop the frame processor and cleanup resources."""
        if not self.is_running:
            return
        
        logger.info("Stopping frame processor...")
        
        self.is_running = False
        self._shutdown_event.set()
        
        # Cancel all active tasks
        for task in list(self._active_tasks):
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete with timeout
        if self._active_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._active_tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not complete during shutdown")
        
        # Clear task sets
        self._active_tasks.clear()
        self._processing_tasks.clear()
        
        logger.info("Frame processor stopped")
    
    async def process_next_frame(self, timeout: Optional[float] = None) -> Optional[ProcessingResult]:
        """
        Process the next frame from the queue.
        
        Args:
            timeout: Timeout for queue operations (uses default if None)
            
        Returns:
            ProcessingResult if frame was processed, None if no frame available
        """
        if timeout is None:
            timeout = self.queue_timeout
        
        queue_start_time = time.time()
        
        # Get frame from queue
        queued_frame = self.frame_queue.get_frame(
            timeout=timeout,
            include_metadata=True
        )
        
        if queued_frame is None:
            return None
        
        queue_wait_time = time.time() - queue_start_time
        self._queue_wait_times.append(queue_wait_time)
        
        # Process the frame
        return await self._process_frame(queued_frame, queue_wait_time)
    
    async def _process_frame(
        self, 
        queued_frame: QueuedFrame, 
        queue_wait_time: float
    ) -> ProcessingResult:
        """
        Process a single frame.
        
        Args:
            queued_frame: Frame with metadata to process
            queue_wait_time: Time spent waiting for frame from queue
            
        Returns:
            ProcessingResult containing detection results and metadata
        """
        process_start_time = time.time()
        
        try:
            # Perform detection with timeout
            detection_result = await asyncio.wait_for(
                self.detector.detect(queued_frame.frame),
                timeout=self.processing_timeout
            )
            
            processing_time = time.time() - process_start_time
            
            # Create successful result
            result = ProcessingResult(
                frame_id=queued_frame.metadata.frame_id,
                human_present=detection_result.human_present,
                confidence=detection_result.confidence,
                processing_time=processing_time,
                timestamp=time.time(),
                source=queued_frame.metadata.source,
                error_occurred=False,
                metadata={
                    'queue_wait_time': queue_wait_time,
                    'frame_timestamp': queued_frame.metadata.timestamp,
                    'detection_metadata': getattr(detection_result, 'metadata', {})
                }
            )
            
            # Update statistics
            with self._lock:
                self._frames_processed += 1
                self._total_processing_time += processing_time
                self._total_queue_wait_time += queue_wait_time
                self._processing_times.append(processing_time)
                self._frame_timestamps.append(time.time())
            
            logger.debug(f"Processed frame {result.frame_id}: human={result.human_present}, "
                        f"confidence={result.confidence:.3f}, time={processing_time:.3f}s")
            
            return result
            
        except asyncio.TimeoutError:
            processing_time = time.time() - process_start_time
            error_msg = f"Frame processing timeout after {self.processing_timeout}s"
            
            result = ProcessingResult(
                frame_id=queued_frame.metadata.frame_id,
                human_present=False,
                confidence=0.0,
                processing_time=processing_time,
                timestamp=time.time(),
                source=queued_frame.metadata.source,
                error_occurred=True,
                error_message=error_msg
            )
            
            with self._lock:
                self._frames_failed += 1
            
            logger.warning(f"Frame {queued_frame.metadata.frame_id} processing timeout")
            return result
            
        except Exception as e:
            processing_time = time.time() - process_start_time
            error_msg = f"Frame processing error: {str(e)}"
            
            result = ProcessingResult(
                frame_id=queued_frame.metadata.frame_id,
                human_present=False,
                confidence=0.0,
                processing_time=processing_time,
                timestamp=time.time(),
                source=queued_frame.metadata.source,
                error_occurred=True,
                error_message=error_msg
            )
            
            with self._lock:
                self._frames_failed += 1
            
            logger.error(f"Error processing frame {queued_frame.metadata.frame_id}: {e}")
            return result
    
    async def process_frames_continuously(self) -> None:
        """
        Process frames continuously until stopped.
        
        This method runs a processing loop that pulls frames from the queue
        and processes them concurrently up to the configured limit.
        """
        logger.info("Starting continuous frame processing")
        
        while self.is_running and not self._shutdown_event.is_set():
            try:
                # Acquire semaphore to limit concurrency
                async with self._semaphore:
                    # Get next frame
                    queued_frame = self.frame_queue.get_frame(
                        timeout=self.queue_timeout,
                        include_metadata=True
                    )
                    
                    if queued_frame is None:
                        await asyncio.sleep(0.01)  # Brief pause if no frames
                        continue
                    
                    # Start processing task
                    task = asyncio.create_task(
                        self._process_frame(queued_frame, 0.0)
                    )
                    
                    self._active_tasks.add(task)
                    self._processing_tasks.add(task)
                    
                    # Update peak concurrent tasks
                    with self._lock:
                        current_tasks = len(self._processing_tasks)
                        if current_tasks > self._peak_concurrent_tasks:
                            self._peak_concurrent_tasks = current_tasks
                    
                    # Add callback to remove completed tasks
                    task.add_done_callback(
                        lambda t: self._processing_tasks.discard(t)
                    )
                    task.add_done_callback(
                        lambda t: self._active_tasks.discard(t)
                    )
                    
            except Exception as e:
                logger.error(f"Error in continuous processing loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
        
        logger.info("Continuous frame processing stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary containing processing metrics
        """
        with self._lock:
            uptime = time.time() - self._start_time
            
            return {
                'frames_processed': self._frames_processed,
                'frames_failed': self._frames_failed,
                'success_rate': (
                    self._frames_processed / max(self._frames_processed + self._frames_failed, 1)
                ),
                'average_processing_time': (
                    self._total_processing_time / max(self._frames_processed, 1)
                ),
                'average_queue_wait_time': (
                    self._total_queue_wait_time / max(self._frames_processed, 1)
                ),
                'peak_concurrent_tasks': self._peak_concurrent_tasks,
                'current_active_tasks': len(self._active_tasks),
                'uptime': uptime,
                'is_running': self.is_running
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get detailed performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        with self._lock:
            stats = {
                'frames_per_second': 0.0,
                'average_queue_wait_time': 0.0,
                'peak_concurrent_tasks': self._peak_concurrent_tasks,
                'recent_processing_times': list(self._processing_times),
                'recent_queue_wait_times': list(self._queue_wait_times)
            }
            
            # Calculate FPS from recent frame timestamps
            if len(self._frame_timestamps) >= 2:
                time_span = self._frame_timestamps[-1] - self._frame_timestamps[0]
                if time_span > 0:
                    stats['frames_per_second'] = (len(self._frame_timestamps) - 1) / time_span
            
            # Calculate average queue wait time
            if self._queue_wait_times:
                stats['average_queue_wait_time'] = (
                    sum(self._queue_wait_times) / len(self._queue_wait_times)
                )
            
            return stats
    
    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        with self._lock:
            self._frames_processed = 0
            self._frames_failed = 0
            self._total_processing_time = 0.0
            self._total_queue_wait_time = 0.0
            self._peak_concurrent_tasks = 0
            self._start_time = time.time()
            self._processing_times.clear()
            self._queue_wait_times.clear()
            self._frame_timestamps.clear()
        
        logger.info("Processing statistics reset")
    
    async def __aenter__(self) -> 'FrameProcessor':
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with cleanup."""
        await self.stop()
        logger.debug("Frame processor context manager cleanup completed") 