"""
Tests for async description processing pipeline.

Phase 3.2 of TDD Ollama Description Endpoint Feature.
Following TDD methodology - RED phase: Write failing tests first.

This module tests the async processing pipeline which provides:
- Background description processing queue
- Rate limiting to prevent Ollama overload (max 1 per 2 seconds)
- Concurrent request handling with proper async coordination
- Integration with existing async architecture
"""
import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# These imports will fail initially - that's the RED phase!
try:
    from src.ollama.async_processor import (
        AsyncDescriptionProcessor,
        ProcessingQueue,
        RateLimiter,
        ProcessingRequest,
        ProcessingResult
    )
    from src.ollama.description_service import DescriptionService
    from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
    from src.ollama.client import OllamaClient
except ImportError:
    # Expected to fail during RED phase
    AsyncDescriptionProcessor = None
    ProcessingQueue = None
    RateLimiter = None
    ProcessingRequest = None
    ProcessingResult = None
    DescriptionService = None
    Snapshot = None
    SnapshotMetadata = None
    OllamaClient = None


class TestAsyncDescriptionProcessingQueue:
    """RED TESTS: Test async description processing queue implementation."""
    
    @pytest.mark.asyncio
    async def test_processing_queue_initialization(self):
        """
        RED TEST: ProcessingQueue should initialize with configurable size.
        
        This test will fail because ProcessingQueue doesn't exist yet.
        Expected behavior:
        - Should accept max_size parameter for queue capacity
        - Should initialize empty async queue
        - Should track queue statistics
        """
        queue = ProcessingQueue(max_size=10)
        
        assert queue.max_size == 10
        assert queue.is_empty() is True
        assert queue.size() == 0
        assert queue.is_full() is False
        
        # Should have statistics tracking
        stats = queue.get_statistics()
        assert isinstance(stats, dict)
        assert 'total_requests' in stats
        assert 'completed_requests' in stats
        assert 'failed_requests' in stats
        assert 'average_processing_time_ms' in stats
    
    @pytest.mark.asyncio
    async def test_processing_queue_add_request(self):
        """
        RED TEST: Should add processing requests to queue asynchronously.
        """
        queue = ProcessingQueue(max_size=5)
        
        # Create test snapshot
        frame = np.zeros((320, 240, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Create processing request
        request = ProcessingRequest(
            snapshot=snapshot,
            priority=1,
            timestamp=datetime.now(),
            request_id="test_req_001"
        )
        
        # Should add request to queue
        await queue.add_request(request)
        
        assert queue.size() == 1
        assert queue.is_empty() is False
        
        # Should be able to retrieve request
        retrieved_request = await queue.get_next_request()
        assert retrieved_request.request_id == "test_req_001"
        assert retrieved_request.snapshot == snapshot
    
    @pytest.mark.asyncio
    async def test_processing_queue_priority_ordering(self):
        """
        RED TEST: Should process requests in priority order.
        """
        queue = ProcessingQueue(max_size=10)
        
        # Create multiple requests with different priorities
        requests = []
        for i, priority in enumerate([3, 1, 2, 1, 3]):
            frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            metadata = SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=0.8,
                human_present=True,
                detection_source="multimodal"
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            
            request = ProcessingRequest(
                snapshot=snapshot,
                priority=priority,
                timestamp=datetime.now(),
                request_id=f"req_{i}"
            )
            requests.append(request)
            await queue.add_request(request)
        
        # Should retrieve in priority order (1=highest, 3=lowest)
        first_request = await queue.get_next_request()
        assert first_request.priority == 1
        
        second_request = await queue.get_next_request()
        assert second_request.priority == 1
        
        third_request = await queue.get_next_request()
        assert third_request.priority == 2
    
    @pytest.mark.asyncio
    async def test_processing_queue_full_capacity_handling(self):
        """
        RED TEST: Should handle queue at full capacity gracefully.
        """
        queue = ProcessingQueue(max_size=2)  # Small queue for testing
        
        # Fill queue to capacity
        for i in range(2):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            metadata = SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=0.8,
                human_present=True,
                detection_source="multimodal"
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            
            request = ProcessingRequest(
                snapshot=snapshot,
                priority=1,
                timestamp=datetime.now(),
                request_id=f"req_{i}"
            )
            await queue.add_request(request)
        
        assert queue.is_full() is True
        assert queue.size() == 2
        
        # Adding another request should either:
        # 1. Block until space available, or
        # 2. Reject with appropriate exception, or  
        # 3. Drop oldest request
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        overflow_request = ProcessingRequest(
            snapshot=snapshot,
            priority=1,
            timestamp=datetime.now(),
            request_id="overflow_req"
        )
        
        # Should handle overflow gracefully (implementation can choose strategy)
        try:
            # Try to add with timeout
            await asyncio.wait_for(queue.add_request(overflow_request), timeout=0.1)
        except (asyncio.TimeoutError, Exception):
            # Expected - queue should handle overflow somehow
            pass


class TestRateLimiter:
    """RED TESTS: Test rate limiting for Ollama processing."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """
        RED TEST: RateLimiter should initialize with configurable rate.
        
        This test will fail because RateLimiter doesn't exist yet.
        Expected behavior:
        - Should accept requests_per_second parameter
        - Should track request timing
        - Should enforce rate limits
        """
        # Max 1 request per 2 seconds = 0.5 requests per second
        rate_limiter = RateLimiter(requests_per_second=0.5)
        
        assert rate_limiter.requests_per_second == 0.5
        assert rate_limiter.interval_seconds == 2.0
        assert rate_limiter.can_proceed() is True  # First request should be allowed
    
    @pytest.mark.asyncio
    async def test_rate_limiter_enforce_timing(self):
        """
        RED TEST: Should enforce rate limiting timing correctly.
        """
        rate_limiter = RateLimiter(requests_per_second=0.5)  # 1 per 2 seconds
        
        # First request should be immediate
        start_time = asyncio.get_event_loop().time()
        
        await rate_limiter.acquire()
        first_request_time = asyncio.get_event_loop().time()
        assert (first_request_time - start_time) < 0.1  # Should be immediate
        
        # Second request should be delayed
        await rate_limiter.acquire()
        second_request_time = asyncio.get_event_loop().time()
        delay = second_request_time - first_request_time
        assert delay >= 1.9  # Should wait ~2 seconds (allowing small tolerance)
        assert delay <= 2.2
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_requests(self):
        """
        RED TEST: Should handle concurrent rate limiting correctly.
        """
        rate_limiter = RateLimiter(requests_per_second=1.0)  # 1 per second
        
        # Start multiple concurrent requests
        start_time = asyncio.get_event_loop().time()
        
        tasks = []
        for i in range(3):
            task = asyncio.create_task(rate_limiter.acquire())
            tasks.append(task)
        
        # Wait for all requests to complete
        await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # Should take at least 2 seconds for 3 requests at 1/second
        total_time = end_time - start_time
        assert total_time >= 1.9  # Allow some tolerance
        assert total_time <= 3.0   # But not too slow
    
    def test_rate_limiter_statistics(self):
        """
        RED TEST: Should track rate limiting statistics.
        """
        rate_limiter = RateLimiter(requests_per_second=1.0)
        
        stats = rate_limiter.get_statistics()
        assert isinstance(stats, dict)
        assert 'total_requests' in stats
        assert 'total_wait_time_ms' in stats
        assert 'average_wait_time_ms' in stats
        assert 'requests_per_second_actual' in stats


class TestAsyncDescriptionProcessor:
    """RED TESTS: Test main async description processor."""
    
    @pytest.mark.asyncio
    async def test_async_processor_initialization(self):
        """
        RED TEST: AsyncDescriptionProcessor should initialize with dependencies.
        
        This test will fail because AsyncDescriptionProcessor doesn't exist yet.
        Expected behavior:
        - Should accept DescriptionService dependency
        - Should initialize processing queue and rate limiter
        - Should integrate with existing async architecture
        """
        mock_description_service = Mock(spec=DescriptionService)
        
        processor = AsyncDescriptionProcessor(
            description_service=mock_description_service,
            max_queue_size=10,
            rate_limit_per_second=0.5
        )
        
        assert processor.description_service == mock_description_service
        assert processor.queue is not None
        assert processor.rate_limiter is not None
        assert processor.is_running is False
        
        # Should have async processing methods
        assert hasattr(processor, 'start_processing')
        assert hasattr(processor, 'stop_processing')
        assert hasattr(processor, 'submit_request')
        assert asyncio.iscoroutinefunction(processor.start_processing)
        assert asyncio.iscoroutinefunction(processor.submit_request)
    
    @pytest.mark.asyncio
    async def test_async_processor_background_processing(self):
        """
        RED TEST: Should process requests in background continuously.
        """
        mock_description_service = AsyncMock(spec=DescriptionService)
        mock_description_service.describe_snapshot.return_value = Mock(
            description="Test description",
            confidence=0.9,
            processing_time_ms=500
        )
        
        processor = AsyncDescriptionProcessor(
            description_service=mock_description_service,
            max_queue_size=5,
            rate_limit_per_second=2.0  # Faster for testing
        )
        
        # Start background processing
        await processor.start_processing()
        assert processor.is_running is True
        
        # Submit a processing request
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.85,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Submit request and get future for result
        result_future = await processor.submit_request(snapshot, priority=1)
        
        # Wait for processing to complete
        result = await asyncio.wait_for(result_future, timeout=2.0)
        
        # Should have processed the request
        assert isinstance(result, ProcessingResult)
        assert result.description == "Test description"
        assert result.success is True
        assert mock_description_service.describe_snapshot.called
        
        # Stop processing
        await processor.stop_processing()
        assert processor.is_running is False
    
    @pytest.mark.asyncio
    async def test_async_processor_rate_limiting_integration(self):
        """
        RED TEST: Should integrate rate limiting with async processing.
        """
        mock_description_service = AsyncMock(spec=DescriptionService)
        mock_description_service.describe_snapshot.return_value = Mock(
            description="Rate limited description",
            confidence=0.8,
            processing_time_ms=300
        )
        
        # Slow rate for testing rate limiting
        processor = AsyncDescriptionProcessor(
            description_service=mock_description_service,
            max_queue_size=10,
            rate_limit_per_second=0.5  # 1 per 2 seconds
        )
        
        await processor.start_processing()
        
        # Submit multiple requests quickly
        start_time = asyncio.get_event_loop().time()
        
        futures = []
        for i in range(2):
            frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            metadata = SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=0.8,
                human_present=True,
                detection_source="multimodal"
            )
            snapshot = Snapshot(frame=frame, metadata=metadata)
            
            future = await processor.submit_request(snapshot, priority=1)
            futures.append(future)
        
        # Wait for both to complete
        results = await asyncio.gather(*futures)
        end_time = asyncio.get_event_loop().time()
        
        # Should have taken at least 2 seconds due to rate limiting
        processing_time = end_time - start_time
        assert processing_time >= 1.9  # Allow tolerance
        
        # Both should have succeeded
        assert len(results) == 2
        assert all(result.success for result in results)
        
        await processor.stop_processing()
    
    @pytest.mark.asyncio
    async def test_async_processor_error_handling(self):
        """
        RED TEST: Should handle processing errors gracefully.
        """
        mock_description_service = AsyncMock(spec=DescriptionService)
        mock_description_service.describe_snapshot.side_effect = Exception("Ollama error")
        
        processor = AsyncDescriptionProcessor(
            description_service=mock_description_service,
            max_queue_size=5,
            rate_limit_per_second=1.0
        )
        
        await processor.start_processing()
        
        # Submit request that will fail
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        result_future = await processor.submit_request(snapshot, priority=1)
        result = await asyncio.wait_for(result_future, timeout=2.0)
        
        # Should return error result, not raise exception
        assert isinstance(result, ProcessingResult)
        assert result.success is False
        assert result.error is not None
        assert "Ollama error" in result.error
        
        await processor.stop_processing()


class TestProcessingRequestAndResult:
    """RED TESTS: Test processing request and result data structures."""
    
    def test_processing_request_creation(self):
        """
        RED TEST: ProcessingRequest should provide standardized request format.
        """
        frame = np.zeros((320, 240, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.9,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        request = ProcessingRequest(
            snapshot=snapshot,
            priority=1,
            timestamp=datetime.now(),
            request_id="req_123"
        )
        
        assert request.snapshot == snapshot
        assert request.priority == 1
        assert request.timestamp is not None
        assert request.request_id == "req_123"
        
        # Should support priority comparison for queue ordering
        request2 = ProcessingRequest(
            snapshot=snapshot,
            priority=2,
            timestamp=datetime.now(),
            request_id="req_456"
        )
        
        # Lower priority number = higher priority
        assert request < request2  # priority 1 < priority 2
    
    def test_processing_result_creation(self):
        """
        RED TEST: ProcessingResult should provide standardized result format.
        """
        # Success result
        success_result = ProcessingResult(
            request_id="req_123",
            description="Person working at computer",
            confidence=0.92,
            processing_time_ms=1200,
            success=True
        )
        
        assert success_result.request_id == "req_123"
        assert success_result.description == "Person working at computer"
        assert success_result.confidence == 0.92
        assert success_result.processing_time_ms == 1200
        assert success_result.success is True
        assert success_result.error is None
        
        # Error result
        error_result = ProcessingResult(
            request_id="req_456",
            description="Error: Processing failed",
            confidence=0.0,
            processing_time_ms=100,
            success=False,
            error="Ollama timeout"
        )
        
        assert error_result.success is False
        assert error_result.error == "Ollama timeout"
        assert error_result.confidence == 0.0
    
    def test_processing_result_serialization(self):
        """
        RED TEST: ProcessingResult should serialize for event integration.
        """
        result = ProcessingResult(
            request_id="req_789",
            description="Person standing in kitchen",
            confidence=0.87,
            processing_time_ms=890,
            success=True
        )
        
        # Should serialize to dict for event publishing
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict['request_id'] == "req_789"
        assert result_dict['description'] == "Person standing in kitchen"
        assert result_dict['confidence'] == 0.87
        assert result_dict['processing_time_ms'] == 890
        assert result_dict['success'] is True


# Run the tests to see them fail (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 