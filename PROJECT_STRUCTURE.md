# Project Structure Guide

Quick reference for navigating the webcam-detection project.

## 📁 Directory Overview

```
webcam/
├── 🏠 ROOT FILES
│   ├── webcam_http_service.py     # 🚀 MAIN SERVICE (production ready)
│   ├── README.md                  # Project overview and quick start
│   ├── requirements.txt           # Python dependencies
│   ├── setup.py                   # Package configuration
│   └── environment.yml            # Conda environment
├── 
├── 📦 SOURCE CODE
│   ├── src/                       # Main application code
│   │   ├── camera/               # Camera management
│   │   ├── detection/            # Human detection (multimodal)
│   │   ├── processing/           # Frame processing and filtering
│   │   ├── service/              # HTTP API service layer
│   │   ├── cli/                  # Command-line interface
│   │   └── utils/                # Utilities and configuration
│   │
├── 🧪 TESTING
│   ├── tests/                     # 320 comprehensive tests
│   │   ├── test_camera/          # Camera system tests
│   │   ├── test_detection/       # Detection algorithm tests
│   │   ├── test_processing/      # Processing pipeline tests
│   │   ├── test_service/         # Service layer tests
│   │   └── test_integration/     # Integration tests
│   │
├── 📚 DOCUMENTATION
│   ├── docs/                      # 📖 COMPREHENSIVE DOCUMENTATION
│   │   ├── PACKAGE_USAGE.md      # Complete API reference
│   │   ├── package_integration_examples.py  # Advanced patterns
│   │   ├── service_patterns.py   # Service architecture
│   │   └── [more detailed docs]  # Configuration, testing, etc.
│   │
│   ├── examples/                  # 🚀 QUICK START EXAMPLES
│   │   ├── package_usage_examples.py  # Simple usage patterns
│   │   └── README.md             # Quick start guide
│   │
├── ⚙️ CONFIGURATION
│   ├── config/                    # Configuration files
│   │   ├── camera_profiles.yaml  # Camera settings
│   │   ├── detection_config.yaml # Detection parameters
│   │   └── app_config.yaml       # Application settings
│   │
├── 📋 PROJECT DOCS
│   ├── ARCHITECTURE.md            # System architecture (comprehensive)
│   └── TDD_PLAN.md               # Development methodology
│
└── 💾 DATA & OUTPUT
    ├── data/                      # Logs, temporary files, models
    ├── dist/                      # Built packages
    └── .benchmarks/               # Performance benchmarks
```

## 🎯 Quick Navigation

### I want to...

| **Goal** | **Go to** |
|----------|-----------|
| 🚀 **Run the service** | `python webcam_http_service.py` |
| 🧪 **Run tests** | `python -m pytest tests/` |
| 📖 **Learn the API** | `docs/PACKAGE_USAGE.md` |
| 🏃 **Quick examples** | `examples/package_usage_examples.py` |
| 🏗️ **Understand architecture** | `ARCHITECTURE.md` |
| ⚙️ **Configure settings** | `config/` directory |
| 🐛 **Debug issues** | `data/` directory for logs |
| 📦 **Package/publish** | `setup.py` and `docs/PUBLISHING_GUIDE.md` |

## 🔥 Most Important Files

1. **`webcam_http_service.py`** - Production service (START HERE)
2. **`README.md`** - Project overview
3. **`docs/PACKAGE_USAGE.md`** - Complete documentation
4. **`examples/package_usage_examples.py`** - Quick start
5. **`src/`** - Source code
6. **`tests/`** - Test suite (320 tests)

## 🚀 Getting Started

```bash
# 1. Install dependencies
conda env create -f environment.yml
conda activate webcam

# 2. Run tests to verify setup
python -m pytest tests/ -x

# 3. Start the service
python webcam_http_service.py

# 4. Test the service
curl http://localhost:8767/presence/simple
```

---

💡 **Pro tip**: Start with `examples/` for quick prototyping, then refer to `docs/` for production implementations. 