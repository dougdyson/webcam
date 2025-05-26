#!/usr/bin/env python3
"""
Complete Gesture Recognition Client Example

This demonstrates how to integrate with the webcam gesture recognition service
in your external application.

Services:
- HTTP API (port 8767): Human presence detection
- SSE Stream (port 8766): Real-time gesture events

Usage:
    python gesture_client_example.py
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Optional, Callable

class GestureClient:
    """
    Complete client for webcam gesture recognition service.
    
    Provides both presence detection and real-time gesture events.
    """
    
    def __init__(self, 
                 presence_url: str = "http://localhost:8767",
                 gesture_sse_url: str = "http://localhost:8766"):
        self.presence_url = presence_url
        self.gesture_sse_url = gesture_sse_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False
        
        # Callbacks for your app logic
        self.on_human_detected: Optional[Callable[[bool, float], None]] = None
        self.on_gesture_detected: Optional[Callable[[str, float, str], None]] = None
        self.on_connection_error: Optional[Callable[[str], None]] = None
    
    async def initialize(self):
        """Initialize the client session."""
        self.session = aiohttp.ClientSession()
        print("✅ Gesture client initialized")
    
    async def check_presence(self) -> dict:
        """Check if human is present (one-time check)."""
        if not self.session:
            raise RuntimeError("Client not initialized")
        
        try:
            async with self.session.get(f"{self.presence_url}/presence/simple") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise aiohttp.ClientError(f"HTTP {response.status}")
        except Exception as e:
            if self.on_connection_error:
                self.on_connection_error(f"Presence check failed: {e}")
            raise
    
    async def get_detailed_status(self) -> dict:
        """Get detailed detection status."""
        if not self.session:
            raise RuntimeError("Client not initialized")
        
        try:
            async with self.session.get(f"{self.presence_url}/presence") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise aiohttp.ClientError(f"HTTP {response.status}")
        except Exception as e:
            if self.on_connection_error:
                self.on_connection_error(f"Status check failed: {e}")
            raise
    
    async def start_gesture_stream(self, client_id: str = "client_001"):
        """
        Start listening for real-time gesture events via SSE.
        
        This is the main method for gesture integration!
        """
        if not self.session:
            raise RuntimeError("Client not initialized")
        
        self.running = True
        sse_url = f"{self.gesture_sse_url}/events/gestures/{client_id}"
        
        print(f"🔗 Connecting to gesture stream: {sse_url}")
        
        while self.running:
            try:
                async with self.session.get(sse_url) as response:
                    if response.status != 200:
                        raise aiohttp.ClientError(f"SSE connection failed: HTTP {response.status}")
                    
                    print("✅ Connected to gesture stream")
                    
                    async for line in response.content:
                        if not self.running:
                            break
                        
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                        
                        # Parse SSE format
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])  # Remove 'data: ' prefix
                                await self._handle_gesture_event(data)
                            except json.JSONDecodeError as e:
                                print(f"⚠️ Failed to parse SSE data: {e}")
                        elif line.startswith('event: '):
                            event_type = line[7:]  # Remove 'event: ' prefix
                            print(f"📡 SSE Event: {event_type}")
                        # Ignore other SSE lines (id:, retry:, etc.)
            
            except Exception as e:
                error_msg = f"Gesture stream error: {e}"
                print(f"❌ {error_msg}")
                if self.on_connection_error:
                    self.on_connection_error(error_msg)
                
                if self.running:
                    print("🔄 Reconnecting in 3 seconds...")
                    await asyncio.sleep(3)
    
    async def _handle_gesture_event(self, data: dict):
        """Handle incoming gesture event data."""
        event_type = data.get('event_type', '')
        
        if event_type == 'presence_changed':
            # Human presence changed
            human_present = data.get('data', {}).get('human_present', False)
            confidence = data.get('data', {}).get('confidence', 0.0)
            
            print(f"👤 Human {'DETECTED' if human_present else 'LOST'} (conf: {confidence:.2f})")
            
            if self.on_human_detected:
                self.on_human_detected(human_present, confidence)
        
        elif event_type == 'gesture_detected':
            # Gesture detected!
            gesture_data = data.get('data', {})
            gesture_type = gesture_data.get('gesture_type', 'unknown')
            confidence = gesture_data.get('confidence', 0.0)
            hand = gesture_data.get('hand', 'unknown')
            
            print(f"🖐️  GESTURE: {gesture_type.upper()} | Hand: {hand} | Conf: {confidence:.2f}")
            
            if self.on_gesture_detected:
                self.on_gesture_detected(gesture_type, confidence, hand)
    
    def stop_gesture_stream(self):
        """Stop the gesture stream."""
        self.running = False
        print("🛑 Stopping gesture stream...")
    
    async def cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.session:
            await self.session.close()
        print("✅ Client cleaned up")

# Example usage and integration patterns
class YourApp:
    """
    Example of how to integrate gesture recognition into YOUR application.
    
    Replace this with your actual app logic!
    """
    
    def __init__(self):
        self.gesture_client = GestureClient()
        self.user_present = False
    
    async def initialize(self):
        """Initialize your app with gesture support."""
        await self.gesture_client.initialize()
        
        # Set up callbacks for gesture events
        self.gesture_client.on_human_detected = self.handle_human_presence
        self.gesture_client.on_gesture_detected = self.handle_gesture
        self.gesture_client.on_connection_error = self.handle_connection_error
        
        print("🚀 Your app initialized with gesture support!")
    
    def handle_human_presence(self, human_present: bool, confidence: float):
        """
        Handle human presence changes.
        
        This is called whenever someone enters or leaves the camera view.
        """
        self.user_present = human_present
        
        if human_present:
            print("🎉 USER ARRIVED - Starting your app features...")
            # Your code: Turn on lights, start music, activate voice assistant, etc.
            self.start_interactive_features()
        else:
            print("👋 USER LEFT - Pausing your app features...")
            # Your code: Turn off lights, pause music, deactivate voice assistant, etc.
            self.pause_interactive_features()
    
    def handle_gesture(self, gesture_type: str, confidence: float, hand: str):
        """
        Handle gesture detection.
        
        This is called whenever a gesture is detected.
        """
        if gesture_type == "hand_up" and confidence > 0.7:
            print("✋ HAND UP GESTURE - Executing your action!")
            
            # YOUR APP LOGIC HERE:
            # Examples:
            # - Stop voice assistant
            # - Pause music/video
            # - Take a photo
            # - Toggle smart home devices
            # - Send notification
            # - etc.
            
            self.execute_hand_up_action()
    
    def handle_connection_error(self, error_message: str):
        """Handle connection errors gracefully."""
        print(f"⚠️ Connection issue: {error_message}")
        # Your code: Log error, show user notification, try fallback, etc.
    
    # Your app-specific methods
    def start_interactive_features(self):
        """Start your app's interactive features when user is present."""
        print("   🔊 Activating voice commands...")
        print("   💡 Turning on smart lights...")
        print("   🎵 Starting background music...")
        # Add your actual code here
    
    def pause_interactive_features(self):
        """Pause your app's features when user leaves."""
        print("   🔇 Deactivating voice commands...")
        print("   💡 Dimming smart lights...")
        print("   🎵 Pausing background music...")
        # Add your actual code here
    
    def execute_hand_up_action(self):
        """Execute action when hand up gesture is detected."""
        print("   🛑 STOPPING current operation...")
        print("   📢 'Hand up detected - operation paused'")
        # Add your actual code here:
        # - self.voice_assistant.stop()
        # - self.music_player.pause()
        # - self.send_notification("Gesture detected")
        # - etc.
    
    async def run(self):
        """Run your app with gesture support."""
        try:
            # Start gesture monitoring
            await self.gesture_client.start_gesture_stream("your_app_001")
        except KeyboardInterrupt:
            print("\n🛑 App stopped by user")
        finally:
            await self.gesture_client.cleanup()

async def simple_example():
    """Simple example - just print gesture events."""
    print("🎯 Simple Gesture Recognition Example")
    print("=" * 50)
    print("Make a 'hand up' gesture to see it detected!")
    print("Press Ctrl+C to stop")
    print()
    
    client = GestureClient()
    
    try:
        await client.initialize()
        
        # Simple callbacks
        def on_human(present, confidence):
            status = "PRESENT" if present else "ABSENT"
            print(f"👤 Human: {status} (confidence: {confidence:.2f})")
        
        def on_gesture(gesture_type, confidence, hand):
            print(f"🖐️  Gesture: {gesture_type} with {hand} hand (confidence: {confidence:.2f})")
        
        client.on_human_detected = on_human
        client.on_gesture_detected = on_gesture
        
        await client.start_gesture_stream("simple_example")
    
    except KeyboardInterrupt:
        print("\n👋 Example stopped")
    finally:
        await client.cleanup()

async def complete_example():
    """Complete example with full app integration."""
    print("🎯 Complete App Integration Example")
    print("=" * 50)
    print("This shows how to integrate gesture recognition into your app")
    print("Press Ctrl+C to stop")
    print()
    
    app = YourApp()
    
    try:
        await app.initialize()
        await app.run()
    except KeyboardInterrupt:
        print("\n👋 App stopped")

async def test_presence_only():
    """Quick test - just check presence without streaming."""
    print("🧪 Quick Presence Test")
    print("=" * 30)
    
    client = GestureClient()
    
    try:
        await client.initialize()
        
        for i in range(5):
            result = await client.check_presence()
            status = "PRESENT" if result.get('human_present') else "ABSENT"
            print(f"Check {i+1}: Human {status}")
            await asyncio.sleep(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    print("Choose an example:")
    print("1. Simple gesture monitoring")
    print("2. Complete app integration")
    print("3. Quick presence test")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(simple_example())
    elif choice == "2":
        asyncio.run(complete_example())
    elif choice == "3":
        asyncio.run(test_presence_only())
    else:
        print("Running simple example...")
        asyncio.run(simple_example()) 