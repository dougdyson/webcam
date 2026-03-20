"""
Unit tests for NeuralDetector (YOLOv8 primary presence detector).

All tests use mocks for ultralytics YOLO so no model files are needed.
"""
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from src.detection.base import HumanDetector, DetectorConfig, DetectorError, DetectorFactory
from src.detection.result import DetectionResult
from src.detection.neural_detector import NeuralDetector, COCO_PERSON_CLASS_ID


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_frame():
    """A small BGR frame for testing."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


def _make_yolo_box(conf, x1, y1, x2, y2):
    """Create a mock YOLO box object."""
    box = MagicMock()
    box.conf = float(conf)
    xyxy_tensor = MagicMock()
    xyxy_tensor.tolist.return_value = [x1, y1, x2, y2]
    box.xyxy = [xyxy_tensor]
    return box


def _make_yolo_results(boxes):
    """Build mock YOLO results list from a list of mock box objects."""
    result = MagicMock()
    result.boxes = boxes
    return [result]


def _empty_yolo_results():
    """YOLO results with no detections."""
    result = MagicMock()
    result.boxes = []
    return [result]


def _make_detector_with_model(model_mock, config=None):
    """Create a NeuralDetector that's 'initialized' with a mocked YOLO model."""
    d = NeuralDetector(config=config)
    d._model = model_mock
    d._initialized = True
    return d


# ---------------------------------------------------------------------------
# Interface compliance
# ---------------------------------------------------------------------------

class TestInterfaceCompliance:
    def test_is_subclass_of_human_detector(self):
        assert issubclass(NeuralDetector, HumanDetector)

    def test_has_detect_method(self):
        d = NeuralDetector()
        assert callable(getattr(d, 'detect', None))

    def test_has_initialize_method(self):
        d = NeuralDetector()
        assert callable(getattr(d, 'initialize', None))

    def test_has_cleanup_method(self):
        d = NeuralDetector()
        assert callable(getattr(d, 'cleanup', None))

    def test_has_is_initialized_property(self):
        d = NeuralDetector()
        assert isinstance(d.is_initialized, bool)


# ---------------------------------------------------------------------------
# Factory registration
# ---------------------------------------------------------------------------

class TestFactoryRegistration:
    def test_create_via_factory(self):
        DetectorFactory.register('neural', NeuralDetector)
        detector = DetectorFactory.create('neural')
        assert isinstance(detector, NeuralDetector)

    def test_neural_in_available_list(self):
        DetectorFactory.register('neural', NeuralDetector)
        available = DetectorFactory.list_available()
        assert 'neural' in available


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInitialization:
    def test_starts_uninitialized(self):
        d = NeuralDetector()
        assert not d.is_initialized

    def test_missing_model_raises_detector_error(self):
        d = NeuralDetector(model_path="/nonexistent/yolov8n.pt")
        with pytest.raises(DetectorError, match="model not found"):
            d.initialize()

    def test_successful_init(self, tmp_path):
        model_file = tmp_path / "yolov8n.pt"
        model_file.write_bytes(b"\x00" * 100)

        with patch("src.detection.neural_detector.YOLO", create=True) as mock_yolo_cls:
            mock_yolo_cls.return_value = MagicMock()
            # Patch the import inside initialize()
            with patch.dict("sys.modules", {"ultralytics": MagicMock(YOLO=mock_yolo_cls)}):
                d = NeuralDetector(model_path=str(model_file))
                d.initialize()

                assert d.is_initialized

    def test_ultralytics_import_failure_raises_detector_error(self, tmp_path):
        model_file = tmp_path / "yolov8n.pt"
        model_file.write_bytes(b"\x00" * 100)

        d = NeuralDetector(model_path=str(model_file))
        with patch("builtins.__import__", side_effect=ImportError("no ultralytics")):
            with pytest.raises(DetectorError):
                d.initialize()

    def test_model_load_failure_raises_detector_error(self, tmp_path):
        model_file = tmp_path / "yolov8n.pt"
        model_file.write_bytes(b"\x00" * 100)

        mock_yolo_cls = MagicMock(side_effect=RuntimeError("bad model"))
        with patch.dict("sys.modules", {"ultralytics": MagicMock(YOLO=mock_yolo_cls)}):
            d = NeuralDetector(model_path=str(model_file))
            with pytest.raises(DetectorError, match="Failed to load"):
                d.initialize()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_resets_state(self):
        model = MagicMock()
        d = _make_detector_with_model(model)
        assert d.is_initialized

        d.cleanup()
        assert not d.is_initialized

    def test_cleanup_idempotent(self):
        d = NeuralDetector()
        d.cleanup()  # Should not raise even when not initialized
        assert not d.is_initialized


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

class TestDetection:
    def test_detect_when_not_initialized_raises(self, dummy_frame):
        d = NeuralDetector()
        with pytest.raises(DetectorError, match="not initialized"):
            d.detect(dummy_frame)

    def test_returns_detection_result(self, dummy_frame):
        model = MagicMock()
        box = _make_yolo_box(0.85, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert isinstance(result, DetectionResult)

    def test_person_detected_above_threshold(self, dummy_frame):
        model = MagicMock()
        box = _make_yolo_box(0.85, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result.human_present is True
        assert result.confidence == pytest.approx(0.85, abs=0.01)
        assert result.bounding_box is not None

    def test_no_detections(self, dummy_frame):
        model = MagicMock()
        model.return_value = _empty_yolo_results()

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result.human_present is False
        assert result.confidence == 0.0
        assert result.bounding_box is None

    def test_person_below_threshold_rejected(self, dummy_frame):
        model = MagicMock()
        box = _make_yolo_box(0.3, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result.human_present is False
        assert result.confidence == 0.0

    def test_person_at_threshold_accepted(self, dummy_frame):
        model = MagicMock()
        box = _make_yolo_box(0.5, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result.human_present is True
        assert result.confidence == pytest.approx(0.5, abs=0.01)

    def test_multiple_detections_uses_best(self, dummy_frame):
        model = MagicMock()
        box_low = _make_yolo_box(0.3, 10, 10, 100, 100)
        box_high = _make_yolo_box(0.75, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box_low, box_high])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result.human_present is True
        assert result.confidence == pytest.approx(0.75, abs=0.01)

    def test_custom_confidence_threshold(self, dummy_frame):
        config = DetectorConfig(min_detection_confidence=0.8)
        model = MagicMock()
        box = _make_yolo_box(0.7, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model, config=config)
        result = d.detect(dummy_frame)

        # 0.7 < 0.8 threshold → not detected
        assert result.human_present is False


# ---------------------------------------------------------------------------
# Pose landmarks (always None)
# ---------------------------------------------------------------------------

class TestPoseLandmarks:
    def test_original_pose_landmarks_always_none(self, dummy_frame):
        model = MagicMock()
        box = _make_yolo_box(0.9, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result._original_pose_landmarks is None

    def test_getattr_fallback_returns_none(self, dummy_frame):
        model = MagicMock()
        box = _make_yolo_box(0.9, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        # This is the pattern used in webcam_service.py
        assert getattr(result, '_original_pose_landmarks', None) is None


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------

class TestBoundingBox:
    def test_bounding_box_present_on_detection(self, dummy_frame):
        model = MagicMock()
        # Person at pixel coords (64, 96) to (320, 384)
        box = _make_yolo_box(0.9, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result.bounding_box is not None
        x, y, w, h = result.bounding_box
        assert x == 64
        assert y == 96
        assert w == 256   # 320 - 64
        assert h == 288   # 384 - 96

    def test_no_bounding_box_when_no_detection(self, dummy_frame):
        model = MagicMock()
        model.return_value = _empty_yolo_results()

        d = _make_detector_with_model(model)
        result = d.detect(dummy_frame)

        assert result.bounding_box is None


# ---------------------------------------------------------------------------
# No caching (every frame gets fresh inference)
# ---------------------------------------------------------------------------

class TestNoCaching:
    def test_each_detect_call_runs_inference(self, dummy_frame):
        model = MagicMock()
        box = _make_yolo_box(0.9, 64, 96, 320, 384)
        model.return_value = _make_yolo_results([box])

        d = _make_detector_with_model(model)
        d.detect(dummy_frame)
        d.detect(dummy_frame)
        d.detect(dummy_frame)

        assert model.call_count == 3


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_context_manager_init_and_cleanup(self, tmp_path):
        model_file = tmp_path / "yolov8n.pt"
        model_file.write_bytes(b"\x00" * 100)

        mock_yolo_cls = MagicMock(return_value=MagicMock())
        with patch.dict("sys.modules", {"ultralytics": MagicMock(YOLO=mock_yolo_cls)}):
            d = NeuralDetector(model_path=str(model_file))
            with d:
                assert d.is_initialized

            assert not d.is_initialized
