#!/usr/bin/env python3
"""
Test gesture functionality - verify gestures are actually detected when they should be
"""

import requests
import time
import json
from datetime import datetime

def test_sse_connection():
    """Test if SSE service is responsive"""
    try:
        import aiohttp
        import asyncio
        
        async def check_sse():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:8766/events/gestures/test_client', timeout=5) as resp:
                        print(f"✅ SSE connection successful: {resp.status}")
                        # Read a few lines to see if data flows
                        count = 0
                        async for line in resp.content:
                            if line.startswith(b'data: '):
                                event_data = line[6:].decode().strip()
                                print(f"📡 SSE data received: {event_data}")
                                count += 1
                                if count >= 3:  # Just check first few events
                                    break
                        return True
            except Exception as e:
                print(f"❌ SSE connection failed: {e}")
                return False
        
        return asyncio.run(check_sse())
    except ImportError:
        print("❌ aiohttp not available for SSE test")
        return False

def test_http_api():
    """Test HTTP API responsiveness"""
    try:
        # Test presence endpoint
        response = requests.get("http://localhost:8767/presence/simple", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ HTTP API working: {data}")
            return True
        else:
            print(f"❌ HTTP API error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ HTTP API failed: {e}")
        return False

def monitor_gesture_events():
    """Monitor for gesture events in real-time"""
    print("\n🎯 GESTURE DETECTION TEST")
    print("=" * 50)
    print("👋 Please raise your hand with palm facing camera")
    print("⏱️  Monitoring for 30 seconds...")
    
    gesture_detected = False
    start_time = time.time()
    
    try:
        import aiohttp
        import asyncio
        
        async def monitor():
            nonlocal gesture_detected
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:8766/events/gestures/gesture_test') as resp:
                        print(f"📡 Connected to gesture stream")
                        
                        while time.time() - start_time < 30:  # Monitor for 30 seconds
                            try:
                                line = await asyncio.wait_for(resp.content.readline(), timeout=1.0)
                                if line.startswith(b'data: '):
                                    event_data = line[6:].decode().strip()
                                    if event_data and event_data != '[HEARTBEAT]':
                                        print(f"🎉 GESTURE EVENT: {event_data}")
                                        try:
                                            event_json = json.loads(event_data)
                                            if event_json.get('event_type') == 'gesture_detected':
                                                gesture_detected = True
                                                print(f"✅ Gesture detected with confidence: {event_json.get('data', {}).get('confidence', 'unknown')}")
                                        except json.JSONDecodeError:
                                            pass
                            except asyncio.TimeoutError:
                                # Print status every few seconds
                                elapsed = int(time.time() - start_time)
                                if elapsed % 5 == 0:
                                    print(f"⏱️  {elapsed}s elapsed, still monitoring...")
                                continue
                                
            except Exception as e:
                print(f"❌ Monitor error: {e}")
        
        asyncio.run(monitor())
        
    except ImportError:
        print("❌ Cannot monitor gestures - aiohttp not available")
        print("📝 Manual test: Check console output for gesture status")
        time.sleep(30)
    
    return gesture_detected

def main():
    print("🔧 GESTURE FUNCTIONALITY TEST")
    print("=" * 40)
    
    # Test 1: HTTP API
    print("\n1️⃣ Testing HTTP API...")
    http_ok = test_http_api()
    
    # Test 2: SSE Connection
    print("\n2️⃣ Testing SSE connection...")
    sse_ok = test_sse_connection()
    
    # Test 3: Actual gesture detection
    print("\n3️⃣ Testing gesture detection...")
    gesture_detected = monitor_gesture_events()
    
    # Results
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS:")
    print(f"HTTP API: {'✅ PASS' if http_ok else '❌ FAIL'}")
    print(f"SSE Connection: {'✅ PASS' if sse_ok else '❌ FAIL'}")
    print(f"Gesture Detection: {'✅ PASS' if gesture_detected else '❌ FAIL - NO GESTURES DETECTED'}")
    
    if not gesture_detected:
        print("\n🚨 POSSIBLE ISSUE: No gestures detected during test")
        print("💡 Try raising your hand clearly with palm facing camera")
        print("💡 Check if gesture detection thresholds are too strict")
    
    print("\n✅ Test complete")

if __name__ == "__main__":
    main() 