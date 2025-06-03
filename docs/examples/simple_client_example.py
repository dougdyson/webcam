#!/usr/bin/env python3
"""
Simple Webcam Detection Client Example
======================================

A minimal, standalone example showing how to integrate with the webcam detection service
from another Python application. Copy this file into your project and modify as needed.

Prerequisites:
    1. Start the webcam detection service:
       python webcam_service.py
    
    2. Install dependencies:
       pip install requests sseclient-py

Usage:
    python simple_client_example.py
"""

import time
import requests
import json
import threading
from datetime import datetime
from typing import Optional, Callable

# For SSE streaming (install: pip install sseclient-py)
try:
    from sseclient import SSEClient
except ImportError:
    print("Install sseclient-py: pip install sseclient-py")
    SSEClient = None


class SimpleWebcamClient:
    """
    Simple client for webcam detection service.
    
    Provides both presence detection and gesture events in one easy-to-use class.
    """
    
    def __init__(self, 
                 presence_url: str = "http://localhost:8767",
                 gesture_url: str = "http://localhost:8766",
                 client_id: str = "my_app"):
        self.presence_url = presence_url.rstrip('/')
        self.gesture_url = gesture_url.rstrip('/')
        self.client_id = client_id
        
        # Gesture streaming
        self.gesture_callbacks = []
        self.streaming = False
        
    # ========================================================================
    # Presence Detection (HTTP API)
    # ========================================================================
    
    def is_human_present(self) -> bool:
        """
        Check if a human is currently detected.
        
        Returns:
            bool: True if human detected, False otherwise
        """
        try:
            response = requests.get(f"{self.presence_url}/presence/simple", timeout=2.0)
            if response.status_code == 200:
                return response.json().get("human_present", False)
        except Exception as e:
            print(f"Presence check failed: {e}")
        return False
    
    def get_presence_details(self) -> Optional[dict]:
        """
        Get detailed presence information.
        
        Returns:
            dict: Presence details including confidence, or None if failed
        """
        try:
            response = requests.get(f"{self.presence_url}/presence", timeout=2.0)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Failed to get presence details: {e}")
        return None
    
    def wait_for_human(self, timeout: float = 30.0) -> bool:
        """
        Wait until a human is detected or timeout.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if human detected within timeout, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_human_present():
                return True
            time.sleep(0.5)
        return False
    
    # ========================================================================
    # Gesture Events (SSE Streaming)
    # ========================================================================
    
    def add_gesture_callback(self, callback: Callable[[dict], None]):
        """
        Add a callback function for gesture events.
        
        Args:
            callback: Function that takes a gesture event dict as parameter
                     Event format: {
                         "gesture_type": str,
                         "confidence": float,
                         "hand": str,
                         "timestamp": str
                     }
        """
        self.gesture_callbacks.append(callback)
    
    def start_gesture_streaming(self):
        """Start listening for gesture events in background thread."""
        if not SSEClient:
            print("SSEClient not available. Install: pip install sseclient-py")
            return
            
        if self.streaming:
            print("Gesture streaming already active")
            return
            
        self.streaming = True
        thread = threading.Thread(target=self._gesture_stream_worker, daemon=True)
        thread.start()
        print(f"🤚 Started gesture streaming (client_id: {self.client_id})")
    
    def stop_gesture_streaming(self):
        """Stop gesture streaming."""
        self.streaming = False
        print("🛑 Stopped gesture streaming")
    
    def _gesture_stream_worker(self):
        """Background worker for gesture streaming."""
        url = f"{self.gesture_url}/events/gestures/{self.client_id}"
        
        try:
            client = SSEClient(url)
            for event in client:
                if not self.streaming:
                    break
                    
                if event.event == 'gesture':
                    try:
                        gesture_data = json.loads(event.data)
                        
                        # Call all registered callbacks
                        for callback in self.gesture_callbacks:
                            try:
                                callback(gesture_data)
                            except Exception as e:
                                print(f"Gesture callback error: {e}")
                                
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse gesture event: {e}")
                        
        except Exception as e:
            print(f"Gesture streaming error: {e}")
    
    # ========================================================================
    # Convenience Methods
    # ========================================================================
    
    def get_status(self) -> dict:
        """Get combined status of presence and service health."""
        presence = self.get_presence_details()
        
        # Check service health
        try:
            health_response = requests.get(f"{self.presence_url}/health", timeout=2.0)
            service_healthy = health_response.status_code == 200
        except:
            service_healthy = False
        
        return {
            "service_healthy": service_healthy,
            "human_present": presence.get("human_present", False) if presence else False,
            "confidence": presence.get("confidence", 0.0) if presence else 0.0,
            "gesture_streaming": self.streaming,
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# Example Usage Patterns
# ============================================================================

def example_basic_usage():
    """Basic usage example."""
    print("=== Basic Usage Example ===")
    
    client = SimpleWebcamClient(client_id="basic_example")
    
    # Check presence
    if client.is_human_present():
        print("✓ Human detected!")
        
        # Get details
        details = client.get_presence_details()
        if details:
            print(f"  Confidence: {details['confidence']:.2f}")
            print(f"  Detection count: {details.get('detection_count', 0)}")
    else:
        print("✗ No human detected")
    
    # Service status
    status = client.get_status()
    print(f"Service healthy: {status['service_healthy']}")


def example_gesture_integration():
    """Example with gesture event handling."""
    print("=== Gesture Integration Example ===")
    
    client = SimpleWebcamClient(client_id="gesture_example")
    
    # Define gesture handler
    def on_gesture(gesture_event):
        gesture_type = gesture_event.get("gesture_type", "unknown")
        confidence = gesture_event.get("confidence", 0.0)
        hand = gesture_event.get("hand", "unknown")
        palm_facing = gesture_event.get("palm_facing_camera", False)
        
        print(f"🤚 Gesture: {gesture_type} ({confidence:.2f}) with {hand} hand")
        print(f"   Palm facing camera: {palm_facing}")
        
        # Handle hand up gesture
        if gesture_type == "hand_up" and confidence > 0.8:
            print("  ✋ High-confidence hand up detected!")
            print("  🛑 This could trigger: pause voice bot, stop music, emergency stop, etc.")
    
    # Register gesture handler
    client.add_gesture_callback(on_gesture)
    
    # Start gesture streaming
    client.start_gesture_streaming()
    
    # Monitor for 30 seconds
    print("Monitoring gestures for 30 seconds...")
    try:
        for i in range(30):
            # Also check presence every 5 seconds
            if i % 5 == 0:
                if client.is_human_present():
                    print(f"  [{i}s] Human present")
                else:
                    print(f"  [{i}s] No human")
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user")
    
    # Stop streaming
    client.stop_gesture_streaming()


def example_smart_app():
    """Example smart application using both presence and gestures."""
    print("=== Smart Application Example ===")
    
    client = SimpleWebcamClient(client_id="smart_app")
    
    # Application state
    app_active = False
    
    def on_gesture(gesture_event):
        nonlocal app_active
        
        gesture_type = gesture_event.get("gesture_type", "unknown")
        confidence = gesture_event.get("confidence", 0.0)
        
        if confidence < 0.8:  # Only high-confidence gestures
            return
        
        if gesture_type == "hand_up":
            # Hand up gesture - universal stop/pause signal
            if app_active:
                app_active = False
                print("🛑 Hand up detected - app paused!")
            else:
                print("✋ Hand up detected (app already inactive)")
    
    # Setup gesture handling
    client.add_gesture_callback(on_gesture)
    client.start_gesture_streaming()
    
    print("Smart app running...")
    print("Gestures:")
    print("  ✋ Hand up (palm facing camera) = Pause/stop app")
    print("  Note: App auto-activates when human present, hand up pauses it")
    print()
    
    try:
        while True:
            # Check presence
            human_present = client.is_human_present()
            
            # App logic
            if human_present and not app_active:
                app_active = True  # Auto-activate when human appears
                
            if human_present and app_active:
                print(f"\r🟢 App ACTIVE - Human present (raise hand to pause)", end='', flush=True)
            elif human_present and not app_active:
                print(f"\r🟡 App PAUSED - Human present (paused by hand gesture)", end='', flush=True)
            else:
                print(f"\r🔴 App WAITING - No human detected", end='', flush=True)
                app_active = False  # Auto-deactivate when no human
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Smart app stopped")
    finally:
        client.stop_gesture_streaming()


def example_wait_for_human():
    """Example waiting for human presence."""
    print("=== Wait for Human Example ===")
    
    client = SimpleWebcamClient(client_id="wait_example")
    
    print("Waiting for human to appear (30 second timeout)...")
    
    if client.wait_for_human(timeout=30.0):
        print("✓ Human detected! Continuing with application...")
        
        # Get details about the detection
        details = client.get_presence_details()
        if details:
            print(f"  Detection confidence: {details['confidence']:.2f}")
            print(f"  Detection type: {details.get('detection_type', 'unknown')}")
    else:
        print("✗ Timeout - no human detected within 30 seconds")


# ============================================================================
# Main Example Runner
# ============================================================================

def main():
    """Run example demonstrations."""
    print("🎯 Simple Webcam Detection Client Examples")
    print("=" * 50)
    print()
    print("Make sure the webcam detection service is running:")
    print("  python webcam_service.py")
    print()
    
    examples = [
        ("Basic Usage", example_basic_usage),
        ("Gesture Integration", example_gesture_integration),
        ("Smart Application", example_smart_app),
        ("Wait for Human", example_wait_for_human),
    ]
    
    for name, func in examples:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            func()
        except KeyboardInterrupt:
            print(f"\n{name} stopped by user")
        except Exception as e:
            print(f"Error in {name}: {e}")
        
        if name != examples[-1][0]:  # Not the last example
            input("\nPress Enter to continue to next example...")


if __name__ == "__main__":
    main() 