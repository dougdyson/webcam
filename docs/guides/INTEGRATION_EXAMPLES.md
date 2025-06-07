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
        
        if status.gesture == "Open_Palm":
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
                                if gesture_event['data']['gesture_type'] == 'Open_Palm':
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
        await self.update_dashboard(data)
    
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

## Snapshot and AI Description Integration

### Basic Snapshot Capture with AI Descriptions
```python
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from src.camera.manager import CameraManager
from src.camera.config import CameraConfig
from src.detection import create_detector, DetectorConfig
from src.ollama.snapshot_buffer import SnapshotBuffer, Snapshot, SnapshotMetadata
from src.ollama.snapshot_trigger import SnapshotTrigger, SnapshotTriggerConfig
from src.ollama.description_service import DescriptionService
from src.ollama.client import OllamaClient, OllamaConfig

class AIDescriptionSystem:
    """System for capturing snapshots and generating AI descriptions."""
    
    def __init__(self, ollama_available: bool = True):
        # Setup camera and detection
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal', DetectorConfig())
        
        # Setup snapshot system
        self.snapshot_trigger = SnapshotTrigger(
            SnapshotTriggerConfig(
                min_confidence_threshold=0.7,
                debounce_frames=3,
                buffer_max_size=50
            )
        )
        
        # Setup AI descriptions (optional)
        self.description_service = None
        if ollama_available:
            try:
                ollama_client = OllamaClient(OllamaConfig())
                self.description_service = DescriptionService(ollama_client)
                print("✅ AI description service enabled")
            except Exception as e:
                print(f"⚠️ AI descriptions unavailable: {e}")
        
        # Statistics and state
        self.snapshots_captured = 0
        self.descriptions_generated = 0
        self.active_descriptions = {}  # Cache recent descriptions
        
    def initialize(self):
        """Initialize all components."""
        self.detector.initialize()
        print("🔧 AI Description System initialized")
    
    def cleanup(self):
        """Clean up resources."""
        self.camera.cleanup()
        self.detector.cleanup()
        print("🧹 AI Description System cleanup complete")
    
    def capture_snapshot_if_human_detected(self, frame: np.ndarray) -> Optional[Snapshot]:
        """Capture snapshot if human is detected with sufficient confidence."""
        detection_result = self.detector.detect(frame)
        
        snapshot_captured = self.snapshot_trigger.process_detection(frame, detection_result)
        
        if snapshot_captured:
            self.snapshots_captured += 1
            latest_snapshot = self.snapshot_trigger.get_latest_snapshot()
            print(f"📸 Snapshot captured (confidence: {detection_result.confidence:.2f})")
            return latest_snapshot
        
        return None
    
    async def generate_description_for_latest_snapshot(self) -> Optional[Dict]:
        """Generate AI description for the most recent snapshot."""
        if not self.description_service:
            return None
        
        latest_snapshot = self.snapshot_trigger.get_latest_snapshot()
        if not latest_snapshot:
            print("❌ No snapshot available for description")
            return None
        
        try:
            result = await self.description_service.describe_snapshot(latest_snapshot)
            
            if result.error is None:
                self.descriptions_generated += 1
                
                description_data = {
                    'description': result.description,
                    'confidence': result.confidence,
                    'timestamp': latest_snapshot.metadata.timestamp,
                    'processing_time': result.processing_time_ms / 1000,
                    'cached': result.cached,
                    'snapshot_confidence': latest_snapshot.metadata.confidence
                }
                
                # Cache the description
                snapshot_id = id(latest_snapshot)
                self.active_descriptions[snapshot_id] = description_data
                
                print(f"✨ Description: {result.description}")
                print(f"🎯 Confidence: {result.confidence:.2f}")
                print(f"⏱️ Processing time: {description_data['processing_time']:.1f}s")
                
                return description_data
                
            else:
                print(f"❌ Description failed: {result.error}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating description: {e}")
            return None
    
    def get_recent_snapshots_with_descriptions(self, minutes: int = 10) -> List[Dict]:
        """Get recent snapshots with their AI descriptions."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_snapshots = self.snapshot_trigger.buffer.get_snapshots_since(cutoff_time)
        
        results = []
        for snapshot in recent_snapshots:
            snapshot_id = id(snapshot)
            
            snapshot_data = {
                'timestamp': snapshot.metadata.timestamp,
                'confidence': snapshot.metadata.confidence,
                'human_present': snapshot.metadata.human_present,
                'frame_shape': snapshot.frame.shape,
                'description': self.active_descriptions.get(snapshot_id, {}).get('description'),
                'description_confidence': self.active_descriptions.get(snapshot_id, {}).get('confidence')
            }
            
            results.append(snapshot_data)
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get comprehensive system statistics."""
        buffer_stats = self.snapshot_trigger.buffer.get_statistics()
        
        return {
            'snapshots_captured': self.snapshots_captured,
            'descriptions_generated': self.descriptions_generated,
            'buffer_utilization': buffer_stats.get('utilization_percent', 0),
            'active_descriptions': len(self.active_descriptions),
            'buffer_size': buffer_stats.get('current_size', 0),
            'memory_usage_bytes': buffer_stats.get('total_memory_bytes', 0)
        }

# Usage Example
async def ai_description_demo():
    """Demo of AI description system."""
    system = AIDescriptionSystem()
    system.initialize()
    
    try:
        print("🎬 Starting AI description demo for 60 seconds...")
        print("👤 Move in front of camera to trigger snapshots and descriptions")
        
        start_time = datetime.now()
        last_description_time = None
        
        while (datetime.now() - start_time).total_seconds() < 60:
            # Get frame from camera
            frame = system.camera.get_frame()
            if frame is None:
                await asyncio.sleep(0.1)
                continue
            
            # Capture snapshot if human detected
            snapshot = system.capture_snapshot_if_human_detected(frame)
            
            # Generate description periodically (every 10 seconds)
            current_time = datetime.now()
            if (snapshot and 
                (last_description_time is None or 
                 (current_time - last_description_time).total_seconds() > 10)):
                
                description_data = await system.generate_description_for_latest_snapshot()
                if description_data:
                    last_description_time = current_time
            
            await asyncio.sleep(0.1)
        
        # Show final statistics
        stats = system.get_statistics()
        print(f"\n📊 Final Statistics:")
        print(f"   Snapshots captured: {stats['snapshots_captured']}")
        print(f"   Descriptions generated: {stats['descriptions_generated']}")
        print(f"   Buffer utilization: {stats['buffer_utilization']:.1f}%")
        
        # Show recent snapshots with descriptions
        recent_with_descriptions = system.get_recent_snapshots_with_descriptions(minutes=5)
        print(f"\n📋 Recent snapshots with descriptions ({len(recent_with_descriptions)}):")
        for i, item in enumerate(recent_with_descriptions[-3:]):  # Show last 3
            ts = item['timestamp'].strftime("%H:%M:%S")
            desc = item['description'] or "No description"
            conf = item['confidence']
            print(f"   {i+1}. {ts} (conf: {conf:.2f}) - {desc[:60]}...")
        
    finally:
        system.cleanup()

# Run the demo
# asyncio.run(ai_description_demo())
```

### Smart Scene Analysis for Home Automation
```python
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Callable

class SmartSceneAnalyzer:
    """Analyze scenes using AI descriptions to trigger smart home actions."""
    
    def __init__(self, ai_system: AIDescriptionSystem):
        self.ai_system = ai_system
        self.scene_triggers = {}  # Scene pattern -> callback mapping
        self.recent_scenes = []  # History of recent scene descriptions
        
    def register_scene_trigger(self, pattern: str, callback: Callable[[Dict], None], description: str = ""):
        """Register a callback for specific scene patterns."""
        self.scene_triggers[pattern] = {
            'callback': callback,
            'description': description,
            'matches': 0
        }
        print(f"📋 Registered scene trigger: {description or pattern}")
    
    async def analyze_and_trigger_automations(self, duration_minutes: int = 30):
        """Continuously analyze scenes and trigger appropriate automations."""
        print(f"🔍 Starting scene analysis for {duration_minutes} minutes...")
        
        start_time = datetime.now()
        last_analysis_time = None
        
        while (datetime.now() - start_time).total_seconds() < (duration_minutes * 60):
            # Get frame and capture snapshot if human detected
            frame = self.ai_system.camera.get_frame()
            if frame is None:
                await asyncio.sleep(0.5)
                continue
            
            snapshot = self.ai_system.capture_snapshot_if_human_detected(frame)
            
            # Analyze scene every 15 seconds if we have new snapshots
            current_time = datetime.now()
            if (snapshot and 
                (last_analysis_time is None or 
                 (current_time - last_analysis_time).total_seconds() > 15)):
                
                await self.analyze_current_scene()
                last_analysis_time = current_time
            
            await asyncio.sleep(0.5)
    
    async def analyze_current_scene(self):
        """Analyze current scene and trigger matching automations."""
        description_data = await self.ai_system.generate_description_for_latest_snapshot()
        
        if not description_data:
            return
        
        description = description_data['description'].lower()
        timestamp = description_data['timestamp']
        confidence = description_data['confidence']
        
        # Add to recent scenes history
        scene_record = {
            'description': description,
            'timestamp': timestamp,
            'confidence': confidence,
            'triggers_fired': []
        }
        
        # Check all registered triggers
        for pattern, trigger_info in self.scene_triggers.items():
            if re.search(pattern.lower(), description):
                print(f"🎯 Scene match: '{pattern}' in '{description[:50]}...'")
                
                # Fire the trigger
                try:
                    trigger_info['callback'](description_data)
                    trigger_info['matches'] += 1
                    scene_record['triggers_fired'].append(pattern)
                except Exception as e:
                    print(f"❌ Error in trigger '{pattern}': {e}")
        
        # Add to history and maintain size
        self.recent_scenes.append(scene_record)
        if len(self.recent_scenes) > 50:
            self.recent_scenes.pop(0)
    
    def get_scene_analysis_statistics(self) -> Dict:
        """Get statistics about scene analysis."""
        recent_triggers = [scene for scene in self.recent_scenes if scene['triggers_fired']]
        
        trigger_stats = {}
        for pattern, info in self.scene_triggers.items():
            trigger_stats[pattern] = {
                'matches': info['matches'],
                'description': info['description']
            }
        
        return {
            'total_scenes_analyzed': len(self.recent_scenes),
            'scenes_with_triggers': len(recent_triggers),
            'trigger_statistics': trigger_stats,
            'recent_scenes': self.recent_scenes[-5:]  # Last 5 scenes
        }

# Smart home automation callbacks
def kitchen_cooking_detected(scene_data: Dict):
    """Triggered when cooking activity is detected."""
    description = scene_data['description']
    confidence = scene_data['confidence']
    
    print(f"🍳 Cooking detected (confidence: {confidence:.2f})")
    print(f"   Scene: {description}")
    
    # Smart home actions:
    # - Turn on kitchen ventilation
    # - Set appropriate lighting
    # - Start cooking timer
    # - Enable cooking mode on smart devices
    
def reading_activity_detected(scene_data: Dict):
    """Triggered when reading activity is detected."""
    print(f"📚 Reading activity detected")
    print(f"   Scene: {scene_data['description']}")
    
    # Smart home actions:
    # - Dim ambient lighting
    # - Reduce distractions (lower music, pause notifications)
    # - Optimize reading lighting

def exercise_activity_detected(scene_data: Dict):
    """Triggered when exercise activity is detected."""
    print(f"💪 Exercise activity detected")
    print(f"   Scene: {scene_data['description']}")
    
    # Smart home actions:
    # - Increase ventilation
    # - Play workout music
    # - Monitor air quality
    # - Set exercise lighting

def working_at_desk_detected(scene_data: Dict):
    """Triggered when work activity is detected."""
    print(f"💻 Work activity detected")
    print(f"   Scene: {scene_data['description']}")
    
    # Smart home actions:
    # - Optimize desk lighting
    # - Enable focus mode (block distractions)
    # - Start productivity timer
    # - Adjust room temperature for comfort

# Usage Example
async def smart_scene_demo():
    """Demo of smart scene analysis system."""
    ai_system = AIDescriptionSystem()
    ai_system.initialize()
    
    scene_analyzer = SmartSceneAnalyzer(ai_system)
    
    # Register scene triggers with patterns
    scene_analyzer.register_scene_trigger(
        r'(cooking|kitchen|stove|pot|pan|cutting|chopping)',
        kitchen_cooking_detected,
        "Kitchen cooking activity"
    )
    
    scene_analyzer.register_scene_trigger(
        r'(reading|book|magazine|newspaper)',
        reading_activity_detected,
        "Reading activity"
    )
    
    scene_analyzer.register_scene_trigger(
        r'(exercise|workout|yoga|stretching|fitness)',
        exercise_activity_detected,
        "Exercise activity"
    )
    
    scene_analyzer.register_scene_trigger(
        r'(computer|laptop|desk|working|typing|office)',
        working_at_desk_detected,
        "Work at desk activity"
    )
    
    try:
        # Run scene analysis for 10 minutes
        await scene_analyzer.analyze_and_trigger_automations(duration_minutes=10)
        
        # Show final statistics
        stats = scene_analyzer.get_scene_analysis_statistics()
        print(f"\n📊 Scene Analysis Results:")
        print(f"   Total scenes analyzed: {stats['total_scenes_analyzed']}")
        print(f"   Scenes with triggers: {stats['scenes_with_triggers']}")
        
        print(f"\n🎯 Trigger Statistics:")
        for pattern, info in stats['trigger_statistics'].items():
            print(f"   {info['description']}: {info['matches']} matches")
        
    finally:
        ai_system.cleanup()

# Run the demo
# asyncio.run(smart_scene_demo())
```

### Snapshot Archive and Time-lapse Creation
```python
import cv2
import os
from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np

class SnapshotArchiveManager:
    """Manage snapshot archives and create time-lapse videos."""
    
    def __init__(self, ai_system: AIDescriptionSystem, archive_dir: str = "snapshot_archive"):
        self.ai_system = ai_system
        self.archive_dir = archive_dir
        self.ensure_archive_directory()
    
    def ensure_archive_directory(self):
        """Create archive directory if it doesn't exist."""
        os.makedirs(self.archive_dir, exist_ok=True)
        print(f"📁 Archive directory: {self.archive_dir}")
    
    def save_snapshot_to_disk(self, snapshot: Snapshot, description: Optional[str] = None) -> str:
        """Save snapshot to disk with metadata."""
        timestamp = snapshot.metadata.timestamp
        filename = f"snapshot_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(self.archive_dir, filename)
        
        # Save image
        cv2.imwrite(filepath, snapshot.frame)
        
        # Save metadata
        metadata_file = filepath.replace('.jpg', '_metadata.txt')
        with open(metadata_file, 'w') as f:
            f.write(f"Timestamp: {timestamp.isoformat()}\n")
            f.write(f"Confidence: {snapshot.metadata.confidence:.3f}\n")
            f.write(f"Human Present: {snapshot.metadata.human_present}\n")
            f.write(f"Detection Source: {snapshot.metadata.detection_source}\n")
            if description:
                f.write(f"AI Description: {description}\n")
        
        print(f"💾 Saved snapshot: {filename}")
        return filepath
    
    def save_recent_snapshots(self, minutes: int = 60) -> List[str]:
        """Save all snapshots from the last N minutes to disk."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_snapshots = self.ai_system.snapshot_trigger.buffer.get_snapshots_since(cutoff_time)
        
        saved_files = []
        for snapshot in recent_snapshots:
            filepath = self.save_snapshot_to_disk(snapshot)
            saved_files.append(filepath)
        
        print(f"💾 Saved {len(saved_files)} snapshots from last {minutes} minutes")
        return saved_files
    
    def create_timelapse_video(self, snapshot_files: List[str], output_filename: str = None, fps: int = 2) -> str:
        """Create time-lapse video from snapshot files."""
        if not snapshot_files:
            print("❌ No snapshot files provided for time-lapse")
            return None
        
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"timelapse_{timestamp}.mp4"
        
        output_path = os.path.join(self.archive_dir, output_filename)
        
        # Read first frame to get dimensions
        first_frame = cv2.imread(snapshot_files[0])
        if first_frame is None:
            print(f"❌ Cannot read first frame: {snapshot_files[0]}")
            return None
        
        height, width, _ = first_frame.shape
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        print(f"🎬 Creating time-lapse video with {len(snapshot_files)} frames at {fps} FPS...")
        
        for i, filepath in enumerate(snapshot_files):
            frame = cv2.imread(filepath)
            if frame is not None:
                # Add timestamp overlay
                timestamp_text = os.path.basename(filepath).replace('snapshot_', '').replace('.jpg', '')
                cv2.putText(frame, timestamp_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                video_writer.write(frame)
                
                if (i + 1) % 10 == 0:
                    print(f"   Processed {i + 1}/{len(snapshot_files)} frames")
        
        video_writer.release()
        print(f"✅ Time-lapse video created: {output_path}")
        return output_path
    
    async def automated_archive_session(self, duration_minutes: int = 30, save_interval_minutes: int = 5):
        """Run automated archiving session."""
        print(f"📸 Starting automated archive session for {duration_minutes} minutes")
        print(f"💾 Saving snapshots every {save_interval_minutes} minutes")
        
        start_time = datetime.now()
        last_save_time = start_time
        all_saved_files = []
        
        while (datetime.now() - start_time).total_seconds() < (duration_minutes * 60):
            # Capture snapshots
            frame = self.ai_system.camera.get_frame()
            if frame is not None:
                self.ai_system.capture_snapshot_if_human_detected(frame)
            
            # Save snapshots periodically
            current_time = datetime.now()
            if (current_time - last_save_time).total_seconds() >= (save_interval_minutes * 60):
                saved_files = self.save_recent_snapshots(minutes=save_interval_minutes)
                all_saved_files.extend(saved_files)
                last_save_time = current_time
            
            await asyncio.sleep(0.5)
        
        # Save any remaining snapshots
        final_saved = self.save_recent_snapshots(minutes=save_interval_minutes)
        all_saved_files.extend(final_saved)
        
        # Create time-lapse video
        if all_saved_files:
            video_path = self.create_timelapse_video(all_saved_files, fps=3)
            print(f"🎬 Time-lapse video: {video_path}")
        
        return all_saved_files

# Usage Example
async def archive_demo():
    """Demo of snapshot archiving and time-lapse creation."""
    ai_system = AIDescriptionSystem()
    ai_system.initialize()
    
    archive_manager = SnapshotArchiveManager(ai_system)
    
    try:
        # Run automated archiving for 5 minutes, saving every minute
        saved_files = await archive_manager.automated_archive_session(
            duration_minutes=5,
            save_interval_minutes=1
        )
        
        print(f"\n📊 Archive session complete:")
        print(f"   Total files saved: {len(saved_files)}")
        print(f"   Archive directory: {archive_manager.archive_dir}")
        
    finally:
        ai_system.cleanup()

# Run the demo
# asyncio.run(archive_demo())
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
            if gesture == 'Open_Palm' and self.security_level == SecurityLevel.ALERT:
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

For more integration examples and advanced patterns, see the source code examples in the `examples/` directory. 