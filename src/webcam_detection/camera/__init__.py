"""
Camera module for webcam human detection application.

This module provides camera access, configuration, and frame capture functionality.
"""

from .config import CameraConfig, CameraConfigError
from .manager import CameraManager, CameraError
from .capture import FrameCapture, FrameCaptureError

__all__ = [
    'CameraConfig', 'CameraConfigError', 
    'CameraManager', 'CameraError',
    'FrameCapture', 'FrameCaptureError'
] 