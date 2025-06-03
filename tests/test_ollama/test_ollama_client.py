"""
Tests for OllamaClient integration.

Following TDD methodology - RED phase: Write failing tests first.
"""
import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Optional

# This import will fail initially - that's the RED phase!
try:
    from src.ollama.client import OllamaClient, OllamaConfig, OllamaError
except ImportError:
    # Expected to fail during RED phase
    OllamaClient = None
    OllamaConfig = None
    OllamaError = None


class TestOllamaClient:
    """Test suite for OllamaClient initialization and configuration."""
    
    def test_ollama_client_init_with_default_config(self):
        """
        RED: Test OllamaClient initialization with default configuration.
        
        This test will fail because OllamaClient doesn't exist yet.
        Expected behavior:
        - Should create OllamaClient with default OllamaConfig
        - Should set basic properties like model, timeout, base_url
        """
        # This will fail - OllamaClient doesn't exist yet
        client = OllamaClient()
        
        # Expected behavior once implemented
        assert client is not None
        assert hasattr(client, 'config')
        assert client.config is not None
        
    def test_ollama_client_init_with_custom_config(self):
        """
        RED: Test OllamaClient initialization with custom configuration.
        
        This test will fail because OllamaConfig doesn't exist yet.
        """
        # Create custom config (will fail initially)
        custom_config = OllamaConfig(
            model="gemma3:latest",
            base_url="http://localhost:11434",
            timeout=30.0
        )
        
        # Initialize client with custom config (will fail initially) 
        client = OllamaClient(config=custom_config)
        
        # Expected behavior once implemented
        assert client.config == custom_config
        assert client.config.model == "gemma3:latest"
        assert client.config.timeout == 30.0
        
    def test_ollama_config_dataclass_validation(self):
        """
        RED: Test OllamaConfig dataclass with validation.
        
        This test will fail because OllamaConfig doesn't exist yet.
        """
        # Test valid configuration
        config = OllamaConfig(
            model="gemma3:latest",
            base_url="http://localhost:11434",
            timeout=10.0,
            max_retries=3
        )
        
        assert config.model == "gemma3:latest"
        assert config.base_url == "http://localhost:11434"
        assert config.timeout == 10.0
        assert config.max_retries == 3
        
    def test_ollama_config_default_values(self):
        """
        RED: Test OllamaConfig with default values.
        
        This test will fail because OllamaConfig doesn't exist yet.
        """
        config = OllamaConfig()
        
        # Expected defaults (will be defined in GREEN phase)
        assert config.model == "gemma3:latest"  # Default model
        assert config.base_url == "http://localhost:11434"  # Default Ollama URL
        assert config.timeout == 30.0  # Default timeout
        assert config.max_retries == 3  # Default retries

    def test_ollama_client_is_available_service_running(self):
        """
        RED: Test OllamaClient.is_available() when Ollama service is running.
        
        This test will fail because is_available() method doesn't exist yet.
        Expected behavior:
        - Should return True when Ollama service is accessible
        - Should check the /api/tags endpoint or similar health check
        - Should handle network requests properly
        """
        client = OllamaClient()
        
        # Mock successful HTTP response for health check
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response
            
            # This will fail - is_available() doesn't exist yet
            result = client.is_available()
            
            # Expected behavior once implemented
            assert result is True
            mock_get.assert_called_once()
            
    def test_ollama_client_is_available_service_not_running(self):
        """
        RED: Test OllamaClient.is_available() when Ollama service is not running.
        
        This test will fail because is_available() method doesn't exist yet.
        Expected behavior:
        - Should return False when Ollama service is not accessible
        - Should handle connection errors gracefully
        - Should not raise exceptions
        """
        client = OllamaClient()
        
        # Mock connection error
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("Connection refused")
            
            # This will fail - is_available() doesn't exist yet
            result = client.is_available()
            
            # Expected behavior once implemented
            assert result is False
            mock_get.assert_called_once()
            
    def test_ollama_client_is_available_timeout_handling(self):
        """
        RED: Test OllamaClient.is_available() handles timeouts gracefully.
        
        This test will fail because is_available() method doesn't exist yet.
        Expected behavior:
        - Should return False when request times out
        - Should respect the configured timeout value
        - Should not raise exceptions
        """
        config = OllamaConfig(timeout=5.0)
        client = OllamaClient(config=config)
        
        # Mock timeout error
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError("Request timed out")
            
            # This will fail - is_available() doesn't exist yet
            result = client.is_available()
            
            # Expected behavior once implemented
            assert result is False
            mock_get.assert_called_with(
                "http://localhost:11434/api/tags",
                timeout=5.0
            )

    def test_ollama_client_is_available_custom_base_url(self):
        """
        RED: Test OllamaClient.is_available() with custom base URL.
        
        This test will fail because is_available() method doesn't exist yet.
        Expected behavior:
        - Should use the configured base_url for health check
        - Should construct the correct health check endpoint
        """
        config = OllamaConfig(base_url="http://custom.ollama.server:8080")
        client = OllamaClient(config=config)
        
        # Mock successful response
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"models": []}
            mock_get.return_value = mock_response
            
            # This will fail - is_available() doesn't exist yet
            result = client.is_available()
            
            # Expected behavior once implemented
            assert result is True
            mock_get.assert_called_with(
                "http://custom.ollama.server:8080/api/tags",
                timeout=30.0
            )

    def test_ollama_client_describe_image_success(self):
        """
        RED: Test OllamaClient.describe_image() with successful response.
        
        This test will fail because describe_image() method doesn't exist yet.
        Expected behavior:
        - Should accept image data (bytes or base64 string)
        - Should send proper request to Ollama API
        - Should return description string from response
        - Should handle the Ollama chat API format
        """
        client = OllamaClient()
        
        # Sample image data (we'll use base64 string representation)
        sample_image_data = b"fake_image_bytes_data"
        
        # Mock successful Ollama response
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {
                    "content": "A person standing near a desk, typing on a laptop computer"
                }
            }
            mock_post.return_value = mock_response
            
            # This will fail - describe_image() doesn't exist yet
            result = client.describe_image(sample_image_data)
            
            # Expected behavior once implemented
            assert result == "A person standing near a desk, typing on a laptop computer"
            
            # Verify the API call was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "http://localhost:11434/api/chat" in call_args[0][0]
            
            # Check request structure
            request_data = call_args[1]["json"]
            assert request_data["model"] == "gemma3:latest"
            assert len(request_data["messages"]) == 1
            assert request_data["messages"][0]["role"] == "user"
            assert "image" in request_data["messages"][0]["content"].lower()

    def test_ollama_client_describe_image_custom_prompt(self):
        """
        RED: Test OllamaClient.describe_image() with custom prompt.
        
        This test will fail because describe_image() method doesn't exist yet.
        Expected behavior:
        - Should accept custom prompt parameter
        - Should include custom prompt in the request
        - Should handle prompt customization properly
        """
        client = OllamaClient()
        
        sample_image_data = b"fake_image_bytes_data"
        custom_prompt = "Describe what the human is doing in this image in detail"
        
        # Mock successful response
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {
                    "content": "The human is actively typing on a laptop keyboard while standing at a desk"
                }
            }
            mock_post.return_value = mock_response
            
            # This will fail - describe_image() doesn't exist yet
            result = client.describe_image(sample_image_data, prompt=custom_prompt)
            
            # Expected behavior once implemented
            assert result == "The human is actively typing on a laptop keyboard while standing at a desk"
            
            # Verify custom prompt was used
            request_data = mock_post.call_args[1]["json"]
            assert custom_prompt in request_data["messages"][0]["content"]

    def test_ollama_client_describe_image_error_handling(self):
        """
        RED: Test OllamaClient.describe_image() error handling.
        
        This test will fail because describe_image() method doesn't exist yet.
        Expected behavior:
        - Should handle connection errors gracefully
        - Should handle Ollama API errors properly
        - Should raise appropriate exceptions or return error indicators
        """
        client = OllamaClient()
        
        sample_image_data = b"fake_image_bytes_data"
        
        # Test connection error
        with patch('requests.post') as mock_post:
            mock_post.side_effect = ConnectionError("Connection refused")
            
            # This will fail - describe_image() doesn't exist yet
            try:
                client.describe_image(sample_image_data)
                assert False, "Should have raised OllamaError"
            except Exception as e:
                # Expected to raise OllamaError
                assert isinstance(e, OllamaError)
                assert "connection" in str(e).lower()

    def test_ollama_client_describe_image_timeout(self):
        """
        RED: Test OllamaClient.describe_image() timeout handling.
        
        This test will fail because describe_image() method doesn't exist yet.
        Expected behavior:
        - Should respect configured timeout
        - Should handle timeout errors gracefully
        - Should raise appropriate timeout exceptions
        """
        config = OllamaConfig(timeout=5.0)
        client = OllamaClient(config=config)
        
        sample_image_data = b"fake_image_bytes_data"
        
        # Test timeout
        with patch('requests.post') as mock_post:
            mock_post.side_effect = TimeoutError("Request timed out")
            
            # This will fail - describe_image() doesn't exist yet
            try:
                client.describe_image(sample_image_data)
                assert False, "Should have raised OllamaError"
            except Exception as e:
                # Expected to raise OllamaError
                assert isinstance(e, OllamaError)
                assert "timed out" in str(e).lower()
                
            # Verify timeout was passed to requests and retries happened
            assert mock_post.call_count == 4  # 1 initial + 3 retries (max_retries=3)
            assert mock_post.call_args[1]["timeout"] == 5.0

    def test_ollama_client_describe_image_invalid_response(self):
        """
        RED: Test OllamaClient.describe_image() with invalid response format.
        
        This test will fail because describe_image() method doesn't exist yet.
        Expected behavior:
        - Should handle malformed JSON responses
        - Should handle unexpected response structure
        - Should raise appropriate exceptions for invalid data
        """
        client = OllamaClient()
        
        sample_image_data = b"fake_image_bytes_data"
        
        # Test invalid JSON response
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_post.return_value = mock_response
            
            # This will fail - describe_image() doesn't exist yet
            try:
                client.describe_image(sample_image_data)
                assert False, "Should have raised OllamaError"
            except Exception as e:
                # Expected to raise OllamaError
                assert isinstance(e, OllamaError)
                assert "response" in str(e).lower() or "json" in str(e).lower()

    def test_ollama_client_describe_image_different_models(self):
        """
        RED: Test OllamaClient.describe_image() with different models.
        
        This test will fail because describe_image() method doesn't exist yet.
        Expected behavior:
        - Should use the configured model from OllamaConfig
        - Should send the correct model in the API request
        - Should work with different model configurations
        """
        # Test with custom model
        config = OllamaConfig(model="llama3.2-vision:latest")
        client = OllamaClient(config=config)
        
        sample_image_data = b"fake_image_bytes_data"
        
        # Mock successful response
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "message": {
                    "content": "Description from custom model"
                }
            }
            mock_post.return_value = mock_response
            
            # This will fail - describe_image() doesn't exist yet
            result = client.describe_image(sample_image_data)
            
            # Expected behavior once implemented
            assert result == "Description from custom model"
            
            # Verify correct model was used
            request_data = mock_post.call_args[1]["json"]
            assert request_data["model"] == "llama3.2-vision:latest"


# Run the test to see it fail (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 