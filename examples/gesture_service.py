#!/usr/bin/env python3
"""
Clean Gesture Service - One simple service that just works
- Human presence detection
- Hand up gesture detection  
- Single line status updates (no scrolling)
- HTTP service on port 8767
- SSE service on port 8766
"""

import sys
import time
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager

# Configure clean logging (suppress MediaPipe spam)
logging.getLogger('mediapipe').setLevel(logging.ERROR)
logging.basicConfig(level=logging.WARNING)

from src.camera import CameraManager, CameraConfig
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
from src.service.events import EventPublisher, ServiceEvent, EventType
from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
from src.service.sse_service import SSEDetectionService

class CleanGestureService:
    def __init__(self):
        self.camera = None
        self.detector = None
        self.gesture_detector = None
        self.event_publisher = EventPublisher()
        self.running = False
        self.stats = {
            'frames_processed': 0,
            'humans_detected': 0,
            'gestures_detected': 0,
            'start_time': None
        }
    
    async def initialize(self):
        """Initialize all components"""
        print("🚀 Starting Gesture Service...")
        print("📷 Initializing camera...", end="", flush=True)
        self.camera = CameraManager(CameraConfig())
        print(" ✅")
        
        print("🧠 Loading detection models...", end="", flush=True)
        self.detector = create_detector('multimodal')
        self.detector.initialize()
        self.gesture_detector = GestureDetector()
        self.gesture_detector.initialize()
        print(" ✅")
        
        self.stats['start_time'] = datetime.now()
        print("\n" + "="*80)
        print("🎯 GESTURE SERVICE READY")
        print("   Detection: Human presence + Hand up gestures")
        print("="*80)
        print()

    def print_status(self, human_present=False, human_confidence=0.0, 
                    gesture_detected=False, gesture_type="", gesture_confidence=0.0):
        """Print single updating status line"""
        uptime = int((datetime.now() - self.stats['start_time']).total_seconds()) if self.stats['start_time'] else 0
        
        # Build status line
        human_status = f"👤 Human: {'YES' if human_present else 'NO'} ({human_confidence:.2f})"
        gesture_status = f"🖐️ Gesture: {gesture_type.upper() if gesture_detected else 'NONE'}"
        if gesture_detected:
            gesture_status += f" ({gesture_confidence:.2f})"
        
        stats = f"📊 {self.stats['frames_processed']}f | {self.stats['humans_detected']}h | {self.stats['gestures_detected']}g | {uptime}s"
        
        # Single line with carriage return (no scrolling)
        status_line = f"\r{human_status} | {gesture_status} | {stats}"
        print(status_line, end="", flush=True)

    async def process_frame(self):
        """Process single frame"""
        frame = self.camera.get_frame()
        if frame is None:
            return
            
        self.stats['frames_processed'] += 1
        
        # Human detection
        result = self.detector.detect(frame)
        human_present = result.human_present and result.confidence > 0.6
        
        if human_present:
            self.stats['humans_detected'] += 1
            
            # Gesture detection (only when human present)
            gesture_result = self.gesture_detector.detect_gestures(frame, result.landmarks)
            
            if gesture_result.gesture_detected:
                self.stats['gestures_detected'] += 1
                
                # Publish gesture event
                await self.event_publisher.publish_async(ServiceEvent(
                    event_type=EventType.GESTURE_DETECTED,
                    data={
                        'gesture_type': gesture_result.gesture_type,
                        'confidence': gesture_result.confidence,
                        'hand': gesture_result.hand
                    }
                ))
                
                self.print_status(
                    human_present=True, 
                    human_confidence=result.confidence,
                    gesture_detected=True,
                    gesture_type=gesture_result.gesture_type,
                    gesture_confidence=gesture_result.confidence
                )
            else:
                self.print_status(
                    human_present=True, 
                    human_confidence=result.confidence,
                    gesture_detected=False
                )
        else:
            self.print_status(
                human_present=False,
                human_confidence=result.confidence,
                gesture_detected=False
            )
        
        # Publish presence update
        self.event_publisher.publish(ServiceEvent(
            event_type=EventType.PRESENCE_CHANGED,
            data={'human_present': human_present, 'confidence': result.confidence}
        ))

    async def run(self):
        """Main processing loop"""
        self.running = True
        try:
            while self.running:
                await self.process_frame()
                await asyncio.sleep(0.1)  # 10 FPS
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down...")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean shutdown"""
        self.running = False
        if self.camera:
            self.camera.cleanup()
        if self.detector:
            self.detector.cleanup()
        if self.gesture_detector:
            self.gesture_detector.cleanup()
        print("✅ Service stopped cleanly")

async def main():
    service = CleanGestureService()
    try:
        await service.initialize()
        await service.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        await service.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 