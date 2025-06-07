# Client Integration Guide

This guide shows how to integrate the webcam detection service into your Python applications.

## Quick Start

### 1. Start the Service

```bash
python webcam_service.py
```

The service provides two endpoints:
- **HTTP API** (port 8767): Human presence detection
- **SSE Stream** (port 8766): Real-time gesture events

### 2. Install Client Dependencies

```bash
pip install requests sseclient-py
```

### 3. Basic Integration

```python
import requests

# Simple presence check
response = requests.get("http://localhost:8767/presence/simple")
if response.status_code == 200:
    human_present = response.json()["human_present"]
    print(f"Human detected: {human_present}")
```

## API Reference

### HTTP API (Port 8767)

#### GET /presence/simple
Simple boolean presence check.

**Response:**
```json
{
    "human_present": true,
    "confidence": 0.85
}
```

#### GET /presence
Detailed presence information.

**Response:**
```json
{
    "human_present": true,
    "confidence": 0.85,
    "detection_type": "multimodal",
    "timestamp": "2024-01-15T10:30:45.123456",
    "detection_count": 1234
}
```

#### GET /health
Service health check.

**Response:**
```json
{
    "status": "healthy",
    "uptime_seconds": 3600.5,
    "version": "1.0.0"
}
```

#### GET /statistics
Performance statistics.

**Response:**
```json
{
    "total_detections": 1234,
    "uptime_seconds": 3600.5,
    "average_fps": 15.2,
    "current_fps": 14.8
}
```

### SSE Stream (Port 8766)

#### GET /events/gestures/{client_id}
Real-time gesture events via Server-Sent Events.

**Event Format:**
```
event: gesture
data: {
    "gesture_type": "Open_Palm",
    "confidence": 0.92,
    "hand": "right",
    "timestamp": "2024-01-15T10:30:45.123456",
    "position": {
        "hand_x": 0.65,
        "hand_y": 0.25,
        "palm_z_component": 0.85
    },
    "palm_facing_camera": true
}
```

**Supported Gestures (MediaPipe Defaults):**
- `"Open_Palm"` - Open palm facing camera (universal stop/pause signal)
- `"Victory"` - Victory/Peace sign with two fingers extended
- `"Closed_Fist"` - Closed fist gesture
- `"Pointing_Up"` - Index finger pointing upward
- `"Thumb_Up"` - Thumbs up gesture
- `"Thumb_Down"` - Thumbs down gesture
- `"ILoveYou"` - ASL "I Love You" sign
- `"Unknown"` - Unrecognized gesture

### MediaPipe Gesture Detection Details

The current implementation supports **all 8 MediaPipe default gestures**, allowing developers to implement custom interpretation based on their use cases:

**Open Palm Gesture:**
- **Detection**: Open palm raised with palm facing the camera
- **Use Case**: Universal stop/pause signal for voice assistants, presentations, automation
- **MediaPipe Name**: `"Open_Palm"` (replaces custom `"stop"` interpretation)
- **Confidence**: Typically 0.7-0.95 for clear gestures
- **Client Interpretation**: Developers decide if this means stop, pause, or any other action

**Victory Gesture:**
- **Detection**: Two fingers extended (index + middle) in V shape
- **Use Case**: Peace sign, victory celebration, number two
- **MediaPipe Name**: `"Victory"` (replaces custom `"peace"` interpretation)
- **Client Interpretation**: Developers decide meaning (peace, victory, etc.)

**Developer Flexibility:**
The system now returns raw MediaPipe gesture names, allowing each client application to implement custom interpretation logic based on their specific needs.

## Snapshot Feature

The snapshot system captures and stores webcam frames when humans are detected, enabling powerful applications like AI-powered scene descriptions and time-based frame retrieval.

### Key Components

- **SnapshotBuffer**: Circular buffer storing recent frames with metadata
- **SnapshotTrigger**: Intelligent triggering based on detection confidence
- **Snapshot & SnapshotMetadata**: Frame data with timestamp and detection info

### Basic Snapshot Usage

```python
from src.ollama.snapshot_buffer import SnapshotBuffer, Snapshot, SnapshotMetadata
from src.ollama.snapshot_trigger import SnapshotTrigger, SnapshotTriggerConfig

# Setup snapshot system
snapshot_buffer = SnapshotBuffer(max_size=20)
snapshot_trigger = SnapshotTrigger(
    SnapshotTriggerConfig(
        min_confidence_threshold=0.7,
        debounce_frames=3,  # Prevent rapid triggering
        buffer_max_size=20
    )
)

# Process frame and potentially capture snapshot
def process_frame(frame, detection_result):
    # Process with snapshot trigger
    snapshot_captured = snapshot_trigger.process_detection(frame, detection_result)
    
    if snapshot_captured:
        print(f"📸 Snapshot captured! (confidence: {detection_result.confidence:.2f})")
        
        # Get latest snapshot for processing
        latest_snapshot = snapshot_trigger.get_latest_snapshot()
        return latest_snapshot
    
    return None
```

### AI Description Integration

```python
from src.ollama.description_service import DescriptionService
from src.ollama.client import OllamaClient, OllamaConfig

# Setup AI description service
ollama_client = OllamaClient(OllamaConfig())
description_service = DescriptionService(ollama_client)

async def generate_description_for_snapshot(snapshot):
    """Generate AI description for a captured snapshot."""
    try:
        result = await description_service.describe_snapshot(snapshot)
        
        if result.error is None:
            print(f"✨ Description: {result.description}")
            print(f"🎯 Confidence: {result.confidence:.2f}")
            print(f"💾 Cached: {'Yes' if result.cached else 'No'}")
            return result.description
        else:
            print(f"❌ Description failed: {result.error}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating description: {e}")
        return None
```

### Time-Based Snapshot Retrieval

```python
from datetime import datetime, timedelta

# Get snapshots from the last 30 seconds
cutoff_time = datetime.now() - timedelta(seconds=30)
recent_snapshots = snapshot_trigger.buffer.get_snapshots_since(cutoff_time)

print(f"Found {len(recent_snapshots)} snapshots in last 30 seconds")

# Process recent high-confidence snapshots
for snapshot in recent_snapshots:
    if snapshot.metadata.confidence > 0.8:
        timestamp = snapshot.metadata.timestamp.strftime("%H:%M:%S")
        print(f"High-confidence snapshot at {timestamp}: {snapshot.metadata.confidence:.2f}")
```

### Snapshot Buffer Statistics

```python
# Get buffer usage statistics
stats = snapshot_trigger.buffer.get_statistics()

print(f"Buffer utilization: {stats['utilization_percent']:.1f}%")
print(f"Current size: {stats['current_size']}/{stats['max_size']}")
print(f"Memory usage: {stats['total_memory_bytes']} bytes")

if stats['current_size'] > 0:
    oldest = stats['oldest_timestamp']
    newest = stats['newest_timestamp']
    time_span = (newest - oldest).total_seconds()
    print(f"Time span: {time_span:.1f} seconds")
```

### Complete Snapshot Client Example

```python
import asyncio
from datetime import datetime
from src.camera.manager import CameraManager
from src.camera.config import CameraConfig
from src.detection import create_detector, DetectorConfig
from src.ollama.snapshot_trigger import SnapshotTrigger, SnapshotTriggerConfig

class SnapshotClient:
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal', DetectorConfig())
        self.snapshot_trigger = SnapshotTrigger(
            SnapshotTriggerConfig(min_confidence_threshold=0.7)
        )
        
    def initialize(self):
        self.detector.initialize()
        
    def cleanup(self):
        self.camera.cleanup()
        self.detector.cleanup()
        
    async def capture_snapshots(self, duration=60):
        """Capture snapshots for specified duration."""
        print(f"📸 Capturing snapshots for {duration} seconds...")
        
        start_time = datetime.now()
        snapshots_captured = 0
        
        while (datetime.now() - start_time).total_seconds() < duration:
            # Get frame and run detection
            frame = self.camera.get_frame()
            if frame is None:
                await asyncio.sleep(0.1)
                continue
                
            detection_result = self.detector.detect(frame)
            
            # Process with snapshot trigger
            if self.snapshot_trigger.process_detection(frame, detection_result):
                snapshots_captured += 1
                print(f"📸 Snapshot {snapshots_captured} captured!")
                
            await asyncio.sleep(0.1)
        
        print(f"✅ Captured {snapshots_captured} snapshots")
        return snapshots_captured

# Usage
async def main():
    client = SnapshotClient()
    client.initialize()
    
    try:
        await client.capture_snapshots(30)  # Capture for 30 seconds
        
        # Get recent snapshots
        recent = client.snapshot_trigger.buffer.get_snapshots_since(
            datetime.now() - timedelta(seconds=60)
        )
        print(f"Buffer contains {len(recent)} recent snapshots")
        
    finally:
        client.cleanup()

asyncio.run(main())
```

## Client Examples

### Simple Client Class

Copy this class into your project for easy integration:

```python
import requests
import json
import threading
from sseclient import SSEClient

class SimpleWebcamClient:
    def __init__(self, client_id="my_app"):
        self.presence_url = "http://localhost:8767"
        self.gesture_url = "http://localhost:8766"
        self.client_id = client_id
        self.gesture_callbacks = []
        self.streaming = False
    
    def is_human_present(self):
        """Check if human is detected."""
        try:
            response = requests.get(f"{self.presence_url}/presence/simple", timeout=2.0)
            return response.json().get("human_present", False)
        except:
            return False
    
    def get_presence_details(self):
        """Get detailed presence information."""
        try:
            response = requests.get(f"{self.presence_url}/presence", timeout=2.0)
            return response.json()
        except:
            return None
    
    def add_gesture_callback(self, callback):
        """Add callback for gesture events."""
        self.gesture_callbacks.append(callback)
    
    def start_gesture_streaming(self):
        """Start listening for gesture events."""
        if self.streaming:
            return
        self.streaming = True
        thread = threading.Thread(target=self._gesture_worker, daemon=True)
        thread.start()
    
    def _gesture_worker(self):
        """Background worker for gesture streaming."""
        url = f"{self.gesture_url}/events/gestures/{self.client_id}"
        client = SSEClient(url)
        
        for event in client:
            if not self.streaming:
                break
            if event.event == 'gesture':
                gesture_data = json.loads(event.data)
                for callback in self.gesture_callbacks:
                    callback(gesture_data)
```

### Usage Examples

#### Basic Presence Detection

```python
client = SimpleWebcamClient()

if client.is_human_present():
    print("Human detected!")
    details = client.get_presence_details()
    print(f"Confidence: {details['confidence']:.2f}")
```

#### Gesture Event Handling

```python
client = SimpleWebcamClient()

def on_gesture(event):
    gesture = event["gesture_type"]
    confidence = event["confidence"]
    print(f"Gesture: {gesture} ({confidence:.2f})")

client.add_gesture_callback(on_gesture)
client.start_gesture_streaming()

# Your app logic here...
```

#### Smart Home Integration

```python
client = SimpleWebcamClient()

def handle_gesture(event):
    gesture = event["gesture_type"]
    confidence = event["confidence"]
    
    if confidence < 0.8:  # Only high-confidence gestures
        return
    
    # Custom interpretation based on MediaPipe defaults
    if gesture == "Open_Palm":
        # Open palm - interpreted as "stop all" for this smart home
        emergency_stop()
        pause_voice_bot()
        print("Open palm detected - stopping all devices")
    
    elif gesture == "Victory":
        # Victory sign - interpreted as "peace mode" for this smart home
        enable_peace_mode()  # Dim lights, soft music
        print("Victory gesture - enabling peace mode")
    
    elif gesture == "Thumb_Up":
        # Thumbs up - interpreted as "approve/continue"
        approve_current_action()
        print("Thumbs up - approving current action")
    
    elif gesture == "Thumb_Down":
        # Thumbs down - interpreted as "disapprove/cancel"
        cancel_current_action()
        print("Thumbs down - canceling current action")

client.add_gesture_callback(handle_gesture)
client.start_gesture_streaming()

# Monitor presence and gestures
while True:
    if client.is_human_present():
        print("Human present - gesture controls active")
    else:
        print("No human - waiting...")
    time.sleep(1)
```

#### Security System Integration

```python
client = SimpleWebcamClient()

def security_monitor():
    armed = True
    
    while armed:
        status = client.get_presence_details()
        
        if status and status["human_present"] and status["confidence"] > 0.7:
            print("🚨 INTRUSION DETECTED!")
            print(f"Confidence: {status['confidence']:.2f}")
            # Send alert, record video, etc.
            
        time.sleep(2)

# Run security monitoring
security_monitor()
```

## Integration Patterns

### 1. Guard Clause Pattern

Use presence detection as a guard clause before expensive operations:

```python
def process_audio():
    if not client.is_human_present():
        return  # Skip processing if no human
    
    # Expensive audio processing here
    perform_speech_recognition()
```

### 2. Event-Driven Pattern

React to gesture events in real-time:

```python
def setup_gesture_controls():
    def on_gesture(event):
        if event["gesture_type"] == "Open_Palm":
            # Hand up gesture - pause/stop signal
            app.pause()
            print("Hand up detected - pausing application")
    
    client.add_gesture_callback(on_gesture)
    client.start_gesture_streaming()
```

### 3. Polling Pattern

Periodically check presence status:

```python
def monitor_presence():
    while True:
        if client.is_human_present():
            app.keep_active()
        else:
            app.go_idle()
        time.sleep(5)
```

### 4. Async Pattern

For high-performance applications:

```python
import aiohttp
import asyncio

async def async_presence_check():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8767/presence") as response:
            data = await response.json()
            return data["human_present"]

# Usage
human_present = await async_presence_check()
```

## Error Handling

Always handle network errors gracefully:

```python
def safe_presence_check():
    try:
        return client.is_human_present()
    except requests.RequestException:
        # Service unavailable - decide on fallback behavior
        return True  # Fail-safe: assume human present
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
```

## Performance Considerations

### HTTP API
- **Latency**: ~10-50ms per request
- **Rate limit**: No built-in limits, but avoid excessive polling
- **Recommended polling**: Every 1-5 seconds for presence checks

### SSE Streaming
- **Latency**: ~5-20ms for gesture events
- **Connection**: Persistent connection, automatic reconnection
- **Resource usage**: Minimal - events only sent when gestures detected

### Best Practices

1. **Cache presence status** for 1-2 seconds to avoid excessive requests
2. **Use SSE for real-time** gesture events, HTTP for periodic presence checks
3. **Handle service unavailability** with appropriate fallback behavior
4. **Set reasonable timeouts** (1-3 seconds) for HTTP requests
5. **Use unique client IDs** for SSE connections to avoid conflicts

## Troubleshooting

### Service Not Responding
```python
# Check if service is running
try:
    response = requests.get("http://localhost:8767/health", timeout=2.0)
    if response.status_code == 200:
        print("Service is healthy")
    else:
        print("Service responding but unhealthy")
except requests.RequestException:
    print("Service not reachable - is it running?")
```

### SSE Connection Issues
```python
# Test SSE connection
try:
    from sseclient import SSEClient
    client = SSEClient("http://localhost:8766/events/gestures/test")
    for event in client:
        print(f"Received: {event}")
        break  # Just test connection
except Exception as e:
    print(f"SSE connection failed: {e}")
```

### Common Issues

1. **Port conflicts**: Ensure ports 8767 and 8766 are available
2. **Firewall**: Allow connections to localhost on these ports
3. **Dependencies**: Install `requests` and `sseclient-py`
4. **Service startup**: Wait a few seconds after starting the service

## Complete Example

See `docs/examples/simple_client_example.py` for a complete, runnable example that demonstrates all integration patterns.

## Advanced Usage

For more advanced integration patterns, see:
- `docs/examples/client_examples.py` - Comprehensive client examples
- `docs/examples/package_integration_examples.py` - Package-level integration
- `docs/examples/service_patterns.py` - Service architecture patterns 