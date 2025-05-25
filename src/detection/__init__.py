"""
Human detection module.

This module provides human presence detection capabilities using various
computer vision backends including MediaPipe.
"""

from .result import DetectionResult, DetectionError
from .base import HumanDetector, DetectorConfig, DetectorError as BaseDetectorError, DetectorFactory, create_detector
from .mediapipe_detector import MediaPipeDetector

# Use the base DetectorError as the main one (more comprehensive)
DetectorError = BaseDetectorError

__all__ = [
    'DetectionResult',
    'DetectionError',
    'HumanDetector',
    'DetectorConfig', 
    'DetectorFactory',
    'create_detector',
    'MediaPipeDetector',
] 