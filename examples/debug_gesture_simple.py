#!/usr/bin/env python3
"""
Simple Gesture Detection Debug Tool

Tests gesture detection step by step to identify issues.
"""

import sys
import os
import time
import traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gesture_detection():
    print("🧪 Simple Gesture Detection Test")
    print("=" * 40)
    
    try:
        print("📷 Step 1: Initialize camera...")
        from src.camera import CameraManager
        from src.camera.config import CameraConfig
        camera = CameraManager(CameraConfig())
        print("✅ Camera initialized")
        
        print("🧠 Step 2: Initialize human detector...")
        from src.detection import create_detector
        human_detector = create_detector('multimodal')
        human_detector.initialize()
        print("✅ Human detector initialized")
        
        print("🖐️ Step 3: Initialize gesture detector...")
        from src.detection.gesture_detector import GestureDetector
        gesture_detector = GestureDetector()
        gesture_detector.initialize()
        print("✅ Gesture detector initialized")
        
        print("\n🎥 Step 4: Testing frame capture and detection...")
        print("Wave your hand! Testing for 10 seconds...")
        
        start_time = time.time()
        frame_count = 0
        gesture_detected_count = 0
        
        while time.time() - start_time < 10:
            try:
                frame = camera.get_frame()
                if frame is not None:
                    frame_count += 1
                    
                    # Test human detection
                    human_result = human_detector.detect(frame)
                    
                    # Test gesture detection if human present
                    gesture_result = None
                    if human_result.human_present and human_result.confidence > 0.3:
                        try:
                            gesture_result = gesture_detector.detect_gestures(frame)
                            if gesture_result and gesture_result.gesture_detected:
                                gesture_detected_count += 1
                                print(f"🎉 GESTURE DETECTED! Frame {frame_count}: {gesture_result.gesture_type} (conf: {gesture_result.confidence:.2f})")
                        except Exception as e:
                            print(f"⚠️ Gesture detection error: {e}")
                    
                    # Show status every 30 frames
                    if frame_count % 30 == 0:
                        human_status = f"👤 HUMAN ({human_result.confidence:.2f})" if human_result.human_present else f"❌ NO HUMAN ({human_result.confidence:.2f})"
                        print(f"Frame {frame_count:3d}: {human_status}")
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                print(f"❌ Frame processing error: {e}")
                traceback.print_exc()
                break
        
        print(f"\n📊 Test Results:")
        print(f"   Frames processed: {frame_count}")
        print(f"   Gestures detected: {gesture_detected_count}")
        print(f"   Detection rate: {gesture_detected_count/frame_count*100:.1f}%" if frame_count > 0 else "0%")
        
    except Exception as e:
        print(f"❌ Setup error: {e}")
        traceback.print_exc()
    
    finally:
        print("🧹 Cleaning up...")
        try:
            if 'gesture_detector' in locals():
                gesture_detector.cleanup()
            if 'human_detector' in locals():
                human_detector.cleanup()
            if 'camera' in locals():
                camera.cleanup()
        except:
            pass
        print("✅ Cleanup complete!")

if __name__ == "__main__":
    test_gesture_detection() 