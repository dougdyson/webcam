"""
Integration tests for main application initialization.

These tests verify that all components integrate correctly during
initialization and that the complete detection pipeline works.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.cli.main import MainApp, MainAppConfig, MainAppError
from src.detection.result import DetectionResult


class TestMainAppInitializationIntegration:
    """Integration tests for MainApp initialization and component coordination."""

    @patch('src.cli.main.create_detector')  # Updated to use factory pattern
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_detector_is_properly_initialized(self, mock_filter, mock_processor,
                                            mock_queue, mock_camera, mock_create_detector):
        """Should properly initialize detector with correct configuration."""
        # Setup mocks
        mock_detector_instance = Mock()
        mock_create_detector.return_value = mock_detector_instance
        
        config = MainAppConfig(detection_confidence_threshold=0.7)
        app = MainApp(config)
        app.initialize()
        
        # Verify detector was created with correct configuration
        mock_create_detector.assert_called_once()
        args, kwargs = mock_create_detector.call_args
        assert args[0] == 'multimodal'  # Updated default detector type
        assert hasattr(args[1], 'min_detection_confidence')
        assert args[1].min_detection_confidence == 0.7
        
        # Verify detector initialization was called
        mock_detector_instance.initialize.assert_called_once()
        
        # Verify detector is accessible
        assert app.detector is mock_detector_instance

    @patch('src.cli.main.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_complete_initialization_chain(self, mock_filter, mock_processor,
                                         mock_queue, mock_camera, mock_create_detector):
        """Should initialize complete component chain correctly."""
        # Setup mock detector
        mock_detector_instance = Mock()
        mock_create_detector.return_value = mock_detector_instance
        
        # Setup other mocks
        mock_camera_instance = Mock()
        mock_camera.return_value = mock_camera_instance
        
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        mock_filter_instance = Mock()
        mock_filter.return_value = mock_filter_instance
        
        app = MainApp()
        app.initialize()
        
        # Verify all components were created and connected
        assert app.camera_manager is mock_camera_instance
        assert app.detector is mock_detector_instance
        assert app.frame_queue is mock_queue_instance
        assert app.frame_processor is mock_processor_instance
        assert app.presence_filter is mock_filter_instance
        
        # Verify processor was initialized with correct dependencies
        mock_processor.assert_called_once()
        processor_kwargs = mock_processor.call_args[1]
        assert processor_kwargs['frame_queue'] is mock_queue_instance
        assert processor_kwargs['detector'] is mock_detector_instance

    @patch('src.cli.main.create_detector')  # Updated to use factory pattern
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_initialization_failure_cleanup(self, mock_filter, mock_processor,
                                           mock_queue, mock_camera, mock_create_detector):
        """Should handle initialization failures gracefully."""
        # Setup detector mock to succeed
        mock_detector_instance = Mock()
        mock_create_detector.return_value = mock_detector_instance
        
        # Make frame processor creation fail
        mock_processor.side_effect = Exception("Processor initialization failed")
        
        app = MainApp()
        
        with pytest.raises(MainAppError) as exc_info:
            app.initialize()
        
        assert "Failed to initialize application components" in str(exc_info.value)
        assert exc_info.value.original_error is not None

    @patch('src.cli.main.create_detector')  # Updated to use factory pattern
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_real_frame_processing_pipeline(self, mock_filter, mock_processor,
                                          mock_queue, mock_camera, mock_create_detector):
        """Should coordinate frame processing through complete pipeline."""
        # Setup detector with realistic behavior
        mock_detector_instance = Mock()
        mock_create_detector.return_value = mock_detector_instance
        
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.8,
            bounding_box=(100, 100, 200, 300),
            landmarks=[(0.5, 0.3), (0.6, 0.4)]
        )
        mock_detector_instance.detect.return_value = detection_result
        
        # Setup camera with test frame
        mock_camera_instance = Mock()
        mock_camera.return_value = mock_camera_instance
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_camera_instance.get_frame.return_value = test_frame
        
        # Setup other components
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        mock_filter_instance = Mock()
        mock_filter.return_value = mock_filter_instance
        
        app = MainApp()
        app.initialize()
        
        # Process a frame through the pipeline (integration test would do this asynchronously)
        frame = app.camera_manager.get_frame()
        result = app.detector.detect(frame)
        app.presence_filter.add_result(result)
        
        # Verify pipeline coordination
        assert frame is test_frame
        assert result is detection_result
        mock_filter_instance.add_result.assert_called_once_with(detection_result) 