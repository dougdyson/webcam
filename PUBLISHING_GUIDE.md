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

# Create detector
detector = create_detector('multimodal')
detector.initialize()

# Use in speaker verification guard clause
def should_process_audio():
    try:
        human_present, confidence, _ = detector.detect_person()
        return human_present and confidence > 0.6
    except:
        return True  # Fail safe

# Integration example
if should_process_audio():
    # Process audio
    pass
else:
    # Skip processing
    pass

detector.cleanup()
```

### Service Integration
```bash
pip install webcam-detection[service]
```

```python
# HTTP API guard clause
import requests

def check_presence():
    response = requests.get("http://localhost:8767/presence/simple")
    return response.json().get("human_present", False)
```

## Your Package Details

- **Package Name**: `webcam-detection`
- **Import Name**: `webcam_detection`
- **Version**: `2.0.0`
- **Description**: Advanced multi-modal human detection system with service integration
- **Main Features**:
  - Multi-modal detection (pose + face) for extended range
  - Simple guard clause integration for speaker verification
  - Service layer with HTTP/WebSocket/SSE APIs
  - 264+ comprehensive tests
  - Ready for production use

## Ready to Publish!

Your package is production-ready and well-tested. The build artifacts in `dist/` are ready for PyPI upload whenever you're ready to make it publicly available.

## Support and Documentation

After publishing, users can find:
- **Installation**: `pip install webcam-detection`
- **Documentation**: README.md and docs/ folder
- **Examples**: demo_speaker_verification.py
- **Issues**: GitHub issues page
- **Integration patterns**: docs/PACKAGE_USAGE.md 