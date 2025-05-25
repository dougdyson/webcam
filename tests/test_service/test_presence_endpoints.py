"""
Test suite for presence detection endpoints.
These endpoints serve as guard clauses for speaker verification and other applications.
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch
import aiohttp
from src.service.http_service import HTTPService
from src.detection.factory import create_detector


class TestPresenceSimpleEndpoint:
    """Test the /presence/simple endpoint for guard clause integration."""
    
    @pytest.fixture
    def mock_detection_service(self):
        """Mock detection service with predictable responses."""
        mock = Mock()
        mock.detect_person = Mock(return_value=(True, 0.85, 'multimodal'))
        return mock
    
    @pytest.fixture 
    def http_service(self, mock_detection_service):
        """HTTP service with mock detection for testing."""
        return HTTPService(detection_service=mock_detection_service)
    
    @pytest.mark.asyncio
    async def test_presence_simple_person_detected(self, http_service):
        """Test simple endpoint when person is detected."""
        # Configure mock for person present
        http_service.detection_service.detect_person.return_value = (True, 0.85, 'multimodal')
        
        response = await http_service.get_presence_simple()
        
        assert response['present'] is True
        assert response['confidence'] == 0.85
        assert 'timestamp' in response
        
        # Validate timestamp format (ISO 8601)
        timestamp = datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00'))
        assert timestamp.tzinfo is not None
        
    @pytest.mark.asyncio
    async def test_presence_simple_no_person_detected(self, http_service):
        """Test simple endpoint when no person is detected."""
        # Configure mock for no person
        http_service.detection_service.detect_person.return_value = (False, 0.3, 'multimodal')
        
        response = await http_service.get_presence_simple()
        
        assert response['present'] is False
        assert response['confidence'] == 0.3
        assert 'timestamp' in response
        
    @pytest.mark.asyncio
    async def test_presence_simple_confidence_threshold(self, http_service):
        """Test simple endpoint respects confidence threshold."""
        # Test with confidence below default threshold (0.5)
        http_service.detection_service.detect_person.return_value = (True, 0.4, 'multimodal')
        
        response = await http_service.get_presence_simple()
        
        # Should report not present due to low confidence
        assert response['present'] is False
        assert response['confidence'] == 0.4
        
    @pytest.mark.asyncio
    async def test_presence_simple_custom_confidence_threshold(self, http_service):
        """Test simple endpoint with custom confidence threshold."""
        # Set custom threshold
        http_service.confidence_threshold = 0.3
        http_service.detection_service.detect_person.return_value = (True, 0.35, 'multimodal')
        
        response = await http_service.get_presence_simple()
        
        # Should report present with custom lower threshold
        assert response['present'] is True
        assert response['confidence'] == 0.35
        
    @pytest.mark.asyncio 
    async def test_presence_simple_performance_timing(self, http_service):
        """Test simple endpoint meets <100ms performance requirement."""
        start_time = time.time()
        
        response = await http_service.get_presence_simple()
        
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        assert elapsed_time < 100, f"Response took {elapsed_time}ms, should be <100ms"
        assert 'present' in response
        
    @pytest.mark.asyncio
    async def test_presence_simple_error_handling(self, http_service):
        """Test simple endpoint handles detection errors gracefully."""
        # Configure mock to raise exception
        http_service.detection_service.detect_person.side_effect = RuntimeError("Camera error")
        
        response = await http_service.get_presence_simple()
        
        # Should return safe default for guard clause
        assert response['present'] is False
        assert response['confidence'] == 0.0
        assert 'error' in response
        
    @pytest.mark.asyncio
    async def test_presence_simple_no_detection_service(self):
        """Test simple endpoint with no detection service (graceful degradation)."""
        service = HTTPService()  # No detection service
        
        response = await service.get_presence_simple()
        
        # Should return safe default
        assert response['present'] is False
        assert response['confidence'] == 0.0
        assert response.get('error') == "Detection service unavailable"
        
    @pytest.mark.asyncio
    async def test_presence_simple_json_schema_validation(self, http_service):
        """Test simple endpoint returns valid JSON schema."""
        response = await http_service.get_presence_simple()
        
        # Required fields
        assert 'present' in response
        assert 'confidence' in response  
        assert 'timestamp' in response
        
        # Field types
        assert isinstance(response['present'], bool)
        assert isinstance(response['confidence'], (int, float))
        assert isinstance(response['timestamp'], str)
        
        # Value ranges
        assert 0.0 <= response['confidence'] <= 1.0


class TestPresenceDetailedEndpoint:
    """Test the /presence/detailed endpoint for comprehensive information."""
    
    @pytest.fixture
    def mock_multimodal_detection_service(self):
        """Mock multimodal detection service with detailed responses."""
        mock = Mock()
        mock.detect_person = Mock(return_value=(True, 0.85, 'multimodal'))
        mock.get_detection_info = Mock(return_value={
            'pose_confidence': 0.9,
            'face_confidence': 0.8,
            'detection_method': 'multimodal',
            'pose_keypoints_detected': 15,
            'face_landmarks_detected': 68
        })
        return mock
    
    @pytest.fixture
    def detailed_http_service(self, mock_multimodal_detection_service):
        """HTTP service with multimodal detection for detailed testing."""
        return HTTPService(detection_service=mock_multimodal_detection_service)
    
    @pytest.mark.asyncio
    async def test_presence_detailed_full_response(self, detailed_http_service):
        """Test detailed endpoint returns comprehensive information."""
        response = await detailed_http_service.get_presence_detailed()
        
        # Basic presence info
        assert response['present'] is True
        assert response['confidence'] == 0.85
        assert response['detection_type'] == 'multimodal'
        
        # Detailed multimodal info
        assert response['pose_confidence'] == 0.9
        assert response['face_confidence'] == 0.8
        
        # Metadata
        assert 'timestamp' in response
        assert 'processing_time_ms' in response
        assert isinstance(response['processing_time_ms'], (int, float))
        
    @pytest.mark.asyncio
    async def test_presence_detailed_pose_only_detection(self, detailed_http_service):
        """Test detailed endpoint with pose-only detection."""
        # Configure for pose-only detection
        detailed_http_service.detection_service.detect_person.return_value = (True, 0.7, 'pose')
        detailed_http_service.detection_service.get_detection_info.return_value = {
            'pose_confidence': 0.7,
            'face_confidence': 0.0,
            'detection_method': 'pose',
            'pose_keypoints_detected': 12,
            'face_landmarks_detected': 0
        }
        
        response = await detailed_http_service.get_presence_detailed()
        
        assert response['present'] is True
        assert response['detection_type'] == 'pose'
        assert response['pose_confidence'] == 0.7
        assert response['face_confidence'] == 0.0
        
    @pytest.mark.asyncio
    async def test_presence_detailed_face_only_detection(self, detailed_http_service):
        """Test detailed endpoint with face-only detection."""
        # Configure for face-only detection
        detailed_http_service.detection_service.detect_person.return_value = (True, 0.75, 'face')
        detailed_http_service.detection_service.get_detection_info.return_value = {
            'pose_confidence': 0.0,
            'face_confidence': 0.75,
            'detection_method': 'face',
            'pose_keypoints_detected': 0,
            'face_landmarks_detected': 68
        }
        
        response = await detailed_http_service.get_presence_detailed()
        
        assert response['present'] is True
        assert response['detection_type'] == 'face'
        assert response['pose_confidence'] == 0.0
        assert response['face_confidence'] == 0.75
        
    @pytest.mark.asyncio
    async def test_presence_detailed_processing_time_tracking(self, detailed_http_service):
        """Test detailed endpoint tracks processing time accurately."""
        # Add delay to detection
        def slow_detection(*args, **kwargs):
            time.sleep(0.05)  # 50ms delay
            return (True, 0.8, 'multimodal')
            
        detailed_http_service.detection_service.detect_person = slow_detection
        
        response = await detailed_http_service.get_presence_detailed()
        
        # Should track the processing time
        assert response['processing_time_ms'] >= 50
        assert response['processing_time_ms'] < 200  # Reasonable upper bound
        
    @pytest.mark.asyncio
    async def test_presence_detailed_error_with_partial_info(self, detailed_http_service):
        """Test detailed endpoint handles partial detection errors."""
        # Detection works but get_detection_info fails
        detailed_http_service.detection_service.get_detection_info.side_effect = Exception("Info unavailable")
        
        response = await detailed_http_service.get_presence_detailed()
        
        # Should still return basic detection info
        assert response['present'] is True
        assert response['confidence'] == 0.85
        assert response['detection_type'] == 'multimodal'
        
        # Detailed info should have safe defaults
        assert response['pose_confidence'] == 0.0
        assert response['face_confidence'] == 0.0
        
    @pytest.mark.asyncio
    async def test_presence_detailed_json_schema_validation(self, detailed_http_service):
        """Test detailed endpoint returns valid extended JSON schema."""
        response = await detailed_http_service.get_presence_detailed()
        
        # Required fields from simple endpoint
        assert 'present' in response
        assert 'confidence' in response
        assert 'timestamp' in response
        
        # Additional detailed fields
        assert 'detection_type' in response
        assert 'pose_confidence' in response
        assert 'face_confidence' in response
        assert 'processing_time_ms' in response
        
        # Field types
        assert isinstance(response['detection_type'], str)
        assert isinstance(response['pose_confidence'], (int, float))
        assert isinstance(response['face_confidence'], (int, float))
        assert isinstance(response['processing_time_ms'], (int, float))
        
        # Value ranges
        assert 0.0 <= response['pose_confidence'] <= 1.0
        assert 0.0 <= response['face_confidence'] <= 1.0
        assert response['processing_time_ms'] >= 0


class TestPresenceEndpointConfiguration:
    """Test presence endpoint configuration and customization."""
    
    @pytest.mark.asyncio
    async def test_configurable_confidence_thresholds(self):
        """Test endpoints respect configurable confidence thresholds."""
        config = {
            'confidence_threshold': 0.7,
            'pose_threshold': 0.8, 
            'face_threshold': 0.6
        }
        
        mock_detector = Mock()
        mock_detector.detect_person = Mock(return_value=(True, 0.65, 'multimodal'))
        
        service = HTTPService(detection_service=mock_detector, config=config)
        
        response = await service.get_presence_simple()
        
        # Should be False due to confidence below threshold
        assert response['present'] is False
        assert response['confidence'] == 0.65
        
    @pytest.mark.asyncio 
    async def test_endpoint_response_caching(self):
        """Test endpoint implements response caching for performance."""
        mock_detector = Mock()
        mock_detector.detect_person = Mock(return_value=(True, 0.8, 'multimodal'))
        
        service = HTTPService(detection_service=mock_detector, config={'cache_duration_ms': 100})
        
        # First request
        response1 = await service.get_presence_simple()
        timestamp1 = response1['timestamp']
        
        # Second request immediately (should be cached)
        response2 = await service.get_presence_simple()
        timestamp2 = response2['timestamp']
        
        # Should be identical (cached)
        assert timestamp1 == timestamp2
        assert mock_detector.detect_person.call_count == 1
        
        # Wait for cache expiry
        await asyncio.sleep(0.15)
        
        # Third request (cache expired)
        response3 = await service.get_presence_simple()
        
        # Should be new detection
        assert mock_detector.detect_person.call_count == 2
        
    @pytest.mark.asyncio
    async def test_endpoint_timeout_configuration(self):
        """Test endpoints respect timeout configuration."""
        mock_detector = Mock()
        
        def slow_detection(*args, **kwargs):
            time.sleep(0.2)  # 200ms delay
            return (True, 0.8, 'multimodal')
            
        mock_detector.detect_person = slow_detection
        
        service = HTTPService(
            detection_service=mock_detector, 
            config={'detection_timeout_ms': 100}  # 100ms timeout
        )
        
        response = await service.get_presence_simple()
        
        # Should timeout and return safe default
        assert response['present'] is False
        assert response['confidence'] == 0.0
        assert 'timeout' in response.get('error', '')


class TestPresenceEndpointPerformance:
    """Test presence endpoint performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test endpoints handle concurrent requests efficiently."""
        mock_detector = Mock()
        mock_detector.detect_person = Mock(return_value=(True, 0.8, 'multimodal'))
        
        service = HTTPService(detection_service=mock_detector)
        
        # Launch multiple concurrent requests
        tasks = [service.get_presence_simple() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(responses) == 10
        assert all(response['present'] is True for response in responses)
        assert all(response['confidence'] == 0.8 for response in responses)
        
    @pytest.mark.asyncio
    async def test_request_rate_limiting_behavior(self):
        """Test endpoints implement proper rate limiting."""
        mock_detector = Mock()
        mock_detector.detect_person = Mock(return_value=(True, 0.8, 'multimodal'))
        
        service = HTTPService(
            detection_service=mock_detector,
            config={'rate_limit_per_second': 5}
        )
        
        # Make rapid requests
        start_time = time.time()
        responses = []
        
        for _ in range(10):
            response = await service.get_presence_simple()
            responses.append(response)
            
        elapsed_time = time.time() - start_time
        
        # Should take at least 2 seconds for 10 requests at 5/sec rate limit
        assert elapsed_time >= 1.8  # Allow some tolerance
        assert len(responses) == 10
        
    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self):
        """Test endpoints collect performance metrics."""
        mock_detector = Mock()
        mock_detector.detect_person = Mock(return_value=(True, 0.8, 'multimodal'))
        
        service = HTTPService(detection_service=mock_detector)
        
        # Make several requests
        for _ in range(5):
            await service.get_presence_simple()
            
        metrics = service.get_performance_metrics()
        
        assert metrics['total_requests'] == 5
        assert metrics['avg_response_time_ms'] > 0
        assert metrics['requests_per_second'] > 0
        assert 'error_rate' in metrics
        
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test endpoints maintain stable memory usage under load."""
        import tracemalloc
        
        mock_detector = Mock()
        mock_detector.detect_person = Mock(return_value=(True, 0.8, 'multimodal'))
        
        service = HTTPService(detection_service=mock_detector)
        
        tracemalloc.start()
        
        # Baseline memory
        await service.get_presence_simple()
        current, peak = tracemalloc.get_traced_memory()
        baseline_memory = current
        
        # Make many requests
        for _ in range(100):
            await service.get_presence_simple()
            
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory should not grow significantly
        memory_growth = current - baseline_memory
        assert memory_growth < 1024 * 1024  # Less than 1MB growth
        
        
class TestPresenceEndpointIntegration:
    """Test presence endpoints with real detection system integration."""
    
    @pytest.fixture
    def real_multimodal_detector(self):
        """Real multimodal detector for integration tests."""
        config = {
            'detector_type': 'multimodal',
            'pose_weight': 0.6,
            'face_weight': 0.4,
            'confidence_threshold': 0.5
        }
        return create_detector('multimodal', config)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_integration_with_real_detector(self, real_multimodal_detector):
        """Test endpoints work with real multimodal detector."""
        service = HTTPService(detection_service=real_multimodal_detector)
        
        # Test simple endpoint
        simple_response = await service.get_presence_simple()
        assert 'present' in simple_response
        assert 'confidence' in simple_response
        assert 'timestamp' in simple_response
        
        # Test detailed endpoint  
        detailed_response = await service.get_presence_detailed()
        assert 'detection_type' in detailed_response
        assert 'pose_confidence' in detailed_response
        assert 'face_confidence' in detailed_response
        
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_speaker_verification_guard_clause_workflow(self, real_multimodal_detector):
        """Test complete workflow for speaker verification guard clause."""
        service = HTTPService(detection_service=real_multimodal_detector)
        
        # Simulate speaker verification system checking presence
        presence_check = await service.get_presence_simple()
        
        # Guard clause logic
        if presence_check['present'] and presence_check['confidence'] >= 0.5:
            # Would proceed with speaker verification
            verification_authorized = True
        else:
            # Would skip verification or use fallback
            verification_authorized = False
            
        # Should have a definitive result
        assert isinstance(verification_authorized, bool)
        
        # Response should be fast enough for real-time use
        start_time = time.time()
        await service.get_presence_simple()
        response_time = (time.time() - start_time) * 1000
        
        assert response_time < 100  # <100ms for guard clause 