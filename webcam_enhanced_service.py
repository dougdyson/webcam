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

# Ollama integration (NEW - Phase 6.2)
from src.utils.config import ConfigManager
from src.ollama.client import OllamaClient, OllamaConfig
from src.ollama.description_service import DescriptionService
from src.ollama.image_processing import OllamaImageProcessor

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
        
        # Ollama integration (NEW - Phase 6.2)
        self.config_manager = None
        self.ollama_config = None
        self.ollama_client = None
        self.ollama_image_processor = None
        self.description_service = None
        
        # State
        self.is_running = False
        self._shutdown_requested = False
        self._description_service_failed = False
        
    def initialize(self):
        """Initialize all components with proper error handling."""
        try:
            # Step 1: Initialize configuration (FIRST)
            self.config_manager = ConfigManager()
            self.ollama_config = self.config_manager.load_ollama_config()
            
            # Step 2: Initialize camera (quiet)
            camera_config = CameraConfig()
            self.camera = CameraManager(camera_config)
            
            # Step 3: Initialize multimodal detector (quiet)
            self.detector = create_detector('multimodal')
            self.detector.initialize()
            
            # Step 4: Initialize gesture detector
            self.gesture_detector = GestureDetector()
            self.gesture_detector.initialize()
            
            # Step 5: Initialize Ollama components
            try:
                # Initialize OllamaClient with configuration
                client_config = self.ollama_config['client']
                ollama_config = OllamaConfig(
                    model=client_config['model'],
                    base_url=client_config['base_url'],
                    timeout=client_config['timeout_seconds'],
                    max_retries=client_config['max_retries']
                )
                self.ollama_client = OllamaClient(config=ollama_config)
                
                # Initialize OllamaImageProcessor
                self.ollama_image_processor = OllamaImageProcessor()
                
                # Initialize DescriptionService with all required parameters
                self.description_service = DescriptionService(
                    ollama_client=self.ollama_client,
                    image_processor=self.ollama_image_processor
                )
                
                # NEW: Setup event publisher integration for description events (Phase 6.2)
                self.description_service.set_event_publisher(self.event_publisher)
                
                logger.info("✅ Ollama integration initialized successfully")
                
            except Exception as ollama_error:
                logger.warning(f"⚠️ Ollama integration failed: {ollama_error}")
                logger.warning("📍 Service will continue without AI description features")
                # Set flag to indicate description service failed but don't raise
                self._description_service_failed = True
                self.description_service = None
                self.ollama_client = None
            
            # DISABLED: Initialize enhanced frame processor with BALANCED SETTINGS (prevent false positives but still work)
            # processor_config = EnhancedProcessorConfig(
            #     min_human_confidence_for_gesture=0.4,  # Lower - your 0.54 confidence should work
            #     min_gesture_confidence_threshold=0.8,  # HIGH but not extreme - 80% confidence required
            #     enable_gesture_detection=True,
            #     publish_gesture_events=True,
            #     performance_monitoring=True,
            #     gesture_detection_every_n_frames=2,    # Every 2nd frame - balance between speed and accuracy
            #     max_gesture_fps=10.0                   # Moderate rate
            # )
            
            # self.frame_processor = EnhancedFrameProcessor(
            #     detector=self.detector,
            #     gesture_detector=self.gesture_detector,
            #     event_publisher=self.event_publisher,
            #     config=processor_config
            # )
            
            # Initialize HTTP service (presence detection)
            http_config = HTTPServiceConfig(
                host="localhost",
                port=8767,
                enable_history=True,
                history_limit=100
            )
            self.http_service = HTTPDetectionService(http_config)
            self.http_service.setup_event_integration(self.event_publisher)
            
            # NEW: Setup description integration with HTTP service (Phase 6.2)
            if self.description_service:
                self.http_service.setup_description_integration(self.description_service)
            
            # ENABLED: Initialize SSE service (gesture streaming)
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
            # Cleanup Ollama components
            if self.description_service and hasattr(self.description_service, 'cleanup'):
                self.description_service.cleanup()
            if self.ollama_client and hasattr(self.ollama_client, 'cleanup'):
                self.ollama_client.cleanup()
            if self.ollama_image_processor and hasattr(self.ollama_image_processor, 'cleanup'):
                self.ollama_image_processor.cleanup()
            
            # Cleanup existing components
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
            # Reset Ollama components
            self.description_service = None
            self.ollama_client = None
            self.ollama_config = None
            self.config_manager = None
            self.ollama_image_processor = None
    
    def detection_loop(self):
        """Main detection loop - SIMPLIFIED like debug script."""        
        last_status_print = 0
        detection_count = 0
        fps_target = 15
        frame_time = 1.0 / fps_target
        
        while self.is_running and not self._shutdown_requested:
            try:
                # Get frame from camera
                frame = self.camera.get_frame()
                if frame is not None:
                    # SIMPLIFIED: Direct detection like debug script
                    human_result = self.detector.detect(frame)
                    detection_count += 1
                    
                    # TESTING: Re-enable gesture detection to test shoulder fix
                    gesture_status = "None"
                    gesture_confidence = 0.0
                    
                    # TESTING: Simple threshold check with shoulder validation
                    if human_result.human_present and human_result.confidence > 0.6:
                        try:
                            # Direct gesture detection with pose landmarks for shoulder reference
                            gesture_result = self.gesture_detector.detect_gestures(
                                frame, 
                                pose_landmarks=getattr(human_result, '_original_pose_landmarks', None)
                            )
                            
                            if gesture_result and gesture_result.gesture_detected:
                                gesture_status = f"{gesture_result.gesture_type}"
                                gesture_confidence = gesture_result.confidence
                                
                                # ENABLED: Simple event publishing - BOTH sync and async for SSE
                                if self.sse_service:
                                    try:
                                        from src.service.events import ServiceEvent, EventType
                                        event = ServiceEvent(
                                            event_type=EventType.GESTURE_DETECTED,
                                            data={
                                                "gesture_type": gesture_result.gesture_type,
                                                "confidence": gesture_result.confidence,
                                                "hand": gesture_result.hand
                                            },
                                            timestamp=datetime.now()
                                        )
                                        # Publish both sync AND async for SSE service
                                        self.event_publisher.publish(event)
                                        
                                        # CRITICAL: Also publish async for SSE service
                                        import asyncio
                                        try:
                                            loop = asyncio.get_event_loop()
                                            if loop.is_running():
                                                asyncio.create_task(self.event_publisher.publish_async(event))
                                        except RuntimeError:
                                            # No event loop running - create one
                                            asyncio.run(self.event_publisher.publish_async(event))
                                        
                                    except Exception as e:
                                        print(f"Event publishing error: {e}")  # DON'T HIDE ERRORS
                        except Exception as e:
                            pass  # Don't let gesture detection break human detection
                    
                    # NEW: Process frame for AI description (Phase 6.2)
                    if human_result.human_present and human_result.confidence > 0.6 and self.description_service:
                        try:
                            # Process frame for description
                            description_result = self.description_service.describe_snapshot(frame)
                            
                            if description_result and hasattr(description_result, 'success') and description_result.success:
                                # Description processing successful
                                logger.debug(f"Description generated: {description_result.description}")
                            
                        except Exception as e:
                            logger.debug(f"Description processing error: {e}")  # Don't break detection loop
                    
                    # Update HTTP service status (simple)
                    if self.http_service:
                        self.http_service.current_status.human_present = human_result.human_present
                        self.http_service.current_status.confidence = human_result.confidence
                        self.http_service.current_status.last_detection = datetime.now()
                        self.http_service.current_status.detection_count += 1
                    
                    # Print status update every 2 seconds (single updating line)
                    current_time = time.time()
                    if current_time - last_status_print >= 2.0:
                        status = "👤 HUMAN" if human_result.human_present else "❌ NO HUMAN"
                        # TESTING: Re-enable gesture display to test shoulder fix
                        gesture_display = f"{gesture_status} ({gesture_confidence:.2f})" if gesture_confidence > 0 else gesture_status
                        print(f"\r{status} | Conf: {human_result.confidence:.2f} | Gesture: {gesture_display} | Frames: {detection_count} | FPS: {fps_target}", end='', flush=True)
                        last_status_print = current_time
                    
                    time.sleep(frame_time)
                else:
                    time.sleep(0.1)
                    
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
            # ENABLED: SSE service for gesture events
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
        
        # Cleanup Ollama components
        if self.description_service and hasattr(self.description_service, 'cleanup'):
            self.description_service.cleanup()
        if self.ollama_client and hasattr(self.ollama_client, 'cleanup'):
            self.ollama_client.cleanup()
        if self.ollama_image_processor and hasattr(self.ollama_image_processor, 'cleanup'):
            self.ollama_image_processor.cleanup()
        
        # Cleanup existing components
        if self.gesture_detector:
            self.gesture_detector.cleanup()
        if self.detector:
            self.detector.cleanup()
        if self.camera:
            self.camera.cleanup()
        
        # Set components to None
        self.description_service = None
        self.ollama_client = None
        self.ollama_image_processor = None
        self.gesture_detector = None
        
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