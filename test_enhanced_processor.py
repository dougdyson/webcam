#!/usr/bin/env python3
"""
Test Enhanced Frame Processor - Debug why gesture detection isn't working
"""
import sys
import time
sys.path.insert(0, 'src')

from src.camera.manager import CameraManager
from src.camera.config import CameraConfig
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
from src.processing.enhanced_frame_processor import EnhancedFrameProcessor, EnhancedProcessorConfig
from src.service.events import EventPublisher

def main():
    print("🔍 Testing Enhanced Frame Processor")
    print("=" * 50)
    
    # Setup exactly like the enhanced service
    camera = CameraManager(CameraConfig())
    detector = create_detector('multimodal')
    detector.initialize()
    
    gesture_detector = GestureDetector()
    gesture_detector.initialize()
    
    event_publisher = EventPublisher()
    
    # Create enhanced processor with same config as service
    config = EnhancedProcessorConfig(
        min_human_confidence_for_gesture=0.6,
        enable_gesture_detection=True,
        publish_gesture_events=True
    )
    
    processor = EnhancedFrameProcessor(
        detector=detector,
        gesture_detector=gesture_detector,
        event_publisher=event_publisher,
        config=config
    )
    
    print("✅ All components initialized, testing detection...")
    print("✋ Raise your hand up at shoulder level!")
    
    try:
        for i in range(100):  # Test 100 frames
            frame = camera.get_frame()
            if frame is not None:
                # This should trigger the debug output we added
                result = processor.process_frame(frame)
                
                if result.human_present:
                    print(f"Frame {i}: Human detected (conf: {result.confidence:.2f})")
                
            time.sleep(0.1)  # 10 FPS for testing
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    finally:
        gesture_detector.cleanup()
        detector.cleanup()
        camera.cleanup()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    main() 