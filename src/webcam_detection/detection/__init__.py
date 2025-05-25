"""
Human detection module.

This module provides human presence detection capabilities using various
computer vision backends including MediaPipe with both single-mode and
multi-modal detection approaches.
"""

from .result import DetectionResult, DetectionError
from .base import HumanDetector, DetectorConfig, DetectorError as BaseDetectorError, DetectorFactory, create_detector
from .mediapipe_detector import MediaPipeDetector
from .multimodal_detector import MultiModalDetector

# Use the base DetectorError as the main one (more comprehensive)
DetectorError = BaseDetectorError

# Register detectors in factory
DetectorFactory.register('mediapipe', MediaPipeDetector)
DetectorFactory.register('multimodal', MultiModalDetector)

# Alias for backwards compatibility and convenience
DetectorFactory.register('pose', MediaPipeDetector)  # Single pose detection
DetectorFactory.register('pose_face', MultiModalDetector)  # Combined detection

__all__ = [
    'DetectionResult',
    'DetectionError',
    'HumanDetector',
    'DetectorConfig', 
    'DetectorFactory',
    'create_detector',
    'MediaPipeDetector',
    'MultiModalDetector',
] 