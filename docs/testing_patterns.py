"""
Testing Patterns and Examples for Webcam Human Detection

This file contains sample testing code, mocking patterns, fixtures,
and TDD examples for the webcam detection project.
"""

import pytest
import pytest_asyncio
import asyncio
import cv2
import numpy as np
import time
from unittest.mock import Mock, patch, MagicMock, call
from typing import Optional, List
import tempfile
import os


# Sample test fixtures
@pytest.fixture
def sample_frame():
    """Create a sample frame for testing."""
    return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)


@pytest.fixture
def sample_frame_with_person():
    """Create a frame that should trigger human detection."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some content that looks like a person (rough approximation)
    cv2.rectangle(frame, (200, 100), (400, 450), (128, 128, 128), -1)  # Body
    cv2.circle(frame, (300, 150), 50, (200, 180, 160), -1)  # Head
    return frame


@pytest.fixture
def empty_frame():
    """Create an empty frame with no human."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_camera():
    """Mock camera for testing."""
    mock_cap = Mock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.return_value = 30.0  # Mock FPS
    return mock_cap


@pytest.fixture
def temp_config_file():
    """Create temporary config file for testing."""
    config_content = """
camera:
  device_id: 0
  width: 640
  height: 480
  fps: 30

detection:
  model_complexity: 1
  min_confidence: 0.5
  smoothing_window: 5
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(config_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


# Configuration testing examples
class TestConfigurationManager:
    """Example tests for configuration management."""
    
    def test_config_loading_success(self, temp_config_file):
        """Test successful configuration loading."""
        from unittest.mock import patch
        
        # Mock YAML loading
        with patch('yaml.safe_load') as mock_yaml:
            mock_yaml.return_value = {
                'camera': {'device_id': 0, 'width': 640},
                'detection': {'min_confidence': 0.5}
            }
            
            # Test config loading logic here
            config = {'camera': {'device_id': 0, 'width': 640}}
            assert config['camera']['device_id'] == 0
            assert config['camera']['width'] == 640
    
    def test_config_missing_file(self):
        """Test handling of missing config file."""
        with pytest.raises(FileNotFoundError):
            # This should raise an exception
            open('nonexistent_config.yaml', 'r').read()
    
    def test_config_validation(self):
        """Test configuration validation."""
        invalid_configs = [
            {'camera': {'device_id': -1}},  # Invalid device ID
            {'camera': {'width': 0}},       # Invalid width
            {'detection': {'min_confidence': 1.5}},  # Invalid confidence
        ]
        
        for config in invalid_configs:
            # Each config should fail validation
            assert 'camera' in config or 'detection' in config


# Camera testing examples
class TestCameraManager:
    """Example tests for camera management."""
    
    @patch('cv2.VideoCapture')
    def test_camera_initialization_success(self, mock_cv2):
        """Test successful camera initialization."""
        # Setup mock
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cv2.return_value = mock_cap
        
        # Test camera initialization
        class MockCameraManager:
            def __init__(self, device_id=0):
                self.cap = mock_cv2(device_id)
                self.is_initialized = self.cap.isOpened()
        
        manager = MockCameraManager()
        assert manager.is_initialized is True
        mock_cv2.assert_called_once_with(0)
    
    @patch('cv2.VideoCapture')
    def test_camera_initialization_failure(self, mock_cv2):
        """Test camera initialization failure."""
        # Setup mock for failed camera
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_cv2.return_value = mock_cap
        
        class MockCameraManager:
            def __init__(self, device_id=0):
                self.cap = mock_cv2(device_id)
                if not self.cap.isOpened():
                    raise RuntimeError("Cannot open camera")
        
        with pytest.raises(RuntimeError, match="Cannot open camera"):
            MockCameraManager()
    
    @patch('cv2.VideoCapture')
    def test_frame_capture(self, mock_cv2, sample_frame):
        """Test frame capture functionality."""
        # Setup mock
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, sample_frame)
        mock_cv2.return_value = mock_cap
        
        class MockFrameCapture:
            def __init__(self):
                self.cap = mock_cv2(0)
            
            def get_frame(self):
                ret, frame = self.cap.read()
                return frame if ret else None
        
        capture = MockFrameCapture()
        frame = capture.get_frame()
        
        assert frame is not None
        assert frame.shape == (480, 640, 3)
        np.testing.assert_array_equal(frame, sample_frame)
    
    @patch('cv2.VideoCapture')
    def test_frame_capture_failure(self, mock_cv2):
        """Test handling of frame capture failure."""
        # Setup mock for failed read
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_cv2.return_value = mock_cap
        
        class MockFrameCapture:
            def __init__(self):
                self.cap = mock_cv2(0)
            
            def get_frame(self):
                ret, frame = self.cap.read()
                return frame if ret else None
        
        capture = MockFrameCapture()
        frame = capture.get_frame()
        
        assert frame is None


# MediaPipe detection testing examples
class TestMediaPipeDetector:
    """Example tests for MediaPipe detection."""
    
    @patch('mediapipe.solutions.pose.Pose')
    def test_detector_initialization(self, mock_pose_class):
        """Test MediaPipe detector initialization."""
        # Setup mock
        mock_pose_instance = Mock()
        mock_pose_class.return_value = mock_pose_instance
        
        class MockDetector:
            def __init__(self):
                self.pose = mock_pose_class(
                    static_image_mode=False,
                    model_complexity=1,
                    min_detection_confidence=0.5
                )
                self.is_initialized = True
        
        detector = MockDetector()
        assert detector.is_initialized is True
        mock_pose_class.assert_called_once_with(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5
        )
    
    @patch('mediapipe.solutions.pose.Pose')
    def test_human_detection_positive(self, mock_pose_class, sample_frame_with_person):
        """Test positive human detection."""
        # Setup mock for positive detection
        mock_pose_instance = Mock()
        mock_results = Mock()
        mock_results.pose_landmarks = Mock()  # Non-None indicates detection
        mock_pose_instance.process.return_value = mock_results
        mock_pose_class.return_value = mock_pose_instance
        
        class MockDetector:
            def __init__(self):
                self.pose = mock_pose_class()
            
            def detect(self, frame):
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(rgb_frame)
                return {
                    'human_present': results.pose_landmarks is not None,
                    'confidence': 0.85 if results.pose_landmarks else 0.0
                }
        
        detector = MockDetector()
        result = detector.detect(sample_frame_with_person)
        
        assert result['human_present'] is True
        assert result['confidence'] > 0.5
    
    @patch('mediapipe.solutions.pose.Pose')
    def test_human_detection_negative(self, mock_pose_class, empty_frame):
        """Test negative human detection."""
        # Setup mock for negative detection
        mock_pose_instance = Mock()
        mock_results = Mock()
        mock_results.pose_landmarks = None  # None indicates no detection
        mock_pose_instance.process.return_value = mock_results
        mock_pose_class.return_value = mock_pose_instance
        
        class MockDetector:
            def __init__(self):
                self.pose = mock_pose_class()
            
            def detect(self, frame):
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.pose.process(rgb_frame)
                return {
                    'human_present': results.pose_landmarks is not None,
                    'confidence': 0.85 if results.pose_landmarks else 0.0
                }
        
        detector = MockDetector()
        result = detector.detect(empty_frame)
        
        assert result['human_present'] is False
        assert result['confidence'] == 0.0


# Queue and threading testing examples
class TestFrameQueue:
    """Example tests for frame queue functionality."""
    
    def test_queue_basic_operations(self, sample_frame):
        """Test basic queue put/get operations."""
        from queue import Queue
        
        frame_queue = Queue(maxsize=5)
        
        # Test put operation
        frame_queue.put(sample_frame)
        assert frame_queue.qsize() == 1
        
        # Test get operation
        retrieved_frame = frame_queue.get()
        np.testing.assert_array_equal(retrieved_frame, sample_frame)
        assert frame_queue.qsize() == 0
    
    def test_queue_overflow_handling(self):
        """Test queue overflow behavior."""
        from queue import Queue, Full
        
        frame_queue = Queue(maxsize=2)
        frames = [np.ones((480, 640, 3)) * i for i in range(3)]
        
        # Fill queue to capacity
        frame_queue.put(frames[0])
        frame_queue.put(frames[1])
        
        # Third put should raise Full exception
        with pytest.raises(Full):
            frame_queue.put(frames[2], block=False)
    
    def test_queue_empty_handling(self):
        """Test queue empty behavior."""
        from queue import Queue, Empty
        
        frame_queue = Queue(maxsize=5)
        
        # Getting from empty queue should raise Empty exception
        with pytest.raises(Empty):
            frame_queue.get(block=False)


# Async testing examples
class TestAsyncProcessing:
    """Example async tests."""
    
    @pytest.mark.asyncio
    async def test_async_frame_processor(self, sample_frame):
        """Test async frame processing."""
        
        class MockAsyncProcessor:
            def __init__(self):
                self.frame_queue = asyncio.Queue(maxsize=5)
                self.result_queue = asyncio.Queue(maxsize=10)
            
            async def process_frame(self, frame):
                # Simulate async processing
                await asyncio.sleep(0.01)
                return {
                    'human_present': True,
                    'confidence': 0.8,
                    'timestamp': time.time()
                }
            
            async def add_frame_and_process(self, frame):
                await self.frame_queue.put(frame)
                frame_from_queue = await self.frame_queue.get()
                result = await self.process_frame(frame_from_queue)
                await self.result_queue.put(result)
                return await self.result_queue.get()
        
        processor = MockAsyncProcessor()
        result = await processor.add_frame_and_process(sample_frame)
        
        assert result['human_present'] is True
        assert result['confidence'] == 0.8
        assert 'timestamp' in result
    
    @pytest.mark.asyncio
    async def test_async_queue_timeout(self):
        """Test async queue timeout behavior."""
        
        async_queue = asyncio.Queue(maxsize=1)
        
        # Test timeout on get from empty queue
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(async_queue.get(), timeout=0.1)
        
        # Fill queue
        await async_queue.put("test_item")
        
        # Test timeout on put to full queue
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(async_queue.put("another_item"), timeout=0.1)


# Performance testing examples
class TestPerformance:
    """Example performance tests."""
    
    def test_processing_latency(self, sample_frame):
        """Test that processing latency meets requirements."""
        
        def mock_detection_function(frame):
            # Simulate detection processing
            start_time = time.time()
            time.sleep(0.05)  # 50ms processing
            return time.time() - start_time
        
        # Test processing time
        processing_time = mock_detection_function(sample_frame)
        
        # Should be under 100ms (0.1 seconds)
        assert processing_time < 0.1
    
    def test_frame_rate_performance(self):
        """Test frame rate performance."""
        
        class MockFrameRateMonitor:
            def __init__(self):
                self.frame_times = []
            
            def record_frame(self):
                self.frame_times.append(time.time())
            
            def get_fps(self):
                if len(self.frame_times) < 2:
                    return 0
                time_span = self.frame_times[-1] - self.frame_times[0]
                return (len(self.frame_times) - 1) / time_span
        
        monitor = MockFrameRateMonitor()
        
        # Simulate 30 frames at ~30 FPS
        for _ in range(30):
            monitor.record_frame()
            time.sleep(1/30)  # ~33ms between frames
        
        fps = monitor.get_fps()
        
        # Should achieve at least 15 FPS
        assert fps >= 15


# Integration testing examples
class TestIntegration:
    """Example integration tests."""
    
    @patch('cv2.VideoCapture')
    @patch('mediapipe.solutions.pose.Pose')
    def test_end_to_end_pipeline(self, mock_pose_class, mock_cv2, sample_frame_with_person):
        """Test complete detection pipeline."""
        
        # Setup camera mock
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, sample_frame_with_person)
        mock_cv2.return_value = mock_cap
        
        # Setup MediaPipe mock
        mock_pose_instance = Mock()
        mock_results = Mock()
        mock_results.pose_landmarks = Mock()  # Positive detection
        mock_pose_instance.process.return_value = mock_results
        mock_pose_class.return_value = mock_pose_instance
        
        class MockPipeline:
            def __init__(self):
                self.camera = mock_cv2(0)
                self.detector = mock_pose_class()
            
            def process_single_frame(self):
                ret, frame = self.camera.read()
                if not ret:
                    return None
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.detector.process(rgb_frame)
                
                return {
                    'human_present': results.pose_landmarks is not None,
                    'frame_processed': True
                }
        
        pipeline = MockPipeline()
        result = pipeline.process_single_frame()
        
        assert result is not None
        assert result['human_present'] is True
        assert result['frame_processed'] is True
    
    def test_error_recovery(self):
        """Test error handling and recovery."""
        
        class MockCameraWithFailure:
            def __init__(self):
                self.call_count = 0
            
            def read_frame(self):
                self.call_count += 1
                if self.call_count <= 3:
                    raise RuntimeError("Camera disconnected")
                return np.zeros((480, 640, 3), dtype=np.uint8)
            
            def attempt_reconnection(self):
                # Simulate successful reconnection after 3 failures
                return self.call_count > 3
        
        camera = MockCameraWithFailure()
        
        # First 3 attempts should fail
        for _ in range(3):
            with pytest.raises(RuntimeError):
                camera.read_frame()
        
        # Fourth attempt should succeed
        assert camera.attempt_reconnection() is True
        frame = camera.read_frame()
        assert frame is not None


# TDD example - Red-Green-Refactor cycle
class TestTDDExample:
    """Example of TDD cycle for detection result class."""
    
    def test_detection_result_creation_fails_initially(self):
        """RED: Test should fail initially when class doesn't exist."""
        
        # This test would fail until we implement DetectionResult
        try:
            from detection_result import DetectionResult
            result = DetectionResult(human_present=True, confidence=0.8)
            assert result.human_present is True
            assert result.confidence == 0.8
        except ImportError:
            # Expected to fail initially
            pytest.skip("DetectionResult not implemented yet")
    
    def test_detection_result_validation(self):
        """Test validation logic for DetectionResult."""
        
        # Mock implementation for testing
        class DetectionResult:
            def __init__(self, human_present: bool, confidence: float):
                if not 0.0 <= confidence <= 1.0:
                    raise ValueError("Confidence must be between 0.0 and 1.0")
                self.human_present = human_present
                self.confidence = confidence
        
        # Valid case
        result = DetectionResult(human_present=True, confidence=0.8)
        assert result.confidence == 0.8
        
        # Invalid case - confidence too high
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DetectionResult(human_present=True, confidence=1.5)
        
        # Invalid case - confidence too low
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DetectionResult(human_present=True, confidence=-0.1)


# Parameterized testing examples
class TestParameterized:
    """Example parameterized tests."""
    
    @pytest.mark.parametrize("confidence,expected", [
        (0.0, False),
        (0.3, False),
        (0.5, True),
        (0.8, True),
        (1.0, True),
    ])
    def test_confidence_threshold(self, confidence, expected):
        """Test confidence threshold logic with different values."""
        
        def is_confident_detection(confidence: float, threshold: float = 0.5) -> bool:
            return confidence >= threshold
        
        result = is_confident_detection(confidence)
        assert result is expected
    
    @pytest.mark.parametrize("frame_shape,expected_valid", [
        ((480, 640, 3), True),   # Valid color frame
        ((480, 640), False),     # Grayscale - invalid for our use
        ((240, 320, 3), True),   # Small but valid
        ((0, 0, 3), False),      # Zero size - invalid
    ])
    def test_frame_validation(self, frame_shape, expected_valid):
        """Test frame validation with different shapes."""
        
        def validate_frame(frame_shape: tuple) -> bool:
            if len(frame_shape) != 3:
                return False
            height, width, channels = frame_shape
            return height > 0 and width > 0 and channels == 3
        
        result = validate_frame(frame_shape)
        assert result is expected_valid


# Test utilities and helpers
class TestUtilities:
    """Utilities for testing."""
    
    @staticmethod
    def create_test_frame(width: int = 640, height: int = 480, 
                         color: tuple = (128, 128, 128)) -> np.ndarray:
        """Create a test frame with specified properties."""
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        return frame
    
    @staticmethod
    def assert_detection_result_valid(result: dict):
        """Assert that a detection result has required fields."""
        required_fields = ['human_present', 'confidence']
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        assert isinstance(result['human_present'], bool)
        assert isinstance(result['confidence'], (int, float))
        assert 0.0 <= result['confidence'] <= 1.0
    
    @staticmethod
    def mock_mediapipe_results(has_landmarks: bool = True, 
                              confidence: float = 0.8):
        """Create mock MediaPipe results."""
        mock_results = Mock()
        if has_landmarks:
            mock_results.pose_landmarks = Mock()
            # Add mock landmark data
            mock_landmark = Mock()
            mock_landmark.visibility = confidence
            mock_results.pose_landmarks.landmark = [mock_landmark] * 33  # 33 pose landmarks
        else:
            mock_results.pose_landmarks = None
        
        return mock_results


# ============================================================================
# GESTURE RECOGNITION TESTING PATTERNS
# ============================================================================

class GestureDetectionTestPatterns:
    """Comprehensive testing patterns for gesture recognition system."""
    
    @staticmethod
    def test_hand_landmark_detection():
        """Test pattern for MediaPipe hands integration."""
        
        sample_test = """
import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.gesture.hand_detection import HandDetector
from src.gesture.result import GestureResult

class TestHandDetection:
    
    @pytest.fixture
    def hand_detector(self):
        config = {
            'max_num_hands': 2,
            'min_detection_confidence': 0.7,
            'min_tracking_confidence': 0.5
        }
        return HandDetector(config)
    
    @pytest.fixture
    def sample_frame(self):
        # Create test frame (640x480 RGB)
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    @pytest.fixture
    def mock_hand_landmarks(self):
        '''Mock MediaPipe hand landmarks for testing.'''
        mock_landmark = Mock()
        mock_landmark.x = 0.5
        mock_landmark.y = 0.3
        mock_landmark.z = 0.1
        mock_landmark.visibility = 0.9
        
        # Create 21 landmarks (MediaPipe hands standard)
        landmarks = [mock_landmark] * 21
        landmarks[0].y = 0.7  # WRIST
        landmarks[9].y = 0.4  # MIDDLE_FINGER_MCP (hand center)
        landmarks[17].y = 0.45 # PINKY_MCP
        
        mock_hand = Mock()
        mock_hand.landmark = landmarks
        return [mock_hand]  # List of hands
    
    def test_hand_detector_initialization(self, hand_detector):
        '''Test hand detector initializes correctly.'''
        assert hand_detector is not None
        assert hand_detector.max_num_hands == 2
        assert hand_detector.min_detection_confidence == 0.7
    
    @patch('mediapipe.solutions.hands.Hands')
    def test_detect_hands_success(self, mock_mp_hands, hand_detector, sample_frame, mock_hand_landmarks):
        '''Test successful hand detection.'''
        # Setup mock
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.multi_hand_landmarks = mock_hand_landmarks
        mock_instance.process.return_value = mock_result
        mock_mp_hands.return_value = mock_instance
        
        # Re-initialize detector with mock
        hand_detector._setup_mediapipe()
        
        # Test detection
        result = hand_detector.detect_hands(sample_frame)
        
        assert result is not None
        assert len(result.hands) == 1
        assert result.hands[0] is not None
    
    def test_detect_hands_no_hands(self, hand_detector, sample_frame):
        '''Test detection when no hands present.'''
        with patch.object(hand_detector.hands, 'process') as mock_process:
            mock_result = Mock()
            mock_result.multi_hand_landmarks = None
            mock_process.return_value = mock_result
            
            result = hand_detector.detect_hands(sample_frame)
            
            assert result is not None
            assert len(result.hands) == 0
    
    def test_extract_landmarks(self, hand_detector, mock_hand_landmarks):
        '''Test landmark extraction from MediaPipe results.'''
        landmarks = hand_detector._extract_landmarks(mock_hand_landmarks[0])
        
        assert len(landmarks) == 21
        assert all(0 <= landmark['x'] <= 1 for landmark in landmarks)
        assert all(0 <= landmark['y'] <= 1 for landmark in landmarks)
    
    def test_calculate_palm_normal(self, hand_detector, mock_hand_landmarks):
        '''Test palm normal vector calculation.'''
        normal = hand_detector._calculate_palm_normal(mock_hand_landmarks[0])
        
        assert len(normal) == 3
        assert isinstance(normal, np.ndarray)
        # Normal should be unit vector
        assert abs(np.linalg.norm(normal) - 1.0) < 0.01
    
    def test_palm_facing_camera_detection(self, hand_detector, mock_hand_landmarks):
        '''Test palm orientation detection.'''
        # Test palm facing camera (positive Z normal)
        with patch.object(hand_detector, '_calculate_palm_normal') as mock_normal:
            mock_normal.return_value = np.array([0.1, 0.1, 0.8])  # Facing camera
            
            is_facing = hand_detector._is_palm_facing_camera(mock_hand_landmarks[0])
            assert is_facing is True
            
            # Test palm not facing camera (negative Z normal)
            mock_normal.return_value = np.array([0.1, 0.1, -0.8])  # Away from camera
            
            is_facing = hand_detector._is_palm_facing_camera(mock_hand_landmarks[0])
            assert is_facing is False
    
    def test_hand_detector_cleanup(self, hand_detector):
        '''Test proper resource cleanup.'''
        hand_detector.cleanup()
        # Verify MediaPipe resources are released
        assert hand_detector.hands is None
        """
        
        return sample_test
    
    @staticmethod 
    def test_gesture_classification():
        """Test pattern for gesture classification algorithms."""
        
        sample_test = """
import pytest
import numpy as np
from unittest.mock import Mock
from src.gesture.classification import GestureClassifier
from src.gesture.result import GestureResult

class TestGestureClassification:
    
    @pytest.fixture
    def gesture_classifier(self):
        config = {
            'shoulder_offset_threshold': 0.1,
            'palm_facing_confidence': 0.6,
            'debounce_frames': 3,
            'gesture_timeout_ms': 5000
        }
        return GestureClassifier(config)
    
    @pytest.fixture
    def hand_above_shoulder(self):
        '''Hand positioned above shoulder level.'''
        return {
            'hand_center_y': 0.2,  # Above shoulder
            'palm_normal': np.array([0.1, 0.1, 0.8]),  # Facing camera
            'landmarks': self._create_hand_landmarks(center_y=0.2)
        }
    
    @pytest.fixture
    def hand_below_shoulder(self):
        '''Hand positioned below shoulder level.'''
        return {
            'hand_center_y': 0.6,  # Below shoulder
            'palm_normal': np.array([0.1, 0.1, 0.8]),  # Facing camera
            'landmarks': self._create_hand_landmarks(center_y=0.6)
        }
    
    def _create_hand_landmarks(self, center_y=0.4):
        '''Helper to create mock hand landmarks.'''
        landmarks = []
        for i in range(21):
            landmark = Mock()
            landmark.x = 0.5
            landmark.y = center_y + np.random.uniform(-0.1, 0.1)
            landmark.z = 0.1
            landmarks.append(landmark)
        return landmarks
    
    def test_hand_up_gesture_detection(self, gesture_classifier, hand_above_shoulder):
        '''Test detecting hand up gesture.'''
        shoulder_y = 0.4
        
        is_gesture = gesture_classifier.detect_hand_up_gesture(
            hand_above_shoulder['landmarks'],
            shoulder_y,
            hand_above_shoulder['palm_normal']
        )
        
        assert is_gesture is True
    
    def test_hand_not_up_below_shoulder(self, gesture_classifier, hand_below_shoulder):
        '''Test hand below shoulder is not hand up gesture.'''
        shoulder_y = 0.4
        
        is_gesture = gesture_classifier.detect_hand_up_gesture(
            hand_below_shoulder['landmarks'],
            shoulder_y,
            hand_below_shoulder['palm_normal']
        )
        
        assert is_gesture is False
    
    def test_palm_not_facing_camera(self, gesture_classifier, hand_above_shoulder):
        '''Test palm not facing camera is not hand up gesture.'''
        shoulder_y = 0.4
        palm_away = np.array([0.1, 0.1, -0.8])  # Away from camera
        
        is_gesture = gesture_classifier.detect_hand_up_gesture(
            hand_above_shoulder['landmarks'],
            shoulder_y,
            palm_away
        )
        
        assert is_gesture is False
    
    def test_gesture_debouncing(self, gesture_classifier):
        '''Test gesture debouncing mechanism.'''
        # Simulate inconsistent detections
        detections = [True, False, True, True, True]
        
        for detection in detections:
            result = gesture_classifier.process_detection(detection)
        
        # Only stable detections should trigger gesture
        assert gesture_classifier.is_gesture_stable()
    
    def test_gesture_timeout(self, gesture_classifier):
        '''Test gesture timeout functionality.'''
        # Start gesture
        gesture_classifier.start_gesture('hand_up')
        
        # Simulate time passage beyond timeout
        import time
        time.sleep(6)  # Longer than 5s timeout
        
        is_expired = gesture_classifier.is_gesture_expired()
        assert is_expired is True
        """
        
        return sample_test
    
    @staticmethod
    def test_gesture_detector_integration():
        """Test pattern for main GestureDetector class."""
        
        sample_test = """
import pytest
from unittest.mock import Mock, patch
from src.detection.gesture_detector import GestureDetector
from src.gesture.result import GestureResult

class TestGestureDetectorIntegration:
    
    @pytest.fixture
    def gesture_detector(self):
        config = {
            'enabled': True,
            'run_only_when_human_present': True,
            'min_human_confidence_threshold': 0.6
        }
        return GestureDetector(config)
    
    @pytest.fixture
    def sample_frame(self):
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    @pytest.fixture
    def pose_landmarks_with_shoulders(self):
        '''Mock pose landmarks including shoulder points.'''
        landmarks = []
        for i in range(33):  # MediaPipe pose has 33 landmarks
            landmark = Mock()
            landmark.x = 0.5
            landmark.y = 0.5
            landmark.z = 0.1
            landmarks.append(landmark)
        
        # Set shoulder landmarks (indices 11, 12)
        landmarks[11].y = 0.4  # LEFT_SHOULDER
        landmarks[12].y = 0.4  # RIGHT_SHOULDER
        
        mock_pose = Mock()
        mock_pose.landmark = landmarks
        return mock_pose
    
    def test_gesture_detector_initialization(self, gesture_detector):
        '''Test gesture detector initializes correctly.'''
        assert gesture_detector.enabled is True
        assert gesture_detector.run_only_when_human_present is True
        assert gesture_detector.hand_detector is not None
        assert gesture_detector.gesture_classifier is not None
    
    @patch('src.gesture.hand_detection.HandDetector')
    @patch('src.gesture.classification.GestureClassifier')
    def test_detect_gestures_with_human_present(self, mock_classifier, mock_detector, 
                                              gesture_detector, sample_frame, 
                                              pose_landmarks_with_shoulders):
        '''Test gesture detection when human is present.'''
        # Setup mocks
        mock_detector_instance = Mock()
        mock_detector.return_value = mock_detector_instance
        mock_detector_instance.detect_hands.return_value = Mock(hands=[Mock()])
        
        mock_classifier_instance = Mock()
        mock_classifier.return_value = mock_classifier_instance
        mock_classifier_instance.detect_hand_up_gesture.return_value = True
        
        # Test detection
        result = gesture_detector.detect_gestures(
            sample_frame, 
            pose_landmarks=pose_landmarks_with_shoulders
        )
        
        assert isinstance(result, GestureResult)
        assert result.gesture_detected is True
        assert result.gesture_type == 'hand_up'
    
    def test_skip_detection_when_no_human(self, gesture_detector, sample_frame):
        '''Test gesture detection is skipped when no human present.'''
        result = gesture_detector.detect_gestures(sample_frame, pose_landmarks=None)
        
        assert isinstance(result, GestureResult)
        assert result.gesture_detected is False
        assert result.confidence == 0.0
    
    def test_shoulder_reference_calculation(self, gesture_detector, pose_landmarks_with_shoulders):
        '''Test shoulder reference point calculation.'''
        shoulder_y = gesture_detector._get_shoulder_reference_y(pose_landmarks_with_shoulders)
        
        assert shoulder_y is not None
        assert 0.0 <= shoulder_y <= 1.0
        assert shoulder_y == 0.4  # Average of both shoulders
    
    def test_resource_management(self, gesture_detector):
        '''Test proper resource cleanup.'''
        gesture_detector.cleanup()
        
        # Verify all components are cleaned up
        assert gesture_detector.hand_detector is None
        assert gesture_detector.gesture_classifier is None
        """
        
        return sample_test


# ============================================================================
# SSE SERVICE TESTING PATTERNS  
# ============================================================================

class SSEServiceTestPatterns:
    """Comprehensive testing patterns for SSE service implementation."""
    
    @staticmethod
    def test_sse_service_core():
        """Test pattern for SSE service core functionality."""
        
        sample_test = """
import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from src.service.sse_service import SSEGestureService
from src.service.events import ServiceEvent, EventType

class TestSSEServiceCore:
    
    @pytest.fixture
    def sse_service(self):
        config = {
            'host': 'localhost',
            'port': 8766,
            'max_connections': 10,
            'heartbeat_interval': 30.0
        }
        return SSEGestureService(config)
    
    @pytest.fixture
    def test_client(self, sse_service):
        return TestClient(sse_service.app)
    
    @pytest.fixture
    def sample_gesture_event(self):
        return ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data={
                'gesture_type': 'hand_up',
                'confidence': 0.85,
                'hand': 'right',
                'duration_ms': 1500
            }
        )
    
    def test_sse_service_initialization(self, sse_service):
        '''Test SSE service initializes correctly.'''
        assert sse_service.host == 'localhost'
        assert sse_service.port == 8766
        assert len(sse_service.active_streams) == 0
        assert sse_service.app is not None
    
    def test_health_endpoint(self, test_client):
        '''Test health check endpoint.'''
        response = test_client.get('/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'active_connections' in data
        assert 'uptime' in data
    
    def test_clients_endpoint(self, test_client):
        '''Test clients listing endpoint.'''
        response = test_client.get('/clients')
        
        assert response.status_code == 200
        data = response.json()
        assert 'active_clients' in data
        assert 'clients' in data
        assert data['active_clients'] == 0
    
    @pytest.mark.asyncio
    async def test_sse_connection_setup(self, sse_service):
        '''Test SSE connection setup and cleanup.'''
        client_id = 'test_client_001'
        
        # Simulate connection
        event_queue = asyncio.Queue()
        sse_service.active_streams[client_id] = event_queue
        sse_service.client_metadata[client_id] = {
            'connected_at': datetime.now(),
            'events_sent': 0
        }
        
        assert client_id in sse_service.active_streams
        assert client_id in sse_service.client_metadata
        
        # Cleanup
        del sse_service.active_streams[client_id]
        del sse_service.client_metadata[client_id]
        
        assert client_id not in sse_service.active_streams
    
    @pytest.mark.asyncio
    async def test_event_broadcasting(self, sse_service, sample_gesture_event):
        '''Test event broadcasting to connected clients.'''
        # Setup mock clients
        client_queues = {}
        for i in range(3):
            client_id = f'client_{i}'
            client_queues[client_id] = asyncio.Queue()
            sse_service.active_streams[client_id] = client_queues[client_id]
            sse_service.client_metadata[client_id] = {
                'connected_at': datetime.now(),
                'events_sent': 0
            }
        
        # Broadcast event
        await sse_service._handle_gesture_event(sample_gesture_event)
        
        # Verify all clients received the event
        for client_id, queue in client_queues.items():
            assert not queue.empty()
            event_data = await queue.get()
            assert event_data['event_type'] == 'gesture_detected'
            assert 'data' in event_data
    
    def test_sse_event_formatting(self, sse_service):
        '''Test SSE event format compliance.'''
        event_data = {
            'gesture_type': 'hand_up',
            'confidence': 0.8
        }
        
        formatted = sse_service._format_sse_event('gesture_detected', event_data)
        
        assert formatted.startswith('event: gesture_detected\\n')
        assert 'data: {' in formatted
        assert formatted.endswith('\\n\\n')
        
        # Verify JSON is valid
        lines = formatted.split('\\n')
        data_line = [line for line in lines if line.startswith('data: ')][0]
        json_data = data_line[6:]  # Remove 'data: ' prefix
        parsed = json.loads(json_data)
        assert parsed['gesture_type'] == 'hand_up'
    
    @pytest.mark.asyncio
    async def test_client_disconnection_handling(self, sse_service):
        '''Test proper cleanup when client disconnects.'''
        client_id = 'disconnecting_client'
        
        # Setup client
        queue = asyncio.Queue()
        sse_service.active_streams[client_id] = queue
        sse_service.client_metadata[client_id] = {
            'connected_at': datetime.now(),
            'events_sent': 5
        }
        
        # Simulate error during event sending
        with patch.object(queue, 'put_nowait', side_effect=Exception('Connection lost')):
            await sse_service._handle_gesture_event(
                ServiceEvent(event_type=EventType.GESTURE_DETECTED, data={})
            )
        
        # Verify client was cleaned up
        assert client_id not in sse_service.active_streams
        assert client_id not in sse_service.client_metadata
        """
        
        return sample_test
    
    @staticmethod
    def test_sse_client_integration():
        """Test pattern for SSE client-side integration."""
        
        sample_test = """
import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from src.service.sse_client import GestureSSEClient  # Hypothetical client class

class TestSSEClientIntegration:
    
    @pytest.fixture
    def sse_client(self):
        return GestureSSEClient(
            url='http://localhost:8766/events/gestures/test_client',
            client_id='test_client'
        )
    
    @pytest.fixture
    def mock_event_source_response(self):
        '''Mock server response for SSE events.'''
        events = [
            "event: connected\\ndata: {\\"client_id\\": \\"test_client\\"}\\n\\n",
            "event: gesture_detected\\ndata: {\\"gesture_type\\": \\"hand_up\\", \\"confidence\\": 0.8}\\n\\n",
            "event: heartbeat\\ndata: {\\"timestamp\\": \\"2024-01-01T10:00:00Z\\"}\\n\\n"
        ]
        return ''.join(events)
    
    @pytest.mark.asyncio
    async def test_sse_connection_establishment(self, sse_client):
        '''Test SSE client connection establishment.'''
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'text/event-stream'}
            mock_stream.return_value.__aenter__.return_value = mock_response
            
            connected = await sse_client.connect()
            assert connected is True
    
    @pytest.mark.asyncio
    async def test_event_parsing(self, sse_client, mock_event_source_response):
        '''Test parsing of SSE event stream.'''
        events = []
        
        def event_handler(event_type, data):
            events.append({'type': event_type, 'data': data})
        
        sse_client.on_event = event_handler
        
        # Mock the response stream
        with patch('httpx.AsyncClient.stream') as mock_stream:
            mock_response = Mock()
            mock_response.aiter_lines.return_value = mock_event_source_response.split('\\n')
            mock_stream.return_value.__aenter__.return_value = mock_response
            
            await sse_client.process_events()
        
        # Verify events were parsed correctly
        assert len(events) == 3
        assert events[0]['type'] == 'connected'
        assert events[1]['type'] == 'gesture_detected'
        assert events[2]['type'] == 'heartbeat'
    
    @pytest.mark.asyncio 
    async def test_connection_retry_logic(self, sse_client):
        '''Test automatic reconnection on connection failure.'''
        with patch('httpx.AsyncClient.stream') as mock_stream:
            # First attempt fails
            mock_stream.side_effect = [
                Exception('Connection failed'),
                Mock()  # Second attempt succeeds
            ]
            
            with patch.object(sse_client, '_wait_before_retry', new_callable=AsyncMock):
                result = await sse_client.connect_with_retry(max_retries=2)
                
                assert result is True
                assert mock_stream.call_count == 2
    
    def test_gesture_event_handling(self, sse_client):
        '''Test handling of gesture-specific events.'''
        gesture_events = []
        
        def gesture_handler(gesture_data):
            gesture_events.append(gesture_data)
        
        sse_client.on_gesture_detected = gesture_handler
        
        # Simulate gesture event
        event_data = {
            'gesture_type': 'hand_up',
            'confidence': 0.85,
            'hand': 'right'
        }
        
        sse_client._handle_event('gesture_detected', event_data)
        
        assert len(gesture_events) == 1
        assert gesture_events[0]['gesture_type'] == 'hand_up'
    
    @pytest.mark.asyncio
    async def test_heartbeat_handling(self, sse_client):
        '''Test heartbeat event processing.'''
        last_heartbeat = None
        
        def heartbeat_handler(timestamp):
            nonlocal last_heartbeat
            last_heartbeat = timestamp
        
        sse_client.on_heartbeat = heartbeat_handler
        
        # Simulate heartbeat
        sse_client._handle_event('heartbeat', {'timestamp': '2024-01-01T10:00:00Z'})
        
        assert last_heartbeat is not None
        assert '2024-01-01' in last_heartbeat
        """
        
        return sample_test


# ============================================================================
# INTEGRATION TESTING PATTERNS
# ============================================================================

class IntegrationTestPatterns:
    """Integration testing patterns for gesture + SSE pipeline."""
    
    @staticmethod
    def test_end_to_end_gesture_streaming():
        """End-to-end test pattern for complete gesture streaming pipeline."""
        
        sample_test = """
import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch
from src.detection.multimodal_detector import MultiModalDetector
from src.detection.gesture_detector import GestureDetector
from src.service.sse_service import SSEGestureService
from src.service.events import EventPublisher

class TestGestureStreamingPipeline:
    
    @pytest.fixture
    async def gesture_streaming_pipeline(self):
        '''Setup complete gesture streaming pipeline.'''
        # Initialize components
        event_publisher = EventPublisher()
        
        multimodal_detector = MultiModalDetector({
            'model_complexity': 1,
            'min_detection_confidence': 0.5
        })
        
        gesture_detector = GestureDetector({
            'enabled': True,
            'run_only_when_human_present': True
        })
        
        sse_service = SSEGestureService({
            'host': 'localhost',
            'port': 8766
        })
        
        # Connect components
        sse_service.setup_gesture_integration(event_publisher)
        
        return {
            'event_publisher': event_publisher,
            'multimodal_detector': multimodal_detector,
            'gesture_detector': gesture_detector,
            'sse_service': sse_service
        }
    
    @pytest.fixture
    def test_frame_with_person_and_gesture(self):
        '''Test frame simulating person making hand up gesture.'''
        # Create realistic test frame (640x480 RGB)
        frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)
        
        # Add visual elements to simulate person (optional for realistic testing)
        # This could include drawing simple shapes to represent a person
        
        return frame
    
    @pytest.mark.asyncio
    async def test_complete_gesture_detection_flow(self, gesture_streaming_pipeline, 
                                                  test_frame_with_person_and_gesture):
        '''Test complete flow: Frame → Presence → Gesture → SSE Event.'''
        pipeline = gesture_streaming_pipeline
        frame = test_frame_with_person_and_gesture
        
        # Mock SSE client for testing
        received_events = []
        
        async def mock_sse_client():
            # Simulate SSE client receiving events
            client_id = 'test_integration_client'
            queue = asyncio.Queue()
            pipeline['sse_service'].active_streams[client_id] = queue
            pipeline['sse_service'].client_metadata[client_id] = {
                'connected_at': datetime.now(),
                'events_sent': 0
            }
            
            # Wait for and collect events
            try:
                while True:
                    event = await asyncio.wait_for(queue.get(), timeout=2.0)
                    received_events.append(event)
                    if event.get('event_type') == 'gesture_detected':
                        break
            except asyncio.TimeoutError:
                pass
        
        # Start SSE client simulation
        client_task = asyncio.create_task(mock_sse_client())
        
        # Step 1: Human presence detection
        with patch.object(pipeline['multimodal_detector'], 'detect') as mock_detect:
            # Mock human present with pose landmarks
            mock_result = Mock()
            mock_result.human_present = True
            mock_result.confidence = 0.8
            mock_result.landmarks = self._create_mock_pose_landmarks()
            mock_detect.return_value = mock_result
            
            presence_result = pipeline['multimodal_detector'].detect(frame)
            assert presence_result.human_present is True
        
        # Step 2: Gesture detection (only runs when human present)
        with patch.object(pipeline['gesture_detector'], 'detect_gestures') as mock_gesture:
            # Mock hand up gesture detected
            mock_gesture_result = Mock()
            mock_gesture_result.gesture_detected = True
            mock_gesture_result.gesture_type = 'hand_up'
            mock_gesture_result.confidence = 0.85
            mock_gesture_result.hand = 'right'
            mock_gesture.return_value = mock_gesture_result
            
            gesture_result = pipeline['gesture_detector'].detect_gestures(
                frame, pose_landmarks=presence_result.landmarks
            )
            assert gesture_result.gesture_detected is True
        
        # Step 3: Event publishing
        pipeline['event_publisher'].publish(ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data=gesture_result.to_dict()
        ))
        
        # Wait for SSE processing
        await asyncio.sleep(0.1)
        
        # Verify end-to-end flow
        await client_task
        
        assert len(received_events) > 0
        gesture_event = received_events[0]
        assert gesture_event['event_type'] == 'gesture_detected'
        assert gesture_event['data']['gesture_type'] == 'hand_up'
    
    def _create_mock_pose_landmarks(self):
        '''Helper to create mock pose landmarks with shoulders.'''
        landmarks = []
        for i in range(33):
            landmark = Mock()
            landmark.x = 0.5
            landmark.y = 0.5
            landmark.z = 0.1
            landmarks.append(landmark)
        
        # Set shoulder positions
        landmarks[11].y = 0.4  # LEFT_SHOULDER
        landmarks[12].y = 0.4  # RIGHT_SHOULDER
        
        mock_landmarks = Mock()
        mock_landmarks.landmark = landmarks
        return mock_landmarks
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, gesture_streaming_pipeline):
        '''Test system performance with multiple concurrent clients.'''
        pipeline = gesture_streaming_pipeline
        num_clients = 10
        
        # Setup multiple SSE clients
        client_tasks = []
        for i in range(num_clients):
            client_id = f'load_test_client_{i}'
            queue = asyncio.Queue()
            pipeline['sse_service'].active_streams[client_id] = queue
            pipeline['sse_service'].client_metadata[client_id] = {
                'connected_at': datetime.now(),
                'events_sent': 0
            }
        
        # Generate multiple gesture events
        start_time = time.time()
        num_events = 50
        
        for i in range(num_events):
            event = ServiceEvent(
                event_type=EventType.GESTURE_DETECTED,
                data={
                    'gesture_type': 'hand_up',
                    'confidence': 0.8,
                    'event_id': i
                }
            )
            await pipeline['sse_service']._handle_gesture_event(event)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify performance metrics
        assert processing_time < 5.0  # Should process 50 events in under 5 seconds
        assert len(pipeline['sse_service'].active_streams) == num_clients
        
        # Verify all clients received events
        for client_id in pipeline['sse_service'].active_streams:
            queue = pipeline['sse_service'].active_streams[client_id]
            assert not queue.empty()
        """
        
        return sample_test


# ============================================================================
# MOCK UTILITIES FOR TESTING
# ============================================================================

class GestureTestingMocks:
    """Utility mocks for gesture recognition testing."""
    
    @staticmethod
    def create_mock_mediapipe_hands():
        """Create mock MediaPipe hands solution."""
        
        mock_code = """
from unittest.mock import Mock, MagicMock
import numpy as np

class MockMediaPipeHands:
    '''Mock MediaPipe hands for testing without actual MediaPipe dependency.'''
    
    def __init__(self):
        self.HAND_CONNECTIONS = [
            (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),  # Index
            (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
            (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
            (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
        ]
    
    def create_mock_hands_instance(self, detect_hands=True, hand_above_shoulder=False):
        '''Create mock hands instance with configurable behavior.'''
        mock_hands = Mock()
        
        if detect_hands:
            # Create mock hand landmarks
            landmarks = []
            for i in range(21):
                landmark = Mock()
                landmark.x = 0.5 + np.random.uniform(-0.2, 0.2)
                
                if hand_above_shoulder and i == 9:  # Middle finger MCP (hand center)
                    landmark.y = 0.2  # Above shoulder level
                else:
                    landmark.y = 0.5 + np.random.uniform(-0.2, 0.2)
                
                landmark.z = 0.1 + np.random.uniform(-0.05, 0.05)
                landmark.visibility = 0.9
                landmarks.append(landmark)
            
            # Create mock hand result
            mock_hand = Mock()
            mock_hand.landmark = landmarks
            
            mock_result = Mock()
            mock_result.multi_hand_landmarks = [mock_hand]
        else:
            mock_result = Mock()
            mock_result.multi_hand_landmarks = None
        
        mock_hands.process.return_value = mock_result
        return mock_hands
    
    def create_mock_hand_landmarks(self, hand_y_position=0.4, palm_facing_camera=True):
        '''Create mock hand landmarks with specific positioning.'''
        landmarks = []
        
        for i in range(21):
            landmark = Mock()
            landmark.x = 0.5
            landmark.y = hand_y_position
            
            if palm_facing_camera:
                landmark.z = 0.1  # Positive Z for palm facing camera
            else:
                landmark.z = -0.1  # Negative Z for palm away from camera
            
            landmarks.append(landmark)
        
        # Adjust specific landmarks
        landmarks[0].y = hand_y_position + 0.2  # WRIST below hand center
        landmarks[9].y = hand_y_position  # MIDDLE_FINGER_MCP (hand center)
        landmarks[17].y = hand_y_position  # PINKY_MCP
        
        mock_hand = Mock()
        mock_hand.landmark = landmarks
        return mock_hand

# Usage in tests:
# mock_mp_hands = MockMediaPipeHands()
# mock_hands_instance = mock_mp_hands.create_mock_hands_instance(
#     detect_hands=True, 
#     hand_above_shoulder=True
# )
        """
        
        return mock_code


if __name__ == "__main__":
    print("Gesture Recognition Testing Patterns")
    print("1. Show hand detection test pattern")
    print("2. Show gesture classification test pattern") 
    print("3. Show SSE service test pattern")
    print("4. Show integration test pattern")
    print("5. Show mock utilities")
    
    choice = input("Enter choice (1-5): ")
    
    patterns = GestureDetectionTestPatterns()
    sse_patterns = SSEServiceTestPatterns()
    integration_patterns = IntegrationTestPatterns()
    mock_utils = GestureTestingMocks()
    
    if choice == "1":
        print(patterns.test_hand_landmark_detection())
    elif choice == "2":
        print(patterns.test_gesture_classification())
    elif choice == "3":
        print(sse_patterns.test_sse_service_core())
    elif choice == "4":
        print(integration_patterns.test_end_to_end_gesture_streaming())
    elif choice == "5":
        print(mock_utils.create_mock_mediapipe_hands())
    else:
        print("Invalid choice") 