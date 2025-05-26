#!/usr/bin/env python3
"""
Test MediaPipe hands detection at different resolutions to confirm resolution sensitivity.
"""

import cv2
import mediapipe as mp
import numpy as np


def test_hands_at_resolution(width, height, name):
    """Test hands detection at specific resolution."""
    print(f"\n🔍 Testing Hands Detection at {name} ({width}x{height})")
    print("=" * 60)
    
    cap = cv2.VideoCapture(0)
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    # Verify actual resolution
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Requested: {width}x{height}, Actual: {actual_width}x{actual_height}")
    
    mp_hands = mp.solutions.hands
    
    # Configure hands detection
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    print("✋ Please raise your hand! Testing for 10 frames...")
    
    hands_detected_count = 0
    for i in range(10):
        ret, frame = cap.read()
        
        if not ret or frame is None:
            print(f"  ❌ Frame {i}: Failed to read frame")
            continue
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = hands.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hands_detected_count += 1
            print(f"  ✅ Frame {i}: {len(results.multi_hand_landmarks)} hand(s) detected")
        else:
            print(f"  ❌ Frame {i}: No hands detected")
    
    detection_rate = (hands_detected_count / 10) * 100
    print(f"\n📊 {name} Results: {hands_detected_count}/10 frames ({detection_rate:.0f}% detection rate)")
    
    # Cleanup
    hands.close()
    cap.release()
    
    return detection_rate


def main():
    """Test hands detection at various resolutions."""
    print("🎯 RESOLUTION SENSITIVITY TEST FOR MEDIAPIPE HANDS")
    print("=" * 60)
    
    # Test resolutions from low to high
    resolutions = [
        (320, 240, "QVGA"),
        (640, 480, "VGA"),  # Our CameraManager resolution 
        (800, 600, "SVGA"),
        (1280, 720, "HD"),
        (1920, 1080, "Full HD"),  # Direct OpenCV default
    ]
    
    results = []
    
    for width, height, name in resolutions:
        detection_rate = test_hands_at_resolution(width, height, name)
        results.append((name, f"{width}x{height}", detection_rate))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 RESOLUTION SENSITIVITY SUMMARY")
    print("=" * 60)
    print(f"{'Resolution':<15} {'Size':<12} {'Detection Rate':<15}")
    print("-" * 42)
    
    for name, size, rate in results:
        status = "✅ EXCELLENT" if rate >= 80 else "⚠️  POOR" if rate >= 20 else "❌ FAILED"
        print(f"{name:<15} {size:<12} {rate:>6.0f}% {status}")
    
    print("\n🎯 CONCLUSION:")
    best_resolution = max(results, key=lambda x: x[2])
    worst_resolution = min(results, key=lambda x: x[2])
    print(f"   BEST:  {best_resolution[0]} ({best_resolution[1]}) - {best_resolution[2]:.0f}% detection")
    print(f"   WORST: {worst_resolution[0]} ({worst_resolution[1]}) - {worst_resolution[2]:.0f}% detection")


if __name__ == "__main__":
    main() 