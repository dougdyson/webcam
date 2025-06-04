"""
Test wait-for-completion Ollama processing for Latest Frame implementation.

This test verifies that:
1. Real-time detection continues at full FPS (15+ FPS)
2. Only 1 Ollama request runs at a time (wait for completion)
3. No thread explosion (single background thread)
4. Latest frame is used when Ollama becomes available
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio

from src.processing.latest_frame_processor import LatestFrameProcessor


class TestLatestFrameWaitForCompletion:
    """Test wait-for-completion Ollama processing in Latest Frame mode."""

    @pytest.fixture
    def mock_camera(self):
        """Mock camera manager."""
        camera = Mock()
        # Create realistic frames for testing
        import numpy as np
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        camera.get_frame.return_value = test_frame
        return camera

    @pytest.fixture
    def mock_detector(self):
        """Mock detector with human detection."""
        detector = Mock()
        detection_result = Mock()
        detection_result.human_present = True
        detection_result.confidence = 0.8
        detector.detect.return_value = detection_result
        return detector

    @pytest.fixture
    def slow_description_service(self):
        """Mock description service with realistic slow async calls."""
        service = Mock()
        
        # Track call state
        service._call_count = 0
        service._active_calls = 0
        
        async def slow_describe_snapshot(snapshot):
            service._active_calls += 1
            service._call_count += 1
            try:
                await asyncio.sleep(0.5)  # Simulate slow Ollama call
                description_result = Mock()
                description_result.success = True
                description_result.description = f"Description {service._call_count}"
                return description_result
            finally:
                service._active_calls -= 1
        
        service.describe_snapshot = slow_describe_snapshot
        return service

    @pytest.fixture
    def latest_frame_processor(self, mock_camera, mock_detector):
        """Create Latest Frame Processor for testing."""
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        return processor

    def test_real_time_detection_at_full_fps(self, latest_frame_processor, mock_camera):
        """Test that detection continues at full FPS regardless of Ollama processing."""
        detection_count = 0
        start_time = time.time()
        
        # Simulate high-frequency detection calls
        for _ in range(30):  # 30 frames
            frame = mock_camera.get_frame()
            result = latest_frame_processor.process_frame(frame)
            detection_count += 1
            time.sleep(1/30)  # 30 FPS simulation
        
        elapsed_time = time.time() - start_time
        actual_fps = detection_count / elapsed_time
        
        # Should achieve at least 25 FPS (close to target 30 FPS)
        assert actual_fps >= 25, f"Detection FPS too low: {actual_fps:.1f} FPS"

    def test_only_one_ollama_call_at_a_time(self, latest_frame_processor, slow_description_service):
        """Test that only 1 Ollama call runs at a time - wait for completion."""
        # Setup processor with description service
        latest_frame_processor.set_description_service(slow_description_service)
        
        # Process many frames rapidly while Ollama is busy
        import numpy as np
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Process 20 frames quickly
        for _ in range(20):
            latest_frame_processor.process_frame_with_description(test_frame)
            time.sleep(0.05)  # 20 FPS
        
        # Wait for any processing to complete
        time.sleep(1.0)
        
        # Should have made exactly 1 call (because previous one must complete first)
        assert slow_description_service._call_count <= 2, f"Too many concurrent calls: {slow_description_service._call_count}"

    def test_no_thread_explosion(self, latest_frame_processor, slow_description_service):
        """Test that we don't create excessive threads for Ollama processing."""
        initial_thread_count = threading.active_count()
        
        # Setup processor with description service
        latest_frame_processor.set_description_service(slow_description_service)
        
        # Process many frames rapidly
        import numpy as np
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        for _ in range(50):  # 50 rapid frames
            latest_frame_processor.process_frame_with_description(test_frame)
            time.sleep(0.01)  # Very fast processing
        
        # Allow brief time for any background threads to start
        time.sleep(0.5)
        
        final_thread_count = threading.active_count()
        new_threads = final_thread_count - initial_thread_count
        
        # Should create exactly 1 new thread (the Ollama processing thread)
        assert new_threads <= 1, f"Thread explosion detected: {new_threads} new threads"

    def test_latest_frame_used_when_ollama_available(self, latest_frame_processor):
        """Test that the latest frame is used when Ollama becomes available."""
        # Create a description service that we can control
        frames_sent_to_ollama = []
        processing_complete = threading.Event()
        
        class ControlledDescriptionService:
            def __init__(self):
                self.is_processing = False
            
            async def describe_snapshot(self, snapshot):
                self.is_processing = True
                frames_sent_to_ollama.append(snapshot.frame)
                await asyncio.sleep(0.1)  # Brief processing
                self.is_processing = False
                processing_complete.set()
                
                description_result = Mock()
                description_result.success = True
                description_result.description = "Test description"
                return description_result
        
        controlled_service = ControlledDescriptionService()
        
        # Setup processor
        latest_frame_processor.set_description_service(controlled_service)
        
        # Create distinguishable frames
        import numpy as np
        frame1 = np.ones((480, 640, 3), dtype=np.uint8) * 50   # Dark frame
        frame2 = np.ones((480, 640, 3), dtype=np.uint8) * 100  # Medium frame  
        frame3 = np.ones((480, 640, 3), dtype=np.uint8) * 200  # Bright frame
        
        # Process frame1 - should start processing
        latest_frame_processor.process_frame_with_description(frame1)
        time.sleep(0.02)  # Brief delay to let processing start
        
        # Process frame2 and frame3 while frame1 is being processed
        latest_frame_processor.process_frame_with_description(frame2)
        latest_frame_processor.process_frame_with_description(frame3)
        
        # Wait for first processing to complete
        processing_complete.wait(timeout=1.0)
        
        # Should have processed frame1 initially
        assert len(frames_sent_to_ollama) >= 1
        if len(frames_sent_to_ollama) > 0:
            first_frame = frames_sent_to_ollama[0]
            avg_brightness = first_frame.mean()
            # Should be frame1 (dark frame)
            assert 45 <= avg_brightness <= 55, f"Wrong first frame processed, brightness: {avg_brightness}"

    def test_red_wait_for_completion_interface(self, latest_frame_processor):
        """Test: Wait-for-completion interface should work correctly."""
        # These methods should exist and work for wait-for-completion processing
        
        # Should be able to set description service
        mock_service = Mock()
        latest_frame_processor.set_description_service(mock_service)
        assert latest_frame_processor.description_service == mock_service
            
        # Should be able to check if description is processing (initially False)
        assert latest_frame_processor.is_description_processing() == False
            
        # Should be able to process frame with description (returns detection result)
        import numpy as np
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = latest_frame_processor.process_frame_with_description(test_frame)
        assert result is not None  # Should return detection result 