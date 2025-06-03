# Configuration Guide

## Overview

Webcam Detection provides extensive configuration options for different deployment scenarios. This guide covers all configuration files and environment variables.

## Configuration Files

### Detection Configuration (`config/detection_config.yaml`)

#### Multi-Modal Detection (Recommended)
```yaml
multimodal:
  model_complexity: 1
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5
  pose_weight: 0.6          # Weight for pose detection
  face_weight: 0.4          # Weight for face detection
  enable_pose: true
  enable_face: true

presence_filter:
  smoothing_window: 5
  min_confidence_threshold: 0.7
  debounce_frames: 3
```

#### MediaPipe Detection (Legacy)
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

### Camera Configuration (`config/camera_profiles.yaml`)
```yaml
default:
  device_id: 0
  width: 640
  height: 480
  fps: 30
  buffer_size: 5

high_quality:
  device_id: 0
  width: 1280
  height: 720
  fps: 30
  buffer_size: 10

low_latency:
  device_id: 0
  width: 320
  height: 240
  fps: 60
  buffer_size: 2
```

### Service Layer Configuration (`config/service_config.yaml`)
```yaml
service_layer:
  enabled: true
  
  http:
    host: "localhost"
    port: 8767
    enable_history: true
    history_limit: 1000
    
  sse:
    host: "localhost"
    port: 8766
    max_connections: 20
    heartbeat_interval: 30.0
    connection_timeout: 60.0
    
  event_publishing:
    publish_detection_updates: true
    publish_presence_changes: true
    publish_confidence_alerts: true
    confidence_alert_threshold: 0.3
```

### Gesture Recognition Configuration (`config/gesture_config.yaml`)
```yaml
gesture_detection:
  enabled: true
  run_only_when_human_present: true
  min_human_confidence_threshold: 0.6
  
  hand_detection:
    model_complexity: 1
    min_detection_confidence: 0.7
    min_tracking_confidence: 0.5
    max_num_hands: 2
  
  stop_gesture:
    shoulder_offset_threshold: 0.1  # Hand must be 10% above shoulder
    palm_facing_confidence: 0.7
    debounce_frames: 3
    gesture_timeout_ms: 5000
```

## Ollama Integration Configuration

### Use-Case Defaults

#### Development Configuration
```python
from webcam_detection.utils.config import ConfigManager

config_manager = ConfigManager()
dev_config = config_manager.get_ollama_defaults_for_use_case('development')
```

**Development settings:**
- Quick iteration: 20s timeouts
- 3-minute cache TTL
- Debug-friendly settings
- Minimal retry delays

#### Production Configuration
```python
prod_config = config_manager.get_ollama_defaults_for_use_case('production')
```

**Production settings:**
- Reliability-focused: 45s timeouts
- 10-minute cache TTL
- Enhanced retry policies
- Comprehensive error handling

#### Testing Configuration
```python
test_config = config_manager.get_ollama_defaults_for_use_case('testing')
```

**Testing settings:**
- Speed-optimized: 5s timeouts
- Disabled caching
- Minimal buffers
- Fast iteration

### Full Ollama Configuration (`config/ollama_config.yaml`)
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

## Environment Variables

### Ollama Environment Overrides
```bash
# Client configuration
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="gemma3:4b-it-q4_K_M"
export OLLAMA_TIMEOUT=30
export OLLAMA_MAX_RETRIES=2

# Description service
export OLLAMA_CACHE_TTL=300
export OLLAMA_MAX_CONCURRENT=3
export OLLAMA_ENABLE_CACHING=true

# Processing configuration
export OLLAMA_QUEUE_SIZE=100
export OLLAMA_RATE_LIMIT=0.5
export OLLAMA_BUFFER_SIZE=50
export OLLAMA_MIN_CONFIDENCE=0.7
```

### Service Configuration
```bash
# HTTP service
export WEBCAM_HTTP_HOST="0.0.0.0"
export WEBCAM_HTTP_PORT=8767

# SSE service
export WEBCAM_SSE_HOST="0.0.0.0"
export WEBCAM_SSE_PORT=8766

# Camera
export WEBCAM_CAMERA_DEVICE=0
export WEBCAM_CAMERA_WIDTH=640
export WEBCAM_CAMERA_HEIGHT=480
```

## Runtime Configuration Management

### Configuration Health Check
```python
config_manager = ConfigManager()
config = config_manager.load_ollama_config()
health_report = config_manager.check_ollama_config_health(config)

print(f"Health Score: {health_report['performance_score']}/100")
print(f"Overall Health: {health_report['overall_health']}")
for recommendation in health_report['recommendations']:
    print(f"💡 {recommendation}")
```

### Dynamic Configuration Updates
```python
# Partial configuration update
config_manager.apply_partial_ollama_config_update({
    'description_service': {
        'cache_ttl_seconds': 600,
        'max_concurrent_requests': 5
    }
})

# Configuration rollback
checkpoint_id = config_manager.create_ollama_config_checkpoint()
# ... make changes ...
config_manager.rollback_ollama_config_to_checkpoint(checkpoint_id)
```

### Model Compatibility Warnings
```python
config = config_manager.load_ollama_config()
warnings = config_manager.validate_ollama_config_with_warnings(config)

for warning in warnings:
    print(f"⚠️ {warning}")
# Example: "High memory usage expected with gemma3:27b model"
```

## Performance Tuning

### Detection Performance
- **model_complexity**: 0 (fastest) to 2 (most accurate)
- **min_detection_confidence**: Lower values detect more (but less accurate)
- **smoothing_window**: Larger values smooth detection but add latency
- **debounce_frames**: Prevent false positive state changes

### Service Performance
- **buffer_size**: Larger buffers smooth frame drops but add memory usage
- **max_connections**: Limit concurrent SSE connections
- **history_limit**: Limit detection history to prevent memory growth

### Ollama Performance
- **timeout_seconds**: Balance between responsiveness and allowing processing time
- **max_concurrent_requests**: Prevent Ollama overload
- **cache_ttl_seconds**: Balance between fresh descriptions and performance
- **rate_limit_per_second**: Prevent overwhelming Ollama service

## Deployment Scenarios

### Development Environment
```yaml
# Optimized for quick iteration
detection_config:
  min_confidence_threshold: 0.5  # More sensitive
  debounce_frames: 1             # Faster response

ollama_config:
  timeout_seconds: 20            # Faster timeouts
  cache_ttl_seconds: 180         # Shorter cache
```

### Production Environment
```yaml
# Optimized for reliability
detection_config:
  min_confidence_threshold: 0.7  # More accurate
  debounce_frames: 3             # Stable detection

ollama_config:
  timeout_seconds: 45            # Allow processing time
  cache_ttl_seconds: 600         # Longer cache
  max_retries: 3                 # More resilient
```

### High-Performance Environment
```yaml
# Optimized for speed
camera_config:
  width: 320
  height: 240
  fps: 60

detection_config:
  model_complexity: 0            # Fastest models
  smoothing_window: 3            # Minimal smoothing

ollama_config:
  enable_caching: false          # Skip caching overhead
  max_concurrent_requests: 1     # Reduce resource usage
```

For more detailed configuration options, see the source code documentation and example configurations in the `config/` directory. 