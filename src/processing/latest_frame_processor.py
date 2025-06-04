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
    
    def process_frame(self, frame):
        """
        Process a single frame using the detector.
        
        This method provides the same interface as direct detector calls
        but goes through the Latest Frame Processor for consistency.
        
        Args:
            frame: Frame to process
            
        Returns:
            Detection result from the detector
        """
        if self.detector is None:
            raise RuntimeError("Detector not initialized")
            
        # For now, just pass through to the detector
        # This maintains compatibility while we migrate
        return self.detector.detect(frame) 