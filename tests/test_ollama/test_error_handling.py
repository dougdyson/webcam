"""
Tests for error handling and resilience in Ollama integration.

Phase 3.3 of TDD Ollama Description Endpoint Feature.
Following TDD methodology - RED phase: Write failing tests first.

This module tests robust error handling and resilience including:
- Ollama service unavailable scenarios
- Timeout handling and recovery
- Malformed response handling
- Retry logic with exponential backoff
- Error categorization and logging
- Graceful degradation patterns
"""
import pytest
import asyncio
import numpy as np
import time
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from datetime import datetime, timedelta

# These imports will fail initially - that's the RED phase!
try:
    from src.ollama.description_service import DescriptionService, DescriptionServiceConfig
    from src.ollama.client import OllamaClient, OllamaConfig
    from src.ollama.async_processor import AsyncDescriptionProcessor
    from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
    from src.ollama.error_handler import (
        OllamaErrorHandler,
        OllamaErrorCategory,
        OllamaTimeoutError,
        OllamaUnavailableError,
        OllamaMalformedResponseError,
        RetryPolicy,
        ExponentialBackoff
    )
except ImportError:
    # Expected to fail during RED phase
    DescriptionService = None
    DescriptionServiceConfig = None
    OllamaClient = None
    OllamaConfig = None
    AsyncDescriptionProcessor = None
    Snapshot = None
    SnapshotMetadata = None
    OllamaErrorHandler = None
    OllamaErrorCategory = None
    OllamaTimeoutError = None
    OllamaUnavailableError = None
    OllamaMalformedResponseError = None
    RetryPolicy = None
    ExponentialBackoff = None


class TestOllamaServiceUnavailable:
    """RED TESTS: Test scenarios when Ollama service is unavailable."""
    
    @pytest.mark.asyncio
    async def test_ollama_service_unavailable_detection(self):
        """
        RED TEST: Should detect when Ollama service is unavailable.
        
        This test will fail because OllamaErrorHandler doesn't exist yet.
        Expected behavior:
        - Should detect connection refused errors
        - Should categorize as SERVICE_UNAVAILABLE
        - Should provide graceful fallback
        """
        error_handler = OllamaErrorHandler()
        
        # Simulate connection refused error
        connection_error = ConnectionRefusedError("Connection refused to localhost:11434")
        
        error_category = error_handler.categorize_error(connection_error)
        assert error_category == OllamaErrorCategory.SERVICE_UNAVAILABLE
        
        # Should provide fallback description
        fallback_description = error_handler.get_fallback_description("service_unavailable")
        assert isinstance(fallback_description, str)
        assert "unavailable" in fallback_description.lower()
        assert len(fallback_description) > 0
    
    @pytest.mark.asyncio
    async def test_description_service_ollama_unavailable_fallback(self):
        """
        RED TEST: DescriptionService should handle Ollama unavailable gracefully.
        """
        # Mock OllamaClient that always fails with connection error
        mock_client = Mock(spec=OllamaClient)
        mock_client.describe_image.side_effect = ConnectionRefusedError("Ollama unavailable")
        mock_client.is_available.return_value = False
        
        # Mock ImageProcessor
        mock_image_processor = Mock()
        
        config = DescriptionServiceConfig(
            cache_ttl_seconds=300,
            enable_fallback_descriptions=True,
            retry_attempts=0  # No retries for this test
        )
        
        service = DescriptionService(
            ollama_client=mock_client,
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
        
        # Should return fallback description instead of raising exception
        result = await service.describe_snapshot(snapshot)
        
        assert result is not None
        assert result.description is not None
        assert "unavailable" in result.description.lower() or "error" in result.description.lower()
        assert result.confidence == 0.0  # Low confidence for fallback
        assert result.error is not None
        assert "unavailable" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_async_processor_ollama_unavailable_handling(self):
        """
        RED TEST: AsyncDescriptionProcessor should handle Ollama unavailable.
        """
        # Mock DescriptionService that fails with service unavailable
        mock_service = AsyncMock(spec=DescriptionService)
        mock_service.describe_snapshot.side_effect = OllamaUnavailableError("Ollama service unavailable")
        
        processor = AsyncDescriptionProcessor(
            description_service=mock_service,
            max_queue_size=5,
            rate_limit_per_second=1.0
        )
        
        await processor.start_processing()
        
        # Submit request that will encounter unavailable service
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
        
        # Should return graceful error result
        assert result.success is False
        assert result.error is not None
        assert "unavailable" in result.error.lower()
        assert result.description.startswith("Error:")
        
        await processor.stop_processing()


class TestOllamaTimeoutHandling:
    """RED TESTS: Test timeout scenarios and recovery."""
    
    @pytest.mark.asyncio
    async def test_ollama_timeout_detection(self):
        """
        RED TEST: Should detect and handle Ollama timeouts properly.
        """
        error_handler = OllamaErrorHandler()
        
        # Simulate timeout error
        timeout_error = asyncio.TimeoutError("Ollama request timed out")
        
        error_category = error_handler.categorize_error(timeout_error)
        assert error_category == OllamaErrorCategory.TIMEOUT
        
        # Should provide appropriate fallback
        fallback_description = error_handler.get_fallback_description("timeout")
        assert isinstance(fallback_description, str)
        assert "timeout" in fallback_description.lower() or "slow" in fallback_description.lower()
    
    @pytest.mark.asyncio
    async def test_description_service_timeout_handling(self):
        """
        RED TEST: DescriptionService should handle timeouts with retries.
        """
        # Mock client that times out on first call, succeeds on second
        mock_client = Mock(spec=OllamaClient)
        mock_client.describe_image.side_effect = [
            asyncio.TimeoutError("Request timeout"),
            "Person working at computer"  # Success on retry
        ]
        mock_client.is_available.return_value = True
        
        # Mock ImageProcessor
        mock_image_processor = Mock()
        
        config = DescriptionServiceConfig(
            timeout_seconds=5.0,
            retry_attempts=2,
            retry_backoff_factor=1.5,
            enable_fallback_descriptions=True
        )
        
        service = DescriptionService(
            ollama_client=mock_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        frame = np.zeros((320, 240, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Should retry and eventually succeed
        result = await service.describe_snapshot(snapshot)
        
        assert result.description == "Person working at computer"
        assert result.confidence > 0.0
        assert result.error is None
        
        # Should have called describe_image twice (initial + 1 retry)
        assert mock_client.describe_image.call_count == 2
    
    @pytest.mark.asyncio
    async def test_timeout_with_exponential_backoff(self):
        """
        RED TEST: Should implement exponential backoff for timeout retries.
        """
        backoff = ExponentialBackoff(
            initial_delay=0.1,
            max_delay=2.0,
            backoff_factor=2.0,
            max_attempts=4
        )
        
        # Test backoff delay calculation
        delays = []
        for attempt in range(4):
            delay = backoff.get_delay(attempt)
            delays.append(delay)
        
        # Should have exponential pattern: 0.1, 0.2, 0.4, 0.8
        assert delays[0] == 0.1
        assert delays[1] == 0.2
        assert delays[2] == 0.4
        assert delays[3] == 0.8
        
        # Should not exceed max_delay
        long_delay = backoff.get_delay(10)
        assert long_delay <= 2.0
    
    @pytest.mark.asyncio
    async def test_async_processor_timeout_retry_logic(self):
        """
        RED TEST: AsyncDescriptionProcessor should handle timeouts with retries.
        """
        # Mock service that times out then succeeds
        mock_service = AsyncMock(spec=DescriptionService)
        mock_service.describe_snapshot.side_effect = [
            OllamaTimeoutError("Timeout on first attempt"),
            Mock(description="Success after retry", confidence=0.85, error=None)
        ]
        
        processor = AsyncDescriptionProcessor(
            description_service=mock_service,
            max_queue_size=5,
            rate_limit_per_second=2.0,  # Faster for testing
            enable_retries=True,
            max_retry_attempts=2
        )
        
        await processor.start_processing()
        
        frame = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        result_future = await processor.submit_request(snapshot, priority=1)
        result = await asyncio.wait_for(result_future, timeout=5.0)
        
        # Should eventually succeed after retry
        assert result.success is True
        assert result.description == "Success after retry"
        assert mock_service.describe_snapshot.call_count == 2
        
        await processor.stop_processing()


class TestMalformedResponseHandling:
    """RED TESTS: Test handling of malformed Ollama responses."""
    
    def test_malformed_response_detection(self):
        """
        RED TEST: Should detect and handle malformed Ollama responses.
        """
        error_handler = OllamaErrorHandler()
        
        # Test various malformed response scenarios
        test_cases = [
            "",  # Empty response
            "Not JSON",  # Invalid JSON
            "{}",  # Empty JSON
            '{"wrong": "format"}',  # Missing expected fields
            '{"message": {"content": ""}}',  # Empty content
            None,  # Null response
        ]
        
        for malformed_response in test_cases:
            try:
                is_valid = error_handler.validate_ollama_response(malformed_response)
                assert is_valid is False
                
                # Should categorize as malformed response
                error = OllamaMalformedResponseError(f"Invalid response: {malformed_response}")
                category = error_handler.categorize_error(error)
                assert category == OllamaErrorCategory.MALFORMED_RESPONSE
                
            except Exception as e:
                # Should handle validation errors gracefully
                assert isinstance(e, (ValueError, TypeError, OllamaMalformedResponseError))
    
    @pytest.mark.asyncio
    async def test_description_service_malformed_response_handling(self):
        """
        RED TEST: DescriptionService should handle malformed responses gracefully.
        """
        # Mock client that returns malformed response
        mock_client = Mock(spec=OllamaClient)
        mock_client.describe_image.return_value = ""  # Empty response
        mock_client.is_available.return_value = True
        
        # Mock ImageProcessor
        mock_image_processor = Mock()
        
        config = DescriptionServiceConfig(
            validate_responses=True,
            enable_fallback_descriptions=True,
            retry_attempts=1
        )
        
        service = DescriptionService(
            ollama_client=mock_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Should handle malformed response and provide fallback
        result = await service.describe_snapshot(snapshot)
        
        assert result is not None
        assert result.description is not None
        assert result.confidence == 0.0  # Low confidence for fallback
        assert result.error is not None
        assert "malformed" in result.error.lower() or "invalid" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_response_validation_edge_cases(self):
        """
        RED TEST: Should handle edge cases in response validation.
        """
        error_handler = OllamaErrorHandler()
        
        # Test edge cases that could cause validation failures
        edge_cases = [
            '{"message": {"content": "A" * 10000}}',  # Very long response
            '{"message": {"content": "🎯🚀✨"}}',  # Unicode emojis
            '{"message": {"content": "Line1\\nLine2\\nLine3"}}',  # Multiline
            '{"message": {"content": "Quote: \\"Hello\\""}}',  # Escaped quotes
        ]
        
        for response in edge_cases:
            # Should handle edge cases gracefully
            is_valid = error_handler.validate_ollama_response(response)
            
            if is_valid:
                # If valid, should extract content properly
                content = error_handler.extract_content(response)
                assert isinstance(content, str)
                assert len(content) > 0
            else:
                # If invalid, should provide fallback
                fallback = error_handler.get_fallback_description("malformed_response")
                assert isinstance(fallback, str)
                assert len(fallback) > 0


class TestRetryPolicyAndBackoff:
    """RED TESTS: Test retry policies and exponential backoff."""
    
    def test_retry_policy_configuration(self):
        """
        RED TEST: RetryPolicy should provide configurable retry behavior.
        """
        policy = RetryPolicy(
            max_attempts=3,
            backoff_strategy="exponential",
            initial_delay=0.5,
            max_delay=10.0,
            backoff_factor=2.0,
            retryable_errors=[OllamaTimeoutError, OllamaUnavailableError]
        )
        
        assert policy.max_attempts == 3
        assert policy.backoff_strategy == "exponential"
        assert policy.initial_delay == 0.5
        assert policy.max_delay == 10.0
        assert policy.backoff_factor == 2.0
        
        # Should determine if error is retryable
        timeout_error = OllamaTimeoutError("Timeout")
        unavailable_error = OllamaUnavailableError("Service down")
        malformed_error = OllamaMalformedResponseError("Bad response")
        
        assert policy.is_retryable(timeout_error) is True
        assert policy.is_retryable(unavailable_error) is True
        assert policy.is_retryable(malformed_error) is False  # Not in retryable list
    
    def test_exponential_backoff_implementation(self):
        """
        RED TEST: ExponentialBackoff should implement proper timing.
        """
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=2.0,
            jitter=False  # No jitter for predictable testing
        )
        
        # Test progression: 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0 (capped)
        expected_delays = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]
        
        for attempt, expected in enumerate(expected_delays):
            actual_delay = backoff.get_delay(attempt)
            assert actual_delay == expected
    
    def test_exponential_backoff_with_jitter(self):
        """
        RED TEST: ExponentialBackoff should support jitter for avoiding thundering herd.
        """
        backoff = ExponentialBackoff(
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=2.0,
            jitter=True,
            jitter_factor=0.1  # 10% jitter
        )
        
        # With jitter, delays should vary slightly
        delays = []
        for i in range(10):
            delay = backoff.get_delay(2)  # 3rd attempt should be ~4.0 seconds
            delays.append(delay)
        
        # Should have some variation due to jitter
        assert len(set(delays)) > 1  # Not all the same
        assert all(3.6 <= delay <= 4.4 for delay in delays)  # Within jitter range
    
    @pytest.mark.asyncio
    async def test_retry_policy_integration_with_description_service(self):
        """
        RED TEST: RetryPolicy should integrate with DescriptionService.
        """
        # Mock client that fails twice then succeeds
        mock_client = Mock(spec=OllamaClient)
        mock_client.describe_image.side_effect = [
            OllamaTimeoutError("First timeout"),
            OllamaTimeoutError("Second timeout"),
            "Success on third attempt"
        ]
        mock_client.is_available.return_value = True
        
        # Mock ImageProcessor
        mock_image_processor = Mock()
        
        retry_policy = RetryPolicy(
            max_attempts=3,
            backoff_strategy="exponential",
            initial_delay=0.01,  # Fast for testing
            retryable_errors=[OllamaTimeoutError]
        )
        
        config = DescriptionServiceConfig(
            retry_policy=retry_policy,
            enable_fallback_descriptions=False  # Should succeed before fallback
        )
        
        service = DescriptionService(
            ollama_client=mock_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.8,
            human_present=True,
            detection_source="multimodal"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Should eventually succeed after retries
        start_time = time.time()
        result = await service.describe_snapshot(snapshot)
        end_time = time.time()
        
        assert result.description == "Success on third attempt"
        assert result.success is True
        assert mock_client.describe_image.call_count == 3
        
        # Should have taken some time due to backoff delays
        assert (end_time - start_time) >= 0.01  # At least some delay


class TestErrorCategorizationAndLogging:
    """RED TESTS: Test comprehensive error categorization and logging."""
    
    def test_error_category_enum(self):
        """
        RED TEST: OllamaErrorCategory should provide comprehensive error types.
        """
        # Should have all necessary error categories
        assert hasattr(OllamaErrorCategory, 'SERVICE_UNAVAILABLE')
        assert hasattr(OllamaErrorCategory, 'TIMEOUT')
        assert hasattr(OllamaErrorCategory, 'MALFORMED_RESPONSE')
        assert hasattr(OllamaErrorCategory, 'AUTHENTICATION_ERROR')
        assert hasattr(OllamaErrorCategory, 'RATE_LIMITED')
        assert hasattr(OllamaErrorCategory, 'UNKNOWN_ERROR')
        
        # Should be proper enum values
        assert isinstance(OllamaErrorCategory.SERVICE_UNAVAILABLE, OllamaErrorCategory)
        assert isinstance(OllamaErrorCategory.TIMEOUT, OllamaErrorCategory)
    
    def test_comprehensive_error_categorization(self):
        """
        RED TEST: Should categorize all types of errors correctly.
        """
        error_handler = OllamaErrorHandler()
        
        # Test categorization of different error types
        test_cases = [
            (ConnectionRefusedError("Connection refused"), OllamaErrorCategory.SERVICE_UNAVAILABLE),
            (asyncio.TimeoutError("Timeout"), OllamaErrorCategory.TIMEOUT),
            (OllamaMalformedResponseError("Bad response"), OllamaErrorCategory.MALFORMED_RESPONSE),
            (ValueError("Invalid input"), OllamaErrorCategory.UNKNOWN_ERROR),
            (Exception("Generic error"), OllamaErrorCategory.UNKNOWN_ERROR),
        ]
        
        for error, expected_category in test_cases:
            actual_category = error_handler.categorize_error(error)
            assert actual_category == expected_category
    
    @pytest.mark.asyncio
    async def test_error_logging_integration(self):
        """
        RED TEST: Should log errors with appropriate levels and context.
        """
        with patch('src.ollama.error_handler.logger') as mock_logger:
            error_handler = OllamaErrorHandler(enable_detailed_logging=True)
            
            # Test different error scenarios and their logging
            errors = [
                (OllamaTimeoutError("Timeout error"), "warning"),
                (OllamaUnavailableError("Service unavailable"), "error"),
                (OllamaMalformedResponseError("Bad response"), "warning"),
                (Exception("Unknown error"), "error"),
            ]
            
            for error, expected_level in errors:
                error_handler.handle_error(error, context="test_context")
                
                # Should log with appropriate level
                if expected_level == "warning":
                    assert mock_logger.warning.called
                elif expected_level == "error":
                    assert mock_logger.error.called
                
                # Should include context in log message
                log_calls = mock_logger.warning.call_args_list + mock_logger.error.call_args_list
                assert any("test_context" in str(call) for call in log_calls)
    
    def test_error_metrics_tracking(self):
        """
        RED TEST: Should track error metrics for monitoring.
        """
        error_handler = OllamaErrorHandler(enable_metrics=True)
        
        # Simulate various errors
        errors = [
            OllamaTimeoutError("Timeout 1"),
            OllamaTimeoutError("Timeout 2"),
            OllamaUnavailableError("Unavailable 1"),
            OllamaMalformedResponseError("Malformed 1"),
        ]
        
        for error in errors:
            error_handler.handle_error(error)
        
        # Should track error counts by category
        metrics = error_handler.get_error_metrics()
        assert isinstance(metrics, dict)
        assert metrics['timeout_errors'] == 2
        assert metrics['unavailable_errors'] == 1
        assert metrics['malformed_response_errors'] == 1
        assert metrics['total_errors'] == 4
        
        # Should provide error rate information
        assert 'error_rate_per_minute' in metrics
        assert 'most_common_error_category' in metrics


# Run the tests to see them fail (RED phase)
if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 