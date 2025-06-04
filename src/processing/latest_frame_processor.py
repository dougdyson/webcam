"""
Latest Frame Processor for zero-lag frame processing.

This module provides Latest Frame processing that always grabs the most current
frame instead of using a queue, eliminating lag and ensuring real-time responsiveness.
"""
import logging
import threading
import asyncio
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LatestFrameProcessor:
    """
    Latest Frame Processor with wait-for-completion Ollama integration.
    
    Provides real-time detection at full FPS while ensuring only one Ollama
    description request runs at a time (wait for completion before starting next).
    """
    
    def __init__(self, camera_manager=None, detector=None):
        """Initialize Latest Frame Processor with wait-for-completion capability."""
        self.camera_manager = camera_manager
        self.detector = detector
        self.is_running = False
        
        # Wait-for-completion Ollama integration
        self.description_service = None
        self.latest_frame_for_description = None
        self.description_processing_lock = threading.Lock()
        self._description_thread = None
        self._is_processing_description = False
        
        logger.info("LatestFrameProcessor created with wait-for-completion Ollama support")
    
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
        
        This method provides real-time detection without any delays.
        
        Args:
            frame: Frame to process
            
        Returns:
            Detection result from the detector
        """
        if self.detector is None:
            raise RuntimeError("Detector not initialized")
            
        return self.detector.detect(frame)
    
    def set_description_service(self, description_service):
        """
        Set the description service for wait-for-completion Ollama processing.
        
        Args:
            description_service: Ollama description service instance
        """
        self.description_service = description_service
        logger.info("Description service configured for wait-for-completion processing")
    
    def is_description_processing(self):
        """
        Check if Ollama description processing is currently active.
        
        Returns:
            bool: True if Ollama is currently processing a description
        """
        return self._is_processing_description
    
    def process_frame_with_description(self, frame):
        """
        Process frame with wait-for-completion description processing.
        
        This method:
        1. Always processes detection immediately (no lag)
        2. Stores latest frame for description processing
        3. Starts Ollama processing only if no current processing is active
        
        Args:
            frame: Frame to process
            
        Returns:
            Detection result (immediate, no delays)
        """
        # Always process detection immediately (real-time, no delays)
        detection_result = self.process_frame(frame)
        
        # Store latest frame for potential description processing
        with self.description_processing_lock:
            self.latest_frame_for_description = frame.copy()
        
        # Start Ollama processing only if human detected AND no current processing
        if (self.description_service and 
            detection_result.human_present and 
            not self._is_processing_description):
            
            self._start_description_processing()
        
        return detection_result
    
    def _start_description_processing(self):
        """
        Start description processing if no other processing is active.
        
        Uses a single background thread - waits for completion before allowing new requests.
        """
        # Only start if no description processing is currently running
        if not self._is_processing_description:
            self._is_processing_description = True
            self._description_thread = threading.Thread(
                target=self._process_description_wait_for_completion,
                daemon=True
            )
            self._description_thread.start()
    
    def _process_description_wait_for_completion(self):
        """
        Process description in background thread using latest available frame.
        
        This method runs synchronously and marks processing complete when done.
        """
        try:
            # Get the latest frame at processing time (not when queued)
            with self.description_processing_lock:
                frame_to_process = self.latest_frame_for_description.copy() if self.latest_frame_for_description is not None else None
            
            if frame_to_process is not None and self.description_service:
                # Create snapshot from latest frame
                from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
                
                snapshot_metadata = SnapshotMetadata(
                    timestamp=datetime.now(),
                    confidence=0.8,  # Placeholder confidence
                    human_present=True,
                    detection_source="latest_frame_wait_for_completion"
                )
                snapshot = Snapshot(frame=frame_to_process, metadata=snapshot_metadata)
                
                # Process description synchronously - wait for completion
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    description_result = loop.run_until_complete(
                        self.description_service.describe_snapshot(snapshot)
                    )
                    if description_result and hasattr(description_result, 'success') and description_result.success:
                        logger.debug(f"Wait-for-completion description: {description_result.description[:50]}...")
                finally:
                    loop.close()
                    
        except Exception as e:
            logger.debug(f"Wait-for-completion description error: {e}")
        finally:
            # Mark processing as complete - allows new requests
            self._is_processing_description = False 