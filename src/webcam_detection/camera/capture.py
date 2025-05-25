"""
Frame capture functionality for webcam human detection application.

This module provides frame capture, preprocessing, and validation capabilities
that integrate with the camera manager.
"""
import logging
import time
import threading
from queue import Queue, Empty
from typing import Optional, Dict, Any, List, Tuple, Callable
import cv2
import numpy as np

from .manager import CameraManager, CameraError


# Set up module logger
logger = logging.getLogger(__name__)


class FrameCaptureError(Exception):
    """Exception raised for frame capture-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize FrameCaptureError.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Chain exceptions for better debugging
        if original_error:
            self.__cause__ = original_error


class FrameCapture:
    """
    Frame capture class for handling video frame acquisition and preprocessing.
    
    This class provides frame capture functionality that integrates with the
    CameraManager, including preprocessing, validation, rate limiting, and
    performance monitoring. Supports both synchronous and threaded capture modes.
    """
    
    def __init__(
        self,
        camera_manager: CameraManager,
        enable_preprocessing: bool = False,
        target_size: Optional[Tuple[int, int]] = None,
        color_format: str = 'BGR',
        max_fps: Optional[float] = None,
        threaded: bool = False,
        buffer_size: int = 3,
        frame_callback: Optional[Callable[[np.ndarray], None]] = None
    ):
        """
        Initialize frame capture with camera manager.
        
        Args:
            camera_manager: Camera manager instance
            enable_preprocessing: Enable frame preprocessing
            target_size: Target frame size (height, width) for resizing
            color_format: Target color format ('BGR', 'RGB', 'GRAY')
            max_fps: Maximum capture frame rate (None for unlimited)
            threaded: Enable threaded capture mode
            buffer_size: Frame buffer size for threaded mode
            frame_callback: Optional callback for each captured frame
            
        Raises:
            FrameCaptureError: If camera manager is not initialized
        """
        if not camera_manager.is_initialized:
            raise FrameCaptureError("Camera manager not initialized")
        
        self.camera_manager = camera_manager
        self.enable_preprocessing = enable_preprocessing
        self.target_size = target_size
        self.color_format = color_format
        self.max_fps = max_fps
        self.threaded = threaded
        self.buffer_size = buffer_size
        self.frame_callback = frame_callback
        
        # State tracking
        self.is_running = False
        self.frame_count = 0
        self._frames_failed = 0
        self._validation_warnings: List[str] = []
        
        # Performance tracking
        self._start_time = time.time()
        self._last_frame_time = 0.0
        self._frame_intervals: List[float] = []
        self._processing_times: List[float] = []
        self._capture_errors = 0
        self._consecutive_failures = 0
        self._max_consecutive_failures = 10
        
        # Rate limiting
        self._min_frame_interval = 1.0 / max_fps if max_fps else 0.0
        
        # Threaded capture
        self._frame_queue: Optional[Queue] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        if self.threaded:
            self._setup_threaded_capture()
        
        logger.info(f"Frame capture initialized with preprocessing={enable_preprocessing}, "
                   f"max_fps={max_fps}, target_size={target_size}, threaded={threaded}")
    
    def _setup_threaded_capture(self) -> None:
        """Setup threaded capture infrastructure."""
        self._frame_queue = Queue(maxsize=self.buffer_size)
        self._stop_event.clear()
        logger.debug("Threaded capture infrastructure initialized")
    
    def start_threaded_capture(self) -> None:
        """Start threaded frame capture."""
        if not self.threaded:
            raise FrameCaptureError("Threaded capture not enabled")
        
        if self._capture_thread and self._capture_thread.is_alive():
            logger.warning("Threaded capture already running")
            return
        
        self._stop_event.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_worker,
            name="FrameCaptureWorker",
            daemon=True
        )
        self._capture_thread.start()
        self.is_running = True
        
        logger.info("Started threaded frame capture")
    
    def stop_threaded_capture(self) -> None:
        """Stop threaded frame capture."""
        if not self.threaded:
            return
        
        self._stop_event.set()
        self.is_running = False
        
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)
            if self._capture_thread.is_alive():
                logger.warning("Capture thread did not stop gracefully")
        
        # Clear remaining frames in queue
        if self._frame_queue:
            while not self._frame_queue.empty():
                try:
                    self._frame_queue.get_nowait()
                except Empty:
                    break
        
        logger.info("Stopped threaded frame capture")
    
    def _capture_worker(self) -> None:
        """Worker thread for continuous frame capture."""
        logger.debug("Frame capture worker thread started")
        
        while not self._stop_event.is_set():
            try:
                # Apply rate limiting
                if self._min_frame_interval > 0:
                    time.sleep(self._min_frame_interval)
                
                # Capture frame
                frame = self._capture_single_frame()
                
                if frame is not None:
                    # Add to queue (non-blocking)
                    if self._frame_queue.full():
                        # Remove oldest frame to make space
                        try:
                            self._frame_queue.get_nowait()
                            logger.debug("Dropped frame due to full buffer")
                        except Empty:
                            pass
                    
                    self._frame_queue.put_nowait(frame)
                    
                    # Call frame callback if provided
                    if self.frame_callback:
                        try:
                            self.frame_callback(frame)
                        except Exception as e:
                            logger.error(f"Frame callback error: {e}")
                
            except Exception as e:
                logger.error(f"Error in capture worker: {e}")
                self._capture_errors += 1
                time.sleep(0.1)  # Brief pause on error
        
        logger.debug("Frame capture worker thread stopped")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capture a frame from the camera.
        
        Returns:
            Frame as numpy array, or None if capture fails
            
        Raises:
            FrameCaptureError: If frame capture encounters an error
        """
        if self.threaded:
            return self._get_threaded_frame()
        else:
            return self._capture_single_frame()
    
    def _get_threaded_frame(self) -> Optional[np.ndarray]:
        """Get frame from threaded capture queue."""
        if not self._frame_queue:
            raise FrameCaptureError("Threaded capture not initialized")
        
        try:
            # Non-blocking get with timeout
            frame = self._frame_queue.get(timeout=0.1)
            return frame
        except Empty:
            logger.debug("No frame available in queue")
            return None
    
    def _capture_single_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame (synchronous mode).
        
        Returns:
            Frame as numpy array, or None if capture fails
        """
        start_time = time.time()
        
        try:
            # Rate limiting for synchronous mode
            if not self.threaded and self._min_frame_interval > 0:
                current_time = time.time()
                if self._last_frame_time > 0:
                    elapsed = current_time - self._last_frame_time
                    if elapsed < self._min_frame_interval:
                        sleep_time = self._min_frame_interval - elapsed
                        time.sleep(sleep_time)
            
            # Capture frame from camera manager
            frame = self.camera_manager.get_frame()
            
            if frame is None:
                self._frames_failed += 1
                self._consecutive_failures += 1
                logger.debug("Frame capture returned None")
                
                # Check for excessive failures
                if self._consecutive_failures >= self._max_consecutive_failures:
                    logger.error(f"Too many consecutive capture failures: {self._consecutive_failures}")
                    raise FrameCaptureError(f"Excessive capture failures: {self._consecutive_failures}")
                
                return None
            
            # Reset consecutive failure counter on success
            self._consecutive_failures = 0
            
            # Validate frame
            self._validate_frame(frame)
            
            # Preprocess if enabled
            if self.enable_preprocessing:
                frame = self._preprocess_frame(frame)
            
            # Update statistics
            processing_time = time.time() - start_time
            self._processing_times.append(processing_time)
            
            # Keep only last 50 processing times
            if len(self._processing_times) > 50:
                self._processing_times.pop(0)
            
            self._update_statistics()
            self.frame_count += 1
            
            return frame
            
        except CameraError as e:
            self._frames_failed += 1
            self._consecutive_failures += 1
            logger.error(f"Camera error during frame capture: {e}")
            raise FrameCaptureError(f"Frame capture failed: {e}", e)
        except Exception as e:
            self._frames_failed += 1
            self._consecutive_failures += 1
            logger.error(f"Unexpected error during frame capture: {e}")
            raise FrameCaptureError(f"Frame capture failed: {e}", e)
    
    def _validate_frame(self, frame: np.ndarray) -> None:
        """
        Validate captured frame format and dimensions.
        
        Args:
            frame: Frame to validate
        """
        if frame is None:
            return
        
        # Validate frame is numpy array
        if not isinstance(frame, np.ndarray):
            warning = f"Frame is not numpy array, got {type(frame)}"
            self._validation_warnings.append(warning)
            logger.warning(warning)
            return
        
        # Validate dimensions against expected config
        expected_height = self.camera_manager.config.height
        expected_width = self.camera_manager.config.width
        
        actual_height, actual_width = frame.shape[:2]
        
        if actual_height != expected_height or actual_width != expected_width:
            warning = (f"Frame dimension mismatch: expected {expected_width}x{expected_height}, "
                      f"got {actual_width}x{actual_height}")
            self._validation_warnings.append(warning)
            logger.warning(warning)
        
        # Validate channel count
        if len(frame.shape) == 2:
            # Grayscale
            warning = "Frame has 1 channel (grayscale) instead of expected 3 channels (RGB/BGR)"
            self._validation_warnings.append(warning)
            logger.debug(warning)  # Debug level for less critical warning
        elif len(frame.shape) == 3 and frame.shape[2] != 3:
            # Wrong channel count
            warning = f"Frame has {frame.shape[2]} channels instead of expected 3 channels"
            self._validation_warnings.append(warning)
            logger.warning(warning)
        
        # Validate data type
        if frame.dtype != np.uint8:
            warning = f"Frame has unexpected dtype: {frame.dtype} (expected uint8)"
            self._validation_warnings.append(warning)
            logger.warning(warning)
        
        # Validate frame content (basic checks)
        if np.all(frame == 0):
            warning = "Frame appears to be all black (potential capture issue)"
            self._validation_warnings.append(warning)
            logger.warning(warning)
        elif np.all(frame == 255):
            warning = "Frame appears to be all white (potential overexposure)"
            self._validation_warnings.append(warning)
            logger.warning(warning)
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame (resize, color conversion, etc.).
        
        Args:
            frame: Input frame
            
        Returns:
            Preprocessed frame
        """
        processed_frame = frame.copy()
        
        # Resize if target size specified
        if self.target_size:
            target_height, target_width = self.target_size
            current_height, current_width = processed_frame.shape[:2]
            
            if current_height != target_height or current_width != target_width:
                processed_frame = cv2.resize(
                    processed_frame, 
                    (target_width, target_height),
                    interpolation=cv2.INTER_LINEAR
                )
                logger.debug(f"Resized frame from {current_width}x{current_height} "
                           f"to {target_width}x{target_height}")
        
        # Color format conversion
        if self.color_format == 'RGB' and len(processed_frame.shape) == 3:
            # Convert BGR to RGB
            processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            logger.debug("Converted frame from BGR to RGB")
        elif self.color_format == 'GRAY':
            # Convert to grayscale
            if len(processed_frame.shape) == 3:
                processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
                logger.debug("Converted frame to grayscale")
        
        return processed_frame
    
    def _update_statistics(self) -> None:
        """Update performance and timing statistics."""
        current_time = time.time()
        
        if self._last_frame_time > 0:
            interval = current_time - self._last_frame_time
            self._frame_intervals.append(interval)
            
            # Keep only last 50 intervals for averaging
            if len(self._frame_intervals) > 50:
                self._frame_intervals.pop(0)
        
        self._last_frame_time = current_time
    
    def get_validation_warnings(self) -> List[str]:
        """Get list of frame validation warnings."""
        return self._validation_warnings.copy()
    
    def clear_validation_warnings(self) -> None:
        """Clear validation warnings list."""
        self._validation_warnings.clear()
        logger.debug("Cleared validation warnings")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get frame capture statistics.
        
        Returns:
            Dictionary containing capture metrics
        """
        total_attempts = self.frame_count + self._frames_failed
        success_rate = self.frame_count / total_attempts if total_attempts > 0 else 0.0
        
        stats = {
            'frames_captured': self.frame_count,
            'frames_failed': self._frames_failed,
            'success_rate': success_rate,
            'total_time': time.time() - self._start_time,
            'validation_warnings': len(self._validation_warnings),
            'consecutive_failures': self._consecutive_failures,
            'capture_errors': self._capture_errors,
            'is_running': self.is_running,
            'threaded_mode': self.threaded
        }
        
        # Add FPS statistics if we have intervals
        if self._frame_intervals:
            avg_interval = sum(self._frame_intervals) / len(self._frame_intervals)
            stats['average_fps'] = 1.0 / avg_interval if avg_interval > 0 else 0.0
            stats['min_fps'] = 1.0 / max(self._frame_intervals) if self._frame_intervals else 0.0
            stats['max_fps'] = 1.0 / min(self._frame_intervals) if self._frame_intervals else 0.0
        else:
            stats['average_fps'] = 0.0
        
        # Add processing time statistics
        if self._processing_times:
            stats['avg_processing_time'] = sum(self._processing_times) / len(self._processing_times)
            stats['min_processing_time'] = min(self._processing_times)
            stats['max_processing_time'] = max(self._processing_times)
        else:
            stats['avg_processing_time'] = 0.0
        
        # Add queue statistics for threaded mode
        if self.threaded and self._frame_queue:
            stats['queue_size'] = self._frame_queue.qsize()
            stats['queue_full'] = self._frame_queue.full()
        
        return stats
    
    def get_buffer_info(self) -> Dict[str, Any]:
        """Get information about frame buffer (threaded mode only)."""
        if not self.threaded or not self._frame_queue:
            return {'error': 'Threaded mode not enabled'}
        
        return {
            'buffer_size': self.buffer_size,
            'current_size': self._frame_queue.qsize(),
            'utilization': self._frame_queue.qsize() / self.buffer_size,
            'is_full': self._frame_queue.full(),
            'is_empty': self._frame_queue.empty()
        }
    
    def cleanup(self) -> None:
        """Clean up resources and reset statistics."""
        logger.info("Cleaning up frame capture resources")
        
        # Stop threaded capture if running
        if self.threaded:
            self.stop_threaded_capture()
        
        # Reset statistics
        self.frame_count = 0
        self._frames_failed = 0
        self._validation_warnings.clear()
        self._frame_intervals.clear()
        self._processing_times.clear()
        self._capture_errors = 0
        self._consecutive_failures = 0
        self._start_time = time.time()
        self._last_frame_time = 0.0
        self.is_running = False
    
    def __enter__(self) -> 'FrameCapture':
        """Context manager entry."""
        if self.threaded:
            self.start_threaded_capture()
        else:
            self.is_running = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        self.cleanup() 