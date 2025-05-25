"""
Configuration Management Sample Code

This file contains starter code and examples for configuration management
including YAML loading, environment variables, validation, and config classes.
"""

import yaml
import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging
from dotenv import load_dotenv


# Basic YAML configuration loading
def basic_yaml_loading():
    """Basic YAML configuration loading example."""
    
    # Sample YAML content
    sample_config = """
camera:
  device_id: 0
  width: 640
  height: 480
  fps: 30
  buffer_size: 10

detection:
  model_complexity: 1
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5
  smoothing_window: 5
  debounce_frames: 3

processing:
  max_queue_size: 10
  num_workers: 2
  enable_threading: true

logging:
  level: INFO
  file_path: logs/app.log
  max_file_size: 10MB
  backup_count: 5
"""
    
    # Save sample config
    with open('sample_config.yaml', 'w') as f:
        f.write(sample_config)
    
    # Load configuration
    try:
        with open('sample_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        print("Loaded configuration:")
        print(f"Camera device: {config['camera']['device_id']}")
        print(f"Resolution: {config['camera']['width']}x{config['camera']['height']}")
        print(f"Detection confidence: {config['detection']['min_detection_confidence']}")
        print(f"Processing workers: {config['processing']['num_workers']}")
        
        return config
        
    except FileNotFoundError:
        print("Configuration file not found!")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return None
    finally:
        # Cleanup
        if os.path.exists('sample_config.yaml'):
            os.remove('sample_config.yaml')


# Configuration dataclasses
@dataclass
class CameraConfig:
    """Camera configuration settings."""
    device_id: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    buffer_size: int = 10
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.device_id < 0:
            raise ValueError("Device ID must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Width and height must be positive")
        if self.fps <= 0:
            raise ValueError("FPS must be positive")
        if self.buffer_size <= 0:
            raise ValueError("Buffer size must be positive")


@dataclass
class DetectionConfig:
    """Detection configuration settings."""
    model_complexity: int = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    smoothing_window: int = 5
    debounce_frames: int = 3
    
    def __post_init__(self):
        """Validate detection configuration."""
        if self.model_complexity not in [0, 1, 2]:
            raise ValueError("Model complexity must be 0, 1, or 2")
        if not 0.0 <= self.min_detection_confidence <= 1.0:
            raise ValueError("Detection confidence must be between 0.0 and 1.0")
        if not 0.0 <= self.min_tracking_confidence <= 1.0:
            raise ValueError("Tracking confidence must be between 0.0 and 1.0")
        if self.smoothing_window <= 0:
            raise ValueError("Smoothing window must be positive")
        if self.debounce_frames < 0:
            raise ValueError("Debounce frames must be non-negative")


@dataclass
class ProcessingConfig:
    """Processing configuration settings."""
    max_queue_size: int = 10
    num_workers: int = 2
    enable_threading: bool = True
    timeout_seconds: float = 1.0
    
    def __post_init__(self):
        """Validate processing configuration."""
        if self.max_queue_size <= 0:
            raise ValueError("Queue size must be positive")
        if self.num_workers <= 0:
            raise ValueError("Number of workers must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    file_path: Optional[str] = None
    max_file_size: str = "10MB"
    backup_count: int = 5
    console_output: bool = True
    
    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        if self.backup_count < 0:
            raise ValueError("Backup count must be non-negative")


@dataclass
class AppConfig:
    """Main application configuration."""
    camera: CameraConfig = field(default_factory=CameraConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AppConfig':
        """Create AppConfig from dictionary."""
        return cls(
            camera=CameraConfig(**config_dict.get('camera', {})),
            detection=DetectionConfig(**config_dict.get('detection', {})),
            processing=ProcessingConfig(**config_dict.get('processing', {})),
            logging=LoggingConfig(**config_dict.get('logging', {}))
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AppConfig to dictionary."""
        return {
            'camera': {
                'device_id': self.camera.device_id,
                'width': self.camera.width,
                'height': self.camera.height,
                'fps': self.camera.fps,
                'buffer_size': self.camera.buffer_size
            },
            'detection': {
                'model_complexity': self.detection.model_complexity,
                'min_detection_confidence': self.detection.min_detection_confidence,
                'min_tracking_confidence': self.detection.min_tracking_confidence,
                'smoothing_window': self.detection.smoothing_window,
                'debounce_frames': self.detection.debounce_frames
            },
            'processing': {
                'max_queue_size': self.processing.max_queue_size,
                'num_workers': self.processing.num_workers,
                'enable_threading': self.processing.enable_threading,
                'timeout_seconds': self.processing.timeout_seconds
            },
            'logging': {
                'level': self.logging.level,
                'file_path': self.logging.file_path,
                'max_file_size': self.logging.max_file_size,
                'backup_count': self.logging.backup_count,
                'console_output': self.logging.console_output
            }
        }


# Configuration Manager class
class ConfigurationManager:
    """Manages application configuration loading and validation."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_cache = {}
        
        # Load environment variables
        load_dotenv()
    
    def load_config(self, config_name: str = "default") -> AppConfig:
        """Load configuration from YAML file."""
        config_file = self.config_dir / f"{config_name}.yaml"
        
        if config_name in self.config_cache:
            return self.config_cache[config_name]
        
        try:
            with open(config_file, 'r') as f:
                config_dict = yaml.safe_load(f)
            
            # Apply environment variable overrides
            config_dict = self._apply_env_overrides(config_dict)
            
            # Create and validate config
            config = AppConfig.from_dict(config_dict)
            
            # Cache the config
            self.config_cache[config_name] = config
            
            return config
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML configuration: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def save_config(self, config: AppConfig, config_name: str = "default"):
        """Save configuration to YAML file."""
        config_file = self.config_dir / f"{config_name}.yaml"
        
        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config.to_dict(), f, default_flow_style=False, indent=2)
            
            print(f"Configuration saved to {config_file}")
            
        except Exception as e:
            raise ValueError(f"Error saving configuration: {e}")
    
    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        
        # Environment variable mappings
        env_mappings = {
            'CAMERA_DEVICE_ID': ('camera', 'device_id', int),
            'CAMERA_WIDTH': ('camera', 'width', int),
            'CAMERA_HEIGHT': ('camera', 'height', int),
            'CAMERA_FPS': ('camera', 'fps', int),
            'DETECTION_CONFIDENCE': ('detection', 'min_detection_confidence', float),
            'DETECTION_COMPLEXITY': ('detection', 'model_complexity', int),
            'PROCESSING_WORKERS': ('processing', 'num_workers', int),
            'PROCESSING_QUEUE_SIZE': ('processing', 'max_queue_size', int),
            'LOG_LEVEL': ('logging', 'level', str),
            'LOG_FILE': ('logging', 'file_path', str),
        }
        
        for env_var, (section, key, type_func) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Ensure section exists
                    if section not in config_dict:
                        config_dict[section] = {}
                    
                    # Convert and set value
                    config_dict[section][key] = type_func(env_value)
                    print(f"Override from env: {env_var} = {env_value}")
                    
                except ValueError as e:
                    print(f"Warning: Invalid environment variable {env_var}={env_value}: {e}")
        
        return config_dict
    
    def list_configs(self) -> list:
        """List available configuration files."""
        if not self.config_dir.exists():
            return []
        
        config_files = list(self.config_dir.glob("*.yaml"))
        return [f.stem for f in config_files]
    
    def validate_config(self, config: AppConfig) -> bool:
        """Validate configuration settings."""
        try:
            # Validation is done in __post_init__ methods
            # This could be extended with additional validation logic
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False


# Profile-based configuration
class ConfigurationProfiles:
    """Manages different configuration profiles."""
    
    PROFILES = {
        'default': {
            'camera': {'device_id': 0, 'width': 640, 'height': 480, 'fps': 30},
            'detection': {'model_complexity': 1, 'min_detection_confidence': 0.5},
            'processing': {'max_queue_size': 10, 'num_workers': 2}
        },
        'high_quality': {
            'camera': {'device_id': 0, 'width': 1280, 'height': 720, 'fps': 30},
            'detection': {'model_complexity': 2, 'min_detection_confidence': 0.7},
            'processing': {'max_queue_size': 5, 'num_workers': 4}
        },
        'low_latency': {
            'camera': {'device_id': 0, 'width': 320, 'height': 240, 'fps': 60},
            'detection': {'model_complexity': 0, 'min_detection_confidence': 0.3},
            'processing': {'max_queue_size': 3, 'num_workers': 1}
        },
        'battery_saver': {
            'camera': {'device_id': 0, 'width': 480, 'height': 360, 'fps': 15},
            'detection': {'model_complexity': 0, 'min_detection_confidence': 0.4},
            'processing': {'max_queue_size': 5, 'num_workers': 1}
        }
    }
    
    @classmethod
    def get_profile(cls, profile_name: str) -> AppConfig:
        """Get configuration for specified profile."""
        if profile_name not in cls.PROFILES:
            raise ValueError(f"Unknown profile: {profile_name}. Available: {list(cls.PROFILES.keys())}")
        
        profile_dict = cls.PROFILES[profile_name]
        return AppConfig.from_dict(profile_dict)
    
    @classmethod
    def list_profiles(cls) -> list:
        """List available configuration profiles."""
        return list(cls.PROFILES.keys())
    
    @classmethod
    def create_custom_profile(cls, base_profile: str, overrides: Dict[str, Any]) -> AppConfig:
        """Create custom profile based on existing profile with overrides."""
        if base_profile not in cls.PROFILES:
            raise ValueError(f"Unknown base profile: {base_profile}")
        
        # Deep copy base profile
        import copy
        profile_dict = copy.deepcopy(cls.PROFILES[base_profile])
        
        # Apply overrides
        for section, values in overrides.items():
            if section not in profile_dict:
                profile_dict[section] = {}
            profile_dict[section].update(values)
        
        return AppConfig.from_dict(profile_dict)


# Environment-specific configuration
class EnvironmentConfig:
    """Environment-specific configuration management."""
    
    @staticmethod
    def get_environment() -> str:
        """Determine current environment."""
        return os.getenv('APP_ENV', 'development').lower()
    
    @staticmethod
    def load_env_config() -> Dict[str, Any]:
        """Load environment-specific configuration."""
        env = EnvironmentConfig.get_environment()
        
        env_configs = {
            'development': {
                'camera': {'device_id': 0, 'fps': 30},
                'detection': {'min_detection_confidence': 0.3},  # Lower for testing
                'logging': {'level': 'DEBUG', 'console_output': True},
                'processing': {'num_workers': 1}  # Single worker for debugging
            },
            'testing': {
                'camera': {'device_id': -1},  # Mock camera
                'detection': {'min_detection_confidence': 0.1},  # Very low for tests
                'logging': {'level': 'WARNING', 'console_output': False},
                'processing': {'num_workers': 1, 'timeout_seconds': 0.1}
            },
            'production': {
                'camera': {'device_id': 0, 'fps': 30},
                'detection': {'min_detection_confidence': 0.6},  # Higher for production
                'logging': {'level': 'INFO', 'file_path': '/var/log/webcam-detection.log'},
                'processing': {'num_workers': 4}  # More workers for performance
            }
        }
        
        return env_configs.get(env, env_configs['development'])


# Configuration validation
def validate_configuration_file(config_file: str) -> bool:
    """Validate a configuration file."""
    try:
        with open(config_file, 'r') as f:
            config_dict = yaml.safe_load(f)
        
        # Try to create AppConfig (will raise exception if invalid)
        config = AppConfig.from_dict(config_dict)
        
        print(f"✓ Configuration file {config_file} is valid")
        return True
        
    except FileNotFoundError:
        print(f"✗ Configuration file {config_file} not found")
        return False
    except yaml.YAMLError as e:
        print(f"✗ YAML parsing error in {config_file}: {e}")
        return False
    except Exception as e:
        print(f"✗ Configuration validation error in {config_file}: {e}")
        return False


# Usage examples
def configuration_examples():
    """Examples of configuration usage."""
    
    print("=== Configuration Management Examples ===\n")
    
    # 1. Basic configuration creation
    print("1. Creating basic configuration:")
    config = AppConfig()
    print(f"Default camera resolution: {config.camera.width}x{config.camera.height}")
    print(f"Default detection confidence: {config.detection.min_detection_confidence}")
    
    # 2. Configuration profiles
    print("\n2. Using configuration profiles:")
    profiles = ConfigurationProfiles.list_profiles()
    print(f"Available profiles: {profiles}")
    
    high_quality_config = ConfigurationProfiles.get_profile('high_quality')
    print(f"High quality resolution: {high_quality_config.camera.width}x{high_quality_config.camera.height}")
    
    # 3. Custom profile
    print("\n3. Creating custom profile:")
    custom_config = ConfigurationProfiles.create_custom_profile(
        'default',
        {'camera': {'fps': 60}, 'detection': {'min_detection_confidence': 0.8}}
    )
    print(f"Custom config FPS: {custom_config.camera.fps}")
    print(f"Custom config confidence: {custom_config.detection.min_detection_confidence}")
    
    # 4. Environment configuration
    print("\n4. Environment-specific configuration:")
    env = EnvironmentConfig.get_environment()
    print(f"Current environment: {env}")
    
    env_config = EnvironmentConfig.load_env_config()
    print(f"Environment config: {env_config}")
    
    # 5. Configuration manager
    print("\n5. Configuration manager:")
    manager = ConfigurationManager()
    
    # Create sample config file for demonstration
    os.makedirs('config', exist_ok=True)
    sample_config = {
        'camera': {'device_id': 0, 'width': 800, 'height': 600},
        'detection': {'min_detection_confidence': 0.6}
    }
    
    with open('config/demo.yaml', 'w') as f:
        yaml.dump(sample_config, f)
    
    try:
        loaded_config = manager.load_config('demo')
        print(f"Loaded config resolution: {loaded_config.camera.width}x{loaded_config.camera.height}")
        
        # List available configs
        available_configs = manager.list_configs()
        print(f"Available configs: {available_configs}")
        
    except Exception as e:
        print(f"Error loading config: {e}")
    
    # Cleanup
    if os.path.exists('config/demo.yaml'):
        os.remove('config/demo.yaml')
    if os.path.exists('config'):
        os.rmdir('config')


if __name__ == "__main__":
    print("Configuration Management Sample Code")
    print("1. Basic YAML loading")
    print("2. Configuration examples")
    print("3. Validate sample configuration")
    
    choice = input("Enter choice (1-3): ")
    
    if choice == "1":
        config = basic_yaml_loading()
        if config:
            print("YAML loading successful!")
    elif choice == "2":
        configuration_examples()
    elif choice == "3":
        # Create a sample config for validation
        sample = {
            'camera': {'device_id': 0, 'width': 640, 'height': 480},
            'detection': {'min_detection_confidence': 0.5}
        }
        with open('test_config.yaml', 'w') as f:
            yaml.dump(sample, f)
        
        validate_configuration_file('test_config.yaml')
        
        # Cleanup
        if os.path.exists('test_config.yaml'):
            os.remove('test_config.yaml')
    else:
        print("Invalid choice") 