# Test-Driven Development Plan - Service Layer Integration

## TDD Philosophy & Process

Following our proven **Red → Green → Refactor** methodology that successfully delivered 264 passing tests:

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
                                    ├── HTTP API (8767) - PRIMARY
                                    ├── WebSocket (8765) - SECONDARY  
                                    └── SSE (8766) - FUTURE
```

## Development Phases

### Phase 9: Service Layer Foundation 
*Goal: Create event publishing system and service base classes*

#### Cycle 9.1: Event System Design
- [ ] **Cycle 9.1 Complete**

**RED**: Test service event system
- [ ] Write failing tests for service event system
```python
def test_service_event_creation():
    # Should create ServiceEvent with required fields
    event = ServiceEvent(
        event_type=EventType.PRESENCE_CHANGED,
        data={"human_present": True, "confidence": 0.85}
    )
    assert event.event_type == EventType.PRESENCE_CHANGED
    assert event.data["human_present"] is True
    assert isinstance(event.timestamp, datetime)

def test_service_event_serialization():
    # Should serialize to JSON for transmission
    event = ServiceEvent(event_type=EventType.DETECTION_UPDATE)
    json_str = event.to_json()
    data = json.loads(json_str)
    assert data["event_type"] == "detection_update"
    assert "timestamp" in data

def test_event_publisher_sync_publish():
    # Should publish to synchronous subscribers
    publisher = EventPublisher()
    received_events = []
    
    def callback(event):
        received_events.append(event)
    
    publisher.subscribe(callback)
    event = ServiceEvent(event_type=EventType.PRESENCE_CHANGED)
    publisher.publish(event)
    
    assert len(received_events) == 1
    assert received_events[0] == event

def test_event_publisher_async_publish():
    # Should publish to asynchronous subscribers
    publisher = EventPublisher()
    received_events = []
    
    async def async_callback(event):
        received_events.append(event)
    
    publisher.subscribe_async(async_callback)
    event = ServiceEvent(event_type=EventType.DETECTION_UPDATE)
    publisher.publish(event)
    
    # Wait for async completion
    await asyncio.sleep(0.1)
    assert len(received_events) == 1
```

**GREEN**: Implement event system
- [ ] Create `src/service/events.py`
- [ ] Implement EventType enum with all event types
- [ ] Implement ServiceEvent dataclass with serialization
- [ ] Implement EventPublisher with sync/async support
- [ ] Add proper error handling and logging
- [ ] Verify tests pass

**REFACTOR**: Add error isolation and performance monitoring
- [ ] Add error isolation between subscribers
- [ ] Add event publishing statistics
- [ ] Ensure all tests still pass

#### Cycle 9.2: Service Configuration Management
- [ ] **Cycle 9.2 Complete**

**RED**: Test service configuration
- [ ] Write failing tests for service configuration
```python
def test_http_service_config_defaults():
    # Should create config with reasonable defaults
    config = HTTPServiceConfig()
    assert config.host == "localhost"
    assert config.port == 8767
    assert config.enable_history is True

def test_websocket_service_config_validation():
    # Should validate configuration parameters
    with pytest.raises(ServiceConfigError):
        WebSocketServiceConfig(port=-1)  # Invalid port
    
    with pytest.raises(ServiceConfigError):
        WebSocketServiceConfig(max_connections=0)  # Invalid max

def test_service_config_from_yaml():
    # Should load configuration from YAML file
    config_data = {
        "http": {"port": 9000, "enable_history": False},
        "websocket": {"port": 9001, "max_connections": 50}
    }
    
    http_config = HTTPServiceConfig.from_dict(config_data["http"])
    assert http_config.port == 9000
    assert http_config.enable_history is False
```

**GREEN**: Implement service configuration
- [ ] Create `src/service/config.py`
- [ ] Implement service configuration dataclasses
- [ ] Add configuration validation and error handling
- [ ] Add YAML loading support
- [ ] Verify tests pass

**REFACTOR**: Add environment variable overrides
- [ ] Add environment variable override support
- [ ] Add configuration validation and defaults
- [ ] Ensure all tests still pass

### Phase 10: HTTP API Service (Primary Integration)
*Goal: Simple HTTP endpoints for speaker verification guard clauses*

#### Cycle 10.1: HTTP Service Core Implementation
- [ ] **Cycle 10.1 Complete**

**RED**: Test HTTP service core functionality
- [ ] Write failing tests for HTTP service
```python
@pytest.fixture
def http_service():
    config = HTTPServiceConfig(port=8767)
    return HTTPDetectionService(config)

def test_http_service_initialization(http_service):
    # Should initialize with proper configuration
    assert http_service.config.port == 8767
    assert http_service.current_status.human_present is False

@pytest.mark.asyncio
async def test_http_presence_endpoint():
    # Should return current presence status
    config = HTTPServiceConfig(port=8767)
    service = HTTPDetectionService(config)
    
    # Mock FastAPI test client
    with TestClient(service.app) as client:
        response = client.get("/presence")
        assert response.status_code == 200
        data = response.json()
        assert "human_present" in data
        assert "confidence" in data
        assert "timestamp" in data

@pytest.mark.asyncio  
async def test_http_simple_presence_endpoint():
    # Should return simple boolean presence
    config = HTTPServiceConfig(port=8767)
    service = HTTPDetectionService(config)
    
    with TestClient(service.app) as client:
        response = client.get("/presence/simple")
        assert response.status_code == 200
        data = response.json()
        assert "human_present" in data
        assert isinstance(data["human_present"], bool)

def test_http_health_endpoint():
    # Should return service health status
    config = HTTPServiceConfig(port=8767)
    service = HTTPDetectionService(config)
    
    with TestClient(service.app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
```

**GREEN**: Implement HTTP service
- [ ] Create `src/service/http_service.py`
- [ ] Implement HTTPDetectionService with FastAPI
- [ ] Add presence status tracking
- [ ] Implement core endpoints: /presence, /presence/simple, /health
- [ ] Add CORS middleware for web access
- [ ] Verify tests pass

**REFACTOR**: Add error handling and performance monitoring
- [ ] Add comprehensive error handling
- [ ] Add request/response logging
- [ ] Add performance metrics tracking
- [ ] Ensure all tests still pass

#### Cycle 10.2: Detection Integration
- [ ] **Cycle 10.2 Complete**

**RED**: Test detection system integration
- [ ] Write failing tests for detection integration
```python
def test_http_service_detection_integration():
    # Should update status when detection events received
    config = HTTPServiceConfig()
    service = HTTPDetectionService(config)
    
    # Create detection event
    event = ServiceEvent(
        event_type=EventType.DETECTION_UPDATE,
        data={
            "human_present": True,
            "confidence": 0.92,
            "timestamp": datetime.now().isoformat()
        }
    )
    
    # Simulate detection event
    service._handle_detection_event(event)
    
    assert service.current_status.human_present is True
    assert service.current_status.confidence == 0.92

def test_http_service_history_tracking():
    # Should track detection history when enabled
    config = HTTPServiceConfig(enable_history=True, history_limit=3)
    service = HTTPDetectionService(config)
    
    # Send multiple detection events
    for i in range(5):
        event = ServiceEvent(
            event_type=EventType.DETECTION_UPDATE,
            data={"human_present": i % 2 == 0, "confidence": 0.8}
        )
        service._handle_detection_event(event)
    
    # Should have limited history
    assert len(service.detection_history) == 3
    
    with TestClient(service.app) as client:
        response = client.get("/history")
        assert response.status_code == 200
        assert len(response.json()["history"]) == 3

def test_http_service_statistics_endpoint():
    # Should provide detection statistics
    config = HTTPServiceConfig()
    service = HTTPDetectionService(config)
    
    # Simulate some detections
    for _ in range(3):
        event = ServiceEvent(
            event_type=EventType.DETECTION_UPDATE,
            data={"human_present": True, "confidence": 0.85}
        )
        service._handle_detection_event(event)
    
    with TestClient(service.app) as client:
        response = client.get("/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["detection_count"] == 3
        assert "uptime_seconds" in data
```

**GREEN**: Implement detection integration
- [ ] Add detection event handling to HTTP service
- [ ] Implement history tracking with size limits
- [ ] Add statistics tracking and endpoint
- [ ] Integrate with EventPublisher for detection events
- [ ] Verify tests pass

**REFACTOR**: Add advanced features and optimization
- [ ] Add configurable history retention
- [ ] Add detection rate limiting and filtering
- [ ] Add performance monitoring
- [ ] Ensure all tests still pass

### Phase 11: Service Manager and Integration
*Goal: Coordinate multiple services and integrate with detection pipeline*

#### Cycle 11.1: Detection Service Manager
- [ ] **Cycle 11.1 Complete**

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

#### Cycle 11.2: Main Application Integration
- [ ] **Cycle 11.2 Complete**

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

### Phase 12: Speaker Verification Integration Testing
*Goal: End-to-end testing of guard clause integration*

#### Cycle 12.1: Guard Clause Integration
- [ ] **Cycle 12.1 Complete**

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

### Phase 13: WebSocket Service (Future Enhancement)
*Goal: Real-time bidirectional communication for interactive applications*

#### Cycle 13.1: WebSocket Core Implementation
- [ ] **Cycle 13.1 Complete**

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

### Phase 14: Server-Sent Events (Future Enhancement)
*Goal: HTTP-based streaming for MCP-like integration patterns*

#### Cycle 14.1: SSE Core Implementation
- [ ] **Cycle 14.1 Complete**

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
│   ├── __init__.py
│   ├── events.py              # ServiceEvent, EventPublisher, EventType
│   ├── config.py              # Service configuration dataclasses
│   ├── manager.py             # DetectionServiceManager
│   ├── http_service.py        # HTTPDetectionService (PRIMARY)
│   ├── websocket_service.py   # WebSocketDetectionService (FUTURE)
│   └── sse_service.py         # SSEDetectionService (FUTURE)
├── cli/
│   ├── main.py               # Updated with service integration
│   └── parser.py             # Updated with service CLI args
└── utils/
    └── service_utils.py       # Service testing utilities

config/
└── service_config.yaml       # Service layer configuration

tests/
├── test_service/
│   ├── test_events.py
│   ├── test_config.py
│   ├── test_manager.py
│   ├── test_http_service.py
│   ├── test_websocket_service.py
│   └── test_sse_service.py
└── test_integration/
    └── test_service_integration.py
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

- [ ] **Phase 9**: Service Layer Foundation
  - [ ] Cycle 9.1: Event System Design
  - [ ] Cycle 9.2: Service Configuration Management

- [ ] **Phase 10**: HTTP API Service (Primary Integration)
  - [ ] Cycle 10.1: HTTP Service Core Implementation
  - [ ] Cycle 10.2: Detection Integration

- [ ] **Phase 11**: Service Manager and Integration
  - [ ] Cycle 11.1: Detection Service Manager
  - [ ] Cycle 11.2: Main Application Integration

- [ ] **Phase 12**: Speaker Verification Integration Testing
  - [ ] Cycle 12.1: Guard Clause Integration

- [ ] **Phase 13**: WebSocket Service (Future Enhancement)
  - [ ] Cycle 13.1: WebSocket Core Implementation

- [ ] **Phase 14**: Server-Sent Events (Future Enhancement)
  - [ ] Cycle 14.1: SSE Core Implementation

### Test Progression Target
- **Starting Point**: 264 tests passing
- **After Phase 9**: ~280 tests (Event system + config)
- **After Phase 10**: ~310 tests (HTTP service + integration)
- **After Phase 11**: ~340 tests (Service manager + main app)
- **After Phase 12**: ~360 tests (Integration testing)
- **Target**: 360+ tests with comprehensive service layer coverage

---

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