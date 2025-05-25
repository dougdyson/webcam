"""
MediaPipe Sample Code for Human Detection

This file contains starter code and examples for MediaPipe human detection
including pose detection, face detection, and holistic solutions.
"""

import cv2
import mediapipe as mp
import numpy as np
import time
from typing import Optional, Tuple, List


def basic_pose_detection():
    """Basic pose detection using MediaPipe Pose."""
    
    # Initialize MediaPipe
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    
    # Configure pose detection
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = pose.process(rgb_frame)
        
        # Draw pose landmarks
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # Print detection confidence (if available)
            print("Person detected!")
        else:
            print("No person detected")
        
        cv2.imshow('MediaPipe Pose', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    pose.close()


def face_detection_example():
    """Face detection using MediaPipe Face Detection."""
    
    mp_face_detection = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils
    
    # Configure face detection
    face_detection = mp_face_detection.FaceDetection(
        model_selection=0,  # 0 for short-range (2 meters), 1 for full-range
        min_detection_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = face_detection.process(rgb_frame)
        
        # Draw face detections
        if results.detections:
            for detection in results.detections:
                mp_drawing.draw_detection(frame, detection)
                
                # Get detection confidence
                confidence = detection.score[0]
                print(f"Face detected with confidence: {confidence:.2f}")
        else:
            print("No face detected")
        
        cv2.imshow('MediaPipe Face Detection', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    face_detection.close()


def holistic_detection():
    """Holistic detection (face, pose, hands) using MediaPipe Holistic."""
    
    mp_holistic = mp.solutions.holistic
    mp_drawing = mp.solutions.drawing_utils
    
    # Configure holistic detection
    holistic = mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        refine_face_landmarks=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = holistic.process(rgb_frame)
        
        # Draw landmarks
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)
        
        if results.face_landmarks:
            mp_drawing.draw_landmarks(
                frame, results.face_landmarks, mp_holistic.FACEMESH_CONTOURS)
        
        if results.left_hand_landmarks:
            mp_drawing.draw_landmarks(
                frame, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
        
        if results.right_hand_landmarks:
            mp_drawing.draw_landmarks(
                frame, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
        
        # Determine if human is present
        human_present = any([
            results.pose_landmarks,
            results.face_landmarks,
            results.left_hand_landmarks,
            results.right_hand_landmarks
        ])
        
        # Display status
        status = "HUMAN DETECTED" if human_present else "NO HUMAN"
        color = (0, 255, 0) if human_present else (0, 0, 255)
        cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        cv2.imshow('MediaPipe Holistic', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    holistic.close()


def pose_landmark_analysis():
    """Detailed pose landmark analysis and confidence calculation."""
    
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    def calculate_pose_confidence(landmarks) -> float:
        """Calculate average confidence of key pose landmarks."""
        if not landmarks:
            return 0.0
        
        # Key landmarks for human detection
        key_landmarks = [
            mp_pose.PoseLandmark.NOSE,
            mp_pose.PoseLandmark.LEFT_SHOULDER,
            mp_pose.PoseLandmark.RIGHT_SHOULDER,
            mp_pose.PoseLandmark.LEFT_HIP,
            mp_pose.PoseLandmark.RIGHT_HIP
        ]
        
        total_visibility = 0.0
        count = 0
        
        for landmark_id in key_landmarks:
            landmark = landmarks.landmark[landmark_id.value]
            total_visibility += landmark.visibility
            count += 1
        
        return total_visibility / count if count > 0 else 0.0
    
    def get_bounding_box(landmarks, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
        """Calculate bounding box around pose landmarks."""
        if not landmarks:
            return (0, 0, 0, 0)
        
        x_coords = [landmark.x * frame_width for landmark in landmarks.landmark]
        y_coords = [landmark.y * frame_height for landmark in landmarks.landmark]
        
        min_x = int(min(x_coords))
        max_x = int(max(x_coords))
        min_y = int(min(y_coords))
        max_y = int(max(y_coords))
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
    
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_height, frame_width = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process the frame
        results = pose.process(rgb_frame)
        
        if results.pose_landmarks:
            # Draw landmarks
            mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            # Calculate confidence
            confidence = calculate_pose_confidence(results.pose_landmarks)
            
            # Get bounding box
            bbox = get_bounding_box(results.pose_landmarks, frame_width, frame_height)
            
            # Draw bounding box
            if bbox[2] > 0 and bbox[3] > 0:  # Valid bounding box
                cv2.rectangle(frame, (bbox[0], bbox[1]), 
                             (bbox[0] + bbox[2], bbox[1] + bbox[3]), (0, 255, 0), 2)
            
            # Display information
            cv2.putText(frame, f"Confidence: {confidence:.2f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"BBox: {bbox}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            print(f"Human detected - Confidence: {confidence:.3f}, BBox: {bbox}")
        else:
            cv2.putText(frame, "No human detected", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow('Pose Analysis', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    pose.close()


def detection_result_class():
    """Example detection result class structure."""
    
    from dataclasses import dataclass
    from typing import Optional, List, Tuple
    
    @dataclass
    class DetectionResult:
        """Standardized detection result format."""
        human_present: bool
        confidence: float
        bounding_box: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
        landmarks: Optional[List[Tuple[float, float]]] = None
        timestamp: float = None
        
        def __post_init__(self):
            if self.timestamp is None:
                self.timestamp = time.time()
            
            # Validate confidence range
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("Confidence must be between 0.0 and 1.0")
    
    class MediaPipeDetector:
        """Example MediaPipe detector class."""
        
        def __init__(self, model_complexity: int = 1, min_confidence: float = 0.5):
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=model_complexity,
                min_detection_confidence=min_confidence,
                min_tracking_confidence=min_confidence
            )
            self.is_initialized = True
        
        def detect(self, frame: np.ndarray) -> DetectionResult:
            """Detect human in frame and return standardized result."""
            if not self.is_initialized:
                return DetectionResult(human_present=False, confidence=0.0)
            
            # Convert to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame
            results = self.pose.process(rgb_frame)
            
            if results.pose_landmarks:
                # Calculate confidence
                confidence = self._calculate_confidence(results.pose_landmarks)
                
                # Extract bounding box
                bbox = self._get_bounding_box(results.pose_landmarks, frame.shape[1], frame.shape[0])
                
                # Extract key landmarks
                landmarks = self._extract_landmarks(results.pose_landmarks)
                
                return DetectionResult(
                    human_present=True,
                    confidence=confidence,
                    bounding_box=bbox,
                    landmarks=landmarks
                )
            else:
                return DetectionResult(human_present=False, confidence=0.0)
        
        def _calculate_confidence(self, landmarks) -> float:
            """Calculate average visibility of key landmarks."""
            key_landmarks = [0, 11, 12, 23, 24]  # Nose, shoulders, hips
            
            if not landmarks:
                return 0.0
            
            total_visibility = sum(landmarks.landmark[i].visibility for i in key_landmarks)
            return total_visibility / len(key_landmarks)
        
        def _get_bounding_box(self, landmarks, width: int, height: int) -> Tuple[int, int, int, int]:
            """Calculate bounding box around landmarks."""
            x_coords = [landmark.x * width for landmark in landmarks.landmark]
            y_coords = [landmark.y * height for landmark in landmarks.landmark]
            
            min_x, max_x = int(min(x_coords)), int(max(x_coords))
            min_y, max_y = int(min(y_coords)), int(max(y_coords))
            
            return (min_x, min_y, max_x - min_x, max_y - min_y)
        
        def _extract_landmarks(self, landmarks) -> List[Tuple[float, float]]:
            """Extract normalized landmark coordinates."""
            return [(landmark.x, landmark.y) for landmark in landmarks.landmark]
        
        def cleanup(self):
            """Release resources."""
            if hasattr(self, 'pose'):
                self.pose.close()
            self.is_initialized = False
    
    # Usage example
    detector = MediaPipeDetector(model_complexity=1, min_confidence=0.5)
    cap = cv2.VideoCapture(0)
    
    for _ in range(10):  # Process 10 frames
        ret, frame = cap.read()
        if ret:
            result = detector.detect(frame)
            print(f"Detection: {result.human_present}, Confidence: {result.confidence:.3f}")
    
    cap.release()
    detector.cleanup()


def performance_optimization():
    """Performance optimization techniques for MediaPipe."""
    
    import threading
    from queue import Queue
    
    class OptimizedDetector:
        """Optimized MediaPipe detector with threading."""
        
        def __init__(self):
            self.mp_pose = mp.solutions.pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=0,  # Faster, less accurate
                enable_segmentation=False,  # Disable segmentation for speed
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            
            self.frame_queue = Queue(maxsize=5)
            self.result_queue = Queue(maxsize=5)
            self.processing_thread = None
            self.running = False
        
        def start_processing(self):
            """Start background processing thread."""
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_frames)
            self.processing_thread.start()
        
        def stop_processing(self):
            """Stop background processing."""
            self.running = False
            if self.processing_thread:
                self.processing_thread.join()
        
        def _process_frames(self):
            """Background frame processing loop."""
            while self.running:
                try:
                    if not self.frame_queue.empty():
                        frame = self.frame_queue.get(timeout=0.1)
                        
                        # Resize for faster processing
                        small_frame = cv2.resize(frame, (320, 240))
                        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        
                        # Process
                        results = self.pose.process(rgb_frame)
                        
                        # Store result
                        human_present = results.pose_landmarks is not None
                        if not self.result_queue.full():
                            self.result_queue.put(human_present)
                        
                except:
                    continue
        
        def add_frame(self, frame: np.ndarray):
            """Add frame for processing."""
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
        
        def get_latest_result(self) -> Optional[bool]:
            """Get latest detection result."""
            if not self.result_queue.empty():
                return self.result_queue.get()
            return None
    
    # Usage example
    detector = OptimizedDetector()
    detector.start_processing()
    
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Add frame for processing
        detector.add_frame(frame)
        
        # Get latest result
        result = detector.get_latest_result()
        if result is not None:
            status = "HUMAN DETECTED" if result else "NO HUMAN"
            color = (0, 255, 0) if result else (0, 0, 255)
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        cv2.imshow('Optimized Detection', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    detector.stop_processing()


if __name__ == "__main__":
    print("MediaPipe Sample Code")
    print("1. Basic pose detection")
    print("2. Face detection")
    print("3. Holistic detection")
    print("4. Pose landmark analysis")
    print("5. Detection result class")
    print("6. Performance optimization")
    
    choice = input("Enter choice (1-6): ")
    
    if choice == "1":
        basic_pose_detection()
    elif choice == "2":
        face_detection_example()
    elif choice == "3":
        holistic_detection()
    elif choice == "4":
        pose_landmark_analysis()
    elif choice == "5":
        detection_result_class()
    elif choice == "6":
        performance_optimization()
    else:
        print("Invalid choice") 