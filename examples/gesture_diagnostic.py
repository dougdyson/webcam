#!/usr/bin/env python3
"""
Gesture Detection Diagnostic Tool

Shows exactly what the gesture detector is seeing to help debug false positives.
Displays hand positions, shoulder reference, and confidence levels in real-time.
"""
import cv2
import time
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
from src.camera import CameraManager
from src.camera.config import CameraConfig

def gesture_diagnostic():
    """Run gesture detection diagnostic."""
    print("🔍 Gesture Detection Diagnostic")
    print("=" * 50)
    print("This will show you exactly what the gesture detector sees")
    print("Keep your hands DOWN to see if false positives occur")
    print("Press 'q' to quit, 's' to show detailed info")
    print()
    
    # Initialize components
    camera = CameraManager(CameraConfig())
    human_detector = create_detector('multimodal')
    human_detector.initialize()
    
    gesture_detector = GestureDetector()
    gesture_detector.initialize()
    
    frame_count = 0
    false_positive_count = 0
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue
                
            frame_count += 1
            
            # Get human pose landmarks first
            human_result = human_detector.detect(frame)
            
            # Only check gestures if human detected
            if human_result.human_present:
                # Get original pose landmarks (needed for gesture detection)
                original_pose_landmarks = getattr(human_result, '_original_pose_landmarks', None)
                
                # Detect gestures
                gesture_result = gesture_detector.detect_gestures(frame, original_pose_landmarks)
                
                # Check for false positives
                if gesture_result.gesture_detected:
                    false_positive_count += 1
                    
                    print(f"\n⚠️  GESTURE DETECTED (Frame {frame_count}):")
                    print(f"   Gesture: {gesture_result.gesture_type}")
                    print(f"   Confidence: {gesture_result.confidence:.3f}")
                    print(f"   Hand: {gesture_result.hand}")
                    print(f"   Total false positives: {false_positive_count}")
                    
                    # Show detailed diagnostic info
                    if hasattr(gesture_result, 'debug_info'):
                        debug = gesture_result.debug_info
                        print(f"   Hand center Y: {debug.get('hand_center_y', 'N/A')}")
                        print(f"   Shoulder Y: {debug.get('shoulder_y', 'N/A')}")
                        print(f"   Above shoulder: {debug.get('above_shoulder', 'N/A')}")
                        print(f"   Palm facing: {debug.get('palm_facing', 'N/A')}")
                        print(f"   Palm Z component: {debug.get('palm_z', 'N/A')}")
            
            # Show status every 30 frames
            if frame_count % 30 == 0:
                print(f"\rFrames: {frame_count} | False positives: {false_positive_count}", end='', flush=True)
            
            # Minimal delay
            time.sleep(0.03)
            
            # Check for quit (this is basic - would need OpenCV window for 'q' key)
            
    except KeyboardInterrupt:
        print(f"\n\n📊 Diagnostic Summary:")
        print(f"Total frames processed: {frame_count}")
        print(f"False positives detected: {false_positive_count}")
        if frame_count > 0:
            false_positive_rate = (false_positive_count / frame_count) * 100
            print(f"False positive rate: {false_positive_rate:.2f}%")
        
    finally:
        # Cleanup
        gesture_detector.cleanup()
        human_detector.cleanup()
        camera.cleanup()

if __name__ == "__main__":
    gesture_diagnostic() 