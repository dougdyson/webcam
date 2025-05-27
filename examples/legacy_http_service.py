#!/usr/bin/env python3
"""
Webcam Human Detection HTTP Service

This service provides real-time human presence detection via HTTP API.
Connects live webcam detection to REST endpoints for integration with any application.

Usage:
    python webcam_http_service.py

HTTP Endpoints:
    GET http://localhost:8767/presence/simple  - Boolean presence check (primary)
    GET http://localhost:8767/presence         - Full detection status
    GET http://localhost:8767/health           - Service health check
    GET http://localhost:8767/statistics       - Performance metrics
    GET http://localhost:8767/history          - Detection history (optional)

Integration Examples:
    - Speaker verification guard clauses
    - Smart home automation triggers  
    - Security system integration
    - Interactive application presence detection
    - Any system requiring human presence awareness

The service connects real camera detection to HTTP endpoints in real-time.
All detection processing happens locally with no cloud dependencies.
"""
import asyncio
import time
import threading
import signal
import sys
from typing import Optional
from datetime import datetime

# Real detection system
from src.cli.main import MainApp, MainAppConfig
from src.detection.result import DetectionResult

# HTTP service system
from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
from src.service.events import EventPublisher, ServiceEvent, EventType

class WebcamHTTPService:
    """
    Webcam Human Detection HTTP Service
    
    Provides real-time human presence detection via HTTP API.
    Integrates live camera detection with REST endpoints for any application.
    """
    
    def __init__(self):
        self.detection_app = None
        self.http_service = None
        self.event_publisher = EventPublisher()
        self.is_running = True
        self._shutdown_requested = False
        self._last_presence = False
        
    def setup_detection_system(self):
        """Setup the real detection system with camera."""
        print("🎥 Setting up real webcam detection system...")
        
        # Configure for multimodal detection (best range)
        config = MainAppConfig(
            detector_type='multimodal',  # Use best detector for range
            detection_confidence_threshold=0.5,
            enable_display=True,  # Show detection status
            enable_logging=True,
            log_level='INFO'
        )
        
        self.detection_app = MainApp(config)
        self.detection_app.initialize()
        print("✅ Detection system initialized")
        
    def setup_http_service(self):
        """Setup the HTTP API service."""
        print("🌐 Setting up HTTP API service...")
        
        # Configure HTTP service
        config = HTTPServiceConfig(
            host="localhost",
            port=8767,
            enable_history=True,
            history_limit=100
        )
        
        self.http_service = HTTPDetectionService(config)
        # Setup event integration after creation
        self.http_service.setup_detection_integration(self.event_publisher)
        print("✅ HTTP API service configured on http://localhost:8767")
        
    def connect_systems(self):
        """Connect detection system to HTTP service via events."""
        print("🔗 Connecting detection pipeline to HTTP service...")
        
        # Bridge detection results to service events
        def detection_bridge():
            """Bridge function to convert detection results to service events."""
            while self.is_running and not self._shutdown_requested:
                try:
                    if self.detection_app and self.detection_app.is_running:
                        # Get current presence status from the detection app
                        presence_status = self.detection_app.get_presence_status()
                        current_presence = presence_status.get('human_present', False)
                        
                        # Check if presence state has changed
                        if hasattr(self, '_last_presence') and self._last_presence != current_presence:
                            # Create detection result for the service
                            detection_result = DetectionResult(
                                human_present=current_presence,
                                confidence=presence_status.get('confidence', 0.0),
                                timestamp=time.time(),
                                bounding_box=(0, 0, 0, 0),  # Empty bounding box as tuple
                                landmarks=[]
                            )
                            
                            # Publish to HTTP service
                            self.publish_detection_result(detection_result)
                        
                        self._last_presence = current_presence
                        time.sleep(0.1)  # 10Hz update rate
                    else:
                        time.sleep(1)
                except Exception as e:
                    print(f"⚠️  Detection bridge error: {e}")
                    time.sleep(1)
        
        # Start bridge in background thread
        self.bridge_thread = threading.Thread(target=detection_bridge, daemon=True)
        self.bridge_thread.start()
        print("✅ Systems connected - detection events update HTTP endpoints")
        
    def publish_detection_result(self, detection_result: DetectionResult):
        """Publish detection result to HTTP service."""
        try:
            # Update HTTP service presence status
            if self.http_service:
                self.http_service.current_status.human_present = detection_result.human_present
                self.http_service.current_status.confidence = detection_result.confidence
                # Convert float timestamp to datetime if needed
                if isinstance(detection_result.timestamp, (int, float)):
                    self.http_service.current_status.last_detection = datetime.fromtimestamp(detection_result.timestamp)
                else:
                    self.http_service.current_status.last_detection = detection_result.timestamp
                self.http_service.current_status.detection_count += 1
                
                # Publish event with proper timestamp handling
                event_timestamp = detection_result.timestamp
                if isinstance(event_timestamp, (int, float)):
                    event_timestamp_str = datetime.fromtimestamp(event_timestamp).isoformat()
                else:
                    event_timestamp_str = event_timestamp.isoformat()
                    
                event = ServiceEvent(
                    event_type=EventType.DETECTION_UPDATE,
                    data={
                        "human_present": detection_result.human_present,
                        "confidence": detection_result.confidence,
                        "timestamp": event_timestamp_str,  # Now properly converted to string
                        "detection_count": self.http_service.current_status.detection_count
                    }
                )
                
                # Publish to all subscribers
                self.event_publisher.publish(event)
                
        except Exception as e:
            print(f"⚠️  Event publishing error: {e}")
            # Continue running even if event publishing fails
    
    async def start_http_service(self):
        """Start HTTP service in background."""
        if self.http_service:
            try:
                import uvicorn
                config = uvicorn.Config(
                    self.http_service.app, 
                    host="localhost", 
                    port=8767,
                    log_level="warning"  # Reduce noise
                )
                server = uvicorn.Server(config)
                print("🚀 Starting HTTP service for speaker verification...")
                await server.serve()
            except Exception as e:
                print(f"❌ HTTP service error: {e}")
    
    async def start_detection_system(self):
        """Start detection system."""
        if self.detection_app:
            try:
                print("🚀 Starting real webcam detection...")
                await self.detection_app.start()
                await self.detection_app.run()
            except Exception as e:
                print(f"❌ Detection system error: {e}")
    
    async def run(self):
        """Run the integrated service."""
        print("🔄 Starting webcam detection and HTTP service...")
        print("📡 Endpoints will be available for integration")
        print()
        
        try:
            # Setup systems
            self.setup_detection_system()
            self.setup_http_service()
            self.connect_systems()
            
            # Start both systems concurrently
            await asyncio.gather(
                self.start_detection_system(),
                self.start_http_service()
            )
        except Exception as e:
            print(f"❌ Service startup error: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Gracefully shutdown all systems."""
        self._shutdown_requested = True
        self.is_running = False
        
        if self.detection_app:
            await self.detection_app.shutdown()
        
        print("✅ Shutdown complete")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\n📡 Received signal {signum}, shutting down...")
            self._shutdown_requested = True
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main entry point."""
    demo = WebcamHTTPService()
    demo.setup_signal_handlers()
    
    print("🎯 Webcam Human Detection HTTP Service")
    print("=" * 60)
    print("Real-time human presence detection via HTTP API")
    print("Endpoints available at: http://localhost:8767")
    print("Primary endpoint: /presence/simple")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        asyncio.run(demo.run())
    except KeyboardInterrupt:
        print("\n🛑 Service stopped by user")
    except Exception as e:
        print(f"\n❌ Service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()