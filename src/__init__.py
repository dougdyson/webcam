"""
Webcam Detection Package
========================

Advanced multi-modal human detection system with service integration.

Main exports:
- create_detector: Factory function for creating detectors
- HumanDetector: Abstract base class for detectors  
- DetectionResult: Detection result data structure
- Service components: HTTPService, DetectionServiceManager, etc.
"""

from .detection import create_detector, HumanDetector, DetectionResult

# Version info
__version__ = "2.0.0"
__author__ = "Your Name"

# Main exports
__all__ = [
    'create_detector',
    'HumanDetector', 
    'DetectionResult',
    '__version__'
] 