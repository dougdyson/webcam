#!/usr/bin/env python3
"""
Simple Ollama Integration Demo

This script demonstrates the core Ollama integration functionality:
1. Capture frames from webcam
2. Detect human presence 
3. Take snapshots when humans detected
4. Generate AI descriptions using local Ollama
5. Display results in real-time

Prerequisites:
- Ollama service running locally (ollama serve)
- Vision model available (ollama pull llama3.2-vision)
- Webcam connected

Usage:
    conda activate webcam
    python examples/ollama_demo.py
"""
import asyncio
import cv2
import numpy as np
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from camera.manager import CameraManager
from camera.config import CameraConfig
from detection import create_detector
from detection.result import DetectionResult
from ollama.client import OllamaClient, OllamaConfig
from ollama.description_service import DescriptionService, DescriptionServiceConfig
from ollama.snapshot_buffer import SnapshotBuffer, SnapshotMetadata, Snapshot
from ollama.image_processing import OllamaImageProcessor, ImageProcessingConfig


class OllamaDemo:
    """Simple demo of Ollama integration with webcam detection."""
    
    def __init__(self):
        """Initialize demo components."""
        print("🎬 Initializing Ollama Demo...")
        
        # Camera setup
        self.camera = CameraManager(CameraConfig())
        
        # Detector setup (multimodal for best results)
        self.detector = create_detector('multimodal')
        self.detector.initialize()
        
        # Ollama setup
        ollama_config = OllamaConfig(
            base_url="http://localhost:11434",
            model="gemma3:4b-it-q4_K_M",  # Instruction-tuned 4B model - good balance of speed/quality
            timeout=30.0
        )
        self.ollama_client = OllamaClient(config=ollama_config)
        
        # Image processor setup
        image_config = ImageProcessingConfig()
        self.image_processor = OllamaImageProcessor(config=image_config)
        
        # Description service setup
        desc_config = DescriptionServiceConfig(
            cache_ttl_seconds=300,  # 5 minute cache
            max_concurrent_requests=1,  # Keep it simple for demo
        )
        self.description_service = DescriptionService(
            ollama_client=self.ollama_client,
            image_processor=self.image_processor,
            config=desc_config
        )
        
        # Snapshot buffer setup
        self.snapshot_buffer = SnapshotBuffer(max_size=10)  # Small buffer for demo
        
        # State tracking
        self.frame_count = 0
        self.human_detected_count = 0
        self.descriptions_generated = 0
        self.last_description = None
        self.last_description_time = None
        
        print("✅ Demo initialized successfully!")
    
    async def check_ollama_service(self):
        """Check if Ollama service is available."""
        print("🔍 Checking Ollama service...")
        try:
            is_available = self.ollama_client.is_available()
            if is_available:
                print("✅ Ollama service is running and accessible")
                return True
            else:
                print("❌ Ollama service is not available")
                print("   Please start Ollama: ollama serve")
                return False
        except Exception as e:
            print(f"❌ Error checking Ollama service: {e}")
            print("   Please ensure Ollama is installed and running")
            return False
    
    def process_frame(self, frame):
        """Process a single frame for human detection."""
        # Run detection
        detection_result = self.detector.detect(frame)
        self.frame_count += 1
        
        # Track human detection
        if detection_result.human_present:
            self.human_detected_count += 1
            
            # Create snapshot with metadata
            metadata = SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=detection_result.confidence,
                human_present=True,
                detection_source="multimodal"
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            
            # Add to snapshot buffer
            added = self.snapshot_buffer.add_snapshot(snapshot)
            
            # Return detection info
            return {
                'human_present': True,
                'confidence': detection_result.confidence,
                'new_snapshot': added
            }
        
        return {
            'human_present': False,
            'confidence': detection_result.confidence,
            'new_snapshot': False
        }
    
    async def generate_description_if_needed(self):
        """Generate description if we have new snapshots and haven't done one recently."""
        # Get latest snapshot
        latest_snapshot = self.snapshot_buffer.get_latest()
        
        if latest_snapshot is None:
            return None
        
        # Avoid generating descriptions too frequently (max every 10 seconds)
        if (self.last_description_time and 
            (datetime.now() - self.last_description_time).total_seconds() < 10):
            return None
        
        try:
            print("🎨 Generating description with Ollama...")
            start_time = datetime.now()
            
            # Generate description
            result = await self.description_service.describe_snapshot(latest_snapshot)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if result.error is None:
                print(f"✨ Description generated in {processing_time:.1f}s:")
                print(f"   📝 {result.description}")
                print(f"   🎯 Confidence: {result.confidence:.2f}")
                print(f"   💾 Cached: {'Yes' if result.cached else 'No'}")
                
                self.descriptions_generated += 1
                self.last_description = result.description
                self.last_description_time = datetime.now()
                return result
            else:
                print(f"⚠️  Description failed: {result.error}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating description: {e}")
            return None
    
    def display_status(self, detection_info):
        """Display current status in a clean format."""
        human_status = "👤 HUMAN DETECTED" if detection_info['human_present'] else "🚫 No human"
        confidence = f"({detection_info['confidence']:.2f})"
        snapshot_status = "📸 New snapshot!" if detection_info['new_snapshot'] else ""
        
        # Create status line
        status_parts = [
            f"Frame {self.frame_count:4d}",
            f"{human_status} {confidence}",
            f"Humans: {self.human_detected_count}",
            f"Descriptions: {self.descriptions_generated}"
        ]
        
        if snapshot_status:
            status_parts.append(snapshot_status)
        
        if self.last_description:
            # Show last description (truncated)
            desc_preview = self.last_description[:50] + "..." if len(self.last_description) > 50 else self.last_description
            status_parts.append(f"Last: {desc_preview}")
        
        status_line = " | ".join(status_parts)
        
        # Print with carriage return to overwrite previous line
        print(f"\r{status_line:<120}", end="", flush=True)
    
    async def run_demo(self):
        """Run the main demo loop."""
        print("\n🎯 Starting Ollama Demo!")
        print("Press 'q' to quit, 's' to take snapshot manually, 'd' to force description")
        print("Make sure you're visible in the webcam for automatic detection\n")
        
        # Check Ollama first
        if not await self.check_ollama_service():
            return False
        
        frame_skip = 0
        
        try:
            while True:
                # Get frame
                frame = self.camera.get_frame()
                if frame is None:
                    print("❌ Failed to get camera frame")
                    break
                
                # Process every 3rd frame for performance
                frame_skip += 1
                if frame_skip % 3 == 0:
                    detection_info = self.process_frame(frame)
                    self.display_status(detection_info)
                    
                    # Try to generate description periodically
                    if detection_info['human_present'] and frame_skip % 30 == 0:  # Every 10 frames when human present
                        await self.generate_description_if_needed()
                
                # Show video feed (optional - comment out if not needed)
                display_frame = cv2.resize(frame, (640, 480))
                cv2.putText(display_frame, f"Humans detected: {self.human_detected_count}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(display_frame, f"Descriptions: {self.descriptions_generated}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('Ollama Demo - Webcam Feed', display_frame)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("\n👋 Exiting demo...")
                    break
                elif key == ord('s'):
                    # Manual snapshot
                    detection_result = self.detector.detect(frame)
                    self.snapshot_buffer.add_frame_if_human_detected(frame, detection_result)
                    print("\n📸 Manual snapshot taken!")
                elif key == ord('d'):
                    # Force description
                    print("\n🎨 Forcing description generation...")
                    await self.generate_description_if_needed()
                
                # Small delay
                await asyncio.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n👋 Interrupted by user")
        
        finally:
            # Cleanup
            cv2.destroyAllWindows()
            self.camera.cleanup()
            self.detector.cleanup()
            print("\n✅ Demo completed successfully!")
            return True
    
    def print_final_stats(self):
        """Print final statistics."""
        print(f"\n📊 Final Statistics:")
        print(f"   Frames processed: {self.frame_count}")
        print(f"   Human detections: {self.human_detected_count}")
        print(f"   Descriptions generated: {self.descriptions_generated}")
        print(f"   Snapshots in buffer: {self.snapshot_buffer.current_size}")
        
        # Cache stats
        cache_stats = self.description_service.get_cache_statistics()
        print(f"   Cache hits: {cache_stats.get('cache_hits', 0)}")
        print(f"   Cache misses: {cache_stats.get('cache_misses', 0)}")


async def main():
    """Main demo function."""
    print("🎬 Ollama Integration Demo")
    print("=" * 50)
    
    demo = OllamaDemo()
    
    try:
        success = await demo.run_demo()
        demo.print_final_stats()
        
        if success:
            print("\n🎉 Demo completed successfully!")
            print("\nNext steps:")
            print("  • Run full test suite: pytest tests/test_ollama/")
            print("  • Continue to Phase 4: HTTP API integration")
        else:
            print("\n⚠️  Demo encountered issues")
            print("Please check Ollama service and model availability")
    
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 