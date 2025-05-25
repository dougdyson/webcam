# Webcam Detection

[![PyPI version](https://badge.fury.io/py/webcam-detection.svg)](https://badge.fury.io/py/webcam-detection)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Advanced multi-modal human detection system with service integration for real-time applications.**

Webcam Detection provides a comprehensive, local-processing human presence detection system using computer vision. Perfect for guard clauses in speaker verification, smart home automation, security systems, and any application requiring reliable human presence detection.

> 📁 **New to the project?** See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for a quick navigation guide.

## 🚀 Key Features

- **🎯 Multi-Modal Detection**: Combines MediaPipe pose and face detection for 3x extended range
- **⚡ Real-Time Processing**: Low-latency detection with 15-30 FPS performance  
- **🏠 Local Processing**: No cloud dependencies, all computation happens locally
- **🛡️ Guard Clause Ready**: Perfect for speaker verification and audio processing systems
- **🔧 Service Integration**: HTTP/WebSocket/SSE APIs for easy integration
- **📐 Extended Range**: Works from desk distance to kitchen/cooking scenarios
- **🧪 Production Ready**: 320 comprehensive tests, battle-tested architecture
- **⚙️ Configurable**: Extensive configuration options for different scenarios

## 📦 Installation

### Basic Installation
```bash
pip install webcam-detection
```

### With Service Features
```bash
pip install webcam-detection[service]
```

### System Requirements
- Python 3.10+
- Webcam/camera access
- OpenCV compatible system (Windows/macOS/Linux)

## 🎯 Quick Start

### Basic Human Detection
```python
from webcam_detection import create_detector
from webcam_detection.camera import CameraManager
from webcam_detection.camera.config import CameraConfig

# Setup
camera = CameraManager(CameraConfig())
detector = create_detector('multimodal')
detector.initialize()

# Detect
frame = camera.get_frame()
if frame is not None:
    result = detector.detect(frame)
    print(f"Human present: {result.human_present}")
    print(f"Confidence: {result.confidence:.2f}")

# Cleanup
detector.cleanup()
camera.cleanup()
```

### Speaker Verification Guard Clause
```python
from webcam_detection import create_detector
from webcam_detection.camera import CameraManager, CameraConfig

class AudioProcessor:
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal')
        self.detector.initialize()
    
    def should_process_audio(self):
        """Guard clause: only process if human present."""
        try:
            frame = self.camera.get_frame()
            if frame is not None:
                result = self.detector.detect(frame)
                return result.human_present and result.confidence > 0.6
            return False
        except:
            return True  # Fail safe
    
    def process_audio_stream(self, audio_data):
        """Process audio only when humans are present."""
        if self.should_process_audio():
            # Your speaker verification code here
            return self.run_speaker_verification(audio_data)
        else:
            # Skip processing, save resources
            return {"processed": False, "reason": "no_human"}
```

### HTTP Service (Production Ready)

Start the webcam detection HTTP service:

```bash
conda activate webcam
python webcam_http_service.py
```

The service provides REST endpoints for human presence detection:
- **Primary**: `GET http://localhost:8767/presence/simple` → `{"human_present": true/false}`
- **Full status**: `GET http://localhost:8767/presence` → Complete detection details
- **Health check**: `GET http://localhost:8767/health` → Service status
- **Performance**: `GET http://localhost:8767/statistics` → Metrics
- **History**: `GET http://localhost:8767/history` → Detection history (optional)

### Integration Examples

#### Guard Clause Pattern (Speaker Verification, etc.)
```python
import requests

def should_process_audio() -> bool:
    """Check if human is present before processing audio."""
    try:
        response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
        return response.json().get("human_present", False)
    except:
        return True  # Fail safe
```

#### Smart Home Integration
```python
import requests

def trigger_automation():
    """Trigger smart home actions based on presence."""
    response = requests.get("http://localhost:8767/presence/simple")
    if response.json().get("human_present"):
        # Human detected - turn on lights, start music, etc.
        activate_home_automation()
```

## 🔧 Detection Types

### MultiModal (Recommended)
- **Best For**: All scenarios, extended range detection
- **Range**: Desk distance to kitchen distance (3x extended)
- **Technology**: Combined pose + face detection with intelligent fusion
- **Performance**: Optimal balance of accuracy and range

```python
detector = create_detector('multimodal')
```

### MediaPipe (Legacy)
- **Best For**: Close-range scenarios, desk work
- **Range**: Close to medium distance
- **Technology**: Traditional pose-only detection
- **Performance**: Fast processing, good for close interaction

```python
detector = create_detector('mediapipe')
```

## 🛠️ Service Layer

Run the service layer for easy integration with other applications:

```bash
python -m webcam_detection.service --enable-http --enable-websocket
```

### Available Endpoints

#### HTTP API (Port 8767)
- `GET /presence/simple` - Simple boolean presence check
- `GET /presence/detailed` - Full detection information
- `GET /health` - Service health check
- `GET /statistics` - Performance metrics

#### WebSocket (Port 8765)
Real-time presence updates for interactive applications.

#### Server-Sent Events (Port 8766)
HTTP-based streaming for web dashboards and MCP-compatible services.

## 📊 Performance

- **Initialization**: < 3.5 seconds for multi-modal detector
- **Frame Rate**: 15-30 FPS processing capability
- **Latency**: < 100ms from capture to detection result
- **Range**: 3x detection range compared to pose-only systems
- **Memory**: Bounded queues, efficient resource management

## 🏗️ Architecture

```
Video Capture → Frame Queue → Multi-Modal Detection → Presence Decision → Service API
     ↓              ↓              ↓                     ↓                    ↓
   Thread        Async Queue    MediaPipe            Debounce             HTTP/WS
                               (Pose + Face)         Filtering             WebSocket
```

### Key Components
- **Camera Manager**: Hardware abstraction and frame capture
- **Multi-Modal Detector**: Advanced pose + face fusion
- **Presence Filter**: Debouncing and smoothing logic
- **Service Layer**: HTTP/WebSocket/SSE APIs
- **Factory Pattern**: Extensible detector registration

## 🎛️ Configuration

### Camera Settings
```yaml
# config/camera_profiles.yaml
default:
  device_id: 0
  width: 640
  height: 480
  fps: 30
```

### Detection Parameters
```yaml
# config/detection_config.yaml
multimodal:
  model_complexity: 1
  min_detection_confidence: 0.5
  pose_weight: 0.6
  face_weight: 0.4
  
presence_filter:
  smoothing_window: 5
  min_confidence_threshold: 0.7
  debounce_frames: 3
```

## 🎯 Use Cases

### Speaker Verification Systems
Perfect guard clause for audio processing - only run expensive speaker verification when humans are present.

### Smart Home Automation
Trigger cooking timers, lighting, or music when someone enters the kitchen area.

### Security Systems
Human presence detection for surveillance and access control systems.

### Interactive Applications
Real-time presence detection for kiosks, digital signage, and interactive displays.

### Development Tools
Add human presence context to development tools and monitoring systems.

## 🧪 Testing

The package includes 264+ comprehensive tests covering:
- Unit tests for all components
- Integration tests for complete workflows
- Multi-modal detection validation
- Performance and stress testing
- Error recovery scenarios

```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

## 🤝 Integration Examples

### Requirements.txt
```
webcam-detection>=2.0.0
# or with service features
webcam-detection[service]>=2.0.0
```

### Docker
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install package
RUN pip install webcam-detection[service]

# Your application code
COPY . /app
WORKDIR /app
```

## 📖 Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System design and components
- [Package Usage](docs/PACKAGE_USAGE.md) - Detailed integration patterns
- [Service Patterns](docs/service_patterns.py) - Service layer examples
- [Configuration Samples](docs/configuration_samples.py) - Setup examples

## 🔄 Changelog

### v2.0.0 - Multi-Modal Enhancement
- ✨ Multi-modal detection with 3x extended range
- ✨ Factory pattern for extensible detector architecture
- ✨ Service layer with HTTP/WebSocket/SSE APIs
- ✨ Comprehensive test suite (264+ tests)
- ✨ Production-ready architecture

### v1.0.0 - Initial Release
- Basic MediaPipe pose detection
- Camera management system
- CLI interface

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🌟 Why Choose Webcam Detection?

- **🎯 Proven**: Battle-tested with 320 comprehensive tests
- **⚡ Fast**: Optimized for real-time performance
- **🔒 Private**: 100% local processing, no cloud dependencies
- **🎛️ Flexible**: Extensive configuration and integration options
- **📈 Scalable**: From simple scripts to production services
- **🛡️ Reliable**: Robust error handling and graceful fallbacks

---

**Ready to add intelligent human presence detection to your application?**

```bash
pip install webcam-detection
```

*Built with ❤️ for developers who need reliable, local human detection.* 