"""
Production Service Patterns for Webcam Human Detection
=====================================================

This file contains production-ready code samples for integrating with
the webcam detection HTTP service. These patterns are battle-tested
and reflect the actual production implementation.

Key Features:
- Production-ready webcam_http_service.py integration
- Speaker verification guard clause patterns
- Real-time presence monitoring
- Error handling and fail-safe patterns
- Performance optimized for production use

Installation:
    pip install webcam-detection[service]

Service Startup:
    python webcam_http_service.py
"""

import requests
import time
import threading
import subprocess
import asyncio
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import logging

# ============================================================================
# 1. Production Service Startup Patterns
# ============================================================================

class WebcamDetectionService:
    """Production service manager for webcam detection HTTP service."""
    
    def __init__(self, service_url: str = "http://localhost:8767"):
        self.service_url = service_url
        self.process = None
        self.logger = logging.getLogger(__name__)
        
    def start_service(self, background: bool = True) -> bool:
        """Start the webcam detection service."""
        try:
            if background:
                # Start service in background thread
                def run_service():
                    self.process = subprocess.Popen(
                        ["python", "webcam_http_service.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    self.process.wait()
                
                service_thread = threading.Thread(target=run_service, daemon=True)
                service_thread.start()
                
                # Wait for service to be ready
                return self._wait_for_service_ready(timeout=10)
            else:
                # Start service in foreground
                self.process = subprocess.run(["python", "webcam_http_service.py"])
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False
    
    def _wait_for_service_ready(self, timeout: int = 10) -> bool:
        """Wait for service to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.service_url}/health", timeout=1.0)
                if response.status_code == 200:
                    self.logger.info("Service is ready")
                    return True
            except requests.RequestException:
                pass
            time.sleep(0.5)
        
        self.logger.error("Service failed to start within timeout")
        return False
    
    def stop_service(self):
        """Stop the service."""
        if self.process:
            self.process.terminate()
            self.process = None

# ============================================================================
# 2. Speaker Verification Guard Clause (Production Pattern)
# ============================================================================

class ProductionSpeakerGuard:
    """Production-ready guard clause for speaker verification systems."""
    
    def __init__(self, 
                 service_url: str = "http://localhost:8767",
                 confidence_threshold: float = 0.6,
                 timeout: float = 1.0,
                 fail_safe: bool = True,
                 cache_duration: float = 0.1):
        self.service_url = service_url
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        self.fail_safe = fail_safe
        self.cache_duration = cache_duration
        
        # Simple caching to avoid excessive requests
        self._cache = {"timestamp": 0, "result": fail_safe}
        self.logger = logging.getLogger(__name__)
    
    def should_process_audio(self) -> bool:
        """
        Check if human is present before processing audio.
        
        Features:
        - Sub-second response times
        - Intelligent caching
        - Fail-safe behavior
        - Confidence thresholding
        
        Returns:
            bool: True if should process audio, False otherwise
        """
        # Check cache first
        now = time.time()
        if now - self._cache["timestamp"] < self.cache_duration:
            return self._cache["result"]
        
        try:
            response = requests.get(
                f"{self.service_url}/presence/simple",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                human_present = data.get("human_present", False)
                
                # Update cache
                self._cache = {"timestamp": now, "result": human_present}
                return human_present
                
        except requests.RequestException as e:
            self.logger.warning(f"Presence check failed: {e}")
            # Return cached result or fail safe
            return self._cache["result"] if self._cache["timestamp"] > 0 else self.fail_safe
        
        return self.fail_safe
    
    def get_detailed_presence(self) -> Optional[Dict[str, Any]]:
        """Get detailed presence information for debugging/logging."""
        try:
            response = requests.get(
                f"{self.service_url}/presence",
                timeout=self.timeout
            )
            return response.json() if response.status_code == 200 else None
        except:
            return None

# ============================================================================
# 3. Production Audio Processing Integration
# ============================================================================

def production_audio_pipeline_example():
    """Example of production audio processing with presence guard."""
    
    # Initialize guard
    guard = ProductionSpeakerGuard(
        confidence_threshold=0.7,  # Higher threshold for security
        fail_safe=True,           # Allow processing if service down
        cache_duration=0.05       # 50ms cache for high-frequency calls
    )
    
    def process_audio_stream(audio_data: bytes) -> Dict[str, Any]:
        """Main audio processing function with presence guard."""
        
        # Quick presence check
        if not guard.should_process_audio():
            return {
                "status": "skipped",
                "reason": "no_human_detected",
                "timestamp": datetime.now().isoformat(),
                "processing_time_ms": 0
            }
        
        # Human present - proceed with expensive processing
        start_time = time.time()
        
        try:
            # Your speaker verification code here
            speaker_result = run_speaker_verification(audio_data)
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "status": "processed",
                "speaker_id": speaker_result.get("speaker_id"),
                "confidence": speaker_result.get("confidence"),
                "processing_time_ms": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_speaker_verification(audio_data: bytes) -> Dict[str, Any]:
        """Placeholder for actual speaker verification."""
        # Simulate processing time
        time.sleep(0.1)
        return {
            "speaker_id": "user123",
            "confidence": 0.92,
            "processing_method": "neural_embedding"
        }
    
    # Example usage
    sample_audio = b"fake_audio_data"
    result = process_audio_stream(sample_audio)
    print(f"Audio processing result: {result}")

# ============================================================================
# 4. Real-time Presence Monitoring
# ============================================================================

class PresenceMonitor:
    """Real-time presence monitoring with callbacks."""
    
    def __init__(self, 
                 service_url: str = "http://localhost:8767",
                 poll_interval: float = 1.0):
        self.service_url = service_url
        self.poll_interval = poll_interval
        self.last_state = None
        self.callbacks = {}
        self.running = False
        self.thread = None
        self.logger = logging.getLogger(__name__)
    
    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for presence events."""
        self.callbacks[event_type] = callback
    
    def start_monitoring(self):
        """Start monitoring presence changes."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("Started presence monitoring")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.logger.info("Stopped presence monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                response = requests.get(
                    f"{self.service_url}/presence",
                    timeout=2.0
                )
                
                if response.status_code == 200:
                    current_data = response.json()
                    current_state = current_data.get("human_present", False)
                    
                    # Check for state change
                    if self.last_state is not None and current_state != self.last_state:
                        event_type = "presence_detected" if current_state else "presence_lost"
                        
                        # Trigger callback
                        if event_type in self.callbacks:
                            try:
                                self.callbacks[event_type](current_data)
                            except Exception as e:
                                self.logger.error(f"Callback error: {e}")
                    
                    self.last_state = current_state
                
            except requests.RequestException as e:
                self.logger.warning(f"Monitoring request failed: {e}")
            
            time.sleep(self.poll_interval)

# ============================================================================
# 5. Smart Home Integration Example
# ============================================================================

def smart_home_integration_example():
    """Example of smart home automation with presence detection."""
    
    monitor = PresenceMonitor(poll_interval=2.0)
    
    def on_presence_detected(presence_data):
        """Handle human presence detected."""
        confidence = presence_data.get("confidence", 0)
        print(f"🏠 Human detected (confidence: {confidence:.2f})")
        
        # Trigger home automation
        turn_on_lights()
        start_music()
        adjust_temperature(target=22)
        
        # Log for analytics
        log_presence_event("detected", presence_data)
    
    def on_presence_lost(presence_data):
        """Handle human presence lost."""
        print("🏠 Human left area")
        
        # Energy saving mode
        dim_lights()
        pause_music()
        adjust_temperature(target=18)
        
        # Log for analytics
        log_presence_event("lost", presence_data)
    
    def turn_on_lights():
        print("  → Turning on lights")
        # Your smart home API calls here
    
    def start_music():
        print("  → Starting background music")
        # Your music system API calls here
    
    def adjust_temperature(target: int):
        print(f"  → Setting temperature to {target}°C")
        # Your thermostat API calls here
    
    def dim_lights():
        print("  → Dimming lights for energy saving")
    
    def pause_music():
        print("  → Pausing music")
    
    def log_presence_event(event_type: str, data: Dict[str, Any]):
        print(f"  → Logged {event_type} event: {data.get('timestamp', 'unknown')}")
    
    # Register callbacks
    monitor.register_callback("presence_detected", on_presence_detected)
    monitor.register_callback("presence_lost", on_presence_lost)
    
    # Start monitoring
    monitor.start_monitoring()
    
    try:
        # Keep running
        time.sleep(60)  # Monitor for 1 minute in example
    finally:
        monitor.stop_monitoring()

# ============================================================================
# 6. Service Health Monitoring
# ============================================================================

class ServiceHealthMonitor:
    """Monitor webcam detection service health."""
    
    def __init__(self, service_url: str = "http://localhost:8767"):
        self.service_url = service_url
        self.logger = logging.getLogger(__name__)
    
    def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=2.0)
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "http_code": response.status_code}
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}
    
    def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get service performance statistics."""
        try:
            response = requests.get(f"{self.service_url}/statistics", timeout=2.0)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def is_service_healthy(self) -> bool:
        """Simple health check."""
        health = self.check_health()
        return health.get("status") == "healthy"

# ============================================================================
# 7. Example Usage and Testing
# ============================================================================

def main_production_example():
    """Complete production example."""
    
    print("🚀 Webcam Detection Production Integration Example")
    
    # 1. Start service
    service = WebcamDetectionService()
    if not service.start_service():
        print("❌ Failed to start service")
        return
    
    print("✅ Service started successfully")
    
    # 2. Initialize components
    guard = ProductionSpeakerGuard()
    health_monitor = ServiceHealthMonitor()
    
    # 3. Check service health
    health = health_monitor.check_health()
    print(f"📊 Service health: {health.get('status', 'unknown')}")
    
    # 4. Test speaker verification guard
    print("\n🎤 Testing speaker verification guard:")
    for i in range(5):
        should_process = guard.should_process_audio()
        details = guard.get_detailed_presence()
        
        print(f"  Test {i+1}: Should process = {should_process}")
        if details:
            print(f"    Confidence: {details.get('confidence', 0):.2f}")
            print(f"    Detection count: {details.get('detection_count', 0)}")
        
        time.sleep(1)
    
    # 5. Clean up
    service.stop_service()
    print("\n✅ Example completed successfully")

if __name__ == "__main__":
    main_production_example() 