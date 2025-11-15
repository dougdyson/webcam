"""
Vision-based human presence verification using Ollama vision models.

This module provides a lightweight wrapper around OllamaClient specifically
for binary human presence verification. Designed to run periodically (e.g.,
every 30 seconds) to compare against real-time MediaPipe detections.

Key Features:
- Simple yes/no human presence queries
- Frame caching to avoid redundant processing
- Minimal overhead wrapper around OllamaClient
- Structured logging for comparison analysis
"""
import logging
import hashlib
import time
from typing import Optional, Dict, Any
import numpy as np
import cv2

from .client import OllamaClient, OllamaError

logger = logging.getLogger(__name__)


class VisionVerificationResult:
    """Result of a vision-based human presence verification."""

    def __init__(self, human_detected: bool, confidence: str,
                 raw_response: str, timestamp: float):
        """
        Initialize verification result.

        Args:
            human_detected: Whether a human was detected
            confidence: Confidence level description from model
            raw_response: Raw text response from vision model
            timestamp: Unix timestamp of verification
        """
        self.human_detected = human_detected
        self.confidence = confidence
        self.raw_response = raw_response
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for logging/serialization."""
        return {
            "human_detected": self.human_detected,
            "confidence": self.confidence,
            "raw_response": self.raw_response,
            "timestamp": self.timestamp
        }

    def __repr__(self) -> str:
        """Readable string representation."""
        return (f"VisionVerificationResult(human_detected={self.human_detected}, "
                f"confidence='{self.confidence}')")


class VisionPresenceVerifier:
    """
    Vision-based human presence verification using Ollama vision models.

    This class provides a focused interface for binary presence detection,
    designed to complement real-time MediaPipe detections with periodic
    vision model verification.
    """

    # Simple yes/no prompt optimized for binary detection
    DEFAULT_PROMPT = (
        "Is there a person visible in this image? "
        "Answer with only 'yes' or 'no', followed by your confidence level "
        "(certain/likely/uncertain)."
    )

    def __init__(self, ollama_client: OllamaClient, cache_ttl_seconds: int = 30):
        """
        Initialize vision presence verifier.

        Args:
            ollama_client: OllamaClient instance for vision model queries
            cache_ttl_seconds: Time-to-live for cached results (default: 30s)
        """
        self.ollama_client = ollama_client
        self.cache_ttl_seconds = cache_ttl_seconds

        # Simple cache: frame_hash -> (result, timestamp)
        self._cache: Dict[str, tuple[VisionVerificationResult, float]] = {}

        logger.info(f"Initialized VisionPresenceVerifier with {cache_ttl_seconds}s cache TTL")

    def _compute_frame_hash(self, frame: np.ndarray) -> str:
        """
        Compute MD5 hash of frame for caching.

        Args:
            frame: Image frame as numpy array

        Returns:
            MD5 hash as hex string
        """
        # Encode frame to JPEG for consistent hashing
        _, buffer = cv2.imencode('.jpg', frame)
        return hashlib.md5(buffer.tobytes()).hexdigest()

    def _parse_response(self, response: str) -> tuple[bool, str]:
        """
        Parse vision model response into boolean detection and confidence.

        Args:
            response: Raw text response from vision model

        Returns:
            Tuple of (human_detected, confidence_level)
        """
        response_lower = response.lower().strip()

        # Detect human presence from response
        human_detected = False
        if response_lower.startswith('yes'):
            human_detected = True
        elif response_lower.startswith('no'):
            human_detected = False
        else:
            # Try to find yes/no anywhere in response
            if 'yes' in response_lower and 'no' not in response_lower:
                human_detected = True
                logger.warning(f"Non-standard yes response: {response[:50]}")
            elif 'no' in response_lower and 'yes' not in response_lower:
                human_detected = False
                logger.warning(f"Non-standard no response: {response[:50]}")
            else:
                logger.warning(f"Ambiguous response, defaulting to False: {response[:50]}")
                human_detected = False

        # Extract confidence level (check uncertain before certain to avoid substring match)
        confidence = "unknown"
        if 'uncertain' in response_lower:
            confidence = "uncertain"
        elif 'certain' in response_lower:
            confidence = "certain"
        elif 'likely' in response_lower:
            confidence = "likely"

        return human_detected, confidence

    def verify_human_presence(self, frame: np.ndarray,
                             prompt: Optional[str] = None) -> Optional[VisionVerificationResult]:
        """
        Verify human presence in frame using vision model.

        Args:
            frame: Image frame as numpy array (BGR format from OpenCV)
            prompt: Optional custom prompt (uses DEFAULT_PROMPT if None)

        Returns:
            VisionVerificationResult if successful, None if verification fails
        """
        # Check cache first (handle encoding errors during hash computation)
        try:
            frame_hash = self._compute_frame_hash(frame)
        except Exception as e:
            logger.error(f"Failed to compute frame hash: {e}")
            return None

        current_time = time.time()

        if frame_hash in self._cache:
            cached_result, cached_time = self._cache[frame_hash]
            age = current_time - cached_time

            if age < self.cache_ttl_seconds:
                logger.debug(f"Using cached verification result (age: {age:.1f}s)")
                return cached_result
            else:
                # Remove stale cache entry
                del self._cache[frame_hash]

        # Resize frame for faster processing (binary detection doesn't need high res)
        # 320x240 is plenty for "is there a human yes/no"
        try:
            resized = cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA)
            _, buffer = cv2.imencode('.jpg', resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
            image_bytes = buffer.tobytes()
        except Exception as e:
            logger.error(f"Failed to encode frame: {e}")
            return None

        # Query vision model
        try:
            query_prompt = prompt or self.DEFAULT_PROMPT
            response = self.ollama_client.describe_image(image_bytes, query_prompt)

            # Parse response
            human_detected, confidence = self._parse_response(response)

            # Create result
            result = VisionVerificationResult(
                human_detected=human_detected,
                confidence=confidence,
                raw_response=response,
                timestamp=current_time
            )

            # Cache result
            self._cache[frame_hash] = (result, current_time)

            # Clean old cache entries (simple LRU)
            self._cleanup_cache(current_time)

            logger.debug(f"Vision verification: {result}")
            return result

        except OllamaError as e:
            logger.error(f"Vision verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during vision verification: {e}")
            return None

    def _cleanup_cache(self, current_time: float, max_cache_size: int = 10):
        """
        Remove stale and excess cache entries.

        Args:
            current_time: Current timestamp
            max_cache_size: Maximum number of cached entries to keep
        """
        # Remove stale entries
        stale_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self.cache_ttl_seconds
        ]
        for key in stale_keys:
            del self._cache[key]

        # If still too many entries, remove oldest
        if len(self._cache) > max_cache_size:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda item: item[1][1]  # Sort by timestamp
            )
            # Keep only the newest max_cache_size entries
            self._cache = dict(sorted_entries[-max_cache_size:])

    def clear_cache(self):
        """Clear all cached verification results."""
        self._cache.clear()
        logger.debug("Cleared vision verification cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for monitoring.

        Returns:
            Dictionary with cache size and age information
        """
        if not self._cache:
            return {"size": 0, "oldest_age": 0, "newest_age": 0}

        current_time = time.time()
        ages = [current_time - timestamp for _, timestamp in self._cache.values()]

        return {
            "size": len(self._cache),
            "oldest_age": max(ages) if ages else 0,
            "newest_age": min(ages) if ages else 0
        }
