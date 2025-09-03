# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- **Create environment**: `conda env create -f environment.yml`
- **Activate environment**: `conda activate webcam`
- **Install dependencies**: `pip install -r requirements.txt`

### Running the Service
- **Main service**: `python webcam_service.py` - Starts HTTP API (8767), SSE service (8766), and Presence SSE (8764)
- **Ollama demo**: `bash examples/run_ollama_demo.sh` or `python examples/ollama_demo.py`
- **Status monitoring**: `python scripts/monitor_detection_status.py` (run in separate terminal)
- **Visual debugging**: `python scripts/visual_gesture_debug.py`

### Testing
- **Run all tests**: `pytest tests/`
- **Run specific test modules**: `pytest tests/test_detection/ -v`
- **With coverage**: `pytest --cov=src tests/`
- **Test categories**:
  - Detection algorithms: `pytest tests/test_detection/`
  - Service layer: `pytest tests/test_service/`
  - AI integration: `pytest tests/test_ollama/`
  - Integration tests: `pytest tests/test_integration/`

### Package Management
- **Install as package**: `pip install -e .` (development mode)
- **Install with service extras**: `pip install -e .[service]`
- **Build package**: `python setup.py sdist bdist_wheel`

## Architecture Overview

This is a local real-time human detection system with AI-powered scene descriptions and gesture recognition. The system runs entirely locally with no cloud dependencies.

### Core Pipeline
```
Camera → Multi-Modal Detection → Gesture Detection → Service Layer
  ↓           ↓                      ↓                ↓
Thread    Pose+Face Fusion       MediaPipe         HTTP/SSE APIs
         (Extended Range)        (When Human)      (8767/8766/8764)
```

### Key Components
- **Detection Engine** (`src/detection/`): Multi-modal human detection combining pose and face detection for 3x extended range
- **Gesture Recognition** (`src/gesture/`): MediaPipe-based hand gesture detection (only runs when humans present)
- **Service Layer** (`src/service/`): 
  - HTTP API (port 8767) for presence detection and guard clauses
  - SSE service (port 8766) for real-time gesture event streaming  
  - Presence SSE (port 8764) for presence change events
- **Ollama Integration** (`src/ollama/`): Optional local AI descriptions using Gemma3 models
- **Camera Module** (`src/camera/`): Hardware management and continuous video capture
- **Processing Pipeline** (`src/processing/`): Frame processing, filtering, and debouncing

### Service Endpoints
```
GET /presence/simple     → {"human_present": true}        # Guard clause endpoint
GET /presence           → Full presence status            # For detailed monitoring
GET /health             → Service health check            # System diagnostics
GET /statistics         → Performance metrics             # Usage statistics
GET /description/latest → AI scene descriptions (if enabled)
GET /events/gestures/{client_id} → SSE gesture stream     # Real-time events
```

## Configuration

### Service Configuration
- **HTTP Service**: `src/service/http_service.py` - REST API configuration
- **SSE Service**: `src/service/sse_service.py` - Real-time streaming configuration
- **Detection Config**: `config/detection_config.yaml` - Detection thresholds and parameters
- **Ollama Config**: `config/ollama_config.yaml` - AI integration settings

### Camera Profiles
- **Camera settings**: `config/camera_profiles.yaml` - Hardware-specific configurations

## Development Workflow

### Test-Driven Development
This project follows strict TDD methodology with 734 comprehensive tests organized to mirror the source structure:
- Tests are organized in `tests/` matching `src/` structure exactly
- Every component has corresponding test coverage
- Integration tests validate end-to-end functionality
- All tests must pass before committing changes

### Service Integration Patterns
The system is designed for production use with:
- **Guard Clause Pattern**: Use `/presence/simple` endpoint for quick presence checks
- **Event-Driven Architecture**: Subscribe to SSE streams for real-time updates
- **Graceful Degradation**: Core functionality continues if optional components fail
- **Error Isolation**: Component failures don't cascade

### Performance Characteristics
- **Frame Rate**: 15-30 FPS sustained processing
- **Latency**: <100ms from capture to detection result
- **Initialization**: <3.5s for complete system startup
- **Memory Usage**: <100MB total system footprint
- **HTTP Response**: <50ms for guard clause endpoints

### Primary Use Cases
- **Speaker Verification**: Guard clauses to only process audio when humans present
- **Smart Home Automation**: Trigger actions based on human presence
- **Voice Assistant Control**: Hand gesture detection for voice control
- **Security Monitoring**: Human presence detection for surveillance

### Common Integration Example
```python
import requests

def should_process_audio() -> bool:
    """Guard clause: only process audio when human present."""
    try:
        response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
        return response.json().get("human_present", False) if response.status_code == 200 else True
    except:
        return True  # Fail safe
```

## Important Notes

- **Local Processing**: All computation happens locally - no cloud dependencies
- **Privacy First**: Camera feeds never leave the device  
- **Ollama Optional**: AI descriptions require separate Ollama installation and model
- **Python Version**: Requires Python 3.10+ for MediaPipe compatibility
- **Hardware**: Works with USB webcams or integrated cameras
- **Multi-Modal**: Combines pose and face detection for superior range and accuracy