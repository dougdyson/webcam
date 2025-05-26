#!/usr/bin/env python3
"""
Gesture Recognition Performance Test

Quick test to measure gesture detection performance and compare
with/without optimizations.
"""

import time
import cv2
import logging
import numpy as np
import sys
import os
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.camera import CameraManager
from src.camera.config import CameraConfig
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
from src.processing.enhanced_frame_processor import EnhancedFrameProcessor, EnhancedProcessorConfig
from src.service.events import EventPublisher

# Setup logging
logging.basicConfig(level=logging.WARNING)  # Reduce log noise


class PerformanceTester:
    """Test gesture recognition performance."""
    
    def __init__(self):
        self.camera = None
        self.human_detector = None
        self.gesture_detector = None
        self.event_publisher = None
        self.frame_processor = None
    
    def setup(self):
        """Initialize components."""
        print("🔧 Setting up performance test...")
        
        # Initialize camera
        self.camera = CameraManager(CameraConfig())
        
        # Initialize human detector (multimodal for best results)
        self.human_detector = create_detector('multimodal')
        self.human_detector.initialize()
        
        # Initialize gesture detector with optimized settings
        self.gesture_detector = GestureDetector()
        self.gesture_detector.initialize()
        
        # Initialize event publisher (lightweight)
        self.event_publisher = EventPublisher()
        
        # Initialize enhanced frame processor with performance optimizations
        config = EnhancedProcessorConfig(
            min_human_confidence_for_gesture=0.5,  # Lower threshold for easier detection
            min_gesture_confidence_threshold=0.6,  # Lower threshold
            gesture_detection_every_n_frames=2,    # Skip every other frame
            max_gesture_fps=10.0,                  # Max 10 FPS gesture detection
            enable_gesture_detection=True,
            publish_gesture_events=False  # Don't publish during test
        )
        
        self.frame_processor = EnhancedFrameProcessor(
            detector=self.human_detector,
            gesture_detector=self.gesture_detector,
            event_publisher=self.event_publisher,
            config=config
        )
        
        print("✅ Setup complete!")
    
    def cleanup(self):
        """Clean up resources."""
        if self.gesture_detector:
            self.gesture_detector.cleanup()
        if self.human_detector:
            self.human_detector.cleanup()
        if self.camera:
            self.camera.cleanup()
    
    def run_performance_test(self, duration_seconds: int = 30):
        """
        Run performance test for specified duration.
        
        Args:
            duration_seconds: How long to run the test
        """
        print(f"🚀 Running performance test for {duration_seconds} seconds...")
        print("📋 Metrics being measured:")
        print("   - Overall FPS (frames processed per second)")
        print("   - Gesture detection rate (gestures processed per second)")
        print("   - Human detection accuracy")
        print("   - Average processing time per frame")
        print()
        
        start_time = time.time()
        frame_count = 0
        gesture_detection_count = 0
        human_present_count = 0
        total_processing_time = 0.0
        
        processing_times: List[float] = []
        
        try:
            while time.time() - start_time < duration_seconds:
                frame_start = time.time()
                
                # Get frame
                frame = self.camera.get_frame()
                if frame is not None:
                    # Process frame through enhanced processor
                    result = self.frame_processor.process_frame(frame)
                    
                    frame_count += 1
                    if result.human_present:
                        human_present_count += 1
                    
                    # Check if gesture detection ran (look at performance stats)
                    stats = self.frame_processor.get_performance_stats()
                    if stats["gesture_detection_runs"] > gesture_detection_count:
                        gesture_detection_count = stats["gesture_detection_runs"]
                    
                    # Measure processing time
                    frame_end = time.time()
                    frame_processing_time = frame_end - frame_start
                    processing_times.append(frame_processing_time)
                    total_processing_time += frame_processing_time
                
                # Small sleep to prevent overwhelming the system
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n⏹️ Test stopped by user")
        
        # Calculate results
        actual_duration = time.time() - start_time
        overall_fps = frame_count / actual_duration if actual_duration > 0 else 0
        gesture_fps = gesture_detection_count / actual_duration if actual_duration > 0 else 0
        avg_processing_time = total_processing_time / frame_count if frame_count > 0 else 0
        human_detection_rate = human_present_count / frame_count if frame_count > 0 else 0
        
        # Display results
        print(f"\n📊 Performance Test Results ({actual_duration:.1f}s)")
        print("=" * 50)
        print(f"🎬 Total frames processed: {frame_count}")
        print(f"⚡ Overall FPS: {overall_fps:.1f}")
        print(f"🖐️ Gesture detections: {gesture_detection_count}")
        print(f"🖐️ Gesture detection FPS: {gesture_fps:.1f}")
        print(f"👤 Human present rate: {human_detection_rate:.1%}")
        print(f"⏱️ Avg processing time: {avg_processing_time*1000:.1f}ms per frame")
        
        # Performance stats from frame processor
        stats = self.frame_processor.get_performance_stats()
        if stats:
            print(f"\n🔍 Detailed Stats:")
            print(f"   Gesture detection runs: {stats['gesture_detection_runs']}")
            print(f"   Gesture detection skipped: {stats['gesture_detection_skipped']}")
            print(f"   Gesture events published: {stats['gesture_events_published']}")
            print(f"   Errors handled: {stats['errors_handled']}")
        
        # Performance efficiency
        efficiency = self.frame_processor.get_efficiency_metrics()
        if efficiency and isinstance(efficiency, dict):
            print(f"\n⚡ Efficiency Metrics:")
            if 'gesture_detection_efficiency' in efficiency:
                print(f"   Gesture detection efficiency: {efficiency['gesture_detection_efficiency']:.1%}")
            if 'performance_optimization' in efficiency:
                print(f"   Performance optimization: {efficiency['performance_optimization']:.1%}")
            if 'gesture_detection_run_rate' in efficiency:
                print(f"   Gesture run rate: {efficiency['gesture_detection_run_rate']:.1%}")
            if 'gesture_detection_skip_rate' in efficiency:
                print(f"   Gesture skip rate: {efficiency['gesture_detection_skip_rate']:.1%}")
        
        # Performance assessment
        print(f"\n🎯 Performance Assessment:")
        if overall_fps >= 15:
            print("✅ Excellent overall FPS for real-time use")
        elif overall_fps >= 10:
            print("🟡 Good FPS, acceptable for most use cases")
        else:
            print("🔴 Low FPS, consider further optimization")
        
        if gesture_fps >= 5:
            print("✅ Excellent gesture detection rate")
        elif gesture_fps >= 3:
            print("🟡 Adequate gesture detection rate")
        else:
            print("🔴 Low gesture detection rate")
        
        if avg_processing_time < 0.05:  # 50ms
            print("✅ Excellent processing time per frame")
        elif avg_processing_time < 0.1:  # 100ms
            print("🟡 Good processing time per frame")
        else:
            print("🔴 High processing time, optimization needed")


def main():
    """Run the performance test."""
    print("🎯 Gesture Recognition Performance Test")
    print("=" * 45)
    print("This test measures the performance of the optimized")
    print("gesture recognition system with the latest improvements.")
    print()
    
    tester = PerformanceTester()
    
    try:
        tester.setup()
        
        # Ask user for test duration
        try:
            duration = int(input("Enter test duration in seconds (default 30): ") or "30")
        except ValueError:
            duration = 30
        
        print(f"\n🏃 Starting {duration}-second performance test...")
        print("👋 Wave your hand to test gesture detection!")
        print("⏹️ Press Ctrl+C to stop early")
        print()
        
        tester.run_performance_test(duration)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        tester.cleanup()
        print("\n🧹 Cleanup complete. Test finished!")


if __name__ == "__main__":
    main() 