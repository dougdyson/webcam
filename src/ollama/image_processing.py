"""
Image processing utilities for Ollama integration.

This module provides image optimization and processing specifically for Ollama's
computer vision models, focusing on efficient conversion of webcam frames to 
base64-encoded images ready for Ollama API consumption.

Key Features:
- Frame-to-base64 conversion with optimization
- Image resizing and quality optimization
- Channel normalization and format validation
- Performance statistics and monitoring
"""
import base64
import time
import logging
from io import BytesIO
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImageQuality(Enum):
    """Image quality levels for Ollama optimization."""
    LOW = 60
    MEDIUM = 80
    HIGH = 95


@dataclass
class ImageProcessingConfig:
    """
    Configuration for image processing optimized for Ollama models.
    
    This configuration provides Ollama-specific image optimization settings
    to balance quality and performance for computer vision processing.
    """
    max_width: int = 1024
    max_height: int = 1024
    quality: ImageQuality = ImageQuality.HIGH
    format: str = "JPEG"
    maintain_aspect_ratio: bool = True


class ImageProcessor:
    """
    Core image processor for converting webcam frames to Ollama-ready format.
    
    Handles frame conversion, resizing, quality optimization, and format
    validation for optimal Ollama model performance.
    """
    
    def __init__(self, config: Optional[ImageProcessingConfig] = None):
        """
        Initialize image processor with configuration.
        
        Args:
            config: ImageProcessingConfig instance, creates default if None
        """
        self.config = config or ImageProcessingConfig()
        self.stats = {
            'frames_processed': 0,
            'total_processing_time': 0.0,
            'total_size_reduced': 0
        }
        logger.debug(f"ImageProcessor initialized with config: {self.config}")

    def convert_frame_to_base64(self, frame: np.ndarray) -> str:
        """
        Convert numpy frame to base64 string for Ollama API.
        
        Args:
            frame: Input frame as numpy array (H, W, C)
            
        Returns:
            Base64-encoded image string
            
        Raises:
            ValueError: If frame is invalid or empty
        """
        start_time = time.time()
        
        # Validate input frame
        if frame is None:
            raise ValueError("Frame cannot be None")
        if frame.size == 0:
            raise ValueError("Frame cannot be empty")
        if len(frame.shape) != 3:
            raise ValueError("Frame must be 3-dimensional (H, W, C)")
            
        try:
            # Process image through pipeline
            processed_bytes = self.preprocess_image(frame)
            
            # Convert to base64
            base64_result = base64.b64encode(processed_bytes).decode('utf-8')
            
            # Update statistics
            processing_time = time.time() - start_time
            self.stats['frames_processed'] += 1
            self.stats['total_processing_time'] += processing_time
            
            logger.debug(f"Frame converted to base64 in {processing_time:.3f}s")
            return base64_result
            
        except Exception as e:
            logger.error(f"Failed to convert frame to base64: {e}")
            raise

    def resize_image(self, frame: np.ndarray) -> np.ndarray:
        """
        Resize image to fit within configured dimensions.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Resized frame maintaining aspect ratio
        """
        height, width = frame.shape[:2]
        
        # Don't upscale smaller images
        if width <= self.config.max_width and height <= self.config.max_height:
            return frame
            
        # Calculate resize ratio to fit within bounds
        width_ratio = self.config.max_width / width
        height_ratio = self.config.max_height / height
        resize_ratio = min(width_ratio, height_ratio)
        
        # Calculate new dimensions
        new_width = int(width * resize_ratio)
        new_height = int(height * resize_ratio)
        
        # Resize using high-quality interpolation
        resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        return resized

    def optimize_image_quality(self, frame: np.ndarray) -> bytes:
        """
        Apply quality optimization for Ollama processing.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Optimized image as bytes
        """
        # Convert numpy array to PIL Image for quality control
        if frame.dtype != np.uint8:
            frame = (frame * 255).astype(np.uint8)
            
        # Convert BGR to RGB (OpenCV to PIL)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        
        # Apply JPEG compression with quality setting
        buffer = BytesIO()
        pil_image.save(buffer, format=self.config.format, quality=self.config.quality.value)
        
        optimized_bytes = buffer.getvalue()
        buffer.close()
        
        return optimized_bytes

    def preprocess_image(self, frame: np.ndarray) -> bytes:
        """
        Apply full preprocessing pipeline for Ollama.
        
        Args:
            frame: Input frame as numpy array
            
        Returns:
            Fully processed image as bytes
        """
        # Step 1: Validate format
        self.validate_image_format(frame)
        
        # Step 2: Normalize channels if needed
        normalized_frame = self.normalize_image_channels(frame, 'BGR')
        
        # Step 3: Resize to fit within limits
        resized_frame = self.resize_image(normalized_frame)
        
        # Step 4: Apply quality optimization
        optimized_bytes = self.optimize_image_quality(resized_frame)
        
        return optimized_bytes

    def normalize_image_channels(self, frame: np.ndarray, input_format: str = 'BGR') -> np.ndarray:
        """
        Normalize image channels for consistent processing.
        
        Args:
            frame: Input frame as numpy array
            input_format: Input color format ('BGR', 'RGB', 'GRAY')
            
        Returns:
            Normalized frame in RGB format
        """
        if input_format == 'BGR':
            # Convert BGR to RGB
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        elif input_format == 'GRAY':
            # Convert grayscale to RGB
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif input_format == 'RGB':
            # Already in RGB format
            return frame
        else:
            raise ValueError(f"Unsupported input format: {input_format}")

    def validate_image_format(self, frame: np.ndarray) -> bool:
        """
        Validate image format for Ollama compatibility.
        
        Args:
            frame: Input frame to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If format is incompatible
        """
        if len(frame.shape) != 3:
            raise ValueError("Frame must be 3-dimensional (H, W, C)")
            
        channels = frame.shape[2]
        if channels != 3:
            if channels == 4:
                raise ValueError("RGBA format not supported, use RGB")
            else:
                raise ValueError(f"Unsupported channel count: {channels}")
                
        return True


class OllamaImageProcessor:
    """
    High-level image processor specifically optimized for Ollama models.
    
    Provides a simplified interface for processing webcam frames with
    Ollama-specific optimizations and performance monitoring.
    """
    
    def __init__(self, config: Optional[ImageProcessingConfig] = None):
        """
        Initialize Ollama-optimized image processor.
        
        Args:
            config: Custom configuration, uses Ollama defaults if None
        """
        # Use Ollama-optimized defaults if no config provided
        if config is None:
            config = ImageProcessingConfig(
                max_width=1024,      # Optimal for Ollama models
                max_height=1024,     # Balanced performance/quality
                quality=ImageQuality.HIGH,  # High quality for vision tasks
                format="JPEG",       # Efficient compression
                maintain_aspect_ratio=True
            )
        
        self.config = config
        self.processor = ImageProcessor(config)
        logger.info(f"OllamaImageProcessor initialized with Ollama-optimized settings")

    def process_webcam_frame(self, frame: np.ndarray) -> str:
        """
        Process webcam frame for Ollama API consumption.
        
        Args:
            frame: Raw webcam frame as numpy array
            
        Returns:
            Base64-encoded image ready for Ollama API
        """
        return self.processor.convert_frame_to_base64(frame)

    def estimate_processing_time(self, frame: np.ndarray) -> float:
        """
        Estimate processing time for performance monitoring.
        
        Args:
            frame: Input frame to analyze
            
        Returns:
            Estimated processing time in seconds
        """
        # Simple estimation based on frame size
        pixels = frame.shape[0] * frame.shape[1]
        
        # Base processing time + size-based scaling
        base_time = 0.01  # 10ms base
        size_factor = pixels / (640 * 480)  # Relative to VGA
        
        estimated_time = base_time * (1 + size_factor * 0.5)
        return estimated_time

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics for monitoring.
        
        Returns:
            Dictionary with processing statistics
        """
        stats = self.processor.stats.copy()
        
        # Calculate derived statistics
        if stats['frames_processed'] > 0:
            stats['average_processing_time'] = (
                stats['total_processing_time'] / stats['frames_processed']
            )
        else:
            stats['average_processing_time'] = 0.0
            
        return stats 