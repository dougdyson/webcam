"""
Phase 7.1.1: End-to-End Integration Tests - Human Detection → Description Flow
RED PHASE: Write failing tests for complete pipeline integration

Tests the complete flow:
Camera → Detection → [Human Found] → DescriptionService → EventPublisher → HTTP API
"""

import pytest
import asyncio
import cv2
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

# Import the complete system components
from webcam_enhanced_service import EnhancedWebcamService
from src.utils.config import ConfigManager
from src.ollama.client import OllamaClient
from src.ollama.description_service import DescriptionService
from src.service.events import EventType


class TestEndToEndHumanDetectionToDescriptionFlow:
    """Test Phase 7.1.1: Complete human detection → description processing pipeline (RED PHASE)"""
    
    @pytest.fixture
    def sample_frame_with_human(self):
        """Create a sample frame that should trigger human detection."""
        # Create a simple test frame (we'll mock the detection results)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[100:300, 200:400] = [100, 150, 200]  # Add some content
        return frame
    
    @pytest.fixture
    def sample_frame_without_human(self):
        """Create a sample frame that should NOT trigger human detection."""
        # Create an empty test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        return frame
    
    @pytest.fixture
    def mock_ollama_response(self):
        """Mock successful Ollama response for description generation."""
        return {
            "message": {
                "content": "A person is sitting at a desk, typing on a laptop computer. The person appears to be working in a well-lit office environment."
            }
        }
    
    def test_end_to_end_human_detected_triggers_description_processing(self, sample_frame_with_human, mock_ollama_response):
        """
        RED: Test complete flow when human is detected
        
        Flow: Frame → Human Detection (YES) → Description Processing → Event Publishing
        This test should fail because end-to-end integration is not implemented.
        """
        with patch('webcam_enhanced_service.CameraManager') as mock_camera_class:
            with patch('webcam_enhanced_service.create_detector') as mock_detector_class:
                with patch('webcam_enhanced_service.GestureDetector') as mock_gesture_class:
                    with patch('webcam_enhanced_service.ConfigManager') as mock_config_class:
                        with patch('webcam_enhanced_service.OllamaClient') as mock_ollama_client_class:
                            with patch('webcam_enhanced_service.DescriptionService') as mock_description_service_class:
                                
                                # Setup enhanced service
                                enhanced_service = EnhancedWebcamService()
                                
                                # Mock camera to return our test frame
                                mock_camera = mock_camera_class.return_value
                                mock_camera.get_frame.return_value = sample_frame_with_human
                                mock_camera.is_opened.return_value = True
                                
                                # Mock detector to return human detection
                                mock_detector = mock_detector_class.return_value
                                mock_detection_result = MagicMock()
                                mock_detection_result.human_present = True
                                mock_detection_result.confidence = 0.85
                                mock_detection_result.landmarks = {"pose": [], "face": []}
                                mock_detector.detect.return_value = mock_detection_result
                                
                                # Mock configuration
                                mock_config = mock_config_class.return_value
                                mock_config.load_ollama_config.return_value = {
                                    'client': {
                                        'model': 'gemma3:4b-it-q4_K_M',
                                        'base_url': 'http://localhost:11434',
                                        'timeout_seconds': 30,
                                        'max_retries': 2
                                    }
                                }
                                
                                # Mock Ollama client
                                mock_ollama_client = mock_ollama_client_class.return_value
                                mock_ollama_client.is_available.return_value = True
                                
                                # Mock description service
                                mock_description_service = mock_description_service_class.return_value
                                mock_description_result = MagicMock()
                                mock_description_result.success = True
                                mock_description_result.description = "A person is sitting at a desk, typing on a laptop computer."
                                mock_description_result.confidence = 0.92
                                mock_description_result.processing_time = 15.3
                                mock_description_result.from_cache = False
                                mock_description_service.describe_snapshot.return_value = mock_description_result
                                
                                # Initialize the enhanced service
                                enhanced_service.initialize()
                                
                                # Simulate detection loop processing the frame
                                enhanced_service._process_single_frame(sample_frame_with_human)
                                
                                # Verify the complete flow occurred
                                # 1. Human detection was called
                                mock_detector.detect.assert_called_once_with(sample_frame_with_human)
                                
                                # 2. Description processing was triggered (because human detected with confidence > 0.6)
                                mock_description_service.describe_snapshot.assert_called_once()
                                call_args = mock_description_service.describe_snapshot.call_args
                                assert len(call_args[0]) == 1, "Should be called with one argument"
                                snapshot_arg = call_args[0][0]
                                
                                # Verify it's a Snapshot object with correct frame
                                from src.ollama.snapshot_buffer import Snapshot
                                assert isinstance(snapshot_arg, Snapshot), f"Expected Snapshot object, got {type(snapshot_arg)}"
                                # Note: Can't directly compare numpy arrays, but verify it's the right structure
                                assert hasattr(snapshot_arg, 'frame'), "Snapshot should have frame attribute"
                                assert hasattr(snapshot_arg, 'metadata'), "Snapshot should have metadata attribute"
                                
                                # 3. Events were published for the description result
                                # This should verify that description events flow through the system
                                assert len(enhanced_service.event_publisher.subscribers) > 0 or \
                                       len(enhanced_service.event_publisher.async_subscribers) > 0, \
                                       "Should have event subscribers for description events"
    
    def test_end_to_end_no_human_skips_description_processing(self, sample_frame_without_human):
        """
        RED: Test that NO description processing occurs when no human detected
        
        Flow: Frame → Human Detection (NO) → Skip Description → No Events
        This test should fail because conditional processing logic is not implemented.
        """
        with patch('webcam_enhanced_service.CameraManager') as mock_camera_class:
            with patch('webcam_enhanced_service.create_detector') as mock_detector_class:
                with patch('webcam_enhanced_service.GestureDetector') as mock_gesture_class:
                    with patch('webcam_enhanced_service.ConfigManager') as mock_config_class:
                        with patch('webcam_enhanced_service.OllamaClient') as mock_ollama_client_class:
                            with patch('webcam_enhanced_service.DescriptionService') as mock_description_service_class:
                                
                                # Setup enhanced service
                                enhanced_service = EnhancedWebcamService()
                                
                                # Mock camera to return empty frame
                                mock_camera = mock_camera_class.return_value
                                mock_camera.get_frame.return_value = sample_frame_without_human
                                mock_camera.is_opened.return_value = True
                                
                                # Mock detector to return NO human detection
                                mock_detector = mock_detector_class.return_value
                                mock_detection_result = MagicMock()
                                mock_detection_result.human_present = False
                                mock_detection_result.confidence = 0.15
                                mock_detection_result.landmarks = {}
                                mock_detector.detect.return_value = mock_detection_result
                                
                                # Mock configuration
                                mock_config = mock_config_class.return_value
                                mock_config.load_ollama_config.return_value = {
                                    'client': {
                                        'model': 'gemma3:4b-it-q4_K_M',
                                        'base_url': 'http://localhost:11434',
                                        'timeout_seconds': 30,
                                        'max_retries': 2
                                    }
                                }
                                
                                # Mock description service
                                mock_description_service = mock_description_service_class.return_value
                                
                                # Initialize the enhanced service
                                enhanced_service.initialize()
                                
                                # Simulate detection loop processing the frame
                                enhanced_service._process_single_frame(sample_frame_without_human)
                                
                                # Verify the flow
                                # 1. Human detection was called
                                mock_detector.detect.assert_called_once_with(sample_frame_without_human)
                                
                                # 2. Description processing was NOT triggered (because no human detected)
                                mock_description_service.describe_snapshot.assert_not_called()
                                
                                # 3. No description events should be published
                                # This verifies conditional processing works correctly
    
    def test_end_to_end_low_confidence_human_skips_description_processing(self, sample_frame_with_human):
        """
        RED: Test that low confidence human detection skips description processing
        
        Flow: Frame → Human Detection (YES, low confidence) → Skip Description
        This test should fail because confidence threshold logic is not implemented.
        """
        with patch('webcam_enhanced_service.CameraManager') as mock_camera_class:
            with patch('webcam_enhanced_service.create_detector') as mock_detector_class:
                with patch('webcam_enhanced_service.GestureDetector') as mock_gesture_class:
                    with patch('webcam_enhanced_service.ConfigManager') as mock_config_class:
                        with patch('webcam_enhanced_service.OllamaClient') as mock_ollama_client_class:
                            with patch('webcam_enhanced_service.DescriptionService') as mock_description_service_class:
                                
                                # Setup enhanced service
                                enhanced_service = EnhancedWebcamService()
                                
                                # Mock camera to return test frame
                                mock_camera = mock_camera_class.return_value
                                mock_camera.get_frame.return_value = sample_frame_with_human
                                mock_camera.is_opened.return_value = True
                                
                                # Mock detector to return LOW confidence human detection
                                mock_detector = mock_detector_class.return_value
                                mock_detection_result = MagicMock()
                                mock_detection_result.human_present = True
                                mock_detection_result.confidence = 0.45  # Below 0.6 threshold
                                mock_detection_result.landmarks = {"pose": [], "face": []}
                                mock_detector.detect.return_value = mock_detection_result
                                
                                # Mock configuration
                                mock_config = mock_config_class.return_value
                                mock_config.load_ollama_config.return_value = {
                                    'client': {
                                        'model': 'gemma3:4b-it-q4_K_M',
                                        'base_url': 'http://localhost:11434',
                                        'timeout_seconds': 30,
                                        'max_retries': 2
                                    }
                                }
                                
                                # Mock description service
                                mock_description_service = mock_description_service_class.return_value
                                
                                # Initialize the enhanced service
                                enhanced_service.initialize()
                                
                                # Simulate detection loop processing the frame
                                enhanced_service._process_single_frame(sample_frame_with_human)
                                
                                # Verify the flow
                                # 1. Human detection was called
                                mock_detector.detect.assert_called_once_with(sample_frame_with_human)
                                
                                # 2. Description processing was NOT triggered (because confidence < 0.6)
                                mock_description_service.describe_snapshot.assert_not_called()
                                
 