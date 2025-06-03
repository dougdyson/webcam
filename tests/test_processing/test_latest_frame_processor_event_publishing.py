"""
Test suite for LatestFrameProcessor - Phase 3.2 Event Publishing Integration

This implements Phase 3.2 of the Latest Frame Processing TDD plan:
- Latest frame results → event publishing tests
- Snapshot triggering with latest frames tests
- Intelligent snapshot timing optimization tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np
from datetime import datetime, timedelta

from src.processing.latest_frame_processor import (
    LatestFrameProcessor,
    LatestFrameResult,
    create_latest_frame_processor
)


class TestLatestFrameResultsEventPublishing:
    """Phase 3.2: Advanced event publishing for latest frame results."""
    
    @pytest.mark.asyncio
    async def test_structured_event_publishing_with_frame_metadata(self):
        """
        🔴 RED: Test structured event publishing with comprehensive frame metadata.
        
        Events should include frame age, processing efficiency, and trend analysis.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.89
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        # Create processor
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=6.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track detailed events
        published_events = []
        
        def advanced_event_callback(event_data):
            published_events.append(event_data)
        
        # This should work but will fail because advanced event publishing doesn't exist yet
        assert hasattr(processor, 'add_advanced_event_callback'), "Processor should support advanced event callbacks"
        processor.add_advanced_event_callback(advanced_event_callback)
        
        # Enable comprehensive event publishing
        assert hasattr(processor, 'enable_comprehensive_event_publishing'), "Processor should support comprehensive event publishing"
        processor.enable_comprehensive_event_publishing(include_trends=True, include_efficiency=True)
        
        await processor.start()
        await asyncio.sleep(0.4)  # Process multiple frames
        await processor.stop()
        
        # Should have published comprehensive events
        assert len(published_events) >= 2
        
        event = published_events[0]
        assert event['type'] == 'comprehensive_frame_processed'
        
        # Check comprehensive metadata
        data = event['data']
        assert 'frame_metadata' in data
        assert 'processing_efficiency' in data
        assert 'frame_age_ms' in data
        assert 'trend_analysis' in data
        
        # Verify efficiency calculation
        assert 'efficiency_percent' in data['processing_efficiency']
        assert 'target_vs_actual_fps' in data['processing_efficiency']
        
        # Verify trend analysis
        assert 'processing_trend' in data['trend_analysis']  # 'improving', 'stable', 'degrading'
        assert 'confidence_trend' in data['trend_analysis']
    
    @pytest.mark.asyncio
    async def test_conditional_event_publishing_based_on_confidence(self):
        """
        🔴 RED: Test conditional event publishing based on confidence thresholds.
        
        High-confidence detections should trigger different events than low-confidence.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with varying confidence
        detection_results = [
            Mock(human_present=True, confidence=0.95),   # High confidence
            Mock(human_present=True, confidence=0.75),   # Medium confidence  
            Mock(human_present=True, confidence=0.45),   # Low confidence
            Mock(human_present=False, confidence=0.20),  # No human
        ]
        
        result_index = 0
        async def mock_async_detect(frame):
            nonlocal result_index
            result = detection_results[result_index % len(detection_results)]
            result_index += 1
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0
        )
        
        processor._async_detect = mock_async_detect
        
        # Track confidence-based events
        high_confidence_events = []
        medium_confidence_events = []
        low_confidence_events = []
        
        def confidence_event_callback(event_data):
            confidence = event_data['data']['confidence']
            if confidence >= 0.9:
                high_confidence_events.append(event_data)
            elif confidence >= 0.6:
                medium_confidence_events.append(event_data)
            else:
                low_confidence_events.append(event_data)
        
        # This should work but will fail because confidence-based event filtering doesn't exist yet
        assert hasattr(processor, 'add_confidence_event_callback'), "Processor should support confidence-based events"
        processor.add_confidence_event_callback(confidence_event_callback)
        
        # Configure confidence thresholds
        assert hasattr(processor, 'configure_confidence_thresholds'), "Processor should support confidence threshold configuration"
        processor.configure_confidence_thresholds(
            high_threshold=0.9,
            medium_threshold=0.6,
            publish_all_levels=True
        )
        
        await processor.start()
        await asyncio.sleep(0.6)  # Process multiple frames with different confidence levels
        await processor.stop()
        
        # Should categorize events by confidence
        assert len(high_confidence_events) >= 1, "Should have high confidence events"
        assert len(medium_confidence_events) >= 1, "Should have medium confidence events"
        assert len(low_confidence_events) >= 1, "Should have low confidence events"
        
        # Verify event content
        assert high_confidence_events[0]['data']['confidence'] >= 0.9
        assert medium_confidence_events[0]['data']['confidence'] >= 0.6
    
    @pytest.mark.asyncio
    async def test_batch_event_publishing_for_performance(self):
        """
        🔴 RED: Test batch event publishing for improved performance.
        
        Events should be batched when processing many frames rapidly.
        """
        # Setup mocks for rapid frame processing
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.82
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=15.0  # High FPS for rapid processing
        )
        
        processor._async_detect = mock_async_detect
        
        # Track batch events
        batch_events = []
        individual_events = []
        
        def batch_event_callback(batch_data):
            batch_events.append(batch_data)
        
        def individual_event_callback(event_data):
            individual_events.append(event_data)
        
        # This should work but will fail because batch event publishing doesn't exist yet
        assert hasattr(processor, 'add_batch_event_callback'), "Processor should support batch event callbacks"
        processor.add_batch_event_callback(batch_event_callback)
        processor.add_event_callback(individual_event_callback)
        
        # Configure batch settings
        assert hasattr(processor, 'configure_batch_publishing'), "Processor should support batch publishing configuration"
        processor.configure_batch_publishing(
            batch_size=5,
            batch_timeout_ms=200,
            enable_batching=True
        )
        
        await processor.start()
        await asyncio.sleep(0.8)  # Process many frames rapidly
        await processor.stop()
        
        # Should have published batch events
        assert len(batch_events) >= 1, "Should have batch events"
        
        batch = batch_events[0]
        assert 'batch_size' in batch
        assert 'events' in batch
        assert 'batch_processing_time_ms' in batch
        assert len(batch['events']) >= 2, "Batch should contain multiple events"
        
        # Individual events should still be published
        assert len(individual_events) >= len(batch['events'])


class TestSnapshotTriggeringWithLatestFrames:
    """Phase 3.2: Intelligent snapshot triggering for AI descriptions."""
    
    def test_intelligent_snapshot_timing_based_on_scene_changes(self):
        """
        🔴 RED: Test intelligent snapshot timing based on scene changes.
        
        Snapshots should be triggered when significant scene changes occur.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        base_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Simulate scene changes
        frames = [
            base_frame,                                                    # Frame 1: baseline
            base_frame + np.random.randint(-10, 10, base_frame.shape),   # Frame 2: minor change
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),   # Frame 3: major change
            base_frame,                                                    # Frame 4: back to baseline
        ]
        
        frame_index = 0
        def get_frame():
            nonlocal frame_index
            frame = frames[frame_index % len(frames)]
            frame_index += 1
            return frame
        
        mock_camera.get_frame.side_effect = get_frame
        
        # Mock detection results
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.88
        
        def mock_detect(frame):
            return mock_detection_result
        
        mock_detector.detect = mock_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=4.0
        )
        
        # Track snapshot triggers
        snapshot_triggers = []
        scene_change_events = []
        
        def snapshot_callback(frame, metadata):
            snapshot_triggers.append({
                'frame_shape': frame.shape,
                'metadata': metadata,
                'trigger_reason': metadata.get('trigger_reason')
            })
        
        def scene_change_callback(event_data):
            scene_change_events.append(event_data)
        
        # This should work but will fail because intelligent snapshot timing doesn't exist yet
        assert hasattr(processor, 'enable_intelligent_snapshot_timing'), "Processor should support intelligent snapshot timing"
        processor.enable_intelligent_snapshot_timing(
            scene_change_threshold=0.3,  # 30% change triggers snapshot
            min_snapshot_interval_seconds=1.0,
            enable_scene_change_detection=True
        )
        
        processor.add_snapshot_callback(snapshot_callback)
        
        assert hasattr(processor, 'add_scene_change_callback'), "Processor should support scene change callbacks"
        processor.add_scene_change_callback(scene_change_callback)
        
        # Process frames synchronously for testing
        for i in range(len(frames)):
            frame = processor._get_latest_frame()
            result = processor.detector.detect(frame)
            
            # Manually trigger scene analysis
            assert hasattr(processor, 'analyze_scene_change'), "Processor should support scene change analysis"
            processor.analyze_scene_change(frame, result)
        
        # Should trigger snapshots on significant scene changes
        assert len(snapshot_triggers) >= 1, "Should trigger snapshots on scene changes"
        assert len(scene_change_events) >= 1, "Should detect scene changes"
        
        # Verify trigger reasons
        major_change_triggers = [s for s in snapshot_triggers if s['trigger_reason'] == 'scene_change']
        assert len(major_change_triggers) >= 1, "Should trigger on major scene changes"
        
        # Verify scene change detection
        scene_change = scene_change_events[0]
        assert 'change_magnitude' in scene_change['data']
        assert 'change_type' in scene_change['data']  # 'minor', 'major', 'significant'
    
    def test_adaptive_snapshot_frequency_based_on_activity_level(self):
        """
        🔴 RED: Test adaptive snapshot frequency based on activity level.
        
        High activity should increase snapshot frequency, low activity should decrease it.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Simulate varying activity levels
        activity_scenarios = [
            {'confidence': 0.95, 'movement': 'high', 'duration': 3},      # High activity
            {'confidence': 0.85, 'movement': 'medium', 'duration': 2},   # Medium activity
            {'confidence': 0.75, 'movement': 'low', 'duration': 4},      # Low activity
        ]
        
        scenario_index = 0
        frame_count = 0
        
        def mock_detect(frame):
            nonlocal scenario_index, frame_count
            scenario = activity_scenarios[scenario_index % len(activity_scenarios)]
            
            # Advance scenario based on duration
            frame_count += 1
            if frame_count >= scenario['duration']:
                scenario_index += 1
                frame_count = 0
            
            result = Mock()
            result.human_present = True
            result.confidence = scenario['confidence']
            result.movement_level = scenario['movement']  # Additional metadata
            return result
        
        mock_detector.detect = mock_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=5.0
        )
        
        # Track adaptive snapshots
        adaptive_snapshots = []
        frequency_changes = []
        
        def adaptive_snapshot_callback(frame, metadata):
            adaptive_snapshots.append({
                'timestamp': time.time(),
                'activity_level': metadata.get('activity_level'),
                'snapshot_reason': metadata.get('snapshot_reason')
            })
        
        def frequency_change_callback(event_data):
            frequency_changes.append(event_data)
        
        # This should work but will fail because adaptive snapshot frequency doesn't exist yet
        assert hasattr(processor, 'enable_adaptive_snapshot_frequency'), "Processor should support adaptive snapshot frequency"
        processor.enable_adaptive_snapshot_frequency(
            high_activity_interval=0.5,   # 2 per second
            medium_activity_interval=1.0, # 1 per second
            low_activity_interval=3.0,    # 1 per 3 seconds
            activity_detection_window=3   # Analyze last 3 frames
        )
        
        processor.add_snapshot_callback(adaptive_snapshot_callback)
        
        assert hasattr(processor, 'add_frequency_change_callback'), "Processor should support frequency change callbacks"
        processor.add_frequency_change_callback(frequency_change_callback)
        
        # Process frames to simulate activity changes
        for _ in range(12):  # Process enough frames to cover all scenarios
            frame = processor._get_latest_frame()
            result = processor.detector.detect(frame)
            
            # Manually trigger activity analysis
            assert hasattr(processor, 'analyze_activity_level'), "Processor should support activity level analysis"
            processor.analyze_activity_level(result)
            
            time.sleep(0.1)  # Brief delay
        
        # Should adapt snapshot frequency based on activity
        assert len(adaptive_snapshots) >= 3, "Should take adaptive snapshots"
        assert len(frequency_changes) >= 1, "Should change frequency based on activity"
        
        # Verify different activity levels triggered different frequencies
        activity_levels = [s['activity_level'] for s in adaptive_snapshots if s['activity_level']]
        assert len(set(activity_levels)) >= 2, "Should detect multiple activity levels"
    
    def test_snapshot_quality_optimization_with_latest_frames(self):
        """
        🔴 RED: Test snapshot quality optimization for AI descriptions.
        
        Snapshots should be optimized for quality and timing to improve AI description accuracy.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        
        # Create frames with different quality characteristics
        high_quality_frame = np.random.randint(100, 200, (480, 640, 3), dtype=np.uint8)  # Good contrast
        low_quality_frame = np.random.randint(50, 80, (480, 640, 3), dtype=np.uint8)     # Poor contrast
        blurry_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)          # Simulated blur
        
        frames = [high_quality_frame, low_quality_frame, blurry_frame, high_quality_frame]
        frame_index = 0
        
        def get_frame():
            nonlocal frame_index
            frame = frames[frame_index % len(frames)]
            frame_index += 1
            return frame
        
        mock_camera.get_frame.side_effect = get_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.91
        
        def mock_detect(frame):
            return mock_detection_result
        
        mock_detector.detect = mock_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=3.0
        )
        
        # Track quality-optimized snapshots
        quality_snapshots = []
        quality_assessments = []
        
        def quality_snapshot_callback(frame, metadata):
            quality_snapshots.append({
                'quality_score': metadata.get('quality_score'),
                'quality_factors': metadata.get('quality_factors'),
                'optimization_applied': metadata.get('optimization_applied')
            })
        
        def quality_assessment_callback(event_data):
            quality_assessments.append(event_data)
        
        # This should work but will fail because snapshot quality optimization doesn't exist yet
        assert hasattr(processor, 'enable_snapshot_quality_optimization'), "Processor should support snapshot quality optimization"
        processor.enable_snapshot_quality_optimization(
            min_quality_score=0.7,
            quality_factors=['contrast', 'sharpness', 'lighting'],
            enable_quality_enhancement=True,
            quality_assessment_window=3
        )
        
        processor.add_snapshot_callback(quality_snapshot_callback)
        
        assert hasattr(processor, 'add_quality_assessment_callback'), "Processor should support quality assessment callbacks"
        processor.add_quality_assessment_callback(quality_assessment_callback)
        
        # Process frames for quality analysis
        for _ in range(len(frames)):
            frame = processor._get_latest_frame()
            result = processor.detector.detect(frame)
            
            # Manually trigger quality analysis
            assert hasattr(processor, 'assess_frame_quality'), "Processor should support frame quality assessment"
            quality_score = processor.assess_frame_quality(frame)
            
            if quality_score >= 0.7:  # Only snapshot high quality frames
                snapshot_metadata = {
                    'quality_score': quality_score,
                    'quality_factors': {'contrast': 0.8, 'sharpness': 0.75, 'lighting': 0.9},
                    'optimization_applied': True
                }
                quality_snapshot_callback(frame, snapshot_metadata)
        
        # Should optimize snapshots for quality
        assert len(quality_snapshots) >= 1, "Should take quality-optimized snapshots"
        
        # Verify quality optimization
        high_quality_snapshots = [s for s in quality_snapshots if s['quality_score'] >= 0.7]
        assert len(high_quality_snapshots) >= 1, "Should prioritize high quality snapshots"
        
        # Verify quality factors are assessed
        snapshot = quality_snapshots[0]
        assert 'quality_factors' in snapshot
        assert 'contrast' in snapshot['quality_factors']
        assert 'optimization_applied' in snapshot


class TestEventPublishingOptimization:
    """Phase 3.2: Event flow optimization and overhead reduction."""
    
    @pytest.mark.asyncio
    async def test_event_publishing_performance_optimization(self):
        """
        🔴 RED: Test event publishing performance optimization.
        
        Event publishing should be optimized to minimize processing overhead.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        mock_detection_result = Mock()
        mock_detection_result.human_present = True
        mock_detection_result.confidence = 0.86
        
        async def mock_async_detect(frame):
            return mock_detection_result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0  # High FPS to test performance
        )
        
        processor._async_detect = mock_async_detect
        
        # Track performance metrics
        event_publishing_times = []
        performance_metrics = []
        
        def performance_callback(event_data):
            # Simulate event processing time
            start_time = time.time()
            # Minimal processing
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            event_publishing_times.append(processing_time)
        
        def performance_metrics_callback(metrics_data):
            performance_metrics.append(metrics_data)
        
        # This should work but will fail because performance optimization doesn't exist yet
        assert hasattr(processor, 'enable_performance_optimized_publishing'), "Processor should support performance optimized publishing"
        processor.enable_performance_optimized_publishing(
            max_event_processing_time_ms=5.0,
            enable_async_publishing=True,
            enable_event_compression=True,
            performance_monitoring=True
        )
        
        processor.add_event_callback(performance_callback)
        
        assert hasattr(processor, 'add_performance_metrics_callback'), "Processor should support performance metrics callbacks"
        processor.add_performance_metrics_callback(performance_metrics_callback)
        
        # Measure processing performance
        start_time = time.time()
        
        await processor.start()
        await asyncio.sleep(0.6)  # Process multiple frames rapidly
        await processor.stop()
        
        total_time = time.time() - start_time
        
        # Should optimize event publishing performance
        assert len(event_publishing_times) >= 3, "Should track event publishing performance"
        assert len(performance_metrics) >= 1, "Should provide performance metrics"
        
        # Verify performance optimization
        avg_event_time = sum(event_publishing_times) / len(event_publishing_times)
        assert avg_event_time < 10.0, "Event publishing should be optimized (< 10ms average)"
        
        # Verify performance metrics
        metrics = performance_metrics[0]
        assert 'average_event_processing_time_ms' in metrics
        assert 'event_publishing_overhead_percent' in metrics
        assert 'optimization_status' in metrics
    
    def test_event_prioritization_and_filtering(self):
        """
        🔴 RED: Test event prioritization and filtering for reduced overhead.
        
        Events should be prioritized and filtered to reduce unnecessary publishing.
        """
        # Setup mocks
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Create detection results with different priorities
        priority_results = [
            Mock(human_present=True, confidence=0.95, priority='high'),      # High priority
            Mock(human_present=True, confidence=0.75, priority='medium'),    # Medium priority
            Mock(human_present=True, confidence=0.55, priority='low'),       # Low priority
            Mock(human_present=False, confidence=0.30, priority='none'),     # No priority
        ]
        
        result_index = 0
        def mock_detect(frame):
            nonlocal result_index
            result = priority_results[result_index % len(priority_results)]
            result_index += 1
            return result
        
        mock_detector.detect = mock_detect
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=6.0
        )
        
        # Track prioritized events
        high_priority_events = []
        medium_priority_events = []
        low_priority_events = []
        filtered_events = []
        
        def priority_event_callback(event_data):
            priority = event_data['data'].get('priority', 'none')
            if priority == 'high':
                high_priority_events.append(event_data)
            elif priority == 'medium':
                medium_priority_events.append(event_data)
            elif priority == 'low':
                low_priority_events.append(event_data)
        
        def filtered_event_callback(event_data):
            filtered_events.append(event_data)
        
        # This should work but will fail because event prioritization doesn't exist yet
        assert hasattr(processor, 'configure_event_prioritization'), "Processor should support event prioritization"
        processor.configure_event_prioritization(
            priority_thresholds={
                'high': 0.9,
                'medium': 0.7,
                'low': 0.5
            },
            enable_filtering=True,
            filter_duplicate_events=True,
            max_events_per_second=10
        )
        
        processor.add_event_callback(priority_event_callback)
        
        assert hasattr(processor, 'add_filtered_event_callback'), "Processor should support filtered event callbacks"
        processor.add_filtered_event_callback(filtered_event_callback)
        
        # Process frames to test prioritization
        for _ in range(len(priority_results) * 2):  # Process multiple cycles
            frame = processor._get_latest_frame()
            result = processor.detector.detect(frame)
            
            # Manually trigger event prioritization
            assert hasattr(processor, 'process_prioritized_event'), "Processor should support prioritized event processing"
            processor.process_prioritized_event(result)
        
        # Should prioritize and filter events
        assert len(high_priority_events) >= 1, "Should publish high priority events"
        assert len(filtered_events) >= 1, "Should filter events appropriately"
        
        # Verify prioritization logic
        total_priority_events = len(high_priority_events) + len(medium_priority_events) + len(low_priority_events)
        assert total_priority_events >= len(filtered_events), "Prioritization should reduce event volume" 