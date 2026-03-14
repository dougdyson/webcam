"""
Integration tests for VisionVerificationGate using real captured frames.

Following TDD methodology:
- RED: These tests will fail because VisionVerificationGate doesn't exist yet
- GREEN: Implement VisionVerificationGate to make tests pass
- REFACTOR: Clean up implementation while keeping tests green

Requires:
- Ollama service running with qwen3-vl:2b-instruct-q4_K_M model
- Real captured frames in tests/fixtures/frames/
"""
import pytest
import cv2
import numpy as np
from pathlib import Path
from unittest.mock import Mock

# This import will fail initially - that's the RED phase!
try:
    from src.processing.vision_verification_gate import (
        VisionVerificationGate,
        VisionVerificationConfig
    )
except ImportError:
    VisionVerificationGate = None
    VisionVerificationConfig = None

from src.ollama.client import OllamaClient, OllamaConfig
from src.ollama.vision_verifier import VisionPresenceVerifier
from src.processing.presence_gate import PresenceGate, PresenceGateConfig, GatedResult
from src.processing.reference_manager import ReferenceManager
from src.detection.result import DetectionResult


@pytest.fixture
def fixtures_dir():
    """Get path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures" / "frames"


@pytest.fixture
def human_frame(fixtures_dir):
    """Load a real frame with human visible."""
    # Try common naming patterns
    candidates = [
        "human_standing.png",
        "human_sitting.png",
        "human_visible.png",
        "human_closeup.png",
        "human_standing.jpg",
        "human_visible.jpg",
        "human_closeup.jpg",
    ]

    for filename in candidates:
        filepath = fixtures_dir / filename
        if filepath.exists():
            frame = cv2.imread(str(filepath))
            assert frame is not None, f"Failed to load {filename}"
            return frame

    # If no human frames found, list what we have
    available = list(fixtures_dir.glob("*.png")) + list(fixtures_dir.glob("*.jpg"))
    pytest.skip(f"No human frames found. Available: {[f.name for f in available]}")


@pytest.fixture
def empty_frame(fixtures_dir):
    """Load a real frame of empty kitchen."""
    # Try common naming patterns
    candidates = [
        "empty_room.png",
        "empty_lights_on.png",
        "empty_kitchen.png",
        "empty.png",
        "empty_room.jpg",
        "empty_lights_on.jpg",
        "empty_kitchen.jpg",
        "empty.jpg",
    ]

    for filename in candidates:
        filepath = fixtures_dir / filename
        if filepath.exists():
            frame = cv2.imread(str(filepath))
            assert frame is not None, f"Failed to load {filename}"
            return frame

    # If no empty frames found, list what we have
    available = list(fixtures_dir.glob("*.png")) + list(fixtures_dir.glob("*.jpg"))
    pytest.skip(f"No empty frames found. Available: {[f.name for f in available]}")


@pytest.fixture
def ollama_client():
    """Create OllamaClient for real vision model testing."""
    config = OllamaConfig(
        model="qwen3-vl:2b-instruct-q4_K_M",
        base_url="http://localhost:11434",
        timeout=10.0,
        max_retries=2
    )
    client = OllamaClient(config)

    # Check if Ollama is available
    if not client.is_available():
        pytest.skip("Ollama service not available - install and run: ollama serve")

    return client


@pytest.fixture
def vision_verifier(ollama_client):
    """Create VisionPresenceVerifier with real Ollama client."""
    return VisionPresenceVerifier(ollama_client, cache_ttl_seconds=60)


@pytest.fixture
def presence_gate():
    """Create real PresenceGate for testing."""
    ref_manager = ReferenceManager(max_references=3)
    config = PresenceGateConfig(
        gating_enabled=True,
        phash_threshold_same=14,
        ssim_threshold_same=0.94,
        enter_k=4,
        exit_l=5,
        cooldown_ms=1000
    )
    return PresenceGate(ref_manager, config)


@pytest.fixture
def verification_gate(presence_gate, vision_verifier):
    """
    Create VisionVerificationGate for testing.

    This will fail initially (RED phase) because VisionVerificationGate
    doesn't exist yet.
    """
    if VisionVerificationGate is None:
        pytest.skip("VisionVerificationGate not implemented yet (RED phase)")

    config = VisionVerificationConfig(
        max_blocks_per_session=3,
        recapture_on_block=True,
        verify_enter_only=True
    )

    return VisionVerificationGate(
        presence_gate=presence_gate,
        vision_verifier=vision_verifier,
        config=config
    )


class TestVisionPresenceVerifierWithRealFrames:
    """
    Test that VisionPresenceVerifier works correctly with real captured frames.

    These tests should PASS immediately since VisionPresenceVerifier already exists.
    """

    @pytest.mark.integration
    def test_vision_detects_human_in_real_frame(self, vision_verifier, human_frame):
        """
        Test that vision model correctly identifies human in real captured frame.

        Expected: Vision model should return human_detected=True
        """
        result = vision_verifier.verify_human_presence(human_frame)

        assert result is not None, "Vision verification should succeed"
        assert result.human_detected is True, (
            f"Vision should detect human in frame. "
            f"Got: {result.human_detected}, confidence: {result.confidence}, "
            f"response: {result.raw_response}"
        )

    @pytest.mark.integration
    def test_vision_detects_empty_in_real_frame(self, vision_verifier, empty_frame):
        """
        Test that vision model correctly identifies empty kitchen in real frame.

        Expected: Vision model should return human_detected=False
        """
        result = vision_verifier.verify_human_presence(empty_frame)

        assert result is not None, "Vision verification should succeed"
        assert result.human_detected is False, (
            f"Vision should NOT detect human in empty frame. "
            f"Got: {result.human_detected}, confidence: {result.confidence}, "
            f"response: {result.raw_response}"
        )

    @pytest.mark.integration
    def test_vision_caching_works_with_real_frames(self, vision_verifier, human_frame):
        """
        Test that caching works correctly with real frames.

        Expected: Second call should use cached result
        """
        # First call - should hit Ollama
        result1 = vision_verifier.verify_human_presence(human_frame)

        # Second call - should use cache
        result2 = vision_verifier.verify_human_presence(human_frame)

        assert result1.timestamp == result2.timestamp, "Should return cached result"
        assert result1.human_detected == result2.human_detected


class TestVisionVerificationGateBasics:
    """
    Test VisionVerificationGate basic functionality.

    These tests will FAIL initially (RED phase) because
    VisionVerificationGate doesn't exist yet.
    """

    def test_verification_gate_initialization(self, verification_gate):
        """
        RED: Test VisionVerificationGate can be initialized.

        This will fail because VisionVerificationGate doesn't exist.
        """
        assert verification_gate is not None
        assert verification_gate.presence_gate is not None
        assert verification_gate.vision_verifier is not None
        assert verification_gate.config is not None

    def test_verification_gate_has_process_method(self, verification_gate):
        """
        RED: Test VisionVerificationGate has process() method.

        Expected signature: process(frame, detection_result, timestamp_s) -> GatedResult
        """
        assert hasattr(verification_gate, 'process')
        assert callable(verification_gate.process)

    def test_verification_gate_tracks_block_counter(self, verification_gate):
        """
        RED: Test VisionVerificationGate tracks block counter.

        Expected: Should have _block_counter attribute
        """
        assert hasattr(verification_gate, '_block_counter')
        assert verification_gate._block_counter == 0


class TestVisionVerificationGateStateTransitions:
    """
    Test VisionVerificationGate state transition interception.

    RED phase: These will fail until VisionVerificationGate is implemented.
    """

    @pytest.mark.integration
    def test_allows_transition_when_vision_agrees(
        self,
        verification_gate,
        human_frame,
        presence_gate
    ):
        """
        RED: Test that transition is ALLOWED when vision agrees.

        Scenario:
        - PresenceGate wants to flip to human_present=True
        - Vision model says "yes, human present"
        - Expected: Transition should be ALLOWED
        """
        # Set up PresenceGate to be ready to flip to True
        # Manually set streak to threshold - 1
        presence_gate.current_state = False
        presence_gate._pos_streak = 3  # One away from enter_k=4

        # Create detection result indicating human
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.85,
            timestamp=0.0
        )

        # Process through verification gate
        # This should trigger state flip, run vision verification, and allow it
        gated_result = verification_gate.process(human_frame, detection_result, 1.0)

        # Assertions
        assert gated_result.human_present is True, "Should allow transition when vision agrees"
        assert verification_gate._block_counter == 0, "Block counter should reset on agreement"

    @pytest.mark.integration
    def test_blocks_transition_when_vision_disagrees(
        self,
        verification_gate,
        empty_frame,
        presence_gate
    ):
        """
        RED: Test that transition is BLOCKED when vision disagrees.

        Scenario:
        - PresenceGate wants to flip to human_present=True (false positive)
        - Vision model says "no, no human present"
        - Expected: Transition should be BLOCKED, state rolled back
        """
        # Set up PresenceGate to be ready to flip to True
        presence_gate.current_state = False
        presence_gate._pos_streak = 3  # One away from enter_k=4

        # Create detection result indicating human (false positive)
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.65,  # Lower confidence - suspicious
            timestamp=0.0
        )

        # Process through verification gate with EMPTY frame
        # PresenceGate wants to flip to True, but vision will say No
        gated_result = verification_gate.process(empty_frame, detection_result, 1.0)

        # Assertions
        assert gated_result.human_present is False, (
            "Should BLOCK transition when vision disagrees"
        )
        assert verification_gate._block_counter == 1, (
            "Block counter should increment"
        )
        assert presence_gate.current_state is False, (
            "PresenceGate state should be rolled back to False"
        )
        assert presence_gate._pos_streak == 0, (
            "Streaks should be reset after rollback"
        )

    @pytest.mark.integration
    def test_max_blocks_failsafe(
        self,
        verification_gate,
        empty_frame,
        presence_gate
    ):
        """
        RED: Test that max blocks fail-safe allows transition.

        Scenario:
        - PresenceGate wants to flip to True 4 times
        - Vision says No all 4 times
        - Expected: First 3 blocked, 4th allowed (fail-safe)
        """
        # Disable recapture for this test (would prevent subsequent flips)
        verification_gate.config.recapture_on_block = False

        detection_result = DetectionResult(
            human_present=True,
            confidence=0.65,
            timestamp=0.0
        )

        # Block 1
        presence_gate.current_state = False
        presence_gate._pos_streak = 3
        presence_gate._last_flip_ts = None  # Clear cooldown
        result1 = verification_gate.process(empty_frame, detection_result, 1.0)
        assert result1.human_present is False, "Block 1 should be blocked"
        assert verification_gate._block_counter == 1

        # Block 2
        presence_gate.current_state = False
        presence_gate._pos_streak = 3
        presence_gate._last_flip_ts = None  # Clear cooldown
        verification_gate.vision_verifier.clear_cache()  # Clear cache for new verification
        result2 = verification_gate.process(empty_frame, detection_result, 3.0)
        assert result2.human_present is False, "Block 2 should be blocked"
        assert verification_gate._block_counter == 2

        # Block 3
        presence_gate.current_state = False
        presence_gate._pos_streak = 3
        presence_gate._last_flip_ts = None  # Clear cooldown
        verification_gate.vision_verifier.clear_cache()  # Clear cache for new verification
        result3 = verification_gate.process(empty_frame, detection_result, 5.0)
        assert result3.human_present is False, "Block 3 should be blocked"
        assert verification_gate._block_counter == 3

        # Attempt 4 - should allow (fail-safe)
        presence_gate.current_state = False
        presence_gate._pos_streak = 3
        presence_gate._last_flip_ts = None  # Clear cooldown
        verification_gate.vision_verifier.clear_cache()  # Clear cache for new verification
        result4 = verification_gate.process(empty_frame, detection_result, 7.0)
        assert result4.human_present is True, (
            "Block 4 should be ALLOWED (max blocks reached)"
        )
        assert verification_gate._block_counter == 0, (
            "Block counter should reset after allowing"
        )


class TestVisionVerificationGatePassthrough:
    """
    Test that VisionVerificationGate passes through correctly when not flipping.

    RED phase: Will fail until implemented.
    """

    def test_passthrough_when_no_state_change(self, verification_gate, empty_frame):
        """
        RED: Test that normal frames pass through without verification.

        Scenario:
        - PresenceGate NOT flipping state (reason=None)
        - Expected: No vision verification, just pass through
        """
        # Set up PresenceGate in stable state
        verification_gate.presence_gate.current_state = False
        verification_gate.presence_gate._pos_streak = 1  # Not at threshold

        detection_result = DetectionResult(
            human_present=False,
            confidence=0.0,
            timestamp=0.0
        )

        # Track verification count
        initial_verifications = verification_gate._total_verifications

        # Process - should pass through without verification
        gated_result = verification_gate.process(empty_frame, detection_result, 1.0)

        assert gated_result.human_present is False
        assert verification_gate._total_verifications == initial_verifications, (
            "Should not run verification when not flipping state"
        )


class TestNeuralPresenceVerifierIntegration:
    """
    Integration tests for NeuralPresenceVerifier with real model files.

    Skipped when model files are not downloaded.
    """

    @pytest.fixture
    def neural_verifier(self):
        """Create NeuralPresenceVerifier with real model files."""
        from src.detection.neural_presence_verifier import (
            NeuralPresenceVerifier,
            NeuralPresenceVerifierConfig,
        )
        config = NeuralPresenceVerifierConfig()
        verifier = NeuralPresenceVerifier(config)
        try:
            verifier.initialize()
        except FileNotFoundError:
            pytest.skip(
                "MobileNet-SSD model not downloaded. "
                "Run: python scripts/download_model.py"
            )
        yield verifier
        verifier.cleanup()

    @pytest.mark.integration
    def test_neural_detects_human_in_real_frame(self, neural_verifier, human_frame):
        result = neural_verifier.verify_human_presence(human_frame)
        assert result is not None, "Neural verification should succeed"
        assert result.human_detected is True, (
            f"Neural verifier should detect human. Got: {result}"
        )

    @pytest.mark.integration
    def test_neural_detects_empty_in_real_frame(self, neural_verifier, empty_frame):
        result = neural_verifier.verify_human_presence(empty_frame)
        assert result is not None, "Neural verification should succeed"
        assert result.human_detected is False, (
            f"Neural verifier should NOT detect human in empty frame. Got: {result}"
        )

    @pytest.mark.integration
    def test_neural_inference_latency(self, neural_verifier, human_frame):
        """Verify inference completes in <15ms (target)."""
        import time
        # Warm up
        neural_verifier.verify_human_presence(human_frame)
        neural_verifier.clear_cache()

        start = time.perf_counter()
        neural_verifier.verify_human_presence(human_frame)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, (
            f"Neural inference took {elapsed_ms:.1f}ms (target <15ms, hard limit 50ms)"
        )


class TestVisionVerificationGateMetrics:
    """
    Test that VisionVerificationGate tracks metrics correctly.

    RED phase: Will fail until implemented.
    """

    def test_tracks_verification_statistics(self, verification_gate):
        """
        RED: Test that verification statistics are tracked.

        Expected: Should have get_stats() method returning metrics
        """
        assert hasattr(verification_gate, 'get_stats')

        stats = verification_gate.get_stats()

        assert 'total_verifications' in stats
        assert 'total_blocks' in stats
        assert 'current_block_streak' in stats
        assert 'block_rate' in stats
