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

import argparse
import cv2
import numpy as np
import sys
import os
# Add project root to Python path and set working directory
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)
os.chdir(_PROJECT_ROOT)

from src.camera import CameraManager, CameraConfig
from src.detection import create_detector
from src.detection.neural_detector import NeuralDetector
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

def draw_gesture_status(image, gesture_result, human_result, neural_result=None):
    """Draw gesture detection status overlay with detailed debug info."""
    h, w = image.shape[:2]

    # Background for text - make it bigger for more info
    overlay = image.copy()
    cv2.rectangle(overlay, (10, 10), (500, 320), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.7, image, 0.3, 0, image)

    y_offset = 30
    line_height = 25

    # Neural detector (MobileNet-SSD) status — this is what the service uses
    if neural_result is not None:
        n_color = (0, 255, 0) if neural_result.human_present else (0, 0, 255)
        n_text = f"Neural (SSD): {'YES' if neural_result.human_present else 'NO'} ({neural_result.confidence:.2f})"
        cv2.putText(image, n_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, n_color, 2)
        y_offset += line_height
        # Draw neural bbox
        if neural_result.bounding_box:
            bx, by, bw, bh = neural_result.bounding_box
            cv2.rectangle(image, (bx, by), (bx + bw, by + bh), (0, 165, 255), 2)
            cv2.putText(image, f"SSD {neural_result.confidence:.2f}", (bx, by - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

    # MediaPipe (pose+face) status — skeletal confidence
    color = (0, 255, 0) if human_result.human_present else (0, 0, 255)
    text = f"MediaPipe: {'YES' if human_result.human_present else 'NO'} ({human_result.confidence:.2f})"
    cv2.putText(image, text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    y_offset += line_height
    
    # Gesture detection status with ALL MediaPipe gesture colors
    if gesture_result and gesture_result.gesture_detected:
        if gesture_result.gesture_type == "Open_Palm":
            color = (0, 255, 0)  # Green for Open_Palm gesture (MediaPipe default)
        elif gesture_result.gesture_type == "Victory":
            color = (0, 255, 255)  # Yellow for Victory sign (MediaPipe default)
        elif gesture_result.gesture_type == "Thumb_Up":
            color = (255, 255, 0)  # Cyan for Thumbs Up
        elif gesture_result.gesture_type == "Thumb_Down":
            color = (0, 0, 255)  # Red for Thumbs Down
        elif gesture_result.gesture_type == "Closed_Fist":
            color = (128, 0, 128)  # Purple for Closed Fist
        elif gesture_result.gesture_type == "Pointing_Up":
            color = (255, 165, 0)  # Orange for Pointing Up
        elif gesture_result.gesture_type == "ILoveYou":
            color = (255, 192, 203)  # Pink for I Love You
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
        
        # Hand position and detailed finger info
        if hasattr(gesture_result, 'position'):
            pos = gesture_result.position
            pos_text = f"Hand: ({pos.get('hand_x', 0):.2f}, {pos.get('hand_y', 0):.2f})"
            cv2.putText(image, pos_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            y_offset += line_height
            
            # Finger count with detailed breakdown
            if 'extended_fingers' in pos:
                finger_count = pos['extended_fingers']
                finger_text = f"Fingers Extended: {finger_count}/5"
                
                # Color based on finger count for gesture classification
                if finger_count == 0:
                    finger_color = (128, 0, 128)  # Purple - likely Closed_Fist
                elif finger_count == 1:
                    finger_color = (255, 165, 0)  # Orange - likely Pointing_Up or Thumb
                elif finger_count == 2:
                    finger_color = (0, 255, 255)  # Yellow - likely Victory
                elif finger_count >= 3:
                    finger_color = (0, 255, 0)  # Green - likely Open_Palm
                else:
                    finger_color = (255, 255, 255)  # White - unknown
                    
                cv2.putText(image, finger_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, finger_color, 2)
                
                y_offset += line_height
                
                # Show individual finger states
                if 'fingers' in pos:
                    fingers = pos['fingers']
                    finger_status = []
                    finger_names = ['T', 'I', 'M', 'R', 'P']  # Thumb, Index, Middle, Ring, Pinky
                    finger_keys = ['thumb', 'index', 'middle', 'ring', 'pinky']
                    
                    for name, key in zip(finger_names, finger_keys):
                        if fingers.get(key, False):
                            finger_status.append(f"{name}✓")
                        else:
                            finger_status.append(f"{name}✗")
                    
                    finger_detail = "Fingers: " + " ".join(finger_status)
                    cv2.putText(image, finger_detail, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 2)
                    y_offset += line_height
                
                # Show what gesture SHOULD be detected based on finger pattern
                expected_gesture = "Unknown"
                if 'fingers' in pos:
                    fingers = pos['fingers']
                    if finger_count == 0:
                        expected_gesture = "Should be: Closed_Fist"
                    elif finger_count == 1:
                        if fingers.get('thumb'):
                            expected_gesture = "Should be: Thumb_Up/Down"
                        elif fingers.get('index'):
                            expected_gesture = "Should be: Pointing_Up"
                        else:
                            expected_gesture = "Should be: Single finger gesture"
                    elif finger_count == 2:
                        if fingers.get('index') and fingers.get('middle'):
                            expected_gesture = "Should be: Victory"
                        else:
                            expected_gesture = "Should be: Two finger gesture"
                    elif finger_count == 3:
                        if (fingers.get('thumb') and fingers.get('index') and fingers.get('pinky') and
                            not fingers.get('middle') and not fingers.get('ring')):
                            expected_gesture = "Should be: ILoveYou"
                        else:
                            expected_gesture = "Should be: Open_Palm"
                    elif finger_count >= 4:
                        expected_gesture = "Should be: Open_Palm"
                else:
                    if finger_count == 0:
                        expected_gesture = "Should be: Closed_Fist"
                    elif finger_count == 1:
                        expected_gesture = "Should be: Pointing_Up or Thumb"
                    elif finger_count == 2:
                        expected_gesture = "Should be: Victory"
                    elif finger_count >= 3:
                        expected_gesture = "Should be: Open_Palm"
                
                cv2.putText(image, expected_gesture, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 2)
                y_offset += line_height
    else:
        color = (0, 0, 255)
        text = "Gesture: NONE (Unknown)"
        cv2.putText(image, text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y_offset += line_height
        
        # Show debug info for why no gesture was detected
        debug_text = "Reasons: Check shoulder pos, palm facing, arm geometry"
        cv2.putText(image, debug_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    
    # Add instruction text at bottom
    y_offset = h - 60
    instruction_color = (255, 255, 255)
    cv2.putText(image, "Try: Open Palm, Victory, Thumbs Up/Down, Fist, Point Up, I Love You", 
                (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, instruction_color, 1)
    cv2.putText(image, "Currently detecting: Open_Palm (3+ fingers), Victory (2 fingers)", 
                (20, y_offset + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 200), 1)
    cv2.putText(image, "Need to add: Closed_Fist, Pointing_Up, Thumbs, ILoveYou detection!", 
                (20, y_offset + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 200), 1)
    
    return image

def main():
    parser = argparse.ArgumentParser(description="Visual Gesture Debug Tool")
    parser.add_argument("--diag", action="store_true",
                        help="Enable diagnostic logging: print neural state changes and save snapshots to /tmp/ziggy-webcam/diagnostics/")
    args = parser.parse_args()

    print("🎥 Visual Gesture Debug Tool")
    print("=" * 40)
    print("Visual debugging with live video feed showing:")
    print("- Hand landmarks (green dots)")
    print("- Palm orientation arrows (green=facing, red=away)")
    print("- Shoulder reference line (blue)")
    print("- Head/nose landmark (yellow dot)")
    print("- Head exclusion zone (yellow circle)")
    print("- Real-time confidence scores")
    if args.diag:
        print("- DIAGNOSTIC MODE: logging neural state changes + saving snapshots")
    print()
    print("Press 'q' to quit")
    print()

    # Initialize components
    camera = CameraManager(CameraConfig())
    human_detector = create_detector('multimodal')
    human_detector.initialize()

    # Neural detector (MobileNet-SSD) — same model the service uses
    neural_detector = NeuralDetector()
    neural_detector.initialize()
    print("  Neural detector (MobileNet-SSD) initialized")

    gesture_detector = GestureDetector()
    gesture_detector.initialize()

    # Diagnostic snapshot directory (only when --diag)
    diag_dir = "/tmp/ziggy-webcam/diagnostics"
    if args.diag:
        os.makedirs(diag_dir, exist_ok=True)
        print(f"  Diagnostic snapshots → {diag_dir}")

    # MediaPipe drawing utilities
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    frame_count = 0
    last_neural_state = None

    try:
        while True:
            frame = camera.get_frame()
            if frame is not None:
                frame_count += 1

                # Make a copy for drawing
                debug_frame = frame.copy()

                # Run both detectors
                human_result = human_detector.detect(frame)
                neural_result = neural_detector.detect(frame)

                # Log and snapshot on neural state change (--diag only)
                if args.diag and last_neural_state is not None and neural_result.human_present != last_neural_state:
                    from datetime import datetime
                    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    direction = "ENTER" if neural_result.human_present else "EXIT"
                    bbox = neural_result.bounding_box
                    bbox_desc = ""
                    if bbox:
                        h, w = frame.shape[:2]
                        bx, by, bw, bh = bbox
                        cx = bx + bw // 2
                        horiz = "left" if cx < w // 3 else ("right" if cx > 2 * w // 3 else "center")
                        vert = "top" if by < h // 3 else ("bottom" if by > 2 * h // 3 else "middle")
                        bbox_desc = f" bbox=({bx},{by},{bw},{bh}) region={vert}-{horiz}"
                    print(f"\n⚡ NEURAL {direction} | conf={neural_result.confidence:.3f}{bbox_desc} | {ts_str}")
                    if neural_result.human_present:
                        snap = frame.copy()
                        if bbox:
                            bx, by, bw, bh = bbox
                            cv2.rectangle(snap, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
                            cv2.putText(snap, f"SSD {neural_result.confidence:.2f}",
                                        (bx, by - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        snap_path = os.path.join(diag_dir, f"debug_fp_{ts_str}.jpg")
                        cv2.imwrite(snap_path, snap)
                        print(f"  Snapshot saved: {snap_path}")
                last_neural_state = neural_result.human_present

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
                
                # Draw status overlay with both detector scores
                debug_frame = draw_gesture_status(debug_frame, gesture_result, human_result, neural_result)
                
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
        neural_detector.cleanup()
        human_detector.cleanup()
        camera.cleanup()
        print("✅ Done!")

if __name__ == "__main__":
    main() 