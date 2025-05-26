#!/usr/bin/env python3
"""
Live Gesture Detection Debug Tool

Shows real-time hand detection and gesture recognition status
to help debug why gestures aren't being detected.
"""

import cv2
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.camera import CameraManager
from src.camera.config import CameraConfig
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
from src.processing.enhanced_frame_processor import EnhancedFrameProcessor, EnhancedProcessorConfig
from src.service.events import EventPublisher

def main():
    print("🖐️ Live Gesture Detection Debug")
    print("=" * 40)
    print("This shows what the system is detecting:")
    print("- Human presence and confidence")
    print("- Hand detection status")
    print("- Gesture recognition results")
    print("- Palm orientation")
    print()
    print("👋 Wave your hand in front of the camera!")
    print("Press 'q' to quit")
    print()

    # Initialize components with very sensitive settings
    camera = CameraManager(CameraConfig())
    human_detector = create_detector('multimodal')
    human_detector.initialize()
    
    gesture_detector = GestureDetector()
    gesture_detector.initialize()
    
    event_publisher = EventPublisher()
    
    # Very sensitive configuration
    config = EnhancedProcessorConfig(
        min_human_confidence_for_gesture=0.2,  # Very low
        min_gesture_confidence_threshold=0.1,  # Very low
        enable_gesture_detection=True,
        publish_gesture_events=False,
        gesture_detection_every_n_frames=1,    # Every frame
        max_gesture_fps=30.0                   # High rate
    )
    
    frame_processor = EnhancedFrameProcessor(
        detector=human_detector,
        gesture_detector=gesture_detector,
        event_publisher=event_publisher,
        config=config
    )
    
    frame_count = 0
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is not None:
                frame_count += 1
                
                # Process frame
                result = frame_processor.process_frame(frame)
                
                # Get gesture result
                gesture_result = getattr(frame_processor, 'previous_gesture_result', None)
                
                # Display status
                if frame_count % 5 == 0:  # Update every 5 frames
                    print(f"\r🎥 Frame {frame_count:4d} | ", end="")
                    
                    if result.human_present:
                        print(f"👤 HUMAN ({result.confidence:.2f}) | ", end="")
                    else:
                        print(f"❌ NO HUMAN ({result.confidence:.2f}) | ", end="")
                    
                    if gesture_result and gesture_result.gesture_detected:
                        print(f"🖐️ GESTURE: {gesture_result.gesture_type} ({gesture_result.confidence:.2f}) | ", end="")
                        if hasattr(gesture_result, 'palm_facing_camera'):
                            print(f"Palm: {'✅' if gesture_result.palm_facing_camera else '❌'}", end="")
                    else:
                        print(f"🔍 No gesture detected", end="")
                    
                    print(flush=True)
                
                # Small delay
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    finally:
        print("🧹 Cleaning up...")
        gesture_detector.cleanup()
        human_detector.cleanup()
        camera.cleanup()
        print("✅ Done!")

if __name__ == "__main__":
    main() 