#!/usr/bin/env python3
"""
Live Gesture Video Test - Shows webcam feed with real-time gesture status.
"""

import os
import cv2
import time
import numpy as np
import mediapipe as mp

# Suppress MediaPipe logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import logging
logging.getLogger('mediapipe').setLevel(logging.ERROR)
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from src.camera import CameraManager, CameraConfig
from src.detection import create_detector, DetectorConfig
from src.detection.gesture_detector import GestureDetector

def main():
    print("🎬 Live Gesture Video Test")
    print("Initializing...")

    try:
        camera_config = CameraConfig(device_id=0, width=640, height=480, fps=30)
        camera = CameraManager(camera_config)
        
        # Use a basic detector config
        detector_config = DetectorConfig(min_detection_confidence=0.5)
        
        human_detector = create_detector('multimodal', config=detector_config)
        human_detector.initialize()
        
        gesture_detector = GestureDetector(config=detector_config) # Pass config here too
        gesture_detector.initialize()
        
        print("✅ Initialization Complete. Press 'q' to quit.")

    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return

    frame_count = 0
    start_time = time.time()

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            frame_count += 1
            display_frame = frame.copy()

            try:
                # 1. Human Detection
                human_result = human_detector.detect(display_frame)
                human_present = human_result.human_present and human_result.confidence > 0.6 # Stricter for display
                
                # 2. Gesture Detection (only if human present and landmarks available)
                gesture_text = "GESTURE: NONE"
                gesture_color = (0, 0, 255) # Red for no gesture

                if human_present and human_result.landmarks:
                    try:
                        # We need access to the raw hands_results for handedness
                        rgb_frame_for_hands = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                        hands_results = gesture_detector._hands_detector.process(rgb_frame_for_hands)

                        processed_hands = 0
                        if hands_results.multi_hand_landmarks:
                            for hand_idx, hand_landmarks_mp in enumerate(hands_results.multi_hand_landmarks):
                                processed_hands += 1
                                hand_label = "unknown"
                                if hands_results.multi_handedness and hand_idx < len(hands_results.multi_handedness):
                                    hand_info = hands_results.multi_handedness[hand_idx]
                                    hand_label = hand_info.classification[0].label.lower()
                                
                                # Pass hand_label to _calculate_palm_normal if it accepts it
                                # For now, we assume it doesn't, and we'll adjust based on print output
                                palm_normal = gesture_detector._calculate_palm_normal(hand_landmarks_mp) # Original call
                                palm_z = palm_normal[2]
                                
                                print(f"🖐️ HAND {hand_idx+1}/{len(hands_results.multi_hand_landmarks)}: Label: {hand_label}, Palm Normal Z: {palm_z:.3f}, Num Landmrks: {len(hand_landmarks_mp.landmark)}")

                                # Perform gesture classification for *this specific hand* to update display
                                # Create a temporary hands_results for a single hand to pass to _process_gesture_detection
                                single_hand_results = mp.solutions.hands.Hands().process(np.zeros_like(rgb_frame_for_hands)) # Dummy process
                                single_hand_results.multi_hand_landmarks = [hand_landmarks_mp]
                                single_hand_results.multi_handedness = [hands_results.multi_handedness[hand_idx]] if hands_results.multi_handedness else []

                                current_gesture_result = gesture_detector._process_gesture_detection(
                                    single_hand_results, 
                                    human_result.landmarks, 
                                    display_frame.shape
                                )

                                if current_gesture_result.gesture_detected:
                                    gesture_text = f"GESTURE: {current_gesture_result.gesture_type.upper()} ({current_gesture_result.confidence:.2f}) L:{hand_label}"
                                    gesture_color = (0, 255, 0) 
                                    break # Show first detected gesture for now
                                else:
                                    gesture_text = f"GESTURE: NONE L:{hand_label}" # Update for current hand
                        
                        if processed_hands == 0: # No hands were processed by the loop
                             gesture_text = "GESTURE: NONE (no hands found by MediaPipe)"

                    except Exception as e_gesture:
                        print(f"Error in gesture detection: {e_gesture}") # Keep it simple for overlay


                # 3. Display Information on Frame
                # Human Status
                human_text = f"HUMAN: {'YES' if human_present else 'NO'} ({human_result.confidence:.2f})"
                human_color = (0, 255, 0) if human_present else (0, 0, 255)
                cv2.putText(display_frame, human_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, human_color, 2)

                # Gesture Status
                cv2.putText(display_frame, gesture_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, gesture_color, 2)
                
                # FPS
                if frame_count > 1:
                    fps = (frame_count -1) / (time.time() - start_time)
                    cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)


            except Exception as e_detect:
                print(f"❌ Error during detection loop: {e_detect}")
                cv2.putText(display_frame, "DETECTION ERROR", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)


            cv2.imshow('Live Gesture Test', display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Keep console clean unless there are critical debug messages
            # time.sleep(0.01) # Run as fast as possible

    except KeyboardInterrupt:
        print("🛑 User interrupted. Stopping...")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Cleaning up...")
        camera.cleanup()
        if 'human_detector' in locals() and human_detector.is_initialized:
             human_detector.cleanup()
        if 'gesture_detector' in locals() and gesture_detector.is_initialized:
             gesture_detector.cleanup()
        cv2.destroyAllWindows()
        print("✅ Done.")

if __name__ == "__main__":
    main() 