"""
Tests for VisionPresenceVerifier integration.

Tests vision-based human presence verification using Ollama vision models.
"""
import pytest
import numpy as np
import time
from unittest.mock import Mock, MagicMock, patch

from src.ollama.vision_verifier import VisionPresenceVerifier, VisionVerificationResult
from src.ollama.client import OllamaClient, OllamaConfig, OllamaError


class TestVisionVerificationResult:
    """Test suite for VisionVerificationResult data class."""

    def test_result_initialization(self):
        """Test VisionVerificationResult initialization with all fields."""
        timestamp = time.time()
        result = VisionVerificationResult(
            human_detected=True,
            confidence="certain",
            raw_response="yes, certain",
            timestamp=timestamp
        )

        assert result.human_detected is True
        assert result.confidence == "certain"
        assert result.raw_response == "yes, certain"
        assert result.timestamp == timestamp

    def test_result_to_dict(self):
        """Test conversion of result to dictionary."""
        timestamp = time.time()
        result = VisionVerificationResult(
            human_detected=False,
            confidence="likely",
            raw_response="no, likely",
            timestamp=timestamp
        )

        result_dict = result.to_dict()

        assert result_dict["human_detected"] is False
        assert result_dict["confidence"] == "likely"
        assert result_dict["raw_response"] == "no, likely"
        assert result_dict["timestamp"] == timestamp

    def test_result_repr(self):
        """Test string representation of result."""
        result = VisionVerificationResult(
            human_detected=True,
            confidence="uncertain",
            raw_response="yes, uncertain",
            timestamp=time.time()
        )

        repr_str = repr(result)

        assert "VisionVerificationResult" in repr_str
        assert "human_detected=True" in repr_str
        assert "confidence='uncertain'" in repr_str


class TestVisionPresenceVerifierInit:
    """Test suite for VisionPresenceVerifier initialization."""

    def test_init_with_default_cache_ttl(self):
        """Test initialization with default cache TTL."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        assert verifier.ollama_client == mock_client
        assert verifier.cache_ttl_seconds == 30
        assert len(verifier._cache) == 0

    def test_init_with_custom_cache_ttl(self):
        """Test initialization with custom cache TTL."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client, cache_ttl_seconds=60)

        assert verifier.ollama_client == mock_client
        assert verifier.cache_ttl_seconds == 60

    def test_default_prompt_format(self):
        """Test that default prompt is properly formatted."""
        assert "person" in VisionPresenceVerifier.DEFAULT_PROMPT.lower()
        assert "yes" in VisionPresenceVerifier.DEFAULT_PROMPT.lower()
        assert "no" in VisionPresenceVerifier.DEFAULT_PROMPT.lower()


class TestVisionPresenceVerifierCaching:
    """Test suite for VisionPresenceVerifier caching behavior."""

    def test_frame_hash_computation(self):
        """Test MD5 hash computation for frames."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        hash1 = verifier._compute_frame_hash(frame)

        # Same frame should produce same hash
        hash2 = verifier._compute_frame_hash(frame)
        assert hash1 == hash2

        # Different frame should produce different hash
        frame_different = np.ones((480, 640, 3), dtype=np.uint8)
        hash3 = verifier._compute_frame_hash(frame_different)
        assert hash1 != hash3

    def test_cache_hit_within_ttl(self):
        """Test cache returns cached result within TTL."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client, cache_ttl_seconds=30)

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Mock the describe_image to return a response
        mock_client.describe_image.return_value = "yes, certain"

        # First call - should query model
        result1 = verifier.verify_human_presence(frame)
        assert result1 is not None
        assert mock_client.describe_image.call_count == 1

        # Second call immediately - should use cache
        result2 = verifier.verify_human_presence(frame)
        assert result2 is not None
        assert mock_client.describe_image.call_count == 1  # No additional call

        # Results should be identical
        assert result1.human_detected == result2.human_detected
        assert result1.timestamp == result2.timestamp

    def test_cache_miss_after_ttl(self):
        """Test cache expires after TTL."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client, cache_ttl_seconds=0.1)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "yes, certain"

        # First call
        result1 = verifier.verify_human_presence(frame)
        assert result1 is not None
        assert mock_client.describe_image.call_count == 1

        # Wait for cache to expire
        time.sleep(0.15)

        # Second call - should query model again
        result2 = verifier.verify_human_presence(frame)
        assert result2 is not None
        assert mock_client.describe_image.call_count == 2  # Additional call

    def test_clear_cache(self):
        """Test cache clearing."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "yes, certain"

        # Populate cache
        verifier.verify_human_presence(frame)
        assert len(verifier._cache) == 1

        # Clear cache
        verifier.clear_cache()
        assert len(verifier._cache) == 0

    def test_cache_cleanup_removes_stale_entries(self):
        """Test that cleanup removes stale cache entries."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client, cache_ttl_seconds=0.1)

        # Add entry to cache
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "yes, certain"
        verifier.verify_human_presence(frame)

        # Wait for entry to become stale
        time.sleep(0.15)

        # Trigger cleanup with new verification
        verifier._cleanup_cache(time.time())

        # Cache should be cleaned
        assert len(verifier._cache) == 0

    def test_get_cache_stats_empty(self):
        """Test cache statistics when cache is empty."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        stats = verifier.get_cache_stats()

        assert stats["size"] == 0
        assert stats["oldest_age"] == 0
        assert stats["newest_age"] == 0

    def test_get_cache_stats_with_entries(self):
        """Test cache statistics with cached entries."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "yes, certain"

        # Add entry
        verifier.verify_human_presence(frame)

        stats = verifier.get_cache_stats()

        assert stats["size"] == 1
        assert stats["oldest_age"] >= 0
        assert stats["newest_age"] >= 0


class TestVisionPresenceVerifierResponseParsing:
    """Test suite for parsing vision model responses."""

    def test_parse_yes_certain(self):
        """Test parsing 'yes, certain' response."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        human_detected, confidence = verifier._parse_response("yes, certain")

        assert human_detected is True
        assert confidence == "certain"

    def test_parse_no_likely(self):
        """Test parsing 'no, likely' response."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        human_detected, confidence = verifier._parse_response("no, likely")

        assert human_detected is False
        assert confidence == "likely"

    def test_parse_yes_uncertain(self):
        """Test parsing 'yes, uncertain' response."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        human_detected, confidence = verifier._parse_response("yes, uncertain")

        assert human_detected is True
        assert confidence == "uncertain"

    def test_parse_capitalized_response(self):
        """Test parsing with capitalized response."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        human_detected, confidence = verifier._parse_response("Yes, CERTAIN")

        assert human_detected is True
        assert confidence == "certain"

    def test_parse_ambiguous_response_defaults_false(self):
        """Test that ambiguous responses default to False."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        human_detected, confidence = verifier._parse_response("maybe, possibly")

        assert human_detected is False
        assert confidence == "unknown"

    def test_parse_response_with_only_yes(self):
        """Test parsing response containing only 'yes'."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        human_detected, confidence = verifier._parse_response("yes")

        assert human_detected is True

    def test_parse_response_with_only_no(self):
        """Test parsing response containing only 'no'."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        human_detected, confidence = verifier._parse_response("no")

        assert human_detected is False


class TestVisionPresenceVerifierVerification:
    """Test suite for vision-based verification."""

    def test_successful_verification_human_present(self):
        """Test successful verification when human is present."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "yes, certain"

        result = verifier.verify_human_presence(frame)

        assert result is not None
        assert result.human_detected is True
        assert result.confidence == "certain"
        assert result.raw_response == "yes, certain"
        assert mock_client.describe_image.called

    def test_successful_verification_no_human(self):
        """Test successful verification when no human present."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "no, likely"

        result = verifier.verify_human_presence(frame)

        assert result is not None
        assert result.human_detected is False
        assert result.confidence == "likely"
        assert result.raw_response == "no, likely"

    def test_verification_with_custom_prompt(self):
        """Test verification with custom prompt."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        custom_prompt = "Is there a human in this image?"
        mock_client.describe_image.return_value = "yes, certain"

        result = verifier.verify_human_presence(frame, prompt=custom_prompt)

        assert result is not None
        # Verify custom prompt was used
        call_args = mock_client.describe_image.call_args
        assert call_args[0][1] == custom_prompt

    def test_verification_handles_ollama_error(self):
        """Test verification handles OllamaError gracefully."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.side_effect = OllamaError("Connection failed")

        result = verifier.verify_human_presence(frame)

        assert result is None  # Should return None on error

    def test_verification_handles_generic_exception(self):
        """Test verification handles generic exceptions gracefully."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.side_effect = Exception("Unexpected error")

        result = verifier.verify_human_presence(frame)

        assert result is None  # Should return None on error

    @patch('cv2.imencode')
    def test_verification_handles_frame_encoding_error(self, mock_imencode):
        """Test verification handles frame encoding errors."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_imencode.side_effect = Exception("Encoding failed")

        result = verifier.verify_human_presence(frame)

        assert result is None  # Should return None on encoding error


class TestVisionPresenceVerifierIntegration:
    """Integration tests for VisionPresenceVerifier."""

    def test_multiple_verifications_track_timestamps(self):
        """Test that multiple verifications have different timestamps."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client, cache_ttl_seconds=0)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "yes, certain"

        result1 = verifier.verify_human_presence(frame)
        time.sleep(0.01)
        result2 = verifier.verify_human_presence(frame)

        assert result1.timestamp < result2.timestamp

    def test_different_frames_produce_different_results(self):
        """Test that different frames can produce different results."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame1 = np.zeros((480, 640, 3), dtype=np.uint8)
        frame2 = np.ones((480, 640, 3), dtype=np.uint8)

        # Return different responses for different frames
        mock_client.describe_image.side_effect = ["yes, certain", "no, likely"]

        result1 = verifier.verify_human_presence(frame1)
        result2 = verifier.verify_human_presence(frame2)

        assert result1.human_detected is True
        assert result2.human_detected is False

    def test_verification_result_includes_timestamp(self):
        """Test that verification results include accurate timestamps."""
        mock_client = Mock(spec=OllamaClient)
        verifier = VisionPresenceVerifier(mock_client)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_client.describe_image.return_value = "yes, certain"

        start_time = time.time()
        result = verifier.verify_human_presence(frame)
        end_time = time.time()

        assert result.timestamp >= start_time
        assert result.timestamp <= end_time
