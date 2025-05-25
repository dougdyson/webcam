"""
Tests for configuration management functionality.

Following TDD Phase 1, Cycle 1.1: Configuration Management
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.utils.config import ConfigManager, ConfigurationError


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def test_config_manager_loads_yaml(self):
        """Should load camera_profiles.yaml and return valid config."""
        # This test should fail initially since ConfigManager doesn't exist
        config_manager = ConfigManager()
        config = config_manager.load_camera_profile('default')
        
        assert config is not None
        assert 'device_id' in config
        assert 'width' in config
        assert 'height' in config
        assert config['device_id'] == 0
        assert config['width'] == 640
        assert config['height'] == 480
    
    def test_config_manager_handles_missing_file(self):
        """Should raise appropriate exception for missing config."""
        config_manager = ConfigManager()
        
        with pytest.raises(ConfigurationError):
            config_manager.load_camera_profile('nonexistent')
    
    def test_config_manager_loads_detection_config(self):
        """Should load detection configuration parameters."""
        config_manager = ConfigManager()
        config = config_manager.load_detection_config()
        
        assert config is not None
        assert 'model_complexity' in config
        assert 'min_detection_confidence' in config
        assert 'min_tracking_confidence' in config
        assert config['model_complexity'] in [0, 1, 2]
        assert 0.0 <= config['min_detection_confidence'] <= 1.0
    
    def test_config_manager_validates_yaml_structure(self):
        """Should validate YAML structure and required fields."""
        config_manager = ConfigManager()
        
        # This should work with valid YAML
        valid_config = {
            'device_id': 0,
            'width': 640,
            'height': 480,
            'fps': 30
        }
        
        # Should not raise exception
        result = config_manager.validate_camera_config(valid_config)
        assert result is True
        
        # This should fail with invalid YAML
        invalid_config = {
            'device_id': -1,  # Invalid device ID
            'width': 0,       # Invalid width
        }
        
        with pytest.raises(ConfigurationError):
            config_manager.validate_camera_config(invalid_config)
    
    def test_config_manager_handles_yaml_parse_error(self):
        """Should handle malformed YAML files gracefully."""
        config_manager = ConfigManager()
        
        # Mock a malformed YAML file
        malformed_yaml = "invalid: yaml: content: ["
        
        with patch('builtins.open', mock_open(read_data=malformed_yaml)):
            with pytest.raises(ConfigurationError):
                config_manager.load_camera_profile('malformed')
    
    def test_config_manager_uses_environment_overrides(self):
        """Should apply environment variable overrides to configuration."""
        config_manager = ConfigManager()
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'CAMERA_DEVICE_ID': '1',
            'CAMERA_WIDTH': '1280',
            'CAMERA_HEIGHT': '720'
        }):
            config = config_manager.load_camera_profile('default')
            
            assert config['device_id'] == 1
            assert config['width'] == 1280
            assert config['height'] == 720


class TestConfigurationErrors:
    """Test configuration error handling."""
    
    def test_configuration_error_inheritance(self):
        """ConfigurationError should inherit from Exception."""
        assert issubclass(ConfigurationError, Exception)
    
    def test_configuration_error_message(self):
        """ConfigurationError should accept and store error message."""
        message = "Test configuration error"
        error = ConfigurationError(message)
        
        assert str(error) == message 