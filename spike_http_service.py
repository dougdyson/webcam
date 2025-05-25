#!/usr/bin/env python3
"""
HTTP Service Spike Test

This script demonstrates:
1. Starting the HTTP detection service
2. Simulating detection events
3. Testing client integration patterns (like speaker verification)
"""
import asyncio
import time
import threading
import requests
from datetime import datetime

# Import our service components
from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
from src.service.events import EventPublisher, ServiceEvent, EventType


class HTTPServiceSpike:
    """Spike test for HTTP service functionality."""
    
    def __init__(self):
        self.service = None
        self.event_publisher = None
        self.server_thread = None
        
    def setup_service(self):
        """Setup the HTTP service with event integration."""
        print("🚀 Setting up HTTP Detection Service...")
        
        # Create service configuration
        config = HTTPServiceConfig(
            host="localhost",
            port=8767,
            enable_history=True,
            history_limit=100
        )
        
        # Create service and event publisher
        self.service = HTTPDetectionService(config)
        self.event_publisher = EventPublisher()
        
        # Connect service to event publisher
        self.service.setup_detection_integration(self.event_publisher)
        
        print(f"✅ Service configured on http://{config.host}:{config.port}")
        
    def start_server_background(self):
        """Start the server in a background thread."""
        print("🌐 Starting HTTP server in background...")
        
        def run_server():
            import uvicorn
            uvicorn.run(
                self.service.app,
                host=self.service.config.host,
                port=self.service.config.port,
                log_level="info"
            )
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        print("✅ Server started successfully!")
        
    def simulate_detection_events(self):
        """Simulate some detection events to test the system."""
        print("\n🎯 Simulating detection events...")
        
        # Simulate human detected
        event1 = ServiceEvent(
            event_type=EventType.PRESENCE_CHANGED,
            data={
                "human_present": True,
                "confidence": 0.85,
                "detection_method": "multimodal"
            }
        )
        
        print("📡 Publishing: Human detected (confidence: 0.85)")
        self.event_publisher.publish(event1)
        time.sleep(1)
        
        # Simulate confidence update
        event2 = ServiceEvent(
            event_type=EventType.DETECTION_UPDATE,
            data={
                "human_present": True,
                "confidence": 0.92,
                "detection_method": "multimodal"
            }
        )
        
        print("📡 Publishing: Confidence updated (0.92)")
        self.event_publisher.publish(event2)
        time.sleep(1)
        
        # Simulate human left
        event3 = ServiceEvent(
            event_type=EventType.PRESENCE_CHANGED,
            data={
                "human_present": False,
                "confidence": 0.15,
                "detection_method": "multimodal"
            }
        )
        
        print("📡 Publishing: Human left (confidence: 0.15)")
        self.event_publisher.publish(event3)
        time.sleep(1)
        
    def test_client_integration(self):
        """Test client integration patterns."""
        print("\n🔌 Testing Client Integration Patterns...")
        
        base_url = f"http://{self.service.config.host}:{self.service.config.port}"
        
        # Test 1: Speaker Verification Guard Clause Pattern
        print("\n1️⃣ Testing Speaker Verification Guard Clause:")
        
        def should_process_audio() -> bool:
            """Guard clause for speaker verification."""
            try:
                response = requests.get(f"{base_url}/presence/simple", timeout=1.0)
                if response.status_code == 200:
                    return response.json().get("human_present", False)
            except requests.RequestException as e:
                print(f"   ⚠️  Service unavailable, failing safe: {e}")
                return True  # Fail safe: process audio if service unavailable
            return False
        
        # Test the guard clause
        should_process = should_process_audio()
        print(f"   📋 should_process_audio() = {should_process}")
        
        # Test 2: Full Status Check
        print("\n2️⃣ Testing Full Status Endpoint:")
        try:
            response = requests.get(f"{base_url}/presence")
            if response.status_code == 200:
                status = response.json()
                print(f"   📊 Full Status:")
                print(f"      • Human Present: {status['human_present']}")
                print(f"      • Confidence: {status['confidence']:.2f}")
                print(f"      • Detection Count: {status['detection_count']}")
                print(f"      • Uptime: {status['uptime_seconds']:.1f}s")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        # Test 3: Health Check
        print("\n3️⃣ Testing Health Endpoint:")
        try:
            response = requests.get(f"{base_url}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"   💚 Service Status: {health['status']}")
                print(f"   ⏱️  Uptime: {health['uptime']:.1f}s")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        # Test 4: Statistics
        print("\n4️⃣ Testing Statistics Endpoint:")
        try:
            response = requests.get(f"{base_url}/statistics")
            if response.status_code == 200:
                stats = response.json()
                print(f"   📈 Statistics:")
                print(f"      • Total Detections: {stats['total_detections']}")
                print(f"      • Current Presence: {stats['current_presence']}")
                print(f"      • Current Confidence: {stats['current_confidence']:.2f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        # Test 5: History (if enabled)
        print("\n5️⃣ Testing History Endpoint:")
        try:
            response = requests.get(f"{base_url}/history")
            if response.status_code == 200:
                history = response.json()
                print(f"   📚 History: {len(history['history'])} events")
                if history['history']:
                    latest = history['history'][-1]
                    print(f"      • Latest: {latest['event_type']} at {latest['timestamp']}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    def test_performance(self):
        """Test performance with rapid requests."""
        print("\n⚡ Testing Performance (50 rapid requests)...")
        
        base_url = f"http://{self.service.config.host}:{self.service.config.port}"
        
        start_time = time.time()
        successful_requests = 0
        
        for i in range(50):
            try:
                response = requests.get(f"{base_url}/presence/simple", timeout=0.5)
                if response.status_code == 200:
                    successful_requests += 1
            except:
                pass
        
        elapsed = time.time() - start_time
        requests_per_second = successful_requests / elapsed if elapsed > 0 else 0
        
        print(f"   📊 Results:")
        print(f"      • Successful requests: {successful_requests}/50")
        print(f"      • Time elapsed: {elapsed:.2f}s")
        print(f"      • Requests/second: {requests_per_second:.1f}")
        print(f"      • Average response time: {(elapsed/successful_requests)*1000:.1f}ms" if successful_requests > 0 else "      • No successful requests")
    
    def run_spike(self):
        """Run the complete spike test."""
        print("🧪 HTTP Service Spike Test Starting...\n")
        
        try:
            # Setup and start service
            self.setup_service()
            self.start_server_background()
            
            # Simulate some detection events
            self.simulate_detection_events()
            
            # Test client integration
            self.test_client_integration()
            
            # Test performance
            self.test_performance()
            
            print("\n✅ Spike test completed successfully!")
            print("\n🎯 Key Integration Points for Other Apps:")
            print("   • Guard Clause: GET /presence/simple")
            print("   • Full Status: GET /presence")
            print("   • Health Check: GET /health")
            print("   • Performance: GET /statistics")
            print("   • History: GET /history")
            
        except Exception as e:
            print(f"\n❌ Spike test failed: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point for spike test."""
    spike = HTTPServiceSpike()
    spike.run_spike()
    
    # Keep server running for manual testing
    print("\n🌐 Server is running at http://localhost:8767")
    print("   Try these URLs in your browser:")
    print("   • http://localhost:8767/presence/simple")
    print("   • http://localhost:8767/presence")
    print("   • http://localhost:8767/health")
    print("   • http://localhost:8767/statistics")
    print("   • http://localhost:8767/history")
    print("\n   Press Ctrl+C to stop the server...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down server...")


if __name__ == "__main__":
    main() 
 
 
 