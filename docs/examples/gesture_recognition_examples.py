#!/usr/bin/env python3
"""
Gesture Recognition Examples

Comprehensive examples of gesture detection using MediaPipe hand landmarks,
custom gesture recognition, and integration with the webcam detection system.

Based on MediaPipe's supported gestures:
- Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou
- Plus custom gesture recognition using 21 hand landmarks

Usage:
    conda activate webcam && python docs/examples/gesture_recognition_examples.py
"""

import sys
import cv2
import time
import asyncio
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add src to path for imports
sys.path.append('src')

from camera import CameraManager, CameraConfig
from detection import create_detector
from gesture.hand_detection import HandDetector
from gesture.classification import GestureClassifier
from gesture.result import GestureResult
from service.events import EventPublisher, ServiceEvent, EventType

class BasicGestureDetection:
    """
    Example 1: Basic gesture detection using MediaPipe built-in gestures
    
    Demonstrates the 8 built-in MediaPipe gestures:
    - Unknown, Closed_Fist, Open_Palm, Pointing_Up
    - Thumb_Down, Thumb_Up, Victory, ILoveYou
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.hand_detector = HandDetector()
        self.gesture_classifier = GestureClassifier()
        
    def initialize(self):
        """Initialize detection components"""
        print("🖐️ Initializing basic gesture detection...")
        self.hand_detector.initialize()
        self.gesture_classifier.initialize()
        print("✅ Ready for gesture detection")
        
    def detect_gestures(self, frame: np.ndarray) -> Dict:
        """Detect built-in MediaPipe gestures"""
        # Detect hands first
        hand_results = self.hand_detector.detect_hands(frame)
        
        if not hand_results.hands_detected:
            return {"gestures": [], "landmarks": []}
            
        gestures = []
        for i, landmarks in enumerate(hand_results.hand_landmarks):
            # Classify gesture using MediaPipe's built-in classifier
            gesture_result = self.gesture_classifier.classify_gesture(landmarks)
            
            if gesture_result.confidence > 0.7:  # High confidence only
                gestures.append({
                    "hand_index": i,
                    "gesture": gesture_result.gesture_type,
                    "confidence": gesture_result.confidence,
                    "handedness": hand_results.handedness[i] if i < len(hand_results.handedness) else "unknown"
                })
                
        return {
            "gestures": gestures,
            "landmarks": hand_results.hand_landmarks,
            "frame_with_annotations": self._draw_gestures(frame, gestures, hand_results.hand_landmarks)
        }
    
    def _draw_gestures(self, frame: np.ndarray, gestures: List[Dict], landmarks: List) -> np.ndarray:
        """Draw gesture annotations on frame"""
        annotated_frame = frame.copy()
        
        for gesture in gestures:
            hand_idx = gesture["hand_index"]
            if hand_idx < len(landmarks):
                # Draw hand landmarks
                # (This would use MediaPipe drawing utilities in real implementation)
                
                # Add gesture text
                cv2.putText(
                    annotated_frame,
                    f"{gesture['gesture']} ({gesture['confidence']:.2f})",
                    (50, 50 + hand_idx * 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
                
        return annotated_frame
    
    def run_demo(self, duration_seconds: int = 30):
        """Run gesture detection demo"""
        print(f"🎯 Running gesture detection for {duration_seconds} seconds...")
        print("Show different hand gestures to the camera:")
        print("- ✊ Closed fist")
        print("- 🖐️ Open palm") 
        print("- 👆 Pointing up")
        print("- 👍 Thumbs up")
        print("- 👎 Thumbs down")
        print("- ✌️ Victory/Peace")
        print("- 🤟 I Love You")
        print()
        
        start_time = time.time()
        gesture_counts = {}
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            results = self.detect_gestures(frame)
            
            # Count detected gestures
            for gesture in results["gestures"]:
                gesture_type = gesture["gesture"]
                gesture_counts[gesture_type] = gesture_counts.get(gesture_type, 0) + 1
                print(f"✨ {gesture['handedness']} hand: {gesture_type} (confidence: {gesture['confidence']:.2f})")
            
            # Show annotated frame (optional - requires display)
            if "DISPLAY" in os.environ:  # Only if display available
                cv2.imshow("Gesture Detection", results["frame_with_annotations"])
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            time.sleep(0.1)  # 10 FPS
            
        print(f"\n📊 Gesture Summary:")
        for gesture, count in gesture_counts.items():
            print(f"   {gesture}: {count} detections")
            
    def cleanup(self):
        """Clean up resources"""
        self.camera.cleanup()
        cv2.destroyAllWindows()


class CustomGestureDetection:
    """
    Example 2: Custom gesture recognition using 21 hand landmarks
    
    Demonstrates how to create custom gestures using MediaPipe's
    21 hand landmark coordinates for specialized applications.
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.hand_detector = HandDetector()
        
    def initialize(self):
        """Initialize detection components"""
        print("🎯 Initializing custom gesture detection...")
        self.hand_detector.initialize()
        print("✅ Ready for custom gesture detection")
        
    def detect_custom_gestures(self, frame: np.ndarray) -> Dict:
        """Detect custom gestures using landmark analysis"""
        hand_results = self.hand_detector.detect_hands(frame)
        
        if not hand_results.hands_detected:
            return {"custom_gestures": []}
            
        custom_gestures = []
        
        for i, landmarks in enumerate(hand_results.hand_landmarks):
            # Convert landmarks to normalized coordinates
            landmark_coords = self._extract_landmark_coordinates(landmarks)
            
            # Detect custom gestures
            custom_gesture = self._analyze_custom_gestures(landmark_coords)
            
            if custom_gesture:
                custom_gestures.append({
                    "hand_index": i,
                    "custom_gesture": custom_gesture["name"],
                    "confidence": custom_gesture["confidence"],
                    "handedness": hand_results.handedness[i] if i < len(hand_results.handedness) else "unknown",
                    "landmarks": landmark_coords
                })
                
        return {"custom_gestures": custom_gestures}
    
    def _extract_landmark_coordinates(self, landmarks) -> List[Tuple[float, float]]:
        """Extract (x, y) coordinates from MediaPipe landmarks"""
        coords = []
        for landmark in landmarks.landmark:
            coords.append((landmark.x, landmark.y))
        return coords
    
    def _analyze_custom_gestures(self, landmarks: List[Tuple[float, float]]) -> Optional[Dict]:
        """
        Analyze landmarks for custom gestures
        
        MediaPipe hand landmarks (21 points):
        0: WRIST
        1-4: THUMB (tip to base)
        5-8: INDEX_FINGER (tip to base)  
        9-12: MIDDLE_FINGER (tip to base)
        13-16: RING_FINGER (tip to base)
        17-20: PINKY (tip to base)
        """
        
        # Example: "Finger Gun" gesture (index extended, others folded)
        finger_gun_confidence = self._detect_finger_gun(landmarks)
        if finger_gun_confidence > 0.8:
            return {"name": "finger_gun", "confidence": finger_gun_confidence}
            
        # Example: "Rock Horn" gesture (index + pinky extended)
        rock_horn_confidence = self._detect_rock_horn(landmarks)
        if rock_horn_confidence > 0.8:
            return {"name": "rock_horn", "confidence": rock_horn_confidence}
            
        # Example: "OK" gesture (thumb + index circle)
        ok_confidence = self._detect_ok_gesture(landmarks)
        if ok_confidence > 0.8:
            return {"name": "ok_sign", "confidence": ok_confidence}
            
        return None
    
    def _detect_finger_gun(self, landmarks: List[Tuple[float, float]]) -> float:
        """Detect finger gun gesture (index extended, others folded)"""
        # Check if index finger is extended
        index_tip = landmarks[8]    # INDEX_FINGER_TIP
        index_pip = landmarks[6]    # INDEX_FINGER_PIP
        
        # Check if middle, ring, pinky are folded
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        
        ring_tip = landmarks[16]
        ring_pip = landmarks[14]
        
        pinky_tip = landmarks[20]
        pinky_pip = landmarks[18]
        
        # Index extended: tip higher than pip
        index_extended = index_tip[1] < index_pip[1]
        
        # Other fingers folded: tips lower than pips
        middle_folded = middle_tip[1] > middle_pip[1]
        ring_folded = ring_tip[1] > ring_pip[1]
        pinky_folded = pinky_tip[1] > pinky_pip[1]
        
        if index_extended and middle_folded and ring_folded and pinky_folded:
            return 0.9
        return 0.3
    
    def _detect_rock_horn(self, landmarks: List[Tuple[float, float]]) -> float:
        """Detect rock horn gesture (index + pinky extended, middle + ring folded)"""
        index_tip = landmarks[8]
        index_pip = landmarks[6]
        pinky_tip = landmarks[20]
        pinky_pip = landmarks[18]
        
        middle_tip = landmarks[12]
        middle_pip = landmarks[10]
        ring_tip = landmarks[16]
        ring_pip = landmarks[14]
        
        index_extended = index_tip[1] < index_pip[1]
        pinky_extended = pinky_tip[1] < pinky_pip[1]
        middle_folded = middle_tip[1] > middle_pip[1]
        ring_folded = ring_tip[1] > ring_pip[1]
        
        if index_extended and pinky_extended and middle_folded and ring_folded:
            return 0.9
        return 0.3
    
    def _detect_ok_gesture(self, landmarks: List[Tuple[float, float]]) -> float:
        """Detect OK gesture (thumb + index forming circle)"""
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        
        # Calculate distance between thumb and index tips
        distance = np.sqrt((thumb_tip[0] - index_tip[0])**2 + (thumb_tip[1] - index_tip[1])**2)
        
        # Close distance indicates circle formation
        if distance < 0.05:  # Normalized coordinates
            return 0.9
        return 0.3
    
    def run_demo(self, duration_seconds: int = 30):
        """Run custom gesture detection demo"""
        print(f"🎯 Running custom gesture detection for {duration_seconds} seconds...")
        print("Try these custom gestures:")
        print("- 👉 Finger gun (index extended, others folded)")
        print("- 🤘 Rock horn (index + pinky extended)")
        print("- 👌 OK sign (thumb + index circle)")
        print()
        
        start_time = time.time()
        gesture_counts = {}
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            results = self.detect_custom_gestures(frame)
            
            for gesture in results["custom_gestures"]:
                gesture_type = gesture["custom_gesture"]
                gesture_counts[gesture_type] = gesture_counts.get(gesture_type, 0) + 1
                print(f"🎯 {gesture['handedness']} hand: {gesture_type} (confidence: {gesture['confidence']:.2f})")
                
            time.sleep(0.1)
            
        print(f"\n📊 Custom Gesture Summary:")
        for gesture, count in gesture_counts.items():
            print(f"   {gesture}: {count} detections")
            
    def cleanup(self):
        """Clean up resources"""
        self.camera.cleanup()


class GestureIntegrationExample:
    """
    Example 3: Gesture integration with webcam detection system
    
    Demonstrates how to integrate gesture recognition with the existing
    human detection pipeline for conditional gesture processing.
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.human_detector = create_detector('multimodal')
        self.hand_detector = HandDetector()
        self.gesture_classifier = GestureClassifier()
        self.event_publisher = EventPublisher()
        
    def initialize(self):
        """Initialize all detection components"""
        print("🚀 Initializing integrated gesture detection...")
        self.human_detector.initialize()
        self.hand_detector.initialize()
        self.gesture_classifier.initialize()
        print("✅ Ready for integrated detection")
        
    async def process_frame_with_gestures(self, frame: np.ndarray) -> Dict:
        """
        Process frame with human detection + conditional gesture detection
        
        This demonstrates the performance optimization pattern:
        1. Detect human presence first
        2. Only run gesture detection if human present
        3. Publish events for real-time integration
        """
        # Step 1: Human detection
        human_result = self.human_detector.detect(frame)
        
        result = {
            "human_present": human_result.human_present,
            "human_confidence": human_result.confidence,
            "gestures": [],
            "processing_time_ms": 0
        }
        
        # Step 2: Conditional gesture detection
        if human_result.human_present and human_result.confidence > 0.6:
            start_time = time.time()
            
            # Detect hands
            hand_results = self.hand_detector.detect_hands(frame)
            
            if hand_results.hands_detected:
                # Classify gestures
                for i, landmarks in enumerate(hand_results.hand_landmarks):
                    gesture_result = self.gesture_classifier.classify_gesture(landmarks)
                    
                    if gesture_result.confidence > 0.7:
                        gesture_data = {
                            "hand_index": i,
                            "gesture": gesture_result.gesture_type,
                            "confidence": gesture_result.confidence,
                            "handedness": hand_results.handedness[i] if i < len(hand_results.handedness) else "unknown"
                        }
                        result["gestures"].append(gesture_data)
                        
                        # Publish gesture event
                        await self._publish_gesture_event(gesture_data)
            
            result["processing_time_ms"] = int((time.time() - start_time) * 1000)
        
        return result
    
    async def _publish_gesture_event(self, gesture_data: Dict):
        """Publish gesture detection event"""
        event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                "gesture_type": gesture_data["gesture"],
                "confidence": gesture_data["confidence"],
                "hand": gesture_data["handedness"],
                "timestamp": datetime.now().isoformat()
            }
        )
        
        await self.event_publisher.publish_async(event)
        
    async def run_integrated_demo(self, duration_seconds: int = 30):
        """Run integrated detection demo"""
        print(f"🎯 Running integrated detection for {duration_seconds} seconds...")
        print("This demo shows performance optimization:")
        print("- Human detection runs continuously")
        print("- Gesture detection only when human present")
        print("- Events published for real-time integration")
        print()
        
        start_time = time.time()
        stats = {
            "frames_processed": 0,
            "human_detections": 0,
            "gesture_detections": 0,
            "avg_processing_time_ms": 0
        }
        
        processing_times = []
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            result = await self.process_frame_with_gestures(frame)
            
            # Update stats
            stats["frames_processed"] += 1
            if result["human_present"]:
                stats["human_detections"] += 1
                
            if result["gestures"]:
                stats["gesture_detections"] += len(result["gestures"])
                processing_times.append(result["processing_time_ms"])
                
                for gesture in result["gestures"]:
                    print(f"👤+🖐️ Human present + {gesture['gesture']} gesture "
                          f"(confidence: {gesture['confidence']:.2f}, "
                          f"processing: {result['processing_time_ms']}ms)")
            elif result["human_present"]:
                print(f"👤 Human present (no gestures, confidence: {result['human_confidence']:.2f})")
            else:
                print("🚫 No human detected")
                
            await asyncio.sleep(0.1)  # 10 FPS
            
        # Calculate average processing time
        if processing_times:
            stats["avg_processing_time_ms"] = sum(processing_times) / len(processing_times)
            
        print(f"\n📊 Integration Demo Summary:")
        print(f"   Frames processed: {stats['frames_processed']}")
        print(f"   Human detections: {stats['human_detections']}")
        print(f"   Gesture detections: {stats['gesture_detections']}")
        print(f"   Avg gesture processing time: {stats['avg_processing_time_ms']:.1f}ms")
        
    def cleanup(self):
        """Clean up resources"""
        self.camera.cleanup()
        self.human_detector.cleanup()


class VoiceAssistantGestureControl:
    """
    Example 4: Voice assistant gesture control
    
    Demonstrates how to use gesture detection for voice assistant control,
    particularly the "Open_Palm" gesture for pausing/stopping voice processing.
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.human_detector = create_detector('multimodal')
        self.hand_detector = HandDetector()
        self.gesture_classifier = GestureClassifier()
        self.voice_processing_active = False
        
    def initialize(self):
        """Initialize components"""
        print("🎙️ Initializing voice assistant gesture control...")
        self.human_detector.initialize()
        self.hand_detector.initialize()
        self.gesture_classifier.initialize()
        print("✅ Ready for voice gesture control")
        
    def should_process_voice(self, frame: np.ndarray) -> Tuple[bool, str]:
        """
        Guard clause for voice processing with gesture override
        
        Returns:
            (should_process, reason)
        """
        # Check human presence first
        human_result = self.human_detector.detect(frame)
        
        if not human_result.human_present:
            return False, "no_human_present"
            
        # Check for stop gesture
        hand_results = self.hand_detector.detect_hands(frame)
        
        if hand_results.hands_detected:
            for landmarks in hand_results.hand_landmarks:
                gesture_result = self.gesture_classifier.classify_gesture(landmarks)
                
                # Stop gesture detected
                if (gesture_result.gesture_type in ["Open_Palm", "Closed_Fist"] and 
                    gesture_result.confidence > 0.8):
                    return False, f"stop_gesture_{gesture_result.gesture_type}"
                    
        return True, "ok_to_process"
    
    def simulate_voice_assistant(self, duration_seconds: int = 30):
        """Simulate voice assistant with gesture control"""
        print(f"🎙️ Voice assistant simulation for {duration_seconds} seconds...")
        print("Voice processing states:")
        print("- ✅ Processing: Human present, no stop gesture")
        print("- 🛑 Stopped: Stop gesture detected (open palm or fist)")
        print("- 🚫 Paused: No human detected")
        print()
        
        start_time = time.time()
        states = {"processing": 0, "stopped": 0, "paused": 0}
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            should_process, reason = self.should_process_voice(frame)
            
            if should_process:
                state = "processing"
                status = "✅ PROCESSING VOICE"
                self.voice_processing_active = True
            elif reason == "no_human_present":
                state = "paused"
                status = "🚫 PAUSED (no human)"
                self.voice_processing_active = False
            else:
                state = "stopped" 
                status = f"🛑 STOPPED ({reason})"
                self.voice_processing_active = False
                
            states[state] += 1
            print(f"\r{status} | Active: {self.voice_processing_active}", end="", flush=True)
            
            time.sleep(0.2)  # 5 FPS for this demo
            
        print(f"\n\n📊 Voice Assistant Summary:")
        total = sum(states.values())
        for state, count in states.items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"   {state.capitalize()}: {count} frames ({percentage:.1f}%)")
            
    def cleanup(self):
        """Clean up resources"""
        self.camera.cleanup()
        self.human_detector.cleanup()


def main():
    """Run gesture recognition examples"""
    print("🖐️ Gesture Recognition Examples")
    print("="*50)
    
    examples = {
        "1": ("Basic MediaPipe Gestures", BasicGestureDetection),
        "2": ("Custom Gesture Recognition", CustomGestureDetection), 
        "3": ("Integrated Human + Gesture Detection", GestureIntegrationExample),
        "4": ("Voice Assistant Gesture Control", VoiceAssistantGestureControl)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}: {name}")
        
    choice = input("\nSelect example (1-4, or 'all'): ").strip()
    
    if choice.lower() == 'all':
        # Run all examples
        for key, (name, example_class) in examples.items():
            print(f"\n{'='*60}")
            print(f"Running Example {key}: {name}")
            print('='*60)
            
            example = example_class()
            try:
                example.initialize()
                if hasattr(example, 'run_integrated_demo'):
                    asyncio.run(example.run_integrated_demo(10))
                elif hasattr(example, 'simulate_voice_assistant'):
                    example.simulate_voice_assistant(10)
                else:
                    example.run_demo(10)
            except KeyboardInterrupt:
                print("\n⏹️ Example interrupted")
            finally:
                example.cleanup()
                
    elif choice in examples:
        name, example_class = examples[choice]
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)
        
        example = example_class()
        try:
            example.initialize()
            duration = int(input("Duration in seconds (default 30): ") or "30")
            
            if hasattr(example, 'run_integrated_demo'):
                asyncio.run(example.run_integrated_demo(duration))
            elif hasattr(example, 'simulate_voice_assistant'):
                example.simulate_voice_assistant(duration)
            else:
                example.run_demo(duration)
                
        except KeyboardInterrupt:
            print("\n⏹️ Demo interrupted")
        finally:
            example.cleanup()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    import os
    main() 