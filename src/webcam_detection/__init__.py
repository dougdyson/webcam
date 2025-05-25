"""
Webcam Detection Package
========================

Advanced multi-modal human detection system with service integration.

This package provides human presence detection using computer vision with
MediaPipe, supporting both single-mode (pose) and multi-modal (pose + face)
detection for extended range and improved accuracy.

Main exports:
- create_detector: Factory function for creating detectors
- HumanDetector: Abstract base class for detectors  
- DetectionResult: Detection result data structure
- Service components: HTTPService, DetectionServiceManager, etc.

Examples:
    Basic detection:
        from webcam_detection import create_detector
        
        detector = create_detector('multimodal')
        detector.initialize()
        human_present, confidence, detection_type = detector.detect_person()
        detector.cleanup()

    Guard clause for speaker verification:
        import requests
        
        def should_process_audio():
            try:
                response = requests.get("http://localhost:8767/presence/simple")
                return response.json().get("human_present", False)
            except:
                return True  # Fail safe
"""

from .detection import create_detector, HumanDetector, DetectionResult

# Version info
__version__ = "2.0.0"
__author__ = "Your Name"

# Main exports for external use
__all__ = [
    'create_detector',
    'HumanDetector', 
    'DetectionResult',
    '__version__'
] 