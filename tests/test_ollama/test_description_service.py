"""
Tests for description service core functionality.

Phase 3.1 of TDD Ollama Description Endpoint Feature.
Following TDD methodology - RED phase: Write failing tests first.

This module tests the DescriptionService class which provides:
- Async snapshot description processing using Ollama
- Description caching with TTL
- Integration with existing service patterns
- Error handling and timeouts
"""
import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# This import will fail initially - that's the RED phase!
try:
    from src.ollama.description_service import (
        DescriptionService,
        DescriptionServiceConfig,
        DescriptionResult
    )
    from src.ollama.client import OllamaClient
    from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
    from src.ollama.image_processing import OllamaImageProcessor
except ImportError:
    # Expected to fail during RED phase
    DescriptionService = None
    DescriptionServiceConfig = None
    DescriptionResult = None
    OllamaClient = None
    Snapshot = None
    SnapshotMetadata = None
    OllamaImageProcessor = None


class TestDescriptionServiceInitialization:
    """RED TESTS: Test DescriptionService.__init__() with dependencies."""
    
    def test_description_service_init_with_dependencies(self):
        """
        RED TEST: DescriptionService should initialize with required dependencies.
        
        This test will fail because DescriptionService doesn't exist yet.
        Expected behavior:
        - Should accept OllamaClient, ImageProcessor dependencies
        - Should accept optional configuration
        - Should initialize internal cache and async processing components
        """
        # Mock dependencies
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        
        config = DescriptionServiceConfig(
            cache_ttl_seconds=300,
            max_concurrent_requests=2,
            timeout_seconds=30.0
        )
        
        # Create service with dependencies
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Verify initialization
        assert service.ollama_client == mock_ollama_client
        assert service.image_processor == mock_image_processor
        assert service.config == config
        assert service.cache is not None
        assert service._processing_semaphore is not None
        assert service._processing_semaphore._value == config.max_concurrent_requests
        
    def test_description_service_init_with_default_config(self):
        """
        RED TEST: DescriptionService should use default config when none provided.
        """
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor
        )
        
        # Should have default configuration
        assert service.config is not None
        assert isinstance(service.config, DescriptionServiceConfig)
        assert service.config.cache_ttl_seconds > 0
        assert service.config.max_concurrent_requests > 0
        assert service.config.timeout_seconds > 0
        
    def test_description_service_follows_existing_service_patterns(self):
        """
        RED TEST: DescriptionService should follow patterns from HTTP/SSE services.
        
        Expected patterns:
        - Configuration-driven initialization
        - Dependency injection for testability
        - Proper resource management
        - Service lifecycle methods (start/stop if needed)
        """
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor
        )
        
        # Should have configuration validation
        assert hasattr(service, 'config')
        
        # Should have proper dependency management
        assert hasattr(service, 'ollama_client')
        assert hasattr(service, 'image_processor')
        
        # Should have async processing support
        assert hasattr(service, 'describe_snapshot')
        assert asyncio.iscoroutinefunction(service.describe_snapshot)


class TestDescriptionServiceAsyncProcessing:
    """RED TESTS: Test describe_snapshot() async method."""
    
    @pytest.mark.asyncio
    async def test_describe_snapshot_async_method_signature(self):
        """
        RED TEST: describe_snapshot() should be an async method with proper signature.
        
        This test will fail because the method doesn't exist yet.
        Expected behavior:
        - Should accept Snapshot parameter
        - Should return DescriptionResult
        - Should be async (coroutine)
        """
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor
        )
        
        # Create test snapshot
        frame = np.zeros((640, 480, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.85,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Should be callable as async method
        result = await service.describe_snapshot(snapshot)
        
        # Should return DescriptionResult
        assert isinstance(result, DescriptionResult)
        assert hasattr(result, 'description')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'processing_time_ms')
        
    @pytest.mark.asyncio
    async def test_describe_snapshot_calls_ollama_client(self):
        """
        RED TEST: describe_snapshot() should use OllamaClient for description.
        """
        # Mock successful Ollama response (returns string, not dict)
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_ollama_client.describe_image.return_value = "Person standing at desk, typing on laptop"
        
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        mock_image_processor.process_webcam_frame.return_value = "base64_encoded_image"
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor
        )
        
        # Create test snapshot
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.9,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        result = await service.describe_snapshot(snapshot)
        
        # Verify Ollama client was called
        mock_image_processor.process_webcam_frame.assert_called_once_with(frame)
        mock_ollama_client.describe_image.assert_called_once_with("base64_encoded_image")
        
        # Verify result content
        assert result.description == "Person standing at desk, typing on laptop"
        assert result.confidence == 0.9  # Default confidence
        assert result.timestamp is not None
        assert result.processing_time_ms > 0
        
    @pytest.mark.asyncio
    async def test_describe_snapshot_error_handling_and_timeouts(self):
        """
        RED TEST: describe_snapshot() should handle errors and timeouts properly.
        """
        # Mock Ollama client that raises timeout
        mock_ollama_client = AsyncMock(spec=OllamaClient)
        mock_ollama_client.describe_image.side_effect = asyncio.TimeoutError("Ollama timeout")
        
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        mock_image_processor.process_webcam_frame.return_value = "base64_encoded_image"
        
        config = DescriptionServiceConfig(
            timeout_seconds=5.0,
            enable_fallback_descriptions=False  # Use Error: prefix instead of fallback descriptions
        )
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Create test snapshot
        frame = np.zeros((320, 240, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Should handle timeout gracefully
        result = await service.describe_snapshot(snapshot)
        
        # Should return error result, not raise exception
        assert isinstance(result, DescriptionResult)
        assert result.description.startswith("Error:")
        assert result.confidence == 0.0
        assert result.error is not None
        assert "timeout" in result.error.lower()


class TestDescriptionServiceCaching:
    """RED TESTS: Test description caching mechanism."""
    
    @pytest.mark.asyncio
    async def test_description_cache_with_ttl(self):
        """
        RED TEST: Should implement description cache with TTL.
        
        This test will fail because caching logic doesn't exist yet.
        Expected behavior:
        - Should cache successful descriptions
        - Should respect TTL (time-to-live)
        - Should return cached results for identical snapshots
        - Should evict expired entries
        """
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_ollama_client.describe_image.return_value = "Cached description result"
        
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        mock_image_processor.process_webcam_frame.return_value = "base64_encoded_image"
        
        config = DescriptionServiceConfig(cache_ttl_seconds=300)  # 5 minutes
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Create identical snapshots
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        frame[50:150, 50:150] = [255, 128, 64]  # Orange square for uniqueness
        
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.85,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot1 = Snapshot(frame=frame.copy(), metadata=metadata)
        snapshot2 = Snapshot(frame=frame.copy(), metadata=metadata)
        
        # First call should hit Ollama
        result1 = await service.describe_snapshot(snapshot1)
        assert mock_ollama_client.describe_image.call_count == 1
        
        # Second call should use cache
        result2 = await service.describe_snapshot(snapshot2)
        assert mock_ollama_client.describe_image.call_count == 1  # Still only 1 call
        
        # Results should be identical
        assert result1.description == result2.description
        assert result1.confidence == result2.confidence
        
    @pytest.mark.asyncio
    async def test_cache_eviction_after_ttl_expiry(self):
        """
        RED TEST: Should evict cache entries after TTL expires.
        """
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_ollama_client.describe_image.return_value = "Fresh description after cache expiry"
        
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        mock_image_processor.process_webcam_frame.return_value = "base64_encoded_image"
        
        # Very short TTL for testing
        config = DescriptionServiceConfig(cache_ttl_seconds=0.1)  # 100ms
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Create test snapshot
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.9,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # First call
        result1 = await service.describe_snapshot(snapshot)
        assert mock_ollama_client.describe_image.call_count == 1
        
        # Wait for cache to expire
        await asyncio.sleep(0.2)  # 200ms > 100ms TTL
        
        # Second call should hit Ollama again (cache expired)
        result2 = await service.describe_snapshot(snapshot)
        assert mock_ollama_client.describe_image.call_count == 2
        
    def test_cache_memory_usage_optimization(self):
        """
        RED TEST: Should optimize cache memory usage and provide stats.
        """
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        
        config = DescriptionServiceConfig(
            cache_ttl_seconds=300,
            max_cache_entries=10
        )
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Should have cache statistics
        cache_stats = service.get_cache_statistics()
        assert isinstance(cache_stats, dict)
        assert 'total_entries' in cache_stats
        assert 'hit_rate' in cache_stats
        assert 'memory_usage_mb' in cache_stats
        assert 'expired_entries' in cache_stats
        
        # Should have cache management
        assert hasattr(service, 'clear_cache')
        assert hasattr(service, 'cleanup_expired_entries')


class TestDescriptionServiceConfiguration:
    """RED TESTS: Test DescriptionServiceConfig and validation."""
    
    def test_description_service_config_defaults(self):
        """
        RED TEST: DescriptionServiceConfig should have sensible defaults.
        """
        config = DescriptionServiceConfig()
        
        # Test default values
        assert config.cache_ttl_seconds == 300  # 5 minutes
        assert config.max_concurrent_requests == 3
        assert config.timeout_seconds == 30.0
        assert config.max_cache_entries == 100
        assert config.enable_caching is True
        assert config.default_prompt == "Describe what you see in this image. Be concise and specific."
        
    def test_description_service_config_validation(self):
        """
        RED TEST: DescriptionServiceConfig should validate parameters.
        """
        # Valid configuration should work
        config = DescriptionServiceConfig(
            cache_ttl_seconds=600,
            max_concurrent_requests=5,
            timeout_seconds=45.0
        )
        assert config.cache_ttl_seconds == 600
        assert config.max_concurrent_requests == 5
        assert config.timeout_seconds == 45.0
        
        # Invalid TTL should fail
        with pytest.raises(ValueError, match="cache_ttl_seconds must be positive"):
            DescriptionServiceConfig(cache_ttl_seconds=0)
            
        # Invalid concurrency should fail
        with pytest.raises(ValueError, match="max_concurrent_requests must be positive"):
            DescriptionServiceConfig(max_concurrent_requests=0)
            
        # Invalid timeout should fail
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            DescriptionServiceConfig(timeout_seconds=-1.0)


class TestDescriptionResult:
    """RED TESTS: Test DescriptionResult data structure."""
    
    def test_description_result_creation(self):
        """
        RED TEST: DescriptionResult should provide standardized description output.
        """
        result = DescriptionResult(
            description="Person working at computer",
            confidence=0.92,
            timestamp=datetime.now(),
            processing_time_ms=1250,
            cached=False
        )
        
        assert result.description == "Person working at computer"
        assert result.confidence == 0.92
        assert result.timestamp is not None
        assert result.processing_time_ms == 1250
        assert result.cached is False
        assert result.error is None
        
    def test_description_result_error_case(self):
        """
        RED TEST: DescriptionResult should handle error scenarios.
        """
        result = DescriptionResult(
            description="Error: Ollama service unavailable",
            confidence=0.0,
            timestamp=datetime.now(),
            processing_time_ms=100,
            cached=False,
            error="Connection timeout"
        )
        
        assert result.description.startswith("Error:")
        assert result.confidence == 0.0
        assert result.error == "Connection timeout"
        
    def test_description_result_serialization(self):
        """
        RED TEST: DescriptionResult should serialize for HTTP API integration.
        """
        result = DescriptionResult(
            description="Person standing in kitchen",
            confidence=0.87,
            timestamp=datetime.now(),
            processing_time_ms=890,
            cached=True
        )
        
        # Should serialize to dict for JSON response
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict['description'] == "Person standing in kitchen"
        assert result_dict['confidence'] == 0.87
        assert 'timestamp' in result_dict
        assert result_dict['processing_time_ms'] == 890
        assert result_dict['cached'] is True


# Run the tests to see them fail (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 