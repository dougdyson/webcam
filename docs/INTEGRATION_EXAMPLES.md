# Integration Examples

## Overview

This guide provides comprehensive examples for integrating Webcam Detection into various applications and systems.

## Speaker Verification Systems

### Basic Guard Clause Pattern
```python
import requests
from typing import Optional

class SpeakerVerificationSystem:
    def __init__(self, webcam_service_url: str = "http://localhost:8767"):
        self.webcam_url = webcam_service_url
        
    def should_process_audio(self) -> bool:
        """Guard clause: only process audio when human present."""
        try:
            response = requests.get(f"{self.webcam_url}/presence/simple", timeout=1.0)
            if response.status_code == 200:
                return response.json().get("human_present", False)
        except requests.RequestException:
            # Fail safe: process audio if service unavailable
            return True
        return False
    
    def process_audio_stream(self, audio_data: bytes) -> dict:
        """Process audio only when humans are present."""
        if self.should_process_audio():
            # Your speaker verification code here
            return self.run_speaker_verification(audio_data)
        else:
            # Skip processing, save resources
            return {"processed": False, "reason": "no_human"}
    
    def run_speaker_verification(self, audio_data: bytes) -> dict:
        """Your existing speaker verification implementation."""
        # Placeholder for your actual implementation
        return {"speaker_id": "user123", "confidence": 0.95}

# Usage
speaker_system = SpeakerVerificationSystem()
result = speaker_system.process_audio_stream(audio_data)
```

### Advanced Integration with Confidence Thresholds
```python
import requests
from dataclasses import dataclass
from typing import Optional

@dataclass
class DetectionStatus:
    human_present: bool
    confidence: float
    timestamp: str
    gesture: Optional[str] = None

class AdvancedSpeakerVerification:
    def __init__(self, webcam_url: str = "http://localhost:8767", min_confidence: float = 0.7):
        self.webcam_url = webcam_url
        self.min_confidence = min_confidence
        
    def get_detection_status(self) -> Optional[DetectionStatus]:
        """Get detailed detection status."""
        try:
            response = requests.get(f"{self.webcam_url}/presence", timeout=1.0)
            if response.status_code == 200:
                data = response.json()
                return DetectionStatus(
                    human_present=data.get("human_present", False),
                    confidence=data.get("confidence", 0.0),
                    timestamp=data.get("timestamp", ""),
                    gesture=data.get("gesture", {}).get("type")
                )
        except requests.RequestException:
            pass
        return None
    
    def should_process_with_confidence(self) -> tuple[bool, str]:
        """Enhanced guard clause with confidence checking."""
        status = self.get_detection_status()
        
        if status is None:
            return True, "service_unavailable"  # Fail safe
        
        if not status.human_present:
            return False, "no_human"
        
        if status.confidence < self.min_confidence:
            return False, f"low_confidence_{status.confidence:.2f}"
        
        if status.gesture == "stop":
            return False, "stop_gesture_detected"
            
        return True, f"processing_confidence_{status.confidence:.2f}"
    
    def process_audio_with_context(self, audio_data: bytes) -> dict:
        """Process audio with full context."""
        should_process, reason = self.should_process_with_confidence()
        
        if should_process:
            return {
                "result": self.run_speaker_verification(audio_data),
                "processed": True,
                "reason": reason
            }
        else:
            return {
                "processed": False,
                "reason": reason,
                "timestamp": self.get_detection_status().timestamp if self.get_detection_status() else None
            }

# Usage
advanced_system = AdvancedSpeakerVerification(min_confidence=0.75)
result = advanced_system.process_audio_with_context(audio_data)
print(f"Processed: {result['processed']}, Reason: {result['reason']}")
```

## Voice Assistant Integration

### Stop Gesture Control
```python
import asyncio
import aiohttp
import json
from typing import Callable

class VoiceAssistantController:
    def __init__(self, webcam_url: str = "http://localhost:8767", sse_url: str = "http://localhost:8766"):
        self.webcam_url = webcam_url
        self.sse_url = sse_url
        self.voice_active = False
        self.gesture_listener_task = None
        
    def check_human_presence(self) -> bool:
        """Check if human is present before starting voice assistant."""
        try:
            import requests
            response = requests.get(f"{self.webcam_url}/presence/simple", timeout=1.0)
            return response.json().get("human_present", False) if response.status_code == 200 else False
        except:
            return False
    
    async def start_voice_assistant_with_gesture_control(self, on_voice_start: Callable = None, on_voice_stop: Callable = None):
        """Start voice assistant with gesture-based stop control."""
        if not self.check_human_presence():
            print("No human detected - voice assistant not started")
            return
        
        # Start voice assistant
        self.voice_active = True
        print("🎙️ Voice assistant started - raise hand in stop gesture to pause")
        
        if on_voice_start:
            on_voice_start()
        
        # Start gesture listener
        self.gesture_listener_task = asyncio.create_task(
            self.listen_for_stop_gestures(on_voice_stop)
        )
        
        # Your voice assistant logic here
        await self.run_voice_assistant_loop()
    
    async def listen_for_stop_gestures(self, on_voice_stop: Callable = None):
        """Listen for stop gestures to pause voice assistant."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.sse_url}/events/gestures/voice_assistant") as resp:
                    async for line in resp.content:
                        if line.startswith(b'data: '):
                            event_data = line[6:].decode().strip()
                            if event_data and event_data != '[HEARTBEAT]':
                                gesture_event = json.loads(event_data)
                                if gesture_event['data']['gesture_type'] == 'stop':
                                    print("🖐️ Stop gesture detected - pausing voice assistant")
                                    self.voice_active = False
                                    if on_voice_stop:
                                        on_voice_stop()
                                    break
        except Exception as e:
            print(f"Error in gesture listener: {e}")
    
    async def run_voice_assistant_loop(self):
        """Main voice assistant processing loop."""
        while self.voice_active:
            # Your voice processing logic here
            print("🎤 Listening for voice commands...")
            await asyncio.sleep(1.0)  # Simulate processing
        
        print("🔇 Voice assistant paused")
    
    def stop(self):
        """Manually stop the voice assistant."""
        self.voice_active = False
        if self.gesture_listener_task:
            self.gesture_listener_task.cancel()

# Usage
async def main():
    controller = VoiceAssistantController()
    
    def on_start():
        print("Voice assistant started callback")
    
    def on_stop():
        print("Voice assistant stopped callback")
    
    await controller.start_voice_assistant_with_gesture_control(
        on_voice_start=on_start,
        on_voice_stop=on_stop
    )

# Run the voice assistant
asyncio.run(main())
```

## Smart Home Automation

### Presence-Based Automation
```python
import requests
import time
from typing import Dict, Any, Callable
from datetime import datetime, timedelta

class SmartHomeController:
    def __init__(self, webcam_url: str = "http://localhost:8767"):
        self.webcam_url = webcam_url
        self.last_presence_time = None
        self.automation_active = True
        self.presence_callbacks = {}
        
    def register_presence_callback(self, name: str, callback: Callable[[bool], None]):
        """Register callback for presence changes."""
        self.presence_callbacks[name] = callback
    
    def get_presence_status(self) -> Dict[str, Any]:
        """Get current presence status."""
        try:
            response = requests.get(f"{self.webcam_url}/presence", timeout=1.0)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return {"human_present": False, "confidence": 0.0}
    
    def monitor_presence_changes(self, polling_interval: int = 2):
        """Monitor for presence changes and trigger automations."""
        last_presence_state = None
        
        while self.automation_active:
            status = self.get_presence_status()
            current_presence = status.get("human_present", False)
            
            # Detect presence state change
            if current_presence != last_presence_state:
                print(f"🏠 Presence changed: {current_presence} (confidence: {status.get('confidence', 0):.2f})")
                
                # Update last presence time
                if current_presence:
                    self.last_presence_time = datetime.now()
                
                # Trigger callbacks
                for name, callback in self.presence_callbacks.items():
                    try:
                        callback(current_presence)
                    except Exception as e:
                        print(f"Error in {name} callback: {e}")
                
                last_presence_state = current_presence
            
            time.sleep(polling_interval)
    
    def get_time_since_last_presence(self) -> timedelta:
        """Get time since last human presence."""
        if self.last_presence_time:
            return datetime.now() - self.last_presence_time
        return timedelta(hours=24)  # Long time if never detected

# Smart home automation callbacks
def kitchen_automation(presence: bool):
    """Kitchen-specific automation."""
    if presence:
        print("🍳 Human in kitchen - turning on lights and starting cooking timer")
        # Your smart home integration here
        # smart_lights.turn_on("kitchen")
        # cooking_timer.start(default_duration=30)
    else:
        print("🚪 Human left kitchen - dimming lights")
        # smart_lights.dim("kitchen", level=20)

def security_automation(presence: bool):
    """Security system automation."""
    if presence:
        print("🔓 Human detected - disarming security system")
        # security_system.disarm()
    else:
        print("🔒 No human detected - arming security system in 5 minutes")
        # security_system.arm_delayed(minutes=5)

def energy_automation(presence: bool):
    """Energy management automation."""
    if presence:
        print("💡 Human present - normal energy mode")
        # energy_manager.set_mode("normal")
    else:
        print("🌱 No human - switching to energy saving mode")
        # energy_manager.set_mode("eco")

# Usage
controller = SmartHomeController()
controller.register_presence_callback("kitchen", kitchen_automation)
controller.register_presence_callback("security", security_automation)
controller.register_presence_callback("energy", energy_automation)

# Start monitoring (blocking)
controller.monitor_presence_changes(polling_interval=1)
```

## Real-time Dashboard Integration

### Web Dashboard with SSE Events
```python
import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List

class DashboardEventProcessor:
    def __init__(self, sse_url: str = "http://localhost:8766", http_url: str = "http://localhost:8767"):
        self.sse_url = sse_url
        self.http_url = http_url
        self.event_history = []
        self.current_status = {}
        
    async def connect_to_events(self):
        """Connect to real-time events and process them."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get initial status
                await self.fetch_initial_status(session)
                
                # Connect to SSE stream
                async with session.get(f"{self.sse_url}/events/gestures/dashboard") as resp:
                    print("📡 Connected to real-time events")
                    
                    async for line in resp.content:
                        if line.startswith(b'data: '):
                            event_data = line[6:].decode().strip()
                            if event_data and event_data != '[HEARTBEAT]':
                                await self.process_event(json.loads(event_data))
                                
        except Exception as e:
            print(f"Error connecting to events: {e}")
    
    async def fetch_initial_status(self, session):
        """Fetch initial system status."""
        try:
            async with session.get(f"{self.http_url}/presence") as resp:
                if resp.status == 200:
                    self.current_status = await resp.json()
                    print(f"📊 Initial status: {self.current_status}")
        except Exception as e:
            print(f"Error fetching initial status: {e}")
    
    async def process_event(self, event: Dict):
        """Process incoming events."""
        event_type = event.get('event_type')
        timestamp = event.get('timestamp')
        data = event.get('data', {})
        
        # Add to history
        self.event_history.append({
            'timestamp': timestamp,
            'type': event_type,
            'data': data
        })
        
        # Keep only last 100 events
        if len(self.event_history) > 100:
            self.event_history.pop(0)
        
        # Process different event types
        if event_type == 'gesture_detected':
            await self.handle_gesture_event(data)
        elif event_type == 'presence_changed':
            await self.handle_presence_event(data)
    
    async def handle_gesture_event(self, data: Dict):
        """Handle gesture detection events."""
        gesture_type = data.get('gesture_type')
        confidence = data.get('confidence', 0)
        
        print(f"🖐️ Gesture: {gesture_type} (confidence: {confidence:.2f})")
        
        # Update dashboard display
        await self.update_dashboard({
            'gesture': gesture_type,
            'gesture_confidence': confidence,
            'last_gesture_time': datetime.now().isoformat()
        })
    
    async def handle_presence_event(self, data: Dict):
        """Handle presence change events."""
        human_present = data.get('human_present', False)
        confidence = data.get('confidence', 0)
        
        print(f"👤 Presence: {human_present} (confidence: {confidence:.2f})")
        
        # Update current status
        self.current_status.update({
            'human_present': human_present,
            'confidence': confidence,
            'last_update': datetime.now().isoformat()
        })
        
        # Update dashboard
        await self.update_dashboard(self.current_status)
    
    async def update_dashboard(self, data: Dict):
        """Update dashboard display (implement your UI update logic)."""
        # This would integrate with your web framework (Flask, FastAPI, etc.)
        print(f"📊 Dashboard update: {data}")
        
        # Example: WebSocket broadcast to connected clients
        # await websocket_manager.broadcast(data)
    
    def get_statistics(self) -> Dict:
        """Get event statistics for dashboard."""
        total_events = len(self.event_history)
        gesture_events = len([e for e in self.event_history if e['type'] == 'gesture_detected'])
        presence_events = len([e for e in self.event_history if e['type'] == 'presence_changed'])
        
        return {
            'total_events': total_events,
            'gesture_events': gesture_events,
            'presence_events': presence_events,
            'current_status': self.current_status,
            'recent_events': self.event_history[-10:]  # Last 10 events
        }

# Usage
async def main():
    dashboard = DashboardEventProcessor()
    await dashboard.connect_to_events()

# Run dashboard processor
asyncio.run(main())
```

## Security System Integration

### Advanced Security Monitoring
```python
import requests
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List
from enum import Enum

class SecurityLevel(Enum):
    DISARMED = "disarmed"
    HOME = "home"
    AWAY = "away"
    ALERT = "alert"

class SecuritySystem:
    def __init__(self, webcam_url: str = "http://localhost:8767", sse_url: str = "http://localhost:8766"):
        self.webcam_url = webcam_url
        self.sse_url = sse_url
        self.security_level = SecurityLevel.DISARMED
        self.alerts = []
        self.authorized_users = set()  # Could integrate with face recognition
        
    def set_security_level(self, level: SecurityLevel):
        """Set security system level."""
        old_level = self.security_level
        self.security_level = level
        print(f"🔒 Security level changed: {old_level.value} → {level.value}")
        
    def check_presence_for_security(self) -> Dict:
        """Check presence with security context."""
        try:
            response = requests.get(f"{self.webcam_url}/presence", timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                
                # Add security assessment
                data['security_assessment'] = self.assess_security_threat(data)
                return data
        except requests.RequestException:
            return {"error": "Cannot connect to detection service"}
        
        return {"human_present": False, "confidence": 0.0}
    
    def assess_security_threat(self, detection_data: Dict) -> Dict:
        """Assess security threat level based on detection."""
        human_present = detection_data.get('human_present', False)
        confidence = detection_data.get('confidence', 0.0)
        
        threat_level = "none"
        
        if self.security_level == SecurityLevel.AWAY and human_present:
            if confidence > 0.8:
                threat_level = "high"  # High confidence human when system is away
            elif confidence > 0.5:
                threat_level = "medium"  # Medium confidence detection
            else:
                threat_level = "low"  # Low confidence, might be false positive
        elif self.security_level == SecurityLevel.HOME and human_present:
            threat_level = "monitor"  # Presence expected but monitor anyway
        
        return {
            'threat_level': threat_level,
            'security_mode': self.security_level.value,
            'confidence': confidence,
            'assessment_time': datetime.now().isoformat()
        }
    
    async def monitor_security_events(self):
        """Monitor for security-relevant events."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.sse_url}/events/gestures/security") as resp:
                    print("🛡️ Security monitoring active")
                    
                    async for line in resp.content:
                        if line.startswith(b'data: '):
                            event_data = line[6:].decode().strip()
                            if event_data and event_data != '[HEARTBEAT]':
                                await self.process_security_event(json.loads(event_data))
                                
        except Exception as e:
            print(f"Security monitoring error: {e}")
    
    async def process_security_event(self, event: Dict):
        """Process events for security implications."""
        event_type = event.get('event_type')
        data = event.get('data', {})
        
        if event_type == 'presence_changed':
            human_present = data.get('human_present', False)
            confidence = data.get('confidence', 0.0)
            
            if self.security_level == SecurityLevel.AWAY and human_present and confidence > 0.7:
                await self.trigger_security_alert("Unauthorized presence detected", data)
        
        elif event_type == 'gesture_detected':
            # Could implement gesture-based disarming
            gesture = data.get('gesture_type')
            if gesture == 'stop' and self.security_level == SecurityLevel.ALERT:
                print("🖐️ Stop gesture detected - could be disarm signal")
    
    async def trigger_security_alert(self, message: str, data: Dict):
        """Trigger security alert."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'data': data,
            'security_level': self.security_level.value
        }
        
        self.alerts.append(alert)
        print(f"🚨 SECURITY ALERT: {message}")
        
        # Here you would integrate with:
        # - Push notifications
        # - Email alerts
        # - Security company monitoring
        # - Camera recording triggers
        # - Alarm systems
    
    def get_security_status(self) -> Dict:
        """Get comprehensive security status."""
        presence_data = self.check_presence_for_security()
        
        return {
            'security_level': self.security_level.value,
            'presence_data': presence_data,
            'recent_alerts': self.alerts[-5:],  # Last 5 alerts
            'system_status': 'active',
            'last_check': datetime.now().isoformat()
        }

# Usage
async def main():
    security = SecuritySystem()
    
    # Set security mode
    security.set_security_level(SecurityLevel.AWAY)
    
    # Check current status
    status = security.get_security_status()
    print(f"Security status: {status}")
    
    # Start real-time monitoring
    await security.monitor_security_events()

# Run security monitoring
asyncio.run(main())
```

## Testing and Development Tools

### Mock Service for Testing
```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json
import asyncio
from datetime import datetime

app = FastAPI()

# Mock detection data
mock_presence_data = {
    "human_present": True,
    "confidence": 0.85,
    "timestamp": datetime.now().isoformat(),
    "detection_source": "mock_service"
}

@app.get("/presence/simple")
async def mock_presence_simple():
    """Mock simple presence endpoint."""
    return {"human_present": mock_presence_data["human_present"]}

@app.get("/presence")  
async def mock_presence():
    """Mock full presence endpoint."""
    return mock_presence_data

@app.get("/health")
async def mock_health():
    """Mock health endpoint."""
    return {"status": "healthy", "service": "mock"}

async def mock_gesture_events():
    """Mock gesture event stream."""
    while True:
        # Simulate gesture event every 10 seconds
        event_data = {
            "event_type": "gesture_detected",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "gesture_type": "stop",
                "confidence": 0.92,
                "hand": "right"
            }
        }
        
        yield f"data: {json.dumps(event_data)}\n\n"
        await asyncio.sleep(10)
        
        # Heartbeat
        yield "data: [HEARTBEAT]\n\n"
        await asyncio.sleep(5)

@app.get("/events/gestures/{client_id}")
async def mock_gesture_sse(client_id: str):
    """Mock gesture SSE endpoint."""
    return StreamingResponse(
        mock_gesture_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

# Run with: uvicorn mock_service:app --port 8767
```

For more integration examples and advanced patterns, see the source code examples in the `examples/` directory. 