"""
Unit tests for NeuralDetector (MobileNet-SSD primary presence detector).

All tests use mocks for cv2.dnn so no model files are needed.
"""
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from src.detection.base import HumanDetector, DetectorConfig, DetectorError, DetectorFactory
from src.detection.result import DetectionResult
from src.detection.neural_detector import NeuralDetector, COCO_PERSON_CLASS_ID


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_frame():
    """A small BGR frame for testing."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


def _make_detections(*entries):
    """Build a (1,1,N,7) detection array from (class_id, confidence, x1, y1, x2, y2) tuples.

    If only (class_id, confidence) is given, bbox defaults to (0.1, 0.1, 0.5, 0.5).
    """
    rows = []
    for entry in entries:
        if len(entry) == 2:
            cls_id, conf = entry
            rows.append([0, cls_id, conf, 0.1, 0.1, 0.5, 0.5])
        else:
            cls_id, conf, x1, y1, x2, y2 = entry
            rows.append([0, cls_id, conf, x1, y1, x2, y2])
    arr = np.array(rows, dtype=np.float32).reshape(1, 1, len(rows), 7)
    return arr


def _empty_detections():
    return np.zeros((1, 1, 0, 7), dtype=np.float32)


def _make_detector_with_net(net_mock, config=None):
    """Create a NeuralDetector that's 'initialized' with a mocked network."""
    d = NeuralDetector(config=config)
    d._net = net_mock
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
        # Re-register in case another test cleared the registry
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

    def test_missing_prototxt_raises_detector_error(self):
        d = NeuralDetector(prototxt_path="/nonexistent/deploy.prototxt")
        with pytest.raises(DetectorError, match="Prototxt not found"):
            d.initialize()

    def test_missing_caffemodel_raises_detector_error(self, tmp_path):
        proto = tmp_path / "deploy.prototxt"
        proto.write_text("dummy")
        d = NeuralDetector(
            prototxt_path=str(proto),
            caffemodel_path="/nonexistent/model.caffemodel",
        )
        with pytest.raises(DetectorError, match="Caffemodel not found"):
            d.initialize()

    def test_successful_init(self, tmp_path):
        proto = tmp_path / "deploy.prototxt"
        proto.write_text("dummy")
        model = tmp_path / "model.caffemodel"
        model.write_bytes(b"\x00" * 100)

        with patch("cv2.dnn.readNetFromCaffe") as mock_read:
            mock_read.return_value = MagicMock()
            d = NeuralDetector(
                prototxt_path=str(proto),
                caffemodel_path=str(model),
            )
            d.initialize()

            assert d.is_initialized
            mock_read.assert_called_once_with(str(proto), str(model))

    def test_cv2_load_failure_raises_detector_error(self, tmp_path):
        proto = tmp_path / "deploy.prototxt"
        proto.write_text("dummy")
        model = tmp_path / "model.caffemodel"
        model.write_bytes(b"\x00" * 100)

        with patch("cv2.dnn.readNetFromCaffe", side_effect=RuntimeError("bad model")):
            d = NeuralDetector(
                prototxt_path=str(proto),
                caffemodel_path=str(model),
            )
            with pytest.raises(DetectorError, match="Failed to load"):
                d.initialize()


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_resets_state(self):
        net = MagicMock()
        d = _make_detector_with_net(net)
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
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.85))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert isinstance(result, DetectionResult)

    def test_person_detected_above_threshold(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.85))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.human_present is True
        assert result.confidence == pytest.approx(0.85, abs=0.01)
        assert result.bounding_box is not None

    def test_no_person_detected(self, dummy_frame):
        net = MagicMock()
        # class 6 = bus, not person
        net.forward.return_value = _make_detections((6, 0.95))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.human_present is False
        assert result.confidence == 0.0
        assert result.bounding_box is None

    def test_person_below_threshold_rejected(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.3))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.human_present is False
        assert result.confidence == 0.0

    def test_person_at_threshold_accepted(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.5))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.human_present is True
        assert result.confidence == pytest.approx(0.5, abs=0.01)

    def test_empty_detections(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _empty_detections()

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.human_present is False
        assert result.confidence == 0.0
        assert result.bounding_box is None

    def test_multiple_detections_uses_best(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections(
            (COCO_PERSON_CLASS_ID, 0.3),
            (6, 0.99),  # bus — ignored
            (COCO_PERSON_CLASS_ID, 0.75),
        )

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.human_present is True
        assert result.confidence == pytest.approx(0.75, abs=0.01)

    def test_custom_confidence_threshold(self, dummy_frame):
        config = DetectorConfig(min_detection_confidence=0.8)
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.7))

        d = _make_detector_with_net(net, config=config)
        result = d.detect(dummy_frame)

        # 0.7 < 0.8 threshold → not detected
        assert result.human_present is False


# ---------------------------------------------------------------------------
# Pose landmarks (always None)
# ---------------------------------------------------------------------------

class TestPoseLandmarks:
    def test_original_pose_landmarks_always_none(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result._original_pose_landmarks is None

    def test_getattr_fallback_returns_none(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        # This is the pattern used in webcam_service.py
        assert getattr(result, '_original_pose_landmarks', None) is None


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------

class TestBoundingBox:
    def test_bounding_box_present_on_detection(self, dummy_frame):
        net = MagicMock()
        # Person at normalised coords (0.1, 0.2, 0.5, 0.8)
        net.forward.return_value = _make_detections(
            (COCO_PERSON_CLASS_ID, 0.9, 0.1, 0.2, 0.5, 0.8)
        )

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.bounding_box is not None
        x, y, w, h = result.bounding_box
        # Frame is 640x480
        assert x == int(0.1 * 640)   # 64
        assert y == int(0.2 * 480)   # 96
        assert w == int(0.5 * 640) - int(0.1 * 640)  # 256
        assert h == int(0.8 * 480) - int(0.2 * 480)  # 288

    def test_no_bounding_box_when_no_person(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((6, 0.95))

        d = _make_detector_with_net(net)
        result = d.detect(dummy_frame)

        assert result.bounding_box is None


# ---------------------------------------------------------------------------
# No caching (every frame gets fresh inference)
# ---------------------------------------------------------------------------

class TestNoCaching:
    def test_each_detect_call_runs_inference(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        d = _make_detector_with_net(net)
        d.detect(dummy_frame)
        d.detect(dummy_frame)
        d.detect(dummy_frame)

        assert net.forward.call_count == 3


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_context_manager_init_and_cleanup(self, tmp_path):
        proto = tmp_path / "deploy.prototxt"
        proto.write_text("dummy")
        model = tmp_path / "model.caffemodel"
        model.write_bytes(b"\x00" * 100)

        with patch("cv2.dnn.readNetFromCaffe", return_value=MagicMock()):
            d = NeuralDetector(
                prototxt_path=str(proto),
                caffemodel_path=str(model),
            )
            with d:
                assert d.is_initialized

            assert not d.is_initialized
