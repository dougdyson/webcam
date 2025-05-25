"""
Camera module for webcam human detection application.

This module provides camera access, configuration, and frame capture functionality.
"""

from .config import CameraConfig, CameraConfigError

__all__ = ['CameraConfig', 'CameraConfigError'] 