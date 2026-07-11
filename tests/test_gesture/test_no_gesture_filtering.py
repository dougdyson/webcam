from types import SimpleNamespace

import pytest

from src.gesture.classification import GestureResult
from webcam_service import WebcamService


@pytest.mark.parametrize("gesture_type", ["Unknown", "none", "None", "", None])
def test_no_gesture_sentinels_are_not_detected(gesture_type):
    result = GestureResult(gesture_type, 0.0)

    assert result.gesture_detected is False


@pytest.mark.parametrize("gesture_type", ["Unknown", "none", "None", "", None])
def test_service_does_not_publish_no_gesture_sentinels(gesture_type):
    service = WebcamService()
    gesture_result = SimpleNamespace(
        gesture_detected=True,
        gesture_type=gesture_type,
        confidence=0.9,
    )

    assert service._should_publish_gesture(gesture_result) is False


@pytest.mark.parametrize("confidence", [0.0, 0.69])
def test_service_does_not_publish_low_confidence_gestures(confidence):
    service = WebcamService()
    gesture_result = SimpleNamespace(
        gesture_detected=True,
        gesture_type="Open_Palm",
        confidence=confidence,
    )

    assert service._should_publish_gesture(gesture_result) is False


def test_service_publishes_confident_real_gesture():
    service = WebcamService()
    gesture_result = SimpleNamespace(
        gesture_detected=True,
        gesture_type="Open_Palm",
        confidence=0.7,
    )

    assert service._should_publish_gesture(gesture_result) is True


def test_thumb_like_hand_below_shoulder_is_not_a_thumb_up():
    classifier = _classifier()
    hand_landmarks = _thumb_only_landmarks(hand_center_y=0.84)
    pose_landmarks = _pose_landmarks(shoulder_y=0.56)

    result = classifier.detect_gesture_type(
        hand_landmarks,
        pose_landmarks,
        palm_normal_vector=_palm_away(),
    )

    assert result.gesture_type == "Unknown"
    assert result.gesture_detected is False


def test_lateral_thumb_above_shoulder_is_not_a_thumb_up():
    classifier = _classifier()
    hand_landmarks = _thumb_only_landmarks(
        hand_center_y=0.24,
        thumb_tip_x=0.78,
        thumb_tip_y=0.24,
    )
    pose_landmarks = _pose_landmarks(shoulder_y=0.56)

    result = classifier.detect_gesture_type(
        hand_landmarks,
        pose_landmarks,
        palm_normal_vector=_palm_away(),
    )

    assert result.gesture_type == "Unknown"
    assert result.gesture_detected is False


def test_vertical_thumb_above_shoulder_can_be_thumb_up():
    classifier = _classifier()
    hand_landmarks = _thumb_only_landmarks(
        hand_center_y=0.24,
        thumb_tip_x=0.58,
        thumb_tip_y=0.06,
    )
    pose_landmarks = _pose_landmarks(shoulder_y=0.56)

    result = classifier.detect_gesture_type(
        hand_landmarks,
        pose_landmarks,
        palm_normal_vector=_palm_away(),
    )

    assert result.gesture_type == "Thumb_Up"
    assert result.gesture_detected is True
    assert result.confidence >= 0.7


def _classifier():
    from src.gesture.classification import GestureClassifier

    return GestureClassifier(
        {
            "shoulder_offset_threshold": 0.12,
            "palm_facing_confidence": 0.8,
        }
    )


def _landmark(x=0.5, y=0.5, z=0.0):
    return SimpleNamespace(x=x, y=y, z=z)


def _pose_landmarks(shoulder_y):
    landmarks = [_landmark() for _ in range(33)]
    landmarks[11] = _landmark(y=shoulder_y)
    landmarks[12] = _landmark(y=shoulder_y)
    return landmarks


def _thumb_only_landmarks(hand_center_y, thumb_tip_x=0.76, thumb_tip_y=None):
    thumb_tip_y = hand_center_y if thumb_tip_y is None else thumb_tip_y
    landmarks = [_landmark(y=hand_center_y) for _ in range(21)]
    landmarks[0] = _landmark(0.50, hand_center_y + 0.10)
    landmarks[2] = _landmark(0.56, hand_center_y + 0.02)
    landmarks[3] = _landmark(0.60, hand_center_y)
    landmarks[4] = _landmark(thumb_tip_x, thumb_tip_y)
    landmarks[9] = _landmark(0.50, hand_center_y)

    for tip_idx, pip_idx in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        landmarks[pip_idx] = _landmark(0.50, hand_center_y - 0.02)
        landmarks[tip_idx] = _landmark(0.50, hand_center_y + 0.08)

    return landmarks


def _palm_away():
    import numpy as np

    return np.array([0.0, 0.0, -0.8])
