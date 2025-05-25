"""
Processing module for webcam human detection.

This module provides frame processing, queue management, and presence
filtering capabilities for the webcam detection system.
"""

from .queue import FrameQueue, FrameQueueError, FrameMetadata, QueuedFrame
from .processor import FrameProcessor, FrameProcessorError, ProcessingResult
from .filter import PresenceFilter, PresenceFilterConfig, PresenceFilterError

__all__ = [
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
] 