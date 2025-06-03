"""
Tests for OllamaConfig dataclass validation and defaults.

Phase 1.2 of TDD Ollama Description Endpoint Feature.
Following TDD methodology - RED phase: Write failing tests first.
"""
import pytest
from unittest.mock import Mock, patch
import urllib.parse

# This import will fail initially - that's the RED phase!
try:
    from src.ollama.client import OllamaConfig, OllamaError
except ImportError:
    # Expected to fail during RED phase
    OllamaConfig = None
    OllamaError = None


class TestOllamaConfigDataclassValidation:
    """RED TESTS: Test OllamaConfig dataclass validation and defaults."""
    
    def test_ollama_config_dataclass_creation_with_defaults(self):
        """
        RED TEST: OllamaConfig should be creatable with default values.
        
        This test will fail because enhanced OllamaConfig doesn't exist yet.
        Expected behavior:
        - Should create OllamaConfig with sensible defaults
        - Should have all required fields with proper defaults
        """
        config = OllamaConfig()
        
        # Test default values
        assert config.model == "gemma3:latest"
        assert config.base_url == "http://localhost:11434"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        
    def test_ollama_config_dataclass_creation_with_custom_values(self):
        """
        RED TEST: OllamaConfig should accept custom configuration values.
        
        This test will fail because enhanced OllamaConfig doesn't exist yet.
        Expected behavior:
        - Should accept custom values for all configuration fields
        - Should preserve custom values correctly
        """
        config = OllamaConfig(
            model="gemma3:7b",
            base_url="http://192.168.1.100:11434",
            timeout=60.0,
            max_retries=5
        )
        
        assert config.model == "gemma3:7b"
        assert config.base_url == "http://192.168.1.100:11434" 
        assert config.timeout == 60.0
        assert config.max_retries == 5


class TestOllamaConfigValidation:
    """RED TESTS: Test OllamaConfig validation logic."""
    
    def test_ollama_config_validation_timeout_positive(self):
        """
        RED TEST: OllamaConfig should validate timeout is positive.
        
        This test will fail because validation doesn't exist yet.
        Expected behavior:
        - Should raise ValueError for negative timeout
        - Should provide clear error message
        """
        with pytest.raises(ValueError, match="timeout must be positive"):
            OllamaConfig(timeout=-5.0)
            
    def test_ollama_config_validation_timeout_zero_invalid(self):
        """
        RED TEST: OllamaConfig should reject zero timeout.
        """
        with pytest.raises(ValueError, match="timeout must be positive"):
            OllamaConfig(timeout=0.0)
            
    def test_ollama_config_validation_max_retries_non_negative(self):
        """
        RED TEST: OllamaConfig should validate max_retries is non-negative.
        """
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            OllamaConfig(max_retries=-1)
            
    def test_ollama_config_validation_max_retries_zero_allowed(self):
        """
        RED TEST: OllamaConfig should allow zero retries (no retries).
        """
        config = OllamaConfig(max_retries=0)
        assert config.max_retries == 0
            
    def test_ollama_config_validation_base_url_format(self):
        """
        RED TEST: OllamaConfig should validate base_url is properly formatted.
        """
        with pytest.raises(ValueError, match="base_url must be a valid URL"):
            OllamaConfig(base_url="not-a-url")
            
    def test_ollama_config_validation_base_url_http_scheme(self):
        """
        RED TEST: OllamaConfig should require HTTP/HTTPS scheme in base_url.
        """
        with pytest.raises(ValueError, match="base_url must use http or https scheme"):
            OllamaConfig(base_url="ftp://localhost:11434")
            
    def test_ollama_config_validation_model_non_empty(self):
        """
        RED TEST: OllamaConfig should validate model is not empty.
        """
        with pytest.raises(ValueError, match="model cannot be empty"):
            OllamaConfig(model="")
            
    def test_ollama_config_validation_model_whitespace_only(self):
        """
        RED TEST: OllamaConfig should reject whitespace-only model names.
        """
        with pytest.raises(ValueError, match="model cannot be empty"):
            OllamaConfig(model="   ")


class TestOllamaConfigSerialization:
    """RED TESTS: Test OllamaConfig serialization and deserialization."""
    
    def test_ollama_config_to_dict_serialization(self):
        """
        RED TEST: OllamaConfig should be serializable to dict.
        
        This test will fail because to_dict() doesn't exist yet.
        Expected behavior:
        - Should convert all fields to dictionary
        - Should include all configuration values
        """
        config = OllamaConfig(model="gemma3:7b", timeout=45.0)
        config_dict = config.to_dict()
        
        assert config_dict["model"] == "gemma3:7b"
        assert config_dict["base_url"] == "http://localhost:11434"
        assert config_dict["timeout"] == 45.0
        assert config_dict["max_retries"] == 3
        
    def test_ollama_config_to_dict_all_custom_values(self):
        """
        RED TEST: OllamaConfig.to_dict() should work with all custom values.
        """
        config = OllamaConfig(
            model="llama3.2-vision:latest",
            base_url="http://custom-server:8080",
            timeout=120.0,
            max_retries=10
        )
        config_dict = config.to_dict()
        
        assert config_dict["model"] == "llama3.2-vision:latest"
        assert config_dict["base_url"] == "http://custom-server:8080"
        assert config_dict["timeout"] == 120.0
        assert config_dict["max_retries"] == 10
        
    def test_ollama_config_from_dict_deserialization(self):
        """
        RED TEST: OllamaConfig should be creatable from dict.
        
        This test will fail because from_dict() doesn't exist yet.
        Expected behavior:
        - Should create OllamaConfig instance from dictionary
        - Should handle all configuration fields
        - Should validate input during deserialization
        """
        config_dict = {
            "model": "gemma3:7b",
            "base_url": "http://custom:11434",
            "timeout": 45.0,
            "max_retries": 2
        }
        
        config = OllamaConfig.from_dict(config_dict)
        assert config.model == "gemma3:7b"
        assert config.base_url == "http://custom:11434"
        assert config.timeout == 45.0
        assert config.max_retries == 2
        
    def test_ollama_config_from_dict_missing_fields_use_defaults(self):
        """
        RED TEST: OllamaConfig.from_dict() should use defaults for missing fields.
        """
        config_dict = {
            "model": "custom-model"
            # Missing other fields should use defaults
        }
        
        config = OllamaConfig.from_dict(config_dict)
        assert config.model == "custom-model"
        assert config.base_url == "http://localhost:11434"  # Default
        assert config.timeout == 30.0  # Default
        assert config.max_retries == 3  # Default
        
    def test_ollama_config_from_dict_validation_applied(self):
        """
        RED TEST: OllamaConfig.from_dict() should apply validation.
        """
        config_dict = {
            "model": "",  # Invalid empty model
            "timeout": -5.0  # Invalid negative timeout
        }
        
        with pytest.raises(ValueError):
            OllamaConfig.from_dict(config_dict)


class TestOllamaConfigHelperMethods:
    """RED TESTS: Test OllamaConfig helper methods and utilities."""
    
    def test_ollama_config_validate_url_helper(self):
        """
        RED TEST: OllamaConfig should have URL validation helper.
        
        This test will fail because _validate_url() doesn't exist yet.
        Expected behavior:
        - Should validate URL format
        - Should check for required scheme
        - Should provide descriptive error messages
        """
        # Valid URLs should pass
        assert OllamaConfig._validate_url("http://localhost:11434") is True
        assert OllamaConfig._validate_url("https://example.com:8080") is True
        
        # Invalid URLs should fail
        with pytest.raises(ValueError):
            OllamaConfig._validate_url("not-a-url")
        with pytest.raises(ValueError):
            OllamaConfig._validate_url("ftp://localhost:11434")
            
    def test_ollama_config_get_api_endpoint_helper(self):
        """
        RED TEST: OllamaConfig should provide API endpoint construction.
        
        This test will fail because get_api_endpoint() doesn't exist yet.
        Expected behavior:
        - Should construct proper API endpoints from base_url
        - Should handle trailing slashes correctly
        - Should support different endpoint paths
        """
        config = OllamaConfig(base_url="http://localhost:11434")
        
        # Test different endpoints
        assert config.get_api_endpoint("chat") == "http://localhost:11434/api/chat"
        assert config.get_api_endpoint("tags") == "http://localhost:11434/api/tags"
        
        # Test with trailing slash in base_url
        config_with_slash = OllamaConfig(base_url="http://localhost:11434/")
        assert config_with_slash.get_api_endpoint("chat") == "http://localhost:11434/api/chat"
        
    def test_ollama_config_repr_string_representation(self):
        """
        RED TEST: OllamaConfig should have readable string representation.
        """
        config = OllamaConfig(model="gemma3:7b", timeout=45.0)
        repr_str = repr(config)
        
        assert "OllamaConfig" in repr_str
        assert "gemma3:7b" in repr_str
        assert "45.0" in repr_str
        
    def test_ollama_config_equality_comparison(self):
        """
        RED TEST: OllamaConfig should support equality comparison.
        """
        config1 = OllamaConfig(model="gemma3:7b", timeout=30.0)
        config2 = OllamaConfig(model="gemma3:7b", timeout=30.0)
        config3 = OllamaConfig(model="different-model", timeout=30.0)
        
        assert config1 == config2
        assert config1 != config3


# Run the tests to see them fail (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 