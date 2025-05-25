# Webcam Human Detection System - Architecture

## Project Overview

A local, real-time human presence detection system using computer vision. The system captures video from a webcam, processes frames asynchronously, and determines human presence using MediaPipe. Designed for integration with future speaker verification systems for multi-modal authentication.

## Core Requirements

- **Local Processing**: All computation happens locally, no cloud dependencies
- **Real-time Detection**: Low-latency human presence detection
- **Robust Performance**: Handle varying lighting conditions and distances
- **False Positive Reduction**: Implement debouncing/smoothing mechanisms
- **Future Integration**: Ready for speaker verification system integration
- **Testable**: Full test coverage with mocked camera inputs

## System Architecture

### High-Level Pipeline
```
Video Capture → Frame Queue → Human Detection → Presence Decision → Action/Logging
     ↓              ↓              ↓               ↓              ↓
   Thread        Async Queue    MediaPipe      Debounce       Output
```

### Core Components

#### 1. Camera Module (`src/camera/`)
- **CameraManager**: Handles camera initialization, configuration, and lifecycle
- **FrameCapture**: Continuous video capture in dedicated thread
- **CameraConfig**: Camera settings and profiles management

#### 2. Processing Module (`src/processing/`)
- **FrameQueue**: Thread-safe queue for frame buffering
- **FrameProcessor**: Async frame processing coordinator
- **PresenceFilter**: Debouncing and smoothing logic

#### 3. Detection Module (`src/detection/`)
- **HumanDetector**: Abstract base class for detection providers
- **MediaPipeDetector**: MediaPipe-based human detection implementation
- **DetectionResult**: Standardized detection result format

#### 4. Utils Module (`src/utils/`)
- **ConfigManager**: YAML configuration loading and management
- **Logger**: Structured logging setup
- **PerformanceMonitor**: Frame rate and latency monitoring

#### 5. CLI Module (`src/cli/`)
- **MainApp**: Primary application entry point
- **CommandParser**: CLI argument handling
- **StatusDisplay**: Real-time status output

## Data Flow

### 1. Initialization Phase
1. Load configuration from `config/` directory
2. Initialize camera with specified settings
3. Create frame queue with configured buffer size
4. Initialize MediaPipe detection models
5. Start background threads

### 2. Runtime Phase
1. **Frame Capture Thread**:
   - Continuously capture frames from camera
   - Add frames to processing queue
   - Handle camera errors and reconnection

2. **Processing Loop** (Async):
   - Dequeue frames from buffer
   - Run human detection on each frame
   - Apply presence filtering/debouncing
   - Update system state
   - Log results and performance metrics

3. **Output/Action**:
   - Update presence status
   - Trigger configured actions
   - Log events for debugging

## Technology Stack

### Core Libraries
- **OpenCV (`opencv-python`)**: Camera access and frame processing
- **MediaPipe**: Human pose/face detection
- **NumPy**: Numerical operations and image arrays
- **Threading**: Video capture thread management
- **AsyncIO**: Asynchronous frame processing
- **Queue**: Thread-safe frame buffering

### Supporting Libraries
- **PyYAML**: Configuration file management
- **python-dotenv**: Environment variable handling
- **argparse**: CLI interface
- **pytest**: Testing framework
- **logging**: Application logging

## Directory Structure

```
webcam/
├── src/
│   ├── __init__.py
│   ├── camera/
│   │   ├── __init__.py
│   │   ├── manager.py          # CameraManager
│   │   ├── capture.py          # FrameCapture
│   │   └── config.py           # CameraConfig
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── base.py             # HumanDetector (abstract)
│   │   ├── mediapipe_detector.py
│   │   └── result.py           # DetectionResult
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── queue.py            # FrameQueue
│   │   ├── processor.py        # FrameProcessor
│   │   └── filter.py           # PresenceFilter
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py           # ConfigManager
│   │   ├── logger.py           # Logger setup
│   │   └── monitor.py          # PerformanceMonitor
│   └── cli/
│       ├── __init__.py
│       ├── main.py             # MainApp
│       ├── parser.py           # CommandParser
│       └── display.py          # StatusDisplay
├── config/
│   ├── camera_profiles.yaml    # Camera settings
│   ├── detection_config.yaml   # Detection parameters
│   └── app_config.yaml         # General app settings
├── tests/
│   ├── __init__.py
│   ├── test_camera/
│   ├── test_detection/
│   ├── test_processing/
│   └── fixtures/               # Test images/videos
├── data/                       # Logs, temporary files
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md             # This file
├── TDD_PLAN.md                 # Development plan
└── README.md
```

## Configuration Management

### Camera Profiles (`config/camera_profiles.yaml`)
```yaml
default:
  device_id: 0
  width: 640
  height: 480
  fps: 30
  buffer_size: 10

high_quality:
  device_id: 0
  width: 1280
  height: 720
  fps: 15
  buffer_size: 5
```

### Detection Config (`config/detection_config.yaml`)
```yaml
mediapipe:
  model_complexity: 1
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5

presence_filter:
  smoothing_window: 5
  min_confidence_threshold: 0.7
  debounce_frames: 3
```

## Concurrency Design

### Threading Strategy
- **Main Thread**: CLI interface and coordination
- **Capture Thread**: Camera frame acquisition
- **Processing Thread**: Async event loop for detection

### Queue Management
- **Frame Queue**: Fixed-size buffer with oldest-frame-drop policy
- **Result Queue**: Detection results for status updates
- **Thread-safe**: All inter-thread communication via queues

## Error Handling Strategy

### Camera Errors
- Device not found/accessible
- Connection lost during operation
- Permission denied
- Hardware failure

### Processing Errors
- Frame corruption
- Detection model failures
- Memory constraints
- Performance degradation

### Recovery Mechanisms
- Automatic camera reconnection
- Graceful degradation
- Error logging and alerting
- Resource cleanup

## Performance Considerations

### Optimization Targets
- **Latency**: < 100ms from capture to detection result
- **Frame Rate**: Maintain 15-30 FPS processing
- **Memory**: Bounded queue sizes, proper cleanup
- **CPU**: Efficient frame processing, model optimization

### Monitoring
- Frame processing rates
- Queue sizes and overflow
- Detection confidence scores
- System resource usage

## Future Integration Points

### Speaker Verification System
- Shared presence state
- Combined authentication workflow
- Unified configuration management
- Multi-modal result correlation

### Extension Possibilities
- Multiple camera support
- Custom detection models
- Web dashboard interface
- Home automation integration
- Security system integration

## Testing Strategy

### Unit Tests
- Individual component functionality
- Mocked camera inputs
- Configuration loading
- Error handling paths

### Integration Tests
- End-to-end pipeline
- Camera + detection workflow
- Performance under load
- Error recovery scenarios

### Test Data
- Sample images with/without humans
- Various lighting conditions
- Different poses and distances
- Edge cases and failure scenarios

---

## Change Log

### Version 1.0 (Initial)
- Basic architecture design
- Core component identification
- Technology stack selection
- Directory structure planning 