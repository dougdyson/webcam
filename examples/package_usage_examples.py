#!/usr/bin/env python3
"""
Package Usage Examples for webcam-detection
===========================================

This shows how other developers would use your package after you publish it.

Installation:
    pip install webcam-detection

Or with service features:
    pip install webcam-detection[service]

RECOMMENDED: Use the HTTP service for production integrations.
"""

def example_production_service_startup():
    """RECOMMENDED: Start the production HTTP service."""
    print("=== Production Service Startup (RECOMMENDED) ===")
    
    import subprocess
    import time
    import requests
    
    # Option 1: Start service directly
    print("Option 1: Direct service startup")
    print("Command: python webcam_http_service.py")
    print("Service will be available at: http://localhost:8767")
    
    # Option 2: Programmatic startup
    print("\nOption 2: Programmatic startup")
    try:
        # Start service in background
        process = subprocess.Popen(
            ["python", "webcam_http_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for service to be ready
        for i in range(10):
            try:
                response = requests.get("http://localhost:8767/health", timeout=1.0)
                if response.status_code == 200:
                    print("✅ Service is ready!")
                    break
            except:
                pass
            time.sleep(0.5)
        else:
            print("❌ Service failed to start")
            return
        
        # Test the service
        presence_response = requests.get("http://localhost:8767/presence/simple")
        print(f"Presence check: {presence_response.json()}")
        
        # Clean up
        process.terminate()
        
    except Exception as e:
        print(f"Error: {e}")

def example_speaker_verification_production():
    """RECOMMENDED: Production speaker verification integration."""
    print("\n=== Production Speaker Verification (RECOMMENDED) ===")
    
    import requests
    
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
    
    def speaker_verification_pipeline(audio_data):
        """Complete speaker verification pipeline with presence guard."""
        if not should_process_audio():
            print("⏭️  No human detected - skipping expensive audio processing")
            return {"status": "skipped", "reason": "no_human_present"}
        
        print("✅ Human detected - processing audio")
        
        # Your actual speaker verification code would go here:
        # 1. Transcribe audio
        # 2. Extract speaker features  
        # 3. Compare against known voices
        # 4. Return speaker ID and confidence
        
        # Simulated result
        return {
            "status": "processed",
            "speaker_id": "user123",
            "confidence": 0.92,
            "text": "Hello, this is a test.",
            "processing_time_ms": 150
        }
    
    # Example usage
    sample_audio = b"simulated_audio_data"
    result = speaker_verification_pipeline(sample_audio)
    print(f"Result: {result}")

def example_http_service_client():
    """HTTP service client wrapper example."""
    print("\n=== HTTP Service Client Wrapper ===")
    
    import requests
    import time
    from typing import Dict, Any, Optional
    
    class WebcamDetectionClient:
        """Client wrapper for webcam detection service."""
        
        def __init__(self, base_url: str = "http://localhost:8767"):
            self.base_url = base_url
        
        def is_human_present(self) -> bool:
            """Simple presence check."""
            try:
                response = requests.get(f"{self.base_url}/presence/simple", timeout=1.0)
                return response.json().get("human_present", False)
            except:
                return False
        
        def get_presence_details(self) -> Optional[Dict[str, Any]]:
            """Get detailed presence information."""
            try:
                response = requests.get(f"{self.base_url}/presence", timeout=2.0)
                return response.json() if response.status_code == 200 else None
            except:
                return None
        
        def check_service_health(self) -> bool:
            """Check if service is healthy."""
            try:
                response = requests.get(f"{self.base_url}/health", timeout=1.0)
                return response.status_code == 200
            except:
                return False
    
    # Usage
    client = WebcamDetectionClient()
    
    if client.check_service_health():
        print("✅ Service is healthy")
        print(f"Human present: {client.is_human_present()}")
        
        details = client.get_presence_details()
        if details:
            print(f"Confidence: {details.get('confidence', 0):.2f}")
            print(f"Detection count: {details.get('detection_count', 0)}")
    else:
        print("❌ Service is not available")

def example_basic_usage():
    """Basic human detection usage (Direct API)."""
    print("\n=== Basic Detection Example (Direct API) ===")
    
    from webcam_detection import create_detector
    import cv2
    
    # Create detector
    detector = create_detector('multimodal')
    
    try:
        # Initialize detector
        detector.initialize()
        print("✅ Detector initialized")
        
        # Get camera frame
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        
        if ret:
            # Detect human in frame
            result = detector.detect(frame)
            print(f"Human present: {result.human_present}")
            print(f"Confidence: {result.confidence:.2f}")
            
            # Access detailed results
            if result.landmarks:
                pose_landmarks = result.landmarks.get('pose', [])
                face_landmarks = result.landmarks.get('face', [])
                print(f"Pose landmarks: {len(pose_landmarks)}")
                print(f"Face landmarks: {len(face_landmarks)}")
        else:
            print("No camera frame available")
        
        cap.release()
        
    finally:
        detector.cleanup()
        print("✅ Detector cleaned up")

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
        # PRODUCTION PATTERNS (RECOMMENDED)
        example_production_service_startup()
        example_speaker_verification_production()
        example_http_service_client()
        
        # DIRECT API PATTERNS (Alternative)
        example_basic_usage()
        example_speaker_verification_guard()
        example_simple_guard_clause()
        
        # DEPLOYMENT PATTERNS
        example_package_in_requirements_txt()
        example_docker_integration()
        example_service_startup()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed!")
        print("\n🏆 RECOMMENDED PATTERN:")
        print("   1. Start service: python webcam_http_service.py")
        print("   2. Use HTTP client: requests.get('http://localhost:8767/presence/simple')")
        print("   3. Implement guard clause with fail-safe behavior")
        
    except ImportError as e:
        print(f"❌ Package not installed: {e}")
        print("💡 Install with: pip install webcam-detection[service]")
    except Exception as e:
        print(f"❌ Example failed: {e}")

if __name__ == "__main__":
    main() 