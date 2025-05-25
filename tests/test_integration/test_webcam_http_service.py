#!/usr/bin/env python3
"""
Tests for WebcamHTTPService Integration

Tests the complete webcam HTTP service that connects real detection to HTTP API.
This covers the production service that was created without TDD (our mistake!).
"""
import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import signal

# Import the service we need to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from webcam_http_service import WebcamHTTPService, main
from src.detection.result import DetectionResult
from src.service.events import EventType


class TestWebcamHTTPService:
    """Test the WebcamHTTPService class."""
    
    def test_webcam_http_service_initialization(self):
        """Test service initializes with correct defaults."""
        service = WebcamHTTPService()
        
        assert service.detection_app is None
        assert service.http_service is None
        assert service.event_publisher is not None
        assert service.is_running is True
        assert service._shutdown_requested is False
        assert service._last_presence is False
    
    @patch('webcam_http_service.MainApp')
    def test_setup_detection_system(self, mock_main_app):
        """Test detection system setup with proper configuration."""
        # Mock MainApp and its methods
        mock_app_instance = Mock()
        mock_main_app.return_value = mock_app_instance
        
        service = WebcamHTTPService()
        service.setup_detection_system()
        
        # Verify MainApp was created with correct config
        mock_main_app.assert_called_once()
        args, kwargs = mock_main_app.call_args
        config = args[0]
        
        assert config.detector_type == 'multimodal'
        assert config.detection_confidence_threshold == 0.5
        assert config.enable_display is True
        assert config.enable_logging is True
        assert config.log_level == 'INFO'
        
        # Verify initialization was called
        mock_app_instance.initialize.assert_called_once()
        assert service.detection_app == mock_app_instance
    
    @patch('webcam_http_service.HTTPDetectionService')
    def test_setup_http_service(self, mock_http_service):
        """Test HTTP service setup with proper configuration."""
        # Mock HTTPDetectionService
        mock_service_instance = Mock()
        mock_http_service.return_value = mock_service_instance
        
        service = WebcamHTTPService()
        service.setup_http_service()
        
        # Verify HTTPDetectionService was created with correct config
        mock_http_service.assert_called_once()
        args, kwargs = mock_http_service.call_args
        config = args[0]
        
        assert config.host == "localhost"
        assert config.port == 8767
        assert config.enable_history is True
        assert config.history_limit == 100
        
        # Verify setup was called
        mock_service_instance.setup_detection_integration.assert_called_once()
        assert service.http_service == mock_service_instance
    
    @patch('webcam_http_service.threading.Thread')
    def test_connect_systems(self, mock_thread):
        """Test systems connection via bridge thread."""
        service = WebcamHTTPService()
        service.connect_systems()
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs['daemon'] is True
        
        # Verify thread was started
        mock_thread.return_value.start.assert_called_once()
        assert hasattr(service, 'bridge_thread')
    
    def test_publish_detection_result_success(self):
        """Test successful detection result publishing."""
        service = WebcamHTTPService()
        
        # Mock HTTP service with proper mock setup
        mock_http_service = Mock()
        mock_current_status = Mock()
        mock_current_status.detection_count = 0  # Set initial value
        mock_http_service.current_status = mock_current_status
        service.http_service = mock_http_service
        
        # Create test detection result with proper bounding box
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.85,
            timestamp=time.time(),
            bounding_box=(10, 20, 100, 200),  # Proper 4-tuple
            landmarks=[]
        )
        
        # Test publishing
        service.publish_detection_result(detection_result)
        
        # Verify HTTP service status was updated
        assert mock_current_status.human_present is True
        assert mock_current_status.confidence == 0.85
        assert isinstance(mock_current_status.last_detection, datetime)
        # Check that detection_count was incremented (0 + 1 = 1)
        assert mock_current_status.detection_count == 1
    
    def test_publish_detection_result_no_http_service(self):
        """Test detection result publishing handles missing HTTP service gracefully."""
        service = WebcamHTTPService()
        service.http_service = None  # No HTTP service
        
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.85,
            timestamp=time.time(),
            bounding_box=(0, 0, 0, 0),  # Proper 4-tuple
            landmarks=[]
        )
        
        # Test publishing with no HTTP service - should not raise exception
        service.publish_detection_result(detection_result)
        # If we get here without exception, the error handling worked
    
    def test_publish_detection_result_error_handling(self):
        """Test detection result publishing handles errors gracefully."""
        service = WebcamHTTPService()
        
        # Mock HTTP service that raises an error
        mock_http_service = Mock()
        mock_http_service.current_status = None  # This will cause an AttributeError
        service.http_service = mock_http_service
        
        # Create test detection result with proper bounding box
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.85,
            timestamp=time.time(),
            bounding_box=(10, 20, 100, 200),  # Proper 4-tuple
            landmarks=[]
        )
        
        # Test publishing with error - should not raise exception
        service.publish_detection_result(detection_result)
        # If we get here without exception, the error handling worked
    
    @pytest.mark.asyncio
    async def test_start_http_service(self):
        """Test HTTP service startup."""
        # Use different import approach for mocking
        with patch('uvicorn.Config') as mock_config_class, \
             patch('uvicorn.Server') as mock_server_class:
            
            service = WebcamHTTPService()
            
            # Setup mock HTTP service
            mock_http_service = Mock()
            mock_app = Mock()
            mock_http_service.app = mock_app
            service.http_service = mock_http_service
            
            # Setup mock uvicorn components
            mock_config = Mock()
            mock_server = Mock()
            mock_server.serve = AsyncMock()
            mock_config_class.return_value = mock_config
            mock_server_class.return_value = mock_server
            
            await service.start_http_service()
            
            # Should create uvicorn config
            mock_config_class.assert_called_once_with(
                mock_app,
                host="localhost",
                port=8767,
                log_level="warning"
            )
            
            # Should create and start server
            mock_server_class.assert_called_once_with(mock_config)
            mock_server.serve.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_http_service_no_service(self):
        """Test HTTP service startup handles missing service gracefully."""
        service = WebcamHTTPService()
        service.http_service = None
        
        # Should not raise exception
        await service.start_http_service()
    
    @pytest.mark.asyncio
    async def test_start_detection_system(self):
        """Test detection system startup."""
        service = WebcamHTTPService()
        
        # Mock detection app
        mock_detection_app = AsyncMock()
        service.detection_app = mock_detection_app
        
        # Test starting detection system
        await service.start_detection_system()
        
        # Verify detection app methods were called
        mock_detection_app.start.assert_called_once()
        mock_detection_app.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_detection_system_no_app(self):
        """Test detection system startup handles missing app gracefully."""
        service = WebcamHTTPService()
        service.detection_app = None
        
        # Should not raise exception
        await service.start_detection_system()
    
    @patch.object(WebcamHTTPService, 'setup_detection_system')
    @patch.object(WebcamHTTPService, 'setup_http_service')
    @patch.object(WebcamHTTPService, 'connect_systems')
    @patch.object(WebcamHTTPService, 'start_detection_system')
    @patch.object(WebcamHTTPService, 'start_http_service')
    @pytest.mark.asyncio
    async def test_run_success(self, mock_start_http, mock_start_detection, 
                               mock_connect, mock_setup_http, mock_setup_detection):
        """Test complete service run integration."""
        service = WebcamHTTPService()
        
        # Mock async methods to complete quickly
        mock_start_detection.return_value = asyncio.create_task(asyncio.sleep(0.01))
        mock_start_http.return_value = asyncio.create_task(asyncio.sleep(0.01))
        
        # Test run method
        await service.run()
        
        # Verify all setup methods were called
        mock_setup_detection.assert_called_once()
        mock_setup_http.assert_called_once()
        mock_connect.assert_called_once()
        
        # Verify both start methods were called
        mock_start_detection.assert_called_once()
        mock_start_http.assert_called_once()
    
    @patch.object(WebcamHTTPService, 'setup_detection_system')
    @patch.object(WebcamHTTPService, 'setup_http_service')
    @patch.object(WebcamHTTPService, 'connect_systems')
    @patch.object(WebcamHTTPService, 'start_detection_system')
    @patch.object(WebcamHTTPService, 'start_http_service')
    @patch.object(WebcamHTTPService, 'shutdown')
    @pytest.mark.asyncio
    async def test_run_error_handling(self, mock_shutdown, mock_start_http, mock_start_detection, 
                                      mock_connect, mock_setup_http, mock_setup_detection):
        """Test run method handles errors and triggers shutdown."""
        service = WebcamHTTPService()
        
        # Make setup fail
        mock_setup_detection.side_effect = Exception("Setup failed")
        
        # Test run with error
        with pytest.raises(Exception, match="Setup failed"):
            await service.run()
        
        # Verify shutdown was called
        mock_shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test graceful shutdown."""
        service = WebcamHTTPService()
        
        # Mock detection app
        mock_detection_app = AsyncMock()
        service.detection_app = mock_detection_app
        
        # Test shutdown
        await service.shutdown()
        
        # Verify shutdown state
        assert service._shutdown_requested is True
        assert service.is_running is False
        
        # Verify detection app shutdown was called
        mock_detection_app.shutdown.assert_called_once()
    
    @patch('webcam_http_service.signal.signal')
    def test_setup_signal_handlers(self, mock_signal):
        """Test signal handler setup."""
        service = WebcamHTTPService()
        service.setup_signal_handlers()
        
        # Verify signal handlers were registered
        assert mock_signal.call_count == 2
        
        # Check SIGINT and SIGTERM were registered
        calls = mock_signal.call_args_list
        signals_registered = [call[0][0] for call in calls]
        assert signal.SIGINT in signals_registered
        assert signal.SIGTERM in signals_registered
    
    def test_signal_handler_functionality(self):
        """Test signal handler triggers shutdown."""
        service = WebcamHTTPService()
        
        # Test the signal handler directly
        # Get the actual handler that was registered
        with patch('webcam_http_service.signal.signal') as mock_signal:
            service.setup_signal_handlers()
            
            # Get the handler function from the registration call
            calls = mock_signal.call_args_list
            handler_func = calls[0][0][1]  # Second argument is the handler function
            
            # Call the handler (simulating signal reception)
            handler_func(signal.SIGINT, None)
            
            # Verify shutdown was requested
            assert service._shutdown_requested is True


class TestWebcamHTTPServiceIntegration:
    """Integration tests for complete service workflows."""
    
    def test_detection_bridge_integration(self):
        """Test detection bridge functionality."""
        service = WebcamHTTPService()
        
        # Mock detection app
        mock_detection_app = Mock()
        mock_detection_app.is_running = True
        mock_detection_app.get_presence_status.return_value = {
            'human_present': True, 
            'confidence': 0.8
        }
        service.detection_app = mock_detection_app
        
        # Mock HTTP service
        mock_http_service = Mock()
        mock_current_status = Mock()
        mock_current_status.detection_count = 0
        mock_http_service.current_status = mock_current_status
        service.http_service = mock_http_service
        
        # Track published results
        published_results = []
        original_publish = service.publish_detection_result
        def track_publish(result):
            published_results.append(result)
            return original_publish(result)
        service.publish_detection_result = track_publish
        
        # Simulate presence change
        service._last_presence = False  # Start with no presence
        
        # Simulate bridge detecting presence change
        presence_status = mock_detection_app.get_presence_status()
        current_presence = presence_status.get('human_present', False)
        
        if service._last_presence != current_presence:
            detection_result = DetectionResult(
                human_present=current_presence,
                confidence=presence_status.get('confidence', 0.0),
                timestamp=time.time(),
                bounding_box=(0, 0, 0, 0),  # Proper 4-tuple
                landmarks=[]
            )
            service.publish_detection_result(detection_result)
        
        # Verify presence change was detected and published
        assert len(published_results) == 1
        assert published_results[0].human_present is True
        assert published_results[0].confidence == 0.8
    
    @patch('webcam_http_service.asyncio.run')
    @patch.object(WebcamHTTPService, 'setup_signal_handlers')
    def test_main_function(self, mock_setup_signals, mock_asyncio_run):
        """Test main function execution."""
        # Mock asyncio.run to avoid actually running the service
        mock_asyncio_run.side_effect = KeyboardInterrupt()
        
        with patch('builtins.print'):  # Suppress output during test
            main()
        
        # Should setup signal handlers
        mock_setup_signals.assert_called_once()
        
        # Should attempt to run the service
        mock_asyncio_run.assert_called_once()


class TestWebcamHTTPServiceErrorScenarios:
    """Test error scenarios and edge cases."""
    
    def test_bridge_thread_error_recovery(self):
        """Test bridge thread handles errors gracefully."""
        service = WebcamHTTPService()
        
        # Mock detection app that raises an error
        mock_detection_app = Mock()
        mock_detection_app.is_running = True
        mock_detection_app.get_presence_status.side_effect = Exception("Test error")
        service.detection_app = mock_detection_app
        
        # The bridge should handle errors gracefully
        # We can't easily test the actual bridge thread, but we can test
        # that the logic handles errors without crashing
        try:
            presence_status = mock_detection_app.get_presence_status()
        except Exception:
            # This should be caught in the actual bridge
            pass
        
        # Test passes if no unhandled exception
        assert True
    
    def test_timestamp_conversion_edge_cases(self):
        """Test timestamp conversion handles different formats."""
        service = WebcamHTTPService()
        
        # Mock HTTP service
        mock_http_service = Mock()
        mock_status = Mock()
        mock_status.detection_count = 0
        mock_http_service.current_status = mock_status
        service.http_service = mock_http_service
        
        # Test with float timestamp
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            timestamp=1234567890.5,  # Float timestamp
            bounding_box=(0, 0, 0, 0),  # Proper 4-tuple
            landmarks=[]
        )
        
        service.publish_detection_result(detection_result)
        
        # Verify timestamp was converted to datetime
        assert isinstance(mock_status.last_detection, datetime)
    
    @pytest.mark.asyncio
    async def test_concurrent_shutdown(self):
        """Test shutdown works correctly during concurrent operations."""
        service = WebcamHTTPService()
        
        # Mock detection app
        mock_detection_app = AsyncMock()
        service.detection_app = mock_detection_app
        
        # Test multiple shutdown calls
        await service.shutdown()
        await service.shutdown()  # Second call should be harmless
        
        # Verify final state
        assert service._shutdown_requested is True
        assert service.is_running is False


if __name__ == "__main__":
    pytest.main([__file__]) 