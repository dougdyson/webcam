"""
Ollama client for image description processing.

REFACTOR phase: Adding validation and helper methods following existing patterns.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


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