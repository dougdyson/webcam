"""
Tests for MainApp - Application lifecycle and coordination.

This module tests the main application coordinator that integrates
camera management, detection, processing, and filtering components.
"""

import asyncio
import signal
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
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
        assert config.detection_confidence_threshold == 0.5
        assert config.enable_logging is True
        assert config.log_level == 'INFO'
        assert config.enable_display is False
        assert config.max_runtime_seconds is None

    def test_main_app_config_with_custom_values(self):
        """Should create MainAppConfig with custom values."""
        config = MainAppConfig(
            camera_profile='high_quality',
            detection_confidence_threshold=0.7,
            enable_logging=False,
            log_level='DEBUG',
            enable_display=True,
            max_runtime_seconds=300.0
        )
        
        assert config.camera_profile == 'high_quality'
        assert config.detection_confidence_threshold == 0.7
        assert config.enable_logging is False
        assert config.log_level == 'DEBUG'
        assert config.enable_display is True
        assert config.max_runtime_seconds == 300.0

    def test_main_app_config_validation(self):
        """Should validate MainAppConfig parameters."""
        # Test invalid confidence threshold
        with pytest.raises(ValueError):
            MainAppConfig(detection_confidence_threshold=-0.1)
        
        with pytest.raises(ValueError):
            MainAppConfig(detection_confidence_threshold=1.1)
        
        # Test invalid log level
        with pytest.raises(ValueError):
            MainAppConfig(log_level='INVALID')
        
        # Test invalid runtime
        with pytest.raises(ValueError):
            MainAppConfig(max_runtime_seconds=-10.0)


class TestMainAppInitialization:
    """Test MainApp initialization and component setup."""

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_initialization_with_defaults(self, mock_filter, mock_processor, 
                                                  mock_queue, mock_detector, mock_camera):
        """Should initialize MainApp with default configuration."""
        config = MainAppConfig()
        app = MainApp(config)
        
        assert app.config == config
        assert app.camera_manager is None
        assert app.detector is None
        assert app.frame_queue is None
        assert app.frame_processor is None
        assert app.presence_filter is None
        assert app.is_running is False
        assert app.frames_processed == 0

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_initialization_with_custom_config(self, mock_filter, mock_processor,
                                                       mock_queue, mock_detector, mock_camera):
        """Should initialize MainApp with custom configuration."""
        config = MainAppConfig(
            camera_profile='high_quality',
            detection_confidence_threshold=0.8,
            log_level='DEBUG'
        )
        app = MainApp(config)
        
        assert app.config == config
        assert app.config.camera_profile == 'high_quality'
        assert app.config.detection_confidence_threshold == 0.8
        assert app.config.log_level == 'DEBUG'

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_component_initialization(self, mock_filter, mock_processor,
                                              mock_queue, mock_detector, mock_camera):
        """Should initialize all components during setup."""
        config = MainAppConfig()
        app = MainApp(config)
        
        # Initialize components
        app.initialize()
        
        # Should create all components
        mock_camera.assert_called_once()
        mock_detector.assert_called_once()
        mock_queue.assert_called_once()
        mock_processor.assert_called_once()
        mock_filter.assert_called_once()
        
        # Should assign components to app
        assert app.camera_manager is not None
        assert app.detector is not None
        assert app.frame_queue is not None
        assert app.frame_processor is not None
        assert app.presence_filter is not None

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

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_start_stop_lifecycle(self, mock_filter, mock_processor,
                                          mock_queue, mock_detector, mock_camera):
        """Should handle start and stop lifecycle correctly."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock async methods
        app.frame_processor.start = AsyncMock()
        app.frame_processor.stop = AsyncMock()
        
        # Should not be running initially
        assert app.is_running is False
        
        # Start the app
        asyncio.run(app.start())
        assert app.is_running is True
        app.frame_processor.start.assert_called_once()
        
        # Stop the app
        asyncio.run(app.stop())
        assert app.is_running is False
        app.frame_processor.stop.assert_called_once()

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_graceful_shutdown(self, mock_filter, mock_processor,
                                       mock_queue, mock_detector, mock_camera):
        """Should handle graceful shutdown with cleanup."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock async methods properly
        app.frame_processor.start = AsyncMock()
        app.frame_processor.stop = AsyncMock()
        app.camera_manager.release = Mock()
        app.detector.cleanup = Mock()
        
        # Start then shutdown
        asyncio.run(app.start())
        asyncio.run(app.shutdown())
        
        # Should cleanup all components
        app.frame_processor.stop.assert_called()
        app.camera_manager.release.assert_called_once()
        app.detector.cleanup.assert_called_once()
        assert app.is_running is False

    @pytest.mark.asyncio
    async def test_main_app_processing_loop_with_timeout(self):
        """Should run processing loop until timeout."""
        config = MainAppConfig(max_runtime_seconds=0.1)  # Very short timeout
        app = MainApp(config)
        
        # Mock all components and methods
        with patch.multiple(
            'src.cli.main',
            CameraManager=Mock(),
            MediaPipeDetector=Mock(),
            FrameQueue=Mock(),
            FrameProcessor=Mock(),
            PresenceFilter=Mock()
        ):
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
    """Test MainApp frame processing coordination."""

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')  
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_single_frame_processing(self, mock_filter, mock_processor,
                                             mock_queue, mock_detector, mock_camera):
        """Should process single frame through complete pipeline."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock frame and detection result
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_detection = DetectionResult(human_present=True, confidence=0.8)
        
        # Setup mocks
        app.camera_manager.get_frame.return_value = mock_frame
        app.detector.detect.return_value = mock_detection
        app.presence_filter.get_filtered_presence.return_value = True
        
        # Process single frame
        asyncio.run(app._process_single_frame())
        
        # Should process through complete pipeline
        app.camera_manager.get_frame.assert_called_once()
        app.detector.detect.assert_called_once_with(mock_frame)
        app.presence_filter.add_result.assert_called_once_with(mock_detection)
        assert app.frames_processed == 1

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue') 
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_processing_with_no_frame(self, mock_filter, mock_processor,
                                              mock_queue, mock_detector, mock_camera):
        """Should handle cases where no frame is available."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock no frame available
        app.camera_manager.get_frame.return_value = None
        
        # Process frame
        asyncio.run(app._process_single_frame())
        
        # Should not call detector or filter
        app.detector.detect.assert_not_called()
        app.presence_filter.add_result.assert_not_called()
        assert app.frames_processed == 0

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_processing_error_handling(self, mock_filter, mock_processor,
                                               mock_queue, mock_detector, mock_camera):
        """Should handle processing errors gracefully."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock frame
        mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        app.camera_manager.get_frame.return_value = mock_frame
        
        # Mock detector error
        app.detector.detect.side_effect = Exception("Detection failed")
        
        # Should handle error gracefully
        asyncio.run(app._process_single_frame())
        
        # Should not call filter due to detection error
        app.presence_filter.add_result.assert_not_called()
        assert app.frames_processed == 0


class TestMainAppStatistics:
    """Test MainApp statistics and monitoring."""

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_tracks_processing_statistics(self, mock_filter, mock_processor,
                                                  mock_queue, mock_detector, mock_camera):
        """Should track frame processing statistics."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock presence filter to return actual values
        app.presence_filter.get_filtered_presence.return_value = False
        
        # Initial stats
        stats = app.get_statistics()
        assert stats['frames_processed'] == 0
        assert stats['current_presence'] is False
        assert 'uptime_seconds' in stats
        assert 'frames_per_second' in stats

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_provides_presence_status(self, mock_filter, mock_processor,
                                              mock_queue, mock_detector, mock_camera):
        """Should provide current presence detection status."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock presence filter
        app.presence_filter.get_filtered_presence.return_value = True
        app.presence_filter.get_state_change_count.return_value = 3
        app.presence_filter.get_detection_count.return_value = 50
        
        # Get presence status
        status = app.get_presence_status()
        
        assert status['human_present'] is True
        assert status['state_changes'] == 3
        assert status['total_detections'] == 50


class TestMainAppSignalHandling:
    """Test MainApp signal handling and graceful shutdown."""

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_signal_handler_setup(self, mock_filter, mock_processor,
                                          mock_queue, mock_detector, mock_camera):
        """Should setup signal handlers for graceful shutdown."""
        config = MainAppConfig()
        app = MainApp(config)
        
        with patch('signal.signal') as mock_signal:
            app.setup_signal_handlers()
            
            # Should register SIGINT and SIGTERM handlers
            expected_calls = [
                ((signal.SIGINT, app._signal_handler),),
                ((signal.SIGTERM, app._signal_handler),)
            ]
            
            mock_signal.assert_has_calls(expected_calls, any_order=True)

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_signal_handler_triggers_shutdown(self, mock_filter, mock_processor,
                                                      mock_queue, mock_detector, mock_camera):
        """Should trigger graceful shutdown on signal."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock shutdown method
        app.shutdown = AsyncMock()
        
        # Simulate signal
        app._signal_handler(signal.SIGINT, None)
        
        # Should set shutdown flag
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
    """Integration tests for MainApp with mocked components."""

    @pytest.mark.asyncio
    async def test_main_app_complete_integration_workflow(self):
        """Should coordinate complete detection workflow."""
        config = MainAppConfig(max_runtime_seconds=0.1)
        
        # Mock all components
        with patch.multiple(
            'src.cli.main',
            CameraManager=Mock(),
            MediaPipeDetector=Mock(),
            FrameQueue=Mock(),
            FrameProcessor=Mock(),
            PresenceFilter=Mock()
        ) as mocks:
            
            app = MainApp(config)
            app.initialize()
            
            # Setup processing pipeline mocks
            mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            mock_detection = DetectionResult(human_present=True, confidence=0.8)
            
            app.camera_manager.get_frame.return_value = mock_frame
            app.detector.detect.return_value = mock_detection
            app.presence_filter.get_filtered_presence.return_value = True
            
            # Mock async methods
            app.frame_processor.start = AsyncMock()
            app.frame_processor.stop = AsyncMock()
            
            # Run complete workflow
            await app.run()
            
            # Should have processed frames
            assert app.frames_processed > 0
            
            # Should have called components
            app.camera_manager.get_frame.assert_called()
            app.detector.detect.assert_called()
            app.presence_filter.add_result.assert_called()

    @patch('src.cli.main.CameraManager')
    @patch('src.cli.main.MediaPipeDetector')
    @patch('src.cli.main.FrameQueue')
    @patch('src.cli.main.FrameProcessor')
    @patch('src.cli.main.PresenceFilter')
    def test_main_app_resource_cleanup_on_error(self, mock_filter, mock_processor,
                                               mock_queue, mock_detector, mock_camera):
        """Should cleanup resources even when errors occur."""
        config = MainAppConfig()
        app = MainApp(config)
        app.initialize()
        
        # Mock cleanup methods
        app.frame_processor.stop = AsyncMock()
        app.camera_manager.release = Mock()
        app.detector.cleanup = Mock()
        
        # Mock error during processing
        app._process_single_frame = AsyncMock(side_effect=Exception("Processing error"))
        
        # Should cleanup even on error
        try:
            asyncio.run(app.run())
        except:
            pass
        
        # Cleanup should still be called
        asyncio.run(app.shutdown())
        app.frame_processor.stop.assert_called()
        app.camera_manager.release.assert_called()
        app.detector.cleanup.assert_called() 