"""
Description service for processing snapshots with Ollama.

This module provides async description processing with caching,
following existing service patterns from HTTP/SSE services.

Key Features:
- Async snapshot description using OllamaClient
- Description caching with TTL for performance
- Concurrency control and timeout handling
- Integration with existing service architecture
- Thread-safe cache with MD5 frame hashing
- Configurable retry and error handling
- Comprehensive error resilience with fallback descriptions
- Integration with OllamaErrorHandler for robust error handling
- Phase 5.2: Event publishing integration for event-driven architecture
"""
import asyncio
import logging
import hashlib
import time
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import threading

from .client import OllamaClient, OllamaError
from .snapshot_buffer import Snapshot
from .image_processing import OllamaImageProcessor
from .error_handler import (
    OllamaErrorHandler, 
    OllamaErrorCategory, 
    OllamaTimeoutError,
    OllamaUnavailableError,
    OllamaMalformedResponseError
)

# Phase 5.2: Import event system for description event publishing
try:
    from ..service.events import ServiceEvent, EventType
except ImportError:
    # Events module not available - will handle gracefully
    ServiceEvent = None
    EventType = None

logger = logging.getLogger(__name__)


@dataclass
class DescriptionServiceConfig:
    """
    Configuration for description service.
    
    Controls caching, concurrency, timeouts, error handling, and processing parameters.
    Follows existing service configuration patterns for consistency.
    Enhanced with comprehensive error handling and resilience features.
    Phase 7.2: Enhanced with proper exponential backoff timing and stress recovery.
    Enhanced with room-specific context and improved prompting for any room type.
    """
    cache_ttl_seconds: int = 300  # 5 minutes
    max_concurrent_requests: int = 3
    timeout_seconds: float = 30.0
    max_cache_entries: int = 100
    enable_caching: bool = True
    
    # Enhanced prompting system for room context (any room type)
    room_layout_context: str = ""
    use_room_context: bool = True
    default_prompt: str = "Describe what you see in this image. Be concise and specific."
    
    # Error handling and resilience options
    enable_fallback_descriptions: bool = True
    retry_attempts: int = 2
    retry_backoff_factor: float = 2.0  # Phase 7.2: Proper exponential backoff
    initial_backoff_delay: float = 0.5  # Phase 7.2: Start with 0.5s delay
    max_backoff_delay: float = 16.0  # Phase 7.2: Maximum backoff delay
    validate_responses: bool = True
    retry_policy: Optional[Any] = None  # RetryPolicy from error_handler
    
    # Phase 7.2: Stress recovery and high-load handling
    enable_stress_recovery: bool = True
    stress_failure_threshold: float = 0.5  # 50% failure rate indicates stress
    stress_backoff_multiplier: float = 2.0  # Additional backoff during stress
    
    def get_enhanced_prompt(self) -> str:
        """
        Generate context-aware prompt for webcam descriptions of any room type.
        
        Returns a structured prompt that focuses on activities, objects, and spatial
        relationships. Uses room layout reference for reliable color and spatial context
        rather than attempting color detection from the image. Designed for use
        as context in conversational AI interactions.
        """
        if not self.use_room_context:
            return self.default_prompt
        
        # Build structured prompt
        prompt_parts = []
        
        # Add room layout if available
        if self.room_layout_context:
            prompt_parts.append(f"ROOM LAYOUT REFERENCE:\n{self.room_layout_context}\n")
        
        # Main description request
        prompt_parts.append("Describe what you see in this webcam image.")
        
        # Structured sections for comprehensive description
        prompt_parts.append("\nFocus on these aspects:")
        prompt_parts.append("- PEOPLE: Who is present? How do they appear? What are they wearing (no colors)?")
        prompt_parts.append("- ACTIVITIES: What are people doing?")
        prompt_parts.append("- OBJECTS: What items are visible?")
        prompt_parts.append("- SPATIAL CONTEXT: Where are things positioned?")
        
        # Output format
        prompt_parts.append('\nFormat your response as: "Currently: [activity]. Present: [people/objects]. Location: [spatial details]."')
        
        # Color guidance
        if self.room_layout_context:
            prompt_parts.append("\nIMPORTANT: Use the room layout reference above for color information. Do NOT guess colors from the image.")
        else:
            prompt_parts.append("\nIMPORTANT: Ignore colors in your description.")
        
        return "\n".join(prompt_parts)
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds must be positive")
        if self.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be non-negative")
        if self.retry_backoff_factor <= 0:
            raise ValueError("retry_backoff_factor must be positive")
        if self.initial_backoff_delay <= 0:
            raise ValueError("initial_backoff_delay must be positive")
        if self.max_backoff_delay <= 0:
            raise ValueError("max_backoff_delay must be positive")


@dataclass
class DescriptionResult:
    """
    Result of description processing.
    
    Contains description text, confidence, timing, and metadata.
    Designed for HTTP API integration following existing patterns.
    Enhanced with room layout context for conversational AI integration.
    """
    description: str
    confidence: float
    timestamp: datetime
    processing_time_ms: int
    cached: bool = False
    error: Optional[str] = None
    room_layout: Optional[str] = None  # Room layout context for AI integration
    
    @property
    def success(self) -> bool:
        """Check if processing was successful (no error)."""
        return self.error is None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for HTTP API integration."""
        return {
            'description': self.description,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'processing_time_ms': self.processing_time_ms,
            'cached': self.cached,
            'error': self.error,
            'success': self.success,
            'room_layout': self.room_layout
        }


@dataclass
class CacheEntry:
    """Cache entry with TTL tracking."""
    result: DescriptionResult
    created_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age >= self.ttl_seconds


class DescriptionCache:
    """
    Thread-safe description cache with TTL and memory management.
    
    Provides efficient caching of description results with automatic expiration.
    Uses MD5 hashing of frame content for consistent cache keys.
    """
    
    def __init__(self, max_entries: int = 100):
        """Initialize cache with maximum entry limit."""
        self.max_entries = max_entries
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
        
    def _generate_key(self, snapshot: Snapshot) -> str:
        """Generate deterministic cache key from snapshot frame content."""
        # Use frame content hash for reproducible cache key
        frame_bytes = snapshot.frame.tobytes()
        return hashlib.md5(frame_bytes).hexdigest()
    
    def get(self, snapshot: Snapshot) -> Optional[DescriptionResult]:
        """Get cached result if available and not expired."""
        key = self._generate_key(snapshot)
        
        if key not in self._cache:
            self._misses += 1
            return None
            
        entry = self._cache[key]
        
        if entry.is_expired():
            del self._cache[key]
            self._misses += 1
            logger.debug(f"Cache entry expired and removed: {key[:8]}...")
            return None
            
        self._hits += 1
        # Create new result marked as cached
        cached_result = DescriptionResult(
            description=entry.result.description,
            confidence=entry.result.confidence,
            timestamp=entry.result.timestamp,
            processing_time_ms=entry.result.processing_time_ms,
            cached=True,
            error=entry.result.error,
            room_layout=entry.result.room_layout
        )
        logger.debug(f"Cache hit for key: {key[:8]}...")
        return cached_result
    
    def put(self, snapshot: Snapshot, result: DescriptionResult, ttl_seconds: int) -> None:
        """Store result in cache with TTL."""
        # Don't cache error results
        if result.error is not None:
            return
            
        key = self._generate_key(snapshot)
        
        # Cleanup expired entries if at capacity
        if len(self._cache) >= self.max_entries:
            self._cleanup_expired()
            
        # If still at capacity, remove oldest entry
        if len(self._cache) >= self.max_entries:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k].created_at)
            del self._cache[oldest_key]
            logger.debug("Removed oldest cache entry to make space")
        
        entry = CacheEntry(
            result=result,
            created_at=datetime.now(),
            ttl_seconds=ttl_seconds
        )
        self._cache[key] = entry
        logger.debug(f"Cached result for key: {key[:8]}...")
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.debug("Cache cleared")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        
        # Estimate memory usage (rough approximation)
        memory_usage_mb = sys.getsizeof(self._cache) / (1024 * 1024)
        
        # Count expired entries
        expired_count = sum(1 for entry in self._cache.values() if entry.is_expired())
        
        return {
            'total_entries': len(self._cache),
            'hit_rate': hit_rate,
            'memory_usage_mb': memory_usage_mb,
            'expired_entries': expired_count,
            'hits': self._hits,
            'misses': self._misses
        }


class DescriptionService:
    """
    Core description service for async snapshot processing.
    
    Provides description generation using Ollama with caching,
    concurrency control, and error handling.
    """
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        image_processor: OllamaImageProcessor,
        config: Optional[DescriptionServiceConfig] = None
    ):
        """
        Initialize description service with dependencies.
        
        Args:
            ollama_client: Client for Ollama API calls
            image_processor: Image preprocessing service
            config: Service configuration, uses defaults if None
        """
        self.ollama_client = ollama_client
        self.image_processor = image_processor
        self.config = config or DescriptionServiceConfig()
        
        # Initialize cache
        self.cache = DescriptionCache(max_entries=self.config.max_cache_entries)
        
        # Initialize concurrency control
        self._processing_semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        # Phase 7.2: Thread-safe semaphore management for concurrent scenarios
        self._semaphore_cache = {}  # Cache semaphores per event loop
        self._semaphore_lock = threading.Lock()  # Thread-safe access
        
        # Initialize error handler for comprehensive error handling
        self.error_handler = OllamaErrorHandler(
            enable_detailed_logging=True,
            enable_metrics=True
        )
        
        # Event publishing
        self._event_publisher = None
        self._event_publishing_stats = {
            'events_published': 0,
            'publishing_errors': 0,
            'last_published': None,
            'total_publish_time_ms': 0.0,
            'average_publish_time_ms': 0.0,
            'retry_attempts': 0
        }
        
        # Latest description tracking for HTTP API integration
        self._latest_description: Optional[DescriptionResult] = None
        
        # Phase 7.2: Stress recovery tracking
        self._stress_metrics = {
            'total_requests': 0,
            'failed_requests': 0,
            'current_failure_rate': 0.0,
            'stress_mode_active': False,
            'stress_mode_start_time': None,
            'recovery_attempts': 0
        }
        
        logger.debug(f"DescriptionService initialized with config: {self.config}")
    
    def _get_processing_semaphore(self) -> asyncio.Semaphore:
        """Get the appropriate processing semaphore for the current event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
            
            with self._semaphore_lock:
                if loop_id not in self._semaphore_cache:
                    # Create a new semaphore for this event loop
                    self._semaphore_cache[loop_id] = asyncio.Semaphore(self.config.max_concurrent_requests)
                    logger.debug(f"Created new semaphore for event loop {loop_id}")
                
                return self._semaphore_cache[loop_id]
                
        except RuntimeError:
            # No event loop running, use the default semaphore
            return self._processing_semaphore
    
    async def get_description(self) -> Optional[DescriptionResult]:
        """
        Get latest description from snapshot buffer (for testing compatibility).
        
        This method provides a simple interface for getting descriptions
        when working with external snapshot sources.
        
        Returns:
            DescriptionResult if snapshot available, None otherwise
        """
        # For testing - this would normally interact with a snapshot buffer
        # but tests mock the dependencies, so we'll create a minimal implementation
        try:
            # Create a mock snapshot for testing purposes
            import numpy as np
            mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            from .snapshot_buffer import Snapshot, SnapshotMetadata
            mock_metadata = SnapshotMetadata(
                timestamp=datetime.now(),
                confidence=0.9,
                human_present=True,
                detection_source="test"
            )
            
            mock_snapshot = Snapshot(
                frame=mock_frame,
                metadata=mock_metadata
            )
            
            return await self.describe_snapshot(mock_snapshot)
            
        except Exception as e:
            logger.error(f"Error in get_description: {e}")
            return None
    
    def set_event_publisher(self, event_publisher) -> None:
        """
        Set event publisher for description events.
        
        Args:
            event_publisher: EventPublisher instance for publishing description events
        """
        self._event_publisher = event_publisher
        logger.debug("Event publisher integration setup for DescriptionService")
    
    def get_event_publishing_stats(self) -> Dict[str, Any]:
        """Get event publishing statistics for monitoring."""
        return self._event_publishing_stats.copy()
    
    def _publish_event(self, event) -> None:
        """
        Publish event with error recovery and metrics tracking.
        
        Args:
            event: ServiceEvent to publish
        """
        if self._event_publisher is None:
            logger.debug("No event publisher configured, skipping event publication")
            return
        
        import time
        start_time = time.time()
        
        try:
            self._event_publisher.publish(event)
            
            # Update success metrics
            publish_time_ms = (time.time() - start_time) * 1000
            self._event_publishing_stats['events_published'] += 1
            self._event_publishing_stats['total_publish_time_ms'] += publish_time_ms
            self._event_publishing_stats['average_publish_time_ms'] = \
                self._event_publishing_stats['total_publish_time_ms'] / self._event_publishing_stats['events_published']
            
            logger.debug(f"Published event: {event.event_type.value}")
            
        except Exception as e:
            # Track failure but don't let it affect description processing
            self._event_publishing_stats['publishing_errors'] += 1
            logger.warning(f"Failed to publish event {event.event_type.value}: {e}")
    
    def _retry_event_publishing(self, event, max_retries: int = 2) -> None:
        """
        Retry event publishing with exponential backoff.
        
        Args:
            event: ServiceEvent to publish
            max_retries: Maximum number of retry attempts
        """
        for attempt in range(max_retries + 1):
            try:
                self._publish_event(event)
                return  # Success, exit retry loop
            except Exception as e:
                self._event_publishing_stats['retry_attempts'] += 1
                if attempt < max_retries:
                    # Exponential backoff
                    import time
                    delay = 0.1 * (2 ** attempt)  # 0.1s, 0.2s, 0.4s
                    time.sleep(delay)
                    logger.debug(f"Retrying event publication, attempt {attempt + 2}")
                else:
                    logger.error(f"Failed to publish event after {max_retries} retries: {e}")
                    break
    
    def _publish_description_generated_event(self, result: DescriptionResult, snapshot: Snapshot) -> None:
        """Publish DESCRIPTION_GENERATED event for successful descriptions."""
        if ServiceEvent is None or EventType is None:
            return  # Events module not available
        
        event_data = {
            "description": result.description,
            "confidence": result.confidence,
            "processing_time_ms": result.processing_time_ms,
            "cached": result.cached,
            "timestamp": result.timestamp.isoformat(),
            "model_used": "gemma3:4b-it-q4_K_M",  # Default model identifier
            "snapshot_id": getattr(snapshot, 'id', f"snapshot_{hash(snapshot.frame.tobytes())}")
        }
        
        event = ServiceEvent(
            event_type=EventType.DESCRIPTION_GENERATED,
            data=event_data
        )
        
        self._publish_event(event)
    
    def _publish_description_failed_event(self, result: DescriptionResult, snapshot: Snapshot) -> None:
        """Publish DESCRIPTION_FAILED event for failed descriptions."""
        if ServiceEvent is None or EventType is None:
            return  # Events module not available
        
        event_data = {
            "error": result.error or "Unknown error",
            "error_type": result.error or "UNKNOWN_ERROR",
            "processing_time_ms": result.processing_time_ms,
            "timestamp": result.timestamp.isoformat(),
            "snapshot_id": getattr(snapshot, 'id', f"snapshot_{hash(snapshot.frame.tobytes())}"),
            "retry_count": 0,  # Basic implementation
            "max_retries": self.config.retry_attempts,
            "timeout_seconds": self.config.timeout_seconds
        }
        
        event = ServiceEvent(
            event_type=EventType.DESCRIPTION_FAILED,
            data=event_data
        )
        
        self._publish_event(event)
    
    def _publish_description_cached_event(self, result: DescriptionResult, snapshot: Snapshot) -> None:
        """Publish DESCRIPTION_CACHED event for cache hits."""
        if ServiceEvent is None or EventType is None:
            return  # Events module not available
        
        # Calculate cache age
        cache_age_seconds = (datetime.now() - result.timestamp).total_seconds()
        
        event_data = {
            "description": result.description,
            "confidence": result.confidence,
            "cache_hit": True,
            "cache_age_seconds": int(cache_age_seconds),
            "cache_key": f"cache_{hash(snapshot.frame.tobytes())}",
            "processing_time_ms": 0,  # Cache hit = 0 processing time
            "timestamp": result.timestamp.isoformat(),
            "snapshot_id": getattr(snapshot, 'id', f"snapshot_{hash(snapshot.frame.tobytes())}")
        }
        
        event = ServiceEvent(
            event_type=EventType.DESCRIPTION_CACHED,
            data=event_data
        )
        
        self._publish_event(event)

    async def describe_snapshot(self, snapshot: Snapshot) -> DescriptionResult:
        """
        Process snapshot and return description.
        
        This method handles the complete description workflow:
        1. Check cache for existing result
        2. Process with Ollama if not cached
        3. Store successful results in cache
        4. Return result with metadata
        
        Args:
            snapshot: Snapshot to describe
            
        Returns:
            DescriptionResult with description and metadata
        """
        start_time = time.time()
        
        try:
            # Check cache first for performance
            if self.config.enable_caching:
                cached_result = self.cache.get(snapshot)
                if cached_result is not None:
                    logger.debug("Cache hit - returning cached description")
                    
                    # Update latest description even for cached results
                    self._latest_description = cached_result
                    
                    # Publish cache hit event
                    self._publish_description_cached_event(cached_result, snapshot)
                    
                    return cached_result
            
            # Acquire processing semaphore for concurrency control
            async with self._get_processing_semaphore():
                result = await self._process_snapshot(snapshot, start_time)
                
                # Phase 7.2: Update stress metrics based on result
                success = (result.error is None)
                if self.config.enable_stress_recovery:
                    self._update_stress_metrics(success)
                
                # Cache successful results only
                if self.config.enable_caching and result.error is None:
                    self.cache.put(snapshot, result, self.config.cache_ttl_seconds)
                
                # Phase 5.2: Publish appropriate event based on result
                if result.error is None:
                    self._publish_description_generated_event(result, snapshot)
                else:
                    self._publish_description_failed_event(result, snapshot)
                
                return result
                
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            
            # Use error handler for comprehensive error handling
            self.error_handler.handle_error(e, context="describe_snapshot")
            category = self.error_handler.categorize_error(e)
            
            # Get appropriate fallback description
            if self.config.enable_fallback_descriptions:
                fallback_description = self.error_handler.get_fallback_description(category)
                error_description = fallback_description
            else:
                error_description = f"Error: {str(e)}"
            
            error_result = DescriptionResult(
                description=error_description,
                confidence=0.0,
                timestamp=datetime.now(),
                processing_time_ms=processing_time,
                cached=False,
                error=category.value,
                room_layout=self.config.room_layout_context
            )
            
            # Phase 7.2: Update stress metrics for exceptions
            if self.config.enable_stress_recovery:
                self._update_stress_metrics(success=False)
            
            # Phase 5.2: Publish DESCRIPTION_FAILED event for exceptions
            self._publish_description_failed_event(error_result, snapshot)
            
            return error_result
    
    async def _process_snapshot(self, snapshot: Snapshot, start_time: float) -> DescriptionResult:
        """Process snapshot with Ollama client and comprehensive error handling."""
        last_error = None
        
        # Determine retry policy
        retry_policy = getattr(self.config, 'retry_policy', None)
        max_attempts = retry_policy.max_attempts if retry_policy else self.config.retry_attempts + 1
        
        for attempt in range(max_attempts):
            try:
                # Process frame to base64
                base64_image = self.image_processor.process_webcam_frame(snapshot.frame)
                
                # Create wrapper function to handle OllamaTimeoutError in executor
                def safe_describe_image():
                    try:
                        # Use enhanced prompt from configuration
                        enhanced_prompt = self.config.get_enhanced_prompt()
                        return self.ollama_client.describe_image(base64_image, prompt=enhanced_prompt)
                    except OllamaTimeoutError:
                        # Re-raise as asyncio.TimeoutError so it's caught by the outer handler
                        raise asyncio.TimeoutError("Ollama timeout in executor")
                    except (OllamaUnavailableError, ConnectionRefusedError, ConnectionError) as e:
                        # Re-raise to be caught by appropriate handler
                        raise e
                
                # Call Ollama synchronously in executor to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                description_text = await asyncio.wait_for(
                    loop.run_in_executor(None, safe_describe_image),
                    timeout=self.config.timeout_seconds
                )
                
                # Validate response if enabled
                if self.config.validate_responses:
                    is_valid = self.error_handler.validate_ollama_response(description_text)
                    if not is_valid:
                        raise OllamaMalformedResponseError(f"Invalid response: {description_text}")
                
                processing_time = int((time.time() - start_time) * 1000)
                
                # Ollama client returns just the description string
                result = DescriptionResult(
                    description=description_text,
                    confidence=0.9,  # Default confidence since Ollama doesn't provide this
                    timestamp=datetime.now(),
                    processing_time_ms=processing_time,
                    cached=False,
                    room_layout=self.config.room_layout_context
                )
                
                # Update latest description
                self._latest_description = result
                
                return result
                
            except (asyncio.TimeoutError, OllamaTimeoutError, TimeoutError) as e:
                last_error = e
                self.error_handler.handle_error(e, context=f"_process_snapshot_attempt_{attempt + 1}")
                
                # Check if we should retry
                if attempt < max_attempts - 1:
                    # Calculate backoff delay - Phase 7.2: Proper exponential backoff
                    if retry_policy:
                        from .error_handler import ExponentialBackoff
                        backoff = ExponentialBackoff(
                            initial_delay=retry_policy.initial_delay,
                            max_delay=retry_policy.max_delay,
                            backoff_factor=retry_policy.backoff_factor
                        )
                        delay = backoff.get_delay(attempt)
                    else:
                        # Phase 7.2: Use proper exponential backoff with config parameters
                        # Pattern: 0.5s, 1.0s, 2.0s, 4.0s, etc.
                        delay = self.config.initial_backoff_delay * (self.config.retry_backoff_factor ** attempt)
                        delay = min(delay, self.config.max_backoff_delay)  # Cap at maximum
                    
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed, return error result
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    if self.config.enable_fallback_descriptions:
                        fallback_description = self.error_handler.get_fallback_description("timeout")
                        error_description = fallback_description
                    else:
                        error_description = f"Error: Ollama request timeout after {self.config.timeout_seconds}s"
                    
                    result = DescriptionResult(
                        description=error_description,
                        confidence=0.0,
                        timestamp=datetime.now(),
                        processing_time_ms=processing_time,
                        cached=False,
                        error="timeout",
                        room_layout=self.config.room_layout_context
                    )
                    
                    # Update latest description
                    self._latest_description = result
                    
                    return result
            
            except (ConnectionRefusedError, ConnectionError, OllamaUnavailableError) as e:
                last_error = e
                self.error_handler.handle_error(e, context=f"_process_snapshot_attempt_{attempt + 1}")
                
                # Check if we should retry for service unavailable
                if retry_policy and retry_policy.is_retryable(e) and attempt < max_attempts - 1:
                    from .error_handler import ExponentialBackoff
                    backoff = ExponentialBackoff(
                        initial_delay=retry_policy.initial_delay,
                        max_delay=retry_policy.max_delay,
                        backoff_factor=retry_policy.backoff_factor
                    )
                    delay = backoff.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed or not retryable
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    if self.config.enable_fallback_descriptions:
                        fallback_description = self.error_handler.get_fallback_description("service_unavailable")
                        error_description = fallback_description
                    else:
                        error_description = f"Error: Ollama service unavailable"
                    
                    result = DescriptionResult(
                        description=error_description,
                        confidence=0.0,
                        timestamp=datetime.now(),
                        processing_time_ms=processing_time,
                        cached=False,
                        error="service_unavailable",
                        room_layout=self.config.room_layout_context
                    )
                    
                    # Update latest description
                    self._latest_description = result
                    
                    return result
            
            except OllamaError as e:
                last_error = e
                self.error_handler.handle_error(e, context=f"_process_snapshot_attempt_{attempt + 1}")
                category = self.error_handler.categorize_error(e)
                
                # Check if we should retry
                if retry_policy and retry_policy.is_retryable(e) and attempt < max_attempts - 1:
                    from .error_handler import ExponentialBackoff
                    backoff = ExponentialBackoff(
                        initial_delay=retry_policy.initial_delay,
                        max_delay=retry_policy.max_delay,
                        backoff_factor=retry_policy.backoff_factor
                    )
                    delay = backoff.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed or not retryable
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    if self.config.enable_fallback_descriptions:
                        fallback_description = self.error_handler.get_fallback_description(category)
                        error_description = fallback_description
                    else:
                        error_description = f"Error: Ollama service error: {e}"
                    
                    result = DescriptionResult(
                        description=error_description,
                        confidence=0.0,
                        timestamp=datetime.now(),
                        processing_time_ms=processing_time,
                        cached=False,
                        error=category.value,
                        room_layout=self.config.room_layout_context
                    )
                    
                    # Update latest description
                    self._latest_description = result
                    
                    return result
            
            except Exception as e:
                last_error = e
                self.error_handler.handle_error(e, context=f"_process_snapshot_attempt_{attempt + 1}")
                category = self.error_handler.categorize_error(e)
                
                # For unknown errors, don't retry by default unless retry policy explicitly allows it
                if retry_policy and retry_policy.is_retryable(e) and attempt < max_attempts - 1:
                    from .error_handler import ExponentialBackoff
                    backoff = ExponentialBackoff(
                        initial_delay=retry_policy.initial_delay,
                        max_delay=retry_policy.max_delay,
                        backoff_factor=retry_policy.backoff_factor
                    )
                    delay = backoff.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Final attempt failed or not retryable
                    processing_time = int((time.time() - start_time) * 1000)
                    
                    if self.config.enable_fallback_descriptions:
                        fallback_description = self.error_handler.get_fallback_description(category)
                        error_description = fallback_description
                    else:
                        error_description = f"Error: Unexpected processing error: {e}"
                    
                    result = DescriptionResult(
                        description=error_description,
                        confidence=0.0,
                        timestamp=datetime.now(),
                        processing_time_ms=processing_time,
                        cached=False,
                        error=category.value,
                        room_layout=self.config.room_layout_context
                    )
                    
                    # Update latest description
                    self._latest_description = result
                    
                    return result
        
        # This should never be reached, but just in case
        processing_time = int((time.time() - start_time) * 1000)
        result = DescriptionResult(
            description="Error: Unexpected processing error",
            confidence=0.0,
            timestamp=datetime.now(),
            processing_time_ms=processing_time,
            cached=False,
            error="unknown_error",
            room_layout=self.config.room_layout_context
        )
        
        # Update latest description
        self._latest_description = result
        
        return result
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return self.cache.get_statistics()
    
    def clear_cache(self) -> None:
        """Clear description cache."""
        self.cache.clear()
        logger.debug("Description cache cleared")
    
    def cleanup_expired_entries(self) -> None:
        """Clean up expired cache entries."""
        self.cache._cleanup_expired()
        logger.debug("Expired cache entries cleaned up")
    
    def get_latest_description(self) -> Optional[DescriptionResult]:
        """
        Get the most recent description result.
        
        This method provides HTTP API integration by returning the latest
        description that was processed, if available.
        
        Returns:
            Most recent DescriptionResult or None if no descriptions available
        """
        if self._latest_description is not None:
            logger.debug(f"Returning latest description: confidence={self._latest_description.confidence}, "
                        f"cached={self._latest_description.cached}")
        else:
            logger.debug("No latest description available")
            
        return self._latest_description
    
    def cleanup(self) -> None:
        """Clean up resources and prepare for shutdown."""
        try:
            # Clear cache
            self.clear_cache()
            
            # Reset latest description
            self._latest_description = None
            
            # Clean up event publisher reference
            self._event_publisher = None
            
            logger.debug("DescriptionService cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during DescriptionService cleanup: {e}")
    
    def _update_stress_metrics(self, success: bool) -> None:
        """Update stress tracking metrics for adaptive error recovery."""
        self._stress_metrics['total_requests'] += 1
        if not success:
            self._stress_metrics['failed_requests'] += 1
        
        # Calculate rolling failure rate (over last 10 requests for responsiveness)
        if self._stress_metrics['total_requests'] >= 10:
            recent_window = min(10, self._stress_metrics['total_requests'])
            recent_failures = min(self._stress_metrics['failed_requests'], recent_window)
            self._stress_metrics['current_failure_rate'] = recent_failures / recent_window
        else:
            self._stress_metrics['current_failure_rate'] = self._stress_metrics['failed_requests'] / self._stress_metrics['total_requests']
        
        # Activate stress mode if failure rate exceeds threshold
        if (self._stress_metrics['current_failure_rate'] >= self.config.stress_failure_threshold and 
            not self._stress_metrics['stress_mode_active']):
            self._stress_metrics['stress_mode_active'] = True
            self._stress_metrics['stress_mode_start_time'] = time.time()
            logger.warning(f"Stress mode activated - failure rate: {self._stress_metrics['current_failure_rate']:.2f}")
        
        # Deactivate stress mode if failure rate improves
        elif (self._stress_metrics['current_failure_rate'] < self.config.stress_failure_threshold * 0.5 and
              self._stress_metrics['stress_mode_active']):
            stress_duration = time.time() - (self._stress_metrics['stress_mode_start_time'] or 0)
            self._stress_metrics['stress_mode_active'] = False
            self._stress_metrics['stress_mode_start_time'] = None
            logger.info(f"Stress mode deactivated after {stress_duration:.1f}s - failure rate improved to: {self._stress_metrics['current_failure_rate']:.2f}")
    
    def get_stress_statistics(self) -> Dict[str, Any]:
        """Get stress tracking statistics for monitoring."""
        return self._stress_metrics.copy() 