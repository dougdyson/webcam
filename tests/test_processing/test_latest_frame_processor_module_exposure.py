"""
Test suite for Latest Frame Processor Module Exposure

This implements the missing piece - ensuring Latest Frame Processor is properly
exposed in the processing module's public API for production use.

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock
import numpy as np


class TestLatestFrameProcessorModuleExposure:
    """Test that Latest Frame Processor components are properly exposed in processing module."""
    
    def test_latest_frame_processor_importable_from_processing_module(self):
        """
        🔴 RED: Test that LatestFrameProcessor can be imported from processing module.
        
        The Latest Frame Processor should be accessible as a public API component.
        """
        # This should work but will fail because LatestFrameProcessor is not exposed
        from src.processing import LatestFrameProcessor
        
        # Should be able to create an instance
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        assert processor is not None
        assert hasattr(processor, 'start')
        assert hasattr(processor, 'stop')
        assert hasattr(processor, 'add_result_callback')
    
    def test_latest_frame_result_importable_from_processing_module(self):
        """
        🔴 RED: Test that LatestFrameResult can be imported from processing module.
        
        The result data structure should be accessible for type hints and usage.
        """
        # This should work but will fail because LatestFrameResult is not exposed
        from src.processing import LatestFrameResult
        
        # Should be able to create an instance
        result = LatestFrameResult(
            frame_id=1,
            human_present=True,
            confidence=0.85,
            processing_time=0.1,
            timestamp=1234567890.0,
            frame_age=0.05,
            frames_skipped=0
        )
        
        assert result is not None
        assert result.human_present is True
        assert result.confidence == 0.85
    
    def test_create_latest_frame_processor_factory_exposed(self):
        """
        🔴 RED: Test that create_latest_frame_processor factory function is exposed.
        
        The factory function should be accessible for easy processor creation.
        """
        # This should work but will fail because factory function is not exposed
        from src.processing import create_latest_frame_processor
        
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = create_latest_frame_processor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0,
            real_time_mode=True
        )
        
        assert processor is not None
        assert hasattr(processor, 'start')
        assert hasattr(processor, 'stop')
    
    def test_latest_frame_components_all_exposed(self):
        """
        🔴 RED: Test that all Latest Frame Processor components are exposed.
        
        All components should be importable from the processing module.
        """
        # Test that all expected components can be imported
        from src.processing import (
            LatestFrameProcessor,
            LatestFrameResult, 
            create_latest_frame_processor,
            FrameStatistics,
            PerformanceMonitor,
            CallbackManager,
            ConfigurationManager
        )
        
        # Verify they are the correct types
        assert LatestFrameProcessor is not None
        assert LatestFrameResult is not None
        assert callable(create_latest_frame_processor)
        assert FrameStatistics is not None
        assert PerformanceMonitor is not None
        assert CallbackManager is not None
        assert ConfigurationManager is not None


class TestLatestFrameProcessorProductionIntegration:
    """Test Latest Frame Processor integration for production use."""
    
    def test_latest_frame_processor_integration_with_service_layer(self):
        """
        🔴 RED: Test that Latest Frame Processor integrates with service layer.
        
        The processor should be usable in production service configurations.
        """
        from src.processing import create_latest_frame_processor
        
        # Mock service components
        mock_camera = Mock()
        mock_detector = Mock()
        mock_event_publisher = Mock()
        
        # Create processor for production use
        processor = create_latest_frame_processor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0,
            real_time_mode=True
        )
        
        # Should support service integration
        assert hasattr(processor, 'set_event_publisher')
        processor.set_event_publisher(mock_event_publisher)
        
        # Should support callback registration for service events
        service_callback = Mock()
        processor.add_result_callback(service_callback)
        
        # Should have all production-ready methods
        assert hasattr(processor, 'get_statistics')
        assert hasattr(processor, 'get_real_time_performance_metrics')
        assert hasattr(processor, 'update_configuration')
        assert hasattr(processor, 'save_configuration')
        assert hasattr(processor, 'load_configuration')
    
    @pytest.mark.asyncio
    async def test_latest_frame_processor_production_workflow(self):
        """
        🔴 RED: Test a complete production workflow with Latest Frame Processor.
        
        Simulate a real production usage pattern.
        """
        from src.processing import LatestFrameProcessor, LatestFrameResult
        
        # Mock production components
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Mock frame and detection result
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.85
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        # Create processor with production settings
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0,
            adaptive_fps=True,
            memory_monitoring=True
        )
        
        processor._async_detect = mock_async_detect
        
        # Track production results
        production_results = []
        
        def production_callback(result: LatestFrameResult):
            production_results.append(result)
        
        processor.add_result_callback(production_callback)
        
        # Run production workflow
        await processor.start()
        await asyncio.sleep(0.3)  # Process some frames
        await processor.stop()
        
        # Verify production results
        assert len(production_results) > 0
        result = production_results[0]
        assert isinstance(result, LatestFrameResult)
        assert result.human_present is True
        assert result.confidence == 0.85
        assert result.frame_age >= 0
        assert result.processing_time > 0 