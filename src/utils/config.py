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
        Load Ollama configuration parameters.
        
        Returns:
            Dictionary containing Ollama configuration parameters
            
        Raises:
            ConfigurationError: If config file not found or configuration is invalid
        """
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
            raise ConfigurationError(f"Invalid base_url format: {base_url}")
        
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