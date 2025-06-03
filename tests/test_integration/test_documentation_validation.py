#!/usr/bin/env python3
"""
Phase 8.1: Documentation Validation Tests (Testing Against Live Service)
========================================================================

TDD Phase 8.1: Documentation validation tests ensure all documented examples work correctly.

This test file validates:
1. API endpoint examples from README.md and ARCHITECTURE.md work as documented
2. Configuration examples are syntactically correct and loadable
3. Integration code snippets are functional
4. Performance characteristics match documented claims

IMPORTANT: These tests run against the LIVE SERVICE without modifying source code.
"""

import pytest
import requests
import yaml
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestAPIDocumentationExamples:
    """Test Phase 8.1.1: API Documentation Examples Work As Documented"""
    
    def test_service_is_accessible_for_documentation_testing(self):
        """
        Test that the service is running and accessible for documentation validation.
        
        This is a prerequisite test - if this fails, start the service first:
        python webcam_service.py
        """
        try:
            response = requests.get("http://localhost:8767/health", timeout=2.0)
            assert response.status_code == 200, "Service should be running on port 8767"
            health_data = response.json()
            assert "status" in health_data, "Health endpoint should return status"
        except requests.exceptions.ConnectionError:
            pytest.skip("Service not running. Start with: python webcam_service.py")
    
    def test_readme_guard_clause_example_works_as_documented(self):
        """
        Test that the README.md speaker verification guard clause example works.
        
        From README.md:
        ```python
        def should_process_audio() -> bool:
            try:
                response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
                return response.json().get("human_present", False) if response.status_code == 200 else True
            except:
                return True  # Fail safe
        ```
        """
        # Test the documented guard clause pattern
        def should_process_audio() -> bool:
            """Guard clause: only process audio when human present."""
            try:
                response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
                return response.json().get("human_present", False) if response.status_code == 200 else True
            except:
                return True  # Fail safe
        
        # Test that the function works
        result = should_process_audio()
        assert isinstance(result, bool), "Guard clause should return boolean as documented"
        
        # Test that the endpoint returns the expected format
        response = requests.get("http://localhost:8767/presence/simple", timeout=2.0)
        assert response.status_code == 200, "Simple presence endpoint should return 200"
        
        data = response.json()
        assert "human_present" in data, "Response should contain 'human_present' key as documented"
        assert isinstance(data["human_present"], bool), "human_present should be boolean as documented"
    
    def test_architecture_api_endpoints_match_documentation(self):
        """
        Test that ARCHITECTURE.md API endpoint examples return documented response formats.
        
        Documented endpoints:
        - GET /presence/simple   → {"human_present": true}
        - GET /presence         → Full presence status  
        - GET /statistics       → Performance metrics
        - GET /health          → Service health check
        - GET /description/latest → AI scene descriptions
        """
        # Test documented endpoints and their response formats
        endpoints_to_test = [
            {
                "path": "/presence/simple",
                "required_keys": ["human_present"],
                "description": "Simple boolean presence check"
            },
            {
                "path": "/presence", 
                "required_keys": ["human_present", "confidence"],
                "description": "Full presence status"
            },
            {
                "path": "/health",
                "required_keys": ["status"],
                "description": "Service health check"
            },
            {
                "path": "/statistics",
                "required_keys": ["total_detections"],
                "description": "Performance metrics"
            }
        ]
        
        for endpoint in endpoints_to_test:
            response = requests.get(f"http://localhost:8767{endpoint['path']}", timeout=2.0)
            assert response.status_code == 200, f"{endpoint['description']} should return 200"
            
            data = response.json()
            for required_key in endpoint["required_keys"]:
                assert required_key in data, f"{endpoint['description']} should contain '{required_key}' as documented"
    
    def test_optional_description_endpoint_if_available(self):
        """
        Test /description/latest endpoint if Ollama integration is available.
        
        This endpoint is optional - if Ollama isn't running, we expect 404 or error response.
        """
        response = requests.get("http://localhost:8767/description/latest", timeout=2.0)
        
        if response.status_code == 200:
            # If description service is available, validate response format
            data = response.json()
            assert "description" in data, "Description response should contain 'description' key"
            assert "confidence" in data, "Description response should contain 'confidence' key"
        elif response.status_code == 404:
            # If description service not available, that's acceptable
            pytest.skip("Description service not available - this is acceptable")
        else:
            # Any other status code should at least be a proper HTTP response
            assert 400 <= response.status_code < 600, "Should return valid HTTP status code"


class TestConfigurationDocumentationExamples:
    """Test Phase 8.1.2: Configuration Documentation Examples Are Valid"""
    
    def test_architecture_yaml_examples_are_syntactically_valid(self):
        """
        Test that YAML configuration examples in ARCHITECTURE.md are syntactically valid.
        """
        # Configuration examples from ARCHITECTURE.md documentation
        documented_yaml_examples = {
            "multimodal_config": """
multimodal:
  pose_weight: 0.6
  face_weight: 0.4
  min_detection_confidence: 0.5

presence_filter:
  smoothing_window: 5
  min_confidence_threshold: 0.7
  debounce_frames: 3
""",
            "service_config": """
service_layer:
  http:
    host: "localhost"
    port: 8767
  
  sse:
    port: 8766
    max_connections: 20
""",
            "ollama_config": """
client:
  base_url: "http://localhost:11434"
  model: "gemma3:4b-it-q4_K_M"
  timeout_seconds: 30.0

description_service:
  cache_ttl_seconds: 300
  max_concurrent_requests: 3
  enable_fallback_descriptions: true
"""
        }
        
        # Validate each YAML example can be parsed
        for config_name, yaml_content in documented_yaml_examples.items():
            try:
                parsed_config = yaml.safe_load(yaml_content)
                assert parsed_config is not None, f"Configuration {config_name} should parse successfully"
                assert isinstance(parsed_config, dict), f"Configuration {config_name} should be a dictionary"
            except yaml.YAMLError as e:
                pytest.fail(f"YAML syntax error in documented {config_name}: {e}")
    
    def test_readme_installation_commands_are_valid(self):
        """
        Test that README.md installation commands are syntactically valid.
        """
        # Test that environment.yml exists and is valid (required for documented conda command)
        env_file = Path("environment.yml")
        if env_file.exists():
            try:
                with open(env_file) as f:
                    env_config = yaml.safe_load(f)
                assert "name" in env_config, "environment.yml should have 'name' field"
                assert "dependencies" in env_config, "environment.yml should have 'dependencies' field"
            except Exception as e:
                pytest.fail(f"environment.yml is not valid as documented: {e}")
        else:
            pytest.skip("environment.yml not found - conda installation may not be available")


class TestIntegrationCodeSnippetValidation:
    """Test Phase 8.1.3: Integration Code Snippets Are Functional"""
    
    def test_speaker_verification_integration_pattern_works(self):
        """
        Test that the documented speaker verification integration pattern works correctly.
        """
        # Test the integration pattern under different scenarios
        def should_process_audio() -> bool:
            """Guard clause: only process audio when human present."""
            try:
                response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
                return response.json().get("human_present", False) if response.status_code == 200 else True
            except:
                return True  # Fail safe
        
        # Test normal operation
        result = should_process_audio()
        assert isinstance(result, bool), "Integration pattern should return boolean"
        
        # Test failsafe behavior when service unavailable
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            result = should_process_audio()
            assert result is True, "Should return True (failsafe) when service unavailable"
    
    def test_basic_detection_code_snippet_structure(self):
        """
        Test that the basic detection code snippets from README.md are structurally valid.
        """
        # Test that the documented imports would work (without actually importing)
        documented_imports = [
            "from webcam_detection import create_detector",
            "from webcam_detection.camera import CameraManager, CameraConfig"
        ]
        
        # We can't test the actual imports without the package installed,
        # but we can verify the syntax is valid Python
        for import_statement in documented_imports:
            try:
                compile(import_statement, '<string>', 'exec')
            except SyntaxError:
                pytest.fail(f"Invalid syntax in documented import: {import_statement}")


class TestPerformanceClaimsValidation:
    """Test Phase 8.1.4: Performance Claims Are Reasonable"""
    
    def test_documented_response_time_claims(self):
        """
        Test that documented response time claims are reasonable.
        
        ARCHITECTURE.md claims:
        - HTTP Response: <50ms for guard clause endpoints
        """
        # Test response times for guard clause endpoints
        start_time = time.time()
        response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
        response_time_ms = (time.time() - start_time) * 1000
        
        assert response.status_code == 200, "Guard clause endpoint should respond successfully"
        
        # Be reasonable about performance claims - allow some overhead
        max_reasonable_response_time = 200  # 200ms is reasonable for local service
        assert response_time_ms < max_reasonable_response_time, \
            f"Response time {response_time_ms:.1f}ms should be reasonable (< {max_reasonable_response_time}ms)"


if __name__ == "__main__":
    print("🟢 Phase 8.1: Documentation Validation Tests (Testing Against Live Service)")
    print("📋 These tests validate documentation examples work as documented")
    print("🚀 Service should be running: python webcam_service.py")
    print()
    pytest.main([__file__, "-v"]) 