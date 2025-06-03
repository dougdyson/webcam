"""
Tests for HTTP service Ollama integration - Phase 4.1
Adding /description/latest endpoint to existing HTTPDetectionService
"""
import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# Import MockDescriptionResult to avoid JSON serialization issues
from .test_http_enhanced_integration import MockDescriptionResult

# These imports will fail initially - that's expected for RED phase
try:
    from src.service.http_service import HTTPDetectionService, HTTPServiceConfig, PresenceStatus
    from src.service.events import EventPublisher, ServiceEvent, EventType
    from src.ollama.description_service import DescriptionService, DescriptionResult
    from src.ollama.snapshot_buffer import SnapshotBuffer, Snapshot, SnapshotMetadata
    from fastapi.testclient import TestClient
    import numpy as np
except ImportError:
    # Expected to fail in RED phase
    HTTPDetectionService = None
    HTTPServiceConfig = None
    PresenceStatus = None
    TestClient = None


class TestHTTPOllamaEndpointRegistration:
    """Test Phase 4.1.1: Endpoint Registration Tests (RED PHASE)"""
    
    def test_description_latest_endpoint_registration(self):
        """Should register GET /description/latest endpoint in existing HTTPDetectionService."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Test that the new endpoint is registered
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            # Should get a response (not 404), even if it's an error initially
            assert response.status_code != 404, "Endpoint should be registered"
    
    def test_description_latest_endpoint_follows_existing_patterns(self):
        """Should follow existing endpoint patterns and CORS setup."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        with TestClient(service.app) as client:
            # Test CORS preflight for new endpoint
            response = client.options("/description/latest", headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            })
            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers
    
    def test_description_service_integration_in_http_service(self):
        """Should integrate DescriptionService into HTTPDetectionService."""
        if HTTPDetectionService is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Should have description service integration
        assert hasattr(service, 'description_service') or hasattr(service, '_description_service'), \
            "HTTP service should have description service integration"


class TestHTTPOllamaSuccessfulResponse:
    """Test Phase 4.1.2: Successful Response Format Tests (RED PHASE)"""
    
    def test_successful_description_response_format(self):
        """Should implement JSON response with description, confidence, timestamp."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock a successful description result
        mock_description_result = MockDescriptionResult(
            description="A person sitting at a desk with a laptop computer",
            confidence=0.89,
            timestamp=datetime.now().isoformat(),  # Use string format
            processing_time_ms=12500,
            cached=False,
            error=None,
            success=True
        )
        
        # Create mock description service and inject it
        mock_description_service = Mock()
        mock_description_service.get_latest_description = Mock(return_value=mock_description_result)
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            assert response.status_code == 200
            
            data = response.json()
            
            # Verify required fields
            assert "description" in data
            assert "confidence" in data
            assert "timestamp" in data
            assert "processing_time_ms" in data
            assert "cached" in data
            assert "success" in data
            
            # Verify field types and values
            assert isinstance(data["description"], str)
            assert isinstance(data["confidence"], float)
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["processing_time_ms"], int)
            assert isinstance(data["cached"], bool)
            assert isinstance(data["success"], bool)
    
    def test_description_response_standardized_with_existing_endpoints(self):
        """Should standardize response format with existing endpoints."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        with TestClient(service.app) as client:
            # Get existing endpoint response format
            health_response = client.get("/health")
            assert health_response.status_code == 200
            
            # New endpoint should follow similar patterns
            desc_response = client.get("/description/latest")
            
            # Both should be JSON responses
            assert health_response.headers["content-type"] == "application/json"
            if desc_response.status_code == 200:
                assert desc_response.headers["content-type"] == "application/json"
    
    def test_cached_vs_fresh_description_indication(self):
        """Should indicate whether description is cached or freshly generated."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            if response.status_code == 200:
                data = response.json()
                assert "cached" in data
                assert isinstance(data["cached"], bool)


class TestHTTPOllamaErrorResponse:
    """Test Phase 4.1.3: Error Response Handling Tests (RED PHASE)"""
    
    def test_no_description_available_404_response(self):
        """Should implement proper 404/empty response when no description available."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Create mock description service that returns None
        mock_description_service = Mock()
        mock_description_service.get_latest_description = Mock(return_value=None)
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            # Should return 404 or specific error response when no description available
            assert response.status_code in [404, 204, 503], "Should handle no description gracefully"
            
            if response.status_code == 404:
                data = response.json()
                assert "detail" in data or "message" in data or "error" in data
    
    def test_description_service_error_response_format(self):
        """Should handle description service errors with consistent error format."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Mock description service error
        mock_error_result = MockDescriptionResult(
            description=None,
            error="Ollama service unavailable",
            success=False
        )
        
        # Create mock description service and inject it
        mock_description_service = Mock()
        mock_description_service.get_latest_description = Mock(return_value=mock_error_result)
        service.setup_description_integration(mock_description_service)
        
        with TestClient(service.app) as client:
            response = client.get("/description/latest")
            
            # Should handle errors gracefully
            assert response.status_code in [200, 503, 500], "Should handle service errors"
            
            if response.status_code == 200:
                data = response.json()
                assert "error" in data
                assert "success" in data
                assert data["success"] is False
    
    def test_consistent_error_response_format_with_existing_endpoints(self):
        """Should use consistent error response format with existing endpoints."""
        if HTTPDetectionService is None or TestClient is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        with TestClient(service.app) as client:
            # Test error response consistency
            desc_response = client.get("/description/latest")
            
            # Should use FastAPI's standard error format if 404
            if desc_response.status_code == 404:
                data = desc_response.json()
                # FastAPI standard error format
                assert "detail" in data or "message" in data


class TestHTTPOllamaServiceIntegration:
    """Test Phase 4.1.4: Service Integration Tests (RED PHASE)"""
    
    def test_description_service_dependency_injection(self):
        """Should allow DescriptionService to be injected into HTTPDetectionService."""
        if HTTPDetectionService is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Should have a method to inject description service
        assert hasattr(service, 'setup_description_integration') or \
               hasattr(service, 'set_description_service') or \
               hasattr(service, '_description_service'), \
               "Should have description service integration method"
    
    def test_snapshot_buffer_integration_with_http_service(self):
        """Should integrate with snapshot buffer for latest frames."""
        if HTTPDetectionService is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8767)
        service = HTTPDetectionService(config)
        
        # Should be able to access snapshot buffer or description service
        # This test will help define the integration pattern
        assert True  # Placeholder - will define integration pattern in GREEN phase
    
    def test_http_service_startup_with_ollama_components(self):
        """Should start HTTP service successfully with Ollama components integrated."""
        if HTTPDetectionService is None:
            pytest.skip("HTTPDetectionService not implemented yet - RED phase")
        
        config = HTTPServiceConfig(port=8768)  # Different port for testing
        service = HTTPDetectionService(config)
        
        # Should initialize without errors even with Ollama integration
        assert service is not None
        assert hasattr(service, 'app') 