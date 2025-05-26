#!/usr/bin/env python3
"""
Simple SSE Gesture Client - For Testing

The simplest possible client to test gesture events from the enhanced service.
Connects to SSE stream and prints everything it receives.
"""
import requests
import time
import sys
from datetime import datetime

def simple_gesture_client():
    """Simple SSE client to test gesture events."""
    url = "http://localhost:8766/events/gestures/simple_test_client"
    
    print("🎯 Simple Gesture Client")
    print("=" * 40)
    print(f"Connecting to: {url}")
    print("Waiting for gesture events...")
    print("Raise your hand to test!")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Connect to SSE stream with timeout and streaming
        response = requests.get(
            url,
            stream=True,
            timeout=30,
            headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache'
            }
        )
        
        print(f"✅ Connected! Status: {response.status_code}")
        print("📡 Listening for events...")
        print("-" * 40)
        
        # Read the stream line by line
        for line in response.iter_lines(decode_unicode=True):
            if line:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] {line}")
                
                # Check for gesture events specifically
                if "gesture_detected" in line:
                    print("🖐️ HAND UP DETECTED!")
                elif "gesture_lost" in line:
                    print("❌ GESTURE LOST!")
                elif "hand_up" in line:
                    print("🖐️ HAND UP EVENT!")
                    
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
    except KeyboardInterrupt:
        print("\n🛑 Client stopped by user")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = simple_gesture_client()
    sys.exit(0 if success else 1) 