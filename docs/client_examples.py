#!/usr/bin/env python3
"""
Client Examples for Webcam Detection Service
============================================

This file demonstrates how to integrate with the webcam detection service
from other Python applications. The service provides:

1. HTTP API (port 8767) - Human presence detection
2. SSE Stream (port 8766) - Real-time gesture events

Prerequisites:
    1. Start the webcam detection service:
       python webcam_enhanced_service.py
    
    2. Install required client dependencies:
       pip install requests sseclient-py asyncio aiohttp

Examples included:
- Simple HTTP client for presence detection
- SSE client for real-time gesture events
- Combined client for both presence and gestures
- Integration patterns for different use cases
"""

import asyncio
import time
import requests
import json
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime
import threading
from dataclasses import dataclass

# For SSE streaming
try:
    from sseclient import SSEClient
except ImportError:
    print("Install sseclient-py: pip install sseclient-py")
    SSEClient = None

try:
    import aiohttp
except ImportError:
    print("Install aiohttp: pip install aiohttp")
    aiohttp = None


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class PresenceStatus:
    """Represents human presence status."""
    human_present: bool
    confidence: float
    detection_type: str
    timestamp: datetime
    detection_count: int = 0

@dataclass
class GestureEvent:
    """Represents a gesture detection event."""
    gesture_type: str
    confidence: float
    hand: str
    timestamp: datetime
    client_id: str = ""


# ============================================================================
# Example 1: Simple HTTP Client for Presence Detection
# ============================================================================

class PresenceClient:
    """Simple HTTP client for human presence detection."""
    
    def __init__(self, base_url: str = "http://localhost:8767", timeout: float = 2.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
    def is_human_present(self) -> bool:
        """
        Simple boolean check for human presence.
        
        Returns:
            bool: True if human is detected, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/presence/simple",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("human_present", False)
                
        except requests.RequestException as e:
            print(f"Presence check failed: {e}")
            
        return False
    
    def get_presence_status(self) -> Optional[PresenceStatus]:
        """
        Get detailed presence status.
        
        Returns:
            PresenceStatus: Detailed presence information or None if failed
        """
        try:
            response = requests.get(
                f"{self.base_url}/presence",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return PresenceStatus(
                    human_present=data.get("human_present", False),
                    confidence=data.get("confidence", 0.0),
                    detection_type=data.get("detection_type", "unknown"),
                    timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                    detection_count=data.get("detection_count", 0)
                )
                
        except requests.RequestException as e:
            print(f"Failed to get presence status: {e}")
        except Exception as e:
            print(f"Error parsing presence status: {e}")
            
        return None
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health and statistics."""
        try:
            # Health check
            health_response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            health_data = health_response.json() if health_response.status_code == 200 else {}
            
            # Statistics
            stats_response = requests.get(f"{self.base_url}/statistics", timeout=self.timeout)
            stats_data = stats_response.json() if stats_response.status_code == 200 else {}
            
            return {
                "health": health_data,
                "statistics": stats_data,
                "service_available": health_response.status_code == 200
            }
            
        except requests.RequestException as e:
            return {
                "health": {},
                "statistics": {},
                "service_available": False,
                "error": str(e)
            }


def example_simple_presence_client():
    """Example usage of the simple presence client."""
    print("=== Simple Presence Client Example ===")
    
    client = PresenceClient()
    
    # Simple presence check
    if client.is_human_present():
        print("✓ Human detected!")
        
        # Get detailed status
        status = client.get_presence_status()
        if status:
            print(f"  Confidence: {status.confidence:.2f}")
            print(f"  Detection type: {status.detection_type}")
            print(f"  Detection count: {status.detection_count}")
    else:
        print("✗ No human detected")
    
    # Service health
    health = client.get_service_health()
    print(f"Service available: {health['service_available']}")
    if health['statistics']:
        stats = health['statistics']
        print(f"Total detections: {stats.get('total_detections', 0)}")
        print(f"Uptime: {stats.get('uptime_seconds', 0):.1f}s")


# ============================================================================
# Example 2: SSE Client for Real-time Gesture Events
# ============================================================================

class GestureStreamClient:
    """SSE client for real-time gesture events."""
    
    def __init__(self, base_url: str = "http://localhost:8766", client_id: str = "client_001"):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.is_running = False
        self.event_callbacks: List[Callable[[GestureEvent], None]] = []
        
    def add_gesture_callback(self, callback: Callable[[GestureEvent], None]):
        """Add callback for gesture events."""
        self.event_callbacks.append(callback)
        
    def start_streaming(self):
        """Start streaming gesture events (blocking)."""
        if not SSEClient:
            print("SSEClient not available. Install: pip install sseclient-py")
            return
            
        self.is_running = True
        url = f"{self.base_url}/events/gestures/{self.client_id}"
        
        print(f"🔗 Connecting to gesture stream: {url}")
        
        try:
            client = SSEClient(url)
            
            for event in client:
                if not self.is_running:
                    break
                    
                if event.event == 'gesture':
                    try:
                        data = json.loads(event.data)
                        gesture_event = GestureEvent(
                            gesture_type=data.get("gesture_type", "unknown"),
                            confidence=data.get("confidence", 0.0),
                            hand=data.get("hand", "unknown"),
                            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                            client_id=self.client_id
                        )
                        
                        # Call all registered callbacks
                        for callback in self.event_callbacks:
                            try:
                                callback(gesture_event)
                            except Exception as e:
                                print(f"Callback error: {e}")
                                
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse gesture event: {e}")
                        
                elif event.event == 'ping':
                    print("📡 Connection alive")
                    
        except Exception as e:
            print(f"Gesture streaming error: {e}")
        finally:
            print("🔌 Gesture stream disconnected")
    
    def start_streaming_async(self):
        """Start streaming in background thread."""
        if self.is_running:
            print("Streaming already running")
            return
            
        thread = threading.Thread(target=self.start_streaming, daemon=True)
        thread.start()
        return thread
    
    def stop_streaming(self):
        """Stop streaming."""
        self.is_running = False


def example_gesture_stream_client():
    """Example usage of the gesture stream client."""
    print("=== Gesture Stream Client Example ===")
    
    client = GestureStreamClient(client_id="example_client")
    
    # Add gesture event handler
    def on_gesture(event: GestureEvent):
        print(f"🤚 Gesture detected: {event.gesture_type} "
              f"({event.confidence:.2f}) with {event.hand} hand")
    
    client.add_gesture_callback(on_gesture)
    
    # Start streaming in background
    print("Starting gesture stream (will run for 30 seconds)...")
    stream_thread = client.start_streaming_async()
    
    # Let it run for 30 seconds
    time.sleep(30)
    
    # Stop streaming
    client.stop_streaming()
    print("Gesture streaming stopped")


# ============================================================================
# Example 3: Combined Client (Presence + Gestures)
# ============================================================================

class WebcamDetectionClient:
    """Combined client for both presence detection and gesture events."""
    
    def __init__(self, 
                 presence_url: str = "http://localhost:8767",
                 gesture_url: str = "http://localhost:8766",
                 client_id: str = "combined_client"):
        self.presence_client = PresenceClient(presence_url)
        self.gesture_client = GestureStreamClient(gesture_url, client_id)
        
        # State tracking
        self.current_presence = False
        self.last_gesture = None
        self.gesture_history: List[GestureEvent] = []
        
        # Setup gesture callback
        self.gesture_client.add_gesture_callback(self._on_gesture_event)
        
    def _on_gesture_event(self, event: GestureEvent):
        """Internal gesture event handler."""
        self.last_gesture = event
        self.gesture_history.append(event)
        
        # Keep only last 50 gestures
        if len(self.gesture_history) > 50:
            self.gesture_history = self.gesture_history[-50:]
    
    def start_monitoring(self):
        """Start monitoring both presence and gestures."""
        print("🚀 Starting combined monitoring...")
        
        # Start gesture streaming
        self.gesture_client.start_streaming_async()
        
        # Monitor presence in main thread
        try:
            while True:
                # Check presence
                new_presence = self.presence_client.is_human_present()
                
                if new_presence != self.current_presence:
                    self.current_presence = new_presence
                    if new_presence:
                        print("👤 Human entered the scene")
                    else:
                        print("🚶 Human left the scene")
                
                # Show recent gesture if any
                if self.last_gesture:
                    time_since = (datetime.now() - self.last_gesture.timestamp).total_seconds()
                    if time_since < 5:  # Show gestures from last 5 seconds
                        print(f"   Recent gesture: {self.last_gesture.gesture_type} "
                              f"({self.last_gesture.confidence:.2f})")
                
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping monitoring...")
        finally:
            self.gesture_client.stop_streaming()
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current status summary."""
        presence_status = self.presence_client.get_presence_status()
        
        return {
            "presence": {
                "human_present": self.current_presence,
                "details": presence_status.__dict__ if presence_status else None
            },
            "gestures": {
                "last_gesture": self.last_gesture.__dict__ if self.last_gesture else None,
                "gesture_count": len(self.gesture_history),
                "recent_gestures": [g.gesture_type for g in self.gesture_history[-5:]]
            }
        }


def example_combined_client():
    """Example usage of the combined client."""
    print("=== Combined Client Example ===")
    
    client = WebcamDetectionClient(client_id="combined_example")
    
    # Get initial status
    status = client.get_status_summary()
    print("Initial status:")
    print(f"  Human present: {status['presence']['human_present']}")
    print(f"  Gesture history: {len(status['gestures']['recent_gestures'])} recent")
    
    # Start monitoring (this will run until Ctrl+C)
    print("\nStarting monitoring (press Ctrl+C to stop)...")
    client.start_monitoring()


# ============================================================================
# Example 4: Integration Patterns
# ============================================================================

class SmartHomeController:
    """Example smart home integration using webcam detection."""
    
    def __init__(self):
        self.webcam_client = WebcamDetectionClient(client_id="smart_home")
        self.lights_on = False
        self.music_playing = False
        
        # Setup gesture handlers
        self.webcam_client.gesture_client.add_gesture_callback(self._handle_gesture)
        
    def _handle_gesture(self, event: GestureEvent):
        """Handle gesture events for home automation."""
        if event.confidence < 0.8:  # Only high-confidence gestures
            return
            
        if event.gesture_type == "hand_up":
            # Hand up gesture - emergency stop/pause all systems
            self._emergency_stop()
    
    def _emergency_stop(self):
        """Emergency stop all systems."""
        print("🛑 Emergency stop (hand up gesture detected)")
        print("   Turning off all lights and stopping music")
        self.lights_on = False
        self.music_playing = False
    
    def start_smart_home(self):
        """Start smart home automation."""
        print("🏠 Starting smart home automation...")
        print("Gesture controls:")
        print("  ✋ Hand up (palm facing camera) = Emergency stop all systems")
        print("  Note: Lights and music controlled by other means, gesture for emergency stop only")
        print()
        
        # Start monitoring
        self.webcam_client.start_monitoring()


class SecuritySystem:
    """Example security system integration."""
    
    def __init__(self):
        self.presence_client = PresenceClient()
        self.armed = False
        self.intrusion_detected = False
        
    def arm_system(self):
        """Arm the security system."""
        self.armed = True
        print("🔒 Security system ARMED")
        
    def disarm_system(self):
        """Disarm the security system."""
        self.armed = False
        self.intrusion_detected = False
        print("🔓 Security system DISARMED")
        
    def monitor_security(self):
        """Monitor for security events."""
        print("👮 Security monitoring active...")
        
        try:
            while True:
                if self.armed:
                    # Check for human presence
                    status = self.presence_client.get_presence_status()
                    
                    if status and status.human_present and status.confidence > 0.7:
                        if not self.intrusion_detected:
                            print("🚨 INTRUSION DETECTED!")
                            print(f"   Confidence: {status.confidence:.2f}")
                            print(f"   Time: {status.timestamp}")
                            self.intrusion_detected = True
                            
                            # In real system: send alerts, record video, etc.
                            
                time.sleep(2)  # Check every 2 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Security monitoring stopped")


# ============================================================================
# Example 5: Async Client (Advanced)
# ============================================================================

class AsyncWebcamClient:
    """Async client for high-performance applications."""
    
    def __init__(self, presence_url: str = "http://localhost:8767"):
        self.presence_url = presence_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        if aiohttp:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def get_presence_async(self) -> Optional[PresenceStatus]:
        """Get presence status asynchronously."""
        if not self.session:
            print("Session not initialized. Use async context manager.")
            return None
            
        try:
            async with self.session.get(f"{self.presence_url}/presence") as response:
                if response.status == 200:
                    data = await response.json()
                    return PresenceStatus(
                        human_present=data.get("human_present", False),
                        confidence=data.get("confidence", 0.0),
                        detection_type=data.get("detection_type", "unknown"),
                        timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
                        detection_count=data.get("detection_count", 0)
                    )
        except Exception as e:
            print(f"Async presence check failed: {e}")
            
        return None


async def example_async_client():
    """Example usage of async client."""
    print("=== Async Client Example ===")
    
    if not aiohttp:
        print("aiohttp not available. Install: pip install aiohttp")
        return
    
    async with AsyncWebcamClient() as client:
        # Multiple concurrent requests
        tasks = [client.get_presence_async() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        for i, result in enumerate(results):
            if result:
                print(f"Request {i+1}: Human present = {result.human_present} "
                      f"(confidence: {result.confidence:.2f})")
            else:
                print(f"Request {i+1}: Failed")


# ============================================================================
# Main Examples Runner
# ============================================================================

def main():
    """Run all client examples."""
    print("🎯 Webcam Detection Service - Client Examples")
    print("=" * 50)
    print()
    print("Make sure the webcam detection service is running:")
    print("  python webcam_enhanced_service.py")
    print()
    
    examples = [
        ("Simple Presence Client", example_simple_presence_client),
        ("Gesture Stream Client", example_gesture_stream_client),
        ("Combined Client", example_combined_client),
        ("Async Client", lambda: asyncio.run(example_async_client())),
    ]
    
    for name, func in examples:
        print(f"\n{'='*20} {name} {'='*20}")
        try:
            func()
        except KeyboardInterrupt:
            print(f"\n{name} stopped by user")
        except Exception as e:
            print(f"Error in {name}: {e}")
        
        input("\nPress Enter to continue to next example...")


if __name__ == "__main__":
    main() 