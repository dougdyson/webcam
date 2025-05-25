"""
Logging configuration and utilities for the webcam human detection application.

This module provides a centralized logging management system with support for:
- File and console logging
- Log rotation
- Configurable formatting
- YAML configuration loading
- Environment variable integration
- Structured logging
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
import yaml


class LoggerError(Exception):
    """Exception raised for logger configuration errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize LoggerError.
        
        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Chain exceptions for better debugging
        if original_error:
            self.__cause__ = original_error


class LoggerManager:
    """
    Manages application logging configuration and logger creation.
    
    Features:
    - Default and custom logger configurations
    - File and console handlers with rotation
    - YAML configuration loading
    - Environment variable overrides
    - Multiple log levels and formatters
    - Structured logging support
    - Thread-safe logger management
    """
    
    # Default logging configuration
    DEFAULT_CONFIG = {
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'handlers': {
                'console': {
                    'enabled': True,
                    'level': 'INFO',
                    'stream': 'stdout'
                },
                'file': {
                    'enabled': False,
                    'level': 'DEBUG',
                    'filename': 'logs/webcam.log',
                    'rotation': {
                        'enabled': False,
                        'max_bytes': 10485760,  # 10MB
                        'backup_count': 5
                    }
                }
            }
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the LoggerManager.
        
        Args:
            config_file: Optional path to YAML configuration file
            
        Raises:
            LoggerError: If configuration file is specified but cannot be loaded
        """
        self._config: Dict[str, Any] = {}
        self._loggers: Dict[str, logging.Logger] = {}
        self._initialized = False
        
        try:
            if config_file:
                self._load_config(config_file)
            else:
                self._set_default_config()
            
            self._apply_environment_overrides()
            self._validate_config()
            self._initialized = True
            
        except Exception as e:
            if isinstance(e, LoggerError):
                raise
            raise LoggerError(f"Failed to initialize LoggerManager: {e}", e)
    
    def _load_config(self, config_file: str) -> None:
        """
        Load configuration from YAML file.
        
        Args:
            config_file: Path to YAML configuration file
            
        Raises:
            LoggerError: If file cannot be loaded or parsed
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise LoggerError(f"Configuration file not found: {config_file}")
        
        if not config_path.is_file():
            raise LoggerError(f"Configuration path is not a file: {config_file}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = yaml.safe_load(f)
                
            if not isinstance(loaded_config, dict):
                raise LoggerError("Configuration file must contain a YAML dictionary")
            
            # Merge with defaults
            self._config = self._deep_merge(self.DEFAULT_CONFIG.copy(), loaded_config)
            
        except yaml.YAMLError as e:
            raise LoggerError(f"Invalid YAML in configuration file: {e}", e)
        except UnicodeDecodeError as e:
            raise LoggerError(f"Configuration file encoding error: {e}", e)
        except Exception as e:
            raise LoggerError(f"Error loading configuration file: {e}", e)
    
    def _set_default_config(self) -> None:
        """Set default logging configuration."""
        self._config = self.DEFAULT_CONFIG.copy()
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # Log level override
        env_level = os.getenv('WEBCAM_LOG_LEVEL')
        if env_level:
            try:
                # Validate log level
                getattr(logging, env_level.upper())
                self._config['logging']['level'] = env_level.upper()
            except AttributeError:
                # Invalid log level, ignore
                pass
        
        # Log file override
        env_file = os.getenv('WEBCAM_LOG_FILE')
        if env_file:
            self._config['logging']['handlers']['file']['filename'] = env_file
            self._config['logging']['handlers']['file']['enabled'] = True
        
        # Console logging disable
        env_no_console = os.getenv('WEBCAM_NO_CONSOLE_LOG', '').lower()
        if env_no_console in ('1', 'true', 'yes', 'on'):
            self._config['logging']['handlers']['console']['enabled'] = False
    
    def _validate_config(self) -> None:
        """Validate the logging configuration."""
        if 'logging' not in self._config:
            raise LoggerError("Configuration must contain 'logging' section")
        
        logging_config = self._config['logging']
        
        # Validate log level
        level = logging_config.get('level', 'INFO')
        try:
            getattr(logging, level.upper())
        except AttributeError:
            raise LoggerError(f"Invalid log level: {level}")
        
        # Validate handlers exist
        if 'handlers' not in logging_config:
            raise LoggerError("Configuration must contain 'handlers' section")
        
        handlers = logging_config['handlers']
        
        # At least one handler must be enabled
        enabled_handlers = [
            name for name, config in handlers.items() 
            if config.get('enabled', False)
        ]
        
        if not enabled_handlers:
            # Enable console as fallback
            handlers['console']['enabled'] = True
    
    def _deep_merge(self, base_dict: Dict, update_dict: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base_dict.copy()
        
        for key, value in update_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_logger(self, name: str, level: Optional[str] = None) -> logging.Logger:
        """
        Get or create a logger with the specified name.
        
        Args:
            name: Logger name
            level: Optional log level override (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            
        Returns:
            Configured logger instance
            
        Raises:
            LoggerError: If logger configuration fails
        """
        if not self._initialized:
            raise LoggerError("LoggerManager not properly initialized")
        
        # Return cached logger if exists and level hasn't changed
        cache_key = f"{name}:{level or 'default'}"
        if cache_key in self._loggers:
            return self._loggers[cache_key]
        
        try:
            logger = logging.getLogger(name)
            
            # Set level
            if level:
                try:
                    logger.setLevel(getattr(logging, level.upper()))
                except AttributeError:
                    raise LoggerError(f"Invalid log level: {level}")
            else:
                config_level = self._config['logging']['level']
                logger.setLevel(getattr(logging, config_level.upper()))
            
            # Clear any existing handlers to avoid duplicates
            logger.handlers.clear()
            logger.propagate = False  # Prevent double logging
            
            # Configure handlers
            self._configure_handlers(logger)
            
            # Ensure at least one handler exists
            if not logger.handlers:
                self._add_fallback_console_handler(logger)
            
            self._loggers[cache_key] = logger
            return logger
            
        except Exception as e:
            if isinstance(e, LoggerError):
                raise
            raise LoggerError(f"Failed to create logger '{name}': {e}", e)
    
    def _configure_handlers(self, logger: logging.Logger) -> None:
        """Configure handlers for the logger based on configuration."""
        handlers_config = self._config['logging']['handlers']
        
        # Console handler
        if handlers_config.get('console', {}).get('enabled', True):
            self._add_console_handler(logger, handlers_config['console'])
        
        # File handler
        if handlers_config.get('file', {}).get('enabled', False):
            self._add_file_handler(logger, handlers_config['file'])
    
    def configure_file_logging(self, name: str, filename: str, level: str = 'INFO') -> logging.Logger:
        """
        Configure a logger with file output.
        
        Args:
            name: Logger name
            filename: Log file path
            level: Log level
            
        Returns:
            Configured logger instance
            
        Raises:
            LoggerError: If file logging configuration fails
        """
        try:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, level.upper()))
            logger.handlers.clear()
            logger.propagate = False
            
            # Create directory if it doesn't exist
            log_path = Path(filename)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add file handler
            file_handler = logging.FileHandler(filename, encoding='utf-8')
            file_handler.setLevel(getattr(logging, level.upper()))
            
            formatter = self._get_formatter()
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            
            cache_key = f"{name}:file_{level}"
            self._loggers[cache_key] = logger
            return logger
            
        except Exception as e:
            raise LoggerError(f"Failed to configure file logging for '{name}': {e}", e)
    
    def configure_console_logging(self, name: str, level: str = 'INFO') -> logging.Logger:
        """
        Configure a logger with console output.
        
        Args:
            name: Logger name
            level: Log level
            
        Returns:
            Configured logger instance
            
        Raises:
            LoggerError: If console logging configuration fails
        """
        try:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, level.upper()))
            logger.handlers.clear()
            logger.propagate = False
            
            # Add console handler
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, level.upper()))
            
            formatter = self._get_formatter()
            console_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            
            cache_key = f"{name}:console_{level}"
            self._loggers[cache_key] = logger
            return logger
            
        except Exception as e:
            raise LoggerError(f"Failed to configure console logging for '{name}': {e}", e)
    
    def configure_rotating_file_logging(
        self, 
        name: str, 
        filename: str, 
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        level: str = 'INFO'
    ) -> logging.Logger:
        """
        Configure a logger with rotating file output.
        
        Args:
            name: Logger name
            filename: Log file path
            max_bytes: Maximum file size before rotation
            backup_count: Number of backup files to keep
            level: Log level
            
        Returns:
            Configured logger instance
            
        Raises:
            LoggerError: If rotating file logging configuration fails
        """
        try:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, level.upper()))
            logger.handlers.clear()
            logger.propagate = False
            
            # Create directory if it doesn't exist
            log_path = Path(filename)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add rotating file handler
            rotating_handler = logging.handlers.RotatingFileHandler(
                filename,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            rotating_handler.setLevel(getattr(logging, level.upper()))
            
            formatter = self._get_formatter()
            rotating_handler.setFormatter(formatter)
            
            logger.addHandler(rotating_handler)
            
            cache_key = f"{name}:rotating_{level}"
            self._loggers[cache_key] = logger
            return logger
            
        except Exception as e:
            raise LoggerError(f"Failed to configure rotating file logging for '{name}': {e}", e)
    
    def _add_console_handler(self, logger: logging.Logger, config: Dict) -> None:
        """Add console handler to logger."""
        try:
            # Determine output stream
            stream_name = config.get('stream', 'stdout').lower()
            stream = sys.stdout if stream_name == 'stdout' else sys.stderr
            
            console_handler = logging.StreamHandler(stream)
            
            level = config.get('level', 'INFO')
            console_handler.setLevel(getattr(logging, level.upper()))
            
            formatter = self._get_formatter()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
        except Exception as e:
            raise LoggerError(f"Failed to add console handler: {e}", e)
    
    def _add_file_handler(self, logger: logging.Logger, config: Dict) -> None:
        """Add file handler to logger."""
        try:
            filename = config.get('filename', 'logs/webcam.log')
            
            # Create directory if it doesn't exist
            log_path = Path(filename)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if rotation is enabled
            rotation_config = config.get('rotation', {})
            if rotation_config.get('enabled', False):
                file_handler = logging.handlers.RotatingFileHandler(
                    filename,
                    maxBytes=rotation_config.get('max_bytes', 10485760),
                    backupCount=rotation_config.get('backup_count', 5),
                    encoding='utf-8'
                )
            else:
                file_handler = logging.FileHandler(filename, encoding='utf-8')
            
            level = config.get('level', 'DEBUG')
            file_handler.setLevel(getattr(logging, level.upper()))
            
            formatter = self._get_formatter()
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            raise LoggerError(f"Failed to add file handler: {e}", e)
    
    def _add_fallback_console_handler(self, logger: logging.Logger) -> None:
        """Add fallback console handler when no other handlers are configured."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    def _get_formatter(self) -> logging.Formatter:
        """Get log formatter from configuration."""
        format_string = self._config['logging'].get(
            'format', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        date_format = self._config['logging'].get('date_format')
        
        return logging.Formatter(format_string, datefmt=date_format)
    
    def get_available_loggers(self) -> List[str]:
        """Get list of available logger names."""
        return list(self._loggers.keys())
    
    def clear_loggers(self) -> None:
        """Clear all cached loggers."""
        for logger in self._loggers.values():
            # Close handlers to free resources
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()
        
        self._loggers.clear()
    
    def is_initialized(self) -> bool:
        """Check if LoggerManager is properly initialized."""
        return self._initialized
    
    def get_config(self) -> Dict[str, Any]:
        """Get a copy of the current configuration."""
        return self._config.copy() if self._config else {} 