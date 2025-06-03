"""
Configuration management for webcam human detection project.

This module provides configuration loading, validation, and management
functionality following the TDD approach.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv


# Set up logger
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.original_error:
            return f"{self.message} (Original error: {self.original_error})"
        return self.message


class ConfigManager:
    """Manages application configuration loading and validation."""
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize ConfigManager with config directory path.
        
        Args:
            config_dir: Directory path for configuration files
        """
        self.config_dir = Path(config_dir)
        
        # Load environment variables
        load_dotenv()
        
        # Ensure config directory exists
        self._ensure_config_directory()
        
        # Create default config files if they don't exist
        self._create_default_configs()
        
        # Initialize runtime configuration management
        self._runtime_config_cache = {}
        self._config_change_listeners = []
        self._config_checkpoints = {}
        self._checkpoint_counter = 0
        self._config_lock = None
        
        logger.info(f"ConfigManager initialized with config directory: {self.config_dir}")
    
    def load_camera_profile(self, profile_name: str) -> Dict[str, Any]:
        """
        Load camera profile configuration from YAML file.
        
        Args:
            profile_name: Name of the camera profile to load
            
        Returns:
            Dictionary containing camera configuration parameters
            
        Raises:
            ConfigurationError: If profile file not found, profile doesn't exist,
                               or configuration is invalid
        """
        profile_file = self.config_dir / "camera_profiles.yaml"
        
        if not profile_file.exists():
            raise ConfigurationError(f"Camera profiles file not found: {profile_file}")
        
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profiles = yaml.safe_load(f)
            
            if not profiles:
                raise ConfigurationError("Camera profiles file is empty or invalid")
            
            if profile_name not in profiles:
                available_profiles = list(profiles.keys())
                raise ConfigurationError(
                    f"Profile '{profile_name}' not found. Available profiles: {available_profiles}"
                )
            
            config = profiles[profile_name].copy()
            
            # Apply environment variable overrides
            config = self._apply_camera_env_overrides(config)
            
            # Validate the configuration
            self.validate_camera_config(config)
            
            logger.debug(f"Loaded camera profile '{profile_name}': {config}")
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing YAML file {profile_file}", e)
        except ConfigurationError:
            raise  # Re-raise ConfigurationError as-is
        except Exception as e:
            raise ConfigurationError(f"Unexpected error loading camera profile '{profile_name}'", e)
    
    def load_detection_config(self) -> Dict[str, Any]:
        """
        Load detection configuration parameters.
        
        Returns:
            Dictionary containing detection configuration parameters
            
        Raises:
            ConfigurationError: If config file not found or configuration is invalid
        """
        config_file = self.config_dir / "detection_config.yaml"
        
        if not config_file.exists():
            raise ConfigurationError(f"Detection config file not found: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ConfigurationError("Detection config file is empty or invalid")
            
            # Apply environment variable overrides
            config = self._apply_detection_env_overrides(config)
            
            # Validate detection configuration
            self._validate_detection_config(config)
            
            logger.debug(f"Loaded detection config: {config}")
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing detection config", e)
        except ConfigurationError:
            raise  # Re-raise ConfigurationError as-is
        except Exception as e:
            raise ConfigurationError(f"Unexpected error loading detection config", e)
    
    def validate_camera_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate camera configuration parameters.
        
        Args:
            config: Camera configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        required_fields = ['device_id', 'width', 'height']
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ConfigurationError(f"Missing required camera fields: {missing_fields}")
        
        # Validate device_id
        device_id = config['device_id']
        if not isinstance(device_id, int) or device_id < 0:
            raise ConfigurationError(f"Device ID must be a non-negative integer, got: {device_id}")
        
        # Validate width and height
        width, height = config['width'], config['height']
        if not isinstance(width, int) or width <= 0:
            raise ConfigurationError(f"Width must be a positive integer, got: {width}")
        
        if not isinstance(height, int) or height <= 0:
            raise ConfigurationError(f"Height must be a positive integer, got: {height}")
        
        # Validate fps if present
        if 'fps' in config:
            fps = config['fps']
            if not isinstance(fps, (int, float)) or fps <= 0:
                raise ConfigurationError(f"FPS must be a positive number, got: {fps}")
        
        # Validate buffer_size if present
        if 'buffer_size' in config:
            buffer_size = config['buffer_size']
            if not isinstance(buffer_size, int) or buffer_size <= 0:
                raise ConfigurationError(f"Buffer size must be a positive integer, got: {buffer_size}")
        
        return True
    
    def list_camera_profiles(self) -> List[str]:
        """
        List available camera profiles.
        
        Returns:
            List of available camera profile names
        """
        profile_file = self.config_dir / "camera_profiles.yaml"
        
        if not profile_file.exists():
            return []
        
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profiles = yaml.safe_load(f)
            
            return list(profiles.keys()) if profiles else []
            
        except Exception:
            logger.warning("Failed to load camera profiles for listing")
            return []
    
    def get_config_directory(self) -> Path:
        """Get the configuration directory path."""
        return self.config_dir
    
    def _validate_detection_config(self, config: Dict[str, Any]) -> bool:
        """Validate detection configuration parameters."""
        required_fields = ['model_complexity', 'min_detection_confidence', 'min_tracking_confidence']
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ConfigurationError(f"Missing required detection fields: {missing_fields}")
        
        # Validate model complexity
        model_complexity = config['model_complexity']
        if model_complexity not in [0, 1, 2]:
            raise ConfigurationError(f"Model complexity must be 0, 1, or 2, got: {model_complexity}")
        
        # Validate confidence values
        detection_conf = config['min_detection_confidence']
        if not isinstance(detection_conf, (int, float)) or not 0.0 <= detection_conf <= 1.0:
            raise ConfigurationError(f"Detection confidence must be between 0.0 and 1.0, got: {detection_conf}")
        
        tracking_conf = config['min_tracking_confidence']
        if not isinstance(tracking_conf, (int, float)) or not 0.0 <= tracking_conf <= 1.0:
            raise ConfigurationError(f"Tracking confidence must be between 0.0 and 1.0, got: {tracking_conf}")
        
        return True
    
    def _apply_camera_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to camera configuration."""
        env_mappings = {
            'CAMERA_DEVICE_ID': ('device_id', int),
            'CAMERA_WIDTH': ('width', int),
            'CAMERA_HEIGHT': ('height', int),
            'CAMERA_FPS': ('fps', int),
            'CAMERA_BUFFER_SIZE': ('buffer_size', int),
        }
        
        return self._apply_env_overrides(config, env_mappings)
    
    def _apply_detection_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to detection configuration."""
        env_mappings = {
            'DETECTION_MODEL_COMPLEXITY': ('model_complexity', int),
            'DETECTION_MIN_CONFIDENCE': ('min_detection_confidence', float),
            'DETECTION_MIN_TRACKING': ('min_tracking_confidence', float),
            'DETECTION_SMOOTHING_WINDOW': ('smoothing_window', int),
            'DETECTION_DEBOUNCE_FRAMES': ('debounce_frames', int),
        }
        
        return self._apply_env_overrides(config, env_mappings)
    
    def _apply_env_overrides(self, config: Dict[str, Any], env_mappings: Dict[str, tuple]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        for env_var, (config_key, type_func) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    config[config_key] = type_func(env_value)
                    logger.debug(f"Applied environment override: {env_var}={env_value}")
                except ValueError as e:
                    raise ConfigurationError(f"Invalid environment variable {env_var}={env_value}", e)
        
        return config
    
    def _ensure_config_directory(self):
        """Ensure the configuration directory exists."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigurationError(f"Failed to create config directory {self.config_dir}", e)
    
    def _create_default_configs(self):
        """Create default configuration files if they don't exist."""
        try:
            self._create_camera_profiles_config()
            self._create_detection_config()
        except Exception as e:
            logger.warning(f"Failed to create default configs: {e}")
    
    def _create_camera_profiles_config(self):
        """Create default camera profiles configuration."""
        camera_profiles_file = self.config_dir / "camera_profiles.yaml"
        if camera_profiles_file.exists():
            return
        
        default_camera_profiles = {
            'default': {
                'device_id': 0,
                'width': 640,
                'height': 480,
                'fps': 30,
                'buffer_size': 10
            },
            'high_quality': {
                'device_id': 0,
                'width': 1280,
                'height': 720,
                'fps': 30,
                'buffer_size': 5
            },
            'low_latency': {
                'device_id': 0,
                'width': 320,
                'height': 240,
                'fps': 60,
                'buffer_size': 3
            }
        }
        
        with open(camera_profiles_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_camera_profiles, f, default_flow_style=False, indent=2)
        
        logger.info(f"Created default camera profiles: {camera_profiles_file}")
    
    def _create_detection_config(self):
        """Create default detection configuration."""
        detection_config_file = self.config_dir / "detection_config.yaml"
        if detection_config_file.exists():
            return
        
        default_detection_config = {
            'model_complexity': 1,
            'min_detection_confidence': 0.5,
            'min_tracking_confidence': 0.5,
            'smoothing_window': 5,
            'debounce_frames': 3,
            'enable_segmentation': False
        }
        
        with open(detection_config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_detection_config, f, default_flow_style=False, indent=2)
        
        logger.info(f"Created default detection config: {detection_config_file}")
    
    def load_ollama_config(self) -> Dict[str, Any]:
        """
        Load Ollama configuration parameters (with runtime cache support).
        
        Returns:
            Dictionary containing Ollama configuration parameters
            
        Raises:
            ConfigurationError: If config file not found or configuration is invalid
        """
        # Check runtime cache first
        if 'ollama_config' in self._runtime_config_cache:
            return self._runtime_config_cache['ollama_config'].copy()
        
        config_file = self.config_dir / "ollama_config.yaml"
        
        if not config_file.exists():
            # Create default config if it doesn't exist
            self._create_default_ollama_config()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ConfigurationError("Ollama config file is empty or invalid")
            
            # Apply environment variable overrides
            config = self._apply_ollama_env_overrides(config)
            
            # Validate Ollama configuration
            self.validate_ollama_config(config)
            
            # Cache the config for runtime updates
            self._runtime_config_cache['ollama_config'] = config.copy()
            
            logger.debug(f"Loaded Ollama config: {config}")
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing Ollama config", e)
        except ConfigurationError:
            raise  # Re-raise ConfigurationError as-is
        except Exception as e:
            raise ConfigurationError(f"Unexpected error loading Ollama config", e)
    
    def validate_ollama_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate Ollama configuration parameters.
        
        Args:
            config: Ollama configuration dictionary
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        required_sections = ['client', 'description_service', 'async_processor', 'snapshot_buffer']
        
        # Check required sections
        missing_sections = [section for section in required_sections if section not in config]
        if missing_sections:
            raise ConfigurationError(f"Missing required Ollama sections: {missing_sections}")
        
        # Validate client configuration
        client_config = config['client']
        required_client_fields = ['base_url', 'model', 'timeout_seconds', 'max_retries']
        missing_client_fields = [field for field in required_client_fields if field not in client_config]
        if missing_client_fields:
            raise ConfigurationError(f"Missing required client fields: {missing_client_fields}")
        
        # Validate base_url format
        base_url = client_config['base_url']
        if not isinstance(base_url, str) or not (base_url.startswith('http://') or base_url.startswith('https://')):
            raise ConfigurationError(f"Invalid base_url format: {base_url}. Must start with http:// or https://")
        
        # Validate model name
        model = client_config['model']
        if not isinstance(model, str) or not model.strip():
            raise ConfigurationError("Model name cannot be empty. Please specify a valid Ollama model name.")
        
        # Validate timeout
        timeout = client_config['timeout_seconds']
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ConfigurationError(f"timeout_seconds must be positive, got: {timeout}")
        
        # Validate max_retries
        max_retries = client_config['max_retries']
        if not isinstance(max_retries, int) or max_retries < 0:
            raise ConfigurationError(f"max_retries must be non-negative integer, got: {max_retries}")
        
        # Validate description service configuration
        desc_config = config['description_service']
        required_desc_fields = ['cache_ttl_seconds', 'max_concurrent_requests', 'enable_caching', 'enable_fallback_descriptions']
        missing_desc_fields = [field for field in required_desc_fields if field not in desc_config]
        if missing_desc_fields:
            raise ConfigurationError(f"Missing required description service fields: {missing_desc_fields}")
        
        # Validate cache TTL
        cache_ttl = desc_config['cache_ttl_seconds']
        if not isinstance(cache_ttl, (int, float)) or cache_ttl <= 0:
            raise ConfigurationError(f"cache_ttl_seconds must be positive, got: {cache_ttl}")
        
        # Validate max_concurrent_requests
        max_concurrent = desc_config['max_concurrent_requests']
        if not isinstance(max_concurrent, int) or max_concurrent <= 0:
            raise ConfigurationError(f"max_concurrent_requests must be positive integer for performance, got: {max_concurrent}")
        
        # Validate async processor configuration
        async_config = config['async_processor']
        required_async_fields = ['max_queue_size', 'rate_limit_per_second', 'enable_retries']
        missing_async_fields = [field for field in required_async_fields if field not in async_config]
        if missing_async_fields:
            raise ConfigurationError(f"Missing required async processor fields: {missing_async_fields}")
        
        # Validate snapshot buffer configuration
        buffer_config = config['snapshot_buffer']
        required_buffer_fields = ['max_size', 'min_confidence_threshold', 'debounce_frames']
        missing_buffer_fields = [field for field in required_buffer_fields if field not in buffer_config]
        if missing_buffer_fields:
            raise ConfigurationError(f"Missing required snapshot buffer fields: {missing_buffer_fields}")
        
        # Validate confidence threshold
        confidence = buffer_config['min_confidence_threshold']
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            raise ConfigurationError(f"min_confidence_threshold must be between 0.0 and 1.0, got: {confidence}")
        
        return True
    
    def list_available_ollama_models(self) -> List[str]:
        """
        List available Ollama models.
        
        Returns:
            List of available model names
        """
        # Default list of commonly available models
        default_models = [
            'gemma3:4b-it-q4_K_M',
            'gemma3:12b-it-q4_K_M', 
            'llama3.2-vision'
        ]
        
        try:
            # In a real implementation, this would query the Ollama service
            # For now, return the default list
            return default_models
        except Exception:
            logger.warning("Failed to query Ollama service for available models")
            return default_models
    
    def _create_default_ollama_config(self) -> None:
        """Create default ollama_config.yaml file."""
        default_config = {
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
        
        config_file = self.config_dir / "ollama_config.yaml"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Created default Ollama config: {config_file}")
            
        except Exception as e:
            logger.warning(f"Failed to create default Ollama config: {e}")
    
    def _apply_ollama_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to Ollama configuration."""
        env_mappings = {
            'OLLAMA_BASE_URL': ('client', 'base_url', str),
            'OLLAMA_MODEL': ('client', 'model', str),
            'OLLAMA_TIMEOUT': ('client', 'timeout_seconds', float),
            'OLLAMA_MAX_RETRIES': ('client', 'max_retries', int),
            'OLLAMA_CACHE_TTL': ('description_service', 'cache_ttl_seconds', int),
            'OLLAMA_MAX_CONCURRENT': ('description_service', 'max_concurrent_requests', int),
            'OLLAMA_ENABLE_CACHING': ('description_service', 'enable_caching', lambda x: x.lower() == 'true'),
            'OLLAMA_QUEUE_SIZE': ('async_processor', 'max_queue_size', int),
            'OLLAMA_RATE_LIMIT': ('async_processor', 'rate_limit_per_second', float),
            'OLLAMA_BUFFER_SIZE': ('snapshot_buffer', 'max_size', int),
            'OLLAMA_MIN_CONFIDENCE': ('snapshot_buffer', 'min_confidence_threshold', float),
        }
        
        for env_var, (section, key, type_func) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Ensure section exists
                    if section not in config:
                        config[section] = {}
                    
                    # Convert and set value
                    config[section][key] = type_func(env_value)
                    logger.debug(f"Ollama override from env: {env_var} = {env_value}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment variable {env_var}={env_value}: {e}")
        
        return config
    
    def validate_ollama_config_with_warnings(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate Ollama configuration and return warnings.
        
        Args:
            config: Ollama configuration dictionary
            
        Returns:
            List of warning messages
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        # First validate normally
        self.validate_ollama_config(config)
        
        warnings = []
        
        # Check model and provide warnings
        model = config.get('client', {}).get('model', '')
        if model:
            if 'gemma3:1b' in model:
                warnings.extend(['performance may be limited with lightweight model', 
                               'accuracy may be reduced', 
                               'suitable for lightweight applications'])
            elif 'gemma3:27b' in model or 'q8_0' in model:
                warnings.extend(['high memory usage expected', 
                               'performance may be slow on limited hardware',
                               'resource intensive model'])
            elif model and not any(known in model for known in ['gemma3', 'llama3.2']):
                warnings.extend(['unknown model detected', 
                               'model compatibility not verified',
                               'check available models'])
        
        # Check performance settings
        timeout = config.get('client', {}).get('timeout_seconds', 30)
        if timeout < 10:
            warnings.append('very short timeout may cause failures')
        
        cache_ttl = config.get('description_service', {}).get('cache_ttl_seconds', 300)
        if cache_ttl < 60:
            warnings.append('very short cache TTL may impact performance')
        
        return warnings
    
    def get_ollama_defaults_for_use_case(self, use_case: str) -> Dict[str, Any]:
        """
        Get intelligent default Ollama configuration for specific use cases.
        
        Args:
            use_case: Use case type ('development', 'production', 'testing')
            
        Returns:
            Dictionary with optimized configuration for the use case
        """
        base_config = {
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
        
        if use_case == 'development':
            # Optimize for quick iteration and debugging
            base_config['client']['timeout_seconds'] = 20.0
            base_config['description_service']['cache_ttl_seconds'] = 180
            base_config['description_service']['enable_fallback_descriptions'] = True
            base_config['async_processor']['rate_limit_per_second'] = 1.0
            
        elif use_case == 'production':
            # Optimize for reliability and performance
            base_config['client']['max_retries'] = 3
            base_config['client']['timeout_seconds'] = 45.0
            base_config['description_service']['cache_ttl_seconds'] = 600
            base_config['description_service']['max_concurrent_requests'] = 5
            base_config['async_processor']['max_queue_size'] = 200
            base_config['async_processor']['rate_limit_per_second'] = 0.3
            
        elif use_case == 'testing':
            # Optimize for speed and consistency
            base_config['client']['timeout_seconds'] = 5.0
            base_config['description_service']['enable_caching'] = False
            base_config['description_service']['cache_ttl_seconds'] = 30
            base_config['snapshot_buffer']['max_size'] = 5
            base_config['async_processor']['max_queue_size'] = 10
        
        return base_config
    
    def migrate_ollama_config(self, legacy_config: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Migrate legacy Ollama configuration to current format.
        
        Args:
            legacy_config: Legacy configuration dictionary
            from_version: Source version string
            to_version: Target version string
            
        Returns:
            Migrated configuration in current format
        """
        if from_version == '1.0' and to_version == '2.0':
            # Migrate from v1.0 flat format to v2.0 structured format
            migrated = {
                'client': {
                    'base_url': legacy_config.get('ollama_url', 'http://localhost:11434'),
                    'model': legacy_config.get('model_name', 'gemma3:4b-it-q4_K_M'),
                    'timeout_seconds': legacy_config.get('timeout', 30.0),
                    'max_retries': legacy_config.get('max_retries', 2)
                },
                'description_service': {
                    'cache_ttl_seconds': legacy_config.get('cache_ttl', 300),
                    'max_concurrent_requests': legacy_config.get('max_concurrent', 3),
                    'enable_caching': legacy_config.get('enable_cache', True),
                    'enable_fallback_descriptions': legacy_config.get('enable_fallback', True)
                },
                'async_processor': {
                    'max_queue_size': legacy_config.get('queue_size', 100),
                    'rate_limit_per_second': legacy_config.get('rate_limit', 0.5),
                    'enable_retries': legacy_config.get('async_retries', False)
                },
                'snapshot_buffer': {
                    'max_size': legacy_config.get('buffer_size', 50),
                    'min_confidence_threshold': legacy_config.get('confidence_threshold', 0.7),
                    'debounce_frames': legacy_config.get('debounce', 3)
                }
            }
            return migrated
        
        # For other version combinations, return as-is
        return legacy_config
    
    def check_ollama_config_health(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform health check on Ollama configuration with recommendations.
        
        Args:
            config: Ollama configuration to analyze
            
        Returns:
            Health report with recommendations and warnings
        """
        health_report = {
            'overall_health': 'good',
            'recommendations': [],
            'warnings': [],
            'performance_score': 85
        }
        
        issues = []
        score = 100
        
        # Check client configuration
        client_config = config.get('client', {})
        timeout = client_config.get('timeout_seconds', 30)
        if timeout < 10:
            issues.append('Very short timeout may cause frequent failures')
            health_report['recommendations'].append('Consider increasing timeout to at least 15 seconds')
            score -= 15
        
        max_retries = client_config.get('max_retries', 2)
        if max_retries < 1:
            issues.append('No retries configured - may reduce reliability')
            health_report['recommendations'].append('Enable at least 1-2 retries for better reliability')
            score -= 10
        
        # Check description service configuration
        desc_config = config.get('description_service', {})
        cache_ttl = desc_config.get('cache_ttl_seconds', 300)
        if cache_ttl < 120:
            issues.append('Very short cache TTL may impact performance')
            health_report['recommendations'].append('Consider increasing cache TTL to at least 300 seconds')
            score -= 10
        
        max_concurrent = desc_config.get('max_concurrent_requests', 3)
        if max_concurrent < 2:
            issues.append('Very limited concurrency may create bottlenecks')
            health_report['recommendations'].append('Consider increasing concurrency to 3-5 for better performance')
            score -= 10
        
        enable_caching = desc_config.get('enable_caching', True)
        if not enable_caching:
            issues.append('Caching disabled - may impact performance')
            health_report['recommendations'].append('Enable caching for better performance, disable only for testing')
            score -= 15
        
        # Check async processor configuration
        async_config = config.get('async_processor', {})
        queue_size = async_config.get('max_queue_size', 100)
        if queue_size < 20:
            issues.append('Very small queue size may cause request drops')
            health_report['recommendations'].append('Consider increasing queue size to at least 50-100')
            score -= 10
        
        rate_limit = async_config.get('rate_limit_per_second', 0.5)
        if rate_limit < 0.2:
            issues.append('Very low rate limit may cause slow processing')
            health_report['recommendations'].append('Consider increasing rate limit to 0.5-1.0 req/sec')
            score -= 10
        
        # Check snapshot buffer configuration
        buffer_config = config.get('snapshot_buffer', {})
        buffer_size = buffer_config.get('max_size', 50)
        if buffer_size < 10:
            issues.append('Very small snapshot buffer may lose frames')
            health_report['recommendations'].append('Consider increasing buffer size to at least 20-50')
            score -= 5
        
        confidence_threshold = buffer_config.get('min_confidence_threshold', 0.7)
        if confidence_threshold > 0.9:
            issues.append('Very high confidence threshold may miss detections')
            health_report['recommendations'].append('Consider lowering confidence threshold to 0.7-0.8')
            score -= 5
        
        # Determine overall health
        health_report['performance_score'] = max(0, score)
        health_report['warnings'] = issues
        
        if score >= 85:
            health_report['overall_health'] = 'excellent'
        elif score >= 70:
            health_report['overall_health'] = 'good'
        elif score >= 50:
            health_report['overall_health'] = 'fair'
        else:
            health_report['overall_health'] = 'poor'
        
        return health_report
    
    def _simulate_config_file_update(self, updated_config: Dict[str, Any]) -> None:
        """Simulate config file update for testing purposes."""
        config_file = self.config_dir / "ollama_config.yaml"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(updated_config, f, default_flow_style=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to simulate config file update: {e}")
    
    def reload_ollama_config(self) -> None:
        """Reload Ollama configuration from file."""
        # Clear cached config to force reload
        if 'ollama_config' in self._runtime_config_cache:
            del self._runtime_config_cache['ollama_config']
        
        # Load fresh config
        self.load_ollama_config()
        logger.info("Ollama configuration reloaded from file")
    
    def update_ollama_config_runtime(self, config_update: Dict[str, Any]) -> None:
        """
        Update Ollama configuration at runtime with validation.
        
        Args:
            config_update: Configuration updates to apply
            
        Raises:
            ConfigurationError: If configuration update is invalid
        """
        # Load current config
        current_config = self.load_ollama_config()
        
        # Apply updates to a copy
        updated_config = self._deep_merge_configs(current_config, config_update)
        
        # Validate the updated configuration
        self.validate_ollama_config(updated_config)
        
        # If validation passes, apply the update
        self._runtime_config_cache['ollama_config'] = updated_config
        
        # Notify listeners
        self._notify_config_change_listeners(config_update)
        
        logger.info(f"Runtime configuration update applied: {config_update}")
    
    def apply_partial_ollama_config_update(self, partial_update: Dict[str, Any]) -> None:
        """
        Apply partial configuration update preserving existing values.
        
        Args:
            partial_update: Partial configuration to update
        """
        self._ensure_thread_safety()
        
        try:
            if self._config_lock:
                self._config_lock.acquire()
            
            # Load current config
            current_config = self.load_ollama_config()
            
            # Apply partial update
            updated_config = self._deep_merge_configs(current_config, partial_update)
            
            # Validate updated config
            self.validate_ollama_config(updated_config)
            
            # Apply update
            self._runtime_config_cache['ollama_config'] = updated_config
            
            # Notify listeners with detailed change info
            self._notify_detailed_config_changes(current_config, partial_update)
            
            logger.info(f"Partial configuration update applied: {partial_update}")
            
        finally:
            if self._config_lock:
                self._config_lock.release()
    
    def register_ollama_config_change_listener(self, listener_func) -> None:
        """Register a listener function for configuration changes."""
        self._config_change_listeners.append(listener_func)
        logger.debug(f"Registered config change listener: {listener_func.__name__}")
    
    def create_ollama_config_checkpoint(self) -> str:
        """
        Create a configuration checkpoint for rollback.
        
        Returns:
            Checkpoint ID string
        """
        current_config = self.load_ollama_config()
        checkpoint_id = f"checkpoint_{self._checkpoint_counter}"
        self._config_checkpoints[checkpoint_id] = current_config.copy()
        self._checkpoint_counter += 1
        
        logger.info(f"Created configuration checkpoint: {checkpoint_id}")
        return checkpoint_id
    
    def rollback_ollama_config_to_checkpoint(self, checkpoint_id: str) -> None:
        """
        Rollback configuration to a specific checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to rollback to
            
        Raises:
            ConfigurationError: If checkpoint ID is invalid
        """
        if checkpoint_id not in self._config_checkpoints:
            raise ConfigurationError(f"Invalid checkpoint ID: {checkpoint_id}")
        
        checkpoint_config = self._config_checkpoints[checkpoint_id]
        
        # Validate checkpoint config (should always be valid)
        self.validate_ollama_config(checkpoint_config)
        
        # Apply checkpoint config
        self._runtime_config_cache['ollama_config'] = checkpoint_config.copy()
        
        # Notify listeners
        self._notify_config_change_listeners({'rollback': checkpoint_id})
        
        logger.info(f"Configuration rolled back to checkpoint: {checkpoint_id}")
    
    def _ensure_thread_safety(self) -> None:
        """Ensure thread safety for concurrent updates."""
        if self._config_lock is None:
            import threading
            self._config_lock = threading.Lock()
    
    def _deep_merge_configs(self, base_config: Dict[str, Any], update_config: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge configuration dictionaries."""
        result = base_config.copy()
        
        for key, value in update_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _notify_config_change_listeners(self, config_change: Dict[str, Any]) -> None:
        """Notify all registered listeners of configuration changes."""
        for listener in self._config_change_listeners:
            try:
                listener(config_change)
            except Exception as e:
                logger.warning(f"Config change listener failed: {e}")
    
    def _notify_detailed_config_changes(self, old_config: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Notify listeners with detailed change information."""
        from datetime import datetime
        
        for section, section_data in update.items():
            if isinstance(section_data, dict):
                for field, new_value in section_data.items():
                    old_value = old_config.get(section, {}).get(field)
                    
                    change_event = {
                        'timestamp': datetime.now().isoformat(),
                        'section': section,
                        'field': field,
                        'old_value': old_value,
                        'new_value': new_value
                    }
                    
                    for listener in self._config_change_listeners:
                        try:
                            listener(change_event)
                        except Exception as e:
                            logger.warning(f"Detailed config change listener failed: {e}") 