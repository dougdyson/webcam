"""
Vision-based verification gate for state transitions.

Wraps PresenceGate to add vision model verification before allowing
state transitions to human_present=True, preventing false positives.

Architecture:
- Intercepts state transitions from PresenceGate
- Runs vision verification when state about to flip to PRESENT
- Blocks transition if vision disagrees
- Implements fail-safe: allows after max consecutive blocks
- Rolls back PresenceGate state when blocking
"""
import logging
import time
from dataclasses import dataclass
from typing import Optional
import numpy as np

from src.detection.result import DetectionResult
from src.processing.presence_gate import PresenceGate, GatedResult
from src.ollama.vision_verifier import VisionPresenceVerifier, VisionVerificationResult

logger = logging.getLogger(__name__)


@dataclass
class VisionVerificationConfig:
    """Configuration for vision verification gate."""
    max_blocks_per_session: int = 3  # Max consecutive blocks before allowing
    recapture_on_block: bool = True  # Recapture reference when blocking
    verify_enter_only: bool = True   # Only verify enter transitions (not exit)
    verification_timeout_ms: int = 5000  # Timeout for vision verification


class VisionVerificationGate:
    """
    Wrapper around PresenceGate that adds vision-based verification.

    Intercepts state transitions (False→True) and validates with vision model
    before allowing the transition. Blocks false positives by rolling back
    state when vision disagrees.

    Example:
        >>> gate = VisionVerificationGate(presence_gate, vision_verifier)
        >>> result = gate.process(frame, detection_result, timestamp)
        >>> # If MediaPipe says "human" but vision says "no" → blocked!
    """

    def __init__(
        self,
        presence_gate: PresenceGate,
        vision_verifier: VisionPresenceVerifier,
        config: Optional[VisionVerificationConfig] = None
    ):
        """
        Initialize vision verification gate.

        Args:
            presence_gate: PresenceGate instance to wrap
            vision_verifier: VisionPresenceVerifier for validation
            config: Configuration (uses defaults if None)
        """
        self.presence_gate = presence_gate
        self.vision_verifier = vision_verifier
        self.config = config or VisionVerificationConfig()

        # State tracking
        self._block_counter = 0
        self._total_verifications = 0
        self._total_blocks = 0
        self._verification_history = []

        logger.info(
            f"Initialized VisionVerificationGate "
            f"(max_blocks={self.config.max_blocks_per_session})"
        )

    def process(
        self,
        frame: np.ndarray,
        detection_result: DetectionResult,
        timestamp_s: Optional[float] = None
    ) -> GatedResult:
        """
        Process frame with vision verification on state transitions.

        Flow:
        1. Run normal PresenceGate.process()
        2. If state flipped to PRESENT (flip_enter):
           - Run vision verification
           - If vision disagrees → rollback state, block transition
           - If vision agrees → allow transition, reset block counter
        3. Return GatedResult (potentially modified)

        Args:
            frame: Current frame from camera
            detection_result: Detection result from detector
            timestamp_s: Current timestamp in seconds

        Returns:
            GatedResult with potentially blocked transition
        """
        # Step 1: Normal PresenceGate processing
        gated_result = self.presence_gate.process(frame, detection_result, timestamp_s)

        # Step 2: Detect state transitions
        if gated_result.reason == "flip_enter":
            # State just flipped to PRESENT - verify with vision
            self._handle_enter_transition(frame, gated_result, timestamp_s)

        elif gated_result.reason == "flip_exit" and not self.config.verify_enter_only:
            # Optional: verify exit transitions too
            self._handle_exit_transition(frame, gated_result, timestamp_s)

        return gated_result

    def _handle_enter_transition(
        self,
        frame: np.ndarray,
        gated_result: GatedResult,
        timestamp_s: Optional[float]
    ):
        """
        Handle state flip from False → True with vision verification.

        Args:
            frame: Current frame
            gated_result: GatedResult from PresenceGate (will be modified if blocked)
            timestamp_s: Current timestamp
        """
        # Run vision verification
        vision_result = self._verify_with_vision(frame, timestamp_s)

        if vision_result is None:
            # Vision verification failed (timeout/error) - allow transition
            logger.warning("[VisionGate] Vision verification failed, allowing transition")
            self._block_counter = 0  # Reset on error
            return

        # Check agreement
        if vision_result.human_detected:
            # Vision AGREES - allow transition, reset block counter
            self._block_counter = 0
            logger.info(
                f"[VisionGate] ✓ Vision confirms enter transition "
                f"(confidence: {vision_result.confidence})"
            )

        else:
            # Vision DISAGREES - potential false positive
            if self._block_counter < self.config.max_blocks_per_session:
                # BLOCK the transition
                self._rollback_state_transition(frame, gated_result, vision_result)
                self._block_counter += 1
                self._total_blocks += 1

                logger.warning(
                    f"[VisionGate] ✗ BLOCKED enter transition "
                    f"(vision: {vision_result.confidence}, "
                    f"block {self._block_counter}/{self.config.max_blocks_per_session})"
                )

            else:
                # Max blocks reached - allow transition, reset counter
                self._block_counter = 0
                logger.warning(
                    f"[VisionGate] ⚠ Max blocks reached ({self.config.max_blocks_per_session}), "
                    f"allowing transition despite vision disagreement"
                )

    def _verify_with_vision(
        self,
        frame: np.ndarray,
        timestamp_s: Optional[float]
    ) -> Optional[VisionVerificationResult]:
        """
        Run synchronous vision verification with timeout.

        Args:
            frame: Frame to verify
            timestamp_s: Current timestamp

        Returns:
            VisionVerificationResult if successful, None on error
        """
        try:
            self._total_verifications += 1
            result = self.vision_verifier.verify_human_presence(frame)

            if result:
                # Track in history for analysis
                self._verification_history.append({
                    "timestamp": timestamp_s,
                    "detected": result.human_detected,
                    "confidence": result.confidence,
                    "raw_response": result.raw_response
                })

            return result

        except Exception as e:
            logger.error(f"[VisionGate] Verification error: {e}")
            return None

    def _rollback_state_transition(
        self,
        frame: np.ndarray,
        gated_result: GatedResult,
        vision_result: VisionVerificationResult
    ):
        """
        Rollback state transition by manipulating PresenceGate internal state.

        CRITICAL: This directly modifies PresenceGate internals to prevent
        the state change from persisting.

        Args:
            frame: Current frame (for optional recapture)
            gated_result: GatedResult to modify
            vision_result: Vision verification result (for logging)
        """
        # Flip state back to False
        self.presence_gate.current_state = False

        # Reset hysteresis counters to prevent immediate re-flip
        self.presence_gate._pos_streak = 0
        self.presence_gate._neg_streak = 0

        # Modify GatedResult to reflect blocked state
        gated_result.human_present = False
        gated_result.reason = "vision_blocked"

        # Optional: Recapture reference image
        if self.config.recapture_on_block:
            try:
                # Add current frame as reference (it's "empty" according to vision)
                self.presence_gate.refs.add_reference(frame)
                logger.debug("[VisionGate] Recaptured reference after block")
            except Exception as e:
                logger.debug(f"[VisionGate] Reference recapture failed: {e}")

    def _handle_exit_transition(
        self,
        frame: np.ndarray,
        gated_result: GatedResult,
        timestamp_s: Optional[float]
    ):
        """
        Handle state flip from True → False (optional verification).

        Args:
            frame: Current frame
            gated_result: GatedResult from PresenceGate
            timestamp_s: Current timestamp
        """
        # Could verify that human really left
        # For now, just log
        logger.debug("[VisionGate] Exit transition (not verified)")

    def get_stats(self):
        """
        Get verification statistics.

        Returns:
            Dictionary with verification metrics
        """
        return {
            "total_verifications": self._total_verifications,
            "total_blocks": self._total_blocks,
            "current_block_streak": self._block_counter,
            "block_rate": (
                self._total_blocks / self._total_verifications
                if self._total_verifications > 0
                else 0.0
            )
        }

    def get_verification_history(self):
        """
        Get history of all verification checks.

        Returns:
            List of verification result dictionaries
        """
        return self._verification_history.copy()

    def reset_block_counter(self):
        """Reset block counter (useful for testing or manual reset)."""
        self._block_counter = 0
        logger.debug("[VisionGate] Block counter reset")

    def __repr__(self):
        """String representation for debugging."""
        stats = self.get_stats()
        return (
            f"VisionVerificationGate("
            f"verifications={stats['total_verifications']}, "
            f"blocks={stats['total_blocks']}, "
            f"block_rate={stats['block_rate']:.2%})"
        )
