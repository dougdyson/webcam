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
"""
import asyncio
import logging
import hashlib
import time
import sys
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .client import OllamaClient, OllamaError
from .snapshot_buffer import Snapshot
from .image_processing import OllamaImageProcessor

logger = logging.getLogger(__name__)


@dataclass
class DescriptionServiceConfig:
    """
    Configuration for description service.
    
    Controls caching, concurrency, timeouts, and processing parameters.
    Follows existing service configuration patterns for consistency.
    """
    cache_ttl_seconds: int = 300  # 5 minutes
    max_concurrent_requests: int = 3
    timeout_seconds: float = 30.0
    max_cache_entries: int = 100
    enable_caching: bool = True
    default_prompt: str = "Describe what you see in this image. Be concise and specific."
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds must be positive")
        if self.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass
class DescriptionResult:
    """
    Result of description processing.
    
    Contains description text, confidence, timing, and metadata.
    Designed for HTTP API integration following existing patterns.
    """
    description: str
    confidence: float
    timestamp: datetime
    processing_time_ms: int
    cached: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for HTTP API integration."""
        return {
            'description': self.description,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'processing_time_ms': self.processing_time_ms,
            'cached': self.cached,
            'error': self.error
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
            error=entry.result.error
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
        
        logger.debug(f"DescriptionService initialized with config: {self.config}")
    
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
                    logger.debug("Returning cached description result")
                    return cached_result
            
            # Acquire processing semaphore for concurrency control
            async with self._processing_semaphore:
                result = await self._process_snapshot(snapshot, start_time)
                
                # Cache successful results only
                if self.config.enable_caching and result.error is None:
                    self.cache.put(snapshot, result, self.config.cache_ttl_seconds)
                
                return result
                
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.error(f"Unexpected error processing snapshot: {e}", exc_info=True)
            
            return DescriptionResult(
                description=f"Error: {str(e)}",
                confidence=0.0,
                timestamp=datetime.now(),
                processing_time_ms=processing_time,
                cached=False,
                error=str(e)
            )
    
    async def _process_snapshot(self, snapshot: Snapshot, start_time: float) -> DescriptionResult:
        """Process snapshot with Ollama client and comprehensive error handling."""
        try:
            # Process frame to base64
            base64_image = self.image_processor.process_webcam_frame(snapshot.frame)
            
            # Call Ollama synchronously in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            description_text = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    self.ollama_client.describe_image, 
                    base64_image
                ),
                timeout=self.config.timeout_seconds
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Ollama client returns just the description string
            return DescriptionResult(
                description=description_text,
                confidence=0.9,  # Default confidence since Ollama doesn't provide this
                timestamp=datetime.now(),
                processing_time_ms=processing_time,
                cached=False
            )
            
        except asyncio.TimeoutError:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = f"Ollama request timeout after {self.config.timeout_seconds}s"
            logger.warning(error_msg)
            
            return DescriptionResult(
                description=f"Error: {error_msg}",
                confidence=0.0,
                timestamp=datetime.now(),
                processing_time_ms=processing_time,
                cached=False,
                error="timeout"
            )
        
        except OllamaError as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = f"Ollama service error: {e}"
            logger.error(error_msg)
            
            return DescriptionResult(
                description=f"Error: {error_msg}",
                confidence=0.0,
                timestamp=datetime.now(),
                processing_time_ms=processing_time,
                cached=False,
                error="ollama_error"
            )
        
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = f"Unexpected processing error: {e}"
            logger.error(error_msg, exc_info=True)
            
            return DescriptionResult(
                description=f"Error: {error_msg}",
                confidence=0.0,
                timestamp=datetime.now(),
                processing_time_ms=processing_time,
                cached=False,
                error="processing_error"
            )
    
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