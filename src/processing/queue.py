"""
Frame queue functionality for webcam human detection application.

This module provides thread-safe frame queuing with overflow handling,
statistics tracking, and performance monitoring for the asynchronous
processing pipeline.
"""
import logging
import time
import threading
from queue import Queue, Empty, Full
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass, field
from collections import deque
import numpy as np


# Set up module logger
logger = logging.getLogger(__name__)


@dataclass
class FrameMetadata:
    """Metadata associated with a frame."""
    timestamp: float = field(default_factory=time.time)
    frame_id: int = 0
    source: str = "unknown"
    processing_hints: Dict[str, Any] = field(default_factory=dict)
    
    def age(self) -> float:
        """Get age of frame in seconds."""
        return time.time() - self.timestamp


@dataclass
class QueuedFrame:
    """Frame with associated metadata."""
    frame: np.ndarray
    metadata: FrameMetadata
    
    def __post_init__(self):
        """Validate frame after initialization."""
        if not isinstance(self.frame, np.ndarray):
            raise ValueError("Frame must be numpy array")


class FrameQueueError(Exception):
    """Exception raised for frame queue-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize FrameQueueError.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Chain exceptions for better debugging
        if original_error:
            self.__cause__ = original_error


class FrameQueue:
    """
    Thread-safe frame queue for asynchronous frame processing.
    
    This class provides a thread-safe queue for video frames with configurable
    overflow handling, statistics tracking, and performance monitoring.
    Supports multiple overflow strategies: drop_oldest, drop_newest, block.
    
    Enhanced features:
    - Frame metadata tracking
    - Queue health monitoring  
    - Auto-cleanup of stale frames
    - Batch operations
    - Frame deduplication
    """
    
    def __init__(
        self,
        max_size: int = 10,
        overflow_strategy: str = 'drop_oldest',
        auto_cleanup: bool = True,
        max_frame_age: float = 5.0,
        enable_deduplication: bool = False,
        dedup_threshold: float = 0.95
    ):
        """
        Initialize frame queue.
        
        Args:
            max_size: Maximum number of frames in queue
            overflow_strategy: How to handle overflow ('drop_oldest', 'drop_newest', 'block')
            auto_cleanup: Enable automatic cleanup of stale frames
            max_frame_age: Maximum age of frames in seconds before cleanup
            enable_deduplication: Enable frame deduplication
            dedup_threshold: Similarity threshold for deduplication (0.0-1.0)
            
        Raises:
            FrameQueueError: If max_size is invalid
        """
        if max_size <= 0:
            raise FrameQueueError("Queue size must be positive")
        
        self.max_size = max_size
        self.overflow_strategy = overflow_strategy
        self.auto_cleanup = auto_cleanup
        self.max_frame_age = max_frame_age
        self.enable_deduplication = enable_deduplication
        self.dedup_threshold = dedup_threshold
        
        # Internal queue implementation
        self._queue = Queue(maxsize=max_size)
        self._lock = threading.RLock()
        
        # Statistics tracking
        self._frames_added = 0
        self._frames_removed = 0
        self._frames_dropped = 0
        self._frames_deduplicated = 0
        self._frames_cleaned = 0
        self._peak_size = 0
        self._next_frame_id = 0
        
        # Performance tracking
        self._put_times: deque = deque(maxlen=100)
        self._get_times: deque = deque(maxlen=100)
        self._start_time = time.time()
        
        # Health monitoring
        self._health_stats = {
            'last_cleanup': time.time(),
            'cleanup_count': 0,
            'queue_full_count': 0,
            'queue_empty_count': 0,
            'avg_queue_size': 0.0,
            'size_samples': deque(maxlen=50)
        }
        
        # Deduplication tracking
        self._last_frame_hash: Optional[int] = None
        
        # Cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        if self.auto_cleanup:
            self._start_cleanup_thread()
        
        logger.info(f"Frame queue initialized with max_size={max_size}, "
                   f"overflow_strategy={overflow_strategy}, auto_cleanup={auto_cleanup}, "
                   f"deduplication={enable_deduplication}")
    
    def _start_cleanup_thread(self) -> None:
        """Start automatic cleanup thread."""
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            name="FrameQueueCleanup",
            daemon=True
        )
        self._cleanup_thread.start()
        logger.debug("Started cleanup worker thread")
    
    def _cleanup_worker(self) -> None:
        """Worker thread for automatic frame cleanup."""
        while not self._shutdown_event.is_set():
            try:
                self._cleanup_stale_frames()
                self._update_health_metrics()
                time.sleep(1.0)  # Check every second
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(5.0)  # Back off on error
    
    def _cleanup_stale_frames(self) -> None:
        """Remove frames that are too old."""
        if not self.auto_cleanup:
            return
        
        current_time = time.time()
        frames_to_requeue = []
        cleaned_count = 0
        
        with self._lock:
            # Extract all frames to check ages
            while not self._queue.empty():
                try:
                    queued_frame = self._queue.get_nowait()
                    if current_time - queued_frame.metadata.timestamp <= self.max_frame_age:
                        frames_to_requeue.append(queued_frame)
                    else:
                        cleaned_count += 1
                except Empty:
                    break
            
            # Re-queue valid frames
            for frame in frames_to_requeue:
                try:
                    self._queue.put_nowait(frame)
                except Full:
                    # Queue full, drop frames
                    break
            
            if cleaned_count > 0:
                self._frames_cleaned += cleaned_count
                self._health_stats['cleanup_count'] += 1
                self._health_stats['last_cleanup'] = current_time
                logger.debug(f"Cleaned {cleaned_count} stale frames")
    
    def _update_health_metrics(self) -> None:
        """Update queue health metrics."""
        current_size = self.size()
        self._health_stats['size_samples'].append(current_size)
        
        if self._health_stats['size_samples']:
            self._health_stats['avg_queue_size'] = (
                sum(self._health_stats['size_samples']) / 
                len(self._health_stats['size_samples'])
            )
    
    def _compute_frame_hash(self, frame: np.ndarray) -> int:
        """Compute simple hash of frame for deduplication."""
        # Use a downsampled version for efficiency
        small_frame = frame[::8, ::8]  # Sample every 8th pixel
        return hash(small_frame.tobytes())
    
    def _frames_similar(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        """Check if two frames are similar (for deduplication)."""
        if frame1.shape != frame2.shape:
            return False
        
        # Quick pixel-wise comparison on downsampled frames
        small1 = frame1[::8, ::8]
        small2 = frame2[::8, ::8]
        
        # Calculate normalized correlation
        diff = np.abs(small1.astype(np.float32) - small2.astype(np.float32))
        similarity = 1.0 - (np.mean(diff) / 255.0)
        
        return similarity >= self.dedup_threshold
    
    def put_frame(
        self, 
        frame: Union[np.ndarray, QueuedFrame], 
        timeout: Optional[float] = None,
        metadata: Optional[FrameMetadata] = None,
        source: str = "camera"
    ) -> None:
        """
        Add frame to the queue.
        
        Args:
            frame: Frame to add to queue (numpy array or QueuedFrame)
            timeout: Timeout for blocking operations (None for no timeout)
            metadata: Optional frame metadata
            source: Source identifier for the frame
            
        Raises:
            FrameQueueError: If frame is invalid or operation times out
        """
        start_time = time.time()
        
        # Handle different input types
        if isinstance(frame, QueuedFrame):
            queued_frame = frame
        else:
            # Validate frame
            self._validate_frame(frame)
            
            # Check for deduplication
            if self.enable_deduplication and self._last_frame_hash is not None:
                frame_hash = self._compute_frame_hash(frame)
                if frame_hash == self._last_frame_hash:
                    self._frames_deduplicated += 1
                    logger.debug("Dropped duplicate frame")
                    return
                self._last_frame_hash = frame_hash
            
            # Create metadata if not provided
            if metadata is None:
                metadata = FrameMetadata(
                    frame_id=self._next_frame_id,
                    source=source
                )
                self._next_frame_id += 1
            
            queued_frame = QueuedFrame(frame=frame, metadata=metadata)
        
        with self._lock:
            if self.overflow_strategy == 'block':
                try:
                    self._queue.put(queued_frame, timeout=timeout)
                    self._frames_added += 1
                    self._update_peak_size()
                except Full:
                    self._health_stats['queue_full_count'] += 1
                    raise FrameQueueError("Queue put operation timed out")
            
            elif self.overflow_strategy == 'drop_newest':
                if self._queue.full():
                    # Don't add the new frame
                    self._frames_dropped += 1
                    self._health_stats['queue_full_count'] += 1
                    logger.debug("Dropped newest frame due to full queue")
                else:
                    self._queue.put_nowait(queued_frame)
                    self._frames_added += 1
                    self._update_peak_size()
            
            elif self.overflow_strategy == 'drop_oldest':
                if self._queue.full():
                    # Remove oldest frame to make space
                    try:
                        self._queue.get_nowait()
                        self._frames_dropped += 1
                        self._health_stats['queue_full_count'] += 1
                        logger.debug("Dropped oldest frame due to full queue")
                    except Empty:
                        pass  # Race condition, queue empty now
                
                self._queue.put_nowait(queued_frame)
                self._frames_added += 1
                self._update_peak_size()
            
            else:
                raise FrameQueueError(f"Unknown overflow strategy: {self.overflow_strategy}")
        
        # Track timing
        put_time = time.time() - start_time
        self._put_times.append(put_time)
    
    def get_frame(
        self, 
        timeout: Optional[float] = None,
        include_metadata: bool = False
    ) -> Optional[Union[np.ndarray, QueuedFrame]]:
        """
        Get frame from the queue.
        
        Args:
            timeout: Timeout for blocking operations (None for no timeout)
            include_metadata: Return QueuedFrame with metadata instead of just frame
            
        Returns:
            Frame from queue (numpy array or QueuedFrame), or None if queue is empty
        """
        start_time = time.time()
        
        try:
            if timeout is not None:
                queued_frame = self._queue.get(timeout=timeout)
            else:
                queued_frame = self._queue.get_nowait()
            
            with self._lock:
                self._frames_removed += 1
            
            # Track timing
            get_time = time.time() - start_time
            self._get_times.append(get_time)
            
            # Return based on requested format
            if include_metadata:
                return queued_frame
            else:
                return queued_frame.frame
            
        except Empty:
            self._health_stats['queue_empty_count'] += 1
            return None
    
    def get_frames_batch(
        self, 
        max_count: int, 
        timeout: Optional[float] = None,
        include_metadata: bool = False
    ) -> List[Union[np.ndarray, QueuedFrame]]:
        """
        Get multiple frames from queue.
        
        Args:
            max_count: Maximum number of frames to retrieve
            timeout: Timeout for first frame (subsequent frames are non-blocking)
            include_metadata: Return QueuedFrames with metadata
            
        Returns:
            List of frames (up to max_count)
        """
        frames = []
        
        # Get first frame with timeout
        first_frame = self.get_frame(timeout=timeout, include_metadata=include_metadata)
        if first_frame is not None:
            frames.append(first_frame)
        
        # Get additional frames without timeout
        for _ in range(max_count - 1):
            frame = self.get_frame(timeout=0, include_metadata=include_metadata)
            if frame is None:
                break
            frames.append(frame)
        
        return frames
    
    def put_frames_batch(
        self,
        frames: List[Union[np.ndarray, QueuedFrame]],
        source: str = "batch"
    ) -> int:
        """
        Add multiple frames to queue.
        
        Args:
            frames: List of frames to add
            source: Source identifier for the frames
            
        Returns:
            Number of frames successfully added
        """
        added_count = 0
        
        for frame in frames:
            try:
                self.put_frame(frame, timeout=0, source=source)
                added_count += 1
            except FrameQueueError:
                # Continue with remaining frames
                pass
        
        return added_count
    
    def peek_frame(self, include_metadata: bool = False) -> Optional[Union[np.ndarray, QueuedFrame]]:
        """
        Peek at next frame without removing it.
        
        Args:
            include_metadata: Return QueuedFrame with metadata
            
        Returns:
            Next frame or None if queue is empty
        """
        try:
            # Get frame and immediately put it back
            queued_frame = self._queue.get_nowait()
            self._queue.put_nowait(queued_frame)
            
            if include_metadata:
                return queued_frame
            else:
                return queued_frame.frame
        except (Empty, Full):
            return None
    
    def _validate_frame(self, frame: Any) -> None:
        """
        Validate frame format.
        
        Args:
            frame: Frame to validate
            
        Raises:
            FrameQueueError: If frame is invalid
        """
        if not isinstance(frame, np.ndarray):
            raise FrameQueueError("Frame must be numpy array")
        
        if len(frame.shape) not in [2, 3]:
            raise FrameQueueError("Frame must be 2D or 3D array")
    
    def _update_peak_size(self) -> None:
        """Update peak size statistic."""
        current_size = self._queue.qsize()
        if current_size > self._peak_size:
            self._peak_size = current_size
    
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def is_full(self) -> bool:
        """Check if queue is full."""
        return self._queue.full()
    
    def clear(self) -> None:
        """Clear all frames from queue."""
        with self._lock:
            # Remove all frames
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except Empty:
                    break
        
        # Reset deduplication tracking
        self._last_frame_hash = None
        
        logger.debug("Queue cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Dictionary containing queue metrics
        """
        with self._lock:
            return {
                'frames_added': self._frames_added,
                'frames_removed': self._frames_removed,
                'frames_dropped': self._frames_dropped,
                'frames_deduplicated': self._frames_deduplicated,
                'frames_cleaned': self._frames_cleaned,
                'current_size': self.size(),
                'max_size': self.max_size,
                'peak_size': self._peak_size,
                'overflow_strategy': self.overflow_strategy,
                'uptime': time.time() - self._start_time,
                'auto_cleanup': self.auto_cleanup,
                'deduplication_enabled': self.enable_deduplication
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        stats = {
            'peak_size': self._peak_size,
            'average_put_time': 0.0,
            'average_get_time': 0.0,
            'min_put_time': 0.0,
            'max_put_time': 0.0,
            'min_get_time': 0.0,
            'max_get_time': 0.0
        }
        
        # Calculate put time statistics
        if self._put_times:
            stats['average_put_time'] = sum(self._put_times) / len(self._put_times)
            stats['min_put_time'] = min(self._put_times)
            stats['max_put_time'] = max(self._put_times)
        
        # Calculate get time statistics
        if self._get_times:
            stats['average_get_time'] = sum(self._get_times) / len(self._get_times)
            stats['min_get_time'] = min(self._get_times)
            stats['max_get_time'] = max(self._get_times)
        
        return stats
    
    def get_health_stats(self) -> Dict[str, Any]:
        """
        Get queue health statistics.
        
        Returns:
            Dictionary containing health metrics
        """
        return {
            **self._health_stats,
            'queue_utilization': self.size() / self.max_size,
            'frames_per_second': self._frames_added / (time.time() - self._start_time) if self._frames_added > 0 else 0.0,
            'drop_rate': self._frames_dropped / max(self._frames_added, 1),
            'dedup_rate': self._frames_deduplicated / max(self._frames_added, 1),
            'cleanup_rate': self._frames_cleaned / max(self._frames_added, 1)
        }
    
    def shutdown(self) -> None:
        """Shutdown queue and cleanup resources."""
        logger.info("Shutting down frame queue")
        
        # Signal shutdown to cleanup thread
        self._shutdown_event.set()
        
        # Wait for cleanup thread to finish
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=2.0)
            if self._cleanup_thread.is_alive():
                logger.warning("Cleanup thread did not stop gracefully")
        
        # Clear remaining frames
        self.clear()
    
    def __enter__(self) -> 'FrameQueue':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        self.shutdown()
        logger.debug("Frame queue context manager cleanup completed") 