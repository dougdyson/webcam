"""
Neural network-based human presence verification using MobileNet-SSD.

Drop-in replacement for VisionPresenceVerifier (Ollama-based) that runs
a pre-trained MobileNet-SSD object detection model via cv2.dnn for fast,
local person detection with zero extra dependencies.

Key advantages over Ollama verifier:
- <15ms inference vs ~200ms+ with Ollama
- No external service dependency (no Ollama server required)
- Same interface: verify_human_presence(), clear_cache(), get_cache_stats()
"""
import logging
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import cv2
import numpy as np

from src.ollama.vision_verifier import VisionVerificationResult

logger = logging.getLogger(__name__)

# COCO class ID for "person"
COCO_PERSON_CLASS_ID = 15


@dataclass
class NeuralPresenceVerifierConfig:
    """Configuration for MobileNet-SSD based presence verification."""
    prototxt_path: str = "models/MobileNetSSD_deploy.prototxt"
    caffemodel_path: str = "models/MobileNetSSD_deploy.caffemodel"
    confidence_threshold: float = 0.5
    input_size: Tuple[int, int] = (300, 300)
    cache_ttl_seconds: int = 30


class NeuralPresenceVerifier:
    """
    Human presence verification using MobileNet-SSD via OpenCV DNN.

    Provides the same interface as VisionPresenceVerifier so it can be
    used as a drop-in replacement in VisionVerificationGate.
    """

    def __init__(self, config: Optional[NeuralPresenceVerifierConfig] = None):
        self.config = config or NeuralPresenceVerifierConfig()
        self._net = None
        self._initialized = False
        self._cache: Dict[str, tuple[VisionVerificationResult, float]] = {}

    def initialize(self) -> None:
        """
        Load MobileNet-SSD model files.

        Raises:
            FileNotFoundError: If prototxt or caffemodel files are missing.
        """
        prototxt = Path(self.config.prototxt_path)
        caffemodel = Path(self.config.caffemodel_path)

        if not prototxt.exists():
            raise FileNotFoundError(
                f"Prototxt not found: {prototxt}. "
                f"Run: python scripts/download_model.py"
            )
        if not caffemodel.exists():
            raise FileNotFoundError(
                f"Caffemodel not found: {caffemodel}. "
                f"Run: python scripts/download_model.py"
            )

        self._net = cv2.dnn.readNetFromCaffe(str(prototxt), str(caffemodel))
        self._initialized = True
        logger.info("NeuralPresenceVerifier initialized (MobileNet-SSD)")

    def cleanup(self) -> None:
        """Release model resources."""
        self._net = None
        self._initialized = False
        self._cache.clear()
        logger.info("NeuralPresenceVerifier cleaned up")

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._net is not None

    # ------------------------------------------------------------------
    # Public interface (matches VisionPresenceVerifier)
    # ------------------------------------------------------------------

    def verify_human_presence(
        self, frame: np.ndarray, prompt: Optional[str] = None
    ) -> Optional[VisionVerificationResult]:
        """
        Detect whether a person is present in *frame*.

        Args:
            frame: BGR image as numpy array.
            prompt: Ignored (kept for interface compatibility).

        Returns:
            VisionVerificationResult or None on error / not initialized.
        """
        if not self.is_initialized:
            logger.warning("NeuralPresenceVerifier not initialized")
            return None

        # --- cache lookup ---
        try:
            frame_hash = self._compute_frame_hash(frame)
        except Exception as e:
            logger.error(f"Failed to compute frame hash: {e}")
            return None

        now = time.time()
        if frame_hash in self._cache:
            cached_result, cached_time = self._cache[frame_hash]
            if now - cached_time < self.config.cache_ttl_seconds:
                logger.debug("Using cached neural verification result")
                return cached_result
            else:
                del self._cache[frame_hash]

        # --- inference ---
        try:
            person_detected, confidence = self._detect_person(frame)
        except Exception as e:
            logger.error(f"Neural inference failed: {e}")
            return None

        confidence_label = self._confidence_to_label(confidence)
        raw = (
            f"person detected (conf={confidence:.2f})"
            if person_detected
            else f"no person (max_conf={confidence:.2f})"
        )

        result = VisionVerificationResult(
            human_detected=person_detected,
            confidence=confidence_label,
            raw_response=raw,
            timestamp=now,
        )

        self._cache[frame_hash] = (result, now)
        self._cleanup_cache(now)

        logger.debug(f"Neural verification: {result}")
        return result

    def clear_cache(self) -> None:
        """Clear all cached verification results."""
        self._cache.clear()
        logger.debug("Cleared neural verification cache")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics for monitoring."""
        if not self._cache:
            return {"size": 0, "oldest_age": 0, "newest_age": 0}

        now = time.time()
        ages = [now - ts for _, ts in self._cache.values()]
        return {
            "size": len(self._cache),
            "oldest_age": max(ages),
            "newest_age": min(ages),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_person(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Run MobileNet-SSD and check for person detections.

        Returns:
            (person_found, best_confidence) where best_confidence is the
            highest confidence among person-class detections (0.0 if none).
        """
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=0.007843,
            size=self.config.input_size,
            mean=(127.5, 127.5, 127.5),
            swapRB=False,
            crop=False,
        )
        self._net.setInput(blob)
        detections = self._net.forward()

        best_conf = 0.0
        # detections shape: (1, 1, N, 7)
        for i in range(detections.shape[2]):
            class_id = int(detections[0, 0, i, 1])
            conf = float(detections[0, 0, i, 2])
            if class_id == COCO_PERSON_CLASS_ID and conf > best_conf:
                best_conf = conf

        person_found = best_conf >= self.config.confidence_threshold
        return person_found, best_conf

    @staticmethod
    def _confidence_to_label(confidence: float) -> str:
        """Map numeric confidence to a string label."""
        if confidence >= 0.8:
            return "certain"
        elif confidence >= 0.5:
            return "likely"
        return "uncertain"

    def _compute_frame_hash(self, frame: np.ndarray) -> str:
        _, buffer = cv2.imencode(".jpg", frame)
        return hashlib.md5(buffer.tobytes()).hexdigest()

    def _cleanup_cache(self, current_time: float, max_cache_size: int = 10) -> None:
        stale = [
            k for k, (_, ts) in self._cache.items()
            if current_time - ts >= self.config.cache_ttl_seconds
        ]
        for k in stale:
            del self._cache[k]

        if len(self._cache) > max_cache_size:
            sorted_entries = sorted(
                self._cache.items(), key=lambda item: item[1][1]
            )
            self._cache = dict(sorted_entries[-max_cache_size:])
