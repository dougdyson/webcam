# TDD Plan: Ollama Description Endpoint Feature

## 🎯 Feature Overview
Add an endpoint that provides detailed descriptions of webcam snapshots using local Ollama Gemma3 model, activated only when humans are detected.

**Target Endpoint**: `GET /description/latest` → `{"description": "Person standing near desk, typing on laptop", "confidence": 0.89, "timestamp": "..."}`

## 🧪 TDD Methodology
- ✅ **RED**: Write failing test first
- ✅ **GREEN**: Write minimal code to pass test  
- ✅ **REFACTOR**: Clean up and optimize
- ✅ **TRACK**: Update checkboxes after each cycle
- ✅ **ENVIRONMENT**: Always prepend `conda activate webcam && ` to all terminal commands
- ✅ **TEST ALL**: Run all tests at the end of every section to ensure no regressions - **FIX ANY FAILURES BEFORE PROCEEDING**
- ✅ **COMMIT**: Prompt user to make a code commit at the end of every completed section
- ✅ **FILE ORGANIZATION**: Keep test files 200-300 lines for maintainability - create separate files by functionality/phase when needed

---

## 📋 Phase 1: Core Ollama Integration

### 1.1 Ollama Client Service (Foundation)
- [x] **RED**: Write test for `OllamaClient.__init__()` with configuration
- [x] **GREEN**: Implement basic OllamaClient class structure
- [x] **REFACTOR**: Clean up initialization and error handling
- [x] **RED**: Write test for `OllamaClient.is_available()` health check
- [x] **GREEN**: Implement Ollama service availability check
- [x] **REFACTOR**: Add proper error handling and logging
- [x] **RED**: Write test for `OllamaClient.describe_image()` with mock response
- [x] **GREEN**: Implement basic image description call to Ollama
- [x] **REFACTOR**: Optimize request/response handling

### 1.2 Ollama Configuration Management
- [x] **RED**: Write test for `OllamaConfig` dataclass validation
- [x] **GREEN**: Implement OllamaConfig with model, timeout, retry settings
- [x] **REFACTOR**: Add validation and default values
- [x] **RED**: Write test for invalid configuration handling
- [x] **GREEN**: Implement proper configuration validation
- [x] **REFACTOR**: Clean up error messages and edge cases

### 1.3 Image Processing for Ollama
- [x] **RED**: Write test for frame-to-base64 conversion
- [x] **GREEN**: Implement image encoding for Ollama API
- [x] **REFACTOR**: Optimize image size and quality
- [x] **RED**: Write test for image preprocessing (resize, quality)
- [x] **GREEN**: Implement image optimization for better Ollama performance
- [x] **REFACTOR**: Add configurable image processing parameters

---

## 📋 Phase 2: Snapshot Management System

### 2.1 Snapshot Buffer
- [x] **RED**: Write test for `SnapshotBuffer.__init__()` with size limit
- [x] **GREEN**: Implement circular buffer for storing snapshots
- [x] **REFACTOR**: Optimize memory usage and thread safety
- [x] **RED**: Write test for `SnapshotBuffer.add_snapshot()` when human detected
- [x] **GREEN**: Implement snapshot storage with metadata
- [x] **REFACTOR**: Add timestamp and confidence tracking
- [x] **RED**: Write test for `SnapshotBuffer.get_latest()` retrieval
- [x] **GREEN**: Implement latest snapshot retrieval with validation
- [x] **REFACTOR**: Handle empty buffer and concurrent access

### 2.2 Snapshot Trigger Logic
- [x] **RED**: Write test for snapshot trigger when `human_present=True`
- [x] **GREEN**: Implement human detection → snapshot capture logic
- [x] **REFACTOR**: Integrate with existing detection pipeline
- [x] **RED**: Write test for NO snapshot when `human_present=False`
- [x] **GREEN**: Implement conditional snapshot logic
- [x] **REFACTOR**: Optimize performance by avoiding unnecessary processing
- [x] **RED**: Write test for confidence threshold filtering
- [x] **GREEN**: Implement minimum confidence requirement for snapshots
- [x] **REFACTOR**: Make confidence threshold configurable

---

## 📋 Phase 3: Description Processing Service

### 3.1 Description Service Core
- [x] **RED**: Write test for `DescriptionService.__init__()` with dependencies
- [x] **GREEN**: Implement DescriptionService class structure
- [x] **REFACTOR**: Follow existing service patterns from HTTP/SSE services
- [x] **RED**: Write test for `describe_snapshot()` async method
- [x] **GREEN**: Implement async snapshot description processing
- [x] **REFACTOR**: Add proper error handling and timeouts
- [x] **RED**: Write test for description caching mechanism
- [x] **GREEN**: Implement description cache with TTL
- [x] **REFACTOR**: Optimize cache memory usage and expiration

### 3.2 Async Processing Pipeline
- [ ] **RED**: Write test for async description processing queue
- [ ] **GREEN**: Implement background description processing
- [ ] **REFACTOR**: Integrate with existing async architecture
- [ ] **RED**: Write test for processing rate limiting (max 1 per 2 seconds)
- [ ] **GREEN**: Implement rate limiting to prevent Ollama overload
- [ ] **REFACTOR**: Make rate limiting configurable
- [ ] **RED**: Write test for concurrent request handling
- [ ] **GREEN**: Implement proper async concurrency control
- [ ] **REFACTOR**: Optimize resource usage and prevent blocking

### 3.3 Error Handling & Resilience
- [ ] **RED**: Write test for Ollama service unavailable scenario
- [ ] **GREEN**: Implement graceful fallback when Ollama is down
- [ ] **REFACTOR**: Add proper error logging and monitoring
- [ ] **RED**: Write test for Ollama timeout handling
- [ ] **GREEN**: Implement timeout recovery and retry logic
- [ ] **REFACTOR**: Add exponential backoff for retries
- [ ] **RED**: Write test for malformed Ollama response handling
- [ ] **GREEN**: Implement response validation and error recovery
- [ ] **REFACTOR**: Add comprehensive error categorization

---

## 📋 Phase 4: HTTP API Integration

### 4.1 New HTTP Endpoint
- [ ] **RED**: Write test for `GET /description/latest` endpoint registration
- [ ] **GREEN**: Add new endpoint to existing HTTPDetectionService
- [ ] **REFACTOR**: Follow existing endpoint patterns and CORS setup
- [ ] **RED**: Write test for successful description response format
- [ ] **GREEN**: Implement JSON response with description, confidence, timestamp
- [ ] **REFACTOR**: Standardize response format with existing endpoints
- [ ] **RED**: Write test for endpoint when no description available
- [ ] **GREEN**: Implement proper 404/empty response handling
- [ ] **REFACTOR**: Add consistent error response format

### 4.2 Response Caching & Performance
- [ ] **RED**: Write test for cached response serving
- [ ] **GREEN**: Implement response caching to avoid repeated Ollama calls
- [ ] **REFACTOR**: Optimize cache hit/miss logic
- [ ] **RED**: Write test for cache invalidation when new description ready
- [ ] **GREEN**: Implement cache update mechanism
- [ ] **REFACTOR**: Add cache statistics and monitoring
- [ ] **RED**: Write test for concurrent endpoint requests
- [ ] **GREEN**: Implement proper concurrent access to cached descriptions
- [ ] **REFACTOR**: Optimize thread safety and performance

---

## 📋 Phase 5: Event System Integration

### 5.1 New Event Types
- [ ] **RED**: Write test for `DESCRIPTION_GENERATED` event type
- [ ] **GREEN**: Add new event type to existing EventType enum
- [ ] **REFACTOR**: Follow existing event type patterns
- [ ] **RED**: Write test for `DESCRIPTION_FAILED` event type
- [ ] **GREEN**: Add error event type for failed descriptions
- [ ] **REFACTOR**: Ensure consistent event naming conventions
- [ ] **RED**: Write test for description event data structure
- [ ] **GREEN**: Implement standardized event data format
- [ ] **REFACTOR**: Validate event data consistency

### 5.2 Event Publishing Integration
- [ ] **RED**: Write test for description events published to EventPublisher
- [ ] **GREEN**: Integrate description service with existing event system
- [ ] **REFACTOR**: Follow existing event publishing patterns
- [ ] **RED**: Write test for event subscribers receiving description events
- [ ] **GREEN**: Implement event delivery to HTTP service for endpoint updates
- [ ] **REFACTOR**: Optimize event flow and reduce latency
- [ ] **RED**: Write test for event publishing error handling
- [ ] **GREEN**: Implement robust event publishing with error recovery
- [ ] **REFACTOR**: Add event publishing statistics and monitoring

---

## 📋 Phase 6: Configuration & Setup

### 6.1 Configuration Management
- [ ] **RED**: Write test for Ollama configuration in main config file
- [ ] **GREEN**: Add Ollama settings to existing configuration system
- [ ] **REFACTOR**: Follow existing configuration patterns and validation
- [ ] **RED**: Write test for configuration validation and defaults
- [ ] **GREEN**: Implement proper config validation and error handling
- [ ] **REFACTOR**: Add helpful configuration documentation
- [ ] **RED**: Write test for runtime configuration updates
- [ ] **GREEN**: Implement dynamic configuration reload if needed
- [ ] **REFACTOR**: Optimize configuration change handling

### 6.2 Service Integration
- [ ] **RED**: Write test for DescriptionService integration in main service
- [ ] **GREEN**: Add DescriptionService to EnhancedWebcamService
- [ ] **REFACTOR**: Follow existing service integration patterns
- [ ] **RED**: Write test for proper service startup/shutdown order
- [ ] **GREEN**: Implement proper lifecycle management
- [ ] **REFACTOR**: Add service health monitoring and dependencies
- [ ] **RED**: Write test for service component communication
- [ ] **GREEN**: Implement proper inter-service communication
- [ ] **REFACTOR**: Optimize service coupling and performance

---

## 📋 Phase 7: Integration Testing & Optimization

### 7.1 End-to-End Integration Tests
- [ ] **RED**: Write integration test for full human detection → description flow
- [ ] **GREEN**: Implement complete pipeline test with mocked Ollama
- [ ] **REFACTOR**: Optimize test setup and teardown
- [ ] **RED**: Write integration test for HTTP endpoint with real description
- [ ] **GREEN**: Implement API integration test with full stack
- [ ] **REFACTOR**: Add comprehensive test data and scenarios
- [ ] **RED**: Write integration test for performance under load
- [ ] **GREEN**: Implement load testing for concurrent requests
- [ ] **REFACTOR**: Optimize performance bottlenecks identified

### 7.2 Error Scenario Testing
- [ ] **RED**: Write test for system behavior when Ollama is unavailable
- [ ] **GREEN**: Implement graceful degradation test
- [ ] **REFACTOR**: Improve error handling based on test results
- [ ] **RED**: Write test for network timeout scenarios
- [ ] **GREEN**: Implement timeout and recovery test
- [ ] **REFACTOR**: Optimize timeout handling and user experience
- [ ] **RED**: Write test for high-load scenario (many humans detected)
- [ ] **GREEN**: Implement stress test for description service
- [ ] **REFACTOR**: Add rate limiting and resource management

---

## 📋 Phase 8: Documentation & Production Readiness

### 8.1 API Documentation
- [ ] **RED**: Write test to validate API documentation examples
- [ ] **GREEN**: Add `/description/latest` endpoint to README.md
- [ ] **REFACTOR**: Ensure documentation accuracy and completeness
- [ ] **RED**: Write test for configuration documentation
- [ ] **GREEN**: Document Ollama setup and configuration options
- [ ] **REFACTOR**: Add troubleshooting guide and examples

### 8.2 Production Configuration
- [ ] **RED**: Write test for production-ready default configuration
- [ ] **GREEN**: Set appropriate defaults for production use
- [ ] **REFACTOR**: Optimize for performance and reliability
- [ ] **RED**: Write test for logging and monitoring integration
- [ ] **GREEN**: Add proper logging for description service
- [ ] **REFACTOR**: Integrate with existing monitoring patterns
- [ ] **RED**: Write test for graceful service degradation
- [ ] **GREEN**: Implement fallback behavior when description unavailable
- [ ] **REFACTOR**: Ensure system stability under all conditions

---

## 🎯 Success Criteria

### ✅ **Functional Requirements Met**
- [ ] Endpoint `/description/latest` returns meaningful descriptions
- [ ] Descriptions only generated when humans detected (performance optimized)
- [ ] Integration with existing HTTP service on port 8767
- [ ] Async processing doesn't block human detection pipeline
- [ ] Proper error handling when Ollama unavailable

### ✅ **Quality Requirements Met**
- [ ] All tests passing (maintain 100% success rate)
- [ ] TDD methodology followed throughout (Red→Green→Refactor)
- [ ] Code follows existing patterns and architecture
- [ ] Performance impact < 5% on core detection
- [ ] Documentation complete and accurate

### ✅ **Integration Requirements Met**
- [ ] Event system integration working
- [ ] Configuration system extended properly
- [ ] Service lifecycle management correct
- [ ] No breaking changes to existing functionality
- [ ] Production-ready deployment configuration

---

## 📊 Progress Tracking

**Total Tasks**: 78 checkboxes
**Completed**: 48/78 (61.5%)

### Phase Progress
- [x] Phase 1: Core Ollama Integration (21/21) ✅ COMPLETE
- [x] Phase 2: Snapshot Management System (18/18) ✅ COMPLETE
- [x] Phase 3.1: Description Service Core (9/12) ✅ COMPLETE
- [ ] Phase 3.2: Async Processing Pipeline (0/12)
- [ ] Phase 3.3: Error Handling & Resilience (0/12)
- [ ] Phase 4: HTTP API Integration (0/9)
- [ ] Phase 5: Event System Integration (0/9)
- [ ] Phase 6: Configuration & Setup (0/9)
- [ ] Phase 7: Integration Testing & Optimization (0/9)
- [ ] Phase 8: Documentation & Production Readiness (0/6)

---

## 🚀 Next Steps

1. **Start with Phase 1.1**: Begin with basic OllamaClient structure
2. **Follow TDD strictly**: Red test → Green implementation → Refactor
3. **Update checkboxes**: Mark progress after each Red-Green-Refactor cycle
4. **Review plan**: Adjust if we discover new requirements during development

Ready to begin TDD! 🧪✨ 