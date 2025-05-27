# Webcam Detection

[![PyPI version](https://badge.fury.io/py/webcam-detection.svg)](https://badge.fury.io/py/webcam-detection)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Advanced multi-modal human detection system with service integration for real-time applications.**

Webcam Detection provides a comprehensive, local-processing human presence detection system using computer vision. Perfect for guard clauses in speaker verification, smart home automation, security systems, and any application requiring reliable human presence detection.

**🎯 Clean Project Structure**: Root directory cleaned up! All examples, client code, and debug tools are organized in the `examples/` directory. See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for navigation guide.

> 📁 **New to the project?** See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for a quick navigation guide.
> 🧹 **Recent cleanup**: Test files moved to `tests/`, debug tools to `examples/`, legacy code organized.

## 🚀 Key Features

- **🎯 Multi-Modal Detection**: Combines MediaPipe pose and face detection for 3x extended range
- **⚡ Real-Time Processing**: Low-latency detection with 15-30 FPS performance  
- **🏠 Local Processing**: No cloud dependencies, all computation happens locally
- **🛡️ Guard Clause Ready**: Perfect for speaker verification and audio processing systems
- **🔧 Service Integration**: HTTP/WebSocket/SSE APIs for easy integration
- **📐 Extended Range**: Works from desk distance to medium distance
- **🧪 Production Ready**: 320 comprehensive tests, battle-tested architecture
- **⚙️ Configurable**: Extensive configuration options for different scenarios

## 🎯 Production Ready: Gesture Recognition + Real-Time Streaming ✅

**Fully Implemented** - Following our proven TDD methodology with 414 comprehensive tests:

### 🖐️ Gesture Recognition System ✅ IMPLEMENTED
- **Hand Up Detection**: Recognize "hand up at shoulder level with palm facing camera"
- **Performance Optimized**: Gesture detection only runs when human is present
- **MediaPipe Integration**: Leverages existing pose detection for shoulder reference
- **Smart Debouncing**: Prevents false positive gesture triggers

### 📡 Server-Sent Events (SSE) Service ✅ IMPLEMENTED
- **Real-Time Streaming**: Instant gesture events via SSE on port 8766
- **Web Dashboard Ready**: CORS-enabled for web application integration
- **Multiple Clients**: Support 10+ simultaneous connections
- **Connection Management**: Automatic cleanup and heartbeat monitoring

### 🎯 Use Cases
- **Voice Assistant Stop**: Hand up gesture to pause/stop voice processing
- **Presentation Control**: Remote gesture control for presentations
- **Smart Home**: Gesture-based automation triggers
- **Security Systems**: Gesture-based alerts and controls

### 🧹 Clean Console Output
- **Single Status Line**: Updates in place without scrolling console spam
- **Essential Info**: Shows human detection, confidence, gesture status, and frame count
- **No Log Firehose**: Eliminated verbose logging for clean operation

📋 **ACHIEVED**: 414 comprehensive tests passing ✅ | Clean console output ✅ | Production deployment ✅

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

Start the enhanced webcam detection service with both HTTP API and gesture recognition:

```bash
conda activate webcam
python webcam_enhanced_service.py
```

The service provides:
- **HTTP API** (port 8767): Human presence detection with REST endpoints
- **SSE Events** (port 8766): Real-time gesture event streaming  
- **Clean Console**: Single updating status line without scroll spam

**Primary Endpoints:**
- **Primary**: `GET http://localhost:8767/presence/simple` → `{"human_present": true/false}`
- **Full status**: `GET http://localhost:8767/presence` → Complete detection details
- **Health check**: `GET http://localhost:8767/health` → Service status
- **Gesture events**: `GET http://localhost:8766/events/gestures/client_id` → SSE stream

**Console Output:** Clean single-line status that updates every 2 seconds:
```
🎥 Frame 1250 | 👤 Human: YES (conf: 0.72) | 🖐️ Gesture: hand_up (conf: 0.95) | FPS: 28.5
```

## 🔧 Detection Types

### MultiModal (Recommended)
- **Best For**: All scenarios, extended range detection
- **Range**: Close to medium distance
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

Run the enhanced service for both human detection and gesture recognition:

```bash
conda activate webcam && python webcam_enhanced_service.py
```

### Available Services

#### HTTP API (Port 8767)
- `GET /presence/simple` - Simple boolean presence check
- `GET /presence` - Full detection information  
- `GET /health` - Service health check
- `GET /statistics` - Performance metrics

#### Server-Sent Events (Port 8766) ✅ IMPLEMENTED
Real-time gesture event streaming:
- `GET /events/gestures/{client_id}` - Gesture event stream
- Real-time hand up detection events
- Multiple client support with automatic cleanup

**Sample Gesture Event:**
```json
{
  "event_type": "gesture_detected",
  "timestamp": "2024-01-15T10:30:00Z", 
  "data": {
    "gesture_type": "hand_up",
    "confidence": 0.95,
    "hand": "right",
    "position": {
      "hand_x": 0.65,
      "hand_y": 0.25,
      "palm_z_component": 0.85
    },
    "palm_facing_camera": true
  }
}
```

## 📊 Performance

- **Initialization**: < 3.5 seconds for multi-modal detector
- **Frame Rate**: 15-30 FPS processing capability
- **Latency**: < 100ms from capture to detection result
- **Range**: 3x detection range compared to pose-only systems
- **Memory**: Bounded queues, efficient resource management
- **Gesture Detection**: <50ms per frame when human present
- **SSE Streaming**: <100ms latency from gesture to client

## 🏗️ Architecture

```
Video Capture → Frame Queue → Multi-Modal Detection → Presence Decision → Gesture Detection → Service API
     ↓              ↓              ↓                     ↓                    ↓                ↓
   Thread        Async Queue    MediaPipe            Debounce           MediaPipe         HTTP/SSE
                               (Pose + Face)         Filtering         (Hands + Pose)     WebSocket
                                                                       [if human]
```

### Key Components
- **Camera Manager**: Hardware abstraction and frame capture
- **Multi-Modal Detector**: Advanced pose + face fusion
- **Presence Filter**: Debouncing and smoothing logic
- **Gesture Detector**: Hand up detection with palm orientation analysis
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

The package includes 414 comprehensive tests covering:
- Unit tests for all components
- Integration tests for complete workflows
- Multi-modal detection validation
- Gesture recognition system testing
- SSE service and real-time streaming
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

## 🧹 Recent Project Cleanup ✅ NEW!

**Root Directory Organized** - The project structure has been cleaned up for better navigation:

### ✅ Files Moved to Proper Locations:
- **Test files** → `tests/` directory (properly organized by category)
- **Debug tools** → `examples/` directory (with other development tools)
- **Legacy code** → `examples/legacy_http_service.py` (reference implementation)

### 📁 Clean Root Directory:
- **Main service**: `webcam_enhanced_service.py` (primary entry point)
- **Documentation**: `README.md`, `ARCHITECTURE.md`, `PROJECT_STRUCTURE.md`
- **Configuration**: `setup.py`, `requirements.txt`, `environment.yml`
- **Organized directories**: `src/`, `tests/`, `docs/`, `examples/`, `config/`

### 🎯 Benefits:
- **Cleaner navigation** - Easy to find what you need
- **Professional structure** - Industry-standard organization
- **Better documentation** - Updated guides reflect current structure
- **Preserved functionality** - All files moved, not deleted

## 🔄 Changelog

### v3.0.0 - Gesture Recognition + Real-Time Streaming ✅ NEW!
- ✨ Hand up gesture detection with palm orientation analysis
- ✨ Real-time SSE service for gesture event streaming
- ✨ Performance-optimized conditional gesture detection
- ✨ Comprehensive gesture test suite (+94 tests = 414 total)
- ✨ Production-ready gesture + SSE integration

### v2.0.0 - Multi-Modal Enhancement
- ✨ Multi-modal detection with 3x extended range
- ✨ Factory pattern for extensible detector architecture
- ✨ Service layer with HTTP/WebSocket/SSE APIs
- ✨ Comprehensive test suite (320 tests)
- ✨ Production-ready architecture

### v1.0.0 - Initial Release
- Basic MediaPipe pose detection
- Camera management system
- CLI interface

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🌟 Why Choose Webcam Detection?

- **🎯 Proven**: Battle-tested with 414 comprehensive tests
- **⚡ Fast**: Optimized for real-time performance
- **🔒 Private**: 100% local processing, no cloud dependencies
- **🎛️ Flexible**: Extensive configuration and integration options
- **📈 Scalable**: From simple scripts to production services
- **🛡️ Reliable**: Robust error handling and graceful fallbacks
- **🖐️ Gesture-Ready**: Advanced hand detection for voice control and automation

---

*Built with ❤️ for developers who need reliable, local human detection.* 

## 🔧 Integration Examples

### Real-time Gesture Events
```python
import asyncio
import aiohttp

async def listen_for_gestures():
    """Listen for real-time gesture events via SSE."""
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8766/events/gestures/my_app') as resp:
            async for line in resp.content:
                if line.startswith(b'data: '):
                    event_data = line[6:].decode().strip()
                    if event_data and event_data != '[HEARTBEAT]':
                        import json
                        gesture_event = json.loads(event_data)
                        print(f"Gesture detected: {gesture_event}")
                        # Process gesture event
                        if gesture_event['data']['gesture_type'] == 'hand_up':
                            # Handle hand up gesture (e.g., pause voice bot)
                            handle_hand_up_gesture()

# Run gesture listener
asyncio.run(listen_for_gestures())
```

### Combined Presence + Gesture Integration
```python
import requests
import asyncio
import aiohttp

class VoiceBotController:
    def __init__(self):
        self.voice_bot_active = False
        self.gesture_listener_task = None
    
    def check_human_presence(self):
        """Check if human is present before starting voice bot."""
        try:
            response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
            return response.json().get("human_present", False)
        except:
            return False
    
    async def start_voice_bot_with_gesture_control(self):
        """Start voice bot with gesture-based stop control."""
        if not self.check_human_presence():
            print("No human detected - voice bot not started")
            return
        
        # Start voice bot
        self.voice_bot_active = True
        print("Voice bot started - raise hand to stop")
        
        # Start gesture listener
        self.gesture_listener_task = asyncio.create_task(self.listen_for_stop_gestures())
        
        # Your voice bot logic here
        await self.run_voice_bot()
    
    async def listen_for_stop_gestures(self):
        """Listen for hand up gestures to stop voice bot."""
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8766/events/gestures/voice_bot') as resp:
                async for line in resp.content:
                    if line.startswith(b'data: '):
                        event_data = line[6:].decode().strip()
                        if event_data and event_data != '[HEARTBEAT]':
                            import json
                            gesture_event = json.loads(event_data)
                            if gesture_event['data']['gesture_type'] == 'hand_up':
                                print("Hand up detected - stopping voice bot")
                                self.voice_bot_active = False
                                break
    
    async def run_voice_bot(self):
        """Main voice bot loop."""
        while self.voice_bot_active:
            # Your voice processing logic
            await asyncio.sleep(0.1)
        print("Voice bot stopped")

# Usage
controller = VoiceBotController()
asyncio.run(controller.start_voice_bot_with_gesture_control())
```
