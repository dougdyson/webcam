"""
Shared test configuration and fixtures for webcam detection tests.

This conftest.py ensures that the src module can be imported correctly
for all test files regardless of their location in the test directory.
"""

import sys
from pathlib import Path

# Add the project root to Python path so src module can be imported
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Shared pytest configuration
import pytest
import numpy as np
from unittest.mock import Mock

@pytest.fixture
def mock_frame():
    """Provide a mock camera frame for testing."""
    return np.zeros((480, 640, 3), dtype=np.uint8)

@pytest.fixture
def mock_camera():
    """Provide a mock camera for testing."""
    camera = Mock()
    camera.get_frame.return_value = np.zeros((480, 640, 3), dtype=np.uint8)
    camera.is_connected.return_value = True
    return camera 