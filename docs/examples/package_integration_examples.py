"""
Package Integration Examples for webcam-detection
================================================

This file demonstrates how to integrate the webcam-detection package
into other Python projects after installing via pip.

Installation:
    pip install webcam-detection[service]  # With service layer
    pip install webcam-detection           # Core detection only

Use Cases:
1. Speaker verification guard clauses
2. Home automation presence detection
3. Security system integration
4. Real-time monitoring dashboards
5. Multi-modal authentication systems
"""

import asyncio
import time
import requests
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import cv2

# ============================================================================
# Example 1: Simple Detection Integration
# ============================================================================

def example_basic_detection():
    """Basic detection example with proper frame handling."""
    from webcam_detection import create_detector
    
    # Create detector
    detector = create_detector('multimodal')
    
    try:
        # Initialize detector
        detector.initialize()
        
        # Get camera frame
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        
        if ret:
            # Perform detection with current API
            result = detector.detect(frame)
            
            print(f"Human present: {result.human_present}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Detection type: multimodal")
            
            # Access detailed information
            if result.landmarks:
                pose_landmarks = result.landmarks.get('pose', [])
                face_landmarks = result.landmarks.get('face', [])
                print(f"Pose landmarks: {len(pose_landmarks)}")
                print(f"Face landmarks: {len(face_landmarks)}")
        else:
            print("No camera frame available")
            
        cap.release()
            
    finally:
        # Clean up resources
        detector.cleanup()


# ============================================================================
# Example 2: Speaker Verification Guard Clause
# ============================================================================

class SpeakerVerificationGuard:
    """Guard clause integration for speaker verification systems."""
    
    def __init__(self, 
                 presence_service_url: str = "http://localhost:8767",
                 confidence_threshold: float = 0.5,
                 timeout: float = 1.0,
                 fail_safe: bool = True):
        self.presence_service_url = presence_service_url
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        self.fail_safe = fail_safe
        
    def should_process_audio(self) -> bool:
        """
        Check if human is present before processing audio.
        
        Returns:
            bool: True if should process audio, False otherwise
        """
        try:
            response = requests.get(
                f"{self.presence_service_url}/presence/simple",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                human_present = data.get("human_present", False)
                confidence = data.get("confidence", 0.0)
                
                # Apply confidence threshold
                return human_present and confidence >= self.confidence_threshold
                
        except requests.RequestException as e:
            print(f"Presence check failed: {e}")
            # Fail safe: allow processing if service unavailable
            return self.fail_safe
            
        return self.fail_safe
    
    def get_presence_details(self) -> Optional[Dict[str, Any]]:
        """Get detailed presence information."""
        try:
            response = requests.get(
                f"{self.presence_service_url}/presence",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
                
        except requests.RequestException:
            pass
            
        return None


def example_speaker_verification_integration():
    """Example of speaker verification system integration."""
    
    # Initialize guard clause
    guard = SpeakerVerificationGuard(
        confidence_threshold=0.7,  # Higher threshold for security
        fail_safe=True  # Allow processing if service down
    )
    
    # Simulate audio processing pipeline
    def process_audio_stream():
        """Simulate audio processing with presence guard."""
        
        # Check presence before processing
        if guard.should_process_audio():
            print("✓ Human present - processing audio")
            
            # Get detailed presence info for logging
            details = guard.get_presence_details()
            if details:
                print(f"  Detection confidence: {details.get('confidence', 0):.2f}")
                print(f"  Detection type: {details.get('detection_type', 'unknown')}")
            
            # Continue with speaker verification...
            return perform_speaker_verification()
        else:
            print("✗ No human detected - skipping audio processing")
            return None
    
    def perform_speaker_verification():
        """Placeholder for actual speaker verification."""
        print("  → Running speaker verification...")
        time.sleep(0.1)  # Simulate processing
        return {"speaker_id": "user123", "confidence": 0.92}
    
    # Run example
    result = process_audio_stream()
    if result:
        print(f"  Speaker verified: {result['speaker_id']} ({result['confidence']:.2f})")


# ============================================================================
# Example 3: Home Automation Integration
# ============================================================================

class HomeAutomationPresence:
    """Integration with home automation systems."""
    
    def __init__(self, presence_service_url: str = "http://localhost:8767"):
        self.presence_service_url = presence_service_url
        self.last_presence_state = None
        self.callbacks: Dict[str, Callable] = {}
        
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for presence events."""
        self.callbacks[event_type] = callback
        
    def check_presence_change(self) -> Optional[Dict[str, Any]]:
        """Check for presence state changes."""
        try:
            response = requests.get(
                f"{self.presence_service_url}/presence",
                timeout=2.0
            )
            
            if response.status_code == 200:
                current_state = response.json()
                
                # Check for state change
                if self.last_presence_state is None:
                    self.last_presence_state = current_state
                    return current_state
                    
                if current_state["human_present"] != self.last_presence_state["human_present"]:
                    # State changed
                    event_type = "presence_detected" if current_state["human_present"] else "presence_lost"
                    
                    # Trigger callback
                    if event_type in self.callbacks:
                        self.callbacks[event_type](current_state)
                    
                    self.last_presence_state = current_state
                    return current_state
                    
        except requests.RequestException:
            pass
            
        return None


def example_home_automation():
    """Example home automation integration."""
    
    automation = HomeAutomationPresence()
    
    # Register event handlers
    def on_presence_detected(presence_data):
        print(f"🏠 Person detected! Confidence: {presence_data['confidence']:.2f}")
        print("  → Turning on lights")
        print("  → Adjusting thermostat")
        print("  → Activating security cameras")
        
    def on_presence_lost(presence_data):
        print("🏠 Person left area")
        print("  → Dimming lights")
        print("  → Energy saving mode")
        
    automation.register_callback("presence_detected", on_presence_detected)
    automation.register_callback("presence_lost", on_presence_lost)
    
    # Monitor for changes
    print("Monitoring for presence changes...")
    for _ in range(10):
        automation.check_presence_change()
        time.sleep(2)


# ============================================================================
# Example 4: Enhanced Service Integration (Recommended)
# ============================================================================

def example_enhanced_service_integration():
    """
    Example showing the enhanced service with HTTP + Gesture Recognition + SSE.
    
    The enhanced service provides:
    - HTTP API (port 8767): Human presence detection
    - SSE Events (port 8766): Real-time gesture streaming  
    - Gesture Recognition: Hand up detection with palm analysis
    - Clean Console Output: Single updating status line (no scroll spam)
    """
    
    # Start enhanced service (in production, this would be a separate process)
    import subprocess
    import threading
    
    def start_enhanced_service():
        """Start the enhanced webcam detection service."""
        # In production, you might use systemd, Docker, or process manager
        subprocess.run([
            "conda", "activate", "webcam", "&&", 
            "python", "webcam_service.py"
        ])
    
    # Start service in background
    service_thread = threading.Thread(target=start_enhanced_service, daemon=True)
    service_thread.start()
    
    # Wait for service to start
    time.sleep(3)
    
    # Test HTTP API
    print("Testing Enhanced HTTP API:")
    try:
        # Simple presence check
        response = requests.get("http://localhost:8767/presence/simple")
        if response.status_code == 200:
            presence = response.json()
            print(f"  Human present: {presence.get('human_present')}")
        
        # Detailed presence info
        response = requests.get("http://localhost:8767/presence")
        if response.status_code == 200:
            details = response.json()
            print(f"  Confidence: {details.get('confidence', 0):.2f}")
            print(f"  Last detection: {details.get('last_detection')}")
        
        # Service health
        response = requests.get("http://localhost:8767/health")
        if response.status_code == 200:
            health = response.json()
            print(f"  Service status: {health.get('status')}")
            print(f"  Uptime: {health.get('uptime_seconds', 0):.1f}s")
            
    except requests.RequestException as e:
        print(f"  HTTP API error: {e}")
    
    # Test gesture events via SSE
    async def test_gesture_events():
        """Test real-time gesture event streaming."""
        import aiohttp
        
        print("\nTesting Gesture SSE Events:")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8766/events/gestures/test_client') as resp:
                    print("  Connected to gesture event stream")
                    
                    # Listen for a few events (timeout after 10 seconds)
                    start_time = time.time()
                    async for line in resp.content:
                        if time.time() - start_time > 10:
                            break
                            
                        if line.startswith(b'data: '):
                            event_data = line[6:].decode().strip()
                            if event_data and event_data != '[HEARTBEAT]':
                                import json
                                try:
                                    gesture_event = json.loads(event_data)
                                    print(f"  Gesture event: {gesture_event['data']['gesture_type']} "
                                          f"(conf: {gesture_event['data']['confidence']:.2f})")
                                except json.JSONDecodeError:
                                    pass
                                    
        except Exception as e:
            print(f"  SSE error: {e}")
    
    # Run gesture test
    try:
        asyncio.run(test_gesture_events())
    except Exception as e:
        print(f"Gesture test failed: {e}")
    
    print("\nEnhanced service integration complete!")
    print("Console shows: 🎥 Frame X | 👤 Human: YES/NO | 🖐️ Gesture: type | FPS: X")


# ============================================================================
# Example 5: Voice Bot Integration with Gesture Control
# ============================================================================

class VoiceBotWithGestureControl:
    """Voice bot that uses presence detection and gesture control."""
    
    def __init__(self):
        self.voice_active = False
        self.gesture_listener_task = None
        self.presence_service = "http://localhost:8767"
        self.gesture_service = "http://localhost:8766"
    
    def check_human_presence(self) -> bool:
        """Check if human is present before starting voice bot."""
        try:
            response = requests.get(f"{self.presence_service}/presence/simple", timeout=1.0)
            return response.json().get("human_present", False)
        except:
            return False
    
    async def start_voice_bot_with_gesture_control(self):
        """Start voice bot with gesture-based stop control."""
        if not self.check_human_presence():
            print("No human detected - voice bot not started")
            return
        
        # Start voice bot
        self.voice_active = True
        print("🎤 Voice bot started - raise hand to stop")
        
        # Start gesture listener
        self.gesture_listener_task = asyncio.create_task(self.listen_for_stop_gestures())
        
        # Simulate voice bot processing
        while self.voice_active:
            print("🔊 Voice bot processing... (raise hand to stop)")
            await asyncio.sleep(2)
            
        print("🛑 Voice bot stopped")
    
    async def listen_for_stop_gestures(self):
        """Listen for hand up gestures to stop voice bot."""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{self.gesture_service}/events/gestures/voice_bot') as resp:
                    async for line in resp.content:
                        if not self.voice_active:
                            break
                            
                        if line.startswith(b'data: '):
                            event_data = line[6:].decode().strip()
                            if event_data and event_data != '[HEARTBEAT]':
                                import json
                                try:
                                    gesture_event = json.loads(event_data)
                                    if gesture_event['data']['gesture_type'] == 'hand_up':
                                        print("🖐️ Hand up detected - stopping voice bot")
                                        self.voice_active = False
                                        break
                                except json.JSONDecodeError:
                                    pass
        except Exception as e:
            print(f"Gesture listener error: {e}")


async def example_voice_bot_integration():
    """Example of voice bot with gesture control."""
    bot = VoiceBotWithGestureControl()
    await bot.start_voice_bot_with_gesture_control()


def example_service_integration():
    """Example showing production service integration patterns."""
    print("Enhanced Service Integration Examples")
    print("====================================")
    
    # Test enhanced service
    example_enhanced_service_integration()
    
    print("\nVoice Bot Integration Example")
    print("============================")
    
    # Test voice bot integration
    try:
        asyncio.run(example_voice_bot_integration())
    except KeyboardInterrupt:
        print("Voice bot integration stopped by user")
    except Exception as e:
        print(f"Voice bot integration error: {e}")
    
    # Original service integration for compatibility
    async def run_service():
        # Create detection system
        from webcam_detection import create_detector
        from webcam_detection.camera import CameraManager, CameraConfig
        
        camera = CameraManager(CameraConfig())
        detector = create_detector('multimodal')
        
        try:
            detector.initialize()
            
            # Simple detection loop
            for i in range(5):
                frame = camera.get_frame()
                if frame is not None:
                    result = detector.detect(frame)
                    print(f"Frame {i+1}: Human={result.human_present}, Conf={result.confidence:.2f}")
                await asyncio.sleep(1)
                
        finally:
            detector.cleanup()
            camera.cleanup()
    
    print("\nDirect Detection Integration Example")
    print("===================================")
    try:
        asyncio.run(run_service())
    except Exception as e:
        print(f"Direct detection error: {e}")
        

# ============================================================================
# Enhanced Testing Integration
# ============================================================================

def example_enhanced_testing_integration():
    """Enhanced testing example with gesture recognition."""
    from unittest.mock import patch, MagicMock
    
    @patch('webcam_detection.create_detector')
    def test_enhanced_speaker_verification(mock_create_detector):
        # Setup mock detector with gesture support
        mock_detector = MagicMock()
        mock_detector.detect.return_value = MagicMock(
            human_present=True,
            confidence=0.85,
            landmarks={'pose': [], 'face': []}
        )
        mock_create_detector.return_value = mock_detector
        
        # Test presence-based processing
        guard = SpeakerVerificationGuard()
        
        # Mock HTTP responses for enhanced service
        with patch('requests.get') as mock_get:
            # Mock presence response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "human_present": True,
                "confidence": 0.85,
                "detection_type": "multimodal",
                "gesture_detected": False
            }
            mock_get.return_value = mock_response
            
            # Test guard clause
            should_process = guard.should_process_audio()
            assert should_process == True
            
            # Test detailed info
            details = guard.get_presence_details()
            assert details["human_present"] == True
            assert details["confidence"] == 0.85
            
        print("✓ Enhanced testing integration passed")
    
    test_enhanced_speaker_verification()


# ============================================================================
# Main Examples Runner
# ============================================================================

if __name__ == "__main__":
    print("🎯 Webcam Detection Package Integration Examples")
    print("=" * 50)
    
    examples = [
        ("Basic Detection", example_basic_detection),
        ("Speaker Verification", example_speaker_verification_integration),
        ("Home Automation", example_home_automation),
        ("Package Configuration", example_package_configuration),
        ("Testing Integration", example_testing_integration),
    ]
    
    for name, example_func in examples:
        print(f"\n📋 Running: {name}")
        print("-" * 30)
        try:
            example_func()
            print(f"✅ {name} completed successfully")
        except Exception as e:
            print(f"❌ {name} failed: {e}")
    
    print(f"\n🔄 Async Examples (run separately):")
    print("- WebSocket Client: asyncio.run(example_websocket_client())")
    print("- Service Integration: example_service_integration()") 