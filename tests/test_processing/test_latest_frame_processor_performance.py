"""
Test suite for LatestFrameProcessor - Phase 2.2 Performance Monitoring

This implements Phase 2.2 of the Latest Frame Processing TDD plan:
- Real-time performance metrics tests
- Processing lag detection tests
- Efficiency calculations and monitoring tests
- Adaptive performance optimization tests

These tests follow strict TDD methodology: RED → GREEN → REFACTOR
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch
import numpy as np

from src.processing.latest_frame_processor import (
    LatestFrameProcessor,
    LatestFrameResult
)


class TestLatestFrameProcessorPerformanceMonitoring:
    """Phase 2.2: Real-time performance monitoring tests."""
    
    @pytest.mark.asyncio
    async def test_real_time_performance_metrics_calculation(self):
        """
        🔴 RED: Test real-time performance metrics calculation.
        
        Should provide live performance insights for lag elimination monitoring.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with predictable timing
        async def timed_async_detect(frame):
            await asyncio.sleep(0.05)  # 50ms processing time
            result = Mock()
            result.human_present = True
            result.confidence = 0.88
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0  # 100ms intervals
        )
        
        processor._async_detect = timed_async_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.4)  # Process several frames
        await processor.stop()
        
        # Assert - Should have real-time performance metrics
        perf_metrics = processor.get_real_time_performance_metrics()
        
        assert 'current_fps' in perf_metrics
        assert 'target_fps' in perf_metrics
        assert 'processing_efficiency_percent' in perf_metrics
        assert 'average_processing_latency_ms' in perf_metrics
        assert 'recent_frame_intervals_ms' in perf_metrics
        assert 'frame_processing_trend' in perf_metrics
        assert 'lag_detection_status' in perf_metrics
        assert 'performance_warnings' in perf_metrics
        
        # Validate metric ranges
        assert 0.0 <= perf_metrics['current_fps'] <= 15.0
        assert perf_metrics['target_fps'] == 10.0
        assert 0.0 <= perf_metrics['processing_efficiency_percent'] <= 100.0
        assert perf_metrics['average_processing_latency_ms'] > 45.0  # Should reflect ~50ms processing
        assert isinstance(perf_metrics['recent_frame_intervals_ms'], list)
        assert perf_metrics['frame_processing_trend'] in ['improving', 'stable', 'degrading']
        assert perf_metrics['lag_detection_status'] in ['real_time', 'minor_lag', 'significant_lag']
        
    @pytest.mark.asyncio
    async def test_processing_lag_detection_and_warnings(self):
        """
        🔴 RED: Test detection of processing lag and warning generation.
        
        Critical for identifying when lag elimination is not working effectively.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Create progressively slower detector to trigger lag detection
        call_count = 0
        async def progressively_slower_detect(frame):
            nonlocal call_count
            call_count += 1
            # Start fast, get progressively slower
            delay = 0.02 + (call_count * 0.03)  # 20ms, 50ms, 80ms, 110ms...
            await asyncio.sleep(delay)
            
            result = Mock()
            result.human_present = True
            result.confidence = 0.85
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0  # 125ms intervals
        )
        
        processor._async_detect = progressively_slower_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.8)  # Run long enough to see lag develop
        await processor.stop()
        
        # Assert - Should detect lag and generate warnings
        lag_status = processor.get_lag_detection_status()
        
        assert 'lag_severity' in lag_status
        assert 'lag_trend' in lag_status
        assert 'time_behind_real_time_ms' in lag_status
        assert 'frames_dropped_due_to_lag' in lag_status
        assert 'lag_warning_active' in lag_status
        assert 'recommended_actions' in lag_status
        
        # Should detect increasing lag
        assert lag_status['lag_severity'] in ['none', 'minor', 'moderate', 'severe']
        assert lag_status['lag_trend'] in ['improving', 'stable', 'worsening']
        assert lag_status['time_behind_real_time_ms'] >= 0
        assert lag_status['frames_dropped_due_to_lag'] >= 0
        assert isinstance(lag_status['lag_warning_active'], bool)
        assert isinstance(lag_status['recommended_actions'], list)
        
        # With progressively slower processing, should have some lag
        if lag_status['lag_severity'] != 'none':
            assert lag_status['lag_warning_active'] == True
            assert len(lag_status['recommended_actions']) > 0
    
    @pytest.mark.asyncio
    async def test_efficiency_monitoring_with_adaptive_thresholds(self):
        """
        🔴 RED: Test efficiency monitoring with adaptive performance thresholds.
        
        Should adapt warning thresholds based on system capabilities.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with varying performance
        performance_pattern = [0.03, 0.02, 0.04, 0.02, 0.01, 0.03, 0.02]  # Varying delays
        call_count = 0
        
        async def varying_performance_detect(frame):
            nonlocal call_count
            delay = performance_pattern[call_count % len(performance_pattern)]
            call_count += 1
            await asyncio.sleep(delay)
            
            result = Mock()
            result.human_present = True
            result.confidence = 0.91
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=15.0  # ~67ms intervals
        )
        
        processor._async_detect = varying_performance_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.6)  # Process through performance pattern
        await processor.stop()
        
        # Assert - Should have adaptive efficiency monitoring
        efficiency_status = processor.get_efficiency_monitoring_status()
        
        assert 'current_efficiency_percent' in efficiency_status
        assert 'efficiency_trend' in efficiency_status
        assert 'adaptive_threshold_percent' in efficiency_status
        assert 'baseline_performance_ms' in efficiency_status
        assert 'performance_variability_ms' in efficiency_status
        assert 'efficiency_warning_level' in efficiency_status
        assert 'optimization_suggestions' in efficiency_status
        
        # Validate efficiency calculations
        assert 0.0 <= efficiency_status['current_efficiency_percent'] <= 100.0
        assert efficiency_status['efficiency_trend'] in ['improving', 'stable', 'declining']
        assert 0.0 <= efficiency_status['adaptive_threshold_percent'] <= 100.0
        assert efficiency_status['baseline_performance_ms'] > 0
        assert efficiency_status['performance_variability_ms'] >= 0
        assert efficiency_status['efficiency_warning_level'] in ['none', 'minor', 'moderate', 'critical']
        assert isinstance(efficiency_status['optimization_suggestions'], list)
    
    def test_performance_metrics_thread_safety(self):
        """
        🔴 RED: Test thread safety of performance monitoring operations.
        
        Performance metrics should be safely accessible from multiple threads.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector
        )
        
        # Simulate concurrent access to performance metrics
        metrics_results = []
        errors = []
        
        def access_metrics():
            try:
                for _ in range(50):
                    # Access different performance metric methods
                    real_time_metrics = processor.get_real_time_performance_metrics()
                    lag_status = processor.get_lag_detection_status()
                    efficiency_status = processor.get_efficiency_monitoring_status()
                    
                    metrics_results.append({
                        'real_time': real_time_metrics,
                        'lag': lag_status,
                        'efficiency': efficiency_status
                    })
                    
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Act - Run concurrent metric access
        threads = []
        for _ in range(5):
            t = threading.Thread(target=access_metrics)
            threads.append(t)
            
        for t in threads:
            t.start()
            
        for t in threads:
            t.join()
        
        # Assert - Should handle concurrent access safely
        assert len(errors) == 0  # No thread safety errors
        assert len(metrics_results) == 250  # 5 threads × 50 operations
        
        # All results should be valid
        for result in metrics_results:
            assert 'real_time' in result
            assert 'lag' in result  
            assert 'efficiency' in result
            assert isinstance(result['real_time'], dict)
            assert isinstance(result['lag'], dict)
            assert isinstance(result['efficiency'], dict)


class TestLatestFrameProcessorAdaptiveOptimization:
    """Phase 2.2: Adaptive performance optimization tests."""
    
    @pytest.mark.asyncio
    async def test_adaptive_fps_adjustment_based_on_performance(self):
        """
        🔴 RED: Test adaptive FPS adjustment based on measured performance.
        
        Should automatically adjust target FPS when system can't keep up.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector that's consistently too slow for target FPS
        async def consistently_slow_detect(frame):
            await asyncio.sleep(0.18)  # 180ms - too slow for high FPS
            result = Mock()
            result.human_present = True
            result.confidence = 0.79
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=10.0,  # 100ms intervals - too fast for 180ms processing
            adaptive_fps=True  # Enable adaptive FPS adjustment
        )
        
        processor._async_detect = consistently_slow_detect
        
        # Track FPS adjustments
        fps_adjustments = []
        
        def track_fps_adjustment(old_fps, new_fps, reason):
            fps_adjustments.append({
                'old_fps': old_fps,
                'new_fps': new_fps,
                'reason': reason,
                'timestamp': time.time()
            })
        
        processor.add_fps_adjustment_callback(track_fps_adjustment)
        
        # Act
        await processor.start()
        await asyncio.sleep(1.0)  # Run long enough to trigger adaptation
        await processor.stop()
        
        # Assert - Should have adapted FPS downward
        assert len(fps_adjustments) >= 1  # Should have made adjustments
        
        final_adjustment = fps_adjustments[-1]
        assert final_adjustment['new_fps'] < final_adjustment['old_fps']  # FPS reduced
        assert final_adjustment['new_fps'] >= 3.0  # Should not go too low
        assert 'performance' in final_adjustment['reason'].lower()
        
        # Final FPS should be sustainable for the slow detector
        final_fps = processor.get_current_target_fps()
        assert final_fps < 10.0  # Should be reduced from original
        assert final_fps >= 3.0   # Should not be too low
    
    @pytest.mark.asyncio
    async def test_performance_optimization_recommendations(self):
        """
        🔴 RED: Test generation of performance optimization recommendations.
        
        Should provide actionable suggestions for improving performance.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector with different performance characteristics
        async def variable_performance_detect(frame):
            # Simulate high variability in processing time
            import random
            delay = random.uniform(0.02, 0.20)  # 20ms to 200ms variation
            await asyncio.sleep(delay)
            
            result = Mock()
            result.human_present = True
            result.confidence = 0.82
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=8.0
        )
        
        processor._async_detect = variable_performance_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.8)  # Process with variable performance
        await processor.stop()
        
        # Assert - Should generate optimization recommendations
        recommendations = processor.get_optimization_recommendations()
        
        assert 'performance_analysis' in recommendations
        assert 'recommended_actions' in recommendations
        assert 'estimated_improvements' in recommendations
        assert 'priority_level' in recommendations
        assert 'implementation_complexity' in recommendations
        
        # Should have actionable recommendations
        actions = recommendations['recommended_actions']
        assert len(actions) >= 1
        
        for action in actions:
            assert 'action' in action
            assert 'description' in action
            assert 'expected_benefit' in action
            assert 'effort_level' in action
            
        # Priority should be valid
        assert recommendations['priority_level'] in ['low', 'medium', 'high', 'critical']
        
        # Should analyze high variability
        analysis = recommendations['performance_analysis']
        assert 'variability_detected' in analysis
        assert 'bottleneck_identification' in analysis
        assert 'system_capability_assessment' in analysis
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring_and_optimization(self):
        """
        🔴 RED: Test memory usage monitoring and optimization alerts.
        
        Should track memory usage and warn of potential memory issues.
        """
        # Arrange
        mock_camera = Mock()
        mock_detector = Mock()
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        mock_camera.get_frame.return_value = test_frame
        
        # Mock detector that processes normally
        async def normal_detect(frame):
            await asyncio.sleep(0.03)
            result = Mock()
            result.human_present = True
            result.confidence = 0.86
            return result
        
        processor = LatestFrameProcessor(
            camera_manager=mock_camera,
            detector=mock_detector,
            target_fps=12.0,
            memory_monitoring=True  # Enable memory monitoring
        )
        
        processor._async_detect = normal_detect
        
        # Act
        await processor.start()
        await asyncio.sleep(0.5)  # Process frames while monitoring memory
        await processor.stop()
        
        # Assert - Should have memory usage monitoring
        memory_status = processor.get_memory_usage_status()
        
        assert 'current_memory_mb' in memory_status
        assert 'peak_memory_mb' in memory_status
        assert 'memory_trend' in memory_status
        assert 'memory_efficiency' in memory_status
        assert 'memory_warnings' in memory_status
        assert 'memory_optimization_suggestions' in memory_status
        
        # Validate memory metrics
        assert memory_status['current_memory_mb'] > 0
        assert memory_status['peak_memory_mb'] >= memory_status['current_memory_mb']
        assert memory_status['memory_trend'] in ['increasing', 'stable', 'decreasing']
        assert 0.0 <= memory_status['memory_efficiency'] <= 100.0
        assert isinstance(memory_status['memory_warnings'], list)
        assert isinstance(memory_status['memory_optimization_suggestions'], list) 