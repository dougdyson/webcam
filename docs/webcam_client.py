#!/usr/bin/env python3
"""
Minimal Webcam Detection Client
===============================

Copy this file into your project for easy integration with the webcam detection service.

Dependencies: pip install requests sseclient-py

Usage:
    from webcam_client import WebcamClient
    
    client = WebcamClient()
    
    # Check presence
    if client.is_human_present():
        print("Human detected!")
    
    # Listen for gestures
    def on_gesture(gesture_type, confidence, hand):
        print(f"Gesture: {gesture_type} ({confidence:.2f})")
    
    client.start_gesture_streaming(on_gesture)
"""

import requests
import json
import threading
import time
from typing import Optional, Callable, Dict, Any

# Optional SSE support
try:
    from sseclient import SSEClient
    HAS_SSE = True
except ImportError:
    HAS_SSE = False


class WebcamClient:
    """
    Simple client for webcam detection service.
    
    Provides human presence detection and gesture event streaming.
    """
    
    def __init__(self, 
                 presence_url: str = "http://localhost:8767",
                 gesture_url: str = "http://localhost:8766",
                 client_id: str = "client",
                 timeout: float = 2.0):
        """
        Initialize webcam client.
        
        Args:
            presence_url: URL for presence detection API
            gesture_url: URL for gesture streaming API  
            client_id: Unique identifier for this client
            timeout: Request timeout in seconds
        """
        self.presence_url = presence_url.rstrip('/')
        self.gesture_url = gesture_url.rstrip('/')
        self.client_id = client_id
        self.timeout = timeout
        
        # Gesture streaming state
        self._streaming = False
        self._stream_thread = None
        self._gesture_callback = None
    
    # ========================================================================
    # Presence Detection
    # ========================================================================
    
    def is_human_present(self) -> bool:
        """
        Check if a human is currently detected.
        
        Returns:
            bool: True if human detected, False otherwise
        """
        try:
            response = requests.get(
                f"{self.presence_url}/presence/simple",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json().get("human_present", False)
        except Exception:
            pass
        return False
    
    def get_presence_info(self) -> Optional[Dict[str, Any]]:
        """
        Get detailed presence information.
        
        Returns:
            dict: Presence details or None if failed
                {
                    "human_present": bool,
                    "confidence": float,
                    "detection_type": str,
                    "timestamp": str,
                    "detection_count": int
                }
        """
        try:
            response = requests.get(
                f"{self.presence_url}/presence",
                timeout=self.timeout
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None
    
    def wait_for_human(self, timeout: float = 30.0, check_interval: float = 0.5) -> bool:
        """
        Wait until a human is detected.
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: How often to check in seconds
            
        Returns:
            bool: True if human detected within timeout, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_human_present():
                return True
            time.sleep(check_interval)
        return False
    
    def is_service_healthy(self) -> bool:
        """
        Check if the webcam detection service is healthy.
        
        Returns:
            bool: True if service is responding, False otherwise
        """
        try:
            response = requests.get(
                f"{self.presence_url}/health",
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception:
            return False
    
    # ========================================================================
    # Gesture Streaming
    # ========================================================================
    
    def start_gesture_streaming(self, callback: Callable[[str, float, str], None]):
        """
        Start listening for gesture events.
        
        Args:
            callback: Function called for each gesture event
                     callback(gesture_type: str, confidence: float, hand: str)
        
        Example:
            def on_gesture(gesture_type, confidence, hand):
                print(f"Gesture: {gesture_type} ({confidence:.2f}) with {hand} hand")
            
            client.start_gesture_streaming(on_gesture)
        """
        if not HAS_SSE:
            print("SSE not available. Install: pip install sseclient-py")
            return False
            
        if self._streaming:
            print("Gesture streaming already active")
            return False
        
        self._gesture_callback = callback
        self._streaming = True
        self._stream_thread = threading.Thread(target=self._gesture_worker, daemon=True)
        self._stream_thread.start()
        return True
    
    def stop_gesture_streaming(self):
        """Stop gesture streaming."""
        self._streaming = False
        if self._stream_thread:
            self._stream_thread.join(timeout=1.0)
        self._gesture_callback = None
    
    def _gesture_worker(self):
        """Background worker for gesture streaming."""
        url = f"{self.gesture_url}/events/gestures/{self.client_id}"
        
        try:
            client = SSEClient(url)
            for event in client:
                if not self._streaming:
                    break
                    
                if event.event == 'gesture' and self._gesture_callback:
                    try:
                        data = json.loads(event.data)
                        gesture_type = data.get("gesture_type", "unknown")
                        confidence = data.get("confidence", 0.0)
                        hand = data.get("hand", "unknown")
                        
                        self._gesture_callback(gesture_type, confidence, hand)
                        
                    except (json.JSONDecodeError, Exception) as e:
                        print(f"Gesture event error: {e}")
                        
        except Exception as e:
            if self._streaming:  # Only print if we didn't stop intentionally
                print(f"Gesture streaming error: {e}")
    
    # ========================================================================
    # Convenience Methods
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get overall status of client and service.
        
        Returns:
            dict: Status information
        """
        presence_info = self.get_presence_info()
        
        return {
            "service_healthy": self.is_service_healthy(),
            "human_present": presence_info.get("human_present", False) if presence_info else False,
            "confidence": presence_info.get("confidence", 0.0) if presence_info else 0.0,
            "gesture_streaming": self._streaming,
            "has_sse_support": HAS_SSE,
            "client_id": self.client_id
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup."""
        self.stop_gesture_streaming()


# ============================================================================
# Example Usage
# ============================================================================

def example_basic_usage():
    """Basic usage example."""
    print("=== Basic Usage ===")
    
    client = WebcamClient(client_id="example")
    
    # Check service health
    if not client.is_service_healthy():
        print("❌ Service not available. Start with: python webcam_enhanced_service.py")
        return
    
    print("✅ Service is healthy")
    
    # Check presence
    if client.is_human_present():
        print("👤 Human detected!")
        
        info = client.get_presence_info()
        if info:
            print(f"   Confidence: {info['confidence']:.2f}")
            print(f"   Detection count: {info.get('detection_count', 0)}")
    else:
        print("❌ No human detected")
    
    # Show status
    status = client.get_status()
    print(f"Status: {status}")


def example_gesture_streaming():
    """Gesture streaming example."""
    print("=== Gesture Streaming ===")
    
    client = WebcamClient(client_id="gesture_example")
    
    if not client.is_service_healthy():
        print("❌ Service not available")
        return
    
    # Define gesture handler
    def handle_gesture(gesture_type, confidence, hand):
        if confidence > 0.7:  # Only show high-confidence gestures
            print(f"🤚 {gesture_type.upper()} ({confidence:.2f}) - {hand} hand")
            
            # React to specific gestures
            if gesture_type == "thumbs_up":
                print("   👍 Positive feedback!")
            elif gesture_type == "thumbs_down":
                print("   👎 Negative feedback!")
            elif gesture_type == "peace":
                print("   ✌️ Peace out!")
            elif gesture_type == "stop":
                print("   ✋ Stop detected!")
    
    # Start streaming
    if client.start_gesture_streaming(handle_gesture):
        print("🎯 Gesture streaming started. Make some gestures!")
        print("   Supported: thumbs_up, thumbs_down, peace, stop, pointing, fist")
        
        try:
            # Monitor for 30 seconds
            for i in range(30):
                if i % 5 == 0:  # Check presence every 5 seconds
                    if client.is_human_present():
                        print(f"   [{i}s] Human present - gestures active")
                    else:
                        print(f"   [{i}s] No human - waiting...")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️ Stopped by user")
        
        client.stop_gesture_streaming()
        print("🛑 Gesture streaming stopped")


def example_context_manager():
    """Context manager usage example."""
    print("=== Context Manager Usage ===")
    
    with WebcamClient(client_id="context_example") as client:
        if client.is_human_present():
            print("👤 Human detected in context!")
        else:
            print("❌ No human in context")
    
    print("✅ Client cleaned up automatically")


if __name__ == "__main__":
    print("🎯 Webcam Detection Client Examples")
    print("=" * 40)
    print()
    print("Make sure the service is running:")
    print("  python webcam_enhanced_service.py")
    print()
    
    # Run examples
    example_basic_usage()
    print()
    
    example_context_manager()
    print()
    
    # Ask user if they want to try gesture streaming
    try:
        response = input("Try gesture streaming example? (y/n): ").lower()
        if response.startswith('y'):
            example_gesture_streaming()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!") 