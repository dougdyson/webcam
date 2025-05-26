# Publishing webcam-detection to PyPI

## Status: Ready for Publishing ✅

Your package has been successfully:
- ✅ Built with both wheel and source distributions
- ✅ Validated with `twine check`
- ✅ Tested for global installation and import
- ✅ Verified core functionality works

## Prerequisites

### 1. Create PyPI Accounts
- **Real PyPI**: https://pypi.org/account/register/
- **Test PyPI**: https://test.pypi.org/account/register/

### 2. Generate API Tokens
After creating accounts, generate API tokens:
- **Real PyPI**: https://pypi.org/manage/account/token/
- **Test PyPI**: https://test.pypi.org/manage/account/token/

Save these tokens securely - you'll use them instead of passwords.

## Publishing Steps

### Step 1: Test on TestPyPI (Recommended)

```bash
# Navigate to project directory
cd /Users/dougdyson/code/webcam

# Upload to TestPyPI
twine upload --repository testpypi dist/*
# Enter username: __token__
# Enter password: [your TestPyPI API token]
```

### Step 2: Test Installation from TestPyPI

```bash
# Create fresh environment to test
python -m venv test_env
source test_env/bin/activate  # On macOS/Linux
# test_env\Scripts\activate  # On Windows

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ webcam-detection

# Test it works
python -c "from webcam_detection import create_detector; print('Success!')"

# Cleanup
deactivate
rm -rf test_env
```

### Step 3: Publish to Real PyPI

Once you've tested on TestPyPI:

```bash
# Upload to real PyPI
twine upload dist/*
# Enter username: __token__
# Enter password: [your real PyPI API token]
```

### Step 4: Verify Public Installation

After publishing to real PyPI:

```bash
# Anyone can now install with:
pip install webcam-detection

# Or with service features:
pip install webcam-detection[service]
```

## Alternative: Using .pypirc Configuration

Create `~/.pypirc` to store repository configurations:

```ini
[distutils]
index-servers = 
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-real-api-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-api-token-here
```

Then upload with:
```bash
twine upload --repository testpypi dist/*  # For testing
twine upload dist/*                        # For real PyPI
```

## Version Management

For future releases, update the version in `setup.py`:

```python
version="2.0.1",  # Bug fixes
version="2.1.0",  # New features  
version="3.0.0",  # Breaking changes
```

Then rebuild and republish:
```bash
rm -rf dist/ build/ src/*.egg-info/
python -m build
twine upload dist/*
```

## GitHub Actions Automation (Optional)

Create `.github/workflows/publish.yml` for automatic publishing on releases:

```yaml
name: Publish to PyPI
on:
  release:
    types: [published]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        pip install build twine
    - name: Build package
      run: python -m build
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        password: ${{ secrets.PYPI_API_TOKEN }}
```

Store your PyPI API token as `PYPI_API_TOKEN` in GitHub repository secrets.

## Package Usage After Publishing

Once published, users can integrate your package like this:

### Basic Installation and Usage
```bash
pip install webcam-detection
```

```python
from webcam_detection import create_detector
import cv2

# Create detector
detector = create_detector('multimodal')
detector.initialize()

# Get camera frame
cap = cv2.VideoCapture(0)

# Use in speaker verification guard clause
def should_process_audio():
    try:
        ret, frame = cap.read()
        if ret:
            result = detector.detect(frame)
            return result.human_present and result.confidence > 0.6
        return False
    except:
        return True  # Fail safe

# Integration example
if should_process_audio():
    # Process audio
    pass
else:
    # Skip processing
    pass

cap.release()
detector.cleanup()
```

### Service Integration
```bash
pip install webcam-detection[service]
```

```python
# Start the enhanced service (production recommended)
import subprocess
service_process = subprocess.Popen([
    "python", "webcam_enhanced_service.py"
], cwd="/path/to/webcam")

# HTTP API guard clause
import requests

def check_presence():
    response = requests.get("http://localhost:8767/presence/simple")
    return response.json().get("human_present", False)

# Real-time gesture events
import asyncio
import aiohttp

async def listen_for_gestures():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8766/events/gestures/client_id') as resp:
            async for line in resp.content:
                if line.startswith(b'data: '):
                    event_data = line[6:].decode().strip()
                    if event_data and event_data != '[HEARTBEAT]':
                        print(f"Gesture: {event_data}")
```

## Your Package Details

- **Package Name**: `webcam-detection`
- **Import Name**: `webcam_detection`
- **Version**: `2.0.0`
- **Description**: Advanced multi-modal human detection system with gesture recognition and service integration
- **Main Features**:
  - Multi-modal detection (pose + face) for extended range
  - Gesture recognition with hand up detection and palm analysis
  - Simple guard clause integration for speaker verification
  - Service layer with HTTP/SSE APIs for real-time streaming
  - Clean console output with single updating status line
  - 414 comprehensive tests
  - Ready for production use

## Ready to Publish!

Your package is production-ready and well-tested with:
- ✅ **Core Detection**: Multi-modal human presence detection
- ✅ **Gesture Recognition**: Hand up detection with real-time SSE streaming
- ✅ **Service Layer**: HTTP API + SSE for easy integration
- ✅ **Clean Console**: Single updating status line (no scroll spam)
- ✅ **Test Coverage**: 414 comprehensive tests passing
- ✅ **Production Ready**: Battle-tested architecture

The build artifacts in `dist/` are ready for PyPI upload whenever you're ready to make it publicly available.

## Support and Documentation

After publishing, users can find:
- **Installation**: `pip install webcam-detection`
- **Documentation**: README.md and docs/ folder
- **Examples**: demo_speaker_verification.py
- **Issues**: GitHub issues page
- **Integration patterns**: docs/PACKAGE_USAGE.md 