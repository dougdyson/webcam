# MediaPipe GestureRecognizer Migration - TDD Plan

## 🎯 **Objective**
Migrate from **custom finger-counting gesture recognition** to **MediaPipe's built-in GestureRecognizer** while maintaining backwards compatibility and improving accuracy.

## 📊 **Current vs Target Architecture**

### **❌ CURRENT (Problematic):**
```
Camera → MediaPipe Hands → Hand Landmarks → Custom Finger Counting → Custom Gesture Classification
```

### **✅ TARGET (Correct):**
```
Camera → MediaPipe GestureRecognizer → Direct Gesture Classification → Standard MediaPipe Gesture Names
```

## 🧪 **TDD Methodology**
We will follow **strict RED → GREEN → REFACTOR → TRACK** cycles:

1. **🔴 RED**: Write a failing test that defines the desired behavior
2. **🟢 GREEN**: Write the minimal code to make the test pass
3. **🔵 REFACTOR**: Clean up the code while keeping tests green
4. **📋 TRACK**: Update progress and plan next cycle

---

## 📋 **Phase 1: Research & Analysis**
*Goal: Understand MediaPipe GestureRecognizer API and requirements*

### **Task 1.1: MediaPipe GestureRecognizer API Research**
- [ ] Research MediaPipe GestureRecognizer Python API
- [ ] Document supported gestures vs our current gestures
- [ ] Identify model file requirements
- [ ] Document configuration options
- [ ] Create comparison table: Current vs MediaPipe gestures

### **Task 1.2: Current System Analysis**
- [ ] Document current gesture detection flow
- [ ] Identify all files that use custom gesture recognition
- [ ] Map current gesture names to MediaPipe gesture names
- [ ] Document current test coverage
- [ ] Identify integration points with existing system

### **Task 1.3: Requirements Documentation**
- [ ] Define gesture mapping strategy
- [ ] Plan backwards compatibility approach
- [ ] Document performance requirements
- [ ] Plan testing strategy

**🎯 Success Criteria:** Complete understanding of both systems and clear migration path

---

## 📋 **Phase 2: Test Infrastructure Setup**
*Goal: Create test infrastructure for MediaPipe GestureRecognizer*

### **TDD Cycle 2.1: Test Environment Setup**
**🔴 RED:** Write test for MediaPipe GestureRecognizer availability
```python
def test_mediapipe_gesture_recognizer_import():
    """Test that MediaPipe GestureRecognizer can be imported."""
    from mediapipe.tasks.python import vision
    assert hasattr(vision, 'GestureRecognizer')
```

- [ ] 🔴 Write failing test for MediaPipe imports
- [ ] 🟢 Install/update MediaPipe to version with GestureRecognizer
- [ ] 🔵 Refactor imports to be clean and consistent
- [ ] 📋 Verify MediaPipe version and capabilities

### **TDD Cycle 2.2: Mock Test Data Creation**
**🔴 RED:** Write test for gesture recognition test data
```python
def test_create_mock_gesture_image():
    """Test creation of mock images for gesture testing."""
    mock_image = create_mock_gesture_image("Open_Palm")
    assert mock_image is not None
    assert mock_image.shape == (640, 480, 3)
```

- [ ] 🔴 Write test for mock gesture image creation
- [ ] 🟢 Create mock image generation functions
- [ ] 🔵 Refactor mock data utilities
- [ ] 📋 Validate test data covers all gestures

### **TDD Cycle 2.3: Test Utilities**
**🔴 RED:** Write test for gesture comparison utilities
```python
def test_gesture_result_comparison():
    """Test utilities for comparing gesture results."""
    result1 = GestureResult("Open_Palm", 0.9)
    result2 = GestureResult("Open_Palm", 0.8)
    assert gestures_match(result1, result2, tolerance=0.2)
```

- [ ] 🔴 Write test for result comparison utilities
- [ ] 🟢 Implement gesture result comparison functions
- [ ] 🔵 Refactor utilities for clean interface
- [ ] 📋 Verify utilities work with both old and new gesture formats

**🎯 Success Criteria:** Complete test infrastructure ready for TDD cycles

---

## 📋 **Phase 3: MediaPipe GestureRecognizer Integration**
*Goal: Create new MediaPipe GestureRecognizer wrapper*

### **TDD Cycle 3.1: Basic GestureRecognizer Initialization**
**🔴 RED:** Write test for GestureRecognizer creation
```python
def test_mediapipe_gesture_recognizer_init():
    """Test MediaPipe GestureRecognizer initialization."""
    recognizer = MediaPipeGestureRecognizer()
    assert recognizer.is_initialized()
    assert recognizer.get_supported_gestures() == EXPECTED_GESTURES
```

- [ ] 🔴 Write failing test for GestureRecognizer initialization
- [ ] 🟢 Create `MediaPipeGestureRecognizer` class with basic init
- [ ] 🔵 Refactor initialization code for clarity
- [ ] 📋 Verify initialization works consistently

### **TDD Cycle 3.2: Single Image Gesture Recognition**
**🔴 RED:** Write test for single image processing
```python
def test_recognize_gesture_from_image():
    """Test gesture recognition from single image."""
    recognizer = MediaPipeGestureRecognizer()
    mock_image = create_mock_gesture_image("Open_Palm")
    result = recognizer.recognize_from_image(mock_image)
    assert result.gesture_type == "Open_Palm"
    assert result.confidence > 0.7
```

- [ ] 🔴 Write failing test for image gesture recognition
- [ ] 🟢 Implement `recognize_from_image()` method
- [ ] 🔵 Refactor recognition logic for clean interface
- [ ] 📋 Test with multiple gesture types

### **TDD Cycle 3.3: Video Stream Processing**
**🔴 RED:** Write test for video stream processing
```python
def test_recognize_gesture_from_video():
    """Test gesture recognition from video stream."""
    recognizer = MediaPipeGestureRecognizer()
    mock_frame = create_mock_video_frame("Victory")
    result = recognizer.recognize_from_video(mock_frame, timestamp_ms=1000)
    assert result.gesture_type == "Victory"
```

- [ ] 🔴 Write failing test for video stream recognition
- [ ] 🟢 Implement `recognize_from_video()` method with timestamps
- [ ] 🔵 Refactor video processing logic
- [ ] 📋 Test with realistic video scenarios

### **TDD Cycle 3.4: Configuration Options**
**🔴 RED:** Write test for configuration management
```python
def test_gesture_recognizer_configuration():
    """Test configuration options for GestureRecognizer."""
    config = MediaPipeGestureConfig(
        min_hand_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )
    recognizer = MediaPipeGestureRecognizer(config)
    assert recognizer.get_config().min_hand_detection_confidence == 0.7
```

- [ ] 🔴 Write failing test for configuration
- [ ] 🟢 Implement configuration class and options
- [ ] 🔵 Refactor configuration management
- [ ] 📋 Validate configuration affects recognition behavior

**🎯 Success Criteria:** Working MediaPipe GestureRecognizer wrapper with full functionality

---

## 📋 **Phase 4: Gesture Mapping & Compatibility**
*Goal: Map between old gesture names and MediaPipe gesture names*

### **TDD Cycle 4.1: Gesture Name Mapping**
**🔴 RED:** Write test for gesture name translation
```python
def test_gesture_name_mapping():
    """Test mapping between custom and MediaPipe gesture names."""
    mapper = GestureNameMapper()
    # Old system: "stop" → New system: "Open_Palm"
    assert mapper.old_to_new("stop") == "Open_Palm"
    assert mapper.new_to_old("Open_Palm") == "stop"
    assert mapper.old_to_new("peace") == "Victory"
```

- [ ] 🔴 Write failing test for gesture name mapping
- [ ] 🟢 Implement `GestureNameMapper` class
- [ ] 🔵 Refactor mapping logic for maintainability
- [ ] 📋 Verify all current gestures have mappings

### **TDD Cycle 4.2: Backwards Compatibility Layer**
**🔴 RED:** Write test for backwards compatibility
```python
def test_backwards_compatible_result():
    """Test that new results can be converted to old format."""
    new_result = MediaPipeGestureResult("Open_Palm", 0.9)
    old_result = convert_to_legacy_result(new_result)
    assert old_result.gesture_type == "stop"  # Legacy name
    assert old_result.confidence == 0.9
```

- [ ] 🔴 Write failing test for backwards compatibility
- [ ] 🟢 Implement result conversion functions
- [ ] 🔵 Refactor conversion logic
- [ ] 📋 Test with all existing gesture types

### **TDD Cycle 4.3: Configuration Migration**
**🔴 RED:** Write test for configuration migration
```python
def test_migrate_old_config_to_new():
    """Test migration of old gesture config to new format."""
    old_config = {"shoulder_offset_threshold": 0.1, "palm_facing_confidence": 0.6}
    new_config = migrate_gesture_config(old_config)
    assert new_config.min_hand_detection_confidence > 0
    assert isinstance(new_config, MediaPipeGestureConfig)
```

- [ ] 🔴 Write failing test for config migration
- [ ] 🟢 Implement configuration migration functions
- [ ] 🔵 Refactor migration logic
- [ ] 📋 Verify migration maintains equivalent behavior

**🎯 Success Criteria:** Seamless translation between old and new gesture systems

---

## 📋 **Phase 5: Integration with Existing System**
*Goal: Integrate MediaPipe GestureRecognizer into existing gesture detection pipeline*

### **TDD Cycle 5.1: GestureDetector Integration**
**🔴 RED:** Write test for GestureDetector with new backend
```python
def test_gesture_detector_with_mediapipe_backend():
    """Test GestureDetector using MediaPipe backend."""
    detector = GestureDetector(backend="mediapipe")
    frame = create_test_frame()
    pose_landmarks = create_test_pose_landmarks()
    result = detector.detect_gestures(frame, pose_landmarks)
    assert result.gesture_detected
    assert result.gesture_type in MEDIAPIPE_GESTURES
```

- [ ] 🔴 Write failing test for detector integration
- [ ] 🟢 Add MediaPipe backend option to GestureDetector
- [ ] 🔵 Refactor detector to support multiple backends
- [ ] 📋 Verify integration maintains existing interface

### **TDD Cycle 5.2: Service Layer Integration**
**🔴 RED:** Write test for service layer with new gestures
```python
def test_gesture_service_with_mediapipe():
    """Test gesture service using MediaPipe GestureRecognizer."""
    service = GestureService(gesture_backend="mediapipe")
    event = create_test_gesture_event()
    result = service.process_gesture_event(event)
    assert result.success
    assert result.gesture_name in MEDIAPIPE_GESTURES
```

- [ ] 🔴 Write failing test for service integration
- [ ] 🟢 Update service layer to use new gesture detection
- [ ] 🔵 Refactor service logic for clean separation
- [ ] 📋 Test service integration with existing consumers

### **TDD Cycle 5.3: Event Publishing Compatibility**
**🔴 RED:** Write test for event publishing with new gestures
```python
def test_gesture_events_maintain_compatibility():
    """Test that gesture events maintain backwards compatibility."""
    publisher = GestureEventPublisher(legacy_mode=True)
    mediapipe_result = MediaPipeGestureResult("Open_Palm", 0.9)
    event = publisher.create_event(mediapipe_result)
    assert event.gesture_type == "stop"  # Legacy name for compatibility
```

- [ ] 🔴 Write failing test for event compatibility
- [ ] 🟢 Update event publishing to maintain compatibility
- [ ] 🔵 Refactor event system for clean abstraction
- [ ] 📋 Verify existing event consumers continue working

**🎯 Success Criteria:** Full integration with existing system while maintaining compatibility

---

## 📋 **Phase 6: Performance & Validation**
*Goal: Ensure new system performs better than custom implementation*

### **TDD Cycle 6.1: Performance Benchmarks**
**🔴 RED:** Write test for performance requirements
```python
def test_gesture_recognition_performance():
    """Test that MediaPipe GestureRecognizer meets performance requirements."""
    recognizer = MediaPipeGestureRecognizer()
    frames = create_test_video_frames(100)
    
    start_time = time.time()
    for frame in frames:
        result = recognizer.recognize_from_video(frame, timestamp_ms=0)
    duration = time.time() - start_time
    
    fps = len(frames) / duration
    assert fps >= 15  # Minimum 15 FPS
    assert duration / len(frames) < 0.1  # Max 100ms per frame
```

- [ ] 🔴 Write failing test for performance requirements
- [ ] 🟢 Optimize MediaPipe configuration for performance
- [ ] 🔵 Refactor for performance improvements
- [ ] 📋 Benchmark against old system

### **TDD Cycle 6.2: Accuracy Validation**
**🔴 RED:** Write test for accuracy requirements
```python
def test_gesture_recognition_accuracy():
    """Test gesture recognition accuracy against known test dataset."""
    recognizer = MediaPipeGestureRecognizer()
    test_dataset = load_gesture_test_dataset()
    
    correct_predictions = 0
    for image, expected_gesture in test_dataset:
        result = recognizer.recognize_from_image(image)
        if result.gesture_type == expected_gesture:
            correct_predictions += 1
    
    accuracy = correct_predictions / len(test_dataset)
    assert accuracy >= 0.85  # Minimum 85% accuracy
```

- [ ] 🔴 Write failing test for accuracy requirements
- [ ] 🟢 Tune recognition parameters for accuracy
- [ ] 🔵 Refactor recognition logic for improved accuracy
- [ ] 📋 Compare accuracy with old system

### **TDD Cycle 6.3: Visual Debug Tool Update**
**🔴 RED:** Write test for visual debug tool with new gestures
```python
def test_visual_debug_shows_mediapipe_gestures():
    """Test that visual debug tool displays MediaPipe gestures correctly."""
    debug_tool = VisualGestureDebugTool(backend="mediapipe")
    frame = create_test_frame_with_gesture("Open_Palm")
    annotated_frame = debug_tool.process_frame(frame)
    
    # Check that frame contains proper gesture annotation
    assert "Open_Palm" in extract_text_from_frame(annotated_frame)
    assert "confidence:" in extract_text_from_frame(annotated_frame).lower()
```

- [ ] 🔴 Write failing test for debug tool updates
- [ ] 🟢 Update visual debug tool for MediaPipe gestures
- [ ] 🔵 Refactor debug visualization for clarity
- [ ] 📋 Test debug tool with all gesture types

**🎯 Success Criteria:** New system performs better than old system in speed and accuracy

---

## 📋 **Phase 7: Migration & Cleanup**
*Goal: Migrate existing tests and clean up old code*

### **TDD Cycle 7.1: Existing Test Migration**
**🔴 RED:** Write test to ensure all existing tests pass with new system
```python
def test_existing_gesture_tests_pass_with_mediapipe():
    """Test that existing gesture tests pass when using MediaPipe backend."""
    # Run all existing gesture tests with MediaPipe backend enabled
    test_results = run_existing_gesture_tests(backend="mediapipe")
    assert test_results.all_passed()
    assert test_results.failure_count == 0
```

- [ ] 🔴 Write test for existing test compatibility
- [ ] 🟢 Update existing tests to work with new system
- [ ] 🔵 Refactor tests to be backend-agnostic
- [ ] 📋 Verify 100% test compatibility

### **TDD Cycle 7.2: Configuration Migration**
**🔴 RED:** Write test for automatic configuration migration
```python
def test_automatic_config_migration():
    """Test that old configurations are automatically migrated."""
    old_config_file = "old_gesture_config.yaml"
    migrator = GestureConfigMigrator()
    
    migrator.migrate_config_file(old_config_file)
    
    new_config = load_gesture_config()
    assert isinstance(new_config, MediaPipeGestureConfig)
    assert new_config.is_valid()
```

- [ ] 🔴 Write test for config migration
- [ ] 🟢 Implement automatic configuration migration
- [ ] 🔵 Refactor migration logic
- [ ] 📋 Test migration with various config scenarios

### **TDD Cycle 7.3: Deprecated Code Removal**
**🔴 RED:** Write test to ensure deprecated code is properly removed
```python
def test_deprecated_gesture_code_removed():
    """Test that deprecated gesture recognition code has been removed."""
    # Verify old finger counting logic is no longer accessible
    with pytest.raises(ImportError):
        from src.gesture.classification import _count_extended_fingers
    
    # Verify old gesture names are no longer used internally
    source_code = scan_source_code_for_patterns()
    assert "stop_gesture" not in source_code
    assert "_count_extended_fingers" not in source_code
```

- [ ] 🔴 Write test for deprecated code removal
- [ ] 🟢 Remove deprecated finger counting logic
- [ ] 🔵 Clean up imports and references
- [ ] 📋 Verify no deprecated code remains

**🎯 Success Criteria:** Clean migration with no deprecated code remaining

---

## 📋 **Phase 8: Documentation & Final Validation**
*Goal: Update documentation and perform final validation*

### **Task 8.1: Documentation Updates**
- [ ] Update architecture documentation (ARCHITECTURE.md)
- [ ] Update client integration guide (CLIENT_INTEGRATION.md)
- [ ] Update gesture examples documentation
- [ ] Create MediaPipe migration guide
- [ ] Update API documentation with new gesture names

### **Task 8.2: Final Validation Tests**
- [ ] Run complete test suite (target: 61/61 tests passing)
- [ ] Performance validation against benchmarks
- [ ] Integration testing with real webcam
- [ ] User acceptance testing with visual debug tool
- [ ] Load testing with high-frequency gesture detection

### **Task 8.3: Rollout Planning**
- [ ] Create rollout checklist
- [ ] Plan gradual feature enablement
- [ ] Create rollback procedures
- [ ] Document known issues and workarounds
- [ ] Plan monitoring and metrics collection

**🎯 Success Criteria:** Complete MediaPipe GestureRecognizer migration with improved accuracy and performance

---

## 📊 **Success Metrics**

### **Functional Requirements:**
- [ ] ✅ All 8 MediaPipe gestures supported
- [ ] ✅ Backwards compatibility maintained
- [ ] ✅ All existing tests pass (61/61)
- [ ] ✅ Visual debug tool works correctly

### **Performance Requirements:**
- [ ] ✅ Recognition speed: ≥15 FPS
- [ ] ✅ Latency: ≤100ms per frame
- [ ] ✅ Accuracy: ≥85% on test dataset
- [ ] ✅ Memory usage: ≤100MB total

### **Quality Requirements:**
- [ ] ✅ Test coverage: 100% for new code
- [ ] ✅ Documentation: Complete and up-to-date
- [ ] ✅ Code quality: Clean, maintainable, well-commented
- [ ] ✅ Integration: Seamless with existing system

---

## 🚨 **Risk Mitigation**

### **High Risk Items:**
1. **MediaPipe model dependencies** → Download and version control models
2. **Performance regression** → Continuous benchmarking during development
3. **Breaking existing integrations** → Extensive backwards compatibility testing
4. **Configuration complexity** → Automatic migration tools

### **Rollback Plan:**
1. Keep old gesture system as fallback backend
2. Feature flag for switching between old/new systems
3. Configuration option for legacy mode
4. Quick rollback scripts ready

---

## 📅 **Estimated Timeline**

- **Phase 1-2:** 2-3 days (Research + Test Infrastructure)
- **Phase 3-4:** 3-4 days (Core Implementation + Compatibility)
- **Phase 5-6:** 2-3 days (Integration + Performance)
- **Phase 7-8:** 2-3 days (Migration + Documentation)

**Total Estimated Time:** 9-13 days

---

## 🎯 **Next Steps**

1. **Review this TDD plan** with team/stakeholders
2. **Start with Phase 1.1** - MediaPipe GestureRecognizer API research
3. **Follow strict TDD cycles** - No coding without failing tests first
4. **Update this document** as we discover new requirements
5. **Track progress** using the checkboxes above

**Let's build this right! 🚀** 