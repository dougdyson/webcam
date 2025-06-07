# Webcam Detection Examples

**8,000+ lines of practical patterns and integrations**

## 🚀 Quick Start Examples

### Essential Patterns
- **[simple_client_example.py](simple_client_example.py)** - Basic usage patterns
- **[webcam_client.py](webcam_client.py)** - Complete client implementation
- **[production_service_patterns.py](production_service_patterns.py)** - Production deployment

### Core Technology Examples
- **[mediapipe_samples.py](mediapipe_samples.py)** - MediaPipe detection patterns
- **[opencv_samples.py](opencv_samples.py)** - OpenCV integration
- **[threading_asyncio_samples.py](threading_asyncio_samples.py)** - Async processing

## 🎯 Integration Examples

### Service Integration
- **[service_patterns.py](service_patterns.py)** - HTTP/SSE service patterns
- **[client_examples.py](client_examples.py)** - Client integration patterns
- **[package_integration_examples.py](package_integration_examples.py)** - Package usage

### AI Integration
- **[ollama_multimodal_chat_example.py](ollama_multimodal_chat_example.py)** - Ollama integration
- **[voice_bot_integration.py](voice_bot_integration.py)** - Voice assistant integration
- **[run-gemma-with-ollama.txt](run-gemma-with-ollama.txt)** - Ollama setup guide

## 🖐️ Gesture Recognition Examples (NEW)

### MediaPipe Gesture Examples
- **[gesture_recognition_examples.py](gesture_recognition_examples.py)** - Comprehensive gesture detection examples
  - **Basic MediaPipe Gestures**: 8 built-in gestures (Thumb_Up, Victory, Open_Palm, etc.)
  - **Custom Gesture Recognition**: Using 21 hand landmarks for finger gun, rock horn, OK sign
  - **Integrated Detection**: Human presence + conditional gesture processing
  - **Voice Assistant Control**: Stop gestures for voice command systems

### Advanced Integration Patterns
- **[advanced_integration_patterns.py](advanced_integration_patterns.py)** - Real-world integration examples
  - **Smart Home Automation**: Home Assistant, Phillips Hue, Sonos integration
  - **Web Dashboard Integration**: Real-time SSE streaming, performance metrics
  - **Microservice Architecture**: Circuit breakers, health checks, service discovery

## ⚡ Performance Optimization Examples (NEW)

### Performance Tuning
- **[performance_optimization_examples.py](performance_optimization_examples.py)** - Production performance patterns
  - **Frame Rate Optimization**: Adaptive FPS based on CPU/memory usage and processing load
  - **Memory Management**: Buffer pools, garbage collection optimization, resource cleanup
  - **Concurrent Detection**: Multi-threaded processing with worker pools and rate limiting
  - **Smart Caching**: Frame similarity detection, adaptive TTL, memory-aware eviction

## 🛠️ Development Examples

### Configuration & Testing
- **[configuration_samples.py](configuration_samples.py)** - Configuration patterns
- **[testing_patterns.py](testing_patterns.py)** - Testing methodologies
- **[snapshot_usage_example.py](snapshot_usage_example.py)** - Snapshot processing

## 📋 Usage

```bash
# Activate environment
conda activate webcam

# Run any example
python docs/examples/simple_client_example.py

# Run gesture recognition examples
python docs/examples/gesture_recognition_examples.py

# Run integration patterns
python docs/examples/advanced_integration_patterns.py

# Run performance optimization examples
python docs/examples/performance_optimization_examples.py

# For production deployment
python webcam_service.py
```

## 🎯 Use Case Examples

### Speaker Verification
See [voice_bot_integration.py](voice_bot_integration.py) for complete guard clause patterns.

### Gesture Control Systems
See [gesture_recognition_examples.py](gesture_recognition_examples.py) for:
- MediaPipe's 8 built-in gestures: `Closed_Fist`, `Open_Palm`, `Pointing_Up`, `Thumb_Down`, `Thumb_Up`, `Victory`, `ILoveYou`
- Custom gesture recognition using 21 hand landmarks
- Voice assistant stop/pause gesture control

### Smart Home Integration  
See [advanced_integration_patterns.py](advanced_integration_patterns.py) for automation trigger examples:
- Kitchen presence detection for lighting and music
- Gesture-controlled cooking timers
- Home Assistant webhook integration

### Real-time Dashboards
See [client_examples.py](client_examples.py) and [advanced_integration_patterns.py](advanced_integration_patterns.py) for SSE streaming integration.

### Performance Optimization
See [performance_optimization_examples.py](performance_optimization_examples.py) for production optimization:
- Adaptive frame rate control (10-60 FPS based on system load)
- Memory-efficient processing with buffer pools
- Concurrent detection pipelines
- Smart caching with 95%+ similarity matching

## 🏗️ Architecture Examples

### Microservice Integration
See [advanced_integration_patterns.py](advanced_integration_patterns.py) for production patterns:
- Circuit breaker patterns for failure recovery
- Health check endpoints with automated monitoring
- Service discovery registration
- Load balancing metadata

## 🎭 MediaPipe Gesture Support

Based on MediaPipe's capabilities, the system supports:

### Built-in Gestures (8 total)
1. **Unknown** - Unrecognized gesture
2. **Closed_Fist** - Closed fist
3. **Open_Palm** - Open palm (great for stop commands)
4. **Pointing_Up** - Index finger pointing up
5. **Thumb_Down** - Thumbs down
6. **Thumb_Up** - Thumbs up (perfect for confirmations)
7. **Victory** - Peace/Victory sign
8. **ILoveYou** - ASL "I Love You" sign

### Custom Gestures (Unlimited)
Using MediaPipe's 21 hand landmarks, you can create:
- Finger gun gestures
- Rock horn (🤘) gestures  
- OK sign gestures
- Any custom gesture based on finger positions and hand shapes

See [gesture_recognition_examples.py](gesture_recognition_examples.py) for complete implementation examples. 