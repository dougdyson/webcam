# Examples Directory

This directory contains **simple, quick-start examples** for getting started with webcam-detection.

> **📚 For comprehensive documentation and advanced examples, see the `docs/` directory**

## Quick Start Examples

### `package_usage_examples.py`
Simple, focused examples for common use cases:
- **Basic Detection**: Quick detector setup
- **Speaker Verification Guard**: Simple guard clause pattern
- **HTTP Service Integration**: Basic service consumption
- **Production Patterns**: Minimal working examples

## 📖 Documentation Structure

- **`examples/`** (This directory): Quick-start examples and minimal code samples
- **`docs/`** (Comprehensive): Full documentation, advanced patterns, and detailed guides
  - `PACKAGE_USAGE.md`: Complete API documentation
  - `package_integration_examples.py`: Advanced integration patterns
  - `service_patterns.py`: Service architecture patterns
  - `configuration_samples.py`: Configuration examples
  - `testing_patterns.py`: Testing strategies
  - And more...

## Usage

### Running Examples
```bash
# Quick examples from this directory
python examples/package_usage_examples.py

# For comprehensive examples, see docs/
python docs/package_integration_examples.py
```

### Prerequisites
```bash
# Install with service features
pip install webcam-detection[service]

# Or local development
pip install -e .[service]
```

## 🎯 Production Recommendation

For production use, refer to the comprehensive `docs/` directory. For quick prototyping, use these examples:

**Quick Guard Clause**:
```python
import requests

def should_process_audio() -> bool:
    try:
        response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
        return response.json().get("human_present", False)
    except:
        return True  # Fail safe
```

**Start Service**:
```bash
python webcam_http_service.py
``` 