# Webcam Human Presence Detection

A Python application for real-time human presence detection using webcam input, built with OpenCV and MediaPipe. Designed for local processing with plans for future integration with speaker verification systems.

## Features

- **Real-time human detection** using MediaPipe Pose/Face detection
- **Local processing** - no cloud dependencies
- **Asynchronous frame processing** with queue management
- **Configurable detection parameters** via YAML configuration
- **Debouncing and smoothing** for stable detection results
- **Performance monitoring** and FPS tracking
- **Modular architecture** with provider pattern for different detection backends

## Quick Start

### Option 1: Using Conda (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd webcam

# Create and activate conda environment
conda env create -f environment.yml
conda activate webcam
```

### Option 2: Using pip

```bash
# Clone the repository
git clone <repository-url>
cd webcam

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Architecture

The system follows a modular pipeline architecture:

- **Camera Module** (`src/camera/`) - Camera access and frame capture
- **Detection Module** (`src/detection/`) - Human detection algorithms  
- **Processing Module** (`src/processing/`) - Asynchronous frame processing
- **Utils Module** (`src/utils/`) - Configuration and logging utilities
- **CLI Module** (`src/cli/`) - Command-line interface

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed system design.

## Development

This project follows Test-Driven Development (TDD). See [TDD_PLAN.md](TDD_PLAN.md) for development progress.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_config.py -v
```

### Development Environment

```bash
# Activate environment
conda activate webcam

# Run application (when implemented)
python -m src.cli.main --config config/default.yaml
```

## Configuration

Configuration files are stored in `config/` directory:

- `config/default.yaml` - Default configuration
- `config/high_quality.yaml` - High quality detection profile
- `config/low_latency.yaml` - Low latency profile

Example configuration:

```yaml
camera:
  device_id: 0
  width: 640
  height: 480
  fps: 30

detection:
  model_complexity: 1
  min_detection_confidence: 0.5
  smoothing_window: 5
```

## Performance Targets

- **Latency**: < 100ms per frame
- **Frame Rate**: 15-30 FPS
- **Memory**: < 200MB RAM usage
- **CPU**: Optimized for real-time processing

## Contributing

1. Follow TDD practices - write tests first
2. Maintain the existing architecture patterns
3. Update documentation for new features
4. Ensure all tests pass before submitting PRs

## License

[License information to be added] 