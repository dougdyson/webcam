"""
Latest Frame Processor for zero-lag frame processing.

This module provides Latest Frame processing that always grabs the most current
frame instead of using a queue, eliminating lag and ensuring real-time responsiveness.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LatestFrameProcessor:
    """
    Minimal Latest Frame Processor for queue-to-latest-frame migration.
    
    This is a placeholder implementation created during TDD migration.
    """
    
    def __init__(self, camera_manager=None, detector=None):
        """Initialize minimal Latest Frame Processor."""
        self.camera_manager = camera_manager
        self.detector = detector
        self.is_running = False
        
        logger.info("LatestFrameProcessor created (minimal implementation)")
    
    def start(self):
        """Start the processor."""
        self.is_running = True
        logger.info("LatestFrameProcessor started")
    
    def stop(self):
        """Stop the processor."""
        self.is_running = False
        logger.info("LatestFrameProcessor stopped") 