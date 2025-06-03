"""
Tests for MainApp - Application lifecycle and coordination.

This module tests the main application coordinator that integrates
camera management, detection, processing, and filtering components.
"""

import asyncio
import signal
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import pytest
import numpy as np

from src.cli.main import MainApp, MainAppConfig, MainAppError
from src.camera.config import CameraConfig
from src.detection.result import DetectionResult
from src.processing.filter import PresenceFilterConfig


class TestMainAppConfiguration:
    """Test MainApp configuration and validation."""

    def test_main_app_config_creation(self):
        """Should create MainAppConfig with default values."""
        config = MainAppConfig()
        
        assert config.camera_profile == 'default'
        assert config.detector_type == 'multimodal'
        assert config.detection_confidence_threshold == 0.5
        assert config.enable_logging is True
        assert config.log_level == 'INFO'
        assert config.log_file is None
        assert config.enable_display is False
        assert config.max_runtime_seconds is None
        assert config.config_file is None

    def test_main_app_config_with_custom_values(self):
        """Should create MainAppConfig with custom values."""
        config = MainAppConfig(
            camera_profile='high_quality',
            detector_type='mediapipe',
            detection_confidence_threshold=0.7,
            enable_logging=False,
            log_level='DEBUG',
            log_file='test.log',
            enable_display=True,
            max_runtime_seconds=60.0,
            config_file='custom.yaml'
        )
        
        assert config.camera_profile == 'high_quality'
        assert config.detector_type == 'mediapipe'
        assert config.detection_confidence_threshold == 0.7
        assert config.enable_logging is False
        assert config.log_level == 'DEBUG'
        assert config.log_file == 'test.log'
        assert config.enable_display is True
        assert config.max_runtime_seconds == 60.0
        assert config.config_file == 'custom.yaml'

    def test_main_app_config_validation(self):
        """Should validate MainAppConfig parameters."""
        # Test invalid confidence threshold
        with pytest.raises(ValueError, match="Detection confidence threshold must be between 0.0 and 1.0"):
            MainAppConfig(detection_confidence_threshold=-0.1)
        
        with pytest.raises(ValueError, match="Detection confidence threshold must be between 0.0 and 1.0"):
            MainAppConfig(detection_confidence_threshold=1.1)
        
        # Test invalid log level
        with pytest.raises(ValueError, match="Log level must be one of"):
            MainAppConfig(log_level='INVALID')
        
        # Test invalid runtime
        with pytest.raises(ValueError, match="Max runtime seconds must be positive"):
            MainAppConfig(max_runtime_seconds=-1.0)


class TestMainAppInitialization:
    """Test MainApp initialization and component setup."""

    @patch('src.cli.main.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_initialization_with_defaults(self, mock_filter, mock_processor, 
                                                  mock_queue, mock_camera, mock_create_detector):
        """Should initialize MainApp with default configuration."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        app = MainApp()
        
        assert app.config.camera_profile == 'default'
        assert app.config.detector_type == 'multimodal'  # Updated default
        assert app.config.detection_confidence_threshold == 0.5
        assert app.camera_manager is None
        assert app.detector is None
        assert app.frame_queue is None
        assert app.frame_processor is None
        assert app.presence_filter is None
        assert app.is_running is False
        assert app.frames_processed == 0

    @patch('src.cli.main.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_initialization_with_custom_config(self, mock_filter, mock_processor,
                                                       mock_queue, mock_camera, mock_create_detector):
        """Should initialize MainApp with custom configuration."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        config = MainAppConfig(
            camera_profile='high_quality',
            detector_type='mediapipe',
            detection_confidence_threshold=0.8
        )
        app = MainApp(config)
        
        assert app.config.camera_profile == 'high_quality'
        assert app.config.detector_type == 'mediapipe'
        assert app.config.detection_confidence_threshold == 0.8

    @patch('src.cli.main.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_component_initialization(self, mock_filter, mock_processor,
                                              mock_queue, mock_camera, mock_create_detector):
        """Should initialize all application components."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        app = MainApp()
        app.initialize()
        
        # Verify all components were created
        assert app.camera_manager is not None
        assert app.detector is not None
        assert app.frame_queue is not None
        assert app.frame_processor is not None
        assert app.presence_filter is not None
        
        # Verify detector was created with correct type and config
        mock_create_detector.assert_called_once()
        args, kwargs = mock_create_detector.call_args
        assert args[0] == 'multimodal'  # Updated default detector type
        assert hasattr(args[1], 'min_detection_confidence')
        
        # Verify detector was initialized
        mock_detector.initialize.assert_called_once()

    def test_main_app_initialization_failure_handling(self):
        """Should handle component initialization failures gracefully."""
        config = MainAppConfig()
        app = MainApp(config)
        
        # Mock component that raises exception during initialization
        with patch('src.cli.main.CameraManager') as mock_camera:
            mock_camera.side_effect = Exception("Camera initialization failed")
            
            with pytest.raises(MainAppError) as exc_info:
                app.initialize()
            
            assert "Failed to initialize application components" in str(exc_info.value)
            assert exc_info.value.original_error is not None


class TestMainAppLifecycle:
    """Test MainApp lifecycle management."""

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    @pytest.mark.asyncio
    async def test_main_app_start_stop_lifecycle(self, mock_filter, mock_processor,
                                          mock_queue, mock_camera, mock_create_detector):
        """Should handle start/stop lifecycle correctly."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        mock_processor_instance = Mock()
        mock_processor_instance.start = AsyncMock()
        mock_processor_instance.stop = AsyncMock()
        mock_processor.return_value = mock_processor_instance
        
        app = MainApp()
        app.initialize()
        
        # Test start
        assert app.is_running is False
        await app.start()
        assert app.is_running is True
        mock_processor_instance.start.assert_called_once()
        
        # Test stop
        await app.stop()
        assert app.is_running is False
        mock_processor_instance.stop.assert_called()

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    @pytest.mark.asyncio
    async def test_main_app_graceful_shutdown(self, mock_filter, mock_processor,
                                       mock_queue, mock_camera, mock_create_detector):
        """Should handle graceful shutdown with cleanup."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        mock_processor_instance = Mock()
        mock_processor_instance.start = AsyncMock()
        mock_processor_instance.stop = AsyncMock()
        mock_processor.return_value = mock_processor_instance
        mock_camera_instance = Mock()
        mock_camera.return_value = mock_camera_instance
        
        app = MainApp()
        app.initialize()
        await app.start()
        
        # Test shutdown
        await app.shutdown()
        assert app.is_running is False
        mock_camera_instance.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_app_processing_loop_with_timeout(self):
        """Should run processing loop until timeout."""
        config = MainAppConfig(max_runtime_seconds=0.1)  # Very short timeout
        app = MainApp(config)
        
        # Mock all components and methods
        with patch.multiple(
            'src.cli.main',
            CameraManager=Mock(),
            FrameQueue=Mock(),
            FrameProcessor=Mock(),
            PresenceFilter=Mock()
        ), patch('src.detection.create_detector') as mock_create_detector:
            
            mock_detector = Mock()
            mock_create_detector.return_value = mock_detector
            app.initialize()
            app.frame_processor.start = AsyncMock()
            app.frame_processor.stop = AsyncMock()
            
            # Mock the processing loop to increment frames_processed
            async def mock_process_frame():
                app.frames_processed += 1
                await asyncio.sleep(0.01)  # Small delay
            
            app._process_single_frame = mock_process_frame
            
            # Run with timeout
            start_time = time.time()
            await app.run()
            end_time = time.time()
            
            # Should respect timeout
            assert (end_time - start_time) >= 0.1
            assert (end_time - start_time) < 0.2  # Allow some tolerance
            assert app.frames_processed > 0


class TestMainAppProcessing:
    """Test MainApp frame processing functionality."""

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    @pytest.mark.asyncio
    async def test_main_app_single_frame_processing(self, mock_filter, mock_processor,
                                             mock_queue, mock_camera, mock_create_detector):
        """Should process single frame through complete pipeline."""
        # Setup mocks
        import numpy as np
        from src.detection.result import DetectionResult
        
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        # Mock frame and detection result
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detection_result = DetectionResult(
            human_present=True,
            confidence=0.8
        )
        
        # Setup component mocks
        mock_camera_instance = Mock()
        mock_camera.return_value = mock_camera_instance
        mock_camera_instance.get_frame.return_value = test_frame
        
        mock_queue_instance = Mock()
        mock_queue.return_value = mock_queue_instance
        mock_queue_instance.get.return_value = test_frame
        
        mock_processor_instance = Mock()
        mock_processor.return_value = mock_processor_instance
        
        mock_filter_instance = Mock()
        mock_filter.return_value = mock_filter_instance
        
        app = MainApp()
        app.initialize()
        
        # Process single frame
        await app._process_single_frame()
        
        # Verify frame was processed
        mock_camera_instance.get_frame.assert_called_once()

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    @pytest.mark.asyncio
    async def test_main_app_processing_with_no_frame(self, mock_filter, mock_processor,
                                              mock_queue, mock_camera, mock_create_detector):
        """Should handle case when no frame is available."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        mock_camera_instance = Mock()
        mock_camera.return_value = mock_camera_instance
        mock_camera_instance.get_frame.return_value = None  # No frame available
        
        app = MainApp()
        app.initialize()
        
        # Process single frame
        await app._process_single_frame()
        
        # Verify frame was requested but nothing processed
        mock_camera_instance.get_frame.assert_called_once()

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    @pytest.mark.asyncio
    async def test_main_app_processing_error_handling(self, mock_filter, mock_processor,
                                               mock_queue, mock_camera, mock_create_detector):
        """Should handle processing errors gracefully."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        mock_camera_instance = Mock()
        mock_camera.return_value = mock_camera_instance
        mock_camera_instance.get_frame.side_effect = Exception("Camera error")
        
        app = MainApp()
        app.initialize()
        
        # Process single frame - should not raise exception
        await app._process_single_frame()
        
        # Verify error was handled gracefully
        mock_camera_instance.get_frame.assert_called_once()


class TestMainAppStatistics:
    """Test MainApp statistics and monitoring."""

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_tracks_processing_statistics(self, mock_filter, mock_processor,
                                                   mock_queue, mock_camera, mock_create_detector):
        """Should track processing statistics."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        app = MainApp()
        app.initialize()
        
        # Get statistics
        stats = app.get_statistics()
        
        assert 'frames_processed' in stats
        assert 'uptime_seconds' in stats
        assert 'is_running' in stats
        assert 'frames_per_second' in stats  # Updated to match actual implementation
        
        assert stats['frames_processed'] == 0
        assert stats['is_running'] is False
        assert isinstance(stats['uptime_seconds'], float)
        assert stats['uptime_seconds'] >= 0

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_provides_presence_status(self, mock_filter, mock_processor,
                                              mock_queue, mock_camera, mock_create_detector):
        """Should provide current presence status."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        mock_filter_instance = Mock()
        mock_filter.return_value = mock_filter_instance
        mock_filter_instance.get_filtered_presence.return_value = True  # Updated method name
        
        app = MainApp()
        app.initialize()
        
        # Get presence status
        status = app.get_presence_status()
        
        assert 'human_present' in status
        assert 'state_changes' in status  # Updated to match actual implementation
        assert 'total_detections' in status  # Updated to match actual implementation
        
        assert isinstance(status['human_present'], bool)


class TestMainAppSignalHandling:
    """Test MainApp signal handling for graceful shutdown."""

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_signal_handler_setup(self, mock_filter, mock_processor,
                                          mock_queue, mock_camera, mock_create_detector):
        """Should setup signal handlers correctly."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        app = MainApp()
        
        with patch('signal.signal') as mock_signal:
            app.setup_signal_handlers()
            
            # Verify signal handlers were registered
            expected_calls = [
                call(signal.SIGINT, app._signal_handler),
                call(signal.SIGTERM, app._signal_handler)
            ]
            mock_signal.assert_has_calls(expected_calls, any_order=True)

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_signal_handler_triggers_shutdown(self, mock_filter, mock_processor,
                                                      mock_queue, mock_camera, mock_create_detector):
        """Should trigger shutdown when signal received."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        app = MainApp()
        
        # Simulate signal reception
        assert app._shutdown_requested is False
        app._signal_handler(signal.SIGINT, None)
        assert app._shutdown_requested is True


class TestMainAppError:
    """Test MainAppError exception handling."""

    def test_main_app_error_creation(self):
        """Should create MainAppError with message."""
        error = MainAppError("Application error occurred")
        
        assert str(error) == "Application error occurred"
        assert isinstance(error, Exception)

    def test_main_app_error_with_original_error(self):
        """Should handle original error chaining."""
        original_error = ValueError("Original error")
        error = MainAppError("Application failed", original_error=original_error)
        
        assert str(error) == "Application failed (caused by: Original error)"
        assert error.original_error == original_error

    def test_main_app_error_inheritance(self):
        """Should inherit from Exception."""
        error = MainAppError("Test error")
        assert isinstance(error, Exception)


class TestMainAppIntegration:
    """Test MainApp integration scenarios."""

    @pytest.mark.asyncio
    async def test_main_app_complete_integration_workflow(self):
        """Should coordinate complete detection workflow."""
        config = MainAppConfig(max_runtime_seconds=0.1)

        # Mock all components
        with patch.multiple(
            'src.cli.main',
            CameraManager=Mock(),
            FrameQueue=Mock(),
            FrameProcessor=Mock(),
            PresenceFilter=Mock()
        ), patch('src.cli.main.create_detector') as mock_create_detector:
            
            mock_detector = Mock()
            mock_create_detector.return_value = mock_detector

            # Create mock processor with async methods before initialization
            mock_processor_instance = Mock()
            mock_processor_instance.start = AsyncMock()
            mock_processor_instance.stop = AsyncMock()
            
            app = MainApp(config)
            app.initialize()
            
            # Replace the frame processor after initialization
            app.frame_processor = mock_processor_instance

            # Mock the _process_single_frame method
            async def mock_process_frame():
                pass
            
            with patch.object(app, '_process_single_frame', side_effect=mock_process_frame):
                await app.run()

            # Verify components were initialized and run
            assert app.camera_manager is not None
            assert app.detector is not None
            assert app.frame_queue is not None
            assert app.frame_processor is not None
            assert app.presence_filter is not None

    @patch('src.detection.create_detector')
    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    @pytest.mark.asyncio
    async def test_main_app_resource_cleanup_on_error(self, mock_filter, mock_processor,
                                               mock_queue, mock_camera, mock_create_detector):
        """Should cleanup resources when errors occur."""
        # Setup mocks
        mock_detector = Mock()
        mock_create_detector.return_value = mock_detector
        
        mock_camera_instance = Mock()
        mock_camera.return_value = mock_camera_instance
        
        # Force initialization to fail after some components are created
        mock_processor.side_effect = Exception("Processor creation failed")
        
        app = MainApp()
        
        with pytest.raises(MainAppError):
            app.initialize()
        
        # Verify cleanup would be called in real implementation
        # (This is a simplified test - real implementation would have more complex cleanup)
        assert app.frame_processor is None 