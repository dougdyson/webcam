#!/usr/bin/env python3
"""
GESTURE DEBUG - Shows exactly what's happening with gesture detection
"""

import os
import sys
import time
import numpy as np
from datetime import datetime

# Suppress MediaPipe logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import logging
logging.getLogger('mediapipe').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from src.camera import CameraManager, CameraConfig
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector

def main():
    print("🔍 GESTURE DEBUG MODE")
    print("=" * 50)
    
    # Initialize
    print("📷 Camera...", end="", flush=True)
    camera = CameraManager(CameraConfig())
    print(" ✅")
    
    print("🧠 Detection models...", end="", flush=True)
    detector = create_detector('multimodal')
    detector.initialize()
    gesture_detector = GestureDetector()
    gesture_detector.initialize()
    print(" ✅")
    
    print("\n🎯 READY - Raise your hand to see debug info\n")
    
    try:
        while True:
            # Get frame
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            # Human detection
            result = detector.detect(frame)
            human_present = result.human_present and result.confidence > 0.6
            
            if human_present:
                print(f"\n{'='*50}")
                print(f"👤 HUMAN DETECTED (confidence: {result.confidence:.3f})")
                
                # Check if we have pose landmarks
                if result.landmarks is not None:
                    print("✅ Pose landmarks available")
                    
                    # Try gesture detection with detailed debug
                    try:
                        # Get gesture classifier for debug
                        gesture_classifier = gesture_detector._gesture_classifier
                        
                        # Calculate shoulder reference
                        shoulder_ref_y = gesture_classifier.calculate_shoulder_reference(result.landmarks)
                        if shoulder_ref_y is not None:
                            print(f"✅ Shoulder reference Y: {shoulder_ref_y:.3f}")
                        else:
                            print("❌ Could not calculate shoulder reference")
                            continue
                        
                        # Convert frame for MediaPipe hands
                        import cv2
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        hands_results = gesture_detector._hands_detector.process(rgb_frame)
                        
                        if hands_results.multi_hand_landmarks:
                            print(f"✅ {len(hands_results.multi_hand_landmarks)} hand(s) detected")
                            
                            for i, hand_landmarks in enumerate(hands_results.multi_hand_landmarks):
                                print(f"\n🖐️ HAND {i+1} ANALYSIS:")
                                
                                # Get hand center Y
                                hand_center_y = hand_landmarks.landmark[9].y  # Middle finger MCP
                                print(f"   Hand center Y: {hand_center_y:.3f}")
                                print(f"   Shoulder Y: {shoulder_ref_y:.3f}")
                                print(f"   Difference: {shoulder_ref_y - hand_center_y:.3f}")
                                
                                # Check position requirement
                                offset_threshold = gesture_classifier.shoulder_offset_threshold
                                required_position = shoulder_ref_y - offset_threshold
                                is_above_shoulder = hand_center_y < required_position
                                print(f"   Required position Y < {required_position:.3f}: {'✅' if is_above_shoulder else '❌'}")
                                
                                # Calculate palm normal
                                palm_normal = gesture_detector._calculate_palm_normal(hand_landmarks)
                                palm_z = palm_normal[2]
                                print(f"   Palm Z component: {palm_z:.3f}")
                                
                                # Check palm facing requirement
                                palm_threshold = gesture_classifier.palm_facing_confidence
                                is_palm_facing = palm_z >= palm_threshold
                                print(f"   Palm facing camera (Z >= {palm_threshold:.3f}): {'✅' if is_palm_facing else '❌'}")
                                
                                # Final gesture result
                                gesture_detected = is_above_shoulder and is_palm_facing
                                print(f"   🎯 GESTURE DETECTED: {'✅ YES!' if gesture_detected else '❌ NO'}")
                                
                                if gesture_detected:
                                    confidence = gesture_classifier.calculate_gesture_confidence(
                                        hand_landmarks.landmark, shoulder_ref_y, palm_normal
                                    )
                                    print(f"   Confidence: {confidence:.3f}")
                                    print("\n🎉 HAND UP GESTURE FOUND!")
                        else:
                            print("❌ No hands detected")
                            
                    except Exception as e:
                        print(f"❌ Error in gesture detection: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("❌ No pose landmarks")
            else:
                # Just show human status briefly
                print(f"\r👤 NO HUMAN ({result.confidence:.3f})", end="", flush=True)
            
            time.sleep(0.5)  # Slower for debug readability
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    finally:
        camera.cleanup()
        detector.cleanup()
        gesture_detector.cleanup()
        print("✅ Done")

if __name__ == "__main__":
    main() 