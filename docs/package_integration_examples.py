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
# Example 4: Real-time WebSocket Integration
# ============================================================================

async def example_websocket_client():
    """Example WebSocket client for real-time presence updates."""
    import websockets
    import json
    
    uri = "ws://localhost:8765/ws/home_automation"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔌 Connected to presence WebSocket")
            
            # Send subscription message
            subscribe_msg = {
                "type": "subscribe",
                "event_types": ["presence_changed", "detection_update"]
            }
            await websocket.send(json.dumps(subscribe_msg))
            print("📡 Subscribed to presence events")
            
            # Listen for events
            while True:
                try:
                    message = await websocket.recv()
                    event_data = json.loads(message)
                    
                    if event_data.get("event_type") == "presence_changed":
                        data = event_data.get("data", {})
                        print(f"🔄 Presence changed: {data.get('human_present')}")
                        
                    elif event_data.get("event_type") == "detection_update":
                        data = event_data.get("data", {})
                        print(f"📊 Detection update: {data.get('confidence', 0):.2f}")
                        
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 WebSocket connection closed")
                    break
                    
    except Exception as e:
        print(f"❌ WebSocket error: {e}")


# ============================================================================
# Example 5: Service Layer Integration
# ============================================================================

def example_service_integration():
    """Example of running the detection system as a service."""
    from webcam_detection.service import DetectionServiceManager, HTTPServiceConfig
    from webcam_detection import create_detector
    import cv2
    
    async def run_service():
        # Create detection system
        detector = create_detector('multimodal')
        detector.initialize()
        
        # Create camera
        cap = cv2.VideoCapture(0)
        
        # Create service manager
        manager = DetectionServiceManager()
        
        # Add HTTP service for guard clauses
        http_config = HTTPServiceConfig(
            host="localhost",
            port=8767,
            enable_history=True,
            history_limit=1000
        )
        http_service = manager.add_http_service(http_config)
        
        try:
            print("🚀 Starting detection service...")
            await manager.start_all_services()
            print("✅ Service running on http://localhost:8767")
            
            # Simulate detection loop
            for i in range(100):
                # Get frame from camera
                ret, frame = cap.read()
                
                if ret:
                    # Perform detection with current API
                    result = detector.detect(frame)
                    
                    # Publish to service layer
                    manager.publish_detection_result(result)
                else:
                    print("Warning: No camera frame available")
                
                await asyncio.sleep(1)  # 1 FPS for demo
                
        finally:
            print("🛑 Stopping services...")
            await manager.stop_all_services()
            cap.release()
            detector.cleanup()
    
    # Run the service
    asyncio.run(run_service())


# ============================================================================
# Example 6: Package Configuration
# ============================================================================

def example_package_configuration():
    """Example of configuring the package for different environments."""
    from webcam_detection.utils.config import ConfigManager
    
    # Load configuration
    config_manager = ConfigManager()
    
    # Production configuration
    production_config = {
        'detection': {
            'detector_type': 'multimodal',
            'confidence_threshold': 0.7,  # Higher for production
            'pose_weight': 0.6,
            'face_weight': 0.4
        },
        'service': {
            'http': {
                'host': '0.0.0.0',  # Accept external connections
                'port': 8767,
                'enable_history': True,
                'history_limit': 5000
            },
            'rate_limiting': {
                'requests_per_second': 100,
                'burst_limit': 200
            }
        }
    }
    
    # Development configuration
    development_config = {
        'detection': {
            'detector_type': 'multimodal',
            'confidence_threshold': 0.5,  # Lower for testing
            'pose_weight': 0.6,
            'face_weight': 0.4
        },
        'service': {
            'http': {
                'host': 'localhost',
                'port': 8767,
                'enable_history': True,
                'history_limit': 1000
            },
            'rate_limiting': {
                'requests_per_second': 10,
                'burst_limit': 20
            }
        }
    }
    
    # Use appropriate config based on environment
    import os
    env = os.getenv('ENVIRONMENT', 'development')
    
    if env == 'production':
        config = production_config
        print("📦 Using production configuration")
    else:
        config = development_config
        print("🔧 Using development configuration")
    
    return config


# ============================================================================
# Example 7: Testing Integration
# ============================================================================

def example_testing_integration():
    """Example of testing applications that use webcam-detection."""
    import pytest
    from unittest.mock import Mock, patch
    
    # Mock the detection service for testing
    @patch('webcam_detection.create_detector')
    def test_speaker_verification_with_presence(mock_create_detector):
        # Setup mock detector
        mock_detector = Mock()
        
        # Mock DetectionResult object instead of tuple
        from webcam_detection.detection.result import DetectionResult
        mock_result = DetectionResult(
            human_present=True,
            confidence=0.85,
            bounding_box=[100, 100, 200, 300],
            landmarks={'pose': [], 'face': []}
        )
        mock_detector.detect.return_value = mock_result
        mock_create_detector.return_value = mock_detector
        
        # Test your application logic
        guard = SpeakerVerificationGuard()
        
        # Mock the HTTP request
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "human_present": True,
                "confidence": 0.85
            }
            mock_get.return_value = mock_response
            
            # Test guard clause
            result = guard.should_process_audio()
            assert result is True
    
    # Run the test
    test_speaker_verification_with_presence()
    print("✅ Test passed!")


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