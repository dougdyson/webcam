#!/usr/bin/env python3
"""
Package Usage Examples for webcam-detection
===========================================

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
    """HTTP service integration example (RECOMMENDED)."""
    print("\n=== HTTP Service Integration Example ===")
    
    import requests
    
    class PresenceChecker:
        def __init__(self, service_url="http://localhost:8767"):
            self.service_url = service_url
        
        def is_human_present(self):
            """Check presence via HTTP API (PRODUCTION PATTERN)."""
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
                response = requests.get(f"{self.service_url}/presence", timeout=1.0)
                if response.status_code == 200:
                    return response.json()
            except requests.RequestException:
                pass
            return None
    
    # Usage (would work if service is running)
    checker = PresenceChecker()
    print(f"Human present: {checker.is_human_present()}")
    print(f"Detailed info: {checker.get_detailed_presence()}")

def example_speaker_verification_production():
    """Production speaker verification integration."""
    print("\n=== Production Speaker Verification Example ===")
    
    import requests
    import time
    
    def should_process_audio() -> bool:
        """Production guard clause for speaker verification."""
        try:
            response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
            if response.status_code == 200:
                return response.json().get("human_present", False)
        except requests.RequestException:
            # Fail safe: process audio if service unavailable
            return True
        return False
    
    def speaker_verification_pipeline(audio_stream):
        """Example speaker verification pipeline with human presence guard."""
        if not should_process_audio():
            print("⏭️  No human detected - skipping audio processing")
            return {"status": "skipped", "reason": "no_human_present"}
        
        print("✅ Human detected - processing audio")
        
        # Your actual speaker verification code would go here
        # For example:
        # 1. Transcribe audio
        # 2. Extract speaker features
        # 3. Compare against known voices
        # 4. Return speaker ID or confidence score
        
        # Simulated processing
        time.sleep(0.1)  # Simulate processing time
        
        return {
            "status": "processed",
            "speaker_id": "user_123",
            "confidence": 0.92,
            "transcript": "Hello, this is my voice",
            "human_present": True
        }
    
    # Example usage
    print("Testing production pipeline...")
    for i in range(3):
        result = speaker_verification_pipeline(f"audio_stream_{i}")
        print(f"Audio {i+1}: {result}")
        time.sleep(1)

def example_package_in_requirements_txt():
    """Show how to include in requirements.txt."""
    print("\n=== Requirements.txt Integration ===")
    
    requirements_example = """
# requirements.txt for a project using webcam-detection

# Core detection only
webcam-detection>=3.0.0

# With service features (recommended for production)
# webcam-detection[service]>=3.0.0

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
    libopencv-dev \\
    python3-opencv \\
    libglib2.0-0 \\
    libsm6 \\
    libxext6 \\
    libxrender-dev \\
    libgomp1 \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application
COPY . .

# Expose service port
EXPOSE 8767

# Start the webcam service
CMD ["python", "webcam_http_service.py"]
"""
    
    print("Example Dockerfile:")
    print(dockerfile_example)

def example_service_startup():
    """Show how to start the service."""
    print("\n=== Service Startup Example ===")
    
    startup_script = """
#!/bin/bash
# start_webcam_service.sh

echo "🚀 Starting Webcam Detection Service..."

# Activate virtual environment (if using one)
# source venv/bin/activate

# Start the service
python webcam_http_service.py &

# Wait for service to start
sleep 3

# Test if service is running
curl -s http://localhost:8767/health || {
    echo "❌ Service failed to start"
    exit 1
}

echo "✅ Service started successfully!"
echo "📡 Available at: http://localhost:8767"
echo "🎯 Guard clause endpoint: http://localhost:8767/presence/simple"
"""
    
    print("Example startup script:")
    print(startup_script)

def main():
    """Run all examples."""
    print("🎯 Webcam Detection Package - Usage Examples")
    print("=" * 50)
    
    try:
        # Run HTTP service example (most common)
        example_http_service_integration()
        
        # Run speaker verification production example
        example_speaker_verification_production()
        
        # Show other integration options
        example_package_in_requirements_txt()
        example_docker_integration()
        example_service_startup()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed!")
        print("💡 Recommendation: Use HTTP service integration for production")
        
    except ImportError as e:
        print(f"❌ Package not installed: {e}")
        print("💡 Install with: pip install webcam-detection[service]")
    except Exception as e:
        print(f"❌ Example failed: {e}")

if __name__ == "__main__":
    main() 