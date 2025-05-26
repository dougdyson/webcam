#!/usr/bin/env python3
"""
SIMPLE GESTURE DETECTION - Just works, no mess
"""

import os
import sys
import time
import numpy as np
from datetime import datetime

# Suppress ALL MediaPipe logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import logging
logging.getLogger('mediapipe').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from src.camera import CameraManager, CameraConfig
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector

def main():
    # Initialize - show progress, then clear
    print("🚀 Initializing...")
    
    print("📷 Camera...", end="", flush=True)
    camera = CameraManager(CameraConfig())
    print(" ✅")
    
    print("🧠 Detection models...", end="", flush=True)
    detector = create_detector('multimodal')
    detector.initialize()
    gesture_detector = GestureDetector()
    gesture_detector.initialize()
    print(" ✅")
    
    print("\n🎯 READY - Press Ctrl+C to stop\n")
    
    # Stats
    frame_count = 0
    human_count = 0
    gesture_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Get frame
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
                
            frame_count += 1
            
            # Human detection
            result = detector.detect(frame)
            human_present = result.human_present and result.confidence > 0.6
            
            if human_present:
                human_count += 1
                
                # Gesture detection
                try:
                    gesture_result = gesture_detector.detect_gestures(frame, result.landmarks)
                    gesture_detected = gesture_result.gesture_detected
                    gesture_type = gesture_result.gesture_type if gesture_detected else ""
                    gesture_confidence = gesture_result.confidence if gesture_detected else 0.0
                    
                    if gesture_detected:
                        gesture_count += 1
                except:
                    gesture_detected = False
                    gesture_type = ""
                    gesture_confidence = 0.0
            else:
                gesture_detected = False
                gesture_type = ""
                gesture_confidence = 0.0
            
            # Calculate uptime
            uptime = int(time.time() - start_time)
            
            # Single updating line
            human_status = f"👤 {'YES' if human_present else 'NO'} ({result.confidence:.2f})"
            gesture_status = f"🖐️ {gesture_type.upper() if gesture_detected else 'NONE'}"
            if gesture_detected:
                gesture_status += f" ({gesture_confidence:.2f})"
            stats = f"📊 {frame_count}f | {human_count}h | {gesture_count}g | {uptime}s"
            
            # Print single line with carriage return (overwrites previous line)
            print(f"\r{human_status} | {gesture_status} | {stats}", end="", flush=True)
            
            time.sleep(0.1)  # 10 FPS
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    finally:
        camera.cleanup()
        detector.cleanup()
        gesture_detector.cleanup()
        print("✅ Done")

if __name__ == "__main__":
    main() 