# Webcam Detection Package Usage Guide

## Installation

### Basic Installation (Core Detection Only)
```bash
pip install webcam-detection
```

### Full Installation (With Service Layer)
```bash
pip install webcam-detection[service]
```

### Development Installation
```bash
pip install webcam-detection[dev]
```

### All Features
```bash
pip install webcam-detection[all]
```

## Publishing to PyPI (For Package Authors)

### Prerequisites
```bash
# Install publishing tools
pip install build twine

# Create PyPI account at https://pypi.org/
# Create API token at https://pypi.org/manage/account/token/
```

### Publishing Steps

1. **Test Your Package Locally**:
   ```bash
   # Install in editable mode
   pip install -e .
   
   # Test it works
   python -c "from src import create_detector; print('Works!')"
   ```

2. **Build the Package**:
   ```bash
   # Clean previous builds
   rm -rf dist/ build/ *.egg-info/
   
   # Build distribution files
   python -m build
   ```

3. **Test on PyPI Test Server**:
   ```bash
   # Upload to test server first
   twine upload --repository testpypi dist/*
   
   # Test installation from test server
   pip install --index-url https://test.pypi.org/simple/ webcam-detection
   ```

4. **Publish to Real PyPI**:
   ```bash
   # Upload to real PyPI
   twine upload dist/*
   ```

5. **Now Anyone Can Install**:
   ```bash
   pip install webcam-detection
   ```

### Version Management
```python
# In setup.py, increment version for each release
version="2.0.1",  # Bug fixes
version="2.1.0",  # New features
version="3.0.0",  # Breaking changes
```

### GitHub Integration
```yaml
# .github/workflows/publish.yml
name: Publish to PyPI
on:
  release:
    types: [published]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

## Quick Start

### 1. Basic Human Detection
```python
from webcam_detection import create_detector
import cv2

# Create multimodal detector (default - recommended)
detector = create_detector('multimodal')

try:
    # Initialize detector
    detector.initialize()
    
    # Get camera frame
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    
    if ret:
        # Detect human in frame
        result = detector.detect(frame)
        print(f"Human present: {result.human_present}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Detection type: multimodal")
        
        # Access detailed results
        if result.landmarks:
            print(f"Pose landmarks: {len(result.landmarks.get('pose', []))}")
            print(f"Face landmarks: {len(result.landmarks.get('face', []))}")
    
    cap.release()
finally:
    detector.cleanup()
```

### 2. Production HTTP Service (Recommended)
```python
# Start the production service
import subprocess

# Option 1: Direct service execution
subprocess.run(["python", "webcam_http_service.py"])

# Option 2: Background service
import threading

def start_detection_service():
    subprocess.run(["python", "webcam_http_service.py"])

service_thread = threading.Thread(target=start_detection_service, daemon=True)
service_thread.start()
```

### 3. Speaker Verification Guard Clause (Production Pattern)
```python
import requests

def should_process_audio() -> bool:
    """Production-ready guard clause for speaker verification."""
    try:
        response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
        if response.status_code == 200:
            return response.json().get("human_present", False)
    except requests.RequestException:
        # Fail safe: process audio if service unavailable
        return True
    return False

# Usage in audio pipeline
def audio_processing_pipeline(audio_data):
    """Example audio processing with presence guard."""
    if should_process_audio():
        # Human present - continue with speaker verification
        return run_speaker_verification(audio_data)
    else:
        # No human - skip expensive processing
        return {"status": "skipped", "reason": "no_human_present"}

def run_speaker_verification(audio_data):
    """Placeholder for actual speaker verification."""
    # Your speaker verification code here
    return {"speaker_id": "user123", "confidence": 0.92}
```

### 4. Complete Service Integration
```python
import requests
import time
from typing import Dict, Any, Optional

class WebcamDetectionClient:
    """Client wrapper for webcam detection service."""
    
    def __init__(self, base_url: str = "http://localhost:8767"):
        self.base_url = base_url
        
    def is_human_present(self) -> bool:
        """Simple presence check."""
        try:
            response = requests.get(f"{self.base_url}/presence/simple", timeout=1.0)
            return response.json().get("human_present", False)
        except:
            return False
    
    def get_presence_details(self) -> Optional[Dict[str, Any]]:
        """Get detailed presence information."""
        try:
            response = requests.get(f"{self.base_url}/presence", timeout=2.0)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def get_service_health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=1.0)
            return response.json() if response.status_code == 200 else {"status": "error"}
        except:
            return {"status": "unavailable"}

# Usage examples
client = WebcamDetectionClient()

# Simple presence check
if client.is_human_present():
    print("Human detected!")

# Detailed presence information
details = client.get_presence_details()
if details:
    print(f"Confidence: {details.get('confidence', 0):.2f}")
    print(f"Last detection: {details.get('last_detection', 'unknown')}")

# Service health monitoring
health = client.get_service_health()
print(f"Service status: {health.get('status', 'unknown')}")
```

## API Reference

### Core Detection

#### `create_detector(detector_type='multimodal', config=None)`
Creates a human detection instance.

**Parameters:**
- `detector_type` (str): Type of detector ('multimodal', 'mediapipe', 'pose', 'pose_face')
- `config` (dict): Configuration parameters

**Returns:**
- `HumanDetector`: Detector instance

**Example:**
```python
detector = create_detector('multimodal', {
    'confidence_threshold': 0.7,
    'pose_weight': 0.6,
    'face_weight': 0.4
})
```

#### `HumanDetector.detect(frame)`
Performs human detection on provided frame.

**Parameters:**
- `frame` (numpy.ndarray): Camera frame in BGR format (from cv2.VideoCapture)

**Returns:**
- `DetectionResult`: Object with attributes:
  - `human_present` (bool): Whether human detected
  - `confidence` (float): Detection confidence (0.0-1.0)
  - `landmarks` (dict): Pose and face landmark data
  - `bounding_box` (tuple): Detection bounding box coordinates
  - `detection_info` (dict): Additional detection metadata

**Example:**
```python
import cv2
from webcam_detection import create_detector

detector = create_detector('multimodal')
detector.initialize()

cap = cv2.VideoCapture(0)
ret, frame = cap.read()

if ret:
    result = detector.detect(frame)
    print(f"Human present: {result.human_present}")
    print(f"Confidence: {result.confidence:.2f}")
    
    # Access landmark data
    if result.landmarks:
        pose_landmarks = result.landmarks.get('pose', [])
        face_landmarks = result.landmarks.get('face', [])
        print(f"Pose landmarks: {len(pose_landmarks)}")
        print(f"Face landmarks: {len(face_landmarks)}")

cap.release()
detector.cleanup()
```

### Service Layer

#### `DetectionServiceManager`
Manages multiple service types for detection system.

**Methods:**
- `add_http_service(config)`: Add HTTP API service
- `add_websocket_service(config)`: Add WebSocket service  
- `add_sse_service(config)`: Add Server-Sent Events service
- `start_all_services()`: Start all configured services
- `stop_all_services()`: Stop all running services
- `publish_detection_result(result)`: Publish detection to services

#### HTTP API Endpoints

When running the HTTP service (default port 8767):

- `GET /presence/simple`: Optimized for guard clauses
  ```json
  {"human_present": true}
  ```

- `GET /presence`: Complete presence information
  ```json
  {
    "human_present": true,
    "confidence": 0.85,
    "detection_count": 1247,
    "last_detection": "2024-01-01T12:00:00Z",
    "uptime_seconds": 3600.5
  }
  ```

- `GET /health`: Service health check
  ```json
  {
    "status": "healthy",
    "uptime_seconds": 3600.5,
    "total_detections": 1247,
    "service_version": "3.0.0"
  }
  ```

- `GET /statistics`: Performance metrics
- `GET /history`: Detection history (optional)

## Integration Patterns

### 1. Guard Clause Pattern (Recommended for Speaker Verification)

```python
class SpeakerVerificationGuard:
    def __init__(self, service_url="http://localhost:8767", threshold=0.5):
        self.service_url = service_url
        self.threshold = threshold
    
    def should_process_audio(self):
        try:
            response = requests.get(f"{self.service_url}/presence/simple", timeout=1.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("human_present", False) and data.get("confidence", 0) >= self.threshold
        except:
            return True  # Fail safe
        return False

# Usage in audio pipeline
guard = SpeakerVerificationGuard()
if guard.should_process_audio():
    result = perform_speaker_verification(audio_data)
```

### 2. Event-Driven Pattern (WebSocket)

```python
import asyncio
import websockets
import json

async def presence_monitor():
    uri = "ws://localhost:8765/ws/client_id"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to events
        await websocket.send(json.dumps({
            "type": "subscribe",
            "event_types": ["presence_changed", "detection_update"]
        }))
        
        # Listen for events
        async for message in websocket:
            event = json.loads(message)
            if event["event_type"] == "presence_changed":
                handle_presence_change(event["data"])

def handle_presence_change(data):
    if data["human_present"]:
        print("Person detected!")
        # Trigger actions
    else:
        print("Person left")
        # Cleanup actions
```

### 3. Polling Pattern (Simple HTTP)

```python
import time
import requests

class PresenceMonitor:
    def __init__(self, service_url="http://localhost:8767"):
        self.service_url = service_url
        self.last_state = None
    
    def check_presence_change(self):
        try:
            response = requests.get(f"{self.service_url}/presence")
            if response.status_code == 200:
                current_state = response.json()["human_present"]
                
                if self.last_state is not None and current_state != self.last_state:
                    self.on_presence_change(current_state)
                
                self.last_state = current_state
        except:
            pass
    
    def on_presence_change(self, human_present):
        if human_present:
            print("Person entered area")
        else:
            print("Person left area")

# Usage
monitor = PresenceMonitor()
while True:
    monitor.check_presence_change()
    time.sleep(1)
```

## Configuration

### Detection Configuration
```python
detection_config = {
    'detector_type': 'multimodal',
    'confidence_threshold': 0.7,
    'pose_weight': 0.6,
    'face_weight': 0.4,
    'model_complexity': 1,
    'min_detection_confidence': 0.5,
    'min_tracking_confidence': 0.5
}

detector = create_detector('multimodal', detection_config)
```

### Service Configuration
```python
from webcam_detection.service import HTTPServiceConfig, WebSocketServiceConfig

# HTTP Service
http_config = HTTPServiceConfig(
    host="localhost",
    port=8767,
    enable_history=True,
    history_limit=1000,
    cors_enabled=True
)

# WebSocket Service  
ws_config = WebSocketServiceConfig(
    host="localhost",
    port=8765,
    max_connections=100,
    heartbeat_interval=30.0
)
```

## Testing Your Integration

### Mock Detection for Testing
```python
import pytest
from unittest.mock import Mock, patch

@patch('webcam_detection.create_detector')
def test_my_integration(mock_create_detector):
    # Setup mock
    mock_detector = Mock()
    
    # Mock DetectionResult object
    from webcam_detection.detection.result import DetectionResult
    mock_result = DetectionResult(
        human_present=True,
        confidence=0.85,
        bounding_box=[100, 100, 200, 300],
        landmarks={'pose': [], 'face': []}
    )
    mock_detector.detect.return_value = mock_result
    mock_create_detector.return_value = mock_detector
    
    # Test your code
    result = my_function_using_detection()
    assert result is not None

# Mock HTTP service
@patch('requests.get')
def test_guard_clause(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"human_present": True, "confidence": 0.85}
    mock_get.return_value = mock_response
    
    guard = SpeakerVerificationGuard()
    assert guard.should_process_audio() is True
```

## Performance Considerations

### Response Times
- **HTTP API**: < 50ms for `/presence/simple`
- **WebSocket**: < 10ms for real-time events
- **Detection**: 15-30 FPS processing rate

### Resource Usage
- **Memory**: ~100MB base + ~50MB per service
- **CPU**: 10-25% during active detection
- **Network**: Minimal for local services

### Optimization Tips

1. **Use Simple Endpoint for Guard Clauses**:
   ```python
   # Fast - use for guard clauses
   response = requests.get("/presence/simple")
   
   # Slower - use for detailed analysis
   response = requests.get("/presence")
   ```

2. **Configure Appropriate Timeouts**:
   ```python
   # Quick timeout for guard clauses
   response = requests.get("/presence/simple", timeout=0.5)
   ```

3. **Use Connection Pooling**:
   ```python
   import requests
   
   session = requests.Session()
   # Reuse session for multiple requests
   response = session.get("/presence/simple")
   ```

## Deployment

### Docker Integration
```dockerfile
FROM python:3.11-slim

# Install package
RUN pip install webcam-detection[service]

# Copy your application
COPY . /app
WORKDIR /app

# Run your service
CMD ["python", "-m", "your_app"]
```

### Systemd Service
```ini
[Unit]
Description=Webcam Detection Service
After=network.target

[Service]
Type=simple
User=detection
WorkingDirectory=/opt/webcam-detection
ExecStart=/usr/local/bin/webcam-service --port 8767
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Variables
```bash
# Detection configuration
export WEBCAM_DETECTOR_TYPE=multimodal
export WEBCAM_CONFIDENCE_THRESHOLD=0.7

# Service configuration  
export WEBCAM_SERVICE_HOST=0.0.0.0
export WEBCAM_SERVICE_PORT=8767
export WEBCAM_ENABLE_HISTORY=true
```

## Troubleshooting

### Common Issues

1. **Camera Access Denied**:
   ```python
   # Check camera permissions
   import cv2
   cap = cv2.VideoCapture(0)
   if not cap.isOpened():
       print("Camera access denied")
   ```

2. **Service Connection Failed**:
   ```python
   # Check if service is running
   import requests
   try:
       response = requests.get("http://localhost:8767/health", timeout=1)
       print(f"Service status: {response.json()}")
   except:
       print("Service not available")
   ```

3. **High CPU Usage**:
   ```python
   # Reduce detection frequency
   detector_config = {
       'model_complexity': 0,  # Lower complexity
       'confidence_threshold': 0.8  # Higher threshold
   }
   ```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging
detector = create_detector('multimodal', {'debug': True})
```

## Examples Repository

See `docs/package_integration_examples.py` for complete working examples of:
- Speaker verification integration
- Home automation systems
- Real-time monitoring
- Testing patterns
- Configuration management

## Support

- **Documentation**: See README.md and ARCHITECTURE.md
- **Issues**: Report bugs via GitHub issues
- **Examples**: Check docs/ directory for integration patterns 