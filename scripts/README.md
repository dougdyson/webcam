# Scripts Directory

Utility and debugging scripts for the Webcam Detection project.

## 🔧 Utility Scripts

### `monitor_detection_status.py`
**Real-time monitoring tool for the detection service**

```bash
# Start the main service first
python webcam_enhanced_service.py

# Then run the monitor in another terminal
python scripts/monitor_detection_status.py
```

**Features:**
- Real-time human presence and confidence display
- Gesture detection status monitoring
- FPS and performance metrics
- Clean, updating single-line display
- No interference with main service processing

**Output Example:**
```
👤 HUMAN | Conf: 0.85 | Gesture: stop (0.92) | Frames: 1250 | FPS: 28.5
```

## 🛠️ Debug Tools

### `visual_gesture_debug.py`
**Visual debugging tool with live video feed**

```bash
python scripts/visual_gesture_debug.py
```

**Features:**
- Live webcam feed with overlays
- Hand landmarks and connections visualization
- Shoulder reference lines
- Palm orientation vectors with color coding
- Real-time gesture detection status
- Head exclusion zone visualization

**Visual Elements:**
- 🔵 **Blue line**: Shoulder reference level
- 🟢 **Green dots**: Hand landmarks
- 🟡 **Yellow circle**: Head position and exclusion zone
- 🟢 **Green arrow**: Palm facing camera
- 🔴 **Red arrow**: Palm facing away
- **Text overlay**: Detection confidence and gesture status

## 🚀 Usage Workflow

### Basic Monitoring
```bash
# Terminal 1: Start main service
python webcam_enhanced_service.py

# Terminal 2: Monitor status
python scripts/monitor_detection_status.py
```

### Visual Debugging
```bash
# For gesture detection debugging
python scripts/visual_gesture_debug.py

# Press 'q' to quit visual debug tool
```

### Development Workflow
1. **Start with visual debug** to verify camera and detection work
2. **Run main service** for production use
3. **Use monitor script** for real-time status without visual overhead

## ⚙️ Configuration

Both scripts use the default service endpoints:
- **HTTP API**: `http://localhost:8767`
- **SSE Events**: `http://localhost:8766`

To change endpoints, modify the scripts directly or use command-line arguments where available.

## 🔗 Related

- **[Main Service](../webcam_enhanced_service.py)** - Production service
- **[Documentation](../docs/README.md)** - Complete documentation index
- **[Examples](../docs/examples/)** - Code examples and patterns 