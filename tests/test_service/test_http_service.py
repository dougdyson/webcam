"""
Test suite for HTTP service infrastructure.
Following TDD methodology - these tests define the behavior before implementation.
"""

import pytest
import asyncio
import aiohttp
import threading
import time
from unittest.mock import Mock, patch, AsyncMock
from src.service.http_service import HTTPService
from src.service.base_service import BaseService
from src.detection.factory import create_detector


class TestHTTPServiceInitialization:
    """Test HTTP service initialization and configuration."""
    
    def test_service_initialization_with_default_config(self):
        """Test service initializes with default configuration."""
        service = HTTPService()
        
        assert service.port == 8767  # Default HTTP API port
        assert service.host == "localhost"
        assert service.detection_service is None  # Not initialized yet
        assert service.app is not None  # FastAPI app created
        assert service.server is None  # Server not started
        
    def test_service_initialization_with_custom_config(self):
        """Test service initializes with custom configuration."""
        config = {
            'port': 9000,
            'host': '0.0.0.0',
            'cors_enabled': True,
            'rate_limit': 100
        }
        
        service = HTTPService(config=config)
        
        assert service.port == 9000
        assert service.host == '0.0.0.0'
        assert service.cors_enabled is True
        assert service.rate_limit == 100
        
    def test_service_initialization_with_detection_service(self):
        """Test service initializes with detection service integration."""
        # Mock detection service
        mock_detector = Mock()
        mock_detector.detect_person = Mock(return_value=(True, 0.85, 'multimodal'))
        
        service = HTTPService(detection_service=mock_detector)
        
        assert service.detection_service is mock_detector
        assert service.detection_service.detect_person is not None
        
    def test_service_configuration_validation(self):
        """Test service validates configuration parameters."""
        # Invalid port
        with pytest.raises(ValueError, match="Port must be between 1024 and 65535"):
            HTTPService(config={'port': 80})
            
        # Invalid host
        with pytest.raises(ValueError, match="Invalid host format"):
            HTTPService(config={'host': 'invalid_host_format'})
            
        # Invalid rate limit
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            HTTPService(config={'rate_limit': -1})


class TestHTTPServiceLifecycle:
    """Test HTTP service startup, running, and shutdown."""
    
    @pytest.fixture
    def mock_detection_service(self):
        """Fixture providing mock detection service."""
        mock = Mock()
        mock.detect_person = Mock(return_value=(True, 0.85, 'multimodal'))
        mock.is_active = Mock(return_value=True)
        mock.get_status = Mock(return_value={'status': 'active', 'fps': 25})
        return mock
    
    def test_service_startup_success(self, mock_detection_service):
        """Test successful service startup."""
        service = HTTPService(detection_service=mock_detection_service)
        
        # Start service in thread to avoid blocking
        start_event = threading.Event()
        
        def start_service():
            service.start()
            start_event.set()
            
        thread = threading.Thread(target=start_service, daemon=True)
        thread.start()
        
        # Wait for startup
        assert start_event.wait(timeout=5), "Service should start within 5 seconds"
        assert service.is_running is True
        assert service.server is not None
        
        # Cleanup
        service.stop()
        
    def test_service_startup_without_detection_service(self):
        """Test service startup without detection service (graceful degradation)."""
        service = HTTPService()
        
        # Should start successfully but in degraded mode
        start_event = threading.Event()
        
        def start_service():
            service.start()
            start_event.set()
            
        thread = threading.Thread(target=start_service, daemon=True)
        thread.start()
        
        assert start_event.wait(timeout=5)
        assert service.is_running is True
        assert service.detection_service is None
        
        service.stop()
        
    def test_service_startup_port_already_in_use(self, mock_detection_service):
        """Test service handles port already in use error."""
        # Start first service
        service1 = HTTPService(detection_service=mock_detection_service)
        service1.start()
        
        try:
            # Try to start second service on same port
            service2 = HTTPService(detection_service=mock_detection_service)
            
            with pytest.raises(RuntimeError, match="Port 8767 is already in use"):
                service2.start()
                
        finally:
            service1.stop()
            
    def test_service_graceful_shutdown(self, mock_detection_service):
        """Test service shuts down gracefully."""
        service = HTTPService(detection_service=mock_detection_service)
        service.start()
        
        assert service.is_running is True
        
        # Stop service
        service.stop()
        
        assert service.is_running is False
        assert service.server is None
        
    def test_service_shutdown_timeout_handling(self, mock_detection_service):
        """Test service handles shutdown timeout gracefully."""
        service = HTTPService(detection_service=mock_detection_service)
        service.start()
        
        # Mock server that doesn't respond to shutdown
        mock_server = Mock()
        mock_server.shutdown = AsyncMock(side_effect=asyncio.TimeoutError())
        service.server = mock_server
        
        # Should handle timeout gracefully
        service.stop(timeout=1)
        
        assert service.is_running is False


class TestHTTPServiceDetectionIntegration:
    """Test integration between HTTP service and detection system."""
    
    @pytest.fixture
    def multimodal_detector(self):
        """Fixture providing real multimodal detector for integration tests."""
        config = {
            'detector_type': 'multimodal',
            'pose_weight': 0.6,
            'face_weight': 0.4,
            'confidence_threshold': 0.5
        }
        return create_detector('multimodal', config)
    
    def test_detection_integration_initialization(self, multimodal_detector):
        """Test detection service integrates properly during initialization."""
        service = HTTPService(detection_service=multimodal_detector)
        
        assert service.detection_service is not None
        assert hasattr(service.detection_service, 'detect_person')
        assert hasattr(service.detection_service, 'get_detection_info')
        
    def test_detection_pipeline_health_check(self, multimodal_detector):
        """Test service can check detection pipeline health."""
        service = HTTPService(detection_service=multimodal_detector)
        
        health_status = service.check_detection_health()
        
        assert 'camera_connected' in health_status
        assert 'detection_active' in health_status
        assert 'last_detection_time' in health_status
        
    def test_detection_error_handling(self):
        """Test service handles detection errors gracefully."""
        # Mock detector that raises exceptions
        mock_detector = Mock()
        mock_detector.detect_person = Mock(side_effect=RuntimeError("Camera disconnected"))
        
        service = HTTPService(detection_service=mock_detector)
        
        # Service should handle detection errors and return degraded response
        result = service._safe_detect_person()
        
        assert result['present'] is False
        assert result['confidence'] == 0.0
        assert result['error'] == "Detection unavailable"
        assert result['detection_type'] == 'error'
        
    def test_detection_performance_monitoring(self, multimodal_detector):
        """Test service monitors detection performance."""
        service = HTTPService(detection_service=multimodal_detector)
        
        # Perform several detections
        for _ in range(10):
            service._safe_detect_person()
            
        metrics = service.get_performance_metrics()
        
        assert 'avg_detection_time' in metrics
        assert 'total_detections' in metrics
        assert metrics['total_detections'] == 10
        assert metrics['avg_detection_time'] > 0


class TestHTTPServiceErrorHandling:
    """Test HTTP service error handling and resilience."""
    
    def test_graceful_degradation_no_camera(self):
        """Test service gracefully degrades when no camera available."""
        # Mock detector that simulates no camera
        mock_detector = Mock()
        mock_detector.detect_person = Mock(side_effect=Exception("No camera found"))
        
        service = HTTPService(detection_service=mock_detector)
        
        # Service should start and handle requests with degraded responses
        response = service._safe_detect_person()
        
        assert response['present'] is False
        assert response['confidence'] == 0.0
        assert 'error' in response
        
    def test_detection_timeout_handling(self):
        """Test service handles detection timeouts."""
        # Mock detector with slow response
        mock_detector = Mock()
        mock_detector.detect_person = Mock(side_effect=asyncio.TimeoutError())
        
        service = HTTPService(detection_service=mock_detector)
        
        response = service._safe_detect_person()
        
        assert response['present'] is False
        assert response['error'] == "Detection timeout"
        
    def test_memory_pressure_handling(self):
        """Test service handles memory pressure gracefully."""
        mock_detector = Mock()
        mock_detector.detect_person = Mock(side_effect=MemoryError("Out of memory"))
        
        service = HTTPService(detection_service=mock_detector)
        
        response = service._safe_detect_person()
        
        assert response['present'] is False
        assert response['error'] == "System resource exhausted"
        
    def test_concurrent_request_handling(self, mock_detection_service):
        """Test service handles concurrent requests properly."""
        service = HTTPService(detection_service=mock_detection_service)
        
        # Simulate concurrent detection requests
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(service._safe_detect_person) 
                for _ in range(20)
            ]
            
            responses = [future.result() for future in futures]
            
        # All requests should complete successfully
        assert len(responses) == 20
        assert all('present' in response for response in responses)
        
    def test_request_rate_limiting(self):
        """Test service implements request rate limiting."""
        service = HTTPService(config={'rate_limit': 5})  # 5 requests per second
        
        # Make rapid requests
        start_time = time.time()
        responses = []
        
        for _ in range(10):
            responses.append(service._handle_rate_limited_request())
            
        elapsed_time = time.time() - start_time
        
        # Should have been rate limited
        assert elapsed_time > 1.0  # Should take at least 2 seconds for 10 requests at 5/sec
        assert any('rate_limited' in str(response) for response in responses[-5:])


class TestHTTPServiceConfiguration:
    """Test HTTP service configuration management."""
    
    def test_configuration_loading_from_file(self, tmp_path):
        """Test service loads configuration from file."""
        config_file = tmp_path / "service_config.yml"
        config_content = """
        http_service:
          port: 9999
          host: "127.0.0.1"
          cors_enabled: true
          rate_limit: 50
          timeout: 30
        """
        config_file.write_text(config_content)
        
        service = HTTPService(config_file=str(config_file))
        
        assert service.port == 9999
        assert service.host == "127.0.0.1"
        assert service.cors_enabled is True
        assert service.rate_limit == 50
        assert service.timeout == 30
        
    def test_configuration_validation_and_defaults(self):
        """Test service validates configuration and applies defaults."""
        # Minimal config
        config = {'port': 8888}
        service = HTTPService(config=config)
        
        assert service.port == 8888
        assert service.host == "localhost"  # Default
        assert service.cors_enabled is False  # Default
        assert service.rate_limit == 10  # Default
        
    def test_configuration_hot_reload(self):
        """Test service supports configuration hot reload."""
        service = HTTPService()
        original_rate_limit = service.rate_limit
        
        # Update configuration
        new_config = {'rate_limit': original_rate_limit * 2}
        service.update_config(new_config)
        
        assert service.rate_limit == original_rate_limit * 2
        
    def test_configuration_persistence(self, tmp_path):
        """Test service persists configuration changes."""
        config_file = tmp_path / "service_config.yml"
        service = HTTPService(config_file=str(config_file))
        
        # Update and save configuration
        service.update_config({'rate_limit': 99})
        service.save_config()
        
        # Create new service instance
        new_service = HTTPService(config_file=str(config_file))
        
        assert new_service.rate_limit == 99 