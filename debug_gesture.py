#!/usr/bin/env python3
"""
Debug script to test MediaPipe hands detection with different confidence thresholds.
"""

import cv2
import mediapipe as mp
import numpy as np
from src.camera.manager import CameraManager
from src.camera.config import CameraConfig


def test_hands_detection():
    """Test MediaPipe hands detection with different confidence levels."""
    print("🔍 Testing MediaPipe Hands Detection")
    print("==================================================")
    
    # Initialize camera
    camera_config = CameraConfig()
    camera = CameraManager(camera_config)
    
    # Test different confidence thresholds
    confidence_levels = [0.3, 0.4, 0.5, 0.6, 0.7]
    
    for confidence in confidence_levels:
        print(f"\n🎯 Testing with confidence threshold: {confidence}")
        
        # Initialize MediaPipe hands with current confidence
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=confidence,
            min_tracking_confidence=0.5
        )
        
        print(f"✋ Please raise your hand! Testing for 10 frames with confidence {confidence}...")
        
        # Test 10 frames
        hands_detected_count = 0
        for i in range(10):
            frame = camera.get_frame()
            if frame is not None:
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process with MediaPipe
                results = hands.process(rgb_frame)
                
                if results.multi_hand_landmarks:
                    hands_detected_count += 1
                    print(f"  ✅ Frame {i}: {len(results.multi_hand_landmarks)} hand(s) detected")
                else:
                    print(f"  ❌ Frame {i}: No hands detected")
        
        print(f"📊 Results for confidence {confidence}: {hands_detected_count}/10 frames detected hands")
        
        # Cleanup MediaPipe instance
        hands.close()
    
    # Cleanup camera
    camera.cleanup()
    print("\n✅ Testing complete")


if __name__ == "__main__":
    test_hands_detection() 