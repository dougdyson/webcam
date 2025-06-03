#!/usr/bin/env python3
"""
Snapshot Feature Usage Example

This example demonstrates how to use the snapshot system to capture and manage
webcam frames when humans are detected. The snapshot feature is particularly
useful for:

1. Storing frames for AI description processing
2. Creating a buffer of recent human detection events
3. Time-based retrieval of detection events
4. Efficient memory management with circular buffers

Key Components:
- SnapshotBuffer: Circular buffer for storing snapshots
- SnapshotTrigger: Intelligent triggering based on detection events  
- Snapshot & SnapshotMetadata: Data structures for frame + metadata
"""

import asyncio
import time
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List

# Core detection imports
from src.camera.manager import CameraManager
from src.camera.config import CameraConfig
from src.detection import create_detector, DetectorConfig
from src.detection.result import DetectionResult

# Snapshot system imports
from src.ollama.snapshot_buffer import SnapshotBuffer, Snapshot, SnapshotMetadata
from src.ollama.snapshot_trigger import SnapshotTrigger, SnapshotTriggerConfig

# Optional: For AI descriptions
try:
    from src.ollama.description_service import DescriptionService
    from src.ollama.client import OllamaClient, OllamaConfig
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Note: Ollama not available - descriptions disabled")


class SnapshotExample:
    """Complete example of using the snapshot system."""
    
    def __init__(self):
        """Initialize camera, detector, and snapshot system."""
        # Setup camera and detection
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal', DetectorConfig())
        
        # Setup snapshot system
        self.snapshot_buffer = SnapshotBuffer(max_size=20)
        self.snapshot_trigger = SnapshotTrigger(
            SnapshotTriggerConfig(
                min_confidence_threshold=0.7,
                debounce_frames=3,  # Prevent rapid triggering
                buffer_max_size=20
            )
        )
        
        # Optional: Setup AI descriptions
        self.description_service = None
        if OLLAMA_AVAILABLE:
            try:
                ollama_client = OllamaClient(OllamaConfig())
                self.description_service = DescriptionService(ollama_client)
                print("✅ Ollama integration enabled")
            except Exception as e:
                print(f"⚠️ Ollama not available: {e}")
        
        # Statistics
        self.frames_processed = 0
        self.snapshots_captured = 0
        self.descriptions_generated = 0
        
        print("📸 Snapshot Example initialized!")
        print("🎯 Detection confidence threshold: 0.7")
        print(f"💾 Buffer size: {self.snapshot_buffer.max_size} snapshots")
    
    def initialize(self):
        """Initialize all components."""
        print("🔧 Initializing components...")
        self.detector.initialize()
        print("✅ All components ready!")
    
    def cleanup(self):
        """Clean up all components."""
        self.camera.cleanup()
        self.detector.cleanup()
        print("🧹 Cleanup complete!")
    
    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Process a single frame and potentially capture snapshot.
        
        Args:
            frame: Camera frame to process
            
        Returns:
            Dictionary with processing results
        """
        self.frames_processed += 1
        
        # Run human detection
        detection_result = self.detector.detect(frame)
        
        # Process with snapshot trigger
        snapshot_captured = self.snapshot_trigger.process_detection(frame, detection_result)
        
        if snapshot_captured:
            self.snapshots_captured += 1
            print(f"📸 Snapshot captured! (confidence: {detection_result.confidence:.2f})")
        
        return {
            'frame_number': self.frames_processed,
            'human_detected': detection_result.human_present,
            'confidence': detection_result.confidence,
            'snapshot_captured': snapshot_captured,
            'buffer_size': self.snapshot_trigger.buffer.current_size
        }
    
    def get_latest_snapshot(self) -> Optional[Snapshot]:
        """Get the most recent snapshot."""
        return self.snapshot_trigger.get_latest_snapshot()
    
    def get_recent_snapshots(self, seconds: int = 30) -> List[Snapshot]:
        """
        Get snapshots from the last N seconds.
        
        Args:
            seconds: Time window to search
            
        Returns:
            List of snapshots within the time window
        """
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        return self.snapshot_trigger.buffer.get_snapshots_since(cutoff_time)
    
    def get_buffer_statistics(self) -> dict:
        """Get snapshot buffer statistics."""
        buffer_stats = self.snapshot_trigger.buffer.get_statistics()
        trigger_stats = {
            'total_processed': self.frames_processed,
            'snapshots_captured': self.snapshots_captured,
            'capture_rate': (self.snapshots_captured / max(1, self.frames_processed)) * 100
        }
        
        return {**buffer_stats, **trigger_stats}
    
    async def generate_description(self, snapshot: Optional[Snapshot] = None) -> Optional[str]:
        """
        Generate AI description for a snapshot.
        
        Args:
            snapshot: Snapshot to describe (uses latest if None)
            
        Returns:
            Description string or None if failed
        """
        if not self.description_service:
            print("⚠️ Description service not available")
            return None
        
        if snapshot is None:
            snapshot = self.get_latest_snapshot()
        
        if snapshot is None:
            print("❌ No snapshot available for description")
            return None
        
        try:
            print("🎨 Generating AI description...")
            start_time = time.time()
            
            result = await self.description_service.describe_snapshot(snapshot)
            
            processing_time = time.time() - start_time
            
            if result.error is None:
                self.descriptions_generated += 1
                print(f"✨ Description: {result.description}")
                print(f"🎯 Confidence: {result.confidence:.2f}")
                print(f"⏱️ Generated in {processing_time:.1f}s")
                print(f"💾 Cached: {'Yes' if result.cached else 'No'}")
                return result.description
            else:
                print(f"❌ Description failed: {result.error}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating description: {e}")
            return None
    
    async def run_continuous_mode(self, duration: int = 60):
        """
        Run continuous snapshot capture for specified duration.
        
        Args:
            duration: Duration in seconds to run
        """
        print(f"🎬 Starting continuous capture for {duration} seconds...")
        print("👤 Move in front of camera to trigger snapshots")
        print("📸 Snapshots will be captured when humans detected")
        
        start_time = time.time()
        last_stats_time = start_time
        
        try:
            while (time.time() - start_time) < duration:
                # Get frame from camera
                frame = self.camera.get_frame()
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process frame for snapshots
                result = self.process_frame(frame)
                
                # Print stats every 10 seconds
                current_time = time.time()
                if current_time - last_stats_time >= 10:
                    self.print_current_stats()
                    last_stats_time = current_time
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n⏹️ Stopped by user")
        
        print("\n📊 Final statistics:")
        self.print_current_stats()
    
    def print_current_stats(self):
        """Print current snapshot statistics."""
        stats = self.get_buffer_statistics()
        
        print(f"\n📊 Current Stats:")
        print(f"   Frames processed: {stats['total_processed']}")
        print(f"   Snapshots captured: {stats['snapshots_captured']}")
        print(f"   Buffer utilization: {stats['utilization_percent']:.1f}%")
        print(f"   Capture rate: {stats['capture_rate']:.1f}%")
        
        if stats['current_size'] > 0:
            oldest = stats.get('oldest_timestamp')
            newest = stats.get('newest_timestamp')
            if oldest and newest:
                time_span = (newest - oldest).total_seconds()
                print(f"   Time span: {time_span:.1f} seconds")
    
    async def run_interactive_mode(self):
        """
        Run interactive mode with manual controls.
        """
        print("\n🎮 Interactive Snapshot Mode")
        print("Commands:")
        print("  SPACE - Capture manual snapshot")
        print("  d - Generate description for latest snapshot")
        print("  s - Show buffer statistics")
        print("  r - Show recent snapshots (last 30s)")
        print("  c - Clear buffer")
        print("  q - Quit")
        print("\nPress keys while this window is active...")
        
        # Note: In a real implementation, you'd use cv2.waitKey() or similar
        # For this example, we'll simulate with input()
        while True:
            try:
                # Get frame and process
                frame = self.camera.get_frame()
                if frame is not None:
                    self.process_frame(frame)
                
                # Simulate key input (in real app, use cv2.waitKey())
                print("\nEnter command (space/d/s/r/c/q): ", end="")
                command = input().strip().lower()
                
                if command == 'q':
                    break
                elif command == 'space' or command == ' ':
                    # Manual snapshot
                    if frame is not None:
                        detection_result = self.detector.detect(frame)
                        metadata = SnapshotMetadata(
                            timestamp=datetime.now(),
                            confidence=detection_result.confidence,
                            human_present=detection_result.human_present,
                            detection_source="manual"
                        )
                        snapshot = Snapshot(frame=frame, metadata=metadata)
                        self.snapshot_trigger.buffer.add_snapshot(snapshot)
                        print("📸 Manual snapshot captured!")
                elif command == 'd':
                    # Generate description
                    description = await self.generate_description()
                    if description:
                        print(f"📝 Description: {description}")
                elif command == 's':
                    # Show statistics
                    self.print_current_stats()
                elif command == 'r':
                    # Show recent snapshots
                    recent = self.get_recent_snapshots(30)
                    print(f"\n📅 Recent snapshots (last 30s): {len(recent)}")
                    for i, snapshot in enumerate(recent[-5:]):  # Show last 5
                        ts = snapshot.metadata.timestamp.strftime("%H:%M:%S")
                        conf = snapshot.metadata.confidence
                        print(f"   {i+1}. {ts} - confidence: {conf:.2f}")
                elif command == 'c':
                    # Clear buffer
                    self.snapshot_trigger.buffer = SnapshotBuffer(max_size=20)
                    print("🗑️ Buffer cleared!")
                
                await asyncio.sleep(0.1)
                
            except KeyboardInterrupt:
                break
        
        print("\n👋 Interactive mode ended")


# Example usage functions
async def basic_snapshot_example():
    """Basic example of snapshot usage."""
    print("=== Basic Snapshot Example ===")
    
    example = SnapshotExample()
    example.initialize()
    
    try:
        # Process a few frames
        for i in range(10):
            frame = example.camera.get_frame()
            if frame is not None:
                result = example.process_frame(frame)
                print(f"Frame {i+1}: Human={result['human_detected']}, "
                      f"Confidence={result['confidence']:.2f}, "
                      f"Captured={result['snapshot_captured']}")
                
                # If we captured a snapshot, try to describe it
                if result['snapshot_captured'] and example.description_service:
                    await example.generate_description()
                
                await asyncio.sleep(0.5)
        
        # Show final stats
        example.print_current_stats()
        
    finally:
        example.cleanup()


async def advanced_snapshot_example():
    """Advanced example with custom snapshot handling."""
    print("=== Advanced Snapshot Example ===")
    
    example = SnapshotExample()
    example.initialize()
    
    try:
        # Run for 30 seconds capturing snapshots
        await example.run_continuous_mode(30)
        
        # Get recent snapshots
        recent_snapshots = example.get_recent_snapshots(60)
        print(f"\n📊 Captured {len(recent_snapshots)} snapshots in the last minute")
        
        # Generate descriptions for the best snapshots
        if example.description_service and recent_snapshots:
            print("\n🎨 Generating descriptions for high-confidence snapshots...")
            
            # Sort by confidence and take top 3
            best_snapshots = sorted(recent_snapshots, 
                                  key=lambda s: s.metadata.confidence, 
                                  reverse=True)[:3]
            
            for i, snapshot in enumerate(best_snapshots):
                print(f"\n📸 Snapshot {i+1} (confidence: {snapshot.metadata.confidence:.2f}):")
                description = await example.generate_description(snapshot)
                if description:
                    print(f"   📝 {description}")
        
    finally:
        example.cleanup()


async def main():
    """Main function to run snapshot examples."""
    print("📸 Webcam Snapshot Feature Examples")
    print("===================================")
    
    # Check if camera is available
    try:
        camera_test = CameraManager(CameraConfig())
        frame = camera_test.get_frame()
        camera_test.cleanup()
        
        if frame is None:
            print("❌ Camera not available - cannot run examples")
            return
            
    except Exception as e:
        print(f"❌ Camera initialization failed: {e}")
        return
    
    print("\nSelect example to run:")
    print("1. Basic snapshot capture")
    print("2. Advanced snapshot with descriptions")
    print("3. Interactive mode")
    print("4. Continuous capture mode")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        await basic_snapshot_example()
    elif choice == "2":
        await advanced_snapshot_example()
    elif choice == "3":
        example = SnapshotExample()
        example.initialize()
        try:
            await example.run_interactive_mode()
        finally:
            example.cleanup()
    elif choice == "4":
        duration = int(input("Duration in seconds (default 60): ") or "60")
        example = SnapshotExample()
        example.initialize()
        try:
            await example.run_continuous_mode(duration)
        finally:
            example.cleanup()
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    asyncio.run(main()) 