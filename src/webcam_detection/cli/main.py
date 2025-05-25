"""
Main application coordinator for webcam human detection system.

This module implements the MainApp class that coordinates all components
including camera management, detection, processing, and filtering to
provide a complete human presence detection workflow.
"""

import asyncio
import logging
import signal
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

from ..camera.manager import CameraManager
from ..camera.config import CameraConfig
from ..detection.base import DetectorConfig, HumanDetector
from ..detection import DetectorFactory, create_detector
from ..processing.queue import FrameQueue
from ..processing.processor import FrameProcessor
from ..processing.filter import PresenceFilter, PresenceFilterConfig
from ..utils.config import ConfigManager
from ..utils.logger import LoggerManager


logger = logging.getLogger(__name__)


class MainAppError(Exception):
    """Exception raised by main application operations."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        if original_error:
            super().__init__(f"{message} (caused by: {original_error})")
        else:
            super().__init__(message)


@dataclass
class MainAppConfig:
    """Configuration for main application."""
    
    camera_profile: str = 'default'
    detector_type: str = 'multimodal'  # New multi-modal detector by default
    detection_confidence_threshold: float = 0.5
    enable_logging: bool = True
    log_level: str = 'INFO'
    log_file: Optional[str] = None
    enable_display: bool = False
    max_runtime_seconds: Optional[float] = None
    config_file: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.0 <= self.detection_confidence_threshold <= 1.0:
            raise ValueError("Detection confidence threshold must be between 0.0 and 1.0")
        
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Log level must be one of: {valid_log_levels}")
        
        if self.max_runtime_seconds is not None and self.max_runtime_seconds <= 0:
            raise ValueError("Max runtime seconds must be positive")
            
        # Validate detector type
        available_detectors = DetectorFactory.list_available()
        if self.detector_type not in available_detectors:
            raise ValueError(f"Detector type '{self.detector_type}' not available. Available: {available_detectors}")


class MainApp:
    """
    Main application coordinator for webcam human detection.
    
    Coordinates all components to provide a complete human presence
    detection workflow including camera capture, detection processing,
    filtering, and application lifecycle management.
    """
    
    def __init__(self, config: Optional[MainAppConfig] = None):
        """
        Initialize main application.
        
        Args:
            config: Application configuration, defaults to MainAppConfig()
        """
        self.config = config or MainAppConfig()
        
        # Component instances
        self.camera_manager: Optional[CameraManager] = None
        self.detector: Optional[HumanDetector] = None
        self.frame_queue: Optional[FrameQueue] = None
        self.frame_processor: Optional[FrameProcessor] = None
        self.presence_filter: Optional[PresenceFilter] = None
        
        # State tracking
        self.is_running = False
        self.frames_processed = 0
        self._start_time = time.time()
        self._shutdown_requested = False
        
        logger.info(f"MainApp initialized with config: {self.config}")
    
    def initialize(self) -> None:
        """Initialize all application components."""
        try:
            # Initialize camera configuration
            camera_config = CameraConfig()  # Load from profile in real implementation
            
            # Initialize camera manager
            self.camera_manager = CameraManager(camera_config)
            
            # Initialize human detector
            detector_config = DetectorConfig(
                min_detection_confidence=self.config.detection_confidence_threshold
            )
            self.detector = create_detector(self.config.detector_type, detector_config)
            # Initialize the detector
            self.detector.initialize()
            
            # Initialize frame queue with default parameters
            self.frame_queue = FrameQueue(max_size=10, overflow_strategy='drop_oldest')
            
            # Initialize frame processor
            self.frame_processor = FrameProcessor(
                frame_queue=self.frame_queue,
                detector=self.detector,
                max_concurrent=2,
                processing_timeout=5.0
            )
            
            # Initialize presence filter
            filter_config = PresenceFilterConfig(
                min_confidence_threshold=self.config.detection_confidence_threshold
            )
            self.presence_filter = PresenceFilter(filter_config)
            
            logger.info("All application components initialized successfully")
            
        except Exception as e:
            raise MainAppError(
                "Failed to initialize application components",
                original_error=e
            )
    
    async def start(self) -> None:
        """Start the application and all components."""
        if self.is_running:
            logger.warning("Application is already running")
            return
        
        try:
            # Show startup banner if display enabled
            if self.config.enable_display:
                self._show_startup_banner()
            
            # Start frame processor
            if self.frame_processor:
                await self.frame_processor.start()
            
            self.is_running = True
            logger.info("Application started successfully")
            
            # Show ready message
            if self.config.enable_display:
                print(f"\n🚀 {self.config.detector_type.upper()} detector ready! Monitoring for human presence...")
                print("👤 = Human detected | ❌ = No human | Press Ctrl+C to stop\n")
            
        except Exception as e:
            raise MainAppError(
                "Failed to start application",
                original_error=e
            )
    
    async def stop(self) -> None:
        """Stop the application and all components."""
        if not self.is_running:
            return
        
        try:
            # Stop frame processor
            if self.frame_processor:
                await self.frame_processor.stop()
            
            self.is_running = False
            logger.info("Application stopped successfully")
            
        except Exception as e:
            raise MainAppError(
                "Failed to stop application",
                original_error=e
            )
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the application with cleanup."""
        logger.info("Shutting down application...")
        
        if self.config.enable_display:
            print("\n\n🛑 Shutting down gracefully...")
            print("🧹 Cleaning up components...")
        
        try:
            # Stop processing
            await self.stop()
            
            # Cleanup components
            if self.frame_processor:
                await self.frame_processor.stop()
            
            if self.camera_manager:
                self.camera_manager.cleanup()
            
            if self.detector:
                self.detector.cleanup()
            
            if self.config.enable_display:
                print("✅ All components cleaned up successfully")
                print("👋 Goodbye!")
            
            logger.info("Application shutdown completed")
            
        except Exception as e:
            if self.config.enable_display:
                print(f"❌ Error during shutdown: {e}")
            logger.error(f"Error during shutdown: {e}")
            raise MainAppError(
                "Failed to shutdown application cleanly",
                original_error=e
            )
    
    async def run(self) -> None:
        """Run the main application processing loop."""
        await self.start()
        
        try:
            start_time = time.time()
            
            # Main processing loop
            while self.is_running and not self._shutdown_requested:
                # Check runtime limit
                if (self.config.max_runtime_seconds is not None and 
                    time.time() - start_time >= self.config.max_runtime_seconds):
                    logger.info("Max runtime reached, stopping application")
                    break
                
                # Process single frame
                await self._process_single_frame()
                
                # Small delay to prevent overwhelming the CPU
                await asyncio.sleep(0.001)
            
        except Exception as e:
            logger.error(f"Error in main processing loop: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def _process_single_frame(self) -> None:
        """Process a single frame through the complete pipeline."""
        try:
            # Get frame from camera
            if not self.camera_manager:
                return
                
            frame = self.camera_manager.get_frame()
            if frame is None:
                return
            
            # Detect human presence
            if not self.detector:
                return
                
            detection_result = self.detector.detect(frame)
            
            # Apply presence filtering
            if self.presence_filter:
                self.presence_filter.add_result(detection_result)
            
            # Update statistics
            self.frames_processed += 1
            
            # Live terminal output every 10 frames (about 1-3 times per second)
            if self.frames_processed % 10 == 0:
                self._display_live_status(detection_result)
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            # Continue processing despite errors
    
    def _display_live_status(self, detection_result) -> None:
        """Display live detection status to terminal."""
        if not self.config.enable_display:
            return
            
        # Get current status
        stats = self.get_statistics()
        presence_status = self.get_presence_status()
        current_presence = presence_status.get('human_present', False)
        
        # Clear line and return to beginning
        print('\r', end='')
        
        # Status indicator
        status_emoji = "👤" if current_presence else "❌"
        status_text = "HUMAN DETECTED" if current_presence else "No Human"
        
        # Detection info
        confidence = detection_result.confidence if detection_result else 0.0
        detector_type = self.config.detector_type.upper()
        
        # Statistics
        fps = stats.get('frames_per_second', 0.0)
        total_frames = stats.get('frames_processed', 0)
        state_changes = presence_status.get('state_changes', 0)
        uptime = stats.get('uptime_seconds', 0)
        
        # Create live status line with time
        status_line = (
            f"{status_emoji} {status_text} | "
            f"{detector_type} | "
            f"Conf: {confidence:.2f} | "
            f"FPS: {fps:.1f} | "
            f"Frames: {total_frames} | "
            f"Changes: {state_changes} | "
            f"Uptime: {uptime:.0f}s"
        )
        
        # Print without newline to overwrite
        print(status_line[:79], end='', flush=True)  # Limit line length
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get application statistics and performance metrics."""
        uptime = time.time() - self._start_time
        fps = self.frames_processed / uptime if uptime > 0 else 0.0
        
        return {
            'frames_processed': self.frames_processed,
            'uptime_seconds': uptime,
            'frames_per_second': fps,
            'current_presence': self.get_current_presence(),
            'is_running': self.is_running
        }
    
    def get_presence_status(self) -> Dict[str, Any]:
        """Get current presence detection status."""
        if not self.presence_filter:
            return {
                'human_present': False,
                'state_changes': 0,
                'total_detections': 0
            }
        
        return {
            'human_present': self.presence_filter.get_filtered_presence(),
            'state_changes': self.presence_filter.get_state_change_count(),
            'total_detections': self.presence_filter.get_detection_count()
        }
    
    def get_current_presence(self) -> bool:
        """Get current filtered presence state."""
        if not self.presence_filter:
            return False
        return self.presence_filter.get_filtered_presence()
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("Signal handlers configured")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, requesting shutdown...")
        self._shutdown_requested = True
    
    def __str__(self) -> str:
        """String representation of application state."""
        return (
            f"MainApp(running={self.is_running}, "
            f"frames={self.frames_processed}, "
            f"presence={self.get_current_presence()})"
        )
    
    def __repr__(self) -> str:
        """Detailed representation of application."""
        return (
            f"MainApp(config={self.config}, "
            f"is_running={self.is_running}, "
            f"frames_processed={self.frames_processed})"
        )
    
    def _show_startup_banner(self) -> None:
        """Show startup banner and initialization status."""
        print("=" * 70)
        print("🎯 WEBCAM HUMAN DETECTION SYSTEM")
        print("=" * 70)
        print(f"🔧 Detector Type: {self.config.detector_type.upper()}")
        print(f"📹 Camera Profile: {self.config.camera_profile}")
        print(f"🎚️  Confidence Threshold: {self.config.detection_confidence_threshold}")
        print(f"⚡ Max Runtime: {self.config.max_runtime_seconds or 'Unlimited'} seconds")
        print("=" * 70)
        print("🔄 Initializing components...")
        
        if self.config.detector_type == 'multimodal':
            print("✨ Multi-modal detection: Combining pose + face detection")
            print("📡 Extended range: Desk distance to kitchen distance (3x improvement)")
        elif self.config.detector_type == 'mediapipe':
            print("🎭 MediaPipe pose detection: Traditional close-range detection")
        
        print("⏳ Starting camera and detection systems...") 