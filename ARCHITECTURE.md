# Webcam Human Detection System - Architecture

## Executive Summary

A local, real-time human presence detection system using computer vision with AI-powered scene descriptions. The system captures video from a webcam, processes frames asynchronously, and determines human presence using advanced multi-modal detection combining MediaPipe pose and face detection.

**Key Capabilities:**
- **Real-time Detection**: Multi-modal human presence detection (pose + face)
- **Extended Range**: 3x detection range compared to pose-only systems
- **Gesture Recognition**: Hand gesture detection for voice assistant control
- **AI Descriptions**: Local Ollama integration for scene descriptions
- **Service Integration**: Production-ready HTTP API and SSE streaming
- **Local Processing**: No cloud dependencies, all computation local

**Primary Use Cases:**
- Speaker verification guard clauses
- Smart home automation triggers
- Voice assistant gesture control
- Security and monitoring systems

## System Architecture

### Core Pipeline
```
Video Capture → Frame Queue → Multi-Modal Detection → Presence Decision → Gesture Detection → Service Layer
     ↓              ↓              ↓                     ↓                    ↓                ↓
   Thread        Async Queue    MediaPipe            Debounce           MediaPipe         EventPublisher
                               (Pose + Face)         Filtering         (Hands + Pose)    ├── HTTP API (8767)
                                                                       [if human]        └── SSE Events (8766)
```

### Service Architecture
```
Detection Pipeline → EventPublisher → Service Layer
                                    ├── HTTP API Service (8767) - REST endpoints
                                    ├── SSE Service (8766) - Real-time gesture events
                                    └── Description Service - AI-powered scene analysis
```

### Data Flow
1. **Frame Capture**: Continuous video capture in dedicated thread
2. **Detection Processing**: Async multi-modal detection (pose + face fusion)
3. **Presence Filtering**: Debouncing with weighted voting to reduce false positives
4. **Gesture Analysis**: Conditional gesture detection when humans present
5. **Event Publishing**: Real-time events distributed to service subscribers
6. **Service Responses**: HTTP API and SSE streaming for client integration

## Key Components

### Camera Module (`src/camera/`)
- **CameraManager**: Hardware initialization and lifecycle management
- **FrameCapture**: Continuous video capture with error handling
- **CameraConfig**: Camera settings and profile management

### Detection Engine (`src/detection/`)
- **MultiModalDetector**: Combined pose + face detection for extended range
- **MediaPipeDetector**: Traditional pose-only detection (legacy support)
- **DetectorFactory**: Extensible factory pattern for detector registration
- **Performance**: 15-30 FPS processing, <3.5s initialization

### Gesture Recognition (`src/gesture/`)
- **HandDetection**: MediaPipe hands integration
- **GestureClassification**: "Stop" gesture algorithm with palm orientation
- **Performance Optimization**: Only runs when human presence confirmed

### Service Layer (`src/service/`)
- **HTTPDetectionService**: REST API with 5 endpoints for guard clause integration
- **SSEDetectionService**: Server-Sent Events for real-time gesture streaming
- **EventPublisher**: Central event system with sync/async subscriber support

### Ollama Integration (`src/ollama/`)
- **OllamaClient**: Local Ollama service integration (localhost:11434)
- **DescriptionService**: Async AI-powered scene descriptions
- **Smart Caching**: MD5-based frame caching with 5-minute TTL
- **Error Resilience**: Comprehensive fallback handling and retry policies

### Processing Pipeline (`src/processing/`)
- **FrameQueue**: Thread-safe async frame buffering
- **PresenceFilter**: Debouncing with weighted voting algorithms
- **Performance**: Bounded memory usage, proper cleanup

## Technology Stack

### Core Libraries
- **OpenCV**: Camera access and frame processing
- **MediaPipe**: Human detection (pose, face, hands)
- **NumPy**: Numerical operations and image arrays
- **AsyncIO**: Asynchronous frame processing

### Service Framework
- **FastAPI**: HTTP API with automatic OpenAPI documentation
- **Uvicorn**: ASGI server for production deployment
- **Server-Sent Events**: Real-time streaming capabilities

### AI Integration
- **Ollama**: Local LLM service for scene descriptions
- **Gemma3 Models**: Multimodal vision-language models

### Development
- **PyTest**: 637 comprehensive tests (100% pass rate)
- **Threading**: Video capture and background processing
- **YAML**: Configuration management

## Integration Points

### HTTP API Endpoints
```
GET /presence/simple   → {"human_present": true}     # Guard clause endpoint
GET /presence         → Full presence status         # Detailed information  
GET /statistics       → Performance metrics          # System monitoring
GET /health          → Service health check         # Deployment health
GET /description/latest → AI scene descriptions      # Optional AI features
```

### Speaker Verification Integration
```python
# Guard clause pattern for speaker verification
def should_process_audio() -> bool:
    response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
    return response.json().get("human_present", False) if response.status_code == 200 else True
```

### Real-time Event Streaming
```
GET /events/gestures/{client_id}  → SSE stream for gesture events
Content-Type: text/event-stream
→ Real-time gesture detection events for web dashboards
```

## Configuration

### Detection Configuration
```yaml
multimodal:
  pose_weight: 0.6          # Pose detection influence
  face_weight: 0.4          # Face detection influence  
  min_detection_confidence: 0.5
  
presence_filter:
  smoothing_window: 5
  min_confidence_threshold: 0.7
  debounce_frames: 3
```

### Service Configuration
```yaml
service_layer:
  http:
    host: "localhost"
    port: 8767
  
  sse:
    port: 8766
    max_connections: 20
```

### Ollama Configuration
```yaml
client:
  base_url: "http://localhost:11434"
  model: "gemma3:4b-it-q4_K_M"
  timeout_seconds: 30.0
  
description_service:
  cache_ttl_seconds: 300
  max_concurrent_requests: 3
  enable_fallback_descriptions: true
```

## Directory Structure

```
webcam/
├── src/
│   ├── camera/           # Camera management and capture
│   ├── detection/        # Multi-modal human detection
│   ├── gesture/          # Gesture recognition system
│   ├── processing/       # Frame processing and filtering
│   ├── service/          # HTTP/SSE service layer
│   ├── ollama/          # AI description integration
│   ├── utils/           # Configuration and utilities
│   └── cli/             # Command-line interface
├── scripts/             # Utility and debugging scripts
├── config/              # YAML configuration files
├── tests/               # 637 comprehensive tests
├── docs/                # Organized documentation
│   ├── guides/          # User-focused guides
│   ├── features/        # Feature-specific documentation
│   ├── examples/        # Code examples and patterns
│   └── development/     # Contributor resources
└── examples/            # Usage examples and demos
```

## Performance Characteristics

### Detection Performance
- **Frame Rate**: 15-30 FPS sustained processing
- **Latency**: <100ms from capture to detection result  
- **Range**: 3x extended range vs pose-only detection
- **Initialization**: <3.5s for complete system startup

### Service Performance
- **HTTP Response**: <50ms for guard clause endpoints
- **Concurrent Requests**: 50+ requests/second sustained
- **SSE Connections**: 20+ simultaneous connections supported
- **Memory Usage**: <100MB total system footprint

### AI Integration Performance
- **New Descriptions**: 10-30s processing time (Gemma3:4b)
- **Cached Descriptions**: <1s response time
- **Cache Efficiency**: 5-minute TTL with MD5-based keys
- **Error Recovery**: Comprehensive fallback descriptions

## Deployment Considerations

### Production Ready
- **Error Isolation**: Component failures don't cascade
- **Graceful Degradation**: System continues without AI features if Ollama unavailable
- **Health Monitoring**: Comprehensive health checks and metrics
- **Zero Downtime**: Service continues during component restarts

### Resource Requirements
- **CPU**: Modern multi-core processor (MediaPipe processing)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 2GB for models and dependencies
- **Camera**: USB camera or integrated webcam

### Model Recommendations
- **Recommended**: `gemma3:4b-it-q4_K_M` (best speed/quality balance)
- **High Quality**: `gemma3:12b-it-q4_K_M` (slower, better quality)
- **Lightweight**: `gemma3:1b` (fast, basic descriptions)

## Security & Privacy

### Local Processing
- **No Cloud Dependencies**: All computation happens locally
- **No Data Transmission**: Camera feeds never leave the device
- **Privacy First**: No external network calls for core functionality

### API Security
- **CORS Configured**: Ready for web integration
- **Input Validation**: Comprehensive request validation
- **Error Handling**: No sensitive information in error responses

---

## Quick Start

1. **Install Dependencies**: `conda env create -f environment.yml`
2. **Start Ollama**: `ollama serve` (optional, for AI descriptions)
3. **Run Service**: `python webcam_service.py`
4. **Monitor Status**: `python scripts/monitor_detection_status.py` (optional, in another terminal)
5. **Test Integration**: `curl http://localhost:8767/presence/simple`

For detailed setup instructions, see `README.md` and `docs/` directory. 