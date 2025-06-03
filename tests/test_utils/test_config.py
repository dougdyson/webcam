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


class TestOllamaConfigurationValidationAndDefaults:
    """Test Phase 6.1.2: Configuration Validation and Defaults (RED PHASE)"""
    
    def test_config_manager_validates_comprehensive_ollama_config(self):
        """Should perform comprehensive validation of all Ollama configuration sections."""
        # RED PHASE: This test should fail because comprehensive validation doesn't exist yet
        config_manager = ConfigManager()
        
        # Test validation of all configuration values with edge cases
        edge_case_configs = [
            # Edge case: minimum values
            {
                'client': {
                    'base_url': 'http://localhost:11434',
                    'model': 'gemma3:1b',
                    'timeout_seconds': 0.1,  # Very low but valid
                    'max_retries': 0
                },
                'description_service': {
                    'cache_ttl_seconds': 1,  # Very low but valid
                    'max_concurrent_requests': 1,
                    'enable_caching': True,
                    'enable_fallback_descriptions': True
                },
                'async_processor': {
                    'max_queue_size': 1,
                    'rate_limit_per_second': 0.01,  # Very low but valid
                    'enable_retries': True
                },
                'snapshot_buffer': {
                    'max_size': 1,
                    'min_confidence_threshold': 0.0,  # Edge case: minimum confidence
                    'debounce_frames': 1
                }
            },
            # Edge case: maximum reasonable values
            {
                'client': {
                    'base_url': 'https://production-ollama.company.com:8443',
                    'model': 'custom-enterprise-model:latest-optimized-q8_0',
                    'timeout_seconds': 300.0,  # 5 minutes
                    'max_retries': 10
                },
                'description_service': {
                    'cache_ttl_seconds': 86400,  # 24 hours
                    'max_concurrent_requests': 20,
                    'enable_caching': True,
                    'enable_fallback_descriptions': False  # Disable fallbacks in production
                },
                'async_processor': {
                    'max_queue_size': 10000,
                    'rate_limit_per_second': 10.0,
                    'enable_retries': False
                },
                'snapshot_buffer': {
                    'max_size': 1000,
                    'min_confidence_threshold': 1.0,  # Edge case: maximum confidence
                    'debounce_frames': 100
                }
            }
        ]
        
        # All edge case configs should validate successfully
        for config in edge_case_configs:
            result = config_manager.validate_ollama_config(config)
            assert result is True, f"Edge case config should validate: {config}"
    
    def test_config_manager_provides_helpful_validation_error_messages(self):
        """Should provide detailed, helpful error messages for configuration validation failures."""
        # RED PHASE: This test should fail because detailed error messages don't exist yet
        config_manager = ConfigManager()
        
        # Test specific validation error scenarios with helpful messages
        validation_test_cases = [
            # Test case: Invalid model name format
            {
                'config': {
                    'client': {
                        'base_url': 'http://localhost:11434',
                        'model': '',  # Empty model name
                        'timeout_seconds': 30.0,
                        'max_retries': 2
                    },
                    'description_service': {'cache_ttl_seconds': 300, 'max_concurrent_requests': 3, 'enable_caching': True, 'enable_fallback_descriptions': True},
                    'async_processor': {'max_queue_size': 100, 'rate_limit_per_second': 0.5, 'enable_retries': False},
                    'snapshot_buffer': {'max_size': 50, 'min_confidence_threshold': 0.7, 'debounce_frames': 3}
                },
                'expected_error_keywords': ['model', 'empty', 'name']
            },
            # Test case: Invalid URL with helpful suggestion
            {
                'config': {
                    'client': {
                        'base_url': 'localhost:11434',  # Missing protocol
                        'model': 'gemma3:4b',
                        'timeout_seconds': 30.0,
                        'max_retries': 2
                    },
                    'description_service': {'cache_ttl_seconds': 300, 'max_concurrent_requests': 3, 'enable_caching': True, 'enable_fallback_descriptions': True},
                    'async_processor': {'max_queue_size': 100, 'rate_limit_per_second': 0.5, 'enable_retries': False},
                    'snapshot_buffer': {'max_size': 50, 'min_confidence_threshold': 0.7, 'debounce_frames': 3}
                },
                'expected_error_keywords': ['base_url', 'http://', 'https://']
            },
            # Test case: Invalid concurrent requests with performance warning
            {
                'config': {
                    'client': {'base_url': 'http://localhost:11434', 'model': 'gemma3:4b', 'timeout_seconds': 30.0, 'max_retries': 2},
                    'description_service': {
                        'cache_ttl_seconds': 300,
                        'max_concurrent_requests': 0,  # Invalid: zero concurrent requests
                        'enable_caching': True,
                        'enable_fallback_descriptions': True
                    },
                    'async_processor': {'max_queue_size': 100, 'rate_limit_per_second': 0.5, 'enable_retries': False},
                    'snapshot_buffer': {'max_size': 50, 'min_confidence_threshold': 0.7, 'debounce_frames': 3}
                },
                'expected_error_keywords': ['max_concurrent_requests', 'positive', 'performance']
            }
        ]
        
        for test_case in validation_test_cases:
            with pytest.raises(ConfigurationError) as exc_info:
                config_manager.validate_ollama_config(test_case['config'])
            
            error_message = str(exc_info.value).lower()
            for keyword in test_case['expected_error_keywords']:
                assert keyword.lower() in error_message, \
                    f"Error message should contain '{keyword}': {error_message}"
    
    def test_config_manager_provides_intelligent_defaults_for_different_use_cases(self):
        """Should provide intelligent default configurations for different use cases."""
        # RED PHASE: This test should fail because intelligent defaults don't exist yet
        config_manager = ConfigManager()
        
        # Should provide different default configurations for different scenarios
        development_config = config_manager.get_ollama_defaults_for_use_case('development')
        production_config = config_manager.get_ollama_defaults_for_use_case('production')
        testing_config = config_manager.get_ollama_defaults_for_use_case('testing')
        
        # Development defaults should prioritize quick iteration
        assert development_config['client']['timeout_seconds'] <= 30, "Dev should have shorter timeout"
        assert development_config['description_service']['cache_ttl_seconds'] <= 300, "Dev should have shorter cache"
        assert development_config['description_service']['enable_fallback_descriptions'] is True, "Dev should enable fallbacks"
        
        # Production defaults should prioritize reliability and performance
        assert production_config['client']['max_retries'] >= 2, "Production should have more retries"
        assert production_config['description_service']['cache_ttl_seconds'] >= 600, "Production should have longer cache"
        assert production_config['async_processor']['max_queue_size'] >= 100, "Production should have larger queue"
        
        # Testing defaults should prioritize speed and consistency
        assert testing_config['description_service']['enable_caching'] is False, "Testing should disable caching"
        assert testing_config['client']['timeout_seconds'] <= 10, "Testing should have very short timeout"
        assert testing_config['snapshot_buffer']['max_size'] <= 10, "Testing should have small buffer"
    
    def test_config_manager_validates_model_compatibility_and_performance_warnings(self):
        """Should validate model compatibility and provide performance warnings."""
        # RED PHASE: This test should fail because model validation doesn't exist yet
        config_manager = ConfigManager()
        
        # Test model validation with performance recommendations
        model_test_cases = [
            {
                'model': 'gemma3:1b',
                'expected_warnings': ['performance', 'accuracy', 'lightweight'],
                'should_validate': True
            },
            {
                'model': 'gemma3:4b-it-q4_K_M',
                'expected_warnings': [],  # Recommended model, no warnings
                'should_validate': True
            },
            {
                'model': 'gemma3:27b-it-q8_0',
                'expected_warnings': ['memory', 'performance', 'resource'],
                'should_validate': True
            },
            {
                'model': 'invalid-model-name',
                'expected_warnings': ['unknown', 'model', 'available'],
                'should_validate': True  # Should validate but warn
            },
            {
                'model': '',  # Empty model
                'expected_warnings': [],
                'should_validate': False  # Should fail validation
            }
        ]
        
        for test_case in model_test_cases:
            config = {
                'client': {
                    'base_url': 'http://localhost:11434',
                    'model': test_case['model'],
                    'timeout_seconds': 30.0,
                    'max_retries': 2
                },
                'description_service': {'cache_ttl_seconds': 300, 'max_concurrent_requests': 3, 'enable_caching': True, 'enable_fallback_descriptions': True},
                'async_processor': {'max_queue_size': 100, 'rate_limit_per_second': 0.5, 'enable_retries': False},
                'snapshot_buffer': {'max_size': 50, 'min_confidence_threshold': 0.7, 'debounce_frames': 3}
            }
            
            if test_case['should_validate']:
                # Should validate but may have warnings
                warnings = config_manager.validate_ollama_config_with_warnings(config)
                
                # Check expected warnings
                warning_text = ' '.join(warnings).lower()
                for expected_warning in test_case['expected_warnings']:
                    assert expected_warning.lower() in warning_text, \
                        f"Should warn about '{expected_warning}' for model '{test_case['model']}'"
            else:
                # Should fail validation
                with pytest.raises(ConfigurationError):
                    config_manager.validate_ollama_config(config)
    
    def test_config_manager_handles_configuration_migration_and_upgrades(self):
        """Should handle configuration migration and version upgrades."""
        # RED PHASE: This test should fail because configuration migration doesn't exist yet
        config_manager = ConfigManager()
        
        # Test legacy configuration format migration
        legacy_config_v1 = {
            'ollama_url': 'http://localhost:11434',  # Old format
            'model_name': 'gemma3:4b',  # Old format
            'timeout': 30,  # Old format
            'cache_ttl': 300  # Old format
        }
        
        # Should migrate legacy config to current format
        migrated_config = config_manager.migrate_ollama_config(legacy_config_v1, from_version='1.0', to_version='2.0')
        
        # Migrated config should have current structure
        assert 'client' in migrated_config
        assert 'description_service' in migrated_config
        assert migrated_config['client']['base_url'] == legacy_config_v1['ollama_url']
        assert migrated_config['client']['model'] == legacy_config_v1['model_name']
        assert migrated_config['client']['timeout_seconds'] == legacy_config_v1['timeout']
        assert migrated_config['description_service']['cache_ttl_seconds'] == legacy_config_v1['cache_ttl']
        
        # Should validate migrated config
        result = config_manager.validate_ollama_config(migrated_config)
        assert result is True
    
    def test_config_manager_provides_configuration_health_check(self):
        """Should provide configuration health check with actionable recommendations."""
        # RED PHASE: This test should fail because health check doesn't exist yet
        config_manager = ConfigManager()
        
        # Test configuration health check
        test_config = {
            'client': {
                'base_url': 'http://localhost:11434',
                'model': 'gemma3:4b-it-q4_K_M',
                'timeout_seconds': 5.0,  # Very short timeout
                'max_retries': 0  # No retries
            },
            'description_service': {
                'cache_ttl_seconds': 60,  # Very short cache
                'max_concurrent_requests': 1,  # Very limited concurrency
                'enable_caching': False,  # Caching disabled
                'enable_fallback_descriptions': False  # Fallbacks disabled
            },
            'async_processor': {
                'max_queue_size': 5,  # Very small queue
                'rate_limit_per_second': 0.1,  # Very slow rate limit
                'enable_retries': False
            },
            'snapshot_buffer': {
                'max_size': 3,  # Very small buffer
                'min_confidence_threshold': 0.95,  # Very high threshold
                'debounce_frames': 1
            }
        }
        
        # Should provide health check with recommendations
        health_report = config_manager.check_ollama_config_health(test_config)
        
        assert 'overall_health' in health_report
        assert 'recommendations' in health_report
        assert 'warnings' in health_report
        assert 'performance_score' in health_report
        
        # Should identify performance issues
        assert health_report['overall_health'] in ['poor', 'fair', 'good', 'excellent']
        assert len(health_report['recommendations']) > 0, "Should provide recommendations for improvement"
        
        # Should suggest specific improvements
        recommendations_text = ' '.join(health_report['recommendations']).lower()
        expected_recommendations = ['timeout', 'cache', 'concurrency', 'queue', 'rate_limit']
        for recommendation in expected_recommendations:
            assert any(rec in recommendations_text for rec in [recommendation, recommendation.replace('_', ' ')]), \
                f"Should recommend improvements for {recommendation}"


class TestOllamaRuntimeConfigurationUpdates:
    """Test Phase 6.1.3: Runtime Configuration Updates (RED PHASE)"""
    
    def test_config_manager_supports_runtime_configuration_reload(self):
        """Should support reloading configuration at runtime without restart."""
        # RED PHASE: This test should fail because runtime reload doesn't exist yet
        config_manager = ConfigManager()
        
        # Get initial configuration
        initial_config = config_manager.load_ollama_config()
        initial_timeout = initial_config['client']['timeout_seconds']
        
        # Modify configuration file
        updated_config = initial_config.copy()
        updated_config['client']['timeout_seconds'] = initial_timeout + 10.0
        
        # Simulate config file update (would be done externally)
        config_manager._simulate_config_file_update(updated_config)
        
        # Reload configuration
        config_manager.reload_ollama_config()
        
        # Configuration should be updated
        reloaded_config = config_manager.load_ollama_config()
        assert reloaded_config['client']['timeout_seconds'] == initial_timeout + 10.0, \
            f"Expected timeout {initial_timeout + 10.0}, got {reloaded_config['client']['timeout_seconds']}"
        
        # The reloaded config should have the new timeout value
        assert reloaded_config['client']['timeout_seconds'] != initial_timeout, \
            "Configuration should be updated after reload"
    
    def test_config_manager_validates_configuration_before_runtime_update(self):
        """Should validate configuration before applying runtime updates."""
        # RED PHASE: This test should fail because validation before update doesn't exist yet
        config_manager = ConfigManager()
        
        # Test invalid configuration update
        invalid_config_updates = [
            {'client': {'timeout_seconds': -1}},  # Invalid timeout
            {'description_service': {'max_concurrent_requests': 0}},  # Invalid concurrency
            {'snapshot_buffer': {'min_confidence_threshold': 1.5}},  # Invalid confidence
        ]
        
        for invalid_update in invalid_config_updates:
            # Should fail validation before applying update
            with pytest.raises(ConfigurationError):
                config_manager.update_ollama_config_runtime(invalid_update)
            
            # Original config should remain unchanged
            current_config = config_manager.load_ollama_config()
            assert config_manager.validate_ollama_config(current_config) is True
    
    def test_config_manager_supports_partial_configuration_updates(self):
        """Should support partial configuration updates without affecting other sections."""
        # RED PHASE: This test should fail because partial updates don't exist yet
        config_manager = ConfigManager()
        
        # Get initial configuration
        initial_config = config_manager.load_ollama_config()
        
        # Partial update: only modify client timeout
        partial_update = {
            'client': {
                'timeout_seconds': 60.0
            }
        }
        
        # Apply partial update
        config_manager.apply_partial_ollama_config_update(partial_update)
        
        # Updated config should have new timeout but preserve other values
        updated_config = config_manager.load_ollama_config()
        assert updated_config['client']['timeout_seconds'] == 60.0
        assert updated_config['client']['base_url'] == initial_config['client']['base_url']
        assert updated_config['client']['model'] == initial_config['client']['model']
        assert updated_config['description_service'] == initial_config['description_service']
        assert updated_config['async_processor'] == initial_config['async_processor']
        assert updated_config['snapshot_buffer'] == initial_config['snapshot_buffer']
    
    def test_config_manager_provides_configuration_change_notifications(self):
        """Should provide notifications when configuration changes."""
        # RED PHASE: This test should fail because change notifications don't exist yet
        config_manager = ConfigManager()
        
        # Setup change listener
        changes_received = []
        
        def config_change_listener(change_event):
            changes_received.append(change_event)
        
        # Register listener
        config_manager.register_ollama_config_change_listener(config_change_listener)
        
        # Make configuration changes
        config_manager.apply_partial_ollama_config_update({
            'client': {'timeout_seconds': 45.0}
        })
        
        config_manager.apply_partial_ollama_config_update({
            'description_service': {'cache_ttl_seconds': 600}
        })
        
        # Should receive change notifications
        assert len(changes_received) == 2, "Should receive notification for each config change"
        
        # Check change event structure
        first_change = changes_received[0]
        assert 'timestamp' in first_change
        assert 'section' in first_change
        assert 'field' in first_change
        assert 'old_value' in first_change
        assert 'new_value' in first_change
        
        assert first_change['section'] == 'client'
        assert first_change['field'] == 'timeout_seconds'
        assert first_change['new_value'] == 45.0
        
        second_change = changes_received[1]
        assert second_change['section'] == 'description_service'
        assert second_change['field'] == 'cache_ttl_seconds'
        assert second_change['new_value'] == 600
    
    def test_config_manager_supports_configuration_rollback(self):
        """Should support rolling back configuration changes."""
        # RED PHASE: This test should fail because configuration rollback doesn't exist yet
        config_manager = ConfigManager()
        
        # Get initial configuration
        initial_config = config_manager.load_ollama_config()
        
        # Create checkpoint
        checkpoint_id = config_manager.create_ollama_config_checkpoint()
        assert checkpoint_id is not None, "Should create checkpoint and return ID"
        
        # Make multiple configuration changes
        config_manager.apply_partial_ollama_config_update({
            'client': {'timeout_seconds': 90.0, 'max_retries': 5}
        })
        
        config_manager.apply_partial_ollama_config_update({
            'description_service': {'cache_ttl_seconds': 900, 'max_concurrent_requests': 10}
        })
        
        # Verify changes were applied
        modified_config = config_manager.load_ollama_config()
        assert modified_config['client']['timeout_seconds'] == 90.0
        assert modified_config['client']['max_retries'] == 5
        assert modified_config['description_service']['cache_ttl_seconds'] == 900
        
        # Rollback to checkpoint
        config_manager.rollback_ollama_config_to_checkpoint(checkpoint_id)
        
        # Configuration should be restored to checkpoint state
        restored_config = config_manager.load_ollama_config()
        assert restored_config == initial_config, "Configuration should be restored to checkpoint state"
    
    def test_config_manager_handles_concurrent_configuration_updates(self):
        """Should handle concurrent configuration updates safely."""
        # RED PHASE: This test should fail because concurrent update handling doesn't exist yet
        config_manager = ConfigManager()
        
        import threading
        import time
        
        # Simulate concurrent updates
        update_results = []
        errors = []
        
        def concurrent_update_worker(update_data, worker_id):
            try:
                config_manager.apply_partial_ollama_config_update(update_data)
                update_results.append(f"Worker {worker_id} succeeded")
            except Exception as e:
                errors.append(f"Worker {worker_id} failed: {e}")
        
        # Create multiple threads trying to update config concurrently
        threads = []
        for i in range(5):
            update_data = {
                'client': {'timeout_seconds': 30.0 + i}
            }
            thread = threading.Thread(
                target=concurrent_update_worker, 
                args=(update_data, i)
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should handle concurrent updates without corruption
        assert len(errors) == 0, f"Should handle concurrent updates without errors: {errors}"
        assert len(update_results) == 5, "All concurrent updates should succeed"
        
        # Final configuration should be valid
        final_config = config_manager.load_ollama_config()
        assert config_manager.validate_ollama_config(final_config) is True 