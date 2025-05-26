#!/usr/bin/env python3
"""
Enhanced Webcam Detection Service with Gesture Recognition

This service provides:
1. Real-time human presence detection via HTTP API (port 8767)
2. Hand gesture recognition with SSE streaming (port 8766) 
3. Gesture detection ONLY when humans are detected (performance optimized)

Usage:
    python webcam_enhanced_service.py

HTTP Endpoints (port 8767):
    GET /presence/simple  - Boolean presence check
    GET /presence         - Full detection status
    GET /health           - Service health check
    GET /statistics       - Performance metrics

SSE Endpoints (port 8766):
    GET /events/gestures/{client_id}  - Real-time gesture events

Integration:
    - Your other apps connect to SSE for real-time gesture events
    - Only get gesture events when human is present (optimized)
    - HTTP API still works for presence detection
"""
import asyncio
import time
import threading
import signal
import sys
import logging
from typing import Optional
from datetime import datetime

# Core detection system
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
from src.camera import CameraManager
from src.camera.config import CameraConfig
from src.processing.enhanced_frame_processor import EnhancedFrameProcessor, EnhancedProcessorConfig

# Service layer
from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
from src.service.sse_service import SSEDetectionService, SSEServiceConfig
from src.service.events import EventPublisher

# Configure logging to be quieter
logging.basicConfig(level=logging.WARNING, format='%(message)s')  # Only warnings and errors
logger = logging.getLogger(__name__)

class EnhancedWebcamService:
    """
    Enhanced Webcam Detection Service with Gesture Recognition
    
    Provides both human presence detection AND gesture recognition:
    - HTTP API on port 8767 for presence detection
    - SSE streaming on port 8766 for gesture events
    - Gesture detection only runs when humans are detected
    """
    
    def __init__(self):
        # Core components
        self.camera = None
        self.detector = None
        self.gesture_detector = None
        self.frame_processor = None
        self.event_publisher = EventPublisher()
        
        # Services
        self.http_service = None
        self.sse_service = None
        
        # State
        self.is_running = False
        self._shutdown_requested = False
        
    def initialize(self):
        """Initialize all components with proper error handling."""
        try:
            # Initialize camera (quiet)
            camera_config = CameraConfig()
            self.camera = CameraManager(camera_config)
            
            # Initialize multimodal detector (quiet)
            self.detector = create_detector('multimodal')
            self.detector.initialize()
            
            # Initialize gesture detector (quiet)
            self.gesture_detector = GestureDetector()
            self.gesture_detector.initialize()
            
            # Initialize enhanced frame processor with DEBUG SCRIPT SPEED SETTINGS
            processor_config = EnhancedProcessorConfig(
                min_human_confidence_for_gesture=0.3,  # SAME as debug script
                min_gesture_confidence_threshold=0.2,  # Very low for easy detection
                enable_gesture_detection=True,
                publish_gesture_events=True,
                performance_monitoring=True,
                gesture_detection_every_n_frames=1,    # EVERY FRAME like debug script
                max_gesture_fps=30.0                   # HIGH RATE like debug script
            )
            
            self.frame_processor = EnhancedFrameProcessor(
                detector=self.detector,
                gesture_detector=self.gesture_detector,
                event_publisher=self.event_publisher,
                config=processor_config
            )
            
            # Initialize HTTP service (presence detection)
            http_config = HTTPServiceConfig(
                host="localhost",
                port=8767,
                enable_history=True,
                history_limit=100
            )
            self.http_service = HTTPDetectionService(http_config)
            self.http_service.setup_event_integration(self.event_publisher)
            
            # Initialize SSE service (gesture streaming)
            sse_config = SSEServiceConfig(
                host="localhost",
                port=8766,
                gesture_events_only=True,  # Only stream gesture events
                min_gesture_confidence=0.7,
                max_connections=20
            )
            self.sse_service = SSEDetectionService(sse_config)
            self.sse_service.setup_gesture_integration(self.event_publisher)
            
        except Exception as e:
            logger.error(f"Failed to initialize enhanced service: {e}")
            # Clean up any partially initialized components
            self._cleanup_on_error()
            raise
    
    def _cleanup_on_error(self):
        """Clean up partially initialized components on error."""
        try:
            if self.gesture_detector and hasattr(self.gesture_detector, 'cleanup'):
                self.gesture_detector.cleanup()
            if self.detector and hasattr(self.detector, 'cleanup'):
                self.detector.cleanup()
            if self.camera and hasattr(self.camera, 'cleanup'):
                self.camera.cleanup()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
        finally:
            # Reset components to None
            self.camera = None
            self.detector = None
            self.gesture_detector = None
            self.frame_processor = None
            self.http_service = None
            self.sse_service = None
    
    def detection_loop(self):
        """Main detection loop running in separate thread with performance optimizations."""        
        last_status_print = 0
        detection_count = 0
        fps_target = 15  # Reduced from ~30 FPS for better performance
        frame_time = 1.0 / fps_target  # ~0.067 seconds per frame
        
        while self.is_running and not self._shutdown_requested:
            try:
                # Get frame from camera
                frame = self.camera.get_frame()
                if frame is not None:
                    detection_result = self.frame_processor.process_frame(frame)
                    detection_count += 1
                    
                    # Get gesture status from the previous result
                    gesture_status = "None"
                    if hasattr(self.frame_processor, 'previous_gesture_result') and self.frame_processor.previous_gesture_result:
                        prev_gesture = self.frame_processor.previous_gesture_result
                        if prev_gesture.gesture_detected:
                            gesture_status = f"{prev_gesture.gesture_type} ({prev_gesture.confidence:.2f})"
                    
                    # Update HTTP service status
                    if self.http_service:
                        self.http_service.current_status.human_present = detection_result.human_present
                        self.http_service.current_status.confidence = detection_result.confidence
                        self.http_service.current_status.last_detection = datetime.now()
                        self.http_service.current_status.detection_count += 1
                    
                    # Print status update every 2 seconds (single updating line)
                    current_time = time.time()
                    if current_time - last_status_print >= 2.0:
                        status = "👤 HUMAN" if detection_result.human_present else "❌ NO HUMAN"
                        print(f"\r{status} | Conf: {detection_result.confidence:.2f} | Gesture: {gesture_status} | Frames: {detection_count} | FPS: {fps_target}", end='', flush=True)
                        last_status_print = current_time
                    
                    time.sleep(frame_time)  # Target 15 FPS instead of 30
                else:
                    time.sleep(0.1)  # Wait if no frame
                    
            except Exception as e:
                logger.error(f"Detection loop error: {e}")
                time.sleep(1)
        
        logger.info("Detection loop stopped")
    
    async def start_http_service(self):
        """Start HTTP service."""
        if self.http_service:
            try:
                import uvicorn
                config = uvicorn.Config(
                    self.http_service.app, 
                    host="localhost", 
                    port=8767,
                    log_level="warning"
                )
                server = uvicorn.Server(config)
                logger.info("🚀 HTTP service starting on http://localhost:8767")
                await server.serve()
            except Exception as e:
                logger.error(f"HTTP service error: {e}")
    
    async def start_sse_service(self):
        """Start SSE service."""
        if self.sse_service:
            try:
                import uvicorn
                config = uvicorn.Config(
                    self.sse_service.app,
                    host="localhost",
                    port=8766,
                    log_level="warning"
                )
                server = uvicorn.Server(config)
                logger.info("📡 SSE service starting on http://localhost:8766")
                await server.serve()
            except Exception as e:
                logger.error(f"SSE service error: {e}")
    
    async def run(self):
        """Run the enhanced service with all components."""
        try:
            # Initialize all components
            self.initialize()
            
            self.is_running = True
            
            # Start detection loop in background thread
            detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            detection_thread.start()
            
            # Start both services concurrently
            await asyncio.gather(
                self.start_http_service(),
                self.start_sse_service()
            )
            
        except Exception as e:
            logger.error(f"Service startup error: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Shutdown the service gracefully."""
        logger.info("🛑 Shutting down enhanced service...")
        self._shutdown_requested = True
        self.is_running = False
        
        # Cleanup components
        if self.gesture_detector:
            self.gesture_detector.cleanup()
        if self.detector:
            self.detector.cleanup()
        if self.camera:
            self.camera.cleanup()
        
        logger.info("✅ Enhanced service shutdown complete")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self._shutdown_requested = True
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main entry point."""
    service = EnhancedWebcamService()
    service.setup_signal_handlers()
    
    print("🎯 Enhanced Webcam Detection Service with Gesture Recognition")
    print("=" * 65)
    print("HTTP API: http://localhost:8767 (presence detection)")
    print("SSE Stream: http://localhost:8766 (gesture events)")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        print("\n🛑 Service stopped by user")
    except Exception as e:
        print(f"\n❌ Service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 