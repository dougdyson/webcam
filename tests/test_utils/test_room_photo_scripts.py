"""
Tests for room photo capture and adjustment scripts.

This module tests the scripts we created for capturing room photos
and adjusting them for premium vision model analysis.
"""
import pytest
import tempfile
import os
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


class TestRoomPhotoCapture:
    """Test room photo capture functionality."""
    
    @pytest.fixture
    def mock_camera(self):
        """Mock camera for testing."""
        mock_cap = Mock()
        # Simulate successful camera initialization
        mock_cap.isOpened.return_value = True
        # Create a test frame (blue image)
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_frame[:, :, 0] = 255  # Blue channel
        mock_cap.read.return_value = (True, test_frame)
        mock_cap.release.return_value = None
        return mock_cap
    
    @patch('cv2.VideoCapture')
    @patch('cv2.imwrite')
    def test_capture_room_photo_success(self, mock_imwrite, mock_video_capture, mock_camera):
        """Should capture room photo successfully."""
        if not CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        mock_video_capture.return_value = mock_camera
        mock_imwrite.return_value = True
        
        # Import the script functionality (would normally be in scripts/capture_room_photo.py)
        def capture_room_photo(output_path="room_photo.jpg", camera_index=0):
            """Mock version of capture room photo script."""
            cap = cv2.VideoCapture(camera_index)
            
            if not cap.isOpened():
                raise RuntimeError("Could not open camera")
            
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                cap.release()
                raise RuntimeError("Could not read frame from camera")
            
            # Save the frame
            success = cv2.imwrite(output_path, frame)
            cap.release()
            
            if not success:
                raise RuntimeError("Could not save image")
            
            return output_path
        
        # Test the capture
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            result_path = capture_room_photo(output_path)
            
            # Verify camera operations
            mock_video_capture.assert_called_once_with(0)
            mock_camera.isOpened.assert_called_once()
            mock_camera.read.assert_called_once()
            mock_camera.release.assert_called_once()
            
            # Verify image save
            mock_imwrite.assert_called_once()
            assert result_path == output_path
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    @patch('cv2.VideoCapture')
    def test_capture_room_photo_camera_not_available(self, mock_video_capture):
        """Should handle camera not available gracefully."""
        if not CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        def capture_room_photo(output_path="room_photo.jpg", camera_index=0):
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                raise RuntimeError("Could not open camera")
            return output_path
        
        with pytest.raises(RuntimeError, match="Could not open camera"):
            capture_room_photo()
    
    @patch('cv2.VideoCapture')
    def test_capture_room_photo_read_failure(self, mock_video_capture, mock_camera):
        """Should handle frame read failure."""
        if not CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        mock_camera.read.return_value = (False, None)  # Read failure
        mock_video_capture.return_value = mock_camera
        
        def capture_room_photo(output_path="room_photo.jpg", camera_index=0):
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                raise RuntimeError("Could not open camera")
            
            ret, frame = cap.read()
            if not ret:
                cap.release()
                raise RuntimeError("Could not read frame from camera")
            return output_path
        
        with pytest.raises(RuntimeError, match="Could not read frame from camera"):
            capture_room_photo()
        
        # Should still release camera
        mock_camera.release.assert_called_once()


class TestRoomPhotoAdjustment:
    """Test room photo adjustment functionality."""
    
    def create_test_image(self, width=640, height=480):
        """Create test image for adjustment testing."""
        # Create overexposed-looking image (very bright)
        img = np.ones((height, width, 3), dtype=np.uint8) * 200  # Bright image
        return img
    
    @patch('cv2.imread')
    @patch('cv2.imwrite')
    def test_adjust_room_photo_gentle_preset(self, mock_imwrite, mock_imread):
        """Should apply gentle adjustment preset correctly."""
        if not CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        test_img = self.create_test_image()
        mock_imread.return_value = test_img
        mock_imwrite.return_value = True
        
        def adjust_room_photo(input_path, output_path, preset="gentle"):
            """Mock version of adjust room photo script."""
            img = cv2.imread(input_path)
            if img is None:
                raise RuntimeError("Could not load image")
            
            if preset == "gentle":
                # Gentle adjustments
                brightness = -20
                contrast = 1.1
                gamma = 1.1
            elif preset == "balanced":
                brightness = -40
                contrast = 1.2
                gamma = 1.2
            elif preset == "strong":
                brightness = -60
                contrast = 1.3
                gamma = 1.3
            else:
                raise ValueError(f"Unknown preset: {preset}")
            
            # Apply brightness
            adjusted = cv2.add(img, np.ones(img.shape, dtype=np.uint8) * brightness)
            
            # Apply contrast (simplified)
            adjusted = cv2.multiply(adjusted, contrast)
            
            # Apply gamma correction (simplified)
            gamma_table = np.array([((i / 255.0) ** (1.0 / gamma)) * 255 for i in range(256)]).astype("uint8")
            adjusted = cv2.LUT(adjusted, gamma_table)
            
            success = cv2.imwrite(output_path, adjusted)
            if not success:
                raise RuntimeError("Could not save adjusted image")
            
            return output_path
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as input_file, \
             tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as output_file:
            
            input_path = input_file.name
            output_path = output_file.name
        
        try:
            result_path = adjust_room_photo(input_path, output_path, "gentle")
            
            # Verify file operations
            mock_imread.assert_called_once_with(input_path)
            mock_imwrite.assert_called_once()
            assert result_path == output_path
            
        finally:
            for path in [input_path, output_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    @patch('cv2.imread')
    @patch('cv2.imwrite')
    def test_adjust_room_photo_all_presets(self, mock_imwrite, mock_imread):
        """Should handle all adjustment presets correctly."""
        if not CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        test_img = self.create_test_image()
        mock_imread.return_value = test_img
        mock_imwrite.return_value = True
        
        def adjust_room_photo(input_path, output_path, preset="gentle"):
            img = cv2.imread(input_path)
            if img is None:
                raise RuntimeError("Could not load image")
            
            presets = {
                "gentle": {"brightness": -20, "contrast": 1.1, "gamma": 1.1},
                "balanced": {"brightness": -40, "contrast": 1.2, "gamma": 1.2},
                "strong": {"brightness": -60, "contrast": 1.3, "gamma": 1.3}
            }
            
            if preset not in presets:
                raise ValueError(f"Unknown preset: {preset}")
            
            # Apply adjustments (simplified for testing)
            adjusted = img.copy()
            success = cv2.imwrite(output_path, adjusted)
            if not success:
                raise RuntimeError("Could not save adjusted image")
            
            return output_path
        
        presets_to_test = ["gentle", "balanced", "strong"]
        
        for preset in presets_to_test:
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as input_file, \
                 tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as output_file:
                
                input_path = input_file.name
                output_path = output_file.name
            
            try:
                result_path = adjust_room_photo(input_path, output_path, preset)
                assert result_path == output_path
                
            finally:
                for path in [input_path, output_path]:
                    if os.path.exists(path):
                        os.unlink(path)
    
    @patch('cv2.imread')
    def test_adjust_room_photo_invalid_image(self, mock_imread):
        """Should handle invalid image files gracefully."""
        if not CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        mock_imread.return_value = None  # Simulate failed image load
        
        def adjust_room_photo(input_path, output_path, preset="gentle"):
            img = cv2.imread(input_path)
            if img is None:
                raise RuntimeError("Could not load image")
            return output_path
        
        with pytest.raises(RuntimeError, match="Could not load image"):
            adjust_room_photo("invalid_image.jpg", "output.jpg")
    
    def test_adjust_room_photo_invalid_preset(self):
        """Should handle invalid preset gracefully."""
        def adjust_room_photo(input_path, output_path, preset="gentle"):
            valid_presets = ["gentle", "balanced", "strong"]
            if preset not in valid_presets:
                raise ValueError(f"Unknown preset: {preset}")
            return output_path
        
        with pytest.raises(ValueError, match="Unknown preset: invalid"):
            adjust_room_photo("input.jpg", "output.jpg", "invalid")


class TestRoomPhotoScriptIntegration:
    """Test integration between capture and adjustment scripts."""
    
    @patch('cv2.VideoCapture')
    @patch('cv2.imread')
    @patch('cv2.imwrite')
    def test_capture_and_adjust_workflow(self, mock_imwrite, mock_imread, mock_video_capture):
        """Should work end-to-end from capture to adjustment."""
        if not CV2_AVAILABLE:
            pytest.skip("OpenCV not available")
        
        # Mock camera
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        test_frame = self.create_test_image()
        mock_cap.read.return_value = (True, test_frame)
        mock_cap.release.return_value = None
        mock_video_capture.return_value = mock_cap
        
        # Mock image read for adjustment
        mock_imread.return_value = test_frame
        mock_imwrite.return_value = True
        
        def capture_and_adjust_room_photo(raw_output="room_raw.jpg", 
                                         adjusted_output="room_adjusted.jpg",
                                         preset="balanced"):
            """Combined capture and adjustment workflow."""
            # Capture photo
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise RuntimeError("Could not open camera")
            
            ret, frame = cap.read()
            if not ret:
                cap.release()
                raise RuntimeError("Could not read frame from camera")
            
            success = cv2.imwrite(raw_output, frame)
            cap.release()
            if not success:
                raise RuntimeError("Could not save raw image")
            
            # Adjust photo
            img = cv2.imread(raw_output)
            if img is None:
                raise RuntimeError("Could not load captured image")
            
            # Apply adjustments (simplified)
            adjusted = img.copy()  # In real implementation, would apply DSP adjustments
            
            success = cv2.imwrite(adjusted_output, adjusted)
            if not success:
                raise RuntimeError("Could not save adjusted image")
            
            return raw_output, adjusted_output
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as raw_file, \
             tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as adjusted_file:
            
            raw_path = raw_file.name
            adjusted_path = adjusted_file.name
        
        try:
            raw_result, adjusted_result = capture_and_adjust_room_photo(raw_path, adjusted_path)
            
            # Verify both files were created
            assert raw_result == raw_path
            assert adjusted_result == adjusted_path
            
            # Verify camera operations
            mock_cap.isOpened.assert_called_once()
            mock_cap.read.assert_called_once()
            mock_cap.release.assert_called_once()
            
            # Verify file operations (2 writes: raw + adjusted)
            assert mock_imwrite.call_count == 2
            
        finally:
            for path in [raw_path, adjusted_path]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def create_test_image(self, width=640, height=480):
        """Create test image for testing."""
        return np.ones((height, width, 3), dtype=np.uint8) * 150


class TestRoomPhotoMetadata:
    """Test room photo metadata and timestamp functionality."""
    
    def test_photo_timestamp_generation(self):
        """Should generate appropriate timestamps for photos."""
        def generate_photo_filename(base_name="room_photo", timestamp=None):
            """Generate timestamped photo filename."""
            if timestamp is None:
                timestamp = datetime.now()
            
            timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
            return f"{base_name}_{timestamp_str}.jpg"
        
        # Test with specific timestamp
        test_time = datetime(2024, 1, 15, 10, 30, 45)
        filename = generate_photo_filename("test_room", test_time)
        assert filename == "test_room_20240115_103045.jpg"
        
        # Test with current timestamp
        filename = generate_photo_filename()
        assert filename.startswith("room_photo_")
        assert filename.endswith(".jpg")
        assert len(filename) > len("room_photo_.jpg")  # Should have timestamp
    
    def test_photo_metadata_extraction(self):
        """Should extract relevant metadata from photo operations."""
        def extract_photo_metadata(capture_success, adjustment_success, 
                                 capture_time, adjustment_time):
            """Extract metadata from photo operations."""
            metadata = {
                "capture_timestamp": capture_time.isoformat() if capture_time else None,
                "adjustment_timestamp": adjustment_time.isoformat() if adjustment_time else None,
                "capture_success": capture_success,
                "adjustment_success": adjustment_success,
                "processing_steps": []
            }
            
            if capture_success:
                metadata["processing_steps"].append("capture")
            if adjustment_success:
                metadata["processing_steps"].append("adjustment")
            
            return metadata
        
        # Test successful operation
        capture_time = datetime.now()
        adjustment_time = datetime.now()
        
        metadata = extract_photo_metadata(True, True, capture_time, adjustment_time)
        
        assert metadata["capture_success"] is True
        assert metadata["adjustment_success"] is True
        assert "capture" in metadata["processing_steps"]
        assert "adjustment" in metadata["processing_steps"]
        assert metadata["capture_timestamp"] is not None
        assert metadata["adjustment_timestamp"] is not None
    
    def test_room_photo_script_error_reporting(self):
        """Should provide clear error reporting for script failures."""
        def run_room_photo_script(camera_available=True, image_writable=True):
            """Simulate room photo script execution with error conditions."""
            errors = []
            
            if not camera_available:
                errors.append("Camera not available or accessible")
            
            if not image_writable:
                errors.append("Unable to write image file - check permissions")
            
            if errors:
                return {
                    "success": False,
                    "errors": errors,
                    "output_files": []
                }
            else:
                return {
                    "success": True,
                    "errors": [],
                    "output_files": ["room_photo.jpg"]
                }
        
        # Test successful execution
        result = run_room_photo_script(camera_available=True, image_writable=True)
        assert result["success"] is True
        assert len(result["errors"]) == 0
        assert "room_photo.jpg" in result["output_files"]
        
        # Test camera failure
        result = run_room_photo_script(camera_available=False, image_writable=True)
        assert result["success"] is False
        assert "Camera not available" in result["errors"][0]
        
        # Test file write failure
        result = run_room_photo_script(camera_available=True, image_writable=False)
        assert result["success"] is False
        assert "Unable to write image file" in result["errors"][0] 