# Test-Driven Development Plan - Webcam Human Detection

## TDD Philosophy & Process

Following strict **Red → Green → Refactor** methodology:

1. **RED**: Write a failing test that defines the desired functionality
2. **GREEN**: Write the minimal code to make the test pass
3. **REFACTOR**: Improve the code while keeping tests passing
4. **COMMIT**: After each successful cycle, consider committing changes

## Project Status Summary

**🎉 PRODUCTION READY + GESTURE RECOGNITION MAJOR PROGRESS**: Complete multi-modal detection system with HTTP API service + Gesture Recognition Phase 14 advancing rapidly!
- **339 comprehensive tests passing** ✅ (+19 new gesture tests!)
- **Core Detection System**: Phases 1-6 complete (264 tests)
- **Service Layer**: Phases 9-10 complete (+56 tests = 320 total)
- **Gesture Recognition**: Phase 14.1 nearly complete! (+19 tests = 339 total) 🚀 **MAJOR PROGRESS!**
- **HTTP API Service**: Production ready with speaker verification guard clause integration
- **Live Service**: `webcam_http_service.py` fully operational

## Development Phases

### ✅ COMPLETED PHASES (Phases 1-6: Core System)

#### ✅ Phase 1: Foundation & Configuration 
- ✅ Cycle 1.1: Configuration Management
- ✅ Cycle 1.2: Logging Setup

#### ✅ Phase 2: Camera System (Core Foundation)
- ✅ Cycle 2.1: Camera Configuration  
- ✅ Cycle 2.2: Basic Camera Manager
- ✅ Cycle 2.3: Frame Capture
- ✅ Cycle 2.4: Frame Queue

#### ✅ Phase 3: Queue and Processing Infrastructure
- ✅ Cycle 3.1: Frame Queue
- ✅ Cycle 3.2: Async Frame Processor

#### ✅ Phase 4: Human Detection
- ✅ Cycle 4.1: Detection Result Structure
- ✅ Cycle 4.2: Abstract Detector Base
- ✅ Cycle 4.3: MediaPipe Detector Implementation

#### ✅ Phase 5: Presence Filtering and Decision Making
- ✅ Cycle 5.1: Presence Filter

#### ✅ Phase 6: Integration and CLI
- ✅ Cycle 6.1: Main Application Coordinator
- ✅ Cycle 6.2: CLI Interface

**Core System Status**: 264 tests passing ✅

### ✅ COMPLETED PHASES (Phases 9-10: Service Layer)

#### ✅ Phase 9: Service Layer Foundation 
*Goal: Create event publishing system and HTTP API service*

**✅ Cycle 9.1: Event System Design**
- ✅ ServiceEvent creation, serialization, and timestamp handling
- ✅ EventType enum with all event types (PRESENCE_CHANGED, DETECTION_UPDATE, etc.)
- ✅ EventPublisher with sync/async subscriber support
- ✅ Error handling and event validation
- ✅ 15 comprehensive tests

**✅ Cycle 9.2: HTTP API Service Implementation**
- ✅ HTTPDetectionService with FastAPI and 5 REST endpoints
- ✅ CORS middleware for web dashboard access
- ✅ Event integration via EventPublisher subscription
- ✅ Performance optimization and error handling
- ✅ 15 comprehensive tests + 5 integration tests

#### ✅ Phase 10: Production Integration
*Goal: Complete service integration with detection pipeline*

**✅ Cycle 10.1: WebcamHTTPService Integration**
- ✅ Live camera detection integrated with HTTP API
- ✅ Production-ready service: `webcam_http_service.py`
- ✅ Real-time detection events updating HTTP responses
- ✅ Performance validation: 50 requests/second sustained
- ✅ 21 comprehensive integration tests

**Service Layer Status**: +56 tests (320 total) ✅

### 🎯 PRODUCTION MILESTONE ACHIEVED

#### ✅ HTTP API Service (FULLY IMPLEMENTED)
- **5 REST Endpoints**: `/presence`, `/presence/simple`, `/health`, `/statistics`, `/history`
- **Guard Clause Ready**: Optimized for speaker verification integration
- **Performance**: <50ms response times, 50+ requests/second
- **CORS Support**: Ready for web dashboard integration
- **Production Deployment**: Working service with proper startup/error handling

#### ✅ Speaker Verification Integration (VALIDATED)
```python
# Production-ready guard clause pattern
def should_process_audio() -> bool:
    response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
    return response.json().get("human_present", False)
```

### ⏳ PLANNED PHASES (Future Enhancement)

#### Phase 7: Error Handling and Robustness
- ✅ Cycle 7.1: Camera Error Recovery (Simplified)
- [ ] Cycle 7.2: Performance Monitoring

#### Phase 8: End-to-End Integration
- [ ] Cycle 8.1: Integration Tests

#### Phase 11: Service Manager and Advanced Integration
- [ ] Cycle 11.1: Detection Service Manager  
- [ ] Cycle 11.2: Main Application Integration

#### Phase 12: WebSocket Service (Future Enhancement)
- [ ] Cycle 12.1: WebSocket Core Implementation

#### Phase 13: Server-Sent Events (Future Enhancement)
- [ ] Cycle 13.1: SSE Core Implementation

### 🎯 NEW FEATURES IN DEVELOPMENT

#### Phase 14: Gesture Recognition System
*Goal: Implement "hand up at shoulder level with palm facing camera" detection*

**✅ Cycle 14.1: Gesture Detection Algorithm** *(100% COMPLETE - COMMITTED 🎉)*
- ✅ Test gesture specification: Hand up at shoulder level with palm facing camera (**COMMITTED** 🎉)
- ✅ Test boundary conditions (hand below shoulder, palm not facing camera) (**COMMITTED** 🎉)
- ✅ Test gesture confidence calculation (**COMMITTED** 🎉)
- ✅ Test input validation and error handling (**COMMITTED** 🎉)
- ✅ Test MediaPipe hands integration and landmark extraction (**COMMITTED** 🎉)
- ✅ Test shoulder reference point calculation from existing pose data (**COMMITTED** 🎉)
- ✅ Test palm orientation analysis (facing camera detection) (**COMMITTED** 🎉)
- ✅ **COMPLETE**: 23 gesture algorithm tests implemented and passing (**COMMITTED** 🎉)

**✅ Cycle 14.2: GestureDetector Implementation** *(100% COMPLETE - COMMITTED 🎉)*
- ✅ Test GestureDetector class creation following existing patterns (**COMMITTED** 🎉)
- ✅ Test gesture detection initialization and cleanup (**COMMITTED** 🎉) 
- ✅ Test detect_gestures() method with GestureResult return (**COMMITTED** 🎉)
- ✅ Test integration with MediaPipe hands solution (**COMMITTED** 🎉)
- ✅ Test error handling for hand detection failures (**COMMITTED** 🎉)
- ✅ Test resource management and MediaPipe context sharing (**COMMITTED** 🎉)
- ✅ **COMPLETE**: 12 gesture detector tests implemented and passing (**COMMITTED** 🎉)

**[ ] Cycle 14.3: Gesture Result and Event Integration** *(STARTING NOW 🚀)*
- [ ] Test GestureResult dataclass enhancement (duration tracking, metadata)
- [ ] Test new event types: GESTURE_DETECTED, GESTURE_LOST, GESTURE_CONFIDENCE_UPDATE
- [ ] Test gesture event data structure and serialization
- [ ] Test integration with existing EventPublisher
- [ ] Test gesture debouncing and smoothing (prevent false triggers)
- [ ] Test event timing and duration tracking
- [ ] Estimated: 8-10 tests

#### Phase 15: SSE Service Implementation  
*Goal: Real-time gesture event streaming via Server-Sent Events*

**[ ] Cycle 15.1: SSE Service Core**
- [ ] Test SSE endpoint creation on port 8766 (as planned in architecture)
- [ ] Test Server-Sent Events streaming format and headers
- [ ] Test multiple client connection management
- [ ] Test client disconnection detection and cleanup
- [ ] Test CORS support for web dashboard integration
- [ ] Test heartbeat mechanism for connection health
- [ ] Estimated: 12-15 tests

**[ ] Cycle 15.2: SSE Event Filtering and Integration**
- [ ] Test gesture-specific event filtering (only gesture events via SSE)
- [ ] Test real-time event streaming when gestures detected
- [ ] Test EventPublisher subscription for SSE service
- [ ] Test event queue management for multiple clients
- [ ] Test performance: multiple clients receiving simultaneous events
- [ ] Test error isolation: SSE failures don't affect core detection
- [ ] Estimated: 10-12 tests

**[ ] Cycle 15.3: SSE Service Configuration and Health**
- [ ] Test SSE service configuration (SSEServiceConfig)
- [ ] Test service health endpoints (/health)
- [ ] Test service startup and graceful shutdown
- [ ] Test integration with existing service patterns
- [ ] Test logging and monitoring capabilities
- [ ] Estimated: 6-8 tests

#### Phase 16: Gesture + SSE Pipeline Integration
*Goal: Complete human presence → gesture detection → SSE streaming workflow*

**[ ] Cycle 16.1: Conditional Gesture Detection**
- [ ] Test gesture detection only runs when human is present (performance optimization)
- [ ] Test integration with existing MultiModalDetector presence results
- [ ] Test gesture detection skipped when confidence below threshold
- [ ] Test seamless integration with existing frame processing pipeline
- [ ] Test resource sharing between pose and gesture detection
- [ ] Test performance impact measurement
- [ ] Estimated: 8-10 tests

**[ ] Cycle 16.2: End-to-End Gesture → SSE Flow**
- [ ] Test complete pipeline: Camera → Presence → Gesture → SSE Event
- [ ] Test real-time gesture detection with immediate SSE streaming
- [ ] Test multiple gesture events handled correctly
- [ ] Test gesture lost events when hand goes down
- [ ] Test client receives events in correct format
- [ ] Test performance: gesture detection → SSE streaming latency
- [ ] Estimated: 10-12 tests

**[ ] Cycle 16.3: Production Integration and Performance**
- [ ] Test integration with existing webcam_http_service.py
- [ ] Test simultaneous HTTP API + SSE service operation
- [ ] Test performance with both presence detection and gesture detection
- [ ] Test error handling and graceful degradation
- [ ] Test configuration management for gesture + SSE features
- [ ] Test memory usage and resource management
- [ ] Estimated: 8-10 tests

### 📊 Enhanced Test Progression Tracking

#### Current Status: 355 tests ✅
- **Core Detection System** (Phases 1-6): 264 tests ✅
- **Service Layer** (Phases 9-10): +56 tests (320 total) ✅
- **Gesture Recognition Phase 14.1**: +23 tests (343 total) ✅ **COMMITTED**
- **Gesture Recognition Phase 14.2**: +12 tests (355 total) ✅ **COMMITTED**

#### Gesture Recognition Targets (Phases 14-16):
- **Phase 14.1 Complete**: 23 algorithm tests ✅ **COMMITTED**
- **Phase 14.2 Complete**: 12 detector tests ✅ **COMMITTED**
- **Phase 14.3 Target**: +8-10 tests (363-365 total)
- **Phase 15 Complete**: +28-35 tests (391-400 total)  
- **Phase 16 Complete**: +26-32 tests (417-432 total)
- **🎯 Final Target**: **~420 comprehensive tests**

### 🏗️ Enhanced Architecture Integration

#### New Components Structure:
```
src/
├── detection/
│   └── gesture_detector.py      # NEW: Hand gesture detection
├── gesture/                     # NEW: Gesture-specific logic
│   ├── __init__.py
│   ├── hand_detection.py        # MediaPipe hands integration
│   ├── classification.py       # "Hand up" algorithm
│   └── result.py               # GestureResult dataclass
├── service/
│   └── sse_service.py          # NEW: Server-Sent Events (port 8766)
└── ...existing structure
```

#### New Test Structure:
```
tests/
├── test_gesture/               # NEW: Gesture detection tests
│   ├── test_hand_detection.py  # MediaPipe hands tests
│   ├── test_classification.py  # Hand up algorithm tests
│   ├── test_gesture_detector.py # Main detector tests
│   └── test_gesture_result.py  # Result format tests
├── test_service/
│   └── test_sse_service.py     # NEW: SSE service tests
└── test_integration/
    └── test_gesture_sse_integration.py # NEW: End-to-end tests
```

### 🎯 Success Criteria for Gesture + SSE Features

#### Gesture Detection:
- [ ] Hand up at shoulder level accurately detected (>90% accuracy)
- [ ] Palm facing camera correctly identified
- [ ] Gesture detection only runs when human present (performance)
- [ ] Smooth gesture transitions (debouncing works)
- [ ] Resource usage acceptable (<20% additional CPU)

#### SSE Service:
- [ ] Real-time gesture events streamed to clients (<100ms latency)
- [ ] Multiple clients supported simultaneously (10+ clients)
- [ ] Connection management robust (auto-cleanup, heartbeat)
- [ ] CORS enabled for web dashboard integration
- [ ] Service fails gracefully without affecting core detection

#### Integration:
- [ ] End-to-end pipeline works: Camera → Presence → Gesture → SSE
- [ ] Performance targets met (gesture detection + streaming)
- [ ] All tests pass (target: ~420 comprehensive tests)
- [ ] Documentation updated
- [ ] Production deployment ready

## Test Progression History

### Core System Development (Phases 1-6)
- Phase 2 complete: 67 tests
- Phase 3 complete: 106 tests  
- After Detection Result: 126 tests
- After Detector Base: 147 tests
- After MediaPipe Detector: 170 tests
- After Presence Filter: 197 tests
- After Main App Coordinator: 219 tests
- After CLI Interface: 240 tests
- After Integration & Bug Fixes: 246 tests
- **Core System Complete**: 264 tests ✅

### Service Layer Development (Phases 9-10)
- Starting Point: 264 tests
- After Event System (Phase 9.1): 279 tests
- After HTTP Service (Phase 9.2): 294 tests
- After Integration Tests: 299 tests
- **After WebcamHTTPService Integration**: **320 tests** ✅

## Service Layer Architecture

```
Detection Pipeline → EventPublisher → Service Layer
                                    ├── HTTP API Service (8767) ✅ IMPLEMENTED
                                    ├── WebSocket Service (8765) - FUTURE
                                    └── SSE Service (8766) - FUTURE
```

### Current Service Features ✅
- **Real-time Updates**: Detection events immediately update HTTP responses
- **5 REST Endpoints**: Complete API for presence detection
- **Guard Clause Optimized**: Perfect `/presence/simple` endpoint for speaker verification
- **Performance Tested**: 50 requests/second sustained
- **Production Ready**: Error handling, CORS, health checks

## Success Criteria (Achieved ✅)

- ✅ All tests pass (320/320 tests passing)
- ✅ Service endpoints respond correctly (<50ms response times)
- ✅ Integration with detection pipeline works (EventPublisher pattern)
- ✅ Performance targets met (50+ requests/second for guard clauses)
- ✅ Error handling tested and validated (graceful fallbacks)
- ✅ Documentation updated (ARCHITECTURE.md, README.md)
- ✅ Production deployment ready (`webcam_http_service.py`)

## Current Production Status

**🚀 READY FOR PRODUCTION USE**
- **Start Service**: `python webcam_http_service.py`
- **Test Service**: `curl http://localhost:8767/presence/simple`
- **Speaker Verification**: Ready for guard clause integration
- **Test Coverage**: 320 comprehensive tests
- **Performance**: Validated for real-time applications

---

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
pip install fastapi uvicorn httpx  # Service layer dependencies
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

## Current Directory Structure

```
tests/ (320 tests total)
├── test_camera/              # Camera system tests
├── test_detection/           # Detection algorithm tests  
├── test_processing/          # Processing pipeline tests
├── test_service/             # ✅ Service layer tests (35 tests)
│   ├── test_events.py        # EventPublisher tests (15 tests)
│   ├── test_http_service.py  # HTTP API tests (15 tests)
│   └── test_guard_clause_integration.py # Integration tests (5 tests)
├── test_integration/         # Integration test scenarios  
└── fixtures/                 # Test images/videos
```