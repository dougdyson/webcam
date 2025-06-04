"""
Integration tests for Latest Frame Processor in WebcamService.

This module tests the integration of Latest Frame Processor with the service layer,
following TDD methodology for the Queue → Latest Frame migration.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np


class TestLatestFrameProcessorServiceIntegration:
    """Test Latest Frame Processor integration with WebcamService."""
    
    def test_latest_frame_processor_can_be_imported(self):
        """
        RED: Test that Latest Frame Processor can be imported in webcam_service.
        
        This test will fail initially because the import doesn't exist yet.
        This is Phase 2.1 RED step of our TDD migration.
        """
        # Try to import LatestFrameProcessor in the service context
        try:
            from src.processing.latest_frame_processor import LatestFrameProcessor
            # If we get here, the import works
            assert True, "LatestFrameProcessor can be imported"
        except ImportError as e:
            pytest.fail(f"LatestFrameProcessor import failed: {e}")
    
    def test_webcam_service_can_import_latest_frame_processor(self):
        """
        RED: Test that WebcamService can import LatestFrameProcessor.
        
        This will fail because the import statement doesn't exist in webcam_service.py yet.
        """
        # This test ensures the import exists in the actual service file
        import inspect
        import webcam_service as service_module
        
        # Check if LatestFrameProcessor is imported in the service module
        source = inspect.getsource(service_module)
        assert "from src.processing.latest_frame_processor import LatestFrameProcessor" in source, \
            "WebcamService should import LatestFrameProcessor"
    
    def test_webcam_service_initializes_latest_frame_processor(self):
        """
        RED: Test that WebcamService initializes LatestFrameProcessor.
        
        Phase 2.2 RED step: This will fail because the initialization doesn't exist yet.
        """
        from webcam_service import WebcamService
        
        # Create service instance
        service = WebcamService()
        
        # Check that latest_frame_processor attribute exists initially (should be None)
        assert hasattr(service, 'latest_frame_processor'), \
            "WebcamService should have latest_frame_processor attribute"
        
        # Initialize the service to trigger component initialization
        service.initialize()
        
        # Now check that latest_frame_processor is properly initialized
        assert service.latest_frame_processor is not None, \
            "latest_frame_processor should be initialized after initialize() call"
    
    def test_detection_loop_uses_latest_frame_processor(self):
        """
        RED: Test that detection loop uses Latest Frame Processor instead of direct detector calls.
        
        Phase 3.1 RED step: This will fail because detection_loop still uses direct detector calls.
        """
        from webcam_service import WebcamService
        
        # Create service instance with mocked components
        service = WebcamService()
        
        # Mock the camera and detector to avoid real initialization
        service.camera = Mock()
        service.detector = Mock()
        service.latest_frame_processor = Mock()
        service.gesture_detector = Mock()  # NEW: Mock gesture detector to avoid NoneType errors
        
        # Mock frame from camera
        mock_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        service.camera.get_frame.return_value = mock_frame
        
        # Mock Latest Frame Processor detection result
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.75
        service.latest_frame_processor.process_frame.return_value = mock_detection_result
        
        # Mock gesture detection to return None (no gesture)
        service.gesture_detector.detect_gestures.return_value = None
        
        # Set service as running for single iteration with quick exit
        service.is_running = True
        service._shutdown_requested = False
        
        # Use a counter to stop after a few iterations
        call_counter = [0]
        original_get_frame = service.camera.get_frame
        
        def limited_get_frame():
            call_counter[0] += 1
            if call_counter[0] > 2:  # Stop after 2 frames
                service.is_running = False
                return None
            return original_get_frame()
        
        service.camera.get_frame = limited_get_frame
        
        # Mock time.sleep to avoid actual delays
        with patch('time.sleep'):
            with patch('time.time', return_value=0):  # Fixed time to avoid status printing
                # Run detection loop for limited iterations
                try:
                    service.detection_loop()
                except Exception:
                    pass  # Expected since we'll break the loop
        
        # Verify Latest Frame Processor was called (at least once)
        assert service.latest_frame_processor.process_frame.call_count >= 1, \
            f"Latest Frame Processor should be called at least once, was called {service.latest_frame_processor.process_frame.call_count} times"
        
        # Verify it was called with frame data
        calls = service.latest_frame_processor.process_frame.call_args_list
        assert len(calls) > 0, "Latest Frame Processor should have been called with frame data"
        
        # Verify direct detector was NOT called
        service.detector.detect.assert_not_called() 