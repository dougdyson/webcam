"""
OpenCV Sample Code for Webcam Human Detection Project

This file contains starter code and examples for common OpenCV operations
used in webcam capture and frame processing.
"""

import cv2
import numpy as np
import time
from typing import Optional, Tuple


def basic_camera_capture():
    """Basic camera capture and display loop."""
    # Initialize camera
    cap = cv2.VideoCapture(0)
    
    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    print("Press 'q' to quit")
    
    while True:
        # Capture frame
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Failed to capture frame")
            break
        
        # Display frame
        cv2.imshow('Camera Feed', frame)
        
        # Exit on 'q' press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()


def camera_with_error_handling():
    """Camera capture with robust error handling."""
    cap = None
    
    try:
        # Initialize camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            raise RuntimeError("Cannot open camera")
        
        # Verify camera is working
        ret, test_frame = cap.read()
        if not ret:
            raise RuntimeError("Cannot read from camera")
        
        print(f"Camera initialized: {test_frame.shape}")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("Warning: Failed to read frame, attempting to reconnect...")
                cap.release()
                cap = cv2.VideoCapture(0)
                continue
            
            # Calculate FPS
            frame_count += 1
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"FPS: {fps:.2f}")
            
            # Process frame here
            processed_frame = frame.copy()
            
            # Add FPS counter to frame
            cv2.putText(processed_frame, f"Frame: {frame_count}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow('Camera with Error Handling', processed_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        print(f"Camera error: {e}")
        
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()


def frame_processing_examples(frame: np.ndarray) -> np.ndarray:
    """Examples of common frame processing operations."""
    
    # Convert to different color spaces
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # For MediaPipe
    
    # Resize frame (useful for performance)
    small_frame = cv2.resize(frame, (320, 240))
    
    # Gaussian blur (noise reduction)
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Draw rectangles and text
    annotated = frame.copy()
    cv2.rectangle(annotated, (50, 50), (200, 150), (0, 255, 0), 2)
    cv2.putText(annotated, "Human Detected", (55, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return annotated


def camera_configuration_class():
    """Example camera configuration and management class."""
    
    class CameraConfig:
        def __init__(self, device_id: int = 0, width: int = 640, 
                     height: int = 480, fps: int = 30):
            self.device_id = device_id
            self.width = width
            self.height = height
            self.fps = fps
    
    class CameraManager:
        def __init__(self, config: CameraConfig):
            self.config = config
            self.cap = None
            self.is_initialized = False
        
        def initialize(self) -> bool:
            """Initialize camera with configuration."""
            try:
                self.cap = cv2.VideoCapture(self.config.device_id)
                
                if not self.cap.isOpened():
                    return False
                
                # Apply configuration
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
                
                # Verify settings
                actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
                
                print(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")
                
                self.is_initialized = True
                return True
                
            except Exception as e:
                print(f"Camera initialization failed: {e}")
                return False
        
        def get_frame(self) -> Optional[np.ndarray]:
            """Capture a single frame."""
            if not self.is_initialized or self.cap is None:
                return None
            
            ret, frame = self.cap.read()
            return frame if ret else None
        
        def release(self):
            """Release camera resources."""
            if self.cap is not None:
                self.cap.release()
                self.is_initialized = False
    
    # Usage example
    config = CameraConfig(device_id=0, width=640, height=480, fps=30)
    manager = CameraManager(config)
    
    if manager.initialize():
        for i in range(10):
            frame = manager.get_frame()
            if frame is not None:
                print(f"Captured frame {i}: {frame.shape}")
            time.sleep(0.1)
    
    manager.release()


def performance_monitoring():
    """Example of FPS and performance monitoring."""
    
    class FrameRateMonitor:
        def __init__(self, window_size: int = 30):
            self.window_size = window_size
            self.frame_times = []
            self.frame_count = 0
        
        def update(self):
            """Update with new frame timestamp."""
            current_time = time.time()
            self.frame_times.append(current_time)
            self.frame_count += 1
            
            # Keep only recent frames
            if len(self.frame_times) > self.window_size:
                self.frame_times.pop(0)
        
        def get_fps(self) -> float:
            """Calculate current FPS."""
            if len(self.frame_times) < 2:
                return 0.0
            
            time_span = self.frame_times[-1] - self.frame_times[0]
            if time_span == 0:
                return 0.0
            
            return (len(self.frame_times) - 1) / time_span
        
        def get_total_frames(self) -> int:
            """Get total frame count."""
            return self.frame_count
    
    # Usage in camera loop
    cap = cv2.VideoCapture(0)
    monitor = FrameRateMonitor()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        monitor.update()
        
        # Display FPS every 30 frames
        if monitor.get_total_frames() % 30 == 0:
            fps = monitor.get_fps()
            print(f"Current FPS: {fps:.2f}")
        
        # Add FPS to frame
        fps_text = f"FPS: {monitor.get_fps():.1f}"
        cv2.putText(frame, fps_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('Performance Monitor', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()


def save_and_load_frames():
    """Examples of saving and loading frames for testing."""
    
    # Capture and save a frame
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    
    if ret:
        # Save frame as image
        cv2.imwrite('captured_frame.jpg', frame)
        print("Frame saved as captured_frame.jpg")
        
        # Save frame info
        height, width, channels = frame.shape
        print(f"Frame info: {width}x{height}, {channels} channels")
    
    cap.release()
    
    # Load frame from file
    loaded_frame = cv2.imread('captured_frame.jpg')
    if loaded_frame is not None:
        print(f"Loaded frame: {loaded_frame.shape}")
        cv2.imshow('Loaded Frame', loaded_frame)
        cv2.waitKey(1000)  # Show for 1 second
        cv2.destroyAllWindows()


if __name__ == "__main__":
    print("OpenCV Sample Code")
    print("1. Basic camera capture")
    print("2. Camera with error handling")
    print("3. Camera configuration class")
    print("4. Performance monitoring")
    print("5. Save and load frames")
    
    choice = input("Enter choice (1-5): ")
    
    if choice == "1":
        basic_camera_capture()
    elif choice == "2":
        camera_with_error_handling()
    elif choice == "3":
        camera_configuration_class()
    elif choice == "4":
        performance_monitoring()
    elif choice == "5":
        save_and_load_frames()
    else:
        print("Invalid choice") 