"""
Ollama client for image description using local Ollama models.

This module provides a robust interface to interact with local Ollama installations
for generating descriptions of webcam snapshots when humans are detected.

Key Features:
- Configuration validation and management
- Health checking and service availability
- Image description with retry logic
- Error handling and logging integration
"""
import json
import logging
import time
import base64
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama-related errors."""
    
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        """
        Initialize Ollama error with optional chaining.
        
        Args:
            message: Error description
            original_exception: Original exception that caused this error
        """
        super().__init__(message)
        self.original_exception = original_exception


@dataclass
class OllamaConfig:
    """
    Configuration for Ollama client with validation and helper methods.
    
    This dataclass provides comprehensive configuration management for
    Ollama integration with built-in validation, serialization, and
    API endpoint construction.
    """
    model: str = "gemma3:latest"
    base_url: str = "http://localhost:11434"
    timeout: float = 30.0
    max_retries: int = 3

    def __post_init__(self):
        """Validate all configuration parameters."""
        self._validate_timeout()
        self._validate_max_retries()
        self._validate_model()
        self._validate_base_url()

    def _validate_timeout(self) -> None:
        """Validate timeout parameter."""
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

    def _validate_max_retries(self) -> None:
        """Validate max_retries parameter."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")

    def _validate_model(self) -> None:
        """Validate and clean model name."""
        if not self.model or not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model cannot be empty")
        # Clean up whitespace
        self.model = self.model.strip()

    def _validate_base_url(self) -> None:
        """Validate base_url format and scheme."""
        self._validate_url(self.base_url)

    @staticmethod
    def _validate_url(url: str) -> bool:
        """
        Validate URL format and scheme.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If URL is invalid or uses unsupported scheme
        """
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("base_url must be a valid URL")
            if parsed.scheme not in ['http', 'https']:
                raise ValueError("base_url must use http or https scheme")
            return True
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError("base_url must be a valid URL") from e

    def get_api_endpoint(self, path: str) -> str:
        """
        Construct API endpoint URL from base_url and path.
        
        Args:
            path: API endpoint path (e.g., 'chat', 'tags')
            
        Returns:
            Complete API endpoint URL
            
        Example:
            >>> config = OllamaConfig(base_url="http://localhost:11434")
            >>> config.get_api_endpoint("chat")
            'http://localhost:11434/api/chat'
        """
        # Ensure base_url doesn't end with slash for consistent joining
        base = self.base_url.rstrip('/')
        return f"{base}/api/{path}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary representation of all configuration fields
        """
        return {
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'OllamaConfig':
        """
        Create OllamaConfig from dictionary with defaults.
        
        Args:
            config_dict: Dictionary containing configuration values
            
        Returns:
            Validated OllamaConfig instance
            
        Raises:
            ValueError: If any validation fails
        """
        # Start with sensible defaults
        defaults = {
            "model": "gemma3:latest",
            "base_url": "http://localhost:11434", 
            "timeout": 30.0,
            "max_retries": 3
        }
        
        # Override defaults with provided values
        config_values = {**defaults, **config_dict}
        
        # Create instance (triggers validation in __post_init__)
        return cls(**config_values)

    def __repr__(self) -> str:
        """Readable string representation of configuration."""
        return (f"OllamaConfig(model='{self.model}', base_url='{self.base_url}', "
                f"timeout={self.timeout}, max_retries={self.max_retries})")

    def __eq__(self, other) -> bool:
        """
        Equality comparison for configuration objects.
        
        Args:
            other: Object to compare against
            
        Returns:
            True if all configuration fields are equal
        """
        if not isinstance(other, OllamaConfig):
            return False
        return (self.model == other.model and 
                self.base_url == other.base_url and
                self.timeout == other.timeout and
                self.max_retries == other.max_retries)


class OllamaClient:
    """
    Client for interacting with local Ollama service.
    
    Provides image description capabilities with health checking,
    retry logic, and comprehensive error handling.
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialize Ollama client with configuration.
        
        Args:
            config: OllamaConfig instance, creates default if None
        """
        self.config = config or OllamaConfig()
        logger.info(f"Initialized OllamaClient with model: {self.config.model}")

    def is_available(self) -> bool:
        """
        Check if Ollama service is available and responsive.
        
        Returns:
            True if service is available and responding correctly
            
        Raises:
            OllamaError: If service check fails unexpectedly
        """
        try:
            # Construct health check URL using config helper
            health_url = self.config.get_api_endpoint("tags")
            
            # Make health check request with proper timeout
            response = requests.get(health_url, timeout=self.config.timeout)
            response.raise_for_status()
            
            # Validate response format
            response_data = response.json()
            if not isinstance(response_data, dict) or 'models' not in response_data:
                logger.warning("Ollama health check returned unexpected format")
                return False
                
            logger.debug(f"Ollama service available with {len(response_data['models'])} models")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Ollama service unavailable: {e}")
            return False
        except (ValueError, KeyError) as e:
            logger.warning(f"Ollama health check response invalid: {e}")
            return False
        except (ConnectionError, TimeoutError) as e:
            # These should return False, not raise OllamaError
            logger.debug(f"Ollama service unavailable: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during Ollama health check: {e}")
            raise OllamaError("Unexpected error during health check", e)

    def describe_image(self, image_data: Union[bytes, str], 
                      prompt: str = "Describe what you see in this image. Be detailed and specific.") -> str:
        """
        Generate description of image using Ollama model.
        
        Args:
            image_data: Image as bytes or base64 string
            prompt: Custom prompt for image description
            
        Returns:
            Generated description text
            
        Raises:
            OllamaError: If description generation fails
        """
        # Convert image to base64 if needed
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        else:
            image_b64 = image_data
            
        # Prepare request with retry logic
        for attempt in range(self.config.max_retries + 1):
            try:
                # Construct API URL using config helper
                api_url = self.config.get_api_endpoint("chat")
                
                # Prepare optimized request payload
                payload = {
                    "model": self.config.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [image_b64]
                        }
                    ],
                    "stream": False
                }
                
                # Make request with timeout
                response = requests.post(
                    api_url, 
                    json=payload, 
                    timeout=self.config.timeout,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                # Parse and validate response
                response_data = response.json()
                if 'message' not in response_data or 'content' not in response_data['message']:
                    raise OllamaError("Invalid response format from Ollama")
                
                description = response_data['message']['content'].strip()
                if not description:
                    raise OllamaError("Empty description received from Ollama")
                
                logger.debug(f"Generated description: {description[:100]}...")
                return description
                
            except requests.exceptions.Timeout:
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Ollama timeout on attempt {attempt + 1}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue
                raise OllamaError("Ollama request timed out after all retries")
                
            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Ollama request failed on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                raise OllamaError(f"Ollama request failed after all retries: {e}", e)
                
            except (ConnectionError, TimeoutError) as e:
                # Handle non-requests exceptions that might be raised directly
                if attempt < self.config.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Ollama connection/timeout error on attempt {attempt + 1}, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                raise OllamaError(f"Ollama request failed after all retries: {e}", e)
                
            except (ValueError, KeyError) as e:
                # Response parsing errors are not retryable
                raise OllamaError(f"Failed to parse Ollama response: {e}", e)
                
        raise OllamaError("Exhausted all retry attempts") 