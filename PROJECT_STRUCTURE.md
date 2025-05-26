# Project Structure Guide

Quick reference for navigating the webcam-detection project.

## 📁 Directory Overview

```
webcam/
├── 🏠 ROOT FILES (Clean & Organized)
│   ├── webcam_enhanced_service.py     # 🚀 MAIN SERVICE (production ready + gesture recognition)
│   ├── webcam_http_service.py         # HTTP-only service (alternative)
│   ├── README.md                      # Project overview and quick start
│   ├── requirements.txt               # Python dependencies
│   ├── setup.py                       # Package configuration
│   └── environment.yml                # Conda environment
├── 
├── 📦 SOURCE CODE
│   ├── src/                           # Main application code
│   │   ├── camera/                   # Camera management
│   │   ├── detection/                # Human detection (multimodal)
│   │   ├── processing/               # Frame processing and filtering
│   │   ├── gesture/                  # 🖐️ Gesture recognition (hand up detection)
│   │   ├── service/                  # HTTP API + SSE service layer
│   │   ├── cli/                      # Command-line interface
│   │   └── utils/                    # Utilities and configuration
│   │
├── 🧪 TESTING
│   ├── tests/                         # 414 comprehensive tests
│   │   ├── test_camera/              # Camera system tests
│   │   ├── test_detection/           # Detection algorithm tests
│   │   ├── test_processing/          # Processing pipeline tests
│   │   ├── test_gesture/             # 🖐️ Gesture recognition tests
│   │   ├── test_service/             # Service layer tests (HTTP + SSE)
│   │   └── test_integration/         # Integration tests (including gesture+SSE)
│   │
├── 📚 DOCUMENTATION
│   ├── docs/                          # 📖 COMPREHENSIVE DOCUMENTATION
│   │   ├── PACKAGE_USAGE.md          # Complete API reference
│   │   ├── package_integration_examples.py  # Advanced patterns
│   │   ├── service_patterns.py       # Service architecture
│   │   └── [more detailed docs]      # Configuration, testing, etc.
│   │
│   ├── examples/                      # 🚀 EXAMPLES & CLIENT CODE (Organized!)
│   │   ├── 🎯 Core Examples:
│   │   │   ├── simple_detection.py          # Basic human detection
│   │   │   └── gesture_service.py           # Simplified gesture service
│   │   ├── 🤝 Client Integration:
│   │   │   ├── simple_gesture_client.py     # Simple SSE client
│   │   │   ├── external_app_gesture_client.py  # Comprehensive integration
│   │   │   ├── gesture_client_example.py    # Detailed error handling
│   │   │   ├── voice_bot_quick_integration.py  # Voice bot integration
│   │   │   └── voice_library_examples.py    # Voice library patterns
│   │   ├── 🔧 Testing & Debugging:
│   │   │   ├── debug_gesture_real.py        # Real-time debugging
│   │   │   ├── gesture_diagnostic.py        # System diagnostics
│   │   │   ├── live_gesture_video_test.py   # Live video testing
│   │   │   └── live_status_viewer.py        # Status monitoring
│   │   └── 📚 Production Patterns:
│   │       └── package_usage_examples.py    # Comprehensive integration
│   │
├── ⚙️ CONFIGURATION
│   ├── config/                        # Configuration files
│   │   ├── camera_profiles.yaml      # Camera settings
│   │   ├── detection_config.yaml     # Detection parameters
│   │   └── app_config.yaml           # Application settings
│   │
├── 📋 PROJECT DOCS
│   ├── ARCHITECTURE.md                # System architecture (comprehensive)
│   ├── TDD_PLAN.md                   # Development methodology
│   └── PROJECT_STRUCTURE.md          # This file
│
└── 💾 DATA & OUTPUT
    ├── data/                          # Logs, temporary files, models
    │   └── webcam.log                # Moved here from root
    ├── dist/                          # Built packages
    └── .benchmarks/                   # Performance benchmarks
```

## 🎯 Quick Navigation

### I want to...

| **Goal** | **Go to** |
|----------|-----------|
| 🚀 **Run the service** | `conda activate webcam && python webcam_enhanced_service.py` |
| 🧪 **Run tests** | `python -m pytest tests/` |
| 📖 **Learn the API** | `docs/PACKAGE_USAGE.md` |
| 🏃 **Quick examples** | `examples/package_usage_examples.py` |
| 🏗️ **Understand architecture** | `ARCHITECTURE.md` |
| ⚙️ **Configure settings** | `config/` directory |
| 🐛 **Debug issues** | `data/` directory for logs |
| 📦 **Package/publish** | `setup.py` and `docs/PUBLISHING_GUIDE.md` |

## 🔥 Most Important Files

1. **`webcam_enhanced_service.py`** - Production service with gesture recognition (START HERE)
2. **`webcam_http_service.py`** - HTTP-only service (alternative)
3. **`README.md`** - Project overview
4. **`docs/PACKAGE_USAGE.md`** - Complete documentation
5. **`examples/package_usage_examples.py`** - Quick start
6. **`src/`** - Source code
7. **`tests/`** - Test suite (414 tests)

## 🚀 Getting Started

```bash
# 1. Install dependencies
conda env create -f environment.yml
conda activate webcam

# 2. Run tests to verify setup
python -m pytest tests/ -x

# 3. Start the enhanced service (HTTP + Gesture + SSE)
python webcam_enhanced_service.py

# 4. Test the service
curl http://localhost:8767/presence/simple

# 5. Test gesture events (in another terminal)
curl http://localhost:8766/events/gestures/test_client
```

## 🎯 Service Features

### Enhanced Service (webcam_enhanced_service.py) ✅ RECOMMENDED
- ✅ **HTTP API** (port 8767): Human presence detection
- ✅ **SSE Events** (port 8766): Real-time gesture streaming
- ✅ **Gesture Recognition**: Hand up detection with palm analysis
- ✅ **Clean Console**: Single updating status line (no scroll spam)
- ✅ **Production Ready**: 414 comprehensive tests passing

**Console Output:**
```
🎥 Frame 1250 | 👤 Human: YES (conf: 0.72) | 🖐️ Gesture: hand_up (conf: 0.95) | FPS: 28.5
```

### HTTP-Only Service (webcam_http_service.py) - Alternative
- ✅ **HTTP API** (port 8767): Human presence detection only
- ✅ **Lightweight**: No gesture recognition overhead
- ✅ **Simple**: Basic presence detection service

---

💡 **Pro tip**: Start with `webcam_enhanced_service.py` for full features, then refer to `docs/` for advanced integration patterns.