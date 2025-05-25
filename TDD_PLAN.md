# Test-Driven Development Plan - Webcam Human Detection

## TDD Philosophy & Process

Following strict **Red → Green → Refactor** methodology:

1. **RED**: Write a failing test that defines the desired functionality
2. **GREEN**: Write the minimal code to make the test pass
3. **REFACTOR**: Improve the code while keeping tests passing
4. **COMMIT**: After each successful cycle, consider committing changes

## Development Phases

### Phase 1: Foundation & Configuration ⏳
*Goal: Establish basic infrastructure and configuration management*
- [ ] **Phase 1 Complete**

#### Cycle 1.1: Configuration Management ✅
- [x] **Cycle 1.1 Complete**

**RED**: Test configuration loading ✅
- [x] Write failing tests for configuration loading
```python
def test_config_manager_loads_yaml():
    # Should load camera_profiles.yaml and return valid config
    assert config_manager.load_camera_profile('default') is not None

def test_config_manager_handles_missing_file():
    # Should raise appropriate exception for missing config
    with pytest.raises(ConfigurationError):
        config_manager.load_camera_profile('nonexistent')
```

**GREEN**: Implement basic ConfigManager ✅
- [x] Create `src/utils/config.py`
- [x] Implement YAML loading
- [x] Handle file not found errors
- [x] Verify tests pass

**REFACTOR**: Clean up error handling and add validation ✅
- [x] Clean up error handling and add validation
- [x] Ensure all tests still pass

#### Cycle 1.2: Logging Setup ✅
- [x] **Cycle 1.2 Complete**

**RED**: Test logging configuration ✅
- [x] Write failing tests for logging setup
```python
def test_logger_manager_creates_default_config():
    # Should create logger with default configuration
    logger_manager = LoggerManager()
    logger = logger_manager.get_logger('test')
    assert logger is not None

def test_logger_manager_handles_missing_config():
    # Should handle missing configuration file gracefully
    with pytest.raises(LoggerError):
        LoggerManager(config_file='nonexistent.yaml')
```

**GREEN**: Implement Logger utility ✅
- [x] Create `src/utils/logger.py`
- [x] Set up structured logging
- [x] Configure file and console output
- [x] Verify tests pass

**REFACTOR**: Add log rotation and formatting options ✅
- [x] Add log rotation and formatting options
- [x] Add environment variable overrides
- [x] Add enhanced error handling with exception chaining
- [x] Add thread-safe logger management
- [x] Ensure all tests still pass

### Phase 2: Camera System (Core Foundation)

### ✅ Cycle 2.1: Camera Configuration  
- ✅ Camera config dataclass with validation
- ✅ Camera profile loading from YAML
- ✅ Environment variable overrides
- ✅ Parameter validation and error handling
- ✅ Camera capability detection and validation

### ✅ Cycle 2.2: Basic Camera Manager
- ✅ Camera initialization and resource management
- ✅ Frame capture with error handling
- ✅ Configuration application and validation
- ✅ Camera capability detection
- ✅ Performance monitoring and statistics

#### Cycle 2.3: Frame Capture
- [ ] **Cycle 2.3 Complete**

**RED**: Test frame capture functionality
- [ ] Write failing tests for frame capture
```python
@patch('cv2.VideoCapture')
def test_frame_capture_reads_frame(mock_cv2):
    # Should capture and return frame
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cv2.return_value.read.return_value = (True, mock_frame)
    
    capture = FrameCapture(camera_manager)
    frame = capture.get_frame()
    assert frame is not None
    assert frame.shape == (480, 640, 3)

def test_frame_capture_handles_read_failure(mock_cv2):
    # Should handle failed frame reads
    mock_cv2.return_value.read.return_value = (False, None)
    
    capture = FrameCapture(camera_manager)
    frame = capture.get_frame()
    assert frame is None
```

**GREEN**: Implement FrameCapture class
- [ ] Create `src/camera/capture.py`
- [ ] Implement synchronous frame reading
- [ ] Handle read failures
- [ ] Verify tests pass

**REFACTOR**: Add frame preprocessing and validation
- [ ] Add frame preprocessing and validation
- [ ] Ensure all tests still pass

### Phase 3: Queue and Processing Infrastructure ⏳
*Goal: Establish asynchronous frame processing*
- [ ] **Phase 3 Complete**

#### Cycle 3.1: Frame Queue
- [ ] **Cycle 3.1 Complete**

**RED**: Test thread-safe frame queue
- [ ] Write failing tests for frame queue
```python
def test_frame_queue_basic_operations():
    # Should support put/get operations
    queue = FrameQueue(max_size=5)
    frame = np.zeros((480, 640, 3))
    
    queue.put_frame(frame)
    retrieved_frame = queue.get_frame()
    assert np.array_equal(frame, retrieved_frame)

def test_frame_queue_overflow_handling():
    # Should handle queue overflow (drop oldest)
    queue = FrameQueue(max_size=2)
    frame1, frame2, frame3 = [np.ones((480, 640, 3)) * i for i in range(3)]
    
    queue.put_frame(frame1)
    queue.put_frame(frame2)
    queue.put_frame(frame3)  # Should drop frame1
    
    assert queue.size() == 2
    assert not np.array_equal(queue.get_frame(), frame1)
```

**GREEN**: Implement FrameQueue
- [ ] Create `src/processing/queue.py`
- [ ] Use `queue.Queue` with size limits
- [ ] Implement overflow handling
- [ ] Verify tests pass

**REFACTOR**: Add queue statistics and monitoring
- [ ] Add queue statistics and monitoring
- [ ] Ensure all tests still pass

#### Cycle 3.2: Async Frame Processor
- [ ] **Cycle 3.2 Complete**

**RED**: Test asynchronous frame processing
- [ ] Write failing tests for async frame processing
```python
@pytest.mark.asyncio
async def test_frame_processor_processes_frames():
    # Should process frames from queue asynchronously
    mock_detector = Mock()
    mock_detector.detect.return_value = DetectionResult(human_present=True)
    
    processor = FrameProcessor(frame_queue, mock_detector)
    frame = np.zeros((480, 640, 3))
    frame_queue.put_frame(frame)
    
    result = await processor.process_next_frame()
    assert result.human_present is True

@pytest.mark.asyncio
async def test_frame_processor_handles_empty_queue():
    # Should handle empty queue gracefully
    processor = FrameProcessor(empty_queue, mock_detector)
    result = await processor.process_next_frame()
    assert result is None
```

**GREEN**: Implement FrameProcessor
- [ ] Create `src/processing/processor.py`
- [ ] Implement async frame processing
- [ ] Handle queue operations
- [ ] Verify tests pass

**REFACTOR**: Add error handling and performance monitoring
- [ ] Add error handling and performance monitoring
- [ ] Ensure all tests still pass

### Phase 4: Human Detection ⏳
*Goal: Implement human presence detection using MediaPipe*
- [ ] **Phase 4 Complete**

#### Cycle 4.1: Detection Result Structure
- [ ] **Cycle 4.1 Complete**

**RED**: Test detection result format
- [ ] Write failing tests for detection result
```python
def test_detection_result_creation():
    # Should create valid detection result
    result = DetectionResult(
        human_present=True,
        confidence=0.85,
        bounding_box=(10, 20, 100, 200),
        landmarks=[(50, 60), (70, 80)]
    )
    assert result.human_present is True
    assert result.confidence == 0.85

def test_detection_result_validation():
    # Should validate confidence range
    with pytest.raises(ValueError):
        DetectionResult(human_present=True, confidence=1.5)
```

**GREEN**: Implement DetectionResult
- [ ] Create `src/detection/result.py`
- [ ] Define result data structure
- [ ] Add validation logic
- [ ] Verify tests pass

**REFACTOR**: Add serialization and comparison methods
- [ ] Add serialization and comparison methods
- [ ] Ensure all tests still pass

#### Cycle 4.2: Abstract Detector Base
- [ ] **Cycle 4.2 Complete**

**RED**: Test detector interface
- [ ] Write failing tests for detector interface
```python
def test_human_detector_interface():
    # Should define abstract interface
    assert hasattr(HumanDetector, 'detect')
    assert hasattr(HumanDetector, 'initialize')
    assert hasattr(HumanDetector, 'cleanup')

def test_detector_initialization():
    # Should require implementation of abstract methods
    with pytest.raises(TypeError):
        HumanDetector()  # Cannot instantiate abstract class
```

**GREEN**: Implement HumanDetector abstract base
- [ ] Create `src/detection/base.py`
- [ ] Define abstract interface
- [ ] Set up provider pattern
- [ ] Verify tests pass

**REFACTOR**: Add configuration and lifecycle methods
- [ ] Add configuration and lifecycle methods
- [ ] Ensure all tests still pass

#### Cycle 4.3: MediaPipe Detector Implementation
- [ ] **Cycle 4.3 Complete**

**RED**: Test MediaPipe detector
- [ ] Write failing tests for MediaPipe detector
```python
@patch('mediapipe.solutions.pose.Pose')
def test_mediapipe_detector_initialization(mock_pose):
    # Should initialize MediaPipe pose model
    detector = MediaPipeDetector(detection_config)
    assert detector.is_initialized
    mock_pose.assert_called_once()

@patch('mediapipe.solutions.pose.Pose')
def test_mediapipe_detector_detects_human(mock_pose):
    # Should detect human in frame with person
    mock_results = Mock()
    mock_results.pose_landmarks = Mock()  # Indicates person detected
    mock_pose.return_value.process.return_value = mock_results
    
    detector = MediaPipeDetector(detection_config)
    frame = load_test_image('person.jpg')
    result = detector.detect(frame)
    
    assert result.human_present is True
    assert result.confidence > 0.5

@patch('mediapipe.solutions.pose.Pose')
def test_mediapipe_detector_no_human(mock_pose):
    # Should return no detection for empty frame
    mock_results = Mock()
    mock_results.pose_landmarks = None  # No person detected
    mock_pose.return_value.process.return_value = mock_results
    
    detector = MediaPipeDetector(detection_config)
    frame = load_test_image('empty_room.jpg')
    result = detector.detect(frame)
    
    assert result.human_present is False
```

**GREEN**: Implement MediaPipeDetector
- [ ] Create `src/detection/mediapipe_detector.py`
- [ ] Initialize MediaPipe Pose solution
- [ ] Process frames and extract landmarks
- [ ] Convert to DetectionResult format
- [ ] Verify tests pass

**REFACTOR**: Optimize for performance and add error handling
- [ ] Optimize for performance and add error handling
- [ ] Ensure all tests still pass

### Phase 5: Presence Filtering and Decision Making ⏳
*Goal: Implement debouncing and smoothing for stable detection*
- [ ] **Phase 5 Complete**

#### Cycle 5.1: Presence Filter
- [ ] **Cycle 5.1 Complete**

**RED**: Test presence filtering logic
- [ ] Write failing tests for presence filtering
```python
def test_presence_filter_smoothing():
    # Should smooth detection results over time
    filter = PresenceFilter(window_size=3, threshold=0.7)
    
    # Send mixed results
    filter.add_result(DetectionResult(human_present=True, confidence=0.8))
    filter.add_result(DetectionResult(human_present=False, confidence=0.3))
    filter.add_result(DetectionResult(human_present=True, confidence=0.9))
    
    # Should return True based on majority and confidence
    assert filter.get_filtered_presence() is True

def test_presence_filter_debouncing():
    # Should require consistent results before changing state
    filter = PresenceFilter(debounce_frames=3)
    
    # Initially no presence
    assert filter.get_filtered_presence() is False
    
    # Single positive detection shouldn't change state
    filter.add_result(DetectionResult(human_present=True, confidence=0.8))
    assert filter.get_filtered_presence() is False
    
    # Multiple consistent detections should change state
    for _ in range(3):
        filter.add_result(DetectionResult(human_present=True, confidence=0.8))
    assert filter.get_filtered_presence() is True
```

**GREEN**: Implement PresenceFilter
- [ ] Create `src/processing/filter.py`
- [ ] Implement sliding window smoothing
- [ ] Add debounce logic
- [ ] Track state changes
- [ ] Verify tests pass

**REFACTOR**: Add configurable thresholds and algorithms
- [ ] Add configurable thresholds and algorithms
- [ ] Ensure all tests still pass

### Phase 6: Integration and CLI ⏳
*Goal: Integrate all components into working application*
- [ ] **Phase 6 Complete**

#### Cycle 6.1: Main Application Coordinator
- [ ] **Cycle 6.1 Complete**

**RED**: Test application lifecycle
- [ ] Write failing tests for application lifecycle
```python
@patch('src.camera.manager.CameraManager')
@patch('src.detection.mediapipe_detector.MediaPipeDetector')
def test_main_app_initialization(mock_detector, mock_camera):
    # Should initialize all components
    app = MainApp(config)
    app.initialize()
    
    assert app.camera_manager is not None
    assert app.detector is not None
    assert app.frame_processor is not None

@pytest.mark.asyncio
async def test_main_app_processing_loop():
    # Should run processing loop until stopped
    app = MainApp(config)
    app.initialize()
    
    # Run for short duration
    await asyncio.wait_for(app.run(), timeout=1.0)
    
    # Should have processed some frames
    assert app.frames_processed > 0
```

**GREEN**: Implement MainApp
- [ ] Create `src/cli/main.py`
- [ ] Coordinate component lifecycle
- [ ] Implement main processing loop
- [ ] Handle graceful shutdown
- [ ] Verify tests pass

**REFACTOR**: Add signal handling and cleanup
- [ ] Add signal handling and cleanup
- [ ] Ensure all tests still pass

#### Cycle 6.2: CLI Interface
- [ ] **Cycle 6.2 Complete**

**RED**: Test command-line interface
- [ ] Write failing tests for CLI interface
```python
def test_command_parser_default_args():
    # Should parse default arguments
    parser = CommandParser()
    args = parser.parse(['--profile', 'default'])
    
    assert args.profile == 'default'
    assert args.verbose is False

def test_command_parser_all_options():
    # Should parse all command-line options
    parser = CommandParser()
    args = parser.parse([
        '--profile', 'high_quality',
        '--verbose',
        '--log-file', 'app.log'
    ])
    
    assert args.profile == 'high_quality'
    assert args.verbose is True
    assert args.log_file == 'app.log'
```

**GREEN**: Implement CommandParser
- [ ] Create `src/cli/parser.py`
- [ ] Define command-line arguments
- [ ] Add help and validation
- [ ] Verify tests pass

**REFACTOR**: Add argument groups and better help text
- [ ] Add argument groups and better help text
- [ ] Ensure all tests still pass

### Phase 7: Error Handling and Robustness ⏳
*Goal: Ensure robust operation under various conditions*
- [ ] **Phase 7 Complete**

#### Cycle 7.1: Camera Error Recovery
- [ ] **Cycle 7.1 Complete**

**RED**: Test camera reconnection
- [ ] Write failing tests for camera reconnection
```python
@patch('cv2.VideoCapture')
def test_camera_manager_reconnection(mock_cv2):
    # Should attempt reconnection when camera lost
    mock_cap = Mock()
    mock_cap.isOpened.side_effect = [True, False, True]  # Lost then recovered
    mock_cap.read.side_effect = [(False, None), (True, np.zeros((480, 640, 3)))]
    mock_cv2.return_value = mock_cap
    
    manager = CameraManager(config)
    
    # First read fails (camera lost)
    frame1 = manager.get_frame()
    assert frame1 is None
    
    # Should attempt reconnection and succeed
    frame2 = manager.get_frame()
    assert frame2 is not None
```

**GREEN**: Implement camera error recovery
- [ ] Add reconnection logic to CameraManager
- [ ] Handle temporary failures
- [ ] Log recovery attempts
- [ ] Verify tests pass

**REFACTOR**: Add exponential backoff and max retry limits
- [ ] Add exponential backoff and max retry limits
- [ ] Ensure all tests still pass

#### Cycle 7.2: Performance Monitoring
- [ ] **Cycle 7.2 Complete**

**RED**: Test performance monitoring
- [ ] Write failing tests for performance monitoring
```python
def test_performance_monitor_tracks_fps():
    # Should track frame processing rate
    monitor = PerformanceMonitor()
    
    for _ in range(10):
        monitor.record_frame_processed()
        time.sleep(0.1)
    
    fps = monitor.get_current_fps()
    assert 8 <= fps <= 12  # Should be around 10 FPS

def test_performance_monitor_tracks_latency():
    # Should track processing latency
    monitor = PerformanceMonitor()
    
    monitor.start_timing('detection')
    time.sleep(0.05)  # 50ms processing
    monitor.end_timing('detection')
    
    avg_latency = monitor.get_average_latency('detection')
    assert 0.04 <= avg_latency <= 0.06
```

**GREEN**: Implement PerformanceMonitor
- [ ] Create `src/utils/monitor.py`
- [ ] Track FPS and latency metrics
- [ ] Provide performance statistics
- [ ] Verify tests pass

**REFACTOR**: Add alerting for performance degradation
- [ ] Add alerting for performance degradation
- [ ] Ensure all tests still pass

### Phase 8: End-to-End Integration ⏳
*Goal: Complete system integration and validation*
- [ ] **Phase 8 Complete**

#### Cycle 8.1: Integration Tests
- [ ] **Cycle 8.1 Complete**

**RED**: Test complete pipeline
- [ ] Write failing tests for complete pipeline
```python
@pytest.mark.integration
@patch('cv2.VideoCapture')
def test_end_to_end_detection_pipeline(mock_cv2):
    # Should process frames from camera to presence decision
    # Mock camera to return test frames
    test_frames = [
        load_test_image('person.jpg'),      # Should detect human
        load_test_image('empty_room.jpg'),  # Should not detect human
        load_test_image('person.jpg')       # Should detect human again
    ]
    mock_cv2.return_value.read.side_effect = [(True, frame) for frame in test_frames]
    
    app = MainApp(test_config)
    app.initialize()
    
    results = []
    async def capture_results():
        for _ in range(3):
            result = await app.process_single_frame()
            results.append(result.human_present)
    
    asyncio.run(capture_results())
    
    # Should detect pattern: True, False, True
    assert results == [True, False, True]

@pytest.mark.integration
def test_performance_under_load():
    # Should maintain performance under continuous operation
    app = MainApp(performance_config)
    app.initialize()
    
    start_time = time.time()
    frame_count = 0
    
    # Run for 10 seconds
    async def load_test():
        nonlocal frame_count
        end_time = start_time + 10
        while time.time() < end_time:
            await app.process_single_frame()
            frame_count += 1
    
    asyncio.run(load_test())
    
    # Should maintain minimum FPS
    actual_fps = frame_count / 10
    assert actual_fps >= 10  # Minimum 10 FPS
```

**GREEN**: Implement integration test support
- [ ] Create test fixtures and data
- [ ] Add performance test configurations
- [ ] Implement load testing utilities
- [ ] Verify tests pass

**REFACTOR**: Add comprehensive test scenarios and edge cases
- [ ] Add comprehensive test scenarios and edge cases
- [ ] Ensure all tests still pass

## Commit Strategy

After each successful TDD cycle:
1. **Run all tests** to ensure nothing is broken
2. **Review code quality** and adherence to standards
3. **Update documentation** if needed
4. **Commit with descriptive message** following format:
   ```
   feat: implement [component] with [functionality]
   
   - Add [specific features]
   - Include [test coverage]
   - Handle [error conditions]
   ```

## Testing Infrastructure Setup

### Required Test Dependencies
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov
pip install opencv-python mediapipe numpy
```

### Test Configuration (`pytest.ini`)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --cov=src
    --cov-report=html
    --cov-report=term-missing
markers =
    integration: Integration tests
    slow: Slow running tests
    camera: Tests requiring camera hardware
```

### Test Data Organization
```
tests/
├── fixtures/
│   ├── images/
│   │   ├── person.jpg          # Image with clear human presence
│   │   ├── empty_room.jpg      # Image without humans
│   │   ├── low_light.jpg       # Challenging lighting
│   │   └── multiple_people.jpg # Multiple humans
│   ├── videos/
│   │   └── test_sequence.mp4   # Short test video
│   └── configs/
│       ├── test_config.yaml    # Test configuration
│       └── performance_config.yaml
├── conftest.py                 # Shared fixtures
└── utils.py                   # Test utilities
```

## Success Criteria

Each phase is complete when:
1. All tests pass (RED → GREEN achieved)
2. Code coverage > 90% for new components
3. Performance targets met (latency < 100ms, FPS > 15)
4. Error handling tested and validated
5. Documentation updated
6. Code reviewed and refactored

---

## Phase Progress Tracking

- [ ] **Phase 1**: Foundation & Configuration
  - [x] Cycle 1.1: Configuration Management
  - [x] Cycle 1.2: Logging Setup

- [ ] **Phase 2**: Camera System (Core Foundation)
  - [x] Cycle 2.1: Camera Configuration
  - [x] Cycle 2.2: Basic Camera Manager
  - [ ] Cycle 2.3: Frame Capture

- [ ] **Phase 3**: Queue and Processing Infrastructure
  - [ ] Cycle 3.1: Frame Queue
  - [ ] Cycle 3.2: Async Frame Processor

- [ ] **Phase 4**: Human Detection
  - [ ] Cycle 4.1: Detection Result Structure
  - [ ] Cycle 4.2: Abstract Detector Base
  - [ ] Cycle 4.3: MediaPipe Detector Implementation

- [ ] **Phase 5**: Presence Filtering and Decision Making
  - [ ] Cycle 5.1: Presence Filter

- [ ] **Phase 6**: Integration and CLI
  - [ ] Cycle 6.1: Main Application Coordinator
  - [ ] Cycle 6.2: CLI Interface

- [ ] **Phase 7**: Error Handling and Robustness
  - [ ] Cycle 7.1: Camera Error Recovery
  - [ ] Cycle 7.2: Performance Monitoring

- [ ] **Phase 8**: End-to-End Integration
  - [ ] Cycle 8.1: Integration Tests 