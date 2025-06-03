#!/usr/bin/env python3
"""
External App Integration Client for Webcam Gesture Recognition

This shows how to integrate gesture recognition into your external application.
The webcam_service.py must be running for this to work.

Usage:
    python external_app_gesture_client.py
"""

import asyncio
import aiohttp
import json
import requests
import time
from datetime import datetime
from typing import Optional, Callable

class ExternalAppGestureClient:
    """
    Complete client for integrating webcam gesture recognition
    into your external application.
    """
    
    def __init__(self, 
                 presence_url: str = "http://localhost:8767",
                 gesture_sse_url: str = "http://localhost:8766"):
        self.presence_url = presence_url
        self.gesture_sse_url = gesture_sse_url
        self.gesture_callbacks = []
        self.is_running = False
        
    def add_gesture_callback(self, callback: Callable):
        """Add a callback function to be called when gestures are detected."""
        self.gesture_callbacks.append(callback)
    
    def check_human_presence(self) -> bool:
        """
        Simple HTTP check for human presence.
        Perfect for guard clauses in your app.
        """
        try:
            response = requests.get(f"{self.presence_url}/presence/simple", timeout=1.0)
            if response.status_code == 200:
                return response.json().get("human_present", False)
        except requests.RequestException as e:
            print(f"⚠️  Presence check failed: {e}")
            return True  # Fail safe
        return False
    
    def get_detailed_presence(self) -> dict:
        """Get complete presence information including confidence scores."""
        try:
            response = requests.get(f"{self.presence_url}/presence", timeout=1.0)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException as e:
            print(f"⚠️  Detailed presence check failed: {e}")
        return {}
    
    async def start_gesture_monitoring(self):
        """
        Start real-time gesture event monitoring via SSE.
        This runs in the background and calls your callbacks.
        """
        self.is_running = True
        client_id = f"external_app_{int(time.time())}"
        url = f"{self.gesture_sse_url}/events/gestures/{client_id}"
        
        print(f"🎯 Connecting to gesture stream: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        print("✅ Connected to gesture event stream!")
                        print("🖐️  Monitoring for hand up gestures...")
                        
                        async for line in response.content:
                            if not self.is_running:
                                break
                                
                            line = line.decode('utf-8').strip()
                            
                            if line.startswith('data: ') and not line.endswith('keepalive'):
                                try:
                                    data = line[6:]  # Remove 'data: ' prefix
                                    event = json.loads(data)
                                    await self._handle_gesture_event(event)
                                except json.JSONDecodeError:
                                    continue
                    else:
                        print(f"❌ Failed to connect to gesture stream: {response.status}")
                        
        except Exception as e:
            print(f"❌ Gesture monitoring error: {e}")
    
    async def _handle_gesture_event(self, event: dict):
        """Process incoming gesture events and call callbacks."""
        event_type = event.get('event_type')
        timestamp = event.get('timestamp')
        data = event.get('data', {})
        
        print(f"🎉 GESTURE EVENT: {event_type} at {timestamp}")
        print(f"   └─ Type: {data.get('gesture_type', 'unknown')}")
        print(f"   └─ Confidence: {data.get('confidence', 0):.2f}")
        print(f"   └─ Hand: {data.get('hand', 'unknown')}")
        
        # Call all registered callbacks
        for callback in self.gesture_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                print(f"⚠️  Callback error: {e}")
    
    def stop_monitoring(self):
        """Stop gesture monitoring."""
        self.is_running = False
        print("🛑 Stopping gesture monitoring...")

# Example usage and integration patterns
def example_voice_assistant_integration():
    """Example: Voice assistant that stops on hand up gesture."""
    
    client = ExternalAppGestureClient()
    
    # Voice assistant state
    voice_processing_active = False
    
    def on_gesture_detected(event):
        """Handle gesture events for voice control."""
        nonlocal voice_processing_active
        
        event_type = event.get('event_type')
        gesture_data = event.get('data', {})
        
        if event_type == 'gesture_detected' and gesture_data.get('gesture_type') == 'hand_up':
            if voice_processing_active:
                print("🛑 HAND UP DETECTED - STOPPING VOICE ASSISTANT")
                voice_processing_active = False
                # Your voice assistant stop code here
                stop_voice_processing()
            else:
                print("👋 HAND UP DETECTED - STARTING VOICE ASSISTANT")
                voice_processing_active = True
                # Your voice assistant start code here
                start_voice_processing()
                
        elif event_type == 'gesture_lost':
            print("🖐️  Hand down - voice assistant continues...")
    
    def stop_voice_processing():
        """Your voice assistant stop logic here."""
        print("   🔇 Voice processing stopped")
        print("   🎤 Microphone paused")
        print("   🤖 Assistant sleeping")
    
    def start_voice_processing():
        """Your voice assistant start logic here."""
        print("   🔊 Voice processing active")
        print("   🎤 Listening for commands")
        print("   🤖 Assistant ready")
    
    # Add the gesture callback
    client.add_gesture_callback(on_gesture_detected)
    
    return client

def example_smart_home_integration():
    """Example: Smart home automation triggered by gestures."""
    
    client = ExternalAppGestureClient()
    
    def on_smart_home_gesture(event):
        """Handle gestures for smart home control."""
        event_type = event.get('event_type')
        gesture_data = event.get('data', {})
        
        if event_type == 'gesture_detected' and gesture_data.get('gesture_type') == 'hand_up':
            confidence = gesture_data.get('confidence', 0)
            
            if confidence > 0.8:  # High confidence gestures only
                print("🏠 SMART HOME: Hand up detected - triggering automation")
                print("   💡 Turning on lights")
                print("   🎵 Starting music")
                print("   🌡️  Adjusting thermostat")
                
                # Your smart home API calls here
                # trigger_lighting_scene("active")
                # start_background_music()
                # set_temperature(72)
        
        elif event_type == 'gesture_lost':
            print("🏠 SMART HOME: Hand down - returning to normal")
            # trigger_lighting_scene("normal")
    
    client.add_gesture_callback(on_smart_home_gesture)
    return client

async def main():
    """Main demo showing both integration patterns."""
    print("🚀 External App Gesture Integration Demo")
    print("=" * 50)
    
    # Create client
    client = ExternalAppGestureClient()
    
    # Test basic presence check
    print("🔍 Testing human presence check...")
    is_present = client.check_human_presence()
    print(f"   Human present: {is_present}")
    
    if is_present:
        detailed = client.get_detailed_presence()
        print(f"   Confidence: {detailed.get('confidence', 'unknown')}")
        print(f"   Detection type: {detailed.get('detection_type', 'unknown')}")
    
    print("\n🎯 Setting up voice assistant integration...")
    voice_client = example_voice_assistant_integration()
    
    print("🏠 Setting up smart home integration...")
    smart_home_client = example_smart_home_integration()
    
    # Combine both clients (they can share the same gesture stream)
    client.gesture_callbacks.extend(voice_client.gesture_callbacks)
    client.gesture_callbacks.extend(smart_home_client.gesture_callbacks)
    
    print("\n✅ Ready! Monitoring for hand up gestures...")
    print("📋 Integration examples:")
    print("   • Voice Assistant: Hand up = start/stop voice processing")
    print("   • Smart Home: Hand up = trigger automation")
    print("   • Your App: Add your own gesture_callbacks!")
    print("\n🖐️  Raise your hand to test the integration!")
    print("   Press Ctrl+C to stop\n")
    
    try:
        # Start gesture monitoring
        await client.start_gesture_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Stopping demo...")
    finally:
        client.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main()) 