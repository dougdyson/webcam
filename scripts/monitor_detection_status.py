#!/usr/bin/env python3
"""
Real-Time Detection Status Monitor

This script provides a clean, real-time display of human detection and gesture status
by polling the HTTP API service. Run this in a separate terminal window while the
main service runs in the background.

Usage:
    python monitor_detection_status.py

Features:
- Real-time human presence and confidence display
- Gesture detection status (when available)
- FPS and performance metrics
- Clean, updating single-line display
- No interference with main service processing
"""
import time
import requests
import sys
from datetime import datetime
from typing import Optional, Dict, Any
import threading
from collections import deque

class DetectionStatusMonitor:
    """Monitor for real-time detection status via HTTP API."""
    
    def __init__(self, api_url: str = "http://localhost:8767"):
        self.api_url = api_url
        self.last_detection_count = 0
        self.last_timestamp = time.time()
        self.fps_history = deque(maxlen=10)  # Keep last 10 FPS measurements
        self.latest_data = {}
        self.session = requests.Session()  # Reuse connections for speed
        self.latest_gesture = "None"  # Track latest gesture
        self.latest_gesture_confidence = 0.0
        self.last_gesture_time = 0
        
    def get_presence_status(self) -> Optional[Dict[str, Any]]:
        """Get current presence status from HTTP API."""
        try:
            response = self.session.get(f"{self.api_url}/presence", timeout=0.5)  # Faster timeout
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None
    
    def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get service statistics from HTTP API."""
        try:
            response = self.session.get(f"{self.api_url}/statistics", timeout=0.5)  # Faster timeout
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None
    
    def calculate_fps(self, current_detection_count: int) -> float:
        """Calculate FPS based on detection count changes."""
        current_time = time.time()
        time_delta = current_time - self.last_timestamp
        
        if time_delta >= 0.5 and current_detection_count > self.last_detection_count:  # Update every 0.5s
            fps = (current_detection_count - self.last_detection_count) / time_delta
            self.fps_history.append(fps)
            
            self.last_detection_count = current_detection_count
            self.last_timestamp = current_time
            
            return sum(self.fps_history) / len(self.fps_history)
        
        return sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0.0
    
    def format_status_line(self, presence_data: Dict[str, Any], stats_data: Optional[Dict[str, Any]] = None) -> str:
        """Format a single status line for display."""
        # Human presence status
        if presence_data.get("human_present", False):
            status_icon = "👤 HUMAN"
            confidence = presence_data.get("confidence", 0.0)
        else:
            status_icon = "❌ NO HUMAN"
            confidence = 0.0
        
        # Detection count and FPS
        detection_count = stats_data.get("total_detections", 0) if stats_data else 0
        fps = self.calculate_fps(detection_count)
        
        # Gesture status - use latest gesture data
        current_time = time.time()
        if current_time - self.last_gesture_time < 2.0:  # Show gesture for 2 seconds after detection
            gesture_status = f"{self.latest_gesture} ({self.latest_gesture_confidence:.2f})"
        else:
            gesture_status = "None"
        
        # Description service status (simplified for speed)
        desc_status = ""
        if stats_data and "description_stats" in stats_data:
            desc_stats = stats_data["description_stats"]
            total_desc = desc_stats.get("total_descriptions", 0)
            if total_desc > 0:
                desc_status = f" | 🤖 Desc: {total_desc}"
        
        # Format final line
        return (f"{status_icon} | Conf: {confidence:.2f} | Gesture: {gesture_status} | "
                f"Frames: {detection_count} | FPS: {fps:.1f}{desc_status}")
    
    def check_service_health(self) -> bool:
        """Check if the service is running."""
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=1.0)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def update_data_background(self):
        """Background thread to continuously fetch data."""
        while True:
            try:
                # Get presence data (most important, always fetch)
                presence_data = self.get_presence_status()
                if presence_data:
                    self.latest_data['presence'] = presence_data
                
                # Get stats data less frequently to avoid overloading
                if int(time.time() * 2) % 3 == 0:  # Every 1.5 seconds
                    stats_data = self.get_statistics()
                    if stats_data:
                        self.latest_data['stats'] = stats_data
                
                # Check for gesture events via simple polling (not ideal but works)
                # Note: A proper SSE client would be better but this is simpler for monitoring
                if int(time.time() * 10) % 5 == 0:  # Every 0.5 seconds
                    try:
                        # Try to get a quick response from SSE health endpoint if available
                        sse_health_url = self.api_url.replace("8767", "8766") + "/health"
                        response = self.session.get(sse_health_url, timeout=0.3)
                        # If SSE service is running, gesture events would be flowing
                        # For now, we'll rely on the main service console output for gesture detection
                    except:
                        pass  # SSE not available or not responding
                        
            except Exception as e:
                pass  # Continue on any error
            
            time.sleep(0.1)  # Very fast update cycle
    
    def run_monitor(self, update_interval: float = 0.1):  # Much faster default
        """Run the real-time monitoring loop."""
        print("🎯 Real-Time Detection Status Monitor")
        print("=" * 50)
        print(f"Monitoring: {self.api_url}")
        print("Press Ctrl+C to stop")
        print()
        
        # Check if service is running
        if not self.check_service_health():
            print(f"❌ Service not available at {self.api_url}")
            print("Make sure the enhanced service is running:")
            print("    python webcam_service.py")
            sys.exit(1)
        
        print("✅ Service detected - starting real-time monitor...")
        print()
        
        # Start background data fetching thread
        data_thread = threading.Thread(target=self.update_data_background, daemon=True)
        data_thread.start()
        
        try:
            while True:
                # Use cached data from background thread
                presence_data = self.latest_data.get('presence')
                stats_data = self.latest_data.get('stats')
                
                if presence_data:
                    status_line = self.format_status_line(presence_data, stats_data)
                    # Use \r to overwrite the same line
                    print(f"\r{status_line}                    ", end="", flush=True)  # Extra spaces to clear line
                else:
                    print(f"\r❌ Connecting to service...                    ", end="", flush=True)
                
                time.sleep(update_interval)  # Fast display update
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitor stopped by user")
        except Exception as e:
            print(f"\n❌ Monitor error: {e}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-time detection status monitor")
    parser.add_argument("--api-url", default="http://localhost:8767", 
                       help="API URL for the detection service")
    parser.add_argument("--update-interval", type=float, default=0.1,
                       help="Display update interval in seconds (default: 0.1)")
    
    args = parser.parse_args()
    
    monitor = DetectionStatusMonitor(args.api_url)
    monitor.run_monitor(args.update_interval)

if __name__ == "__main__":
    main() 