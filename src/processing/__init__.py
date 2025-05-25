"""
Processing module for webcam human detection application.

This module provides frame processing infrastructure including queue management
and asynchronous processing capabilities.
"""

from .queue import FrameQueue, FrameQueueError, FrameMetadata, QueuedFrame

__all__ = [
    'FrameQueue', 'FrameQueueError', 'FrameMetadata', 'QueuedFrame'
] 