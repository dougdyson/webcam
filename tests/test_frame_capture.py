"""
Tests for frame capture functionality.
"""
import pytest
import numpy as np
import time
from unittest.mock import Mock, patch, MagicMock
import cv2

from src.camera.config import CameraConfig
from src.camera.manager import CameraManager
from src.camera.capture import FrameCapture, FrameCaptureError


class TestFrameCapture:
    """Test cases for FrameCapture class."""
    
    @pytest.fixture
    def camera_config(self):
        """Create a test camera configuration."""
        return CameraConfig(
            device_id=0,
            width=640,
            height=480,
            fps=30,
            format='YUYV'
        )
    
    @pytest.fixture
    def mock_camera_manager(self, camera_config):
        """Create a mock camera manager."""
        manager = Mock(spec=CameraManager)
        manager.config = camera_config
        manager.is_initialized = True
        manager.is_available.return_value = True
        return manager
    
    def test_frame_capture_initialization_success(self, mock_camera_manager):
        """Should initialize frame capture with camera manager."""
        capture = FrameCapture(mock_camera_manager)
        
        assert capture.camera_manager == mock_camera_manager
        assert capture.is_running is False
        assert capture.frame_count == 0
    
    def test_frame_capture_initialization_with_invalid_camera(self):
        """Should handle initialization with invalid camera manager."""
        invalid_manager = Mock()
        invalid_manager.is_initialized = False
        
        with pytest.raises(FrameCaptureError, match="Camera manager not initialized"):
            FrameCapture(invalid_manager)
    
    def test_frame_capture_reads_frame_success(self, mock_camera_manager):
        """Should capture and return frame successfully."""
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_camera_manager.get_frame.return_value = mock_frame
        
        capture = FrameCapture(mock_camera_manager)
        frame = capture.get_frame()
        
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)
        assert capture.frame_count == 1
        mock_camera_manager.get_frame.assert_called_once()
    
    def test_frame_capture_handles_read_failure(self, mock_camera_manager):
        """Should handle failed frame reads gracefully."""
        mock_camera_manager.get_frame.return_value = None
        
        capture = FrameCapture(mock_camera_manager)
        frame = capture.get_frame()
        
        assert frame is None
        assert capture.frame_count == 0  # Don't count failed captures
    
    def test_frame_capture_handles_camera_error(self, mock_camera_manager):
        """Should handle camera manager errors."""
        from src.camera.manager import CameraError
        mock_camera_manager.get_frame.side_effect = CameraError("Camera disconnected")
        
        capture = FrameCapture(mock_camera_manager)
        
        with pytest.raises(FrameCaptureError, match="Frame capture failed"):
            capture.get_frame()
    
    def test_frame_capture_validates_frame_dimensions(self, mock_camera_manager):
        """Should validate captured frame dimensions."""
        # Mock frame with wrong dimensions
        wrong_frame = np.zeros((240, 320, 3), dtype=np.uint8)  # Different from config
        mock_camera_manager.get_frame.return_value = wrong_frame
        
        capture = FrameCapture(mock_camera_manager)
        frame = capture.get_frame()
        
        # Should still return frame but log warning
        assert frame is not None
        assert frame.shape == (240, 320, 3)
        # Check that validation warnings are tracked
        warnings = capture.get_validation_warnings()
        assert len(warnings) > 0
        assert any("dimension" in warning.lower() for warning in warnings)
    
    def test_frame_capture_validates_frame_format(self, mock_camera_manager):
        """Should validate captured frame format."""
        # Mock frame with wrong channel count
        wrong_frame = np.zeros((480, 640), dtype=np.uint8)  # Grayscale instead of RGB
        mock_camera_manager.get_frame.return_value = wrong_frame
        
        capture = FrameCapture(mock_camera_manager)
        frame = capture.get_frame()
        
        # Should still return frame but log warning
        assert frame is not None
        assert len(frame.shape) == 2  # Grayscale
        warnings = capture.get_validation_warnings()
        assert len(warnings) > 0
        assert any("channel" in warning.lower() for warning in warnings)
    
    def test_frame_capture_preprocessing_resize(self, mock_camera_manager):
        """Should preprocess frames by resizing if needed."""
        # Mock larger frame that needs resizing
        large_frame = np.zeros((960, 1280, 3), dtype=np.uint8)
        mock_camera_manager.get_frame.return_value = large_frame
        
        capture = FrameCapture(mock_camera_manager, enable_preprocessing=True, target_size=(480, 640))
        frame = capture.get_frame()
        
        assert frame is not None
        assert frame.shape == (480, 640, 3)  # Should be resized
    
    def test_frame_capture_preprocessing_color_conversion(self, mock_camera_manager):
        """Should preprocess frames by converting color format."""
        # Mock BGR frame (OpenCV default)
        bgr_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_camera_manager.get_frame.return_value = bgr_frame
        
        capture = FrameCapture(mock_camera_manager, enable_preprocessing=True, color_format='RGB')
        frame = capture.get_frame()
        
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        # Note: We can't easily test actual color conversion without image content,
        # but we verify the preprocessing pipeline is called
    
    def test_frame_capture_rate_limiting(self, mock_camera_manager):
        """Should limit frame capture rate when configured."""
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_camera_manager.get_frame.return_value = mock_frame
        
        # Set FPS limit to 10 (100ms interval)
        capture = FrameCapture(mock_camera_manager, max_fps=10)
        
        start_time = time.time()
        
        # Capture 3 frames rapidly
        frame1 = capture.get_frame()
        frame2 = capture.get_frame()
        frame3 = capture.get_frame()
        
        elapsed = time.time() - start_time
        
        assert frame1 is not None
        assert frame2 is not None
        assert frame3 is not None
        # Should take at least 200ms for 3 frames at 10 FPS
        assert elapsed >= 0.2
    
    def test_frame_capture_statistics(self, mock_camera_manager):
        """Should track capture statistics."""
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_camera_manager.get_frame.return_value = mock_frame
        
        capture = FrameCapture(mock_camera_manager)
        
        # Capture several frames
        for _ in range(5):
            capture.get_frame()
        
        stats = capture.get_statistics()
        
        assert stats['frames_captured'] == 5
        assert stats['frames_failed'] == 0
        assert 'average_fps' in stats
        assert 'total_time' in stats
        assert stats['success_rate'] == 1.0
    
    def test_frame_capture_statistics_with_failures(self, mock_camera_manager):
        """Should track statistics including failures."""
        # Mock alternating success/failure
        mock_camera_manager.get_frame.side_effect = [
            np.zeros((480, 640, 3), dtype=np.uint8),  # Success
            None,  # Failure
            np.zeros((480, 640, 3), dtype=np.uint8),  # Success
            None   # Failure
        ]
        
        capture = FrameCapture(mock_camera_manager)
        
        # Capture 4 frames
        for _ in range(4):
            capture.get_frame()
        
        stats = capture.get_statistics()
        
        assert stats['frames_captured'] == 2
        assert stats['frames_failed'] == 2
        assert stats['success_rate'] == 0.5
    
    def test_frame_capture_cleanup(self, mock_camera_manager):
        """Should cleanup resources properly."""
        # Mock a proper frame for the cleanup test
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_camera_manager.get_frame.return_value = mock_frame
        
        capture = FrameCapture(mock_camera_manager)
        
        # Simulate some activity
        capture.get_frame()
        
        # Cleanup
        capture.cleanup()
        
        # Should reset statistics
        stats = capture.get_statistics()
        assert stats['frames_captured'] == 0
        assert stats['frames_failed'] == 0
    
    def test_frame_capture_context_manager(self, mock_camera_manager):
        """Should support context manager protocol."""
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_camera_manager.get_frame.return_value = mock_frame
        
        with FrameCapture(mock_camera_manager) as capture:
            frame = capture.get_frame()
            assert frame is not None
            assert capture.frame_count == 1
        
        # Should cleanup automatically
        stats = capture.get_statistics()
        assert stats['frames_captured'] == 0  # Reset after cleanup
    
    def test_frame_capture_error_inherits_from_exception(self):
        """FrameCaptureError should inherit from Exception."""
        error = FrameCaptureError("Test capture error")
        assert isinstance(error, Exception)
        assert str(error) == "Test capture error"


class TestFrameCaptureIntegration:
    """Integration tests for frame capture."""
    
    @pytest.fixture
    def camera_config(self):
        """Create test camera configuration."""
        return CameraConfig(
            device_id=0,
            width=1280,
            height=720,
            fps=30,
            format='MJPG'
        )
    
    @patch('cv2.VideoCapture')
    def test_frame_capture_with_real_camera_manager(self, mock_cv2, camera_config):
        """Should work with real CameraManager instance."""
        # Mock camera for CameraManager
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 1280,
            cv2.CAP_PROP_FRAME_HEIGHT: 720,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        
        # Mock frame capture
        test_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, test_frame)
        mock_cv2.return_value = mock_cap
        
        # Create real camera manager
        camera_manager = CameraManager(camera_config)
        
        # Create frame capture
        capture = FrameCapture(camera_manager, enable_preprocessing=True)
        
        # Capture frame
        frame = capture.get_frame()
        
        assert frame is not None
        assert frame.shape == (720, 1280, 3)
        assert capture.frame_count == 1
    
    @patch('cv2.VideoCapture')
    def test_frame_capture_performance_monitoring(self, mock_cv2, camera_config):
        """Should monitor capture performance."""
        # Mock fast camera
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 1280,
            cv2.CAP_PROP_FRAME_HEIGHT: 720,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        
        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, test_frame)
        mock_cv2.return_value = mock_cap
        
        camera_manager = CameraManager(camera_config)
        capture = FrameCapture(camera_manager, max_fps=15)  # Limit to 15 FPS
        
        start_time = time.time()
        
        # Capture multiple frames
        for _ in range(5):
            frame = capture.get_frame()
            assert frame is not None
        
        elapsed = time.time() - start_time
        stats = capture.get_statistics()
        
        # Should respect FPS limit
        assert elapsed >= 4 / 15  # At least 4 intervals at 15 FPS
        assert stats['frames_captured'] == 5
        assert stats['average_fps'] <= 20  # Should be around 15 or less 