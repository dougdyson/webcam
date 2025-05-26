#!/usr/bin/env python3
"""
Simple hands detection test using exact working MediaPipe sample code.
"""

import cv2
import mediapipe as mp
import numpy as np


def test_working_hands_detection():
    """Test using the exact working MediaPipe hands code from samples."""
    print("🔍 Testing Working MediaPipe Hands Detection")
    print("=" * 50)
    
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    
    # Configure hands detection (EXACT same as working sample)
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    frame_count = 0
    max_frames = 20
    
    print("✋ Please raise your hand! Testing for 20 frames...")
    
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to get frame from camera")
            break
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame for hands
        results = hands.process(rgb_frame)
        
        # Check results
        if results.multi_hand_landmarks:
            print(f"  ✅ Frame {frame_count}: {len(results.multi_hand_landmarks)} hand(s) detected")
            
            # Draw hand landmarks for visual confirmation
            for hand_landmarks in results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        else:
            print(f"  ❌ Frame {frame_count}: No hands detected")
        
        # Show frame (optional - comment out if running headless)
        cv2.imshow('Simple Hands Test', frame)
        
        frame_count += 1
        
        # Allow early exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    
    print("\n✅ Testing complete")


if __name__ == "__main__":
    test_working_hands_detection() 