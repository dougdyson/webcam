"""
Ollama client for image description processing.

REFACTOR phase: Adding validation and helper methods following existing patterns.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Union
import requests
import logging
import base64


class OllamaError(Exception):
    """Exception raised for Ollama-related errors."""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        """
        Initialize Ollama error.
        
        Args:
            message: Error description
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error
        
        # Include original error in message if provided
        if original_error:
            self.args = (f"{message} (caused by: {str(original_error)})",)


@dataclass
class OllamaConfig:
    """
    Configuration for Ollama client.
    
    This dataclass standardizes configuration parameters for
    Ollama integration with validation and helper methods.
    """
    model: str = "gemma3:latest"
    base_url: str = "http://localhost:11434"
    timeout: float = 30.0
    max_retries: int = 3
    
    def __post_init__(self):
        """Validate configuration parameters."""
        # Validate timeout
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        
        # Validate max_retries
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")
        
        # Validate model name (basic check)
        if not self.model or not isinstance(self.model, str):
            raise ValueError("Model must be a non-empty string")
        
        # Validate base_url (basic check)
        if not self.base_url or not isinstance(self.base_url, str):
            raise ValueError("Base URL must be a non-empty string")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OllamaConfig':
        """Create OllamaConfig from dictionary."""
        return cls(**data)
    
    def update(self, **kwargs) -> None:
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")
        
        # Re-validate after update
        self.__post_init__()


class OllamaClient:
    """
    Ollama client for image description processing.
    
    Provides interface to local Ollama service for generating
    detailed descriptions of webcam snapshots.
    """
    
    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialize OllamaClient with configuration.
        
        Args:
            config: Ollama configuration, defaults to OllamaConfig()
        """
        self.config = config or OllamaConfig()
        self.logger = logging.getLogger(__name__)
    
    def is_available(self) -> bool:
        """
        Check if Ollama service is available and responding.
        
        Returns:
            True if Ollama service is accessible, False otherwise
        """
        try:
            # Construct health check URL
            health_url = f"{self.config.base_url}/api/tags"
            
            # Make health check request with proper error handling
            response = requests.get(health_url, timeout=self.config.timeout)
            
            # Check if response is successful and valid
            if response.status_code == 200:
                # Try to parse JSON to ensure it's a valid Ollama response
                try:
                    json_data = response.json()
                    # Basic validation - should have models array
                    if isinstance(json_data, dict) and "models" in json_data:
                        self.logger.debug(f"Ollama health check successful: {health_url}")
                        return True
                    else:
                        self.logger.warning(f"Ollama health check returned unexpected format: {json_data}")
                        return False
                except ValueError as e:
                    self.logger.warning(f"Ollama health check returned invalid JSON: {e}")
                    return False
            else:
                self.logger.warning(f"Ollama health check failed with status {response.status_code}: {health_url}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            self.logger.debug(f"Ollama service not available (connection refused): {e}")
            return False
        except requests.exceptions.Timeout as e:
            self.logger.warning(f"Ollama health check timed out after {self.config.timeout}s: {e}")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Ollama health check request failed: {e}")
            return False
        except TimeoutError as e:
            self.logger.warning(f"Ollama health check timeout: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during Ollama health check: {e}")
            return False
    
    def describe_image(self, image_data: Union[bytes, str], prompt: str = "Describe what is happening in this image, particularly what any humans are doing.") -> str:
        """
        Generate a description of the provided image using Ollama.
        
        Args:
            image_data: Image as bytes or base64 string
            prompt: Custom prompt for image description
            
        Returns:
            Description text from Ollama model
            
        Raises:
            OllamaError: If description generation fails
        """
        # Validate inputs
        if not image_data:
            raise OllamaError("Image data cannot be empty")
        if not prompt or not prompt.strip():
            raise OllamaError("Prompt cannot be empty")
        
        try:
            # Convert image data to base64 if needed
            if isinstance(image_data, bytes):
                if len(image_data) == 0:
                    raise OllamaError("Image data is empty")
                image_b64 = base64.b64encode(image_data).decode('utf-8')
            else:
                # Validate base64 string
                if not image_data.strip():
                    raise OllamaError("Image data string is empty")
                image_b64 = image_data.strip()
            
            # Construct API URL  
            api_url = f"{self.config.base_url}/api/chat"
            
            # Prepare optimized request payload
            payload = {
                "model": self.config.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt.strip(),
                        "images": [image_b64]
                    }
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,  # More consistent responses
                    "top_p": 0.9,        # Focus on high probability tokens
                }
            }
            
            # Set appropriate headers for better performance
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            self.logger.debug(f"Sending image description request to {api_url} (model: {self.config.model})")
            
            # Make request to Ollama API with retry logic
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = requests.post(
                        api_url, 
                        json=payload, 
                        headers=headers,
                        timeout=self.config.timeout
                    )
                    
                    # Check response status
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            
                            # Comprehensive response validation
                            if not isinstance(response_data, dict):
                                raise OllamaError(f"Expected JSON object, got {type(response_data)}")
                            
                            # Extract description from response
                            if "message" in response_data and isinstance(response_data["message"], dict):
                                message = response_data["message"]
                                if "content" in message and isinstance(message["content"], str):
                                    description = message["content"].strip()
                                    if not description:
                                        raise OllamaError("Ollama returned empty description")
                                    
                                    self.logger.debug(f"Ollama description generated successfully: {len(description)} chars")
                                    return description
                                else:
                                    raise OllamaError(f"Missing or invalid 'content' in message: {message}")
                            else:
                                raise OllamaError(f"Missing or invalid 'message' in response: {response_data}")
                                
                        except ValueError as e:
                            raise OllamaError(f"Invalid JSON response from Ollama: {e}", e)
                    
                    elif response.status_code in (500, 502, 503, 504) and attempt < self.config.max_retries:
                        # Retry on server errors
                        self.logger.warning(f"Ollama server error {response.status_code}, retrying ({attempt + 1}/{self.config.max_retries})")
                        continue
                    else:
                        # Final attempt or non-retryable error
                        raise OllamaError(f"Ollama API returned status {response.status_code}: {response.text}")
                        
                except (requests.exceptions.Timeout, TimeoutError) as e:
                    if attempt < self.config.max_retries:
                        self.logger.warning(f"Ollama timeout, retrying ({attempt + 1}/{self.config.max_retries})")
                        continue
                    else:
                        raise OllamaError(f"Ollama request timed out after {self.config.max_retries + 1} attempts: {e}", e)
                        
                except requests.exceptions.ConnectionError as e:
                    if attempt < self.config.max_retries:
                        self.logger.warning(f"Ollama connection error, retrying ({attempt + 1}/{self.config.max_retries})")
                        continue
                    else:
                        raise OllamaError(f"Failed to connect to Ollama service after {self.config.max_retries + 1} attempts: {e}", e)
                        
        except requests.exceptions.RequestException as e:
            raise OllamaError(f"Ollama request failed: {e}", e)
        except Exception as e:
            if isinstance(e, OllamaError):
                raise
            raise OllamaError(f"Unexpected error during image description: {e}", e) 