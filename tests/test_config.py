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


class TestOllamaConfigurationIntegration:
    """Test Phase 6.1.1: Ollama Configuration in Main Config File (RED PHASE)"""
    
    def test_config_manager_loads_ollama_config(self):
        """Should load Ollama configuration from main config file."""
        # RED PHASE: This test should fail because Ollama config integration doesn't exist yet
        config_manager = ConfigManager()
        
        # Should be able to load Ollama configuration
        ollama_config = config_manager.load_ollama_config()
        
        # Validate Ollama configuration structure
        assert ollama_config is not None
        assert isinstance(ollama_config, dict)
        
        # Check required Ollama fields
        assert 'client' in ollama_config
        assert 'description_service' in ollama_config
        assert 'async_processor' in ollama_config
        assert 'snapshot_buffer' in ollama_config
        
        # Validate client configuration
        client_config = ollama_config['client']
        assert 'base_url' in client_config
        assert 'model' in client_config
        assert 'timeout_seconds' in client_config
        assert 'max_retries' in client_config
        
        # Validate description service configuration
        desc_config = ollama_config['description_service']
        assert 'cache_ttl_seconds' in desc_config
        assert 'max_concurrent_requests' in desc_config
        assert 'enable_caching' in desc_config
        assert 'enable_fallback_descriptions' in desc_config
        
        # Validate async processor configuration
        async_config = ollama_config['async_processor']
        assert 'max_queue_size' in async_config
        assert 'rate_limit_per_second' in async_config
        assert 'enable_retries' in async_config
        
        # Validate snapshot buffer configuration
        buffer_config = ollama_config['snapshot_buffer']
        assert 'max_size' in buffer_config
        assert 'min_confidence_threshold' in buffer_config
        assert 'debounce_frames' in buffer_config
    
    def test_config_manager_creates_default_ollama_config_file(self):
        """Should create default ollama_config.yaml if it doesn't exist."""
        # RED PHASE: This test should fail because automatic config creation doesn't exist yet
        config_manager = ConfigManager()
        
        # Should create default Ollama config file
        ollama_config_path = config_manager.get_config_directory() / "ollama_config.yaml"
        
        # Config file should exist after ConfigManager initialization
        assert ollama_config_path.exists(), "Default ollama_config.yaml should be created automatically"
        
        # Should be able to load the created config
        ollama_config = config_manager.load_ollama_config()
        assert ollama_config is not None
    
    def test_config_manager_validates_ollama_config_structure(self):
        """Should validate Ollama configuration structure and values."""
        # RED PHASE: This test should fail because validation doesn't exist yet
        config_manager = ConfigManager()
        
        # Valid Ollama configuration
        valid_config = {
            'client': {
                'base_url': 'http://localhost:11434',
                'model': 'gemma3:4b-it-q4_K_M',
                'timeout_seconds': 30.0,
                'max_retries': 2
            },
            'description_service': {
                'cache_ttl_seconds': 300,
                'max_concurrent_requests': 3,
                'enable_caching': True,
                'enable_fallback_descriptions': True
            },
            'async_processor': {
                'max_queue_size': 100,
                'rate_limit_per_second': 0.5,
                'enable_retries': False
            },
            'snapshot_buffer': {
                'max_size': 50,
                'min_confidence_threshold': 0.7,
                'debounce_frames': 3
            }
        }
        
        # Should validate successfully
        result = config_manager.validate_ollama_config(valid_config)
        assert result is True
        
        # Invalid configurations should fail validation
        invalid_configs = [
            # Missing client section
            {'description_service': {'cache_ttl_seconds': 300}},
            # Invalid URL
            {'client': {'base_url': 'invalid-url', 'model': 'gemma3:4b'}},
            # Invalid timeout
            {'client': {'base_url': 'http://localhost:11434', 'timeout_seconds': -1}},
            # Invalid cache TTL
            {'client': {'base_url': 'http://localhost:11434'}, 'description_service': {'cache_ttl_seconds': 0}},
            # Invalid confidence threshold
            {'client': {'base_url': 'http://localhost:11434'}, 'snapshot_buffer': {'min_confidence_threshold': 1.5}},
        ]
        
        for invalid_config in invalid_configs:
            with pytest.raises(ConfigurationError):
                config_manager.validate_ollama_config(invalid_config)
    
    def test_config_manager_applies_ollama_environment_overrides(self):
        """Should apply environment variable overrides to Ollama configuration."""
        # RED PHASE: This test should fail because environment overrides don't exist yet
        config_manager = ConfigManager()
        
        # Mock environment variables for Ollama
        with patch.dict(os.environ, {
            'OLLAMA_BASE_URL': 'http://custom-ollama:11434',
            'OLLAMA_MODEL': 'custom-model:latest',
            'OLLAMA_TIMEOUT': '45.0',
            'OLLAMA_MAX_RETRIES': '5',
            'OLLAMA_CACHE_TTL': '600',
            'OLLAMA_MAX_CONCURRENT': '5',
            'OLLAMA_ENABLE_CACHING': 'false',
            'OLLAMA_QUEUE_SIZE': '200',
            'OLLAMA_RATE_LIMIT': '1.0',
            'OLLAMA_BUFFER_SIZE': '100',
            'OLLAMA_MIN_CONFIDENCE': '0.8'
        }):
            ollama_config = config_manager.load_ollama_config()
            
            # Should apply environment overrides
            assert ollama_config['client']['base_url'] == 'http://custom-ollama:11434'
            assert ollama_config['client']['model'] == 'custom-model:latest'
            assert ollama_config['client']['timeout_seconds'] == 45.0
            assert ollama_config['client']['max_retries'] == 5
            assert ollama_config['description_service']['cache_ttl_seconds'] == 600
            assert ollama_config['description_service']['max_concurrent_requests'] == 5
            assert ollama_config['description_service']['enable_caching'] is False
            assert ollama_config['async_processor']['max_queue_size'] == 200
            assert ollama_config['async_processor']['rate_limit_per_second'] == 1.0
            assert ollama_config['snapshot_buffer']['max_size'] == 100
            assert ollama_config['snapshot_buffer']['min_confidence_threshold'] == 0.8
    
    def test_config_manager_handles_missing_ollama_config_gracefully(self):
        """Should handle missing ollama_config.yaml gracefully."""
        # RED PHASE: This test should fail because graceful handling doesn't exist yet
        config_manager = ConfigManager()
        
        # Mock missing config file
        with patch('pathlib.Path.exists', return_value=False):
            # Should create default config or return default values
            ollama_config = config_manager.load_ollama_config()
            
            # Should still return valid configuration (defaults)
            assert ollama_config is not None
            assert 'client' in ollama_config
            assert ollama_config['client']['base_url'] == 'http://localhost:11434'  # Default URL
    
    def test_config_manager_lists_available_ollama_models(self):
        """Should provide method to list available Ollama models."""
        # RED PHASE: This test should fail because model listing doesn't exist yet
        config_manager = ConfigManager()
        
        # Should provide method to list available models
        available_models = config_manager.list_available_ollama_models()
        
        assert isinstance(available_models, list)
        # Should include commonly available models
        expected_models = ['gemma3:4b-it-q4_K_M', 'gemma3:12b-it-q4_K_M', 'llama3.2-vision']
        for model in expected_models:
            assert model in available_models or len(available_models) == 0  # Empty if Ollama not available 