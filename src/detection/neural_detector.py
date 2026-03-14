"""
Neural network-based human presence detector using MobileNet-SSD.

Primary presence detector that implements the standard HumanDetector interface.
Runs MobileNet-SSD object detection via cv2.dnn for fast, local person detection
with no external dependencies.

Key characteristics:
- ~5-15ms per-frame inference (purpose-built object detection)
- No caching — every frame gets a fresh detection
- Returns DetectionResult with bounding_box, no pose landmarks
- Configurable via DetectorConfig.min_detection_confidence
"""
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .base import HumanDetector, DetectorConfig, DetectorError
from .result import DetectionResult

logger = logging.getLogger(__name__)

# COCO class ID for "person"
COCO_PERSON_CLASS_ID = 15

# Default model paths
DEFAULT_PROTOTXT = "models/MobileNetSSD_deploy.prototxt"
DEFAULT_CAFFEMODEL = "models/MobileNetSSD_deploy.caffemodel"


class NeuralDetector(HumanDetector):
    """
    Human presence detector using MobileNet-SSD via OpenCV DNN.

    Implements the standard HumanDetector interface so it can serve as the
    primary detector in the detection pipeline.  Per-frame detection with
    no result caching — every call to detect() runs inference.
    """

    def __init__(
        self,
        config: Optional[DetectorConfig] = None,
        prototxt_path: str = DEFAULT_PROTOTXT,
        caffemodel_path: str = DEFAULT_CAFFEMODEL,
        input_size: tuple = (300, 300),
    ):
        super().__init__(config)
        self._prototxt_path = prototxt_path
        self._caffemodel_path = caffemodel_path
        self._input_size = input_size
        self._net = None
        self._initialized = False

    # ------------------------------------------------------------------
    # HumanDetector interface
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load MobileNet-SSD model files.

        Raises:
            DetectorError: If model files are missing or loading fails.
        """
        prototxt = Path(self._prototxt_path)
        caffemodel = Path(self._caffemodel_path)

        if not prototxt.exists():
            raise DetectorError(
                f"Prototxt not found: {prototxt}. "
                f"Run: python scripts/download_model.py"
            )
        if not caffemodel.exists():
            raise DetectorError(
                f"Caffemodel not found: {caffemodel}. "
                f"Run: python scripts/download_model.py"
            )

        try:
            self._net = cv2.dnn.readNetFromCaffe(str(prototxt), str(caffemodel))
        except Exception as e:
            raise DetectorError("Failed to load MobileNet-SSD model", original_error=e)

        self._initialized = True
        logger.info("NeuralDetector initialized (MobileNet-SSD primary detector)")

    def cleanup(self) -> None:
        """Release model resources."""
        self._net = None
        self._initialized = False
        logger.info("NeuralDetector cleaned up")

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._net is not None

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Run MobileNet-SSD inference on *frame* and return a DetectionResult.

        Args:
            frame: BGR image as numpy array.

        Returns:
            DetectionResult with human_present, confidence, and bounding_box.
            ``_original_pose_landmarks`` is always None (SSD has no landmarks).

        Raises:
            DetectorError: If detector is not initialized or inference fails.
        """
        if not self.is_initialized:
            raise DetectorError("NeuralDetector not initialized — call initialize() first")

        try:
            person_found, confidence, bbox = self._detect_person(frame)
        except Exception as e:
            raise DetectorError("Neural inference failed", original_error=e)

        result = DetectionResult(
            human_present=person_found,
            confidence=confidence,
            bounding_box=bbox,
        )
        # No pose landmarks from SSD — gesture code uses getattr fallback
        result._original_pose_landmarks = None
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_person(self, frame: np.ndarray):
        """Run MobileNet-SSD and return (person_found, best_confidence, bbox|None)."""
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=0.007843,
            size=self._input_size,
            mean=(127.5, 127.5, 127.5),
            swapRB=False,
            crop=False,
        )
        self._net.setInput(blob)
        detections = self._net.forward()

        best_conf = 0.0
        best_bbox = None

        # detections shape: (1, 1, N, 7)
        for i in range(detections.shape[2]):
            class_id = int(detections[0, 0, i, 1])
            conf = float(detections[0, 0, i, 2])
            if class_id == COCO_PERSON_CLASS_ID and conf > best_conf:
                best_conf = conf
                # Extract bounding box (normalised coords → pixel coords)
                x1 = max(0, int(detections[0, 0, i, 3] * w))
                y1 = max(0, int(detections[0, 0, i, 4] * h))
                x2 = min(w, int(detections[0, 0, i, 5] * w))
                y2 = min(h, int(detections[0, 0, i, 6] * h))
                best_bbox = (x1, y1, max(0, x2 - x1), max(0, y2 - y1))

        threshold = self.config.min_detection_confidence
        person_found = best_conf >= threshold

        if not person_found:
            return False, 0.0, None

        return True, best_conf, best_bbox
