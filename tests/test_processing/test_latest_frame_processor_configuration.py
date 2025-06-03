"""
Test suite for LatestFrameProcessor - Phase 3.3 Dynamic Configuration & Hot-Swapping

This implements Phase 3.3 of the Latest Frame Processing TDD plan:
- Dynamic configuration updates without restart tests
- Component hot-swapping (detector/camera) tests  
- Configuration validation and rollback tests
- Configuration persistence and versioning tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
import threading
import tempfile
import os
import yaml
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np
from datetime import datetime, timedelta

from src.processing.latest_frame_processor_refactored import (
    LatestFrameProcessor,
    LatestFrameResult,
    create_latest_frame_processor
)


class TestDynamicConfigurationUpdates:
    """Phase 3.3: Dynamic configuration updates without service restart."""
    
    @pytest.mark.asyncio
    async def test_dynamic_fps_update_while_running(self):
        """
        🔴 RED: Test dynamic FPS updates while processor is running.
        
        Should be able to change target FPS without stopping the processor.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.87
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        # Create processor with initial FPS
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track configuration changes
        config_changes = []
        
        def config_change_callback(old_config, new_config, change_reason):
            config_changes.append({
                'old_fps': old_config.get('target_fps'),
                'new_fps': new_config.get('target_fps'),
                'reason': change_reason,
                'timestamp': time.time()
            })
        
        # This should work but will fail because dynamic configuration doesn't exist yet
        assert hasattr(processor, 'add_configuration_change_callback'), "Processor should support configuration change callbacks"
        processor.add_configuration_change_callback(config_change_callback)
        
        # Start processor
        await processor.start()
        await asyncio.sleep(0.3)  # Let it run briefly
        
        # Dynamic configuration update
        assert hasattr(processor, 'update_configuration_dynamic'), "Processor should support dynamic configuration updates"
        
        success = await processor.update_configuration_dynamic({
            'target_fps': 10.0,
            'processing_timeout': 2.0
        })
        
        assert success, "Dynamic configuration update should succeed"
        
        await asyncio.sleep(0.3)  # Let it run with new config
        await processor.stop()
        
        # Should have tracked configuration changes
        assert len(config_changes) >= 1, "Should track configuration changes"
        
        change = config_changes[0]
        assert change['old_fps'] == 5.0, "Should track old FPS"
        assert change['new_fps'] == 10.0, "Should track new FPS"
        assert change['reason'] == 'dynamic_update', "Should track update reason"
        
        # Verify processor is using new configuration
        assert processor.target_fps == 10.0, "Processor should use new FPS"
        assert processor.processing_timeout == 2.0, "Processor should use new timeout"
    
    @pytest.mark.asyncio
    async def test_dynamic_callback_registration_while_running(self):
        """
        🔴 RED: Test dynamic callback registration/removal while running.
        
        Should be able to add/remove callbacks without stopping processor.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.91
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track callback invocations
        callback1_calls = []
        callback2_calls = []
        
        def callback1(result):
            callback1_calls.append(result.frame_id)
        
        def callback2(result):
            callback2_calls.append(result.frame_id)
        
        # Start processor
        await processor.start()
        await asyncio.sleep(0.15)  # Initial processing without callbacks
        
        # Add callback dynamically
        assert hasattr(processor, 'add_result_callback_dynamic'), "Processor should support dynamic callback addition"
        success = await processor.add_result_callback_dynamic(callback1)
        assert success, "Dynamic callback addition should succeed"
        
        await asyncio.sleep(0.25)  # Process with callback1 (longer period)
        
        # Add second callback
        success = await processor.add_result_callback_dynamic(callback2)
        assert success, "Second dynamic callback addition should succeed"
        
        await asyncio.sleep(0.25)  # Process with both callbacks (same period)
        
        # Remove first callback dynamically
        assert hasattr(processor, 'remove_result_callback_dynamic'), "Processor should support dynamic callback removal"
        success = await processor.remove_result_callback_dynamic(callback1)
        assert success, "Dynamic callback removal should succeed"
        
        await asyncio.sleep(0.4)  # Process with only callback2 (longest period)
        await processor.stop()
        
        # Verify callback behavior
        assert len(callback1_calls) >= 2, "Callback1 should be called while registered"
        assert len(callback2_calls) >= 4, "Callback2 should be called longer (not removed)"
        
        # Verify callback1 was removed (callback2 should have significantly more calls)
        # Since callback2 is active for 0.65s (0.25 + 0.4) vs callback1 only for 0.5s (0.25 + 0.25)
        # And callback2 has the extra 0.4s period where callback1 is not called
        assert len(callback2_calls) >= len(callback1_calls) + 1, "Callback2 should have more calls after callback1 removal"
    
    @pytest.mark.asyncio
    async def test_real_time_configuration_validation_and_rollback(self):
        """
        🔴 RED: Test real-time configuration validation with automatic rollback.
        
        Invalid configurations should be rejected and rolled back automatically.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.84
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=6.0,
            processing_timeout=3.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track validation events
        validation_events = []
        
        def validation_callback(event_data):
            validation_events.append(event_data)
        
        # This should work but will fail because validation doesn't exist yet
        assert hasattr(processor, 'add_configuration_validation_callback'), "Processor should support validation callbacks"
        processor.add_configuration_validation_callback(validation_callback)
        
        await processor.start()
        await asyncio.sleep(0.2)
        
        # Store original configuration
        original_fps = processor.target_fps
        original_timeout = processor.processing_timeout
        
        # Try invalid configuration (negative FPS)
        assert hasattr(processor, 'update_configuration_with_validation'), "Processor should support validated configuration updates"
        
        result = await processor.update_configuration_with_validation({
            'target_fps': -5.0,  # Invalid: negative FPS
            'processing_timeout': 2.0
        })
        
        assert not result['success'], "Invalid configuration should be rejected"
        assert 'validation_errors' in result, "Should provide validation errors"
        assert len(result['validation_errors']) >= 1, "Should have validation errors for negative FPS"
        
        # Try another invalid configuration (zero timeout)
        result = await processor.update_configuration_with_validation({
            'target_fps': 8.0,
            'processing_timeout': 0.0  # Invalid: zero timeout
        })
        
        assert not result['success'], "Invalid timeout should be rejected"
        
        # Try valid configuration
        result = await processor.update_configuration_with_validation({
            'target_fps': 12.0,
            'processing_timeout': 4.0
        })
        
        assert result['success'], "Valid configuration should be accepted"
        assert 'rollback_point' in result, "Should provide rollback point"
        
        await asyncio.sleep(0.2)
        await processor.stop()
        
        # Verify configuration state
        assert processor.target_fps == 12.0, "Valid FPS update should be applied"
        assert processor.processing_timeout == 4.0, "Valid timeout update should be applied"
        
        # Verify validation events
        assert len(validation_events) >= 2, "Should track validation events"
        
        failed_validations = [e for e in validation_events if not e['validation_success']]
        assert len(failed_validations) >= 2, "Should track failed validations"


class TestComponentHotSwapping:
    """Phase 3.3: Hot-swapping of components (detector, camera) while running."""
    
    @pytest.mark.asyncio
    async def test_detector_hot_swap_without_interruption(self):
        """
        🔴 RED: Test detector hot-swapping without interrupting processing.
        
        Should seamlessly switch to new detector while maintaining processing.
        """
        # Setup initial detector
        mock_camera = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Original detector
        mock_detector1 = Mock()
        mock_result1 = Mock()
        mock_result1.human_present = True
        mock_result1.confidence = 0.85
        
        # New detector for hot swap
        mock_detector2 = Mock()
        mock_result2 = Mock()
        mock_result2.human_present = False
        mock_result2.confidence = 0.95
        
        def detector1_detect(frame):
            return mock_result1
        
        def detector2_detect(frame):
            return mock_result2
        
        mock_detector1.detect = detector1_detect
        mock_detector2.detect = detector2_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector1,
            target_fps=10.0
        )
        
        # Create async detect function for the processor
        current_detector = [mock_detector1]  # Use list to allow modification
        
        async def mock_async_detect(frame):
            # Call the current detector's detect method
            return current_detector[0].detect(frame)
        
        processor._async_detect = mock_async_detect
        
        # Override hot swap to update the current detector reference
        original_hot_swap = processor.hot_swap_detector
        
        async def updated_hot_swap_detector(*args, **kwargs):
            result = await original_hot_swap(*args, **kwargs)
            if result.get('success', False):
                current_detector[0] = processor.detector  # Update current detector reference
            return result
        
        processor.hot_swap_detector = updated_hot_swap_detector
        
        # Track processing results
        detection_results = []
        
        def result_callback(result):
            detection_results.append({
                'confidence': result.confidence,
                'human_present': result.human_present,
                'frame_id': result.frame_id
            })
        
        processor.add_result_callback(result_callback)
        
        # Track hot swap events
        swap_events = []
        
        def swap_callback(event_data):
            swap_events.append(event_data)
        
        # This should work but will fail because hot swapping doesn't exist yet
        assert hasattr(processor, 'add_component_swap_callback'), "Processor should support component swap callbacks"
        processor.add_component_swap_callback(swap_callback)
        
        await processor.start()
        await asyncio.sleep(0.3)  # Process with original detector
        
        # Perform hot swap
        assert hasattr(processor, 'hot_swap_detector'), "Processor should support detector hot swapping"
        
        swap_result = await processor.hot_swap_detector(
            new_detector=mock_detector2,
            swap_reason="performance_upgrade",
            initialize_new=True,
            cleanup_old=True
        )
        
        assert swap_result['success'], "Hot swap should succeed"
        assert 'swap_duration_ms' in swap_result, "Should track swap duration"
        assert swap_result['swap_duration_ms'] < 100, "Hot swap should be fast (< 100ms)"
        
        await asyncio.sleep(0.3)  # Process with new detector
        await processor.stop()
        
        # Verify detector swap occurred
        assert len(detection_results) >= 4, "Should have processed frames with both detectors"
        assert len(swap_events) >= 1, "Should track swap events"
        
        swap_event = swap_events[0]
        assert swap_event['component_type'] == 'detector', "Should identify component type"
        assert swap_event['swap_reason'] == 'performance_upgrade', "Should track swap reason"
        assert 'old_detector_id' in swap_event, "Should track old detector"
        assert 'new_detector_id' in swap_event, "Should track new detector"
        
        # Verify results from both detectors
        results_with_detector1 = [r for r in detection_results if r['confidence'] == 0.85]
        results_with_detector2 = [r for r in detection_results if r['confidence'] == 0.95]
        
        assert len(results_with_detector1) >= 1, "Should have results from original detector"
        assert len(results_with_detector2) >= 1, "Should have results from new detector"
    
    @pytest.mark.asyncio
    async def test_camera_hot_swap_with_frame_continuity(self):
        """
        🔴 RED: Test camera hot-swapping while maintaining frame processing continuity.
        
        Should switch camera sources without losing frames or interrupting detection.
        """
        # Setup cameras
        mock_detector = Mock()
        
        # Original camera
        mock_camera1 = Mock()
        camera1_frame = np.random.randint(100, 150, (480, 640, 3), dtype=np.uint8)  # Darker frames
        mock_camera1.get_frame.return_value = camera1_frame
        
        # New camera for hot swap
        mock_camera2 = Mock()
        camera2_frame = np.random.randint(200, 255, (480, 640, 3), dtype=np.uint8)  # Brighter frames
        mock_camera2.get_frame.return_value = camera2_frame
        
        # Detector responds to different frame brightness
        def mock_detect(frame):
            frame_mean = np.mean(frame)
            result = Mock()
            if frame_mean < 175:  # Darker frames (camera1)
                result.confidence = 0.70
                result.human_present = True
            else:  # Brighter frames (camera2)
                result.confidence = 0.90
                result.human_present = True
            return result
        
        mock_detector.detect = mock_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera1,
            detector=mock_detector,
            target_fps=12.0
        )
        
        # Add async detect function for the processor
        async def mock_async_detect(frame):
            return mock_detector.detect(frame)
        
        processor._async_detect = mock_async_detect
        
        # Track camera swap events
        camera_swap_events = []
        frame_continuity_data = []
        
        def camera_swap_callback(event_data):
            camera_swap_events.append(event_data)
        
        def frame_callback(result):
            frame_continuity_data.append({
                'frame_id': result.frame_id,
                'confidence': result.confidence,
                'timestamp': result.timestamp
            })
        
        processor.add_result_callback(frame_callback)
        
        # This should work but will fail because camera hot swapping doesn't exist yet
        assert hasattr(processor, 'add_camera_swap_callback'), "Processor should support camera swap callbacks"
        processor.add_camera_swap_callback(camera_swap_callback)
        
        await processor.start()
        await asyncio.sleep(0.3)  # Process with original camera
        
        # Hot swap camera
        assert hasattr(processor, 'hot_swap_camera'), "Processor should support camera hot swapping"
        
        swap_result = await processor.hot_swap_camera(
            new_camera=mock_camera2,
            swap_reason="camera_upgrade",
            validate_new_camera=True,
            frame_continuity_check=True
        )
        
        assert swap_result['success'], "Camera hot swap should succeed"
        assert 'frame_gap_ms' in swap_result, "Should track frame gap during swap"
        assert swap_result['frame_gap_ms'] < 200, "Frame gap should be minimal (< 200ms)"
        
        await asyncio.sleep(0.3)  # Process with new camera
        await processor.stop()
        
        # Verify camera swap
        assert len(camera_swap_events) >= 1, "Should track camera swap events"
        assert len(frame_continuity_data) >= 4, "Should maintain frame processing continuity"
        
        # Verify different cameras produced different confidence levels
        low_confidence_frames = [f for f in frame_continuity_data if f['confidence'] == 0.70]
        high_confidence_frames = [f for f in frame_continuity_data if f['confidence'] == 0.90]
        
        assert len(low_confidence_frames) >= 1, "Should have frames from original camera"
        assert len(high_confidence_frames) >= 1, "Should have frames from new camera"
        
        # Verify frame ID continuity (no gaps)
        frame_ids = [f['frame_id'] for f in frame_continuity_data]
        assert frame_ids == sorted(frame_ids), "Frame IDs should be sequential"
        
        camera_swap = camera_swap_events[0]
        assert camera_swap['component_type'] == 'camera', "Should identify component type"
        assert 'frame_continuity_maintained' in camera_swap, "Should track frame continuity"
    
    @pytest.mark.asyncio
    async def test_component_health_monitoring_during_swaps(self):
        """
        🔴 RED: Test component health monitoring during hot swaps.
        
        Should monitor component health and trigger automatic swaps when needed.
        """
        # Setup components
        mock_camera = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Detector that will become unhealthy
        mock_detector = Mock()
        detection_call_count = 0
        
        def failing_detect(frame):
            nonlocal detection_call_count
            detection_call_count += 1
            if detection_call_count > 3:  # Fail after 3 calls
                raise Exception("Detector failure simulation")
            
            result = Mock()
            result.human_present = True
            result.confidence = 0.88
            return result
        
        mock_detector.detect = failing_detect
        
        # Backup detector for automatic swap
        mock_backup_detector = Mock()
        backup_result = Mock()
        backup_result.human_present = True
        backup_result.confidence = 0.75
        
        def backup_detect(frame):
            return backup_result
        
        mock_backup_detector.detect = backup_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0
        )
        
        # Add async detect function for the processor
        async def mock_async_detect(frame):
            return mock_detector.detect(frame)
        
        processor._async_detect = mock_async_detect
        
        # Track health monitoring events
        health_events = []
        automatic_swap_events = []
        
        def health_callback(event_data):
            health_events.append(event_data)
        
        def auto_swap_callback(event_data):
            automatic_swap_events.append(event_data)
        
        # This should work but will fail because health monitoring doesn't exist yet
        assert hasattr(processor, 'enable_component_health_monitoring'), "Processor should support health monitoring"
        processor.enable_component_health_monitoring(
            health_check_interval_seconds=0.2,
            failure_threshold=3,
            auto_swap_enabled=True
        )
        
        processor.add_health_monitoring_callback(health_callback)
        processor.add_automatic_swap_callback(auto_swap_callback)
        
        # Register backup detector
        assert hasattr(processor, 'register_backup_detector'), "Processor should support backup detector registration"
        processor.register_backup_detector(mock_backup_detector, priority=1)
        
        await processor.start()
        await asyncio.sleep(0.6)  # Let it run and trigger failures
        await processor.stop()
        
        # Verify health monitoring detected issues
        assert len(health_events) >= 1, "Should track health monitoring events"
        
        health_event = health_events[-1]  # Latest health event
        assert health_event['component_type'] == 'detector', "Should monitor detector health"
        assert health_event['health_status'] in ['unhealthy', 'failed'], "Should detect detector failure"
        assert 'failure_count' in health_event, "Should track failure count"
        
        # Verify automatic swap occurred
        assert len(automatic_swap_events) >= 1, "Should trigger automatic swap"
        
        auto_swap = automatic_swap_events[0]
        assert auto_swap['trigger_reason'] == 'component_failure', "Should identify failure trigger"
        assert auto_swap['swap_type'] == 'automatic', "Should identify automatic swap"
        assert 'backup_component_id' in auto_swap, "Should track backup component"


class TestConfigurationValidation:
    """Phase 3.3: Configuration validation and error handling."""
    
    def test_comprehensive_configuration_validation_rules(self):
        """
        🔴 RED: Test comprehensive configuration validation with detailed rules.
        
        Should validate all configuration parameters with specific rules and constraints.
        """
        # Setup basic processor for validation testing
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        # This should work but will fail because validation doesn't exist yet
        assert hasattr(processor, 'validate_configuration'), "Processor should support configuration validation"
        
        # Test valid configuration
        valid_config = {
            'target_fps': 10.0,
            'processing_timeout': 3.0,
            'max_frame_age': 1.0,
            'adaptive_fps': True,
            'memory_monitoring': False
        }
        
        validation_result = processor.validate_configuration(valid_config)
        assert validation_result['is_valid'], "Valid configuration should pass validation"
        assert len(validation_result['errors']) == 0, "Valid configuration should have no errors"
        assert len(validation_result['warnings']) == 0, "Valid configuration should have no warnings"
        
        # Test invalid configurations
        invalid_configs = [
            {
                'target_fps': -5.0,  # Negative FPS
                'config_name': 'negative_fps'
            },
            {
                'target_fps': 0.0,  # Zero FPS
                'config_name': 'zero_fps'
            },
            {
                'processing_timeout': -1.0,  # Negative timeout
                'config_name': 'negative_timeout'
            },
            {
                'max_frame_age': 0.0,  # Zero frame age
                'config_name': 'zero_frame_age'
            },
            {
                'target_fps': 100.0,  # Extremely high FPS
                'config_name': 'extreme_fps'
            },
            {
                'processing_timeout': 0.01,  # Extremely low timeout
                'config_name': 'extreme_timeout'
            }
        ]
        
        for invalid_config in invalid_configs:
            config_name = invalid_config.pop('config_name')
            base_config = valid_config.copy()
            base_config.update(invalid_config)
            
            validation_result = processor.validate_configuration(base_config)
            assert not validation_result['is_valid'], f"Invalid configuration {config_name} should fail validation"
            assert len(validation_result['errors']) >= 1, f"Invalid configuration {config_name} should have errors"
            assert 'validation_details' in validation_result, f"Should provide validation details for {config_name}"
        
        # Test configuration with warnings (valid but suboptimal)
        warning_config = {
            'target_fps': 50.0,  # Very high FPS (warning, not error)
            'processing_timeout': 0.1,  # Very low timeout (warning)
            'max_frame_age': 5.0,  # Very high frame age (warning)
            'adaptive_fps': True,
            'memory_monitoring': True
        }
        
        validation_result = processor.validate_configuration(warning_config)
        assert validation_result['is_valid'], "Configuration with warnings should still be valid"
        assert len(validation_result['warnings']) >= 2, "Should generate warnings for suboptimal settings"
        assert len(validation_result['errors']) == 0, "Warnings should not be errors"
    
    def test_configuration_dependency_validation(self):
        """
        🔴 RED: Test validation of configuration dependencies and conflicts.
        
        Should detect invalid combinations and dependency conflicts.
        """
        # Setup processor
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        # This should work but will fail because dependency validation doesn't exist yet
        assert hasattr(processor, 'validate_configuration_dependencies'), "Processor should support dependency validation"
        
        # Test conflicting configuration (adaptive FPS with very low FPS)
        conflicting_config = {
            'target_fps': 1.0,  # Very low FPS
            'adaptive_fps': True,  # Adaptive FPS enabled
            'processing_timeout': 0.5  # Short timeout
        }
        
        dependency_result = processor.validate_configuration_dependencies(conflicting_config)
        assert not dependency_result['dependencies_valid'], "Conflicting configuration should fail dependency validation"
        assert len(dependency_result['dependency_errors']) >= 1, "Should identify dependency conflicts"
        
        dependency_error = dependency_result['dependency_errors'][0]
        assert 'adaptive_fps' in dependency_error['conflicting_parameters'], "Should identify adaptive_fps conflict"
        assert 'target_fps' in dependency_error['conflicting_parameters'], "Should identify target_fps conflict"
        
        # Test valid dependencies
        compatible_config = {
            'target_fps': 10.0,
            'adaptive_fps': True,
            'processing_timeout': 2.0,
            'memory_monitoring': True
        }
        
        dependency_result = processor.validate_configuration_dependencies(compatible_config)
        assert dependency_result['dependencies_valid'], "Compatible configuration should pass dependency validation"
        assert len(dependency_result['dependency_errors']) == 0, "Compatible configuration should have no dependency errors"
        
        # Test performance implications
        performance_risky_config = {
            'target_fps': 30.0,  # High FPS
            'processing_timeout': 5.0,  # Long timeout
            'memory_monitoring': True,  # Memory monitoring overhead
            'adaptive_fps': False  # No adaptive adjustment
        }
        
        dependency_result = processor.validate_configuration_dependencies(performance_risky_config)
        assert dependency_result['dependencies_valid'], "Performance risky config should be valid"
        assert len(dependency_result['performance_warnings']) >= 1, "Should warn about performance risks"
        
        performance_warning = dependency_result['performance_warnings'][0]
        assert 'high_resource_usage' in performance_warning['warning_type'], "Should identify high resource usage"


class TestConfigurationPersistence:
    """Phase 3.3: Configuration persistence and versioning."""
    
    def test_configuration_save_and_load_with_versioning(self):
        """
        🔴 RED: Test configuration persistence with versioning support.
        
        Should save/load configurations with version tracking and metadata.
        """
        # Setup processor
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0,
            processing_timeout=2.5,
            adaptive_fps=True
        )
        
        # This should work but will fail because persistence doesn't exist yet
        assert hasattr(processor, 'save_configuration'), "Processor should support configuration saving"
        assert hasattr(processor, 'load_configuration'), "Processor should support configuration loading"
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as temp_file:
            temp_config_path = temp_file.name
        
        try:
            # Save current configuration
            save_metadata = {
                'description': 'Test configuration for Phase 3.3',
                'author': 'TDD Test Suite',
                'environment': 'test'
            }
            
            save_result = processor.save_configuration(
                config_path=temp_config_path,
                metadata=save_metadata,
                include_runtime_stats=True,
                version_tag='v3.3.0-test'
            )
            
            assert save_result['success'], "Configuration save should succeed"
            assert 'config_version' in save_result, "Should generate configuration version"
            assert 'file_path' in save_result, "Should provide file path"
            assert os.path.exists(temp_config_path), "Configuration file should be created"
            
            # Modify processor configuration
            processor.target_fps = 15.0
            processor.processing_timeout = 4.0
            
            # Load saved configuration
            load_result = processor.load_configuration(
                config_path=temp_config_path,
                validate_before_load=True,
                backup_current_config=True
            )
            
            assert load_result['success'], "Configuration load should succeed"
            assert 'loaded_version' in load_result, "Should provide loaded version"
            assert 'backup_path' in load_result, "Should provide backup path"
            
            # Verify configuration was restored
            assert processor.target_fps == 8.0, "Target FPS should be restored from file"
            assert processor.processing_timeout == 2.5, "Processing timeout should be restored"
            assert processor.adaptive_fps == True, "Adaptive FPS should be restored"
            
            # Verify metadata was loaded
            assert hasattr(processor, 'get_configuration_metadata'), "Processor should provide metadata access"
            metadata = processor.get_configuration_metadata()
            assert metadata['description'] == save_metadata['description'], "Should preserve description"
            assert metadata['version_tag'] == 'v3.3.0-test', "Should preserve version tag"
            
        finally:
            # Cleanup
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_configuration_history_and_rollback(self):
        """
        🔴 RED: Test configuration history tracking and rollback capability.
        
        Should maintain configuration history and support rollback to previous versions.
        """
        # Setup processor
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        # This should work but will fail because history tracking doesn't exist yet
        assert hasattr(processor, 'enable_configuration_history'), "Processor should support configuration history"
        processor.enable_configuration_history(max_history_entries=10)
        
        # Track configuration changes
        original_fps = processor.target_fps
        
        # Make several configuration changes
        config_changes = [
            {'target_fps': 10.0, 'description': 'First update'},
            {'target_fps': 15.0, 'processing_timeout': 3.0, 'description': 'Second update'},
            {'target_fps': 7.0, 'adaptive_fps': True, 'description': 'Third update'}
        ]
        
        for i, config_change in enumerate(config_changes):
            description = config_change.pop('description')
            
            assert hasattr(processor, 'update_configuration_with_history'), "Processor should support configuration updates with history"
            
            update_result = processor.update_configuration_with_history(
                config_change,
                change_description=description,
                author=f'test_user_{i}'
            )
            
            assert update_result['success'], f"Configuration update {i} should succeed"
            assert 'history_entry_id' in update_result, f"Should provide history entry ID for update {i}"
        
        # Get configuration history
        assert hasattr(processor, 'get_configuration_history'), "Processor should provide configuration history"
        history = processor.get_configuration_history()
        
        assert len(history['entries']) >= 3, "Should track all configuration changes"
        assert history['current_version'] >= 3, "Should track current version number"
        
        # Verify history entries
        for i, entry in enumerate(history['entries'][-3:]):  # Last 3 entries
            assert 'timestamp' in entry, f"History entry {i} should have timestamp"
            assert 'change_description' in entry, f"History entry {i} should have description"
            assert 'configuration_snapshot' in entry, f"History entry {i} should have config snapshot"
            assert 'author' in entry, f"History entry {i} should have author"
        
        # Test rollback to previous configuration
        assert hasattr(processor, 'rollback_to_configuration'), "Processor should support configuration rollback"
        
        # Rollback to second-to-last configuration
        target_entry_id = history['entries'][-2]['entry_id']
        
        rollback_result = processor.rollback_to_configuration(
            target_entry_id=target_entry_id,
            rollback_reason='Testing rollback functionality'
        )
        
        assert rollback_result['success'], "Configuration rollback should succeed"
        assert 'rolled_back_to_version' in rollback_result, "Should identify rollback target version"
        assert 'new_history_entry_id' in rollback_result, "Rollback should create new history entry"
        
        # Verify rollback worked
        assert processor.target_fps == 15.0, "Should rollback to previous target FPS"
        assert processor.processing_timeout == 3.0, "Should rollback to previous timeout"
        
        # Verify rollback created history entry
        updated_history = processor.get_configuration_history()
        assert len(updated_history['entries']) == len(history['entries']) + 1, "Rollback should create new history entry"
        
        latest_entry = updated_history['entries'][-1]
        assert latest_entry['change_type'] == 'rollback', "Should identify entry as rollback"
        assert latest_entry['rollback_reason'] == 'Testing rollback functionality', "Should preserve rollback reason" 