# Ollama Integration Guide

## Overview

The Ollama integration extends the webcam detection system with AI-powered image description capabilities using local Ollama models. This feature provides detailed descriptions of webcam snapshots when humans are detected.

## Architecture

### Key Components

#### Ollama Client (`src/ollama/client.py`)
- **Local Integration**: Connects to local Ollama service (default: localhost:11434)
- **Model Support**: Validated with Gemma3 multimodal models (recommended: `gemma3:4b-it-q4_K_M`)
- **Health Checking**: Service availability validation
- **Error Handling**: Connection timeouts and service unavailability detection

#### Description Service (`src/ollama/description_service.py`)
- **Async Processing**: Non-blocking description generation
- **Smart Caching**: MD5-based frame caching with TTL (default: 5 minutes)
- **Concurrency Control**: Configurable semaphore limits (default: 3 concurrent)
- **Error Resilience**: Comprehensive error handling with fallback descriptions

#### Async Processing Pipeline (`src/ollama/async_processor.py`)
- **Background Processing**: Dedicated async processing loop
- **Priority Queue**: Request prioritization with efficient ordering
- **Rate Limiting**: Prevents Ollama overload (configurable req/sec)
- **Future-based Results**: Async result delivery with proper cleanup

#### Snapshot Management (`src/ollama/snapshot_buffer.py`)
- **Circular Buffer**: Memory-efficient frame storage (configurable size)
- **Human-triggered**: Only stores frames when humans detected
- **Thread-safe**: Concurrent access from detection and processing threads
- **Metadata Tracking**: Confidence, timestamp, and detection source information

## Processing Pipeline

```
Human Detection → Snapshot Trigger → Buffer Storage → Description Queue → Ollama Processing → Result Caching
       ↓               ↓                  ↓                  ↓                  ↓               ↓
   Confidence       Debounced         Circular           Priority          Rate Limited    TTL Cache
   Threshold        Trigger           Buffer             Queue             Processing      (5 min)
   (default         (3 frames)        (50 frames)        (async)          (0.5 req/sec)   (MD5 keys)
   0.7)
```

## Configuration

### Full Configuration Example
```yaml
client:
  base_url: "http://localhost:11434"
  model: "gemma3:4b-it-q4_K_M"
  timeout_seconds: 30.0
  max_retries: 2

description_service:
  cache_ttl_seconds: 300
  max_concurrent_requests: 3
  enable_caching: true
  enable_fallback_descriptions: true
  initial_backoff_delay: 0.5
  max_backoff_delay: 16.0
  retry_backoff_factor: 2.0
  enable_stress_recovery: true
  stress_failure_threshold: 0.5
  stress_backoff_multiplier: 2.0

async_processor:
  max_queue_size: 100
  rate_limit_per_second: 0.5
  enable_retries: false

snapshot_buffer:
  max_size: 50
  min_confidence_threshold: 0.7
  debounce_frames: 3
```

### Environment Variable Overrides
- **OLLAMA_BASE_URL**: Override Ollama service URL
- **OLLAMA_MODEL**: Override model selection
- **OLLAMA_TIMEOUT**: Override timeout configuration
- **OLLAMA_MAX_RETRIES**: Override retry policy
- **OLLAMA_CACHE_TTL**: Override cache duration
- **OLLAMA_MAX_CONCURRENT**: Override concurrency limits
- **OLLAMA_ENABLE_CACHING**: Override caching behavior
- **OLLAMA_QUEUE_SIZE**: Override processing queue size
- **OLLAMA_RATE_LIMIT**: Override rate limiting
- **OLLAMA_BUFFER_SIZE**: Override snapshot buffer size
- **OLLAMA_MIN_CONFIDENCE**: Override confidence thresholds

## Model Recommendations

### Validated Models
- **Recommended**: `gemma3:4b-it-q4_K_M` - Instruction-tuned 4B model, excellent speed/quality balance
- **Alternative**: `gemma3:12b-it-q4_K_M` - Larger model for higher quality (slower processing)
- **Lightweight**: `gemma3:1b` - Fast processing for basic descriptions
- **All Gemma3 models confirmed multimodal** - Support vision tasks out of the box

### Performance Characteristics
- **Processing Performance**: 10-30s for new descriptions (validated with Gemma3:4b-it-q4_K_M)
- **Cache Performance**: <1s for cache hits (MD5-based key lookup, validated)
- **Memory Management**: Fixed circular buffer prevents memory growth
- **Resource Isolation**: Ollama failures don't impact core detection functionality

## Error Handling

### Error Categories
- **SERVICE_UNAVAILABLE**: Connection refused, timeout errors
- **TIMEOUT**: Request exceeds configured timeout (default: 30s)
- **MALFORMED_RESPONSE**: Content length, JSON structure, expected fields

### Fallback Descriptions
- Service unavailable: "Description service temporarily unavailable"
- Timeout: "Description generation timeout, taking longer than expected"
- Processing error: "Unable to generate description due to processing error"

### Recovery Strategies
- **Exponential Backoff**: 0.5s → 1.0s → 2.0s → 4.0s timing pattern
- **Stress Recovery**: Adaptive failure rate monitoring with 70%+ recovery under stress
- **Thread-Safe Concurrency**: Per-event-loop semaphore caching for multi-threaded scenarios
- **Concurrent Timeout Isolation**: Independent timeout handling for multiple concurrent requests

## HTTP API Integration

### New Endpoint
```
GET /description/latest
Response: {
  "description": "Person standing near desk, typing on laptop",
  "confidence": 0.89,
  "timestamp": "2024-01-15T10:30:00Z",
  "cached": false,
  "processing_time_ms": 15300
}
```

### Enhanced Statistics
```
GET /statistics
Response: {
  "presence_detection": {...},
  "description_service": {
    "total_descriptions": 45,
    "cache_hits": 23,
    "cache_misses": 22,
    "processing_errors": 2,
    "average_processing_time": 15.3
  }
}
```

## Setup Instructions

1. **Install Ollama**: Download from https://ollama.ai
2. **Start Ollama Service**: `ollama serve`
3. **Pull Model**: `ollama pull gemma3:4b-it-q4_K_M`
4. **Configure**: Update `config/ollama_config.yaml` if needed
5. **Test**: Start enhanced service and check `/description/latest` endpoint

For troubleshooting and advanced configuration, see the main documentation. 