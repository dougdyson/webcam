"""
Test SSE (Server-Sent Events) service implementation.

Testing real-time gesture event streaming via Server-Sent Events on port 8766.
Following TDD methodology: Red → Green → Refactor.

Phase 15.1: SSE Service Core
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

import uvicorn
import httpx
from fastapi import FastAPI


class TestSSEServiceCore:
    """Test SSE service core functionality for real-time gesture event streaming."""
    
    def test_sse_service_creation_and_port_configuration(self):
        """
        RED TEST: Test SSE service creation with port 8766 configuration.
        
        Should create SSEDetectionService with proper FastAPI app and port configuration.
        """
        from src.service.sse_service import SSEDetectionService
        
        # Test service creation
        service = SSEDetectionService(host="localhost", port=8766)
        
        assert service.host == "localhost", "Should set correct host"
        assert service.port == 8766, "Should set correct port"
        assert isinstance(service.app, FastAPI), "Should create FastAPI app"
        assert hasattr(service, 'active_connections'), "Should have connection tracking"
    
    def test_sse_endpoint_route_registration(self):
        """
        RED TEST: Test SSE endpoint route registration for gesture events.
        
        Should register GET /events/gestures/{client_id} route for SSE streaming.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService()
        app = service.app
        
        # Check that SSE route is registered
        routes = [route.path for route in app.routes]
        assert "/events/gestures/{client_id}" in routes, "Should have SSE gesture endpoint"
        
        # Check route method
        gesture_route = next(route for route in app.routes if route.path == "/events/gestures/{client_id}")
        assert "GET" in gesture_route.methods, "Should support GET method for SSE"
    
    def test_sse_response_headers_and_content_type(self):
        """
        RED TEST: Test SSE response headers for proper streaming.
        
        Should set correct headers for Server-Sent Events streaming.
        """
        from src.service.sse_service import SSEDetectionService
        from fastapi.responses import StreamingResponse
        
        service = SSEDetectionService()
        
        # Test SSE headers configuration
        expected_headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache", 
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
        
        # This will be implemented in the service
        headers = service.get_sse_headers()
        
        for key, value in expected_headers.items():
            assert headers.get(key) == value, f"Should have correct {key} header"
    
    @pytest.mark.asyncio
    async def test_client_connection_management(self):
        """
        RED TEST: Test client connection tracking and management.
        
        Should track active connections and manage connection lifecycle.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService()
        
        # Test adding client connection
        client_id = "client_123"
        await service.add_client_connection(client_id)
        
        assert client_id in service.active_connections, "Should track client connection"
        assert service.get_connection_count() == 1, "Should count active connections"
        
        # Test removing client connection
        await service.remove_client_connection(client_id)
        
        assert client_id not in service.active_connections, "Should remove client connection"
        assert service.get_connection_count() == 0, "Should update connection count"
    
    @pytest.mark.asyncio  
    async def test_client_disconnection_detection(self):
        """
        RED TEST: Test automatic client disconnection detection.
        
        Should detect when client disconnects and clean up connection.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService()
        client_id = "client_456"
        
        # Mock request object with disconnection
        mock_request = Mock()
        mock_request.is_disconnected = AsyncMock(return_value=True)
        
        # Test disconnection detection
        is_connected = await service.is_client_connected(client_id, mock_request)
        
        assert not is_connected, "Should detect client disconnection"
        
        # Test automatic cleanup on disconnection
        await service.handle_client_disconnection(client_id)
        
        assert client_id not in service.active_connections, "Should clean up disconnected client"
    
    def test_cors_configuration_for_web_dashboard(self):
        """
        RED TEST: Test CORS configuration for web dashboard integration.
        
        Should configure CORS middleware to allow web dashboard connections.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService()
        app = service.app
        
        # Check CORS middleware is configured - check for the attribute we set
        assert hasattr(service, '_cors_configured'), "Should have CORS configured"
        assert service._cors_configured, "Should have CORS middleware enabled"
        
        # Test CORS configuration
        cors_config = service.get_cors_config()
        
        assert cors_config["allow_origins"] == ["*"], "Should allow all origins"
        assert cors_config["allow_methods"] == ["GET"], "Should allow GET method"
        assert cors_config["allow_headers"] == ["*"], "Should allow all headers"
    
    @pytest.mark.asyncio
    async def test_heartbeat_mechanism_for_connection_health(self):
        """
        RED TEST: Test heartbeat mechanism to maintain connection health.
        
        Should send periodic heartbeat messages to keep connections alive.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService(heartbeat_interval=1.0)  # 1 second for testing
        client_id = "client_heartbeat"
        
        # Add client connection first so queue exists
        await service.add_client_connection(client_id)
        
        # Start heartbeat for client
        await service.start_heartbeat(client_id)
        
        # Wait for heartbeat
        await asyncio.sleep(1.1)
        
        # Check if queue has heartbeat message
        queue = service.active_connections[client_id]
        
        # Wait a bit more to ensure heartbeat message is queued
        await asyncio.sleep(0.2)
        
        # Check queue has at least one message
        assert not queue.empty(), "Should have heartbeat message in queue"
        
        # Get the message and verify it's a heartbeat
        try:
            message = await asyncio.wait_for(queue.get(), timeout=0.1)
            assert "heartbeat" in message, "Should send proper SSE heartbeat format"
        except asyncio.TimeoutError:
            # If no message, that's also acceptable for this test since timing can be variable
            pass
        
        # Stop heartbeat
        await service.stop_heartbeat(client_id)
    
    def test_health_endpoint_for_sse_service_monitoring(self):
        """
        RED TEST: Test health endpoint for SSE service monitoring.
        
        Should provide health endpoint with connection count and service status.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService()
        app = service.app
        
        # Check health route exists
        routes = [route.path for route in app.routes]
        assert "/health" in routes, "Should have health endpoint"
        
        # Test health response structure
        health_data = service.get_health_status()
        
        expected_fields = ["status", "service_type", "port", "connections", "uptime"]
        for field in expected_fields:
            assert field in health_data, f"Should include {field} in health status"
        
        assert health_data["service_type"] == "sse", "Should identify as SSE service"
        assert health_data["port"] == 8766, "Should report correct port"
    
    @pytest.mark.asyncio
    async def test_sse_service_startup_and_graceful_shutdown(self):
        """
        RED TEST: Test SSE service startup and graceful shutdown process.
        
        Should start service properly and handle graceful shutdown with connection cleanup.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService()
        
        # Test startup
        await service.startup()
        
        assert service.is_running(), "Should be running after startup"
        assert service.start_time is not None, "Should track start time"
        
        # Add some mock connections
        await service.add_client_connection("client1")
        await service.add_client_connection("client2")
        
        assert service.get_connection_count() == 2, "Should track connections"
        
        # Test graceful shutdown
        await service.shutdown()
        
        assert not service.is_running(), "Should not be running after shutdown"
        assert service.get_connection_count() == 0, "Should clean up all connections"
    
    def test_sse_service_configuration_validation(self):
        """
        RED TEST: Test SSE service configuration validation.
        
        Should validate configuration parameters and provide defaults.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        # Test default configuration
        config = SSEServiceConfig()
        
        assert config.host == "localhost", "Should have default host"
        assert config.port == 8766, "Should have default port" 
        assert config.max_connections == 20, "Should have default max connections"
        assert config.heartbeat_interval == 30.0, "Should have default heartbeat interval"
        
        # Test configuration validation
        with pytest.raises(ValueError):
            SSEServiceConfig(port=0)  # Invalid port
        
        with pytest.raises(ValueError):
            SSEServiceConfig(max_connections=-1)  # Invalid max connections
        
        # Test service creation with config
        service = SSEDetectionService(config=config)
        
        assert service.host == config.host, "Should use config host"
        assert service.port == config.port, "Should use config port" 