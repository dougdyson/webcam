# Webcam Human Detection System - Architecture

## Project Overview

A local, real-time human presence detection system using computer vision. The system captures video from a webcam, processes frames asynchronously, and determines human presence using advanced multi-modal detection combining MediaPipe pose and face detection. Designed for integration with future speaker verification systems for multi-modal authentication.

## Core Requirements

- **Local Processing**: All computation happens locally, no cloud dependencies
- **Real-time Detection**: Low-latency human presence detection
- **Extended Range**: Multi-modal detection system supporting both close-range (desk) and distant scenarios (kitchen/cooking)
- **Robust Performance**: Handle varying lighting conditions and distances
- **False Positive Reduction**: Implement debouncing/smoothing mechanisms
- **Future Integration**: Ready for speaker verification system integration
- **Testable**: Full test coverage with mocked camera inputs
- **Extensible**: Factory pattern for easy addition of new detection backends

## System Architecture

### High-Level Pipeline
```
Video Capture → Frame Queue → Multi-Modal Detection → Presence Decision → Action/Logging
     ↓              ↓              ↓                     ↓              ↓
   Thread        Async Queue    MediaPipe            Debounce       Output
                               (Pose + Face)
```

### Core Components

#### 1. Camera Module (`src/camera/`)
- **CameraManager**: Handles camera initialization, configuration, and lifecycle
- **FrameCapture**: Continuous video capture in dedicated thread
- **CameraConfig**: Camera settings and profiles management

#### 2. Processing Module (`src/processing/`)
- **FrameQueue**: Thread-safe queue for frame buffering
- **FrameProcessor**: Async frame processing coordinator
- **PresenceFilter**: Debouncing and smoothing logic with weighted voting

#### 3. Detection Module (`src/detection/`)
- **HumanDetector**: Abstract base class for detection providers
- **MediaPipeDetector**: Traditional MediaPipe pose detection implementation
- **MultiModalDetector**: Advanced detector combining pose and face detection for extended range
- **DetectionResult**: Standardized detection result format
- **DetectorFactory**: Factory pattern for detector creation and registration

#### 4. Utils Module (`src/utils/`)
- **ConfigManager**: YAML configuration loading and management
- **Logger**: Structured logging setup
- **PerformanceMonitor**: Frame rate and latency monitoring

#### 5. CLI Module (`src/cli/`)
- **MainApp**: Primary application entry point with factory pattern integration
- **CommandParser**: CLI argument handling with detector type selection
- **StatusDisplay**: Real-time status output

## Detection System

### Multi-Modal Detection Architecture

The system implements a sophisticated multi-modal detection approach:

#### Primary Detector Types
1. **MultiModal (Default)**: Combines pose and face detection with intelligent fusion
   - **Pose Detection Weight**: 0.6 (excellent for close-range full-body detection)
   - **Face Detection Weight**: 0.4 (superior for distant/partial face detection)
   - **Range**: Desk distance to kitchen distance (3x extended range)
   - **Use Case**: Optimal for varied scenarios, cooking detection, smart home integration

2. **MediaPipe (Legacy)**: Traditional pose-only detection
   - **Range**: Close to medium distance
   - **Use Case**: Desk work, close interaction scenarios

#### Factory Pattern Implementation
```python
# Detector registration
DetectorFactory.register('multimodal', MultiModalDetector)
DetectorFactory.register('mediapipe', MediaPipeDetector)

# Detector creation
detector = create_detector(detector_type='multimodal', config=detector_config)
```

#### CLI Integration
```bash
# Multi-modal detection (default)
python -m src.cli.main --detector-type multimodal

# Traditional MediaPipe
python -m src.cli.main --detector-type mediapipe

# Aliases supported
python -m src.cli.main --detector-type pose_face  # → multimodal
python -m src.cli.main --detector-type pose       # → mediapipe
```

### Detection Fusion Algorithm

The multi-modal detector uses weighted fusion:

1. **Parallel Processing**: Both pose and face detection run on each frame
2. **Confidence Calculation**: Individual confidence scores from each detector
3. **Weighted Fusion**: `final_confidence = (pose_conf * 0.6) + (face_conf * 0.4)`
4. **Landmark Combination**: Normalized landmarks from both detection methods
5. **Bounding Box Union**: Combined bounding boxes for complete human detection

## Data Flow

### 1. Initialization Phase
1. Load configuration from `config/` directory
2. Initialize camera with specified settings
3. Create frame queue with configured buffer size
4. Initialize detection models using factory pattern (default: MultiModal)
5. Start background threads

### 2. Runtime Phase
1. **Frame Capture Thread**:
   - Continuously capture frames from camera
   - Add frames to processing queue
   - Handle camera errors and reconnection

2. **Processing Loop** (Async):
   - Dequeue frames from buffer
   - Run multi-modal human detection on each frame
   - Apply presence filtering/debouncing with weighted voting
   - Update system state
   - Log results and performance metrics

3. **Output/Action**:
   - Update presence status
   - Trigger configured actions
   - Log events for debugging

## Technology Stack

### Core Libraries
- **OpenCV (`opencv-python`)**: Camera access and frame processing
- **MediaPipe**: Human pose/face detection with Holistic solution
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
│   │   ├── __init__.py         # DetectorFactory & create_detector
│   │   ├── base.py             # HumanDetector (abstract)
│   │   ├── mediapipe_detector.py  # Traditional pose detection
│   │   ├── multimodal_detector.py # Multi-modal pose+face detection
│   │   └── result.py           # DetectionResult
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── queue.py            # FrameQueue
│   │   ├── processor.py        # FrameProcessor
│   │   └── filter.py           # PresenceFilter with weighted voting
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py           # ConfigManager
│   │   ├── logger.py           # Logger setup
│   │   └── monitor.py          # PerformanceMonitor
│   └── cli/
│       ├── __init__.py
│       ├── main.py             # MainApp with factory integration
│       ├── parser.py           # CommandParser with detector selection
│       └── display.py          # StatusDisplay
├── config/
│   ├── camera_profiles.yaml    # Camera settings
│   ├── detection_config.yaml   # Detection parameters
│   └── app_config.yaml         # General app settings
├── docs/                       # Reference samples and documentation
├── tests/
│   ├── __init__.py
│   ├── test_camera/
│   ├── test_detection/         # Including multimodal tests
│   ├── test_processing/
│   ├── test_integration/       # Integration test scenarios
│   └── fixtures/               # Test images/videos
├── data/                       # Logs, temporary files
├── requirements.txt
├── environment.yml             # Conda environment specification
├── .env.example
├── ARCHITECTURE.md             # This file
├── TDD_PLAN.md                 # Development plan
├── MULTIMODAL_IMPLEMENTATION_SUMMARY.md # Implementation details
└── README.md
```

## Configuration Management

### Detection Config (`config/detection_config.yaml`)
```yaml
multimodal:
  model_complexity: 1
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5
  pose_weight: 0.6          # Weight for pose detection
  face_weight: 0.4          # Weight for face detection
  enable_pose: true
  enable_face: true

mediapipe:
  model_complexity: 1
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5

presence_filter:
  smoothing_window: 5
  min_confidence_threshold: 0.7
  debounce_frames: 3
```

## Performance Considerations

### Multi-Modal Optimization
- **Parallel Processing**: Pose and face detection run concurrently
- **Intelligent Fusion**: Weighted combination reduces false positives
- **Extended Range**: 3x detection range compared to pose-only detection
- **Resource Management**: Proper MediaPipe resource cleanup and initialization

### Performance Targets
- **Latency**: < 100ms from capture to detection result
- **Frame Rate**: Maintain 15-30 FPS processing
- **Memory**: Bounded queue sizes, proper cleanup
- **CPU**: Efficient frame processing, optimized MediaPipe usage
- **Initialization**: < 3.5s for multi-modal detector startup

## Future Integration Points

### Speaker Verification System
- Shared presence state with multi-modal confidence scores
- Combined authentication workflow leveraging extended detection range
- Unified configuration management
- Multi-modal result correlation for enhanced security

### Extension Possibilities
- Additional detection backends via factory pattern
- Custom detection models integration
- Multiple camera support with multi-modal fusion
- Web dashboard interface with detection visualization
- Home automation integration with cooking/kitchen detection
- Security system integration with extended range capabilities

## Testing Strategy

### Comprehensive Test Coverage (264 Tests)
- **Unit Tests**: Individual component functionality
- **Integration Tests**: End-to-end pipeline testing
- **Multi-Modal Tests**: Detector fusion and factory pattern
- **Performance Tests**: Load testing and resource management
- **Error Recovery**: Camera reconnection and failure scenarios

### Test Categories
- Camera system tests (67 tests)
- Detection system tests (23 multimodal + 23 mediapipe + 21 base)
- Processing pipeline tests (28 presence filter + 19 frame processor)
- Integration tests (22 main app + 4 integration scenarios)
- CLI interface tests (21 tests)

---

## Change Log

### Version 2.0 (Multi-Modal Enhancement)
- **Multi-Modal Detection**: Combined pose and face detection for 3x extended range
- **Factory Pattern**: Extensible detector architecture with easy registration
- **CLI Enhancement**: Detector type selection with aliases
- **Weighted Fusion**: Intelligent combination of detection methods
- **Performance Optimization**: <3.5s initialization, maintained FPS
- **Comprehensive Testing**: 264 tests covering all scenarios

### Version 1.0 (Initial)
- Basic architecture design
- Core component identification
- Technology stack selection
- Directory structure planning 