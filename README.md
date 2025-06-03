# Webcam Detection

[![PyPI version](https://badge.fury.io/py/webcam-detection.svg)](https://badge.fury.io/py/webcam-detection)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 637/637](https://img.shields.io/badge/tests-637%2F637%20passing-brightgreen.svg)](README.md#testing)

**Local, real-time human detection system with AI-powered scene descriptions and gesture recognition.**

Perfect for guard clauses in speaker verification, smart home automation, security systems, and any application requiring reliable human presence detection. **No cloud dependencies** - everything runs locally.

## ✨ What's New

- 🚀 **Production Ready**: 637 comprehensive tests, enterprise-grade reliability
- 🤖 **AI Descriptions**: Local Ollama integration with Gemma3 models  
- 🖐️ **Gesture Recognition**: Stop gesture detection for voice control
- 📡 **Real-time Streaming**: SSE events for web dashboards
- ⚡ **Extended Range**: 3x detection range with multi-modal fusion

## 🚀 Key Features

- **🎯 Multi-Modal Detection**: Combines pose + face detection for 3x extended range
- **⚡ Real-Time Processing**: 15-30 FPS with <100ms latency
- **🏠 Local Processing**: No cloud dependencies, complete privacy
- **🛡️ Guard Clause Ready**: Perfect for speaker verification systems
- **🔧 Service Integration**: HTTP/SSE APIs for easy integration
- **🤖 AI Descriptions**: Optional Ollama integration for scene analysis
- **🖐️ Gesture Control**: Hand gesture detection for voice assistants
- **📐 Extended Range**: Works from desk distance to room distance
- **🧪 Production Ready**: 637 tests, battle-tested architecture

## 📦 Quick Start

### Installation
```bash
pip install webcam-detection[service]
```

### Basic Human Detection
```python
from webcam_detection import create_detector
from webcam_detection.camera import CameraManager, CameraConfig

# Setup
camera = CameraManager(CameraConfig())
detector = create_detector('multimodal')  # Recommended: pose + face fusion
detector.initialize()

# Detect
frame = camera.get_frame()
if frame is not None:
    result = detector.detect(frame)
    print(f"Human present: {result.human_present} (confidence: {result.confidence:.2f})")

# Cleanup
detector.cleanup()
camera.cleanup()
```

### Speaker Verification Guard Clause
```python
import requests

def should_process_audio() -> bool:
    """Guard clause: only process audio when human present."""
    try:
        response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
        return response.json().get("human_present", False) if response.status_code == 200 else True
    except:
        return True  # Fail safe

# In your audio pipeline
if should_process_audio():
    result = run_speaker_verification(audio_data)
else:
    print("No human detected - skipping audio processing")
```

## 🛠️ Service Layer (Production Ready)

Start the complete service with HTTP API, gesture recognition, and optional AI descriptions:

```bash
# Start the enhanced service
python webcam_enhanced_service.py
```

### Essential Endpoints
```bash
# Primary guard clause endpoint
curl http://localhost:8767/presence/simple
# → {"human_present": true}

# Full detection details
curl http://localhost:8767/presence
# → {"human_present": true, "confidence": 0.85, "timestamp": "..."}

# Service health
curl http://localhost:8767/health
# → {"status": "healthy", "uptime": 3600, "version": "3.0.0"}

# AI descriptions (optional - requires Ollama)
curl http://localhost:8767/description/latest
# → {"description": "Person standing near desk", "confidence": 0.89}
```

### Real-time Gesture Events
```bash
# Server-Sent Events stream for gesture detection
curl http://localhost:8766/events/gestures/my_app
# → Real-time gesture events for web dashboards
```

## 🔧 Utility Scripts

The project includes helpful scripts for monitoring and debugging:

```bash
# Real-time monitoring (run in separate terminal)
python scripts/monitor_detection_status.py
# → 👤 HUMAN | Conf: 0.85 | Gesture: stop (0.92) | Frames: 1250 | FPS: 28.5

# Visual debugging with live video feed
python scripts/visual_gesture_debug.py
# → Shows webcam feed with detection overlays and landmarks
```

**Available Scripts:**
- **`monitor_detection_status.py`** - Clean real-time status monitoring
- **`visual_gesture_debug.py`** - Visual debugging with video overlays

See [scripts/README.md](scripts/README.md) for detailed usage instructions.

## 🎯 Detection Types

### MultiModal (Recommended)
Best for all scenarios with 3x extended range:
```python
detector = create_detector('multimodal')  # Pose + face fusion
```

### MediaPipe (Legacy)
Traditional pose-only detection for close-range scenarios:
```python
detector = create_detector('mediapipe')   # Pose only
```

## 🤖 AI Integration (Optional)

### Ollama Setup
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start service and pull model
ollama serve
ollama pull gemma3:4b-it-q4_K_M
```

### Configuration
```yaml
# config/ollama_config.yaml
client:
  base_url: "http://localhost:11434"
  model: "gemma3:4b-it-q4_K_M"
  timeout_seconds: 30.0

description_service:
  cache_ttl_seconds: 300
  enable_fallback_descriptions: true
```

## 📊 Performance

- **Initialization**: <3.5s for complete system startup
- **Frame Rate**: 15-30 FPS sustained processing
- **Latency**: <100ms from capture to detection result
- **Memory**: <100MB total footprint
- **Range**: 3x extended range vs pose-only systems
- **HTTP Response**: <50ms for guard clause endpoints

## 🏗️ Architecture

```
Camera → Detection → Service Layer
   ↓        ↓           ↓
Thread   Pose+Face   HTTP API (8767)
Queue    Fusion      SSE Events (8766)
                     AI Descriptions
```

**Key Components:**
- **Multi-Modal Detector**: Advanced pose + face fusion
- **Service Layer**: HTTP/SSE APIs for integration
- **Gesture Recognition**: Hand detection for voice control
- **AI Integration**: Optional Ollama descriptions
- **Factory Pattern**: Extensible detector architecture

## 🎯 Use Cases

### Speaker Verification Systems
Perfect guard clause for audio processing - only run expensive operations when humans present.

### Smart Home Automation
Trigger cooking timers, lighting, or music when someone enters the area.

### Voice Assistants
Stop gesture detection to pause/stop voice processing.

### Security Systems
Human presence detection for surveillance and access control.

### Interactive Applications
Real-time presence for kiosks, digital signage, and interactive displays.

## 🧪 Testing

Comprehensive test suite with 637 tests covering all components:

```bash
# Run all tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Quick test
pytest tests/test_detection/ -v
```

## 📖 Documentation

**[📚 Complete Documentation Index](docs/README.md)** - Find exactly what you need

**Essential Guides:**
- **[Architecture Guide](ARCHITECTURE.md)** - System design and components
- **[Configuration Guide](docs/guides/CONFIGURATION_GUIDE.md)** - Detailed setup options
- **[Integration Examples](docs/guides/INTEGRATION_EXAMPLES.md)** - Advanced usage patterns

**Feature Documentation:**
- **[Ollama Integration](docs/features/ollama/INTEGRATION_GUIDE.md)** - AI description setup
- **[Gesture Performance](docs/features/GESTURE_PERFORMANCE_OPTIMIZATIONS.md)** - Hand detection optimization

**Development Resources:**
- **[Development Guide](docs/development/TDD_METHODOLOGY.md)** - Contributing guidelines
- **[Code Examples](docs/examples/)** - 7,600+ lines of practical patterns
- **[Utility Scripts](scripts/README.md)** - Monitoring and debugging tools

## 🚨 System Requirements

- **Python**: 3.10+
- **OS**: Windows/macOS/Linux
- **Camera**: USB webcam or integrated camera
- **Memory**: 4GB RAM minimum, 8GB recommended
- **CPU**: Modern multi-core processor for MediaPipe processing

## 🔄 What's Changed

### v3.0.0 - Gesture Recognition + Real-Time Streaming
- ✨ Hand gesture detection with palm orientation analysis
- ✨ Real-time SSE service for gesture event streaming
- ✨ Production-ready service integration

### v2.0.0 - Multi-Modal Enhancement  
- ✨ Multi-modal detection with 3x extended range
- ✨ Service layer with HTTP/WebSocket/SSE APIs
- ✨ Factory pattern for extensible architecture

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🌟 Why Choose Webcam Detection?

- **🎯 Proven**: 637 comprehensive tests, production-ready
- **⚡ Fast**: Optimized for real-time performance (<100ms latency)
- **🔒 Private**: 100% local processing, no cloud dependencies
- **🎛️ Flexible**: Extensive configuration and integration options
- **📈 Scalable**: From simple scripts to production services
- **🛡️ Reliable**: Robust error handling and graceful fallbacks
- **🖐️ Gesture-Ready**: Advanced hand detection for automation

---

*Built with ❤️ for developers who need reliable, local human detection.*

**[Get Started →](docs/README.md)** | **[View Examples →](docs/guides/INTEGRATION_EXAMPLES.md)** | **[Architecture →](ARCHITECTURE.md)** 