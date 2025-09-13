"""
Presence gating pipeline with hysteresis and cooldown.

Combines fast pHash and edge-SSIM checks against a ReferenceManager to gate
MediaPipe detections in visually busy scenes. Implements enter/exit hysteresis
and cooldown to stabilize presence state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from src.detection.result import DetectionResult
from .reference_manager import ReferenceManager
from .image_similarity import edge_ssim


@dataclass
class PresenceGateConfig:
    gating_enabled: bool = True
    phash_threshold_same: int = 10
    ssim_threshold_same: float = 0.90
    enter_k: int = 3
    exit_l: int = 5
    cooldown_ms: int = 1000
    capture_stable_seconds: float = 5.0
    max_refs: int = 3


@dataclass
class GatedResult:
    human_present: bool
    confidence: float
    reason: Optional[str] = None


class PresenceGate:
    def __init__(self, ref_manager: ReferenceManager, config: Optional[PresenceGateConfig] = None):
        self.config = config or PresenceGateConfig()
        self.refs = ref_manager
        self.current_state = False
        self._pos_streak = 0
        self._neg_streak = 0
        self._last_flip_ts: Optional[float] = None
        self._last_neg_start: Optional[float] = None
        self._captured_in_period: bool = False

    def _within_cooldown(self, ts: Optional[float]) -> bool:
        if ts is None or self._last_flip_ts is None:
            return False
        return (ts - self._last_flip_ts) * 1000.0 < self.config.cooldown_ms

    def _gate_decision(self, frame: np.ndarray, detected_present: bool) -> bool:
        # If no references, accept detector decision
        if not self.config.gating_enabled or self.refs.size() == 0:
            return detected_present

        # Only gate positives; we allow negatives through (and may capture refs elsewhere)
        if not detected_present:
            return False

        # Compare against best reference
        best_ref, ph_dist = self.refs.get_best_reference(frame)
        if best_ref is None or ph_dist is None:
            return True  # no references yet

        # pHash fast gate
        if ph_dist < self.config.phash_threshold_same:
            return False  # looks like reference (no change)

        # SSIM edge check when pHash suggests change
        # Resize handled inside edge_ssim via reference size in manager; we can just pass arrays
        ssim = edge_ssim(frame, best_ref)
        if ssim >= self.config.ssim_threshold_same:
            return False  # edges are similar to reference

        return True  # looks different enough from reference

    def process(self, frame: np.ndarray, detection_result: DetectionResult, timestamp_s: Optional[float] = None) -> GatedResult:
        detected_present = bool(detection_result.human_present)

        # Track negative streak start for optional reference capture (phase 2)
        if not detected_present:
            if self._last_neg_start is None:
                self._last_neg_start = timestamp_s
                self._captured_in_period = False
            else:
                # Consider auto-capture of reference after stable no-human period
                if (
                    self.config.gating_enabled
                    and not self._captured_in_period
                    and timestamp_s is not None
                    and self._last_neg_start is not None
                    and (timestamp_s - self._last_neg_start) >= self.config.capture_stable_seconds
                    and self.refs.size() < self.config.max_refs
                ):
                    try:
                        self.refs.add_reference(frame)
                        self._captured_in_period = True
                    except Exception:
                        pass
        else:
            self._last_neg_start = None
            self._captured_in_period = False

        candidate_present = self._gate_decision(frame, detected_present)

        # Update hysteresis counters
        if candidate_present:
            self._pos_streak += 1
            self._neg_streak = 0
        else:
            self._neg_streak += 1
            self._pos_streak = 0

        # Evaluate state transitions with cooldown
        flipped = False
        if candidate_present and not self.current_state:
            if self._pos_streak >= self.config.enter_k and not self._within_cooldown(timestamp_s):
                self.current_state = True
                self._pos_streak = 0
                self._neg_streak = 0
                self._last_flip_ts = timestamp_s
                flipped = True
        elif not candidate_present and self.current_state:
            if self._neg_streak >= self.config.exit_l and not self._within_cooldown(timestamp_s):
                self.current_state = False
                self._pos_streak = 0
                self._neg_streak = 0
                self._last_flip_ts = timestamp_s
                flipped = True

        reason = None
        if flipped:
            reason = "flip_enter" if self.current_state else "flip_exit"

        return GatedResult(human_present=self.current_state, confidence=detection_result.confidence, reason=reason)
