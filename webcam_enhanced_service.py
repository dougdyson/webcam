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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        print("🚀 Initializing Enhanced Webcam Service with Gesture Recognition...")
        
        try:
            # Initialize camera
            print("📷 Setting up camera...")
            camera_config = CameraConfig()
            self.camera = CameraManager(camera_config)
            # Note: CameraManager auto-initializes in constructor, no need to call initialize()
            
            # Initialize multimodal detector (best for range)
            print("🧠 Setting up multimodal human detection...")
            self.detector = create_detector('multimodal')
            self.detector.initialize()
            
            # Initialize gesture detector
            print("✋ Setting up gesture recognition...")
            self.gesture_detector = GestureDetector()
            self.gesture_detector.initialize()
            
            # Initialize enhanced frame processor
            print("⚙️ Setting up enhanced processing pipeline...")
            processor_config = EnhancedProcessorConfig(
                min_human_confidence_for_gesture=0.6,  # Only detect gestures when confident human is present
                enable_gesture_detection=True,
                publish_gesture_events=True,
                performance_monitoring=True
            )
            
            self.frame_processor = EnhancedFrameProcessor(
                detector=self.detector,
                gesture_detector=self.gesture_detector,
                event_publisher=self.event_publisher,
                config=processor_config
            )
            
            # Initialize HTTP service (presence detection)
            print("🌐 Setting up HTTP API service (port 8767)...")
            http_config = HTTPServiceConfig(
                host="localhost",
                port=8767,
                enable_history=True,
                history_limit=100
            )
            self.http_service = HTTPDetectionService(http_config)
            self.http_service.setup_event_integration(self.event_publisher)
            
            # Initialize SSE service (gesture streaming)
            print("📡 Setting up SSE service for gesture streaming (port 8766)...")
            sse_config = SSEServiceConfig(
                host="localhost",
                port=8766,
                gesture_events_only=True,  # Only stream gesture events
                min_gesture_confidence=0.7,
                max_connections=20
            )
            self.sse_service = SSEDetectionService(sse_config)
            self.sse_service.setup_gesture_integration(self.event_publisher)
            
            print("✅ All components initialized!")
            
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
        """Main detection loop running in separate thread."""
        print("🎥 Starting detection loop...")
        
        while self.is_running and not self._shutdown_requested:
            try:
                # Get frame from camera
                frame = self.camera.get_frame()
                if frame is not None:
                    # DEBUG: Add logging to see what's happening
                    detection_result = self.frame_processor.process_frame(frame)
                    
                    # DEBUG: Print when human is detected
                    if detection_result.human_present:
                        print(f"👤 Human detected (conf: {detection_result.confidence:.2f}) - gesture detection should run...")
                    
                    # Update HTTP service status
                    if self.http_service:
                        self.http_service.current_status.human_present = detection_result.human_present
                        self.http_service.current_status.confidence = detection_result.confidence
                        self.http_service.current_status.last_detection = datetime.now()
                        self.http_service.current_status.detection_count += 1
                
                # Reasonable frame rate
                time.sleep(1/30)  # 30 FPS
                
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
        """Run the enhanced service."""
        self.is_running = True
        
        # Start detection loop in background thread
        detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
        detection_thread.start()
        
        print("\n🎯 Enhanced Webcam Service is Running!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📋 Available Services:")
        print("   HTTP API (Presence): http://localhost:8767")
        print("   - GET /presence/simple   → Quick presence check")
        print("   - GET /presence          → Full detection info")
        print("   - GET /health            → Service health")
        print("")
        print("   SSE (Gesture Events): http://localhost:8766")
        print("   - GET /events/gestures/your_client_id → Real-time gesture events")
        print("")
        print("🎯 Gesture Recognition Features:")
        print("   ✅ Hand up detection (palm facing camera)")
        print("   ✅ Only runs when human is detected (optimized)")
        print("   ✅ Real-time SSE streaming to your other apps")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("Press Ctrl+C to stop")
        
        try:
            # Run both HTTP and SSE services concurrently
            await asyncio.gather(
                self.start_http_service(),
                self.start_sse_service()
            )
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            await self.shutdown()
    
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
    
    try:
        service.initialize()
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 