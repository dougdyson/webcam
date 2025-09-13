import numpy as np
import time

from src.detection.result import DetectionResult


def _make_gray(h, w, value=0):
    return np.full((h, w), value, dtype=np.uint8)


def _make_rect(h, w, rect_val=255):
    img = np.zeros((h, w), dtype=np.uint8)
    h0, h1 = h // 4, 3 * h // 4
    w0, w1 = w // 4, 3 * w // 4
    img[h0:h1, w0:w1] = rect_val
    return img


def test_phash_distance_identical_vs_different():
    from src.processing.image_similarity import compute_phash, phash_distance

    a = _make_rect(120, 160)
    b = a.copy()
    c = _make_gray(120, 160, value=0)  # very different

    ha = compute_phash(a)
    hb = compute_phash(b)
    hc = compute_phash(c)

    # identical images have tiny distance
    assert phash_distance(ha, hb) <= 2
    # clearly different images have larger distance (at least a few bits)
    assert phash_distance(ha, hc) >= 5


def test_ssim_edges_identical_vs_different():
    from src.processing.image_similarity import edge_ssim

    a = _make_rect(120, 160)
    b = a.copy()
    c = _make_gray(120, 160, value=0)

    ssim_same = edge_ssim(a, b)
    ssim_diff = edge_ssim(a, c)

    assert ssim_same > 0.9
    assert ssim_diff < 0.8


def test_reference_manager_capacity_and_best_match():
    from src.processing.reference_manager import ReferenceManager

    rm = ReferenceManager(max_references=3)
    base = _make_rect(120, 160)
    variant1 = np.roll(base, 2, axis=1)
    variant2 = np.roll(base, 4, axis=0)
    other = _make_gray(120, 160, 0)

    rm.add_reference(base)
    rm.add_reference(variant1)
    rm.add_reference(variant2)
    # Adding a fourth should evict the oldest (base)
    rm.add_reference(other)

    assert rm.size() == 3

    # best match for base-like images should be closer to variant1/2 than to 'other'
    ref, dist = rm.get_best_reference(base)
    assert ref is not None
    assert dist < 20


def test_presence_gate_hysteresis_and_cooldown():
    from src.processing.reference_manager import ReferenceManager
    from src.processing.presence_gate import PresenceGate, PresenceGateConfig

    rm = ReferenceManager(max_references=3)
    gate = PresenceGate(
        rm,
        PresenceGateConfig(
            gating_enabled=True,
            # Lower pHash same-threshold to ensure our synthetic rectangle differs
            phash_threshold_same=4,
            ssim_threshold_same=0.90,
            enter_k=3,
            exit_l=5,
            cooldown_ms=1000,
        ),
    )

    # Seed a reference for the empty scene
    empty = _make_gray(120, 160, 0)
    rm.add_reference(empty)

    ts = 0.0

    # 1) MediaPipe says human present but frame equals reference -> gate should reject
    det = DetectionResult(human_present=True, confidence=0.9)
    gr = gate.process(empty, det, timestamp_s=ts)
    assert gr.human_present is False

    # 2) Provide 3 changed frames -> enter hysteresis should flip to True after 3
    human_frame = _make_rect(120, 160)
    for i in range(3):
        ts += 0.1
        det2 = DetectionResult(human_present=True, confidence=0.9)
        gr = gate.process(human_frame, det2, timestamp_s=ts)
    assert gr.human_present is True

    # 3) Immediately provide negatives within cooldown -> should remain True
    for i in range(3):
        ts += 0.1  # within 1s cooldown
        det3 = DetectionResult(human_present=False, confidence=0.9)
        gr = gate.process(empty, det3, timestamp_s=ts)
        assert gr.human_present is True

    # 4) After cooldown, provide 5 negatives -> should exit to False
    ts += 1.1  # surpass cooldown
    for i in range(5):
        ts += 0.1
        det4 = DetectionResult(human_present=False, confidence=0.9)
        gr = gate.process(empty, det4, timestamp_s=ts)
    assert gr.human_present is False


def test_presence_gate_auto_reference_capture():
    from src.processing.reference_manager import ReferenceManager
    from src.processing.presence_gate import PresenceGate, PresenceGateConfig

    rm = ReferenceManager(max_references=2)
    gate = PresenceGate(
        rm,
        PresenceGateConfig(
            gating_enabled=True,
            phash_threshold_same=10,
            ssim_threshold_same=0.90,
            enter_k=2,
            exit_l=2,
            cooldown_ms=200,
            capture_stable_seconds=0.2,
            max_refs=2,
        ),
    )

    empty = _make_gray(120, 160, 0)
    ts = 0.0

    # Feed stable negatives for > capture_stable_seconds to trigger capture
    for i in range(3):
        gr = gate.process(empty, DetectionResult(human_present=False, confidence=0.9), timestamp_s=ts)
        ts += 0.1

    assert rm.size() >= 1
