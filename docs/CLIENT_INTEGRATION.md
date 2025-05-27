# Client Integration Guide

This guide shows how to integrate the webcam detection service into your Python applications.

## Quick Start

### 1. Start the Service

```bash
python webcam_enhanced_service.py
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
    "gesture_type": "thumbs_up",
    "confidence": 0.92,
    "hand": "right",
    "timestamp": "2024-01-15T10:30:45.123456"
}
```

**Supported Gestures:**
- `thumbs_up` - Thumbs up gesture
- `thumbs_down` - Thumbs down gesture  
- `peace` - Peace/victory sign
- `stop` - Open palm stop gesture
- `pointing` - Index finger pointing
- `fist` - Closed fist

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
    
    if gesture == "thumbs_up":
        turn_on_lights()
    elif gesture == "thumbs_down":
        turn_off_lights()
    elif gesture == "peace":
        toggle_music()
    elif gesture == "stop":
        emergency_stop()

client.add_gesture_callback(handle_gesture)
client.start_gesture_streaming()

# Monitor presence and gestures
while True:
    if client.is_human_present():
        print("Human present - gestures active")
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
        if event["gesture_type"] == "thumbs_up":
            app.activate()
        elif event["gesture_type"] == "stop":
            app.pause()
    
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

See `docs/simple_client_example.py` for a complete, runnable example that demonstrates all integration patterns.

## Advanced Usage

For more advanced integration patterns, see:
- `docs/client_examples.py` - Comprehensive client examples
- `docs/package_integration_examples.py` - Package-level integration
- `docs/service_patterns.py` - Service architecture patterns 