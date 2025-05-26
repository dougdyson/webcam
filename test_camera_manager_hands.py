#!/usr/bin/env python3
"""
Test MediaPipe hands detection with CameraManager vs direct OpenCV.
"""

import cv2
import mediapipe as mp
import numpy as np
from src.camera.manager import CameraManager
from src.camera.config import CameraConfig


def test_camera_manager_hands():
    """Test hands detection using CameraManager."""
    print("🔍 Testing Hands Detection with CameraManager")
    print("=" * 50)
    
    # Initialize camera manager
    camera_config = CameraConfig()
    camera = CameraManager(camera_config)
    
    mp_hands = mp.solutions.hands
    
    # Configure hands detection (same as working test)
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    print("✋ Please raise your hand! Testing for 20 frames with CameraManager...")
    
    hands_detected_count = 0
    for i in range(20):
        frame = camera.get_frame()
        
        if frame is None:
            print(f"  ❌ Frame {i}: CameraManager returned None")
            continue
        
        # Check frame properties
        if i == 0:
            print(f"Frame info: shape={frame.shape}, dtype={frame.dtype}")
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hands_detected_count += 1
            print(f"  ✅ Frame {i}: {len(results.multi_hand_landmarks)} hand(s) detected")
        else:
            print(f"  ❌ Frame {i}: No hands detected")
    
    print(f"\n📊 CameraManager Results: {hands_detected_count}/20 frames detected hands")
    
    # Cleanup
    hands.close()
    camera.cleanup()


def test_direct_opencv_hands():
    """Test hands detection using direct OpenCV (for comparison)."""
    print("\n🔍 Testing Hands Detection with Direct OpenCV")
    print("=" * 50)
    
    cap = cv2.VideoCapture(0)
    mp_hands = mp.solutions.hands
    
    # Configure hands detection (same as working test)
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    print("✋ Please raise your hand! Testing for 20 frames with direct OpenCV...")
    
    hands_detected_count = 0
    for i in range(20):
        ret, frame = cap.read()
        
        if not ret or frame is None:
            print(f"  ❌ Frame {i}: OpenCV returned None")
            continue
        
        # Check frame properties
        if i == 0:
            print(f"Frame info: shape={frame.shape}, dtype={frame.dtype}")
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hands_detected_count += 1
            print(f"  ✅ Frame {i}: {len(results.multi_hand_landmarks)} hand(s) detected")
        else:
            print(f"  ❌ Frame {i}: No hands detected")
    
    print(f"\n📊 Direct OpenCV Results: {hands_detected_count}/20 frames detected hands")
    
    # Cleanup
    hands.close()
    cap.release()


if __name__ == "__main__":
    test_camera_manager_hands()
    test_direct_opencv_hands() 