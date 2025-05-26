#!/usr/bin/env python3
"""
Debug script to check exactly what resolution CameraManager is actually using.
"""

import cv2
import mediapipe as mp
from src.camera.manager import CameraManager
from src.camera.config import CameraConfig


def debug_camera_manager_actual_resolution():
    """Debug what resolution CameraManager is actually using."""
    print("🔍 Debugging CameraManager Actual Resolution")
    print("=" * 60)
    
    # Initialize camera manager 
    print("1. Creating CameraConfig...")
    camera_config = CameraConfig()
    print(f"   Requested config: {camera_config.width}x{camera_config.height}")
    
    print("2. Creating CameraManager...")
    camera = CameraManager(camera_config)
    
    print("3. Getting actual camera properties...")
    actual_width = camera.get_actual_width()
    actual_height = camera.get_actual_height()
    actual_fps = camera.get_actual_fps()
    
    print(f"   Actual resolution: {actual_width}x{actual_height}")
    print(f"   Actual FPS: {actual_fps}")
    
    print("4. Testing frame capture and properties...")
    frame = camera.get_frame()
    if frame is not None:
        print(f"   Frame shape: {frame.shape}")
        print(f"   Frame dtype: {frame.dtype}")
    else:
        print("   ❌ Failed to get frame")
        camera.cleanup()
        return
    
    print("5. Testing MediaPipe hands detection...")
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    print("   ✋ Please raise your hand! Testing 5 frames...")
    hands_detected_count = 0
    
    for i in range(5):
        frame = camera.get_frame()
        if frame is None:
            print(f"     Frame {i}: Failed to get frame")
            continue
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hands_detected_count += 1
            print(f"     ✅ Frame {i}: {len(results.multi_hand_landmarks)} hand(s) detected")
        else:
            print(f"     ❌ Frame {i}: No hands detected")
    
    print(f"\n📊 Results: {hands_detected_count}/5 frames detected hands")
    
    # Compare with direct OpenCV at same resolution
    print(f"\n6. Testing direct OpenCV at {actual_width}x{actual_height}...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, actual_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, actual_height)
    
    direct_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    direct_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"   Direct OpenCV resolution: {direct_width}x{direct_height}")
    
    hands_detected_direct = 0
    print("   ✋ Testing 5 frames with direct OpenCV...")
    
    for i in range(5):
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"     Frame {i}: Failed to get frame")
            continue
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hands_detected_direct += 1
            print(f"     ✅ Frame {i}: {len(results.multi_hand_landmarks)} hand(s) detected")
        else:
            print(f"     ❌ Frame {i}: No hands detected")
    
    print(f"\n📊 Direct OpenCV Results: {hands_detected_direct}/5 frames detected hands")
    
    # Summary
    print(f"\n🎯 SUMMARY:")
    print(f"   CameraManager: {camera_config.width}x{camera_config.height} → {actual_width}x{actual_height} → {hands_detected_count}/5 detection")
    print(f"   Direct OpenCV: {direct_width}x{direct_height} → {hands_detected_direct}/5 detection")
    
    # Cleanup
    hands.close()
    cap.release()
    camera.cleanup()


if __name__ == "__main__":
    debug_camera_manager_actual_resolution() 