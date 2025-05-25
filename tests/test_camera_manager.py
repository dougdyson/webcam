"""
Tests for camera manager functionality.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import cv2

from src.camera.config import CameraConfig
from src.camera.manager import CameraManager, CameraError


class TestCameraManager:
    """Test cases for CameraManager class."""
    
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
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_initialization_success(self, mock_cv2, camera_config):
        """Should initialize camera successfully with valid configuration."""
        # Mock successful camera initialization
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        
        assert manager.is_initialized is True
        assert manager.config == camera_config
        mock_cv2.assert_called_with(0)
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_initialization_failure(self, mock_cv2, camera_config):
        """Should handle camera initialization failure."""
        # Mock failed camera initialization
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_cv2.return_value = mock_cap
        
        with pytest.raises(CameraError, match="Failed to initialize camera"):
            CameraManager(camera_config)
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_applies_configuration_properties(self, mock_cv2, camera_config):
        """Should apply camera configuration properties during initialization."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        
        # Should set camera properties
        expected_calls = [
            (cv2.CAP_PROP_FRAME_WIDTH, 640),
            (cv2.CAP_PROP_FRAME_HEIGHT, 480),
            (cv2.CAP_PROP_FPS, 30),
            (cv2.CAP_PROP_BRIGHTNESS, 0.5),
            (cv2.CAP_PROP_CONTRAST, 0.5),
            (cv2.CAP_PROP_BUFFERSIZE, 1)
        ]
        
        for prop, value in expected_calls:
            mock_cap.set.assert_any_call(prop, value)
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_get_frame_success(self, mock_cv2, camera_config):
        """Should successfully capture and return a frame."""
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cap.read.return_value = (True, mock_frame)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        frame = manager.get_frame()
        
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)
        mock_cap.read.assert_called_once()
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_get_frame_failure(self, mock_cv2, camera_config):
        """Should handle failed frame capture."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cap.read.return_value = (False, None)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        frame = manager.get_frame()
        
        assert frame is None
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_get_frame_timeout(self, mock_cv2, camera_config):
        """Should handle frame capture timeout by attempting reconnection and returning None."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        # Simulate timeout by making read hang
        mock_cap.read.side_effect = Exception("Timeout")
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        
        # Should attempt reconnection and return None when it fails
        frame = manager.get_frame()
        assert frame is None
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_is_available(self, mock_cv2, camera_config):
        """Should check if camera is available and working."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        
        assert manager.is_available() is True
        
        # Simulate camera becoming unavailable
        mock_cap.isOpened.return_value = False
        assert manager.is_available() is False
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_cleanup(self, mock_cv2, camera_config):
        """Should properly cleanup camera resources."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        manager.cleanup()
        
        mock_cap.release.assert_called_once()
        assert manager.is_initialized is False
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_context_manager(self, mock_cv2, camera_config):
        """Should support context manager protocol."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        with CameraManager(camera_config) as manager:
            assert manager.is_initialized is True
        
        # Should cleanup automatically
        mock_cap.release.assert_called_once()
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_get_capabilities(self, mock_cv2, camera_config):
        """Should detect and return camera capabilities."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 1920,
            cv2.CAP_PROP_FRAME_HEIGHT: 1080,
            cv2.CAP_PROP_FPS: 60,
            cv2.CAP_PROP_BRIGHTNESS: 0.5,
            cv2.CAP_PROP_CONTRAST: 0.5
        }.get(prop, -1)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(camera_config)
        capabilities = manager.get_capabilities()
        
        assert isinstance(capabilities, dict)
        assert 'max_width' in capabilities
        assert 'max_height' in capabilities
        assert 'max_fps' in capabilities
        assert capabilities['max_width'] == 1920
        assert capabilities['max_height'] == 1080
    
    def test_camera_error_inherits_from_exception(self):
        """CameraError should inherit from Exception."""
        error = CameraError("Test camera error")
        assert isinstance(error, Exception)
        assert str(error) == "Test camera error"


class TestCameraManagerIntegration:
    """Integration tests for camera manager."""
    
    @pytest.fixture
    def high_quality_config(self):
        """Create a high-quality camera configuration."""
        return CameraConfig(
            device_id=0,
            width=1920,
            height=1080,
            fps=30,
            format='MJPG',
            brightness=60,
            contrast=55
        )
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_configuration_validation(self, mock_cv2, high_quality_config):
        """Should validate that applied configuration matches requested configuration."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        # Mock that camera accepts all our settings
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 1920,
            cv2.CAP_PROP_FRAME_HEIGHT: 1080,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        manager = CameraManager(high_quality_config)
        
        # Should verify applied settings match requested
        assert manager.get_actual_width() == 1920
        assert manager.get_actual_height() == 1080
        assert manager.get_actual_fps() == 30
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_with_unsupported_resolution(self, mock_cv2):
        """Should handle camera that doesn't support requested resolution."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        # Mock that camera falls back to lower resolution
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,  # Falls back from 1920
            cv2.CAP_PROP_FRAME_HEIGHT: 480,  # Falls back from 1080
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        config = CameraConfig(width=1920, height=1080, fps=30)
        manager = CameraManager(config)
        
        # Should log warning about resolution fallback
        warnings = manager.get_configuration_warnings()
        assert len(warnings) > 0
        assert any("resolution" in warning.lower() for warning in warnings)
    
    @patch('cv2.VideoCapture')
    def test_camera_manager_multiple_devices(self, mock_cv2):
        """Should handle different camera device IDs."""
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            cv2.CAP_PROP_FRAME_WIDTH: 640,
            cv2.CAP_PROP_FRAME_HEIGHT: 480,
            cv2.CAP_PROP_FPS: 30
        }.get(prop, 0)
        mock_cv2.return_value = mock_cap
        
        # Test device ID 0
        config_0 = CameraConfig(device_id=0)
        manager_0 = CameraManager(config_0)
        mock_cv2.assert_called_with(0)
        
        # Test device ID 1
        config_1 = CameraConfig(device_id=1)
        manager_1 = CameraManager(config_1)
        mock_cv2.assert_called_with(1)
        
        # Both should be initialized
        assert manager_0.is_initialized is True
        assert manager_1.is_initialized is True 