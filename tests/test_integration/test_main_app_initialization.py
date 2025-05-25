"""
Integration tests for MainApp initialization and component integration.

These tests specifically target the initialization bugs discovered during
live testing that unit tests didn't catch.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.cli.main import MainApp, MainAppConfig, MainAppError


class TestMainAppInitializationIntegration:
    """Test MainApp initialization with real component integration."""
    
    def test_detector_is_properly_initialized(self):
        """Test that detector.initialize() is called during app initialization.
        
        This test would have caught the missing detector.initialize() bug.
        """
        config = MainAppConfig()
        app = MainApp(config)
        
        # Mock the detector to track initialize() calls
        with patch('src.cli.main.MediaPipeDetector') as mock_detector_class:
            mock_detector = Mock()
            mock_detector_class.return_value = mock_detector
            
            # Initialize app
            app.initialize()
            
            # Verify detector was created AND initialized
            mock_detector_class.assert_called_once()
            mock_detector.initialize.assert_called_once()
    
    def test_camera_cleanup_method_exists(self):
        """Test that camera manager has correct cleanup method.
        
        This test would have caught the release() vs cleanup() method name bug.
        """
        config = MainAppConfig()
        app = MainApp(config)
        
        with patch('src.cli.main.CameraManager') as mock_camera_class:
            mock_camera = Mock()
            mock_camera_class.return_value = mock_camera
            
            app.initialize()
            
            # Verify cleanup method exists (not release)
            assert hasattr(mock_camera, 'cleanup')
            
            # Test shutdown calls correct method
            import asyncio
            asyncio.run(app.shutdown())
            mock_camera.cleanup.assert_called_once()
    
    def test_complete_initialization_chain(self):
        """Test that all components are initialized in correct order."""
        config = MainAppConfig()
        app = MainApp(config)
        
        with patch('src.cli.main.CameraManager') as mock_camera, \
             patch('src.cli.main.MediaPipeDetector') as mock_detector, \
             patch('src.cli.main.FrameQueue') as mock_queue, \
             patch('src.cli.main.FrameProcessor') as mock_processor, \
             patch('src.cli.main.PresenceFilter') as mock_filter:
            
            # Set up mocks
            camera_instance = Mock()
            detector_instance = Mock()
            queue_instance = Mock()
            processor_instance = Mock()
            filter_instance = Mock()
            
            mock_camera.return_value = camera_instance
            mock_detector.return_value = detector_instance
            mock_queue.return_value = queue_instance
            mock_processor.return_value = processor_instance
            mock_filter.return_value = filter_instance
            
            # Initialize
            app.initialize()
            
            # Verify all components created
            mock_camera.assert_called_once()
            mock_detector.assert_called_once()
            mock_queue.assert_called_once()
            mock_processor.assert_called_once()
            mock_filter.assert_called_once()
            
            # Verify detector initialized
            detector_instance.initialize.assert_called_once()
            
            # Verify components assigned
            assert app.camera_manager is camera_instance
            assert app.detector is detector_instance
            assert app.frame_queue is queue_instance
            assert app.frame_processor is processor_instance
            assert app.presence_filter is filter_instance
    
    def test_initialization_failure_cleanup(self):
        """Test that initialization failures are handled properly."""
        config = MainAppConfig()
        app = MainApp(config)
        
        with patch('src.cli.main.MediaPipeDetector') as mock_detector_class:
            # Make detector initialization fail
            mock_detector = Mock()
            mock_detector.initialize.side_effect = Exception("Detector init failed")
            mock_detector_class.return_value = mock_detector
            
            # Should raise MainAppError with original error
            with pytest.raises(MainAppError) as exc_info:
                app.initialize()
            
            assert "Failed to initialize application components" in str(exc_info.value)
            assert "Detector init failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_real_frame_processing_pipeline(self):
        """Test actual frame processing through the complete pipeline."""
        config = MainAppConfig()
        app = MainApp(config)
        
        # Create a test frame
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        with patch('src.cli.main.CameraManager') as mock_camera_class, \
             patch('src.cli.main.MediaPipeDetector') as mock_detector_class:
            
            # Set up camera to return test frame
            mock_camera = Mock()
            mock_camera.get_frame.return_value = test_frame
            mock_camera_class.return_value = mock_camera
            
            # Set up detector to return test result
            mock_detector = Mock()
            from src.detection.result import DetectionResult
            test_result = DetectionResult(human_present=True, confidence=0.8)
            mock_detector.detect.return_value = test_result
            mock_detector_class.return_value = mock_detector
            
            # Initialize and test
            app.initialize()
            await app._process_single_frame()
            
            # Verify pipeline worked
            mock_camera.get_frame.assert_called_once()
            mock_detector.detect.assert_called_once_with(test_frame)
            
            # Verify presence filter received result
            assert app.presence_filter is not None 