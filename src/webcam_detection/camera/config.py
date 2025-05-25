"""
Camera configuration management for webcam human detection application.

This module provides configuration structures and validation for camera settings,
supporting different camera profiles and parameter validation.
"""
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple
from dataclasses import dataclass, asdict, field
import yaml

from src.utils.config import ConfigManager, ConfigurationError


# Set up module logger
logger = logging.getLogger(__name__)


class CameraConfigError(Exception):
    """Exception raised for camera configuration errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize CameraConfigError.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Chain exceptions for better debugging
        if original_error:
            self.__cause__ = original_error


@dataclass
class CameraConfig:
    """
    Camera configuration with validation and profile loading.
    
    This class provides comprehensive camera configuration management with:
    - Validation of all camera parameters
    - Profile-based configuration loading
    - Environment variable overrides
    - Common resolution and format validation
    - Serialization support
    
    Attributes:
        device_id: Camera device index (0, 1, 2, etc.)
        width: Frame width in pixels
        height: Frame height in pixels  
        fps: Target frames per second
        format: Video format (YUYV, MJPG, etc.)
        auto_exposure: Enable automatic exposure control
        exposure_time: Manual exposure time (when auto_exposure=False)
        brightness: Brightness setting (0-100)
        contrast: Contrast setting (0-100)
        buffer_size: Frame buffer size for capture
        timeout: Capture timeout in seconds
    """
    
    # Core camera settings
    device_id: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    format: str = 'YUYV'
    
    # Advanced settings
    auto_exposure: bool = True
    exposure_time: Optional[int] = None
    brightness: int = 50
    contrast: int = 50
    
    # Performance settings
    buffer_size: int = 1
    timeout: float = 5.0
    
    # Supported video formats with descriptions
    SUPPORTED_FORMATS = {
        'YUYV': 'YUV 4:2:2 (most common, good compatibility)',
        'MJPG': 'Motion JPEG (compressed, higher FPS possible)',
        'RGB24': 'RGB 24-bit (uncompressed, high quality)',
        'BGR24': 'BGR 24-bit (OpenCV native format)',
        'UYVY': 'YUV 4:2:2 alternative format'
    }
    
    # Common resolutions with aspect ratios
    COMMON_RESOLUTIONS = {
        'QVGA': (320, 240, '4:3'),
        'VGA': (640, 480, '4:3'),
        'SVGA': (800, 600, '4:3'),
        'XGA': (1024, 768, '4:3'),
        'HD': (1280, 720, '16:9'),
        'SXGA': (1280, 1024, '5:4'),
        'FHD': (1920, 1080, '16:9'),
        'QHD': (2560, 1440, '16:9'),
        'UHD': (3840, 2160, '16:9')
    }
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        try:
            self._validate()
            logger.debug(f"Created camera config: {self}")
        except Exception as e:
            logger.error(f"Camera configuration validation failed: {e}")
            raise
    
    def _validate(self) -> None:
        """Validate all camera configuration parameters."""
        validation_errors = []
        
        # Validate device ID
        if not isinstance(self.device_id, int) or self.device_id < 0:
            validation_errors.append("Device ID must be non-negative integer")
        
        # Validate dimensions
        if not isinstance(self.width, int) or self.width <= 0:
            validation_errors.append("Width must be positive integer")
            
        if not isinstance(self.height, int) or self.height <= 0:
            validation_errors.append("Height must be positive integer")
        
        # Check for reasonable dimension limits
        if hasattr(self, 'width') and hasattr(self, 'height'):
            if self.width > 7680 or self.height > 4320:  # 8K limit
                validation_errors.append("Resolution exceeds reasonable limits (8K max)")
        
        # Validate FPS
        if not isinstance(self.fps, (int, float)) or self.fps <= 0:
            validation_errors.append("FPS must be positive number")
        elif self.fps > 240:  # Reasonable FPS limit
            validation_errors.append("FPS exceeds reasonable limit (240 max)")
        
        # Validate format
        if self.format not in self.SUPPORTED_FORMATS:
            validation_errors.append(
                f"Invalid video format '{self.format}'. "
                f"Supported: {list(self.SUPPORTED_FORMATS.keys())}"
            )
        
        # Validate exposure settings
        if not self.auto_exposure and self.exposure_time is None:
            validation_errors.append("Exposure time must be provided when auto_exposure is False")
        
        if self.exposure_time is not None and self.exposure_time <= 0:
            validation_errors.append("Exposure time must be positive")
        
        # Validate brightness and contrast
        if not (0 <= self.brightness <= 100):
            validation_errors.append("Brightness must be between 0 and 100")
            
        if not (0 <= self.contrast <= 100):
            validation_errors.append("Contrast must be between 0 and 100")
        
        # Validate performance settings
        if not isinstance(self.buffer_size, int) or self.buffer_size < 1:
            validation_errors.append("Buffer size must be positive integer")
        elif self.buffer_size > 10:
            validation_errors.append("Buffer size should not exceed 10 frames")
        
        if not isinstance(self.timeout, (int, float)) or self.timeout <= 0:
            validation_errors.append("Timeout must be positive number")
        
        # Report all validation errors
        if validation_errors:
            error_msg = "Camera configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in validation_errors
            )
            raise ValueError(error_msg)
    
    @classmethod
    def from_profile(cls, profile_name: str, config_file: Optional[str] = None) -> 'CameraConfig':
        """
        Create CameraConfig from a named profile.
        
        Args:
            profile_name: Name of the camera profile to load
            config_file: Optional path to configuration file
            
        Returns:
            CameraConfig instance with profile settings
            
        Raises:
            CameraConfigError: If profile cannot be loaded
        """
        logger.info(f"Loading camera profile: {profile_name}")
        
        try:
            # Load configuration using ConfigManager
            if config_file:
                logger.debug(f"Using custom config file: {config_file}")
                # Use custom config file
                config_path = Path(config_file)
                if not config_path.exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_file}")
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                logger.debug("Using default configuration manager")
                # Use default config manager
                try:
                    config_manager = ConfigManager()
                    config_data = config_manager.load_camera_profile(profile_name)
                except ConfigurationError as e:
                    raise CameraConfigError(f"Failed to load profile '{profile_name}': {e}", e)
            
            # Extract camera profile data
            if config_file:
                # Custom config file format
                if not isinstance(config_data, dict):
                    raise CameraConfigError("Configuration file must contain a valid YAML dictionary")
                
                if 'camera_profiles' not in config_data:
                    raise CameraConfigError("Configuration file must contain 'camera_profiles' section")
                
                profiles = config_data['camera_profiles']
                if not isinstance(profiles, dict):
                    raise CameraConfigError("'camera_profiles' must be a dictionary")
                
                if profile_name not in profiles:
                    available_profiles = list(profiles.keys())
                    raise CameraConfigError(
                        f"Profile '{profile_name}' not found. "
                        f"Available profiles: {available_profiles}"
                    )
                
                profile_data = profiles[profile_name]
            else:
                # Default config manager format
                profile_data = config_data
            
            if not isinstance(profile_data, dict):
                raise CameraConfigError(f"Profile data for '{profile_name}' must be a dictionary")
            
            # Apply environment overrides
            profile_data = cls._apply_env_overrides(profile_data.copy())
            
            # Log configuration details
            logger.debug(f"Profile '{profile_name}' loaded successfully: {profile_data}")
            
            # Create CameraConfig from profile data
            return cls.from_dict(profile_data)
            
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in configuration file: {e}"
            logger.error(error_msg)
            raise CameraConfigError(error_msg, e)
        except FileNotFoundError as e:
            error_msg = f"Configuration file not found: {config_file}"
            logger.error(error_msg)
            raise CameraConfigError(error_msg, e)
        except Exception as e:
            if isinstance(e, CameraConfigError):
                raise
            error_msg = f"Failed to load camera profile '{profile_name}': {e}"
            logger.error(error_msg)
            raise CameraConfigError(error_msg, e)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'CameraConfig':
        """
        Create CameraConfig from dictionary.
        
        Args:
            config_dict: Dictionary containing camera configuration
            
        Returns:
            CameraConfig instance
            
        Raises:
            CameraConfigError: If dictionary contains invalid data
        """
        try:
            if not isinstance(config_dict, dict):
                raise CameraConfigError("Configuration data must be a dictionary")
            
            # Filter only valid fields for the dataclass
            valid_fields = {field.name for field in cls.__dataclass_fields__.values()}
            filtered_dict = {k: v for k, v in config_dict.items() if k in valid_fields}
            
            # Log ignored fields if any
            ignored_fields = set(config_dict.keys()) - valid_fields
            if ignored_fields:
                logger.warning(f"Ignoring unknown configuration fields: {ignored_fields}")
            
            return cls(**filtered_dict)
            
        except Exception as e:
            if isinstance(e, CameraConfigError):
                raise
            raise CameraConfigError(f"Failed to create camera config from dictionary: {e}", e)
    
    @classmethod
    def _apply_env_overrides(cls, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        logger.debug("Applying environment variable overrides")
        original_data = config_data.copy()
        
        env_overrides = {
            'WEBCAM_DEVICE_ID': ('device_id', int),
            'WEBCAM_WIDTH': ('width', int),
            'WEBCAM_HEIGHT': ('height', int),
            'WEBCAM_FPS': ('fps', int),
            'WEBCAM_FORMAT': ('format', str),
            'WEBCAM_BRIGHTNESS': ('brightness', int),
            'WEBCAM_CONTRAST': ('contrast', int),
            'WEBCAM_BUFFER_SIZE': ('buffer_size', int),
            'WEBCAM_TIMEOUT': ('timeout', float)
        }
        
        applied_overrides = []
        
        for env_var, (field_name, field_type) in env_overrides.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Special handling for format validation
                    if field_name == 'format':
                        if env_value in cls.SUPPORTED_FORMATS:
                            config_data[field_name] = env_value
                            applied_overrides.append(f"{field_name}={env_value}")
                        else:
                            logger.warning(
                                f"Invalid format in {env_var}: {env_value}. "
                                f"Supported: {list(cls.SUPPORTED_FORMATS.keys())}"
                            )
                    else:
                        # Type conversion and assignment
                        converted_value = field_type(env_value)
                        config_data[field_name] = converted_value
                        applied_overrides.append(f"{field_name}={converted_value}")
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid value for {env_var}: {env_value} ({e})")
        
        if applied_overrides:
            logger.info(f"Applied environment overrides: {', '.join(applied_overrides)}")
        
        return config_data
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert CameraConfig to dictionary.
        
        Returns:
            Dictionary representation of camera configuration
        """
        return asdict(self)
    
    def __repr__(self) -> str:
        """String representation of CameraConfig."""
        return (f"CameraConfig(device_id={self.device_id}, "
                f"{self.width}x{self.height}@{self.fps}fps, "
                f"format={self.format})")
    
    def copy(self, **changes) -> 'CameraConfig':
        """
        Create a copy of the configuration with optional changes.
        
        Args:
            **changes: Field updates to apply
            
        Returns:
            New CameraConfig instance with changes applied
        """
        config_dict = self.to_dict()
        config_dict.update(changes)
        return self.from_dict(config_dict)
    
    def is_valid_resolution(self) -> bool:
        """Check if the resolution is commonly supported."""
        return any(
            self.width == width and self.height == height 
            for width, height, _ in self.COMMON_RESOLUTIONS.values()
        )
    
    def get_resolution_name(self) -> Optional[str]:
        """Get the name of the resolution if it's a common one."""
        for name, (width, height, _) in self.COMMON_RESOLUTIONS.items():
            if self.width == width and self.height == height:
                return name
        return None
    
    def get_aspect_ratio(self) -> float:
        """Get the aspect ratio of the configured resolution."""
        return self.width / self.height
    
    def get_aspect_ratio_string(self) -> str:
        """Get a string representation of the aspect ratio."""
        ratio = self.get_aspect_ratio()
        
        # Check for common aspect ratios
        common_ratios = {
            4/3: '4:3',
            16/9: '16:9',
            5/4: '5:4',
            3/2: '3:2',
            16/10: '16:10'
        }
        
        for known_ratio, ratio_string in common_ratios.items():
            if abs(ratio - known_ratio) < 0.01:  # Allow small tolerance
                return ratio_string
        
        # Return decimal representation for non-standard ratios
        return f"{ratio:.2f}:1"
    
    def get_total_pixels(self) -> int:
        """Get the total number of pixels in each frame."""
        return self.width * self.height
    
    def get_megapixels(self) -> float:
        """Get the resolution in megapixels."""
        return self.get_total_pixels() / 1_000_000
    
    def estimate_bandwidth(self, bits_per_pixel: int = 12) -> float:
        """
        Estimate bandwidth requirements in Mbps.
        
        Args:
            bits_per_pixel: Bits per pixel (varies by format)
            
        Returns:
            Estimated bandwidth in Mbps
        """
        # Format-specific bits per pixel estimates
        format_bpp = {
            'YUYV': 16,
            'MJPG': 4,  # Compressed
            'RGB24': 24,
            'BGR24': 24,
            'UYVY': 16
        }
        
        bpp = format_bpp.get(self.format, bits_per_pixel)
        total_bits_per_frame = self.get_total_pixels() * bpp
        bits_per_second = total_bits_per_frame * self.fps
        return bits_per_second / 1_000_000  # Convert to Mbps
    
    def get_format_description(self) -> str:
        """Get description of the video format."""
        return self.SUPPORTED_FORMATS.get(self.format, f"Unknown format: {self.format}")
    
    def validate_compatibility(self) -> List[str]:
        """
        Check configuration for potential compatibility issues.
        
        Returns:
            List of warning messages about potential issues
        """
        warnings = []
        
        # High resolution warnings
        if self.get_total_pixels() > 2073600:  # > 1920x1080
            warnings.append("High resolution may require significant processing power")
        
        # High FPS warnings  
        if self.fps > 60:
            warnings.append("High frame rate may stress system resources")
        
        # Format-specific warnings
        if self.format == 'MJPG' and self.fps > 30:
            warnings.append("MJPG at high FPS may cause quality degradation")
        
        if self.format in ['RGB24', 'BGR24']:
            warnings.append("Uncompressed formats require high bandwidth")
        
        # Buffer size warnings
        if self.buffer_size > 5:
            warnings.append("Large buffer size may increase latency")
        
        # Unusual aspect ratio warning
        ratio = self.get_aspect_ratio()
        if ratio < 1.0 or ratio > 3.0:
            warnings.append(f"Unusual aspect ratio: {self.get_aspect_ratio_string()}")
        
        return warnings
    
    def get_opencv_properties(self) -> Dict[str, Any]:
        """
        Get OpenCV VideoCapture property mappings.
        
        Returns:
            Dictionary of OpenCV property constants to values
        """
        # This would normally import cv2, but we'll use constants for now
        CV_CAP_PROP_FRAME_WIDTH = 3
        CV_CAP_PROP_FRAME_HEIGHT = 4
        CV_CAP_PROP_FPS = 5
        CV_CAP_PROP_BRIGHTNESS = 10
        CV_CAP_PROP_CONTRAST = 11
        CV_CAP_PROP_AUTO_EXPOSURE = 21
        CV_CAP_PROP_EXPOSURE = 15
        CV_CAP_PROP_BUFFERSIZE = 38
        
        properties = {
            CV_CAP_PROP_FRAME_WIDTH: self.width,
            CV_CAP_PROP_FRAME_HEIGHT: self.height,
            CV_CAP_PROP_FPS: self.fps,
            CV_CAP_PROP_BRIGHTNESS: self.brightness / 100.0,
            CV_CAP_PROP_CONTRAST: self.contrast / 100.0,
            CV_CAP_PROP_BUFFERSIZE: self.buffer_size
        }
        
        # Exposure settings
        if self.auto_exposure:
            properties[CV_CAP_PROP_AUTO_EXPOSURE] = 0.75  # Auto mode
        else:
            properties[CV_CAP_PROP_AUTO_EXPOSURE] = 0.25  # Manual mode
            if self.exposure_time is not None:
                properties[CV_CAP_PROP_EXPOSURE] = self.exposure_time
        
        return properties
    
    @classmethod
    def get_available_profiles(cls) -> List[str]:
        """Get list of available camera profiles."""
        try:
            config_manager = ConfigManager()
            return config_manager.list_camera_profiles()
        except Exception as e:
            logger.warning(f"Could not load available profiles: {e}")
            return ['default', 'high_quality', 'low_latency']  # Fallback list 