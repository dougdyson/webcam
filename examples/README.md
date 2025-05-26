# Examples Directory

Quick-start examples for getting up and running with webcam-detection package.

## 🚀 Quick Start (RECOMMENDED)

**For Production Use:**

1. **Start the enhanced service (HTTP + Gesture Recognition + SSE):**
   ```bash
   conda activate webcam && python webcam_enhanced_service.py
   ```
   
   **Clean Console Output:** Single updating status line (no scroll spam):
   ```
   🎥 Frame 1250 | 👤 Human: YES (conf: 0.72) | 🖐️ Gesture: hand_up (conf: 0.95) | FPS: 28.5
   ```

2. **Use HTTP guard clause in your code:**
   ```python
   import requests
   
   def should_process_audio():
       try:
           response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
           return response.json().get("human_present", False)
       except:
           return True  # Fail safe
   ```

3. **Listen for gesture events (optional):**
   ```python
   import asyncio
   import aiohttp
   
   async def listen_for_gestures():
       async with aiohttp.ClientSession() as session:
           async with session.get('http://localhost:8766/events/gestures/my_app') as resp:
               async for line in resp.content:
                   if line.startswith(b'data: '):
                       event_data = line[6:].decode().strip()
                       if event_data and event_data != '[HEARTBEAT]':
                           print(f"Gesture detected: {event_data}")
   ```

## 📁 What's Here

### 🎯 **Core Examples**
- **`simple_detection.py`** - Basic human detection example
- **`gesture_service.py`** - Simplified gesture service (alternative to enhanced service)

### 🤝 **Client Integration Examples**
- **`simple_gesture_client.py`** - Simple SSE gesture client
- **`external_app_gesture_client.py`** - Comprehensive external app integration
- **`gesture_client_example.py`** - Detailed gesture client with error handling
- **`voice_bot_quick_integration.py`** - Quick voice bot integration
- **`voice_library_examples.py`** - Voice library integration patterns

### 🔧 **Testing & Debugging**
- **`debug_gesture_real.py`** - Real-time gesture debugging tools
- **`gesture_diagnostic.py`** - Gesture system diagnostics
- **`live_gesture_video_test.py`** - Live video testing with gesture overlay
- **`live_status_viewer.py`** - Real-time status monitoring

### 📚 **Comprehensive Patterns**
- **`package_usage_examples.py`** - Production-ready integration patterns
  - ✅ HTTP service startup (recommended)
  - ✅ Speaker verification guard clauses  
  - ✅ Client wrapper classes
  - ✅ Direct API usage (alternative)
  - ✅ Docker deployment examples

## 🆚 Examples vs Docs

| **Purpose** | **Use This** |
|-------------|--------------|
| 🚀 **Get started quickly** | `examples/` - Simple, working code |
| 📖 **Learn comprehensive patterns** | `docs/` - Detailed architecture & advanced patterns |
| 🎯 **Speaker verification integration** | `examples/package_usage_examples.py` |
| 🏗️ **Custom service architecture** | `docs/service_patterns.py` |
| 📚 **Complete API reference** | `docs/PACKAGE_USAGE.md` |

## 🏃 Run Examples

### Basic Detection
```bash
python examples/simple_detection.py
```

### Gesture Service (Alternative)
```bash
python examples/gesture_service.py
```

### Client Examples
```bash
# Simple gesture client
python examples/simple_gesture_client.py

# External app integration
python examples/external_app_gesture_client.py

# Voice bot integration
python examples/voice_bot_quick_integration.py
```

### Testing & Debugging
```bash
# Real-time gesture debugging
python examples/debug_gesture_real.py

# Live video testing
python examples/live_gesture_video_test.py

# System diagnostics
python examples/gesture_diagnostic.py
```

### All Production Patterns
```bash
# Run all examples
python examples/package_usage_examples.py
```

## 💡 Next Steps

1. **Quick prototype**: Start with examples here
2. **Production deployment**: Use main `webcam_enhanced_service.py` in root
3. **Advanced patterns**: See `docs/service_patterns.py`
4. **API reference**: Check `docs/PACKAGE_USAGE.md` 