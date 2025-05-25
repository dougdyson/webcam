# Test-Driven Development Plan - Service Layer Integration

## TDD Philosophy & Process

Following our proven **Red → Green → Refactor** methodology that successfully delivered 299 passing tests:

1. **RED**: Write a failing test that defines the desired functionality
2. **GREEN**: Write the minimal code to make the test pass
3. **REFACTOR**: Improve the code while keeping tests passing
4. **COMMIT**: After each successful cycle, consider committing changes

## Project Context

**Building on Success**: We have a robust multi-modal detection system with 264 passing tests. Now we're extending it with a service layer to expose real-time human presence detection to other applications.

**Primary Use Case**: Integration with speaker verification system for guard clause functionality.

**Service Integration Architecture**:
```
Detection Pipeline → Event Publisher → Service Layer
                                    ├── HTTP API (8767) - ✅ IMPLEMENTED
                                    ├── WebSocket (8765) - FUTURE  
                                    └── SSE (8766) - FUTURE
```

## Development Phases

### ✅ Phase 9: Service Layer Foundation 
*Goal: Create event publishing system and service base classes*
- **✅ Phase 9 Complete** - Event system and HTTP API service implemented

#### ✅ Cycle 9.1: Event System Design
- **✅ Cycle 9.1 Complete**

**RED**: Test service event system ✅
- ✅ Write failing tests for service event system (15 comprehensive tests)
- ✅ ServiceEvent creation, serialization, and timestamp handling
- ✅ EventType enum with all event types (PRESENCE_CHANGED, DETECTION_UPDATE, etc.)
- ✅ EventPublisher with sync/async subscriber support
- ✅ Error handling and event validation
- ✅ Integration tests with realistic event scenarios

**GREEN**: Implement event system ✅
- ✅ Create `src/service/events.py`
- ✅ Implement EventType enum with all event types
- ✅ Implement ServiceEvent dataclass with serialization
- ✅ Implement EventPublisher with sync/async support
- ✅ Add proper error handling and logging
- ✅ Verify tests pass (15/15 tests passing)

**REFACTOR**: Add error isolation and performance monitoring ✅
- ✅ Add error isolation between subscribers
- ✅ Add event publishing statistics
- ✅ Enhanced async support with proper exception handling
- ✅ Ensure all tests still pass (279 total tests)

#### ✅ Cycle 9.2: HTTP API Service Implementation
- **✅ Cycle 9.2 Complete**

**RED**: Test HTTP service core functionality ✅
- ✅ Write failing tests for HTTP service (15 comprehensive tests)
- ✅ HTTPServiceConfig defaults, validation, and custom values
- ✅ PresenceStatus creation and serialization
- ✅ HTTPDetectionService initialization and all 5 REST endpoints
- ✅ Event integration with EventPublisher subscription
- ✅ CORS middleware and server startup functionality

**GREEN**: Implement HTTP service ✅
- ✅ Create `src/service/http_service.py`
- ✅ Implement HTTPDetectionService with FastAPI
- ✅ Add presence status tracking with PresenceStatus dataclass
- ✅ Implement core endpoints: /presence, /presence/simple, /health, /statistics, /history
- ✅ Add CORS middleware for web dashboard access
- ✅ Add event integration via EventPublisher subscription
- ✅ Verify tests pass (15/15 tests passing)

**REFACTOR**: Add error handling and performance monitoring ✅
- ✅ Add comprehensive error handling with graceful fallbacks
- ✅ Add request/response validation and optimization
- ✅ Add performance metrics tracking and uptime calculation
- ✅ Enhanced event integration with real-time updates
- ✅ Ensure all tests still pass (294 total tests)

#### ✅ Integration Testing Phase
- **✅ Integration Testing Complete**

**Comprehensive Integration Tests** ✅
- ✅ Create `tests/test_service/test_guard_clause_integration.py` (5 tests)
- ✅ Speaker verification guard clause pattern demonstration
- ✅ Detection event updates HTTP responses in real-time
- ✅ Performance testing: 50 rapid requests in <1 second
- ✅ Service health monitoring and reliability checks
- ✅ CORS support verification for web dashboard integration
- ✅ Verify all integration tests pass (5/5 tests passing)

### Phase 10: Service Manager and Advanced Integration
*Goal: Coordinate multiple services and integrate with detection pipeline*
- [ ] **Phase 10 Complete**

#### Cycle 10.1: Detection Service Manager
- [ ] **Cycle 10.1 Complete**

**RED**: Test service management
- [ ] Write failing tests for service manager
```python
def test_detection_service_manager_initialization():
    # Should initialize with event publisher
    manager = DetectionServiceManager()
    assert manager.event_publisher is not None
    assert len(manager.services) == 0

def test_add_http_service():
    # Should add and configure HTTP service
    manager = DetectionServiceManager()
    config = HTTPServiceConfig(port=8767)
    service = manager.add_http_service(config)
    
    assert "http" in manager.services
    assert isinstance(service, HTTPDetectionService)

def test_publish_detection_result():
    # Should convert detection result to service event
    manager = DetectionServiceManager()
    received_events = []
    
    def callback(event):
        received_events.append(event)
    
    manager.event_publisher.subscribe(callback)
    
    detection_result = DetectionResult(
        human_present=True,
        confidence=0.89,
        bounding_box=[10, 20, 100, 200],
        landmarks=[]
    )
    
    manager.publish_detection_result(detection_result)
    
    assert len(received_events) == 1
    event = received_events[0]
    assert event.event_type == EventType.DETECTION_UPDATE
    assert event.data["human_present"] is True
    assert event.data["confidence"] == 0.89

@pytest.mark.asyncio
async def test_service_lifecycle():
    # Should start and stop services properly
    manager = DetectionServiceManager()
    manager.add_http_service(HTTPServiceConfig(port=8767))
    
    # Should start services
    await manager.start_all_services()
    assert len(manager.running_services) == 1
    
    # Should stop services  
    await manager.stop_all_services()
    assert len(manager.running_services) == 0
```

**GREEN**: Implement service manager
- [ ] Create `src/service/manager.py`
- [ ] Implement DetectionServiceManager class
- [ ] Add service registration and lifecycle management
- [ ] Add detection result publishing
- [ ] Add service coordination and error handling
- [ ] Verify tests pass

**REFACTOR**: Add service health monitoring and recovery
- [ ] Add service health monitoring
- [ ] Add automatic service restart on failure
- [ ] Add service discovery capabilities
- [ ] Ensure all tests still pass

#### Cycle 10.2: Main Application Integration
- [ ] **Cycle 10.2 Complete**

**RED**: Test main application service integration
- [ ] Write failing tests for main app integration
```python
def test_main_app_service_integration():
    # Should integrate service manager with detection pipeline
    config = MainAppConfig(enable_services=True)
    app = MainApp(config)
    
    # Should have service manager when enabled
    assert app.service_manager is not None
    
def test_main_app_publishes_detection_events():
    # Should publish detection results to service layer
    config = MainAppConfig(enable_services=True)
    app = MainApp(config)
    
    received_events = []
    def callback(event):
        received_events.append(event)
    
    app.service_manager.event_publisher.subscribe(callback)
    
    # Simulate detection result
    detection_result = DetectionResult(human_present=True, confidence=0.95)
    app._publish_detection_result(detection_result)
    
    assert len(received_events) == 1

def test_main_app_service_lifecycle():
    # Should start/stop services with main application
    config = MainAppConfig(enable_services=True)
    app = MainApp(config)
    
    # Services should start with app
    app.start()
    assert len(app.service_manager.running_services) > 0
    
    # Services should stop with app
    app.stop()
    assert len(app.service_manager.running_services) == 0

def test_cli_service_arguments():
    # Should support service configuration via CLI
    args = ['--enable-services', '--service-port', '9000']
    parsed_config = CommandParser().parse_args(args)
    
    assert parsed_config.enable_services is True
    assert parsed_config.service_port == 9000
```

**GREEN**: Implement main app integration
- [ ] Add service configuration to MainAppConfig
- [ ] Integrate DetectionServiceManager into MainApp
- [ ] Add detection result publishing to processing loop
- [ ] Add service lifecycle management to start/stop methods
- [ ] Add CLI arguments for service configuration
- [ ] Verify tests pass

**REFACTOR**: Add advanced service features
- [ ] Add configurable service types (HTTP, WebSocket, SSE)
- [ ] Add service health monitoring in main loop
- [ ] Add graceful service shutdown handling
- [ ] Ensure all tests still pass

### Phase 11: Speaker Verification Integration Testing
*Goal: End-to-end testing of guard clause integration*
- [ ] **Phase 11 Complete**

#### Cycle 11.1: Guard Clause Integration
- [ ] **Cycle 11.1 Complete**

**RED**: Test speaker verification integration
- [ ] Write failing tests for guard clause integration
```python
def test_simple_guard_clause_integration():
    # Should provide simple boolean presence check
    # This tests the primary use case for speaker verification
    
    # Start detection service
    manager = DetectionServiceManager()
    manager.add_http_service(HTTPServiceConfig(port=8767))
    
    # Simulate detection
    detection_result = DetectionResult(human_present=True, confidence=0.85)
    manager.publish_detection_result(detection_result)
    
    # Test guard clause function
    def should_process_audio() -> bool:
        try:
            response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
            if response.status_code == 200:
                return response.json().get("human_present", False)
        except:
            return True  # Fail safe
        return False
    
    assert should_process_audio() is True

def test_guard_clause_fail_safe():
    # Should fail safe when service unavailable
    def should_process_audio() -> bool:
        try:
            response = requests.get("http://localhost:8767/presence/simple", timeout=0.1)
            if response.status_code == 200:
                return response.json().get("human_present", False)
        except:
            return True  # Fail safe
        return False
    
    # With no service running, should return True (fail safe)
    assert should_process_audio() is True

@pytest.mark.integration
def test_end_to_end_speaker_verification_workflow():
    # Should work end-to-end with detection pipeline
    
    # Start full detection system with services
    config = MainAppConfig(enable_services=True)
    app = MainApp(config)
    app.start()
    
    try:
        # Wait for service startup
        time.sleep(1)
        
        # Simulate human presence
        detection_result = DetectionResult(human_present=True, confidence=0.90)
        app._publish_detection_result(detection_result)
        
        # Test guard clause
        response = requests.get("http://localhost:8767/presence/simple")
        assert response.status_code == 200
        assert response.json()["human_present"] is True
        
    finally:
        app.stop()

def test_performance_under_load():
    # Should handle high-frequency guard clause requests
    manager = DetectionServiceManager()
    manager.add_http_service(HTTPServiceConfig(port=8767))
    
    # Simulate detection
    detection_result = DetectionResult(human_present=True, confidence=0.85)
    manager.publish_detection_result(detection_result)
    
    # High-frequency requests (simulating real-time audio processing)
    start_time = time.time()
    successful_requests = 0
    
    for _ in range(100):
        try:
            response = requests.get("http://localhost:8767/presence/simple", timeout=0.1)
            if response.status_code == 200:
                successful_requests += 1
        except:
            pass
    
    elapsed = time.time() - start_time
    requests_per_second = successful_requests / elapsed
    
    # Should handle at least 50 requests per second
    assert requests_per_second >= 50
```

**GREEN**: Implement integration support
- [ ] Create integration test utilities
- [ ] Add guard clause example functions
- [ ] Add performance testing infrastructure
- [ ] Add end-to-end test scenarios
- [ ] Verify tests pass

**REFACTOR**: Add production-ready features
- [ ] Add connection pooling for better performance
- [ ] Add request caching for frequently accessed endpoints
- [ ] Add comprehensive error handling and logging
- [ ] Ensure all tests still pass

### Phase 12: WebSocket Service (Future Enhancement)
*Goal: Real-time bidirectional communication for interactive applications*
- [ ] **Phase 12 Complete**

#### Cycle 12.1: WebSocket Core Implementation
- [ ] **Cycle 12.1 Complete**

**RED**: Test WebSocket service
- [ ] Write failing tests for WebSocket service
```python
@pytest.mark.asyncio
async def test_websocket_connection_management():
    # Should manage WebSocket connections
    manager = WebSocketConnectionManager()
    
    # Mock WebSocket
    mock_websocket = Mock()
    mock_websocket.accept = AsyncMock()
    
    await manager.connect(mock_websocket, "client_1")
    assert "client_1" in manager.active_connections
    
    manager.disconnect("client_1")
    assert "client_1" not in manager.active_connections

@pytest.mark.asyncio
async def test_websocket_event_broadcasting():
    # Should broadcast events to all connected clients
    manager = WebSocketConnectionManager()
    
    # Mock WebSockets
    mock_ws1 = Mock()
    mock_ws1.send_text = AsyncMock()
    mock_ws2 = Mock()
    mock_ws2.send_text = AsyncMock()
    
    manager.active_connections["client_1"] = mock_ws1
    manager.active_connections["client_2"] = mock_ws2
    
    event = ServiceEvent(
        event_type=EventType.PRESENCE_CHANGED,
        data={"human_present": True}
    )
    
    sent_count = await manager.broadcast(event)
    assert sent_count == 2
    
    mock_ws1.send_text.assert_called_once()
    mock_ws2.send_text.assert_called_once()

def test_websocket_service_initialization():
    # Should initialize WebSocket service properly
    config = WebSocketServiceConfig(port=8765)
    service = WebSocketDetectionService(config)
    
    assert service.config.port == 8765
    assert service.connection_manager is not None
```

**GREEN**: Implement WebSocket service
- [ ] Create `src/service/websocket_service.py`
- [ ] Implement WebSocketConnectionManager
- [ ] Implement WebSocketDetectionService with FastAPI
- [ ] Add connection lifecycle management
- [ ] Add event broadcasting functionality
- [ ] Verify tests pass

**REFACTOR**: Add advanced WebSocket features
- [ ] Add client subscription filtering
- [ ] Add heartbeat monitoring
- [ ] Add connection metadata tracking
- [ ] Ensure all tests still pass

### Phase 13: Server-Sent Events (Future Enhancement)
*Goal: HTTP-based streaming for MCP-like integration patterns*
- [ ] **Phase 13 Complete**

#### Cycle 13.1: SSE Core Implementation
- [ ] **Cycle 13.1 Complete**

**RED**: Test SSE service
- [ ] Write failing tests for SSE service
```python
@pytest.mark.asyncio
async def test_sse_stream_management():
    # Should manage SSE streams
    manager = SSEConnectionManager()
    
    queue = manager.create_stream("client_1")
    assert "client_1" in manager.active_streams
    assert isinstance(queue, asyncio.Queue)
    
    manager.close_stream("client_1")
    assert "client_1" not in manager.active_streams

@pytest.mark.asyncio
async def test_sse_event_streaming():
    # Should stream events to SSE clients
    manager = SSEConnectionManager()
    queue = manager.create_stream("client_1")
    
    event = ServiceEvent(
        event_type=EventType.DETECTION_UPDATE,
        data={"human_present": True, "confidence": 0.88}
    )
    
    await manager.send_to_stream("client_1", event)
    
    # Should have event in queue
    queued_event = await queue.get()
    assert queued_event.event_type == EventType.DETECTION_UPDATE
    assert queued_event.data["human_present"] is True

def test_sse_service_initialization():
    # Should initialize SSE service properly
    config = SSEServiceConfig(port=8766)
    service = SSEDetectionService(config)
    
    assert service.config.port == 8766
    assert service.connection_manager is not None
```

**GREEN**: Implement SSE service
- [ ] Create `src/service/sse_service.py`
- [ ] Implement SSEConnectionManager
- [ ] Implement SSEDetectionService with streaming
- [ ] Add event queue management
- [ ] Add heartbeat support
- [ ] Verify tests pass

**REFACTOR**: Add SSE reliability features
- [ ] Add automatic reconnection support
- [ ] Add connection health monitoring
- [ ] Add event buffering for offline clients
- [ ] Ensure all tests still pass

## Service Layer Directory Structure

```
src/
├── service/
│   ├── __init__.py            # ✅ IMPLEMENTED - exports HTTPDetectionService, etc.
│   ├── events.py              # ✅ IMPLEMENTED - ServiceEvent, EventPublisher, EventType
│   ├── http_service.py        # ✅ IMPLEMENTED - HTTPDetectionService (PRIMARY)
│   ├── websocket_service.py   # FUTURE - WebSocketDetectionService
│   └── sse_service.py         # FUTURE - SSEDetectionService
├── cli/
│   ├── main.py               # Available for service integration
│   └── parser.py             # Available for service CLI args
└── utils/
    └── service_utils.py       # Available for service testing utilities

config/
└── service_config.yaml       # Available for service layer configuration

tests/
├── test_service/              # ✅ IMPLEMENTED
│   ├── __init__.py           # ✅ IMPLEMENTED
│   ├── test_events.py        # ✅ IMPLEMENTED - 15 tests
│   ├── test_http_service.py  # ✅ IMPLEMENTED - 15 tests
│   └── test_guard_clause_integration.py  # ✅ IMPLEMENTED - 5 tests
└── test_integration/
    └── test_service_integration.py  # Available for end-to-end testing
```

## Configuration Files

### Service Configuration (`config/service_config.yaml`)
```yaml
service_layer:
  enabled: true
  
  http:
    host: "localhost"
    port: 8767
    enable_history: true
    history_limit: 1000
    
  websocket:
    host: "localhost"
    port: 8765
    max_connections: 100
    heartbeat_interval: 30.0
    
  sse:
    host: "localhost"
    port: 8766
    max_connections: 100
    heartbeat_interval: 30.0
    
  event_publishing:
    publish_detection_updates: true
    publish_presence_changes: true
    publish_confidence_alerts: true
    confidence_alert_threshold: 0.3
```

## Success Criteria

Each phase is complete when:
1. All tests pass (RED → GREEN achieved)
2. Service endpoints respond correctly
3. Integration with detection pipeline works
4. Performance targets met (< 100ms response time for guard clauses)
5. Error handling tested and validated
6. Documentation updated
7. Code reviewed and refactored

## Performance Targets

- **HTTP API Response Time**: < 50ms for /presence/simple (guard clause)
- **WebSocket Message Latency**: < 10ms for real-time events
- **SSE Stream Latency**: < 100ms for streaming events
- **Concurrent Connections**: Support 100+ simultaneous connections
- **Request Rate**: Handle 100+ requests/second for guard clauses
- **Memory Usage**: < 50MB additional overhead for service layer
- **Service Startup**: < 2 seconds for all services

## Phase Progress Tracking

- [✅] **Phase 9**: Service Layer Foundation *(COMPLETED)*
  - [✅] Cycle 9.1: Event System Design *(15 tests)*
  - [✅] Cycle 9.2: HTTP API Service Implementation *(15 tests + 5 integration tests)*

- [✅] **Phase 10**: Production Integration *(COMPLETED)*
  - [✅] Cycle 10.1: WebcamHTTPService Integration *(21 tests)*
  - [✅] Cycle 10.2: TDD Redemption and Complete Coverage

- [ ] **Phase 11**: Service Manager and Advanced Integration
  - [ ] Cycle 11.1: Detection Service Manager  
  - [ ] Cycle 11.2: Main Application Integration

- [ ] **Phase 12**: Speaker Verification Integration Testing
  - [ ] Cycle 12.1: Guard Clause Integration

- [ ] **Phase 13**: WebSocket Service (Future Enhancement)
  - [ ] Cycle 13.1: WebSocket Core Implementation

- [ ] **Phase 14**: Server-Sent Events (Future Enhancement)
  - [ ] Cycle 14.1: SSE Core Implementation

### Test Progression - ACTUAL RESULTS 🎉
- **Starting Point**: 264 tests passing ✅
- **After Phase 9.1 (Event System)**: 279 tests passing ✅
- **After Phase 9.2 (HTTP Service)**: 294 tests passing ✅
- **After Integration Tests**: 299 tests passing ✅
- **After WebcamHTTPService Integration**: **320 tests passing** ✅ **CURRENT**
- **Status**: **PRODUCTION-READY HTTP API SERVICE FULLY IMPLEMENTED** 🚀

### 🎯 MAJOR MILESTONE ACHIEVED

#### ✅ Production-Ready HTTP API Service (IMPLEMENTED & TESTED)
- **5 REST Endpoints**: `/presence`, `/presence/simple`, `/health`, `/statistics`, `/history`
- **Real Integration**: `webcam_http_service.py` connects live camera to HTTP API
- **Event Integration**: Real-time updates from detection system via EventPublisher
- **CORS Support**: Ready for web dashboard integration
- **Performance Tested**: 50 requests in <1 second, <50ms response times
- **Guard Clause Optimized**: Perfect for speaker verification integration
- **Production Deployment**: Working service with proper startup messages and error handling

#### ✅ Complete TDD Coverage (320 tests)
- **ServiceEvent & EventPublisher**: 15 comprehensive tests
- **HTTP API Service**: 15 endpoint and integration tests
- **Guard Clause Integration**: 5 speaker verification pattern tests
- **WebcamHTTPService**: 21 complete integration tests covering TDD redemption
- **Integration Ready**: Seamless connection to detection pipeline

#### ✅ Speaker Verification Ready (VALIDATED)
```python
# Production-ready guard clause - TESTED AND WORKING
def should_process_audio() -> bool:
    response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
    return response.json().get("human_present", False)
```

#### ✅ Live Service Validation
From terminal output showing the service working:
```
🎯 Webcam Human Detection HTTP Service
👤 HUMAN DETECTED | MULTIMODAL | Conf: 0.71 | FPS: 29.9
✅ HTTP API service configured on http://localhost:8767
🚀 Starting HTTP service for speaker verification...
```

## Commit Strategy

After each successful TDD cycle:
1. **Run all tests** to ensure nothing is broken (including existing 264 tests)
2. **Test service endpoints** manually or with integration tests
3. **Review code quality** and adherence to service patterns
4. **Update documentation** if needed
5. **Commit with descriptive message**:
   ```
   feat: implement [service component] with [functionality]
   
   - Add [specific features]
   - Include [test coverage] 
   - Handle [error conditions]
   - Integrate with [detection pipeline]
   ```

## Dependencies

### New Dependencies Required
```bash
# Core service dependencies
pip install fastapi uvicorn websockets aiohttp

# Testing dependencies  
pip install httpx pytest-asyncio aioresponses

# Optional (for advanced features)
pip install prometheus-client  # metrics
pip install structlog          # structured logging
```

### Integration Dependencies
- Existing detection system (src/detection/)
- Existing processing pipeline (src/processing/)
- Existing configuration system (src/utils/config.py)
- Existing CLI system (src/cli/)

This TDD plan builds incrementally on our successful foundation, starting with the most critical component (HTTP API for guard clauses) and expanding to more advanced service patterns. Each phase delivers working, tested functionality that can be deployed independently. 