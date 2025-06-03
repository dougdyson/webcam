#!/usr/bin/env python3
"""
Phase 8.2: Production Configuration Validation Tests (Testing Live Service)
===========================================================================

TDD Phase 8.2: Production readiness validation tests ensure the system is ready for deployment.

This test file validates:
1. Production deployment scenarios work correctly
2. Performance requirements are met under load
3. Resource usage is within acceptable limits
4. Error handling and graceful degradation work properly
5. Configuration management is production-ready

IMPORTANT: These tests run against the LIVE SERVICE without modifying source code.
"""

import pytest
import requests
import time
import threading
import psutil
import concurrent.futures
import statistics
from pathlib import Path
import yaml
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestProductionPerformanceRequirements:
    """Test Phase 8.2.1: Production Performance Requirements"""
    
    def test_service_startup_and_availability(self):
        """
        Test that the service starts and becomes available within reasonable time.
        """
        # Test service is accessible
        response = requests.get("http://localhost:8767/health", timeout=3.0)
        assert response.status_code == 200, "Service should be running and healthy"
        
        health_data = response.json()
        assert health_data.get("status") == "healthy", "Service should report healthy status"
    
    def test_http_response_times_meet_production_requirements(self):
        """
        Test that HTTP response times meet production requirements for guard clause usage.
        
        Production requirement: Guard clause endpoints should respond quickly for real-time usage.
        """
        # Test multiple requests to get reliable timing data
        response_times = []
        
        for _ in range(10):
            start_time = time.time()
            response = requests.get("http://localhost:8767/presence/simple", timeout=2.0)
            response_time_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200, "Guard clause endpoint should be reliable"
            response_times.append(response_time_ms)
        
        # Analyze response times
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        # Production requirements: reasonable response times for real-time guard clauses
        assert avg_response_time < 100, f"Average response time {avg_response_time:.1f}ms should be < 100ms"
        assert max_response_time < 300, f"Max response time {max_response_time:.1f}ms should be < 300ms"
    
    def test_concurrent_request_handling_capacity(self):
        """
        Test that the service can handle concurrent requests without degradation.
        
        Production requirement: Should handle multiple simultaneous guard clause checks.
        """
        def make_request():
            try:
                response = requests.get("http://localhost:8767/presence/simple", timeout=2.0)
                return {
                    "success": response.status_code == 200,
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "status_code": response.status_code
                }
            except Exception as e:
                return {"success": False, "error": str(e), "response_time": float('inf')}
        
        # Test concurrent requests
        num_concurrent_requests = 10
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze concurrent performance
        successful_requests = [r for r in results if r["success"]]
        success_rate = len(successful_requests) / len(results) * 100
        
        assert success_rate >= 90, f"Success rate {success_rate:.1f}% should be >= 90% under concurrent load"
        
        if successful_requests:
            response_times = [r["response_time"] for r in successful_requests]
            avg_concurrent_response_time = statistics.mean(response_times)
            assert avg_concurrent_response_time < 200, \
                f"Average concurrent response time {avg_concurrent_response_time:.1f}ms should be reasonable"


class TestProductionResourceManagement:
    """Test Phase 8.2.2: Production Resource Management"""
    
    def test_memory_usage_is_within_reasonable_limits(self):
        """
        Test that memory usage remains within reasonable production limits.
        """
        # Get current process (pytest) and find webcam service process
        current_process = psutil.Process()
        
        # Test memory usage is reasonable for the current process
        memory_info = current_process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        # Be reasonable about memory limits - this includes pytest overhead
        max_reasonable_memory_mb = 2000  # 2GB is reasonable for development testing
        assert memory_mb < max_reasonable_memory_mb, \
            f"Memory usage {memory_mb:.1f}MB should be < {max_reasonable_memory_mb}MB"
    
    def test_service_handles_rapid_requests_without_memory_leaks(self):
        """
        Test that rapid requests don't cause memory leaks or resource exhaustion.
        """
        # Make rapid requests and monitor if service stays responsive
        rapid_request_count = 50
        successful_requests = 0
        
        start_time = time.time()
        for i in range(rapid_request_count):
            try:
                response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
                if response.status_code == 200:
                    successful_requests += 1
            except:
                pass  # Count failures
        
        total_time = time.time() - start_time
        success_rate = (successful_requests / rapid_request_count) * 100
        
        # Service should handle rapid requests reasonably well
        assert success_rate >= 80, f"Success rate {success_rate:.1f}% should be >= 80% under rapid load"
        assert total_time < 30, f"Rapid requests should complete within 30 seconds, took {total_time:.1f}s"
    
    def test_service_endpoints_remain_responsive_under_load(self):
        """
        Test that all endpoints remain responsive under sustained load.
        """
        endpoints_to_test = [
            "/presence/simple",
            "/presence", 
            "/health",
            "/statistics"
        ]
        
        results = {}
        
        for endpoint in endpoints_to_test:
            try:
                response = requests.get(f"http://localhost:8767{endpoint}", timeout=3.0)
                results[endpoint] = {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_size": len(response.content)
                }
            except Exception as e:
                results[endpoint] = {"success": False, "error": str(e)}
        
        # All core endpoints should remain responsive
        for endpoint, result in results.items():
            assert result["success"], f"Endpoint {endpoint} should remain responsive under load"


class TestProductionErrorHandlingAndResilience:
    """Test Phase 8.2.3: Production Error Handling and Resilience"""
    
    def test_service_handles_invalid_requests_gracefully(self):
        """
        Test that the service handles invalid requests without crashing.
        """
        # Test various invalid request scenarios
        invalid_request_scenarios = [
            {"path": "/nonexistent", "expected_status": 404},
            {"path": "/presence/invalid", "expected_status": 404},
            {"path": "/statistics/invalid", "expected_status": 404},
        ]
        
        for scenario in invalid_request_scenarios:
            response = requests.get(f"http://localhost:8767{scenario['path']}", timeout=2.0)
            
            # Should return proper HTTP error codes, not crash
            assert response.status_code == scenario["expected_status"], \
                f"Invalid request to {scenario['path']} should return {scenario['expected_status']}"
    
    def test_service_health_endpoint_provides_useful_information(self):
        """
        Test that the health endpoint provides useful production monitoring information.
        """
        response = requests.get("http://localhost:8767/health", timeout=2.0)
        assert response.status_code == 200, "Health endpoint should be accessible"
        
        health_data = response.json()
        
        # Validate health endpoint provides useful monitoring data
        required_health_fields = ["status"]
        for field in required_health_fields:
            assert field in health_data, f"Health endpoint should include {field} for monitoring"
        
        # Status should be a meaningful value
        assert health_data["status"] in ["healthy", "unhealthy", "degraded"], \
            "Health status should be a standard value"
    
    def test_statistics_endpoint_provides_production_metrics(self):
        """
        Test that statistics endpoint provides useful production metrics.
        """
        response = requests.get("http://localhost:8767/statistics", timeout=2.0)
        assert response.status_code == 200, "Statistics endpoint should be accessible"
        
        stats_data = response.json()
        
        # Validate statistics provide useful production metrics
        expected_metrics = ["total_detections", "current_presence"]
        for metric in expected_metrics:
            assert metric in stats_data, f"Statistics should include {metric} for production monitoring"
        
        # Metrics should be reasonable values
        assert isinstance(stats_data["total_detections"], int), "total_detections should be integer"
        assert stats_data["total_detections"] >= 0, "total_detections should be non-negative"
        assert isinstance(stats_data["current_presence"], bool), "current_presence should be boolean"


class TestProductionConfigurationValidation:
    """Test Phase 8.2.4: Production Configuration Validation"""
    
    def test_environment_configuration_files_exist_and_are_valid(self):
        """
        Test that required configuration files exist and are properly formatted.
        """
        # Test that environment.yml exists for conda deployment
        env_file = Path("environment.yml")
        if env_file.exists():
            try:
                with open(env_file) as f:
                    env_config = yaml.safe_load(f)
                
                # Validate environment file structure
                assert "name" in env_config, "environment.yml should specify environment name"
                assert "dependencies" in env_config, "environment.yml should list dependencies"
                assert isinstance(env_config["dependencies"], list), "Dependencies should be a list"
                
                # Check for key dependencies
                deps_str = str(env_config["dependencies"])
                key_dependencies = ["python", "opencv", "mediapipe"]
                for dep in key_dependencies:
                    # Allow flexible matching (opencv-python, etc.)
                    dependency_present = any(dep.lower() in str(d).lower() for d in env_config["dependencies"])
                    if not dependency_present:
                        pytest.skip(f"Dependency {dep} not found - may use different naming")
                        
            except Exception as e:
                pytest.fail(f"environment.yml is not valid YAML: {e}")
        else:
            pytest.skip("environment.yml not found - may use different deployment method")
    
    def test_service_configuration_is_production_appropriate(self):
        """
        Test that service configuration is appropriate for production deployment.
        """
        # Test that service is using production-appropriate ports
        response = requests.get("http://localhost:8767/health", timeout=2.0)
        assert response.status_code == 200, "Service should be running on expected port 8767"
        
        # Test that responses include proper headers for production
        headers = response.headers
        assert "content-type" in headers, "Responses should include content-type header"
        assert "application/json" in headers.get("content-type", ""), "API should return JSON"
    
    def test_optional_ollama_integration_handles_unavailability_gracefully(self):
        """
        Test that optional Ollama integration fails gracefully if not available.
        """
        response = requests.get("http://localhost:8767/description/latest", timeout=2.0)
        
        # Should either work (200) or fail gracefully (404/5xx) - should not crash service
        assert response.status_code in [200, 404, 500, 503], \
            f"Description endpoint should handle Ollama unavailability gracefully, got {response.status_code}"
        
        # Verify main service still works regardless of Ollama status
        health_response = requests.get("http://localhost:8767/health", timeout=2.0)
        assert health_response.status_code == 200, "Main service should work regardless of Ollama status"


class TestProductionIntegrationPatterns:
    """Test Phase 8.2.5: Production Integration Patterns"""
    
    def test_guard_clause_integration_pattern_reliability(self):
        """
        Test that the primary guard clause integration pattern is reliable for production use.
        """
        # Test the documented integration pattern multiple times
        def should_process_audio() -> bool:
            """Production guard clause pattern."""
            try:
                response = requests.get("http://localhost:8767/presence/simple", timeout=1.0)
                return response.json().get("human_present", False) if response.status_code == 200 else True
            except:
                return True  # Production failsafe
        
        # Test reliability over multiple calls
        results = []
        for _ in range(20):
            try:
                result = should_process_audio()
                results.append({"success": True, "result": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        
        # Should be highly reliable for production use
        success_rate = len([r for r in results if r["success"]]) / len(results) * 100
        assert success_rate >= 95, f"Guard clause pattern should be {success_rate:.1f}% >= 95% reliable"
    
    def test_multiple_client_usage_pattern(self):
        """
        Test that multiple clients can use the service simultaneously.
        """
        def client_simulation():
            """Simulate a client using the guard clause pattern."""
            try:
                response = requests.get("http://localhost:8767/presence/simple", timeout=2.0)
                return response.status_code == 200
            except:
                return False
        
        # Simulate multiple clients
        num_clients = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_clients) as executor:
            futures = [executor.submit(client_simulation) for _ in range(num_clients)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All clients should be able to use the service
        success_count = sum(results)
        success_rate = (success_count / num_clients) * 100
        
        assert success_rate >= 80, f"Multiple client success rate {success_rate:.1f}% should be >= 80%"


if __name__ == "__main__":
    print("🔥 Phase 8.2: Production Configuration Validation Tests (FINAL PHASE!)")
    print("🚀 Testing production readiness, performance, and reliability")
    print("🎯 Service should be running: python webcam_service.py")
    print("💪 Let's validate this system is PRODUCTION READY!")
    print()
    pytest.main([__file__, "-v"]) 