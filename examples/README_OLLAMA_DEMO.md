# Ollama Integration Demo 🎬

A simple standalone demo to test the Ollama integration before moving to HTTP API endpoints.

## What This Demo Does

1. **🎥 Captures webcam frames** using the existing camera system
2. **👤 Detects human presence** using our multi-modal detector  
3. **📸 Takes smart snapshots** when humans are detected
4. **🎨 Generates AI descriptions** using local Ollama models
5. **📊 Shows real-time stats** and caching performance

## Prerequisites 

### 1. Ollama Service Setup
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull vision model (in another terminal)
ollama pull llama3.2-vision
```

### 2. Environment Setup
```bash
# Activate conda environment
conda activate webcam

# Ensure webcam is connected and accessible
```

## Running the Demo

```bash
# From the webcam project root directory
python examples/ollama_demo.py
```

## Demo Controls

- **`q`** - Quit the demo
- **`s`** - Take manual snapshot 
- **`d`** - Force description generation
- **Camera window** - Shows live webcam feed with detection stats

## What You'll See

### Console Output
```
🎬 Ollama Integration Demo
==================================================
🎬 Initializing Ollama Demo...
✅ Demo initialized successfully!
🔍 Checking Ollama service...
✅ Ollama service is running and accessible

🎯 Starting Ollama Demo!
Press 'q' to quit, 's' to take snapshot manually, 'd' to force description

Frame  123 | 👤 HUMAN DETECTED (0.85) | Humans: 45 | Descriptions: 3 | Last: Person sitting at desk working on laptop...
```

### When Descriptions Generate
```
🎨 Generating description with Ollama...
✨ Description generated in 12.3s:
   📝 A person sitting at a desk with a laptop computer, wearing glasses and a dark shirt
   🎯 Confidence: 0.89
   💾 Cached: No
```

### Final Statistics
```
📊 Final Statistics:
   Frames processed: 456
   Human detections: 123
   Descriptions generated: 8
   Snapshots in buffer: 10
   Cache hits: 3
   Cache misses: 5
```

## Features Demonstrated

### ✅ **Core Integration**
- OllamaClient connection and health checking
- DescriptionService async processing  
- Smart snapshot triggering based on human detection
- Real-time status display

### ✅ **Performance Features**
- **Caching**: Identical frames get cached descriptions (5 min TTL)
- **Rate Limiting**: Descriptions only every 10 seconds max
- **Smart Triggering**: Only processes when humans detected
- **Frame Skipping**: Processes every 3rd frame for performance

### ✅ **Error Handling**
- Ollama service availability checking
- Graceful handling of description failures
- Fallback descriptions when Ollama unavailable
- Proper cleanup on exit

## Troubleshooting

### "Ollama service is not available"
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# If not running, start it
ollama serve
```

### "Model not found" or similar
```bash
# Ensure vision model is pulled
ollama pull llama3.2-vision

# Check available models
ollama list
```

### Camera issues
```bash
# Check camera permissions and availability
# Make sure no other applications are using the webcam
```

### Import errors
```bash
# Make sure you're in the webcam project root
cd /path/to/webcam

# Run from correct directory
python examples/ollama_demo.py
```

## Performance Notes

- **First description**: Takes 10-30 seconds (model loading)
- **Subsequent descriptions**: 5-15 seconds typically
- **Cached descriptions**: <1 second
- **Memory usage**: ~200-500MB additional for Ollama integration

## Next Steps

After running this demo successfully:

1. **✅ Validate functionality** - Ensure descriptions are reasonable
2. **✅ Test caching** - Identical snapshots should show "Cached: Yes" 
3. **✅ Test error handling** - Stop Ollama service and see fallback behavior
4. **➡️ Move to Phase 4** - HTTP API integration (`/description/latest` endpoint)

## Code Structure

The demo uses all our implemented components:
- `OllamaClient` - HTTP communication with Ollama
- `DescriptionService` - Async processing and caching
- `SnapshotBuffer` - Circular buffer for human-detected frames
- `ImageProcessor` - Frame preprocessing for Ollama
- Existing camera and detection systems

This provides a complete end-to-end test of the Ollama integration before adding HTTP endpoints! 