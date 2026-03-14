"""
Unit tests for NeuralPresenceVerifier (MobileNet-SSD based).

All tests use mocks for cv2.dnn so no model files are needed.
"""
import time
from unittest.mock import patch, MagicMock, PropertyMock

import numpy as np
import pytest

from src.detection.neural_presence_verifier import (
    NeuralPresenceVerifier,
    NeuralPresenceVerifierConfig,
    COCO_PERSON_CLASS_ID,
)
from src.ollama.vision_verifier import VisionVerificationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return NeuralPresenceVerifierConfig(
        prototxt_path="models/MobileNetSSD_deploy.prototxt",
        caffemodel_path="models/MobileNetSSD_deploy.caffemodel",
        confidence_threshold=0.5,
        input_size=(300, 300),
        cache_ttl_seconds=30,
    )


@pytest.fixture
def dummy_frame():
    """A small BGR frame for testing."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


def _make_detections(*entries):
    """Build a (1,1,N,7) detection array from (class_id, confidence) tuples."""
    rows = []
    for cls_id, conf in entries:
        rows.append([0, cls_id, conf, 0, 0, 0, 0])
    arr = np.array(rows, dtype=np.float32).reshape(1, 1, len(rows), 7)
    return arr


def _empty_detections():
    return np.zeros((1, 1, 0, 7), dtype=np.float32)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestNeuralPresenceVerifierConfig:
    def test_defaults(self):
        cfg = NeuralPresenceVerifierConfig()
        assert cfg.confidence_threshold == 0.5
        assert cfg.input_size == (300, 300)
        assert cfg.cache_ttl_seconds == 30
        assert "prototxt" in cfg.prototxt_path.lower()
        assert "caffemodel" in cfg.caffemodel_path.lower()

    def test_custom_values(self):
        cfg = NeuralPresenceVerifierConfig(
            prototxt_path="/custom/path.prototxt",
            caffemodel_path="/custom/model.caffemodel",
            confidence_threshold=0.7,
            input_size=(224, 224),
            cache_ttl_seconds=60,
        )
        assert cfg.prototxt_path == "/custom/path.prototxt"
        assert cfg.confidence_threshold == 0.7
        assert cfg.input_size == (224, 224)
        assert cfg.cache_ttl_seconds == 60


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------

class TestInitialization:
    def test_init_without_model_files_raises(self, config):
        """FileNotFoundError when model files don't exist."""
        config.prototxt_path = "/nonexistent/deploy.prototxt"
        verifier = NeuralPresenceVerifier(config)
        with pytest.raises(FileNotFoundError, match="Prototxt not found"):
            verifier.initialize()

    def test_init_missing_caffemodel_raises(self, config, tmp_path):
        proto = tmp_path / "deploy.prototxt"
        proto.write_text("dummy")
        config.prototxt_path = str(proto)
        config.caffemodel_path = "/nonexistent/model.caffemodel"

        verifier = NeuralPresenceVerifier(config)
        with pytest.raises(FileNotFoundError, match="Caffemodel not found"):
            verifier.initialize()

    def test_init_with_model_files_succeeds(self, config, tmp_path):
        proto = tmp_path / "deploy.prototxt"
        proto.write_text("dummy")
        model = tmp_path / "model.caffemodel"
        model.write_bytes(b"\x00" * 100)

        config.prototxt_path = str(proto)
        config.caffemodel_path = str(model)

        with patch("cv2.dnn.readNetFromCaffe") as mock_read:
            mock_read.return_value = MagicMock()
            verifier = NeuralPresenceVerifier(config)
            verifier.initialize()

            assert verifier.is_initialized
            mock_read.assert_called_once_with(str(proto), str(model))

    def test_not_initialized_returns_none(self, dummy_frame):
        verifier = NeuralPresenceVerifier()
        result = verifier.verify_human_presence(dummy_frame)
        assert result is None

    def test_cleanup(self, config, tmp_path):
        proto = tmp_path / "deploy.prototxt"
        proto.write_text("dummy")
        model = tmp_path / "model.caffemodel"
        model.write_bytes(b"\x00" * 100)
        config.prototxt_path = str(proto)
        config.caffemodel_path = str(model)

        with patch("cv2.dnn.readNetFromCaffe", return_value=MagicMock()):
            verifier = NeuralPresenceVerifier(config)
            verifier.initialize()
            assert verifier.is_initialized

            verifier.cleanup()
            assert not verifier.is_initialized


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------

def _make_verifier_with_net(net_mock, config=None):
    """Create a verifier that's 'initialized' with a mocked network."""
    v = NeuralPresenceVerifier(config or NeuralPresenceVerifierConfig())
    v._net = net_mock
    v._initialized = True
    return v


class TestDetection:
    def test_person_detected_above_threshold(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.85))

        verifier = _make_verifier_with_net(net)
        result = verifier.verify_human_presence(dummy_frame)

        assert result is not None
        assert result.human_detected is True
        assert result.confidence == "certain"

    def test_no_person_detected(self, dummy_frame):
        net = MagicMock()
        # class 6 = bus, not person
        net.forward.return_value = _make_detections((6, 0.95))

        verifier = _make_verifier_with_net(net)
        result = verifier.verify_human_presence(dummy_frame)

        assert result is not None
        assert result.human_detected is False

    def test_person_below_threshold_rejected(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.3))

        verifier = _make_verifier_with_net(net)
        result = verifier.verify_human_presence(dummy_frame)

        assert result is not None
        assert result.human_detected is False

    def test_person_at_threshold_accepted(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.5))

        verifier = _make_verifier_with_net(net)
        result = verifier.verify_human_presence(dummy_frame)

        assert result is not None
        assert result.human_detected is True
        assert result.confidence == "likely"

    def test_empty_detections(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _empty_detections()

        verifier = _make_verifier_with_net(net)
        result = verifier.verify_human_presence(dummy_frame)

        assert result is not None
        assert result.human_detected is False

    def test_multiple_detections_uses_best(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections(
            (COCO_PERSON_CLASS_ID, 0.3),
            (6, 0.99),  # bus
            (COCO_PERSON_CLASS_ID, 0.75),
        )

        verifier = _make_verifier_with_net(net)
        result = verifier.verify_human_presence(dummy_frame)

        assert result.human_detected is True
        assert result.confidence == "likely"  # 0.75 -> "likely"


# ---------------------------------------------------------------------------
# Confidence string mapping
# ---------------------------------------------------------------------------

class TestConfidenceMapping:
    @pytest.mark.parametrize("conf,expected", [
        (0.95, "certain"),
        (0.80, "certain"),
        (0.79, "likely"),
        (0.50, "likely"),
        (0.49, "uncertain"),
        (0.10, "uncertain"),
        (0.0, "uncertain"),
    ])
    def test_confidence_label(self, conf, expected):
        assert NeuralPresenceVerifier._confidence_to_label(conf) == expected


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCaching:
    def test_cache_hit_within_ttl(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        verifier = _make_verifier_with_net(net)
        r1 = verifier.verify_human_presence(dummy_frame)
        r2 = verifier.verify_human_presence(dummy_frame)

        assert r1.timestamp == r2.timestamp
        # network called only once
        assert net.forward.call_count == 1

    def test_cache_miss_after_ttl(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        cfg = NeuralPresenceVerifierConfig(cache_ttl_seconds=1)
        verifier = _make_verifier_with_net(net, cfg)

        r1 = verifier.verify_human_presence(dummy_frame)

        # Expire the cache entry
        frame_hash = list(verifier._cache.keys())[0]
        verifier._cache[frame_hash] = (r1, time.time() - 2)

        r2 = verifier.verify_human_presence(dummy_frame)
        assert r2.timestamp != r1.timestamp
        assert net.forward.call_count == 2

    def test_clear_cache(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        verifier = _make_verifier_with_net(net)
        verifier.verify_human_presence(dummy_frame)
        assert verifier.get_cache_stats()["size"] == 1

        verifier.clear_cache()
        assert verifier.get_cache_stats()["size"] == 0

    def test_cache_stats_empty(self):
        verifier = NeuralPresenceVerifier()
        stats = verifier.get_cache_stats()
        assert stats == {"size": 0, "oldest_age": 0, "newest_age": 0}

    def test_cache_stats_populated(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        verifier = _make_verifier_with_net(net)
        verifier.verify_human_presence(dummy_frame)

        stats = verifier.get_cache_stats()
        assert stats["size"] == 1
        assert stats["oldest_age"] >= 0
        assert stats["newest_age"] >= 0


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

class TestResultType:
    def test_returns_vision_verification_result(self, dummy_frame):
        net = MagicMock()
        net.forward.return_value = _make_detections((COCO_PERSON_CLASS_ID, 0.9))

        verifier = _make_verifier_with_net(net)
        result = verifier.verify_human_presence(dummy_frame)

        assert isinstance(result, VisionVerificationResult)
        assert hasattr(result, "human_detected")
        assert hasattr(result, "confidence")
        assert hasattr(result, "raw_response")
        assert hasattr(result, "timestamp")


# ---------------------------------------------------------------------------
# Interface compatibility
# ---------------------------------------------------------------------------

class TestInterfaceCompatibility:
    """Verify NeuralPresenceVerifier has the same public methods as VisionPresenceVerifier."""

    def test_has_verify_human_presence(self):
        v = NeuralPresenceVerifier()
        assert callable(getattr(v, "verify_human_presence", None))

    def test_has_clear_cache(self):
        v = NeuralPresenceVerifier()
        assert callable(getattr(v, "clear_cache", None))

    def test_has_get_cache_stats(self):
        v = NeuralPresenceVerifier()
        assert callable(getattr(v, "get_cache_stats", None))

    def test_has_initialize(self):
        v = NeuralPresenceVerifier()
        assert callable(getattr(v, "initialize", None))

    def test_has_cleanup(self):
        v = NeuralPresenceVerifier()
        assert callable(getattr(v, "cleanup", None))
