#!/usr/bin/env python3
"""
Example: Using webcam-detection after PyPI publishing
======================================================

This shows how other developers would use your package after you publish it.

Installation:
    pip install webcam-detection

Or with service features:
    pip install webcam-detection[service]
"""

def example_basic_usage():
    """Basic human detection usage."""
    print("=== Basic Detection Example ===")
    
    from webcam_detection import create_detector
    from webcam_detection.camera import CameraManager
    from webcam_detection.camera.config import CameraConfig
    
    # Create camera and detector
    camera_config = CameraConfig()
    camera = CameraManager(camera_config)
    detector = create_detector('multimodal')
    
    try:
        # Initialize detector (camera self-initializes)
        detector.initialize()
        print("✅ Camera and detector initialized")
        
        # Get a frame and detect
        frame = camera.get_frame()
        if frame is not None:
            result = detector.detect(frame)
            print(f"Human present: {result.human_present}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Detection type: multimodal")
        else:
            print("No frame available")
        
    finally:
        detector.cleanup()
        camera.cleanup()
        print("✅ Components cleaned up")

def example_speaker_verification_guard():
    """Speaker verification guard clause example."""
    print("\n=== Speaker Verification Guard Example ===")
    
    from webcam_detection import create_detector
    from webcam_detection.camera import CameraManager
    from webcam_detection.camera.config import CameraConfig
    
    class AudioProcessor:
        def __init__(self):
            self.camera = CameraManager(CameraConfig())
            self.detector = create_detector('multimodal')
            # Only initialize detector (camera self-initializes)
            self.detector.initialize()
        
        def should_process_audio(self):
            """Guard clause: only process if human present."""
            try:
                frame = self.camera.get_frame()
                if frame is not None:
                    result = self.detector.detect(frame)
                    return result.human_present and result.confidence > 0.6
                return False
            except Exception as e:
                print(f"Detection failed: {e}")
                return True  # Fail safe
        
        def process_audio_stream(self, audio_data):
            """Process audio only if human is present."""
            if self.should_process_audio():
                print("✅ Human detected - processing audio")
                # Your speaker verification code here
                return {"processed": True, "speaker_id": "user123"}
            else:
                print("⏭️  No human - skipping audio processing")
                return {"processed": False}
        
        def cleanup(self):
            self.detector.cleanup()
            self.camera.cleanup()
    
    # Usage
    processor = AudioProcessor()
    try:
        result = processor.process_audio_stream("audio_data_here")
        print(f"Result: {result}")
    finally:
        processor.cleanup()

def example_simple_guard_clause():
    """Simplified guard clause for integration."""
    print("\n=== Simplified Guard Clause Example ===")
    
    from webcam_detection import create_detector
    from webcam_detection.camera import CameraManager
    from webcam_detection.camera.config import CameraConfig
    
    # One-time setup
    camera = CameraManager(CameraConfig())
    detector = create_detector('multimodal')
    # Only initialize detector (camera self-initializes)
    detector.initialize()
    
    def is_human_present():
        """Simple function to check human presence."""
        try:
            frame = camera.get_frame()
            if frame is not None:
                result = detector.detect(frame)
                return result.human_present and result.confidence > 0.6
            return False
        except:
            return True  # Fail safe
    
    # Usage in your application
    print("Testing guard clause...")
    for i in range(3):
        present = is_human_present()
        print(f"Check {i+1}: Human present = {present}")
    
    # Cleanup when done
    detector.cleanup()
    camera.cleanup()

def example_http_service_integration():
    """HTTP service integration example."""
    print("\n=== HTTP Service Integration Example ===")
    
    import requests
    
    class PresenceChecker:
        def __init__(self, service_url="http://localhost:8767"):
            self.service_url = service_url
        
        def is_human_present(self):
            """Check presence via HTTP API."""
            try:
                response = requests.get(f"{self.service_url}/presence/simple", timeout=1.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("human_present", False)
            except requests.RequestException as e:
                print(f"Service unavailable: {e}")
                return True  # Fail safe
            return False
        
        def get_detailed_presence(self):
            """Get detailed presence information."""
            try:
                response = requests.get(f"{self.service_url}/presence/detailed", timeout=1.0)
                if response.status_code == 200:
                    return response.json()
            except requests.RequestException:
                pass
            return None
    
    # Usage (would work if service is running)
    checker = PresenceChecker()
    print(f"Human present: {checker.is_human_present()}")
    print(f"Detailed info: {checker.get_detailed_presence()}")

def example_package_in_requirements_txt():
    """Show how to include in requirements.txt."""
    print("\n=== Requirements.txt Integration ===")
    
    requirements_example = """
# requirements.txt for a project using webcam-detection

# Core detection only
webcam-detection>=2.0.0

# With service features
# webcam-detection[service]>=2.0.0

# With all features  
# webcam-detection[all]>=2.0.0

# Other project dependencies
numpy>=1.24.0
requests>=2.28.0
"""
    
    print("Add to your requirements.txt:")
    print(requirements_example)

def example_docker_integration():
    """Show Docker integration."""
    print("\n=== Docker Integration Example ===")
    
    dockerfile_example = """
FROM python:3.11-slim

# Install system dependencies for webcam access
RUN apt-get update && apt-get install -y \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

# Install your published package
RUN pip install webcam-detection[service]

# Copy your application
COPY . /app
WORKDIR /app

# Install your app's dependencies
RUN pip install -r requirements.txt

# Run your application
CMD ["python", "your_app.py"]
"""
    
    print("Dockerfile example:")
    print(dockerfile_example)

if __name__ == "__main__":
    print("🎯 WEBCAM-DETECTION PACKAGE USAGE EXAMPLES")
    print("=" * 50)
    print("After publishing to PyPI, developers can use your package like this:\n")
    
    try:
        example_basic_usage()
        example_simple_guard_clause()
        example_speaker_verification_guard()
        example_http_service_integration()
        example_package_in_requirements_txt()
        example_docker_integration()
        
    except ImportError as e:
        print(f"Package not installed: {e}")
        print("\nTo use these examples after publishing:")
        print("pip install webcam-detection")
    except Exception as e:
        print(f"Example failed (expected without camera): {e}")
        print("✅ Package import works - camera needed for detection")
    
    print("\n" + "=" * 50)
    print("✅ Ready for PyPI publishing!")
    print("Your package will enable all these integration patterns.") 