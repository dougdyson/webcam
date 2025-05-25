"""
Camera manager for webcam human detection application.

This module provides camera access, initialization, and frame capture management
using OpenCV VideoCapture.
"""
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
import cv2
import numpy as np

from .config import CameraConfig


# Set up module logger
logger = logging.getLogger(__name__)


class CameraError(Exception):
    """Exception raised for camera-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize CameraError.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Chain exceptions for better debugging
        if original_error:
            self.__cause__ = original_error


class CameraManager:
    """
    Camera manager for handling video capture operations.
    
    This class provides camera initialization, configuration, frame capture,
    and resource management functionality with advanced capability detection
    and error recovery.
    """
    
    def __init__(self, config: CameraConfig):
        """
        Initialize camera manager with configuration.
        
        Args:
            config: Camera configuration
            
        Raises:
            CameraError: If camera initialization fails
        """
        self.config = config
        self._cap: Optional[cv2.VideoCapture] = None
        self._is_initialized = False
        self._configuration_warnings: List[str] = []
        self._frame_count = 0
        self._last_frame_time = 0.0
        self._fps_history: List[float] = []
        self._supported_resolutions: List[Tuple[int, int]] = []
        self._supported_formats: List[str] = []
        
        logger.info(f"Initializing camera manager with config: {config}")
        
        try:
            self._initialize_camera()
            self._detect_capabilities()
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            raise CameraError(f"Failed to initialize camera: {e}", e)
    
    def _initialize_camera(self) -> None:
        """Initialize the camera with configuration settings."""
        try:
            # Create VideoCapture instance
            self._cap = cv2.VideoCapture(self.config.device_id)
            
            if not self._cap.isOpened():
                raise CameraError(f"Camera device {self.config.device_id} could not be opened")
            
            # Apply configuration properties
            self._apply_configuration()
            
            # Verify configuration was applied
            self._validate_configuration()
            
            self._is_initialized = True
            logger.info("Camera initialized successfully")
            
        except Exception as e:
            if self._cap:
                self._cap.release()
                self._cap = None
            raise
    
    def _apply_configuration(self) -> None:
        """Apply camera configuration properties."""
        if not self._cap:
            return
        
        # Get OpenCV property mappings from config
        properties = self.config.get_opencv_properties()
        
        logger.debug(f"Applying camera properties: {properties}")
        
        for prop, value in properties.items():
            success = self._cap.set(prop, value)
            if not success:
                logger.warning(f"Failed to set camera property {prop} to {value}")
    
    def _validate_configuration(self) -> None:
        """Validate that camera configuration was applied correctly."""
        if not self._cap:
            return
        
        # Check actual vs requested resolution
        actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        
        if actual_width != self.config.width or actual_height != self.config.height:
            warning = (f"Camera resolution fallback: requested {self.config.width}x{self.config.height}, "
                      f"got {actual_width}x{actual_height}")
            self._configuration_warnings.append(warning)
            logger.warning(warning)
        
        if abs(actual_fps - self.config.fps) > 1:
            warning = (f"Camera FPS fallback: requested {self.config.fps}, "
                      f"got {actual_fps}")
            self._configuration_warnings.append(warning)
            logger.warning(warning)
    
    def _detect_capabilities(self) -> None:
        """Detect and catalog camera capabilities."""
        if not self._cap:
            return
        
        logger.debug("Detecting camera capabilities")
        
        # Store original settings
        original_width = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        original_height = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        # Test common resolutions
        test_resolutions = [
            (320, 240),   # QVGA
            (640, 480),   # VGA
            (800, 600),   # SVGA
            (1024, 768),  # XGA
            (1280, 720),  # HD
            (1280, 1024), # SXGA
            (1920, 1080), # FHD
            (2560, 1440), # QHD
            (3840, 2160)  # UHD
        ]
        
        supported_resolutions = []
        for width, height in test_resolutions:
            try:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                
                # Verify the resolution was actually set
                actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                
                if actual_width == width and actual_height == height:
                    supported_resolutions.append((width, height))
                    logger.debug(f"Resolution {width}x{height} supported")
                
            except Exception as e:
                logger.debug(f"Resolution {width}x{height} not supported: {e}")
        
        self._supported_resolutions = supported_resolutions
        
        # Restore original settings
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, original_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, original_height)
        
        logger.info(f"Detected {len(supported_resolutions)} supported resolutions")
    
    @property
    def is_initialized(self) -> bool:
        """Check if camera is initialized."""
        return self._is_initialized
    
    def is_available(self) -> bool:
        """Check if camera is available and working."""
        if not self._cap:
            return False
        return self._cap.isOpened()
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Capture a frame from the camera.
        
        Returns:
            Frame as numpy array, or None if capture fails
            
        Raises:
            CameraError: If frame capture encounters an error
        """
        if not self._cap or not self.is_available():
            logger.warning("Camera not available for frame capture")
            return None
        
        try:
            ret, frame = self._cap.read()
            
            if not ret or frame is None:
                logger.debug("Frame capture failed")
                return None
            
            # Update performance metrics
            self._update_performance_metrics()
            
            return frame
            
        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            raise CameraError(f"Frame capture failed: {e}", e)
    
    def _update_performance_metrics(self) -> None:
        """Update performance tracking metrics."""
        current_time = time.time()
        
        if self._last_frame_time > 0:
            frame_interval = current_time - self._last_frame_time
            if frame_interval > 0:
                fps = 1.0 / frame_interval
                self._fps_history.append(fps)
                
                # Keep only last 30 FPS measurements
                if len(self._fps_history) > 30:
                    self._fps_history.pop(0)
        
        self._frame_count += 1
        self._last_frame_time = current_time
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get camera capabilities and properties.
        
        Returns:
            Dictionary of camera capabilities
        """
        if not self._cap:
            return {}
        
        capabilities = {}
        
        try:
            capabilities['max_width'] = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            capabilities['max_height'] = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            capabilities['max_fps'] = self._cap.get(cv2.CAP_PROP_FPS)
            capabilities['brightness'] = self._cap.get(cv2.CAP_PROP_BRIGHTNESS)
            capabilities['contrast'] = self._cap.get(cv2.CAP_PROP_CONTRAST)
            capabilities['supported_resolutions'] = self._supported_resolutions.copy()
            capabilities['frame_count'] = self._frame_count
            
            # Add backend information
            backend = self._cap.getBackendName()
            capabilities['backend'] = backend
            
            # Add current FPS if available
            if self._fps_history:
                capabilities['current_fps'] = sum(self._fps_history) / len(self._fps_history)
                capabilities['min_fps'] = min(self._fps_history)
                capabilities['max_fps'] = max(self._fps_history)
            
        except Exception as e:
            logger.warning(f"Could not retrieve camera capabilities: {e}")
        
        return capabilities
    
    def get_actual_width(self) -> int:
        """Get actual camera width."""
        if not self._cap:
            return 0
        return int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    
    def get_actual_height(self) -> int:
        """Get actual camera height."""
        if not self._cap:
            return 0
        return int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    def get_actual_fps(self) -> float:
        """Get actual camera FPS."""
        if not self._cap:
            return 0.0
        return self._cap.get(cv2.CAP_PROP_FPS)
    
    def get_configuration_warnings(self) -> List[str]:
        """Get list of configuration warnings."""
        return self._configuration_warnings.copy()
    
    def get_supported_resolutions(self) -> List[Tuple[int, int]]:
        """Get list of supported camera resolutions."""
        return self._supported_resolutions.copy()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get camera performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        stats = {
            'frame_count': self._frame_count,
            'fps_history_length': len(self._fps_history),
            'is_available': self.is_available(),
            'is_initialized': self.is_initialized
        }
        
        if self._fps_history:
            stats.update({
                'average_fps': sum(self._fps_history) / len(self._fps_history),
                'min_fps': min(self._fps_history),
                'max_fps': max(self._fps_history),
                'current_fps': self._fps_history[-1] if self._fps_history else 0
            })
        
        return stats
    
    def test_resolution(self, width: int, height: int) -> bool:
        """
        Test if a specific resolution is supported.
        
        Args:
            width: Frame width to test
            height: Frame height to test
            
        Returns:
            True if resolution is supported, False otherwise
        """
        if not self._cap:
            return False
        
        try:
            # Store current settings
            current_width = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            current_height = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            # Test the resolution
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            # Check if it was actually set
            actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            is_supported = (actual_width == width and actual_height == height)
            
            # Restore original settings
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, current_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, current_height)
            
            return is_supported
            
        except Exception as e:
            logger.debug(f"Error testing resolution {width}x{height}: {e}")
            return False
    
    def cleanup(self) -> None:
        """Release camera resources."""
        if self._cap:
            logger.info("Releasing camera resources")
            self._cap.release()
            self._cap = None
        self._is_initialized = False
        
        # Clear performance metrics
        self._frame_count = 0
        self._last_frame_time = 0.0
        self._fps_history.clear()
    
    def __enter__(self) -> 'CameraManager':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        self.cleanup()
    
    def __del__(self) -> None:
        """Destructor to ensure cleanup."""
        self.cleanup() 