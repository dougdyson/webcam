#!/usr/bin/env python3
"""
Live Status Viewer - Real-time feedback for webcam detection
============================================================

Shows real-time status of:
- Human presence detection
- Gesture recognition  
- Service health

Run this to see what your webcam detection service is doing!
"""
import requests
import time
import json
from datetime import datetime
import signal
import sys

class LiveStatusViewer:
    def __init__(self):
        self.running = True
        self.last_presence = None
        self.last_gesture = None
        
    def signal_handler(self, signum, frame):
        print("\n\n🛑 Stopping status viewer...")
        self.running = False
        sys.exit(0)
        
    def clear_screen(self):
        print("\033[2J\033[H", end="")
        
    def get_presence_status(self):
        """Get current presence detection status."""
        try:
            response = requests.get("http://localhost:8767/presence", timeout=1.0)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            return {"error": str(e)}
        return None
        
    def get_service_health(self):
        """Get service health status."""
        try:
            http_health = requests.get("http://localhost:8767/health", timeout=1.0).json()
            sse_health = requests.get("http://localhost:8766/health", timeout=1.0).json()
            return {"http": http_health, "sse": sse_health}
        except Exception as e:
            return {"error": str(e)}
            
    def format_presence_status(self, status):
        """Format presence status for display."""
        if not status or "error" in status:
            return "❌ PRESENCE SERVICE DOWN"
            
        human_present = status.get("human_present", False)
        confidence = status.get("confidence", 0.0)
        detection_count = status.get("detection_count", 0)
        
        if human_present:
            confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
            return f"✅ HUMAN DETECTED | Confidence: {confidence:.2f} [{confidence_bar}] | Detections: {detection_count}"
        else:
            return f"🚫 NO HUMAN | Confidence: {confidence:.2f} | Detections: {detection_count}"
            
    def format_health_status(self, health):
        """Format service health for display."""
        if not health or "error" in health:
            return "❌ SERVICES DOWN"
            
        http_status = "✅" if health.get("http", {}).get("status") == "healthy" else "❌"
        sse_status = "✅" if health.get("sse", {}).get("status") == "healthy" else "❌"
        
        http_uptime = health.get("http", {}).get("uptime", 0)
        sse_connections = health.get("sse", {}).get("connections", 0)
        
        return f"HTTP: {http_status} (⏱️ {http_uptime:.1f}s) | SSE: {sse_status} (🔗 {sse_connections} clients)"
        
    def run(self):
        """Run the live status viewer."""
        signal.signal(signal.SIGINT, self.signal_handler)
        
        print("🚀 Starting Live Status Viewer...")
        print("Press Ctrl+C to stop")
        time.sleep(1)
        
        while self.running:
            try:
                self.clear_screen()
                
                # Header
                print("=" * 80)
                print("🎯 WEBCAM DETECTION - LIVE STATUS")
                print("=" * 80)
                print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print()
                
                # Get current status
                presence = self.get_presence_status()
                health = self.get_service_health()
                
                # Display presence status
                print("👤 HUMAN PRESENCE DETECTION:")
                print(f"   {self.format_presence_status(presence)}")
                print()
                
                # Display service health
                print("🏥 SERVICE HEALTH:")
                print(f"   {self.format_health_status(health)}")
                print()
                
                # Gesture status (placeholder for now)
                print("✋ GESTURE RECOGNITION:")
                print("   🔄 Monitoring for hand-up gestures...")
                print("   📡 Connect to: http://localhost:8766/events/gestures/client_id")
                print()
                
                # Instructions
                print("📋 QUICK TESTS:")
                print("   curl http://localhost:8767/presence/simple  # Quick presence check")
                print("   curl http://localhost:8766/health           # SSE service health")
                print()
                
                # Recent changes detection
                if presence and self.last_presence:
                    if presence.get("human_present") != self.last_presence.get("human_present"):
                        if presence.get("human_present"):
                            print("🎉 HUMAN ENTERED FRAME!")
                        else:
                            print("👋 HUMAN LEFT FRAME!")
                        print()
                
                self.last_presence = presence
                
                print("=" * 80)
                print("Press Ctrl+C to stop | Refreshing every 0.5s")
                
                time.sleep(0.5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(1)
                
        print("\n✅ Status viewer stopped.")

def main():
    viewer = LiveStatusViewer()
    viewer.run()

if __name__ == "__main__":
    main() 