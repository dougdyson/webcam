#!/usr/bin/env python3
"""
Live Gesture Recognition Test
============================

Connect to the SSE endpoint and show real-time gesture events.
Raise your hand up at shoulder level with palm facing camera to test!
"""
import requests
import time
import json
import threading
from datetime import datetime

def test_sse_connection():
    """Test SSE connection for gesture events."""
    print("🔗 Connecting to gesture SSE endpoint...")
    
    try:
        response = requests.get(
            "http://localhost:8766/events/gestures/live_test",
            headers={"Accept": "text/event-stream"},
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Connected to gesture events!")
            print("✋ Raise your hand up at shoulder level with palm facing camera...")
            print("=" * 60)
            
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"📡 {datetime.now().strftime('%H:%M:%S')} | {line}")
                    
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:])  # Remove "data:" prefix
                            if data.get("event_type") == "gesture_detected":
                                print(f"🎉 GESTURE DETECTED: {data}")
                            elif data.get("event_type") == "gesture_lost":
                                print(f"👋 GESTURE LOST: {data}")
                        except json.JSONDecodeError:
                            pass
        else:
            print(f"❌ Failed to connect: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Stopping gesture test...")

def check_presence_status():
    """Check if human presence is detected."""
    try:
        response = requests.get("http://localhost:8767/presence", timeout=2)
        if response.status_code == 200:
            data = response.json()
            human_present = data.get("human_present", False)
            confidence = data.get("confidence", 0.0)
            
            if human_present:
                print(f"✅ Human detected (confidence: {confidence:.2f}) - gesture recognition should work!")
                return True
            else:
                print(f"🚫 No human detected - gesture recognition won't work")
                return False
        else:
            print(f"❌ Presence service error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot check presence: {e}")
        return False

def check_sse_service():
    """Check if SSE service is running."""
    try:
        response = requests.get("http://localhost:8766/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SSE service healthy: {data}")
            return True
        else:
            print(f"❌ SSE service error: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ SSE service not accessible: {e}")
        return False

def main():
    print("🎯 Live Gesture Recognition Test")
    print("=" * 60)
    
    # Check prerequisites
    print("🔍 Checking prerequisites...")
    
    if not check_presence_status():
        print("❌ Human presence not detected - make sure you're in front of the camera!")
        return
        
    if not check_sse_service():
        print("❌ SSE service not running - make sure enhanced service is started!")
        return
    
    print("\n🎯 All checks passed! Starting gesture monitoring...")
    print("📋 Instructions:")
    print("   1. Raise your hand up to shoulder level or higher")
    print("   2. Make sure your palm is facing the camera")
    print("   3. Hold the gesture for a few seconds")
    print("   4. Press Ctrl+C to stop")
    print()
    
    # Start SSE monitoring
    test_sse_connection()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n✅ Test stopped by user") 