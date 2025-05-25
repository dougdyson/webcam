"""
Test SSE (Server-Sent Events) service configuration and health monitoring.

Testing advanced configuration features and health monitoring for SSE service.
Following TDD methodology: Red → Green → Refactor.

Phase 15.3: SSE Service Configuration and Health
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

import uvicorn
import httpx
from fastapi import FastAPI


class TestSSEServiceConfigurationAndHealth:
    """Test SSE service advanced configuration and health monitoring features."""
    
    def test_sse_service_config_enhancement_with_advanced_features(self):
        """
        RED TEST: Test SSEServiceConfig enhancement with advanced configuration features.
        
        Should support advanced configuration like connection limits, timeout settings,
        and service documentation features.
        """
        from src.service.sse_service import SSEServiceConfig
        
        # Test advanced configuration options
        config = SSEServiceConfig(
            host="0.0.0.0",
            port=8766,
            max_connections=50,
            connection_timeout=120.0,
            heartbeat_interval=45.0,
            enable_detailed_logging=True,
            service_name="GestureSSEService",
            service_version="1.0.0"
        )
        
        # Verify all advanced options are set
        assert config.host == "0.0.0.0", "Should support custom host"
        assert config.max_connections == 50, "Should support custom connection limit"
        assert config.connection_timeout == 120.0, "Should support custom timeout"
        assert config.enable_detailed_logging is True, "Should support logging configuration"
        assert config.service_name == "GestureSSEService", "Should support service naming"
        assert config.service_version == "1.0.0", "Should support version tracking"
        
        # Test configuration validation for edge cases
        with pytest.raises(ValueError):
            SSEServiceConfig(connection_timeout=-1.0)  # Invalid timeout
        
        with pytest.raises(ValueError):
            SSEServiceConfig(max_connections=0)  # Invalid connection limit
    
    def test_detailed_health_endpoint_with_sse_metrics(self):
        """
        RED TEST: Test enhanced health endpoint with detailed SSE service metrics.
        
        Should provide comprehensive health information including connection statistics,
        uptime, and service performance metrics.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        config = SSEServiceConfig(
            service_name="TestSSEService",
            service_version="1.0.0",
            enable_detailed_logging=True
        )
        service = SSEDetectionService(config=config)
        
        # Mock some service activity - use correct attribute name
        service.start_time = datetime.now() - timedelta(minutes=30)
        service._total_connections = 15
        service._total_events_sent = 250
        service._total_heartbeats_sent = 45
        
        # Get enhanced health status
        health_data = service.get_detailed_health_status()
        
        # Verify comprehensive health information
        expected_fields = [
            "status", "service_type", "service_name", "service_version",
            "port", "host", "uptime_seconds", "active_connections", 
            "total_connections", "max_connections", "total_events_sent",
            "total_heartbeats_sent", "events_per_minute", "connection_timeout",
            "heartbeat_interval", "memory_usage_mb", "last_activity"
        ]
        
        for field in expected_fields:
            assert field in health_data, f"Should include {field} in detailed health status"
        
        # Verify calculated metrics
        assert health_data["service_name"] == "TestSSEService", "Should report service name"
        assert health_data["service_version"] == "1.0.0", "Should report service version"
        assert health_data["total_connections"] == 15, "Should track total connections"
        assert health_data["total_events_sent"] == 250, "Should track events sent"
        assert health_data["uptime_seconds"] >= 1800, "Should calculate uptime correctly"
    
    @pytest.mark.asyncio
    async def test_service_startup_with_configuration_validation(self):
        """
        RED TEST: Test service startup with comprehensive configuration validation.
        
        Should validate all configuration parameters during startup and provide
        clear error messages for invalid configurations.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        # Test valid configuration startup
        valid_config = SSEServiceConfig(
            host="localhost",
            port=8766,
            max_connections=25,
            heartbeat_interval=30.0
        )
        service = SSEDetectionService(config=valid_config)
        
        # Test startup validation
        startup_result = await service.startup_with_validation()
        
        assert startup_result["success"] is True, "Should start successfully with valid config"
        assert startup_result["validation_errors"] == [], "Should have no validation errors"
        assert service.is_running(), "Should be running after successful startup"
        
        # Test configuration validation - some parameters validated in __post_init__
        with pytest.raises(ValueError, match="max_connections must be positive"):
            SSEServiceConfig(max_connections=0)
        
        with pytest.raises(ValueError, match="heartbeat_interval must be positive"):
            SSEServiceConfig(heartbeat_interval=0)
        
        # Port validation happens in startup_with_validation
        invalid_port_config = SSEServiceConfig(port=-1)  # This should succeed
        invalid_service = SSEDetectionService(config=invalid_port_config)
        
        # But startup validation should catch the invalid port
        startup_result = await invalid_service.startup_with_validation()
        assert startup_result["success"] is False, "Should fail startup with invalid port"
        assert "Port must be between 1024 and 65535" in startup_result["validation_errors"], "Should report port error"
        
        # Cleanup
        await service.shutdown()
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_event_cleanup(self):
        """
        RED TEST: Test graceful shutdown with proper event cleanup and client notification.
        
        Should notify all connected clients before shutdown and clean up all resources.
        """
        from src.service.sse_service import SSEDetectionService
        
        service = SSEDetectionService()
        await service.startup()
        
        # Add multiple clients
        client_ids = ["client1", "client2", "client3"]
        for client_id in client_ids:
            await service.add_client_connection(client_id)
        
        assert service.get_connection_count() == 3, "Should have 3 active connections"
        
        # Test graceful shutdown with client notification
        shutdown_result = await service.graceful_shutdown_with_cleanup()
        
        # Verify shutdown notification was sent to clients
        assert shutdown_result["clients_notified"] == 3, "Should notify all clients"
        assert shutdown_result["connections_cleaned"] == 3, "Should clean up all connections"
        assert shutdown_result["resources_freed"] is True, "Should free all resources"
        
        # Verify service state after shutdown
        assert not service.is_running(), "Should not be running after shutdown"
        assert service.get_connection_count() == 0, "Should have no active connections"
        
        # Verify cleanup completed
        cleanup_status = service.get_cleanup_status()
        assert cleanup_status["event_queues_cleared"] is True, "Should clear all event queues"
        assert cleanup_status["heartbeat_tasks_stopped"] is True, "Should stop heartbeat tasks"
        assert cleanup_status["memory_freed"] is True, "Should free memory resources"
    
    def test_service_manager_compatibility_integration(self):
        """
        RED TEST: Test integration with existing service patterns (ServiceManager compatibility).
        
        Should integrate seamlessly with existing service manager patterns and
        follow established service lifecycle conventions.
        """
        from src.service.sse_service import SSEDetectionService
        from src.service.events import EventPublisher  # Existing service pattern
        
        # Test service manager registration pattern
        service = SSEDetectionService()
        
        # Should implement standard service interface
        assert hasattr(service, 'startup'), "Should have startup method"
        assert hasattr(service, 'shutdown'), "Should have shutdown method"
        assert hasattr(service, 'is_running'), "Should have running status method"
        assert hasattr(service, 'get_health_status'), "Should have health status method"
        
        # Test service manager compatibility
        service_info = service.get_service_info()
        
        expected_info_fields = [
            "service_type", "service_name", "port", "version",
            "capabilities", "dependencies", "status"
        ]
        
        for field in expected_info_fields:
            assert field in service_info, f"Should include {field} in service info"
        
        # Test EventPublisher integration compatibility
        event_publisher = EventPublisher()
        integration_result = service.integrate_with_event_publisher(event_publisher)
        
        assert integration_result["success"] is True, "Should integrate with EventPublisher"
        assert integration_result["subscription_count"] > 0, "Should subscribe to relevant events"
    
    def test_detailed_logging_and_monitoring_capabilities(self):
        """
        RED TEST: Test detailed logging and monitoring capabilities for SSE operations.
        
        Should provide comprehensive logging for debugging and monitoring SSE service operations.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        # Create service with detailed logging enabled
        config = SSEServiceConfig(enable_detailed_logging=True)
        service = SSEDetectionService(config=config)
        
        # Test logging configuration
        assert service.is_detailed_logging_enabled(), "Should enable detailed logging"
        
        # Test monitoring capabilities
        monitoring_data = service.get_monitoring_data()
        
        expected_monitoring_fields = [
            "connection_events", "event_stream_stats", "error_counts",
            "performance_metrics", "client_activity", "heartbeat_stats"
        ]
        
        for field in expected_monitoring_fields:
            assert field in monitoring_data, f"Should include {field} in monitoring data"
        
        # Test log message formatting
        log_entry = service.format_log_entry("client_connected", {"client_id": "test123"})
        
        assert "timestamp" in log_entry, "Should include timestamp in log entry"
        assert "event_type" in log_entry, "Should include event type"
        assert "client_id" in log_entry["data"], "Should include client data"
        assert log_entry["service"] == "sse_service", "Should identify service source"
    
    def test_sse_service_documentation_and_configuration_validation(self):
        """
        RED TEST: Test SSE service documentation features and configuration validation.
        
        Should provide comprehensive documentation features and validate all
        configuration parameters with helpful error messages.
        """
        from src.service.sse_service import SSEDetectionService, SSEServiceConfig
        
        # Test configuration documentation
        config_docs = SSEServiceConfig.get_configuration_documentation()
        
        expected_doc_sections = [
            "parameters", "examples", "validation_rules", "default_values",
            "performance_considerations", "security_notes"
        ]
        
        for section in expected_doc_sections:
            assert section in config_docs, f"Should include {section} in documentation"
        
        # Test configuration validation with detailed messages
        validation_results = SSEServiceConfig.validate_configuration({
            "host": "localhost",
            "port": 8766,
            "max_connections": 25,
            "heartbeat_interval": 30.0,
            "invalid_param": "should_be_ignored"
        })
        
        assert validation_results["is_valid"] is True, "Should validate correct configuration"
        assert any("invalid_param" in warning for warning in validation_results["warnings"]), "Should warn about unknown parameters"
        
        # Test validation error messages
        invalid_validation = SSEServiceConfig.validate_configuration({
            "port": -1,
            "max_connections": 0,
            "heartbeat_interval": -5.0
        })
        
        assert invalid_validation["is_valid"] is False, "Should reject invalid configuration"
        assert len(invalid_validation["errors"]) >= 3, "Should report multiple errors"
        
        # Verify error messages are helpful
        error_messages = invalid_validation["errors"]
        assert any("port" in error.lower() for error in error_messages), "Should mention port error"
        assert any("connections" in error.lower() for error in error_messages), "Should mention connections error"
        assert any("heartbeat" in error.lower() for error in error_messages), "Should mention heartbeat error" 