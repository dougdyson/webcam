#!/usr/bin/env python3
"""
Capture Room Photo for Layout Analysis

This script captures a single frame from your webcam and saves it as an image
that you can then upload to a premium vision model (GPT-4 Vision, Claude Vision, etc.)
to generate your room layout description.

Usage:
    python scripts/capture_room_photo.py
    
The image will be saved as 'room_layout_photo.jpg' in the current directory.
"""

import cv2
import sys
import os
from datetime import datetime
from pathlib import Path

def capture_room_photo(output_filename: str = "room_layout_photo.jpg", camera_index: int = 0):
    """
    Capture a single frame from the webcam and save it as an image.
    
    Args:
        output_filename: Name of the output image file
        camera_index: Camera index (0 for default camera)
        
    Returns:
        bool: True if successful, False otherwise
    """
    print("📸 Capturing Room Photo for Layout Analysis")
    print("=" * 45)
    
    # Initialize camera
    print(f"🔍 Initializing camera {camera_index}...")
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"❌ Error: Could not open camera {camera_index}")
        print("💡 Try a different camera index (1, 2, etc.) or check camera permissions")
        return False
    
    # Set camera properties for better quality
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  # Try for 1080p
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("📷 Camera initialized successfully")
    print("⏳ Waiting 2 seconds for camera to stabilize...")
    
    # Let camera stabilize
    for i in range(60):  # Read a few frames to let camera adjust
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Could not read frame from camera")
            cap.release()
            return False
    
    print("📸 Capturing photo...")
    
    # Capture the final frame
    ret, frame = cap.read()
    
    if not ret:
        print("❌ Error: Could not capture frame")
        cap.release()
        return False
    
    # Get actual frame dimensions
    height, width = frame.shape[:2]
    print(f"📐 Captured frame size: {width}x{height}")
    
    # Save the image
    success = cv2.imwrite(output_filename, frame)
    
    if success:
        file_size = os.path.getsize(output_filename) / (1024 * 1024)  # MB
        print(f"✅ Photo saved successfully!")
        print(f"📁 File: {output_filename}")
        print(f"📏 Size: {file_size:.1f} MB")
        print(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"❌ Error: Could not save image to {output_filename}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    return success


def display_next_steps(filename: str):
    """Display instructions for using the captured image."""
    print("\n🚀 Next Steps:")
    print("=" * 15)
    print("1. Upload the captured image to a premium vision model:")
    print("   • GPT-4 Vision (ChatGPT Plus)")
    print("   • Claude 3 Opus/Sonnet with Vision")
    print("   • Google Gemini Pro Vision")
    print()
    print("2. Use the prompt from: prompts/room_layout_generator.md")
    print()
    print("3. Copy the generated layout to: config/room_layout.txt")
    print()
    print("4. Test with: python examples/enhanced_room_description.py")
    print()
    print(f"📎 Your image: {filename}")


def main():
    """Main function to capture room photo."""
    # Check if we're in the right directory
    if not Path("src").exists():
        print("⚠️  Warning: Run this from the project root directory")
        print("💡 Current directory:", os.getcwd())
        print("🔄 Change to the webcam project directory first")
        return
    
    # Default output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"room_layout_photo_{timestamp}.jpg"
    
    # Allow custom filename from command line
    if len(sys.argv) > 1:
        output_filename = sys.argv[1]
    else:
        output_filename = default_filename
    
    # Allow custom camera index
    camera_index = 0
    if len(sys.argv) > 2:
        try:
            camera_index = int(sys.argv[2])
        except ValueError:
            print("⚠️  Invalid camera index, using default (0)")
    
    print(f"🎯 Output file: {output_filename}")
    print(f"📹 Camera index: {camera_index}")
    print()
    
    # Capture the photo
    success = capture_room_photo(output_filename, camera_index)
    
    if success:
        display_next_steps(output_filename)
    else:
        print("\n🔧 Troubleshooting:")
        print("• Check camera permissions")
        print("• Try different camera index: python scripts/capture_room_photo.py room.jpg 1")
        print("• Ensure no other app is using the camera")
        print("• On macOS, check System Preferences > Security & Privacy > Camera")


if __name__ == "__main__":
    main() 