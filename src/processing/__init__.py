"""
Processing module for webcam human detection application.

This module provides frame processing infrastructure including queue management
and asynchronous processing capabilities.
"""

from .queue import FrameQueue, FrameQueueError, FrameMetadata, QueuedFrame
from .processor import FrameProcessor, FrameProcessorError, ProcessingResult

__all__ = [
    'FrameQueue', 'FrameQueueError', 'FrameMetadata', 'QueuedFrame',
    'FrameProcessor', 'FrameProcessorError', 'ProcessingResult'
] 