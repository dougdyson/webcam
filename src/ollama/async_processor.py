"""
Async description processing pipeline.

This module provides background description processing with rate limiting
and queue management, integrating with the existing async architecture.

Key Features:
- Async processing queue with priority ordering
- Rate limiting to prevent Ollama overload (configurable requests per second)
- Background processing with proper async coordination
- Concurrent request handling with futures
- Integration with existing service patterns
- Comprehensive statistics and monitoring
- Graceful error handling and recovery

Integration with Existing Architecture:
- Follows patterns from HTTP/SSE services
- Uses same logging and configuration approaches
- Designed for integration with EventPublisher system
- Compatible with existing snapshot management
"""
import asyncio
import logging
import time
import heapq
import uuid
from typing import Dict, Any, Optional
from concurrent.futures import Future
from dataclasses import dataclass, field
from datetime import datetime

from .description_service import DescriptionService, DescriptionResult
from .snapshot_buffer import Snapshot
from .error_handler import OllamaTimeoutError, OllamaUnavailableError

logger = logging.getLogger(__name__)


@dataclass
class ProcessingRequest:
    """
    Request for description processing with priority support.
    
    Lower priority number = higher priority (1 is highest priority).
    Supports comparison for priority queue ordering.
    
    Attributes:
        snapshot: Snapshot to process
        priority: Processing priority (1=highest, higher numbers=lower priority)
        timestamp: When request was created
        request_id: Unique identifier for tracking
    """
    snapshot: Snapshot
    priority: int
    timestamp: datetime
    request_id: str
    
    def __lt__(self, other):
        """Support priority queue ordering (lower priority number = higher priority)."""
        if not isinstance(other, ProcessingRequest):
            return NotImplemented
        return self.priority < other.priority
    
    def __str__(self):
        """String representation for debugging."""
        return f"ProcessingRequest(id={self.request_id}, priority={self.priority})"


@dataclass
class ProcessingResult:
    """
    Result of description processing with metadata.
    
    Contains description, processing information, and error details.
    Designed for event integration and HTTP API responses.
    
    Attributes:
        request_id: Unique identifier matching the request
        description: Generated description text
        confidence: Confidence score (0.0-1.0)
        processing_time_ms: Time taken to process in milliseconds
        success: Whether processing succeeded
        error: Error message if processing failed
    """
    request_id: str
    description: str
    confidence: float
    processing_time_ms: int
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for event publishing and HTTP responses."""
        return {
            'request_id': self.request_id,
            'description': self.description,
            'confidence': self.confidence,
            'processing_time_ms': self.processing_time_ms,
            'success': self.success,
            'error': self.error,
            'timestamp': datetime.now().isoformat()
        }
    
    def __str__(self):
        """String representation for debugging."""
        status = "SUCCESS" if self.success else f"ERROR: {self.error}"
        return f"ProcessingResult(id={self.request_id}, {status})"


class ProcessingQueue:
    """
    Async processing queue with priority ordering and statistics.
    
    Provides priority-based request queuing for description processing.
    Tracks statistics for monitoring and performance analysis.
    
    Features:
    - Priority-based ordering (lower number = higher priority)
    - Configurable capacity with overflow handling
    - Comprehensive statistics tracking
    - Thread-safe async operations
    """
    
    def __init__(self, max_size: int = 100):
        """
        Initialize processing queue.
        
        Args:
            max_size: Maximum number of requests in queue
        """
        self.max_size = max_size
        self._queue = asyncio.PriorityQueue(maxsize=max_size)
        self._stats = {
            'total_requests': 0,
            'completed_requests': 0,
            'failed_requests': 0,
            'processing_times': []
        }
        logger.debug(f"ProcessingQueue initialized with max_size={max_size}")
    
    async def add_request(self, request: ProcessingRequest) -> None:
        """
        Add processing request to queue.
        
        Args:
            request: Request to add to queue
            
        Raises:
            asyncio.QueueFull: If queue is at capacity and can't accept more requests
        """
        try:
            await self._queue.put(request)
            self._stats['total_requests'] += 1
            logger.debug(f"Added request to queue: {request}")
        except Exception as e:
            logger.error(f"Failed to add request to queue: {e}")
            raise
    
    async def get_next_request(self) -> ProcessingRequest:
        """
        Get next request from queue (highest priority first).
        
        Returns:
            Next request to process
            
        Raises:
            asyncio.QueueEmpty: If queue is empty and no requests available
        """
        request = await self._queue.get()
        logger.debug(f"Retrieved request from queue: {request}")
        return request
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        return self._queue.full()
    
    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics for monitoring."""
        processing_times = self._stats['processing_times']
        avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        return {
            'total_requests': self._stats['total_requests'],
            'completed_requests': self._stats['completed_requests'],
            'failed_requests': self._stats['failed_requests'],
            'average_processing_time_ms': avg_time,
            'current_queue_size': self.size(),
            'queue_capacity': self.max_size,
            'queue_utilization': self.size() / self.max_size if self.max_size > 0 else 0,
            'success_rate': (
                self._stats['completed_requests'] / self._stats['total_requests'] 
                if self._stats['total_requests'] > 0 else 0
            )
        }
    
    def mark_completed(self, processing_time_ms: int) -> None:
        """Mark request as completed and update statistics."""
        self._stats['completed_requests'] += 1
        self._stats['processing_times'].append(processing_time_ms)
        # Keep only last 100 processing times for memory efficiency
        if len(self._stats['processing_times']) > 100:
            self._stats['processing_times'] = self._stats['processing_times'][-100:]
        logger.debug(f"Marked request completed, processing_time={processing_time_ms}ms")
    
    def mark_failed(self) -> None:
        """Mark request as failed and update statistics."""
        self._stats['failed_requests'] += 1
        logger.debug("Marked request failed")


class RateLimiter:
    """
    Rate limiter for controlling Ollama request frequency.
    
    Prevents overwhelming Ollama service with too many concurrent requests.
    Provides configurable rate limiting with timing enforcement.
    
    Features:
    - Configurable requests per second
    - Thread-safe async operations
    - Statistics tracking for monitoring
    - Proper concurrent request handling
    """
    
    def __init__(self, requests_per_second: float):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests allowed per second
        """
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
            
        self.requests_per_second = requests_per_second
        self.interval_seconds = 1.0 / requests_per_second
        self._lock = asyncio.Lock()
        self._last_request_time = 0.0
        self._stats = {
            'total_requests': 0,
            'total_wait_time_ms': 0,
            'start_time': time.time()
        }
        logger.debug(f"RateLimiter initialized: {requests_per_second} req/sec, interval={self.interval_seconds:.3f}s")
    
    def can_proceed(self) -> bool:
        """Check if a request can proceed without waiting."""
        current_time = time.time()
        return (current_time - self._last_request_time) >= self.interval_seconds
    
    async def acquire(self) -> None:
        """
        Acquire permission to proceed with request (with rate limiting).
        
        This method ensures that requests are spaced according to the configured
        rate limit. Concurrent calls will be serialized to maintain proper timing.
        """
        async with self._lock:  # Ensure only one request can proceed at a time
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.interval_seconds:
                wait_time = self.interval_seconds - time_since_last
                logger.debug(f"Rate limiting: waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)
                self._stats['total_wait_time_ms'] += wait_time * 1000
            
            self._last_request_time = time.time()
            self._stats['total_requests'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        total_requests = self._stats['total_requests']
        avg_wait_time = (
            self._stats['total_wait_time_ms'] / total_requests 
            if total_requests > 0 else 0
        )
        
        # Calculate actual requests per second based on elapsed time
        elapsed_time = time.time() - self._stats['start_time']
        actual_rate = total_requests / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'total_requests': total_requests,
            'total_wait_time_ms': self._stats['total_wait_time_ms'],
            'average_wait_time_ms': avg_wait_time,
            'requests_per_second_actual': actual_rate,
            'configured_requests_per_second': self.requests_per_second,
            'efficiency': actual_rate / self.requests_per_second if self.requests_per_second > 0 else 0
        }


class AsyncDescriptionProcessor:
    """
    Main async description processor with background processing.
    
    Coordinates description processing with rate limiting, queuing,
    and async result handling. Integrates with existing service patterns.
    
    Features:
    - Background processing loop with proper lifecycle management
    - Rate limiting integration to prevent Ollama overload
    - Priority-based request queuing
    - Future-based async result delivery
    - Comprehensive error handling and recovery
    - Statistics and monitoring support
    
    Usage:
        processor = AsyncDescriptionProcessor(description_service)
        await processor.start_processing()
        future = await processor.submit_request(snapshot)
        result = await future
        await processor.stop_processing()
    """
    
    def __init__(
        self,
        description_service: DescriptionService,
        max_queue_size: int = 100,
        rate_limit_per_second: float = 0.5,
        enable_retries: bool = False,
        max_retry_attempts: int = 2
    ):
        """
        Initialize async description processor.
        
        Args:
            description_service: Service for processing descriptions
            max_queue_size: Maximum queue capacity
            rate_limit_per_second: Rate limit for Ollama requests
            enable_retries: Whether to enable retry logic for failed requests
            max_retry_attempts: Maximum number of retry attempts
        """
        if max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
        if rate_limit_per_second <= 0:
            raise ValueError("rate_limit_per_second must be positive")
        if max_retry_attempts < 0:
            raise ValueError("max_retry_attempts must be non-negative")
            
        self.description_service = description_service
        self.queue = ProcessingQueue(max_size=max_queue_size)
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit_per_second)
        self.enable_retries = enable_retries
        self.max_retry_attempts = max_retry_attempts
        
        self.is_running = False
        self._processing_task: Optional[asyncio.Task] = None
        self._result_futures: Dict[str, asyncio.Future] = {}
        
        logger.info(
            f"AsyncDescriptionProcessor initialized: "
            f"queue_size={max_queue_size}, rate={rate_limit_per_second}/sec, "
            f"retries={'enabled' if enable_retries else 'disabled'}"
        )
    
    async def start_processing(self) -> None:
        """Start background processing loop."""
        if self.is_running:
            logger.warning("AsyncDescriptionProcessor already running")
            return
        
        self.is_running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        logger.info("AsyncDescriptionProcessor started")
    
    async def stop_processing(self) -> None:
        """Stop background processing loop and cleanup resources."""
        if not self.is_running:
            logger.debug("AsyncDescriptionProcessor not running, nothing to stop")
            return
        
        logger.info("Stopping AsyncDescriptionProcessor...")
        self.is_running = False
        
        # Cancel processing task
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                logger.debug("Processing task cancelled successfully")
        
        # Cancel any pending futures
        cancelled_count = 0
        for future in self._result_futures.values():
            if not future.done():
                future.cancel()
                cancelled_count += 1
        
        if cancelled_count > 0:
            logger.warning(f"Cancelled {cancelled_count} pending request futures")
        
        self._result_futures.clear()
        logger.info("AsyncDescriptionProcessor stopped")
    
    async def submit_request(
        self, 
        snapshot: Snapshot, 
        priority: int = 1
    ) -> asyncio.Future[ProcessingResult]:
        """
        Submit processing request and return future for result.
        
        Args:
            snapshot: Snapshot to process
            priority: Request priority (1 = highest)
            
        Returns:
            Future that will contain ProcessingResult when complete
            
        Raises:
            RuntimeError: If processor is not running
            ValueError: If priority is invalid
        """
        if not self.is_running:
            raise RuntimeError("AsyncDescriptionProcessor is not running")
        
        if priority < 1:
            raise ValueError("Priority must be >= 1")
        
        request_id = str(uuid.uuid4())
        
        # Create future for result
        result_future = asyncio.Future()
        self._result_futures[request_id] = result_future
        
        # Create and queue request
        request = ProcessingRequest(
            snapshot=snapshot,
            priority=priority,
            timestamp=datetime.now(),
            request_id=request_id
        )
        
        try:
            await self.queue.add_request(request)
            logger.debug(f"Submitted processing request: {request}")
        except Exception as e:
            # Clean up future if queueing failed
            self._result_futures.pop(request_id, None)
            result_future.cancel()
            logger.error(f"Failed to submit request: {e}")
            raise
        
        return result_future
    
    async def _processing_loop(self) -> None:
        """Main background processing loop."""
        logger.info("Starting async description processing loop")
        
        while self.is_running:
            try:
                # Get next request from queue with timeout
                request = await asyncio.wait_for(
                    self.queue.get_next_request(), 
                    timeout=1.0  # Check is_running periodically
                )
                
                # Process request in background to avoid blocking queue
                asyncio.create_task(self._process_request(request))
                
            except asyncio.TimeoutError:
                # No requests in queue, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                await asyncio.sleep(0.1)  # Brief pause on error
        
        logger.info("Async description processing loop ended")
    
    async def _process_request(self, request: ProcessingRequest) -> None:
        """
        Process a single request from the queue.
        
        Handles description generation, error handling, and result publishing.
        Updates queue statistics and performance metrics.
        """
        start_time = time.time()
        
        try:
            # Apply rate limiting
            await self.rate_limiter.acquire()
            
            logger.debug(f"Processing request: {request}")
            
            # Process description with retry logic if enabled
            if self.enable_retries:
                result = await self._process_with_retries(request, start_time)
            else:
                # Single attempt processing
                description_result = await self.description_service.describe_snapshot(request.snapshot)
                result = self._convert_to_processing_result(request, description_result, start_time)
            
            # Mark request completed in queue
            processing_time_ms = int((time.time() - start_time) * 1000)
            self.queue.mark_completed(processing_time_ms)
            
            logger.debug(f"Completed processing request: {request.request_id}")
            
        except Exception as e:
            logger.error(f"Failed processing request {request.request_id}: {e}")
            
            # Mark request failed in queue
            self.queue.mark_failed()
            
            # Create error result
            processing_time_ms = int((time.time() - start_time) * 1000)
            error_result = ProcessingResult(
                request_id=request.request_id,
                description=f"Error: {str(e)}",
                confidence=0.0,
                processing_time_ms=processing_time_ms,
                success=False,
                error=str(e)
            )
            
            result = error_result
        
        # Deliver result to waiting future
        future = self._result_futures.pop(request.request_id, None)
        if future and not future.cancelled():
            future.set_result(result)
        elif future and future.cancelled():
            logger.debug(f"Request {request.request_id} was cancelled before completion")
    
    async def _process_with_retries(self, request: ProcessingRequest, start_time: float) -> 'ProcessingResult':
        """
        Process request with retry logic for recoverable errors.
        
        Args:
            request: Processing request to handle
            start_time: Start time for timing calculations
            
        Returns:
            ProcessingResult with success/error status
        """
        last_error = None
        
        for attempt in range(self.max_retry_attempts + 1):  # +1 for initial attempt
            try:
                description_result = await self.description_service.describe_snapshot(request.snapshot)
                
                # If successful, return result immediately
                if description_result.error is None:
                    return self._convert_to_processing_result(request, description_result, start_time)
                
                # If description service returned error result, check if retryable
                if attempt < self.max_retry_attempts:
                    # For certain error types, we can retry
                    if description_result.error in ["timeout", "service_unavailable"]:
                        # Wait with exponential backoff before retry
                        delay = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s, 4s...
                        await asyncio.sleep(delay)
                        continue
                
                # Not retryable or max attempts reached, return error result
                return self._convert_to_processing_result(request, description_result, start_time)
                
            except (OllamaTimeoutError, OllamaUnavailableError) as e:
                last_error = e
                
                # Check if we should retry
                if attempt < self.max_retry_attempts:
                    # Wait with exponential backoff before retry
                    delay = 0.5 * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Max attempts reached, return error
                    break
            
            except Exception as e:
                # For unexpected errors, don't retry
                last_error = e
                break
        
        # If we get here, all retries failed
        processing_time_ms = int((time.time() - start_time) * 1000)
        return ProcessingResult(
            request_id=request.request_id,
            description=f"Error after {self.max_retry_attempts + 1} attempts: {str(last_error)}",
            confidence=0.0,
            processing_time_ms=processing_time_ms,
            success=False,
            error=str(last_error)
        )
    
    def _convert_to_processing_result(
        self, 
        request: ProcessingRequest, 
        description_result: DescriptionResult, 
        start_time: float
    ) -> 'ProcessingResult':
        """
        Convert DescriptionResult to ProcessingResult.
        
        Args:
            request: Original processing request
            description_result: Result from description service
            start_time: Processing start time
            
        Returns:
            ProcessingResult with consistent format
        """
        return ProcessingResult(
            request_id=request.request_id,
            description=description_result.description,
            confidence=description_result.confidence,
            processing_time_ms=description_result.processing_time_ms,
            success=description_result.error is None,
            error=description_result.error
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        return {
            'is_running': self.is_running,
            'queue_stats': self.queue.get_statistics(),
            'rate_limiter_stats': self.rate_limiter.get_statistics(),
            'pending_futures': len(self._result_futures),
            'has_processing_task': self._processing_task is not None,
            'task_done': self._processing_task.done() if self._processing_task else None
        } 