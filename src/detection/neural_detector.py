"""
Neural network-based human presence detector using YOLOv8.

Primary presence detector that implements the standard HumanDetector interface.
Runs YOLOv8 nano model via ultralytics for fast, reliable person detection
at all ranges including close-up webcam views.

Key characteristics:
- Reliable at close range, partial body, varied angles
- No caching — every frame gets a fresh detection
- Returns DetectionResult with bounding_box, no pose landmarks
- Configurable via DetectorConfig.min_detection_confidence
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from .base import HumanDetector, DetectorConfig, DetectorError
from .result import DetectionResult

logger = logging.getLogger(__name__)

# COCO class ID for "person" in YOLOv8
COCO_PERSON_CLASS_ID = 0

# Default model path
DEFAULT_MODEL_PATH = "models/yolov8n.pt"


class NeuralDetector(HumanDetector):
    """
    Human presence detector using YOLOv8 via ultralytics.

    Implements the standard HumanDetector interface so it can serve as the
    primary detector in the detection pipeline.  Per-frame detection with
    no result caching — every call to detect() runs inference.
    """

    def __init__(
        self,
        config: Optional[DetectorConfig] = None,
        model_path: str = DEFAULT_MODEL_PATH,
        # Legacy kwargs accepted but ignored (MobileNet-SSD compat)
        prototxt_path: str = "",
        caffemodel_path: str = "",
        input_size: tuple = (640, 640),
    ):
        super().__init__(config)
        self._model_path = model_path
        self._input_size = input_size
        self._model = None
        self._initialized = False

    # ------------------------------------------------------------------
    # HumanDetector interface
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Load YOLOv8 model.

        Raises:
            DetectorError: If model file is missing or loading fails.
        """
        model_file = Path(self._model_path)

        if not model_file.exists():
            raise DetectorError(
                f"YOLOv8 model not found: {model_file}. "
                f"Download with: pip install ultralytics && yolo export"
            )

        try:
            from ultralytics import YOLO
            self._model = YOLO(str(model_file))
        except ImportError:
            raise DetectorError(
                "ultralytics package not installed. Run: pip install ultralytics"
            )
        except Exception as e:
            raise DetectorError("Failed to load YOLOv8 model", original_error=e)

        self._initialized = True
        logger.info("NeuralDetector initialized (YOLOv8 nano primary detector)")

    def cleanup(self) -> None:
        """Release model resources."""
        self._model = None
        self._initialized = False
        logger.info("NeuralDetector cleaned up")

    @property
    def is_initialized(self) -> bool:
        return self._initialized and self._model is not None

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """Run YOLOv8 inference on *frame* and return a DetectionResult.

        Args:
            frame: BGR image as numpy array.

        Returns:
            DetectionResult with human_present, confidence, and bounding_box.
            ``_original_pose_landmarks`` is always None (YOLO has no landmarks).

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
        # No pose landmarks from YOLO — gesture code uses getattr fallback
        result._original_pose_landmarks = None
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_person(self, frame: np.ndarray):
        """Run YOLOv8 and return (person_found, best_confidence, bbox|None)."""
        h, w = frame.shape[:2]

        results = self._model(
            frame,
            verbose=False,
            conf=0.25,  # Low threshold — let our gate handle filtering
            classes=[COCO_PERSON_CLASS_ID],
        )

        best_conf = 0.0
        best_bbox = None

        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                conf = float(box.conf)
                if conf > best_conf:
                    best_conf = conf
                    # Extract bounding box (xyxy format → x,y,w,h)
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1 = max(0, int(x1))
                    y1 = max(0, int(y1))
                    x2 = min(w, int(x2))
                    y2 = min(h, int(y2))
                    best_bbox = (x1, y1, max(0, x2 - x1), max(0, y2 - y1))

        threshold = self.config.min_detection_confidence
        person_found = best_conf >= threshold

        if not person_found:
            return False, 0.0, None

        return True, best_conf, best_bbox
