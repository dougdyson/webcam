#!/usr/bin/env python3
"""
Simple script to capture test fixture frames from webcam.

Usage:
    python scripts/capture_test_fixtures.py

Controls:
    SPACE - Capture current frame
    Q     - Quit

Saves frames to: tests/fixtures/frames/
"""
import cv2
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.camera import CameraManager
from src.camera.config import CameraConfig


def main():
    # Create fixtures directory
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "frames"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Test Fixture Frame Capture")
    print("=" * 60)
    print(f"Saving to: {fixtures_dir}")
    print()
    print("Controls:")
    print("  SPACE - Capture frame")
    print("  Q     - Quit")
    print()
    print("Suggested captures:")
    print("  1. Human visible (standing normally)")
    print("  2. Human close up (close to camera)")
    print("  3. Empty kitchen, lights on")
    print("  4. Empty kitchen, lights dim")
    print()
    print("Starting camera...")
    print()

    # Initialize camera
    camera_config = CameraConfig()
    camera = CameraManager(camera_config)

    # Try to disable background effects (macOS Portrait mode, etc.)
    # These may or may not work depending on your camera/OS
    try:
        if camera.cap:
            # Disable auto exposure
            camera.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            # Try to disable any background processing
            camera.cap.set(cv2.CAP_PROP_BACKEND, cv2.CAP_AVFOUNDATION)
    except:
        pass  # Some properties may not be supported

    frame_count = 0

    try:
        while True:
            # Get frame
            frame = camera.get_frame()

            if frame is None:
                print("No frame from camera")
                continue

            # Show live preview
            cv2.imshow("Test Fixture Capture - Press SPACE to capture, Q to quit", frame)

            # Wait for key press
            key = cv2.waitKey(1) & 0xFF

            # Q to quit
            if key == ord('q') or key == ord('Q'):
                print("\nQuitting...")
                break

            # SPACE to capture
            elif key == ord(' '):
                frame_count += 1

                # Ask for label
                print(f"\n--- Capture #{frame_count} ---")
                label = input("Enter label (e.g., 'human_standing', 'empty_lights_on'): ").strip()

                if not label:
                    label = f"frame_{frame_count:03d}"

                # Clean label (remove spaces, make lowercase)
                clean_label = label.replace(" ", "_").lower()

                # Save frame
                filename = f"{clean_label}.jpg"
                filepath = fixtures_dir / filename

                cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

                print(f"✓ Saved: {filename}")
                print(f"  Path: {filepath}")
                print()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    finally:
        # Cleanup
        camera.cleanup()
        cv2.destroyAllWindows()

        print()
        print("=" * 60)
        print(f"Captured {frame_count} frames")
        print(f"Saved to: {fixtures_dir}")
        print("=" * 60)


if __name__ == "__main__":
    main()
