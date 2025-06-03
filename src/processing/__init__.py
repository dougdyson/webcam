"""
Processing module for webcam human detection.

This module provides frame processing, queue management, presence filtering,
and latest frame processing capabilities for the webcam detection system.
"""

from .queue import FrameQueue, FrameQueueError, FrameMetadata, QueuedFrame
from .processor import FrameProcessor, FrameProcessorError, ProcessingResult
from .filter import PresenceFilter, PresenceFilterConfig, PresenceFilterError

# Latest Frame Processing components (refactored architecture)
from .latest_frame_processor_refactored import (
    LatestFrameProcessor,
    LatestFrameResult,
    create_latest_frame_processor
)
from .frame_statistics import FrameStatistics
from .performance_monitor import PerformanceMonitor
from .callback_manager import CallbackManager
from .configuration_manager import ConfigurationManager

__all__ = [
    # Original processing components
    'FrameQueue',
    'FrameQueueError', 
    'FrameMetadata',
    'QueuedFrame',
    'FrameProcessor',
    'ProcessingResult',
    'FrameProcessorError',
    'PresenceFilter',
    'PresenceFilterConfig',
    'PresenceFilterError',
    
    # Latest Frame Processing components (refactored architecture)
    'LatestFrameProcessor',
    'LatestFrameResult',
    'create_latest_frame_processor',
    'FrameStatistics',
    'PerformanceMonitor', 
    'CallbackManager',
    'ConfigurationManager',
] 