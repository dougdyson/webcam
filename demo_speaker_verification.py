#!/usr/bin/env python3
"""
Speaker Verification + Webcam Detection Integration Demo
========================================================

This demonstrates how to integrate webcam-detection package
as a guard clause in speaker verification systems.

Integration Pattern:
1. Initialize webcam detection system
2. Check for human presence before processing audio
3. Only run speaker verification when humans are detected
4. Skip processing when no one is present (save resources)
"""

import random
import time
from typing import Optional, Tuple
from webcam_detection import create_detector
from webcam_detection.camera import CameraManager
from webcam_detection.camera.config import CameraConfig

class SpeakerVerificationSystem:
    """Mock speaker verification system for demonstration."""
    
    def __init__(self):
        # Initialize webcam detection
        self.camera_manager = CameraManager(CameraConfig())
        self.human_detector = create_detector('multimodal')
        self.human_detector.initialize()
        
        # Mock audio processor
        self.known_speakers = ["user123", "admin456", "guest789"]
        self.verification_threshold = 0.8
    
    def is_human_present(self) -> Tuple[bool, float]:
        """
        Guard clause: Check if human is present before processing audio.
        
        Returns:
            Tuple of (human_present, confidence)
        """
        try:
            frame = self.camera_manager.get_frame()
            if frame is not None:
                result = self.human_detector.detect(frame)
                return result.human_present, result.confidence
            return False, 0.0
        except Exception as e:
            print(f"   ⚠️  Detection failed: {e}")
            return True, 1.0  # Fail safe: assume human present
    
    def process_audio_frame(self, audio_data: str) -> Optional[dict]:
        """
        Process an audio frame with human presence guard clause.
        
        Args:
            audio_data: Mock audio data
            
        Returns:
            Processing result or None if skipped
        """
        # Guard clause: Check human presence first
        human_present, confidence = self.is_human_present()
        
        if human_present and confidence > 0.6:
            print("   ✅ Human detected - processing audio")
            return self._process_audio_internal(audio_data)
        else:
            print("   ⏭️  No human - skipping audio processing")
            return None
    
    def _process_audio_internal(self, audio_data: str) -> dict:
        """Internal audio processing (mock implementation)."""
        print("   🎤 Processing audio...")
        
        # Simulate processing time
        time.sleep(0.1)
        
        # Mock transcription and speaker verification
        speaker_id = random.choice(self.known_speakers)
        confidence = random.uniform(0.6, 0.95)
        
        verified = confidence >= self.verification_threshold
        
        if verified:
            print(f"   🎉 Speaker verified: {speaker_id} ({confidence:.2f})")
        else:
            print(f"   ❌ Speaker not verified: {confidence:.2f} too low")
        
        return {
            "speaker_id": speaker_id if verified else None,
            "confidence": confidence,
            "verified": verified,
            "processed": True
        }
    
    def cleanup(self):
        """Clean up resources."""
        self.human_detector.cleanup()
        self.camera_manager.cleanup()

def main():
    """Run the integration demo."""
    print("=" * 60)
    print("🎯 SPEAKER VERIFICATION + WEBCAM DETECTION DEMO")
    print("=" * 60)
    print()
    print("This demo shows how to integrate webcam-detection package")
    print("as a guard clause in speaker verification systems.")
    print()
    
    print("🎯 Initializing Speaker Verification System...")
    system = SpeakerVerificationSystem()
    print("📷 Setting up webcam detection...")
    print("✅ Detection system ready!")
    print()
    
    try:
        print("🔄 Starting audio processing pipeline...")
        print()
        
        # Simulate processing 5 audio frames
        for i in range(1, 6):
            print(f"📊 Audio Frame {i}:")
            
            # Mock audio data
            audio_data = f"mock_audio_frame_{i}"
            
            # Process with guard clause
            result = system.process_audio_frame(audio_data)
            
            if result:
                # Audio was processed
                pass
            else:
                # Audio was skipped due to no human presence
                pass
            
            print()
            time.sleep(0.5)  # Brief pause between frames
    
    finally:
        print("🧹 Cleaning up...")
        system.cleanup()
        print("✅ Cleanup complete!")
    
    print()
    print("=" * 60)
    print("✅ Demo complete! Package integration successful!")
    print("=" * 60)

if __name__ == "__main__":
    main() 