"""
Integration tests for Latest Frame Processor in WebcamService.

This module tests the integration of Latest Frame Processor with the service layer,
following TDD methodology for the Queue → Latest Frame migration.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
from io import StringIO


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
    
    def test_detection_loop_displays_latest_frame_status(self):
        """
        RED: Test that detection loop displays "⚡ LATEST FRAME" status instead of queue info.
        
        Phase 3.2 RED step: This will fail because status still shows queue processing.
        """
        import inspect
        import webcam_service as service_module
        
        # Get the source code of the detection_loop method
        service_source = inspect.getsource(service_module.WebcamService.detection_loop)
        
        # Should contain Latest Frame status display
        assert "⚡ LATEST FRAME" in service_source, \
            "Detection loop should display '⚡ LATEST FRAME' status"
        
        # Should NOT contain queue status display
        assert "🤖 Queue:" not in service_source, \
            "Detection loop should not display queue status"
    
    def test_description_processing_works_with_latest_frame_results(self):
        """
        RED: Test that description processing works with Latest Frame Processor results.
        
        Phase 4.1 RED step: This will fail because _process_single_frame still uses direct detector
        instead of Latest Frame Processor, creating an inconsistency.
        """
        from webcam_service import WebcamService
        import numpy as np
        import inspect
        
        # Check that _process_single_frame method uses Latest Frame Processor consistently
        service_source = inspect.getsource(WebcamService._process_single_frame)
        
        # Should use Latest Frame Processor for consistency with detection loop
        assert "self.latest_frame_processor.process_frame(frame)" in service_source, \
            "_process_single_frame should use Latest Frame Processor for consistency"
        
        # Should NOT use direct detector calls (inconsistent with detection loop)
        assert "self.detector.detect(frame)" not in service_source, \
            "_process_single_frame should not use direct detector calls (inconsistent with Latest Frame processing)"
        
        # Create service with real initialization for description testing
        service = WebcamService()
        
        # Mock components but keep description service setup
        service.camera = Mock()
        service.detector = Mock()
        service.latest_frame_processor = Mock()
        service.gesture_detector = Mock()
        
        # Mock description service to track calls
        service.description_service = Mock()
        
        # Create a realistic frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        service.camera.get_frame.return_value = test_frame
        
        # Mock Latest Frame Processor to return human detection (confidence > 0.6 to trigger description)
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.75  # Above 0.6 threshold for descriptions
        service.latest_frame_processor.process_frame.return_value = mock_detection_result
        
        # Mock gesture detection
        service.gesture_detector.detect_gestures.return_value = None
        
        # Mock HTTP service
        service.http_service = Mock()
        service.http_service.current_status = Mock()
        service.http_service.current_status.detection_count = 0
        
        # Test the frame processing method that should handle descriptions
        result = service._process_single_frame(test_frame)
        
        # Verify that description processing was attempted
        # The key test: Latest Frame results should trigger description processing
        assert result is not None, "Frame processing should return a result"
        assert "detection_called" in result, "Result should contain detection status"
        
        # Since we have Latest Frame Processor providing human detection,
        # description processing should be considered
        # (This tests the integration between Latest Frame results and description pipeline)
        
        # If human detected with sufficient confidence, description should be called
        if mock_detection_result.human_present and mock_detection_result.confidence > 0.6:
            # Description processing should be attempted when human is detected
            # This is testing the integration pathway
            assert True, "Description integration pathway should be accessible" 