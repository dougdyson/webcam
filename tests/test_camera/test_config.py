"""
Tests for camera configuration and validation.
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, Mock

from src.camera.config import CameraConfig, CameraConfigError


class TestCameraConfig:
    """Test cases for CameraConfig class."""
    
    def test_camera_config_creation_from_profile(self):
        """Should create valid camera config from profile."""
        config = CameraConfig.from_profile('default')
        
        assert config is not None
        assert config.device_id == 0
        assert config.width == 640
        assert config.height == 480
        assert config.fps == 30
    
    def test_camera_config_creation_with_parameters(self):
        """Should create camera config with explicit parameters."""
        config = CameraConfig(
            device_id=1,
            width=1280,
            height=720,
            fps=60,
            format='MJPG'
        )
        
        assert config.device_id == 1
        assert config.width == 1280
        assert config.height == 720
        assert config.fps == 60
        assert config.format == 'MJPG'
    
    def test_camera_config_validates_device_id(self):
        """Should validate camera device ID."""
        with pytest.raises(ValueError, match="Device ID must be non-negative"):
            CameraConfig(device_id=-1)
    
    def test_camera_config_validates_dimensions(self):
        """Should validate camera dimensions."""
        with pytest.raises(ValueError, match="Width must be positive"):
            CameraConfig(width=0)
            
        with pytest.raises(ValueError, match="Height must be positive"):
            CameraConfig(height=0)
            
        with pytest.raises(ValueError, match="Width must be positive"):
            CameraConfig(width=-1)
    
    def test_camera_config_validates_fps(self):
        """Should validate frame rate."""
        with pytest.raises(ValueError, match="FPS must be positive"):
            CameraConfig(fps=0)
            
        with pytest.raises(ValueError, match="FPS must be positive"):
            CameraConfig(fps=-1)
    
    def test_camera_config_validates_format(self):
        """Should validate video format."""
        with pytest.raises(ValueError, match="Invalid video format"):
            CameraConfig(format='INVALID')
    
    def test_camera_config_loads_from_yaml_profile(self):
        """Should load camera config from YAML profile."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
camera_profiles:
  test_profile:
    device_id: 2
    width: 1920
    height: 1080
    fps: 24
    format: 'YUYV'
    auto_exposure: false
    exposure_time: 100
""")
            config_file = f.name
        
        try:
            config = CameraConfig.from_profile('test_profile', config_file=config_file)
            
            assert config.device_id == 2
            assert config.width == 1920
            assert config.height == 1080
            assert config.fps == 24
            assert config.format == 'YUYV'
            assert config.auto_exposure is False
            assert config.exposure_time == 100
        finally:
            os.unlink(config_file)
    
    def test_camera_config_handles_missing_profile(self):
        """Should handle missing camera profile."""
        with pytest.raises(CameraConfigError, match="Profile 'nonexistent' not found"):
            CameraConfig.from_profile('nonexistent')
    
    def test_camera_config_uses_default_values(self):
        """Should use default values for optional parameters."""
        config = CameraConfig(device_id=0)
        
        assert config.width == 640
        assert config.height == 480
        assert config.fps == 30
        assert config.format == 'YUYV'
        assert config.auto_exposure is True
        assert config.exposure_time is None
        assert config.brightness == 50
        assert config.contrast == 50
    
    def test_camera_config_validates_exposure_settings(self):
        """Should validate exposure settings."""
        # Auto exposure False requires exposure_time
        with pytest.raises(ValueError, match="Exposure time must be provided"):
            CameraConfig(auto_exposure=False, exposure_time=None)
        
        # Exposure time must be positive
        with pytest.raises(ValueError, match="Exposure time must be positive"):
            CameraConfig(auto_exposure=False, exposure_time=0)
    
    def test_camera_config_validates_brightness_contrast(self):
        """Should validate brightness and contrast values."""
        with pytest.raises(ValueError, match="Brightness must be between 0 and 100"):
            CameraConfig(brightness=-1)
            
        with pytest.raises(ValueError, match="Brightness must be between 0 and 100"):
            CameraConfig(brightness=101)
            
        with pytest.raises(ValueError, match="Contrast must be between 0 and 100"):
            CameraConfig(contrast=-1)
            
        with pytest.raises(ValueError, match="Contrast must be between 0 and 100"):
            CameraConfig(contrast=101)
    
    def test_camera_config_to_dict(self):
        """Should convert camera config to dictionary."""
        config = CameraConfig(
            device_id=1,
            width=1280,
            height=720,
            fps=60
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['device_id'] == 1
        assert config_dict['width'] == 1280
        assert config_dict['height'] == 720
        assert config_dict['fps'] == 60
    
    def test_camera_config_from_dict(self):
        """Should create camera config from dictionary."""
        config_dict = {
            'device_id': 2,
            'width': 1920,
            'height': 1080,
            'fps': 24,
            'format': 'MJPG'
        }
        
        config = CameraConfig.from_dict(config_dict)
        
        assert config.device_id == 2
        assert config.width == 1920
        assert config.height == 1080
        assert config.fps == 24
        assert config.format == 'MJPG'
    
    def test_camera_config_repr(self):
        """Should have meaningful string representation."""
        config = CameraConfig(device_id=1, width=1280, height=720)
        
        repr_str = repr(config)
        assert 'CameraConfig' in repr_str
        assert 'device_id=1' in repr_str
        assert '1280x720' in repr_str
    
    def test_camera_config_error_inherits_from_exception(self):
        """CameraConfigError should inherit from Exception."""
        error = CameraConfigError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestCameraConfigIntegration:
    """Integration tests for camera configuration."""
    
    def test_camera_config_loads_all_default_profiles(self):
        """Should load all default camera profiles."""
        profiles = ['default', 'high_quality', 'low_latency']
        
        for profile_name in profiles:
            config = CameraConfig.from_profile(profile_name)
            assert config is not None
            assert config.device_id is not None
            assert config.width > 0
            assert config.height > 0
            assert config.fps > 0
    
    def test_camera_config_applies_environment_overrides(self):
        """Should apply environment variable overrides."""
        with patch.dict(os.environ, {
            'WEBCAM_DEVICE_ID': '3',
            'WEBCAM_WIDTH': '1920',
            'WEBCAM_HEIGHT': '1080'
        }):
            config = CameraConfig.from_profile('default')
            
            assert config.device_id == 3
            assert config.width == 1920
            assert config.height == 1080
    
    def test_camera_config_validation_comprehensive(self):
        """Should perform comprehensive validation of all parameters."""
        # Test multiple validation failures
        with pytest.raises(ValueError):
            CameraConfig(
                device_id=-1,
                width=0,
                height=-1,
                fps=0,
                brightness=150,
                contrast=-50
            ) 