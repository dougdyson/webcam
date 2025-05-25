#!/usr/bin/env python3
"""
Presence Simulation Script

This script simulates human presence changes by directly publishing
events to the HTTP service while client integration examples are running.
"""
import time
import requests
from src.service.events import EventPublisher, ServiceEvent, EventType

def simulate_human_presence():
    """Simulate a realistic presence detection scenario."""
    
    # Create event publisher (this would normally be connected to the detection pipeline)
    event_publisher = EventPublisher()
    
    # We need to get access to the running HTTP service's event publisher
    # For simulation, we'll use HTTP requests to check current state
    base_url = "http://localhost:8767"
    
    print("🎭 Human Presence Simulation Starting...")
    print("   This will simulate detection events that would come from the camera")
    print("   Run this while the client integration examples are running!\n")
    
    scenarios = [
        {"description": "Human walks into view", "present": True, "confidence": 0.75},
        {"description": "Human settles at desk", "present": True, "confidence": 0.92},
        {"description": "Human working (high confidence)", "present": True, "confidence": 0.98},
        {"description": "Human steps away briefly", "present": False, "confidence": 0.25},
        {"description": "Human returns", "present": True, "confidence": 0.88},
        {"description": "Human leaves for extended period", "present": False, "confidence": 0.05},
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"📋 Scenario {i}: {scenario['description']}")
        print(f"   👤 Human Present: {scenario['present']}")
        print(f"   📊 Confidence: {scenario['confidence']}")
        
        # Check if service is still running
        try:
            response = requests.get(f"{base_url}/health", timeout=1.0)
            if response.status_code != 200:
                print("   ❌ HTTP service not responding")
                break
        except:
            print("   ❌ HTTP service not available")
            break
        
        # Check current status
        try:
            response = requests.get(f"{base_url}/presence", timeout=1.0)
            if response.status_code == 200:
                current = response.json()
                print(f"   📈 Current stats: {current['detection_count']} detections, uptime: {current['uptime_seconds']:.1f}s")
        except:
            pass
            
        print(f"   ⏰ Waiting 10 seconds before next scenario...\n")
        time.sleep(10)
    
    print("🎭 Simulation complete!")
    print("   Note: This simulation shows the HTTP endpoints, but doesn't inject events")
    print("   In real usage, detection events would come from the camera pipeline")

def simple_presence_toggle():
    """Simple toggle between human present/absent for testing."""
    base_url = "http://localhost:8767"
    
    print("🔄 Simple Presence Toggle Test")
    print("   This will check the current service status every 5 seconds")
    print("   Run the spike_http_service.py script to inject real events\n")
    
    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"🔍 Cycle {cycle} - Checking service status...")
            
            # Health check
            try:
                response = requests.get(f"{base_url}/health", timeout=1.0)
                if response.status_code == 200:
                    health = response.json()
                    print(f"   💚 Service: {health['status']} (uptime: {health['uptime']:.1f}s)")
                else:
                    print(f"   ⚠️  Service returned status: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Health check failed: {e}")
                break
            
            # Presence check
            try:
                response = requests.get(f"{base_url}/presence/simple", timeout=1.0)
                if response.status_code == 200:
                    presence = response.json()
                    human_present = presence.get("human_present", False)
                    print(f"   👤 Human Present: {human_present}")
                    
                    if human_present:
                        print("   🎯 Speaker verification would PROCESS audio")
                    else:
                        print("   ⏭️  Speaker verification would SKIP audio processing")
                else:
                    print(f"   ⚠️  Presence check returned status: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Presence check failed: {e}")
            
            # Full status
            try:
                response = requests.get(f"{base_url}/presence", timeout=1.0)
                if response.status_code == 200:
                    status = response.json()
                    print(f"   📊 Confidence: {status['confidence']:.2f}, Count: {status['detection_count']}")
            except:
                pass
            
            print(f"   ⏰ Waiting 5 seconds...\n")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n👋 Stopped after {cycle} cycles")

def main():
    """Main entry point."""
    print("🧪 Detection Service - Presence Simulation Tools\n")
    
    print("Choose a simulation mode:")
    print("1. Realistic presence scenarios (descriptive)")
    print("2. Simple status monitoring (recommended)")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        simulate_human_presence()
    elif choice == "2":
        simple_presence_toggle()
    else:
        print("👋 Goodbye!")

if __name__ == "__main__":
    main() 
 
 