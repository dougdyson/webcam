#!/usr/bin/env python3
"""
Speaker Verification Integration Demo

This script demonstrates the complete integration between:
1. Real webcam detection pipeline (your working camera detection)
2. HTTP service for speaker verification guard clauses
3. Live presence status updates from actual camera feed

This connects the HTTP service to REAL camera detection events.
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

class SpeakerVerificationDemo:
    """Integrated demo connecting real detection to HTTP service."""
    
    def __init__(self):
        self.detection_app: Optional[MainApp] = None
        self.http_service: Optional[HTTPDetectionService] = None
        self.event_publisher = EventPublisher()
        self.is_running = False
        self._shutdown_requested = False
        
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
        """Setup HTTP service for speaker verification."""
        print("🌐 Setting up HTTP service for speaker verification...")
        
        config = HTTPServiceConfig(
            host="localhost",
            port=8767,
            enable_history=True,
            history_limit=100
        )
        
        self.http_service = HTTPDetectionService(config)
        
        # Connect HTTP service to event publisher
        self.http_service.event_publisher = self.event_publisher
        print("✅ HTTP service configured on http://localhost:8767")
        
    def connect_systems(self):
        """Connect detection system to HTTP service via events."""
        print("🔗 Connecting detection pipeline to HTTP service...")
        
        # This is where we bridge the detection system to the service layer
        # We'll periodically check detection results and publish events
        def detection_bridge():
            """Bridge function to forward detection results to HTTP service."""
            while self.is_running and not self._shutdown_requested:
                try:
                    if self.detection_app and self.detection_app.is_running:
                        # Get current presence status from detection system
                        presence_status = self.detection_app.get_presence_status()
                        
                        if presence_status:
                            # Create detection result
                            detection_result = DetectionResult(
                                human_present=presence_status.get('human_present', False),
                                confidence=presence_status.get('confidence', 0.0),
                                bounding_box=(0, 0, 0, 0),  # Empty bounding box as tuple
                                landmarks=[]      # Not needed for presence check
                            )
                            
                            # Publish to HTTP service
                            self.publish_detection_result(detection_result)
                    
                except Exception as e:
                    print(f"⚠️  Detection bridge error: {e}")
                
                time.sleep(0.5)  # Check twice per second
        
        # Start bridge in separate thread
        self.bridge_thread = threading.Thread(target=detection_bridge, daemon=True)
        self.bridge_thread.start()
        print("✅ Systems connected - detection events will update HTTP service")
        
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
        """Run the complete integrated demo."""
        try:
            self.is_running = True
            
            print("🎤 Speaker Verification + Webcam Detection Integration Demo")
            print("=" * 60)
            print("This demo connects REAL camera detection to HTTP service")
            print("Your speaker verification system can use: http://localhost:8767/presence/simple")
            print("Press Ctrl+C to stop")
            print("")
            
            # Setup systems
            self.setup_detection_system()
            self.setup_http_service()
            self.connect_systems()
            
            # Start both systems concurrently
            detection_task = asyncio.create_task(self.start_detection_system())
            http_task = asyncio.create_task(self.start_http_service())
            
            print("🔄 Both systems running... Check http://localhost:8767/presence/simple")
            print("👀 Watch the detection display and test the HTTP endpoints!")
            
            # Wait for either to complete (or Ctrl+C)
            await asyncio.gather(detection_task, http_task, return_exceptions=True)
            
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            await self.shutdown()
    
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
    demo = SpeakerVerificationDemo()
    demo.setup_signal_handlers()
    
    try:
        asyncio.run(demo.run())
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())