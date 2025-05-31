#!/usr/bin/env python3
"""
Visual Gesture Debug Tool

Shows live webcam feed with gesture detection overlays:
- Hand landmarks and connections
- Shoulder reference lines  
- Palm orientation vectors
- Confidence scores
- Gesture detection status
"""

import cv2
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.camera import CameraManager, CameraConfig
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
import mediapipe as mp

def draw_landmarks(image, landmarks, connections=None, color=(0, 255, 0), thickness=2):
    """Draw landmarks and connections on image."""
    if landmarks is None:
        return image
    
    h, w = image.shape[:2]
    
    # Draw connections first (behind landmarks)
    if connections:
        for connection in connections:
            start_idx, end_idx = connection
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                start_point = landmarks[start_idx]
                end_point = landmarks[end_idx]
                
                start_pixel = (int(start_point.x * w), int(start_point.y * h))
                end_pixel = (int(end_point.x * w), int(end_point.y * h))
                
                cv2.line(image, start_pixel, end_pixel, color, thickness//2)
    
    # Draw landmarks on top
    for landmark in landmarks:
        x = int(landmark.x * w)
        y = int(landmark.y * h)
        cv2.circle(image, (x, y), thickness*2, color, -1)
    
    return image

def draw_palm_orientation(image, hand_landmarks, palm_normal, hand_label="unknown"):
    """Draw palm orientation vector."""
    if hand_landmarks is None or palm_normal is None:
        return image
    
    h, w = image.shape[:2]
    
    # Get wrist position as starting point
    wrist = hand_landmarks.landmark[0]
    wrist_pixel = (int(wrist.x * w), int(wrist.y * h))
    
    # Calculate end point of orientation vector
    vector_length = 100  # pixels
    end_x = int(wrist_pixel[0] + palm_normal[0] * vector_length)
    end_y = int(wrist_pixel[1] + palm_normal[1] * vector_length)
    
    # Color based on Z component (facing camera)
    z_component = palm_normal[2]
    if z_component > 0.8:
        color = (0, 255, 0)  # Green - facing camera
    elif z_component > 0.4:
        color = (0, 255, 255)  # Yellow - somewhat facing
    else:
        color = (0, 0, 255)  # Red - facing away
    
    # Draw arrow
    cv2.arrowedLine(image, wrist_pixel, (end_x, end_y), color, 3)
    
    # Draw Z component text
    text = f"Z: {z_component:.2f}"
    cv2.putText(image, text, (wrist_pixel[0] + 10, wrist_pixel[1] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return image

def draw_shoulder_reference(image, pose_landmarks):
    """Draw shoulder reference line and head landmarks."""
    if pose_landmarks is None:
        return image
    
    h, w = image.shape[:2]
    
    try:
        # Get shoulder landmarks
        left_shoulder = pose_landmarks.landmark[11]  # LEFT_SHOULDER
        right_shoulder = pose_landmarks.landmark[12]  # RIGHT_SHOULDER
        nose = pose_landmarks.landmark[0]  # NOSE
        
        left_pixel = (int(left_shoulder.x * w), int(left_shoulder.y * h))
        right_pixel = (int(right_shoulder.x * w), int(right_shoulder.y * h))
        nose_pixel = (int(nose.x * w), int(nose.y * h))
        
        # Draw shoulder line
        cv2.line(image, left_pixel, right_pixel, (255, 0, 0), 3)
        
        # Draw shoulder reference line across frame
        shoulder_y = int((left_shoulder.y + right_shoulder.y) / 2 * h)
        cv2.line(image, (0, shoulder_y), (w, shoulder_y), (255, 0, 0), 2)
        
        # Draw nose landmark as head reference
        cv2.circle(image, nose_pixel, 8, (255, 255, 0), -1)  # Yellow circle for nose
        cv2.circle(image, nose_pixel, 12, (255, 255, 0), 2)   # Yellow outline
        
        # Draw head exclusion zone (circle around nose)
        head_exclusion_radius = int(0.25 * w)  # 25% of frame width - matches gesture detection threshold
        cv2.circle(image, nose_pixel, head_exclusion_radius, (255, 255, 0), 2)
        
        # Labels
        cv2.putText(image, "SHOULDER REF", (10, shoulder_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        cv2.putText(image, "HEAD", (nose_pixel[0] + 15, nose_pixel[1] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        cv2.putText(image, "HEAD ZONE", (nose_pixel[0] + 15, nose_pixel[1] + head_exclusion_radius + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
        
    except (IndexError, AttributeError):
        pass
    
    return image

def draw_gesture_status(image, gesture_result, human_result):
    """Draw gesture detection status overlay."""
    h, w = image.shape[:2]
    
    # Background for text
    overlay = image.copy()
    cv2.rectangle(overlay, (10, 10), (400, 220), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)
    
    y_offset = 30
    line_height = 25
    
    # Human detection status
    color = (0, 255, 0) if human_result.human_present else (0, 0, 255)
    text = f"Human: {'YES' if human_result.human_present else 'NO'} ({human_result.confidence:.2f})"
    cv2.putText(image, text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    y_offset += line_height
    
    # Gesture detection status with different colors for different types
    if gesture_result and gesture_result.gesture_detected:
        if gesture_result.gesture_type == "stop":
            color = (0, 255, 0)  # Green for stop gesture
        elif gesture_result.gesture_type == "peace":
            color = (0, 255, 255)  # Yellow for peace sign
        else:
            color = (255, 255, 255)  # White for other gestures
            
        text = f"Gesture: {gesture_result.gesture_type} ({gesture_result.confidence:.2f})"
        cv2.putText(image, text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        y_offset += line_height
        
        # Palm facing status
        if hasattr(gesture_result, 'palm_facing_camera'):
            palm_color = (0, 255, 0) if gesture_result.palm_facing_camera else (0, 0, 255)
            palm_text = f"Palm facing: {'YES' if gesture_result.palm_facing_camera else 'NO'}"
            cv2.putText(image, palm_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, palm_color, 2)
        
        y_offset += line_height
        
        # Hand position
        if hasattr(gesture_result, 'position'):
            pos = gesture_result.position
            pos_text = f"Hand: ({pos.get('hand_x', 0):.2f}, {pos.get('hand_y', 0):.2f})"
            cv2.putText(image, pos_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            y_offset += line_height
            
            # Finger count (NEW)
            if 'extended_fingers' in pos:
                finger_count = pos['extended_fingers']
                finger_text = f"Fingers: {finger_count}"
                finger_color = (0, 255, 255) if finger_count == 2 else (0, 255, 0) if finger_count >= 3 else (0, 0, 255)
                cv2.putText(image, finger_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, finger_color, 2)
    else:
        color = (0, 0, 255)
        text = "Gesture: NONE"
        cv2.putText(image, text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    return image

def main():
    print("🎥 Visual Gesture Debug Tool")
    print("=" * 40)
    print("Visual debugging with live video feed showing:")
    print("- Hand landmarks (green dots)")
    print("- Palm orientation arrows (green=facing, red=away)")
    print("- Shoulder reference line (blue)")
    print("- Head/nose landmark (yellow dot)")
    print("- Head exclusion zone (yellow circle)")
    print("- Real-time confidence scores")
    print()
    print("Press 'q' to quit")
    print()

    # Initialize components
    camera = CameraManager(CameraConfig())
    human_detector = create_detector('multimodal')
    human_detector.initialize()
    
    gesture_detector = GestureDetector()
    gesture_detector.initialize()
    
    # MediaPipe drawing utilities
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose
    
    frame_count = 0
    
    try:
        while True:
            frame = camera.get_frame()
            if frame is not None:
                frame_count += 1
                
                # Make a copy for drawing
                debug_frame = frame.copy()
                
                # Run human detection
                human_result = human_detector.detect(frame)
                
                # Run gesture detection if human present
                gesture_result = None
                if human_result.human_present:
                    pose_landmarks = getattr(human_result, '_original_pose_landmarks', None)
                    gesture_result = gesture_detector.detect_gestures(frame, pose_landmarks)
                    
                    # Draw shoulder reference
                    debug_frame = draw_shoulder_reference(debug_frame, pose_landmarks)
                    
                    # Get hand detection for visualization
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    hands_detector = gesture_detector._hands_detector
                    hands_results = hands_detector.process(rgb_frame)
                    
                    if hands_results.multi_hand_landmarks:
                        for hand_idx, hand_landmarks in enumerate(hands_results.multi_hand_landmarks):
                            # Draw hand landmarks
                            mp_drawing.draw_landmarks(
                                debug_frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2)
                            )
                            
                            # Get hand label
                            hand_label = "unknown"
                            if hands_results.multi_handedness and hand_idx < len(hands_results.multi_handedness):
                                hand_info = hands_results.multi_handedness[hand_idx]
                                hand_label = hand_info.classification[0].label.lower()
                            
                            # Calculate and draw palm orientation
                            palm_normal = gesture_detector._calculate_palm_normal(hand_landmarks, hand_label)
                            debug_frame = draw_palm_orientation(debug_frame, hand_landmarks, palm_normal, hand_label)
                
                # Draw status overlay
                debug_frame = draw_gesture_status(debug_frame, gesture_result, human_result)
                
                # Show frame
                cv2.imshow('Gesture Debug', debug_frame)
                
                # Check for quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")
    finally:
        print("🧹 Cleaning up...")
        cv2.destroyAllWindows()
        gesture_detector.cleanup()
        human_detector.cleanup()
        camera.cleanup()
        print("✅ Done!")

if __name__ == "__main__":
    main() 