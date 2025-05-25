"""
Multi-modal human detector implementation.

This module implements the HumanDetector interface using both MediaPipe's
pose detection AND face detection for extended range and improved reliability.
Optimized for scenarios requiring detection at various distances (desk to kitchen).
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import List, Tuple, Optional
import logging

from .base import HumanDetector, DetectorConfig, DetectorError
from .result import DetectionResult


logger = logging.getLogger(__name__)


class MultiModalDetector(HumanDetector):
    """
    Multi-modal human detector using pose + face detection.
    
    Combines MediaPipe's pose detection (excellent for close range, full body)
    with face detection (excellent for longer range) to provide comprehensive
    human presence detection across varying distances and scenarios.
    
    Optimized for:
    - Close range: Desk work, detailed pose analysis
    - Medium range: Standing behind chair, partial visibility  
    - Far range: Kitchen/cooking distance, voice interaction
    - Side angles: Partial body visibility scenarios
    """
    
    def __init__(self, config: Optional[DetectorConfig] = None):
        """
        Initialize multi-modal detector.
        
        Args:
            config: Detector configuration, defaults to DetectorConfig()
        """
        super().__init__(config)
        
        # MediaPipe components
        self._mp_pose = None
        self._mp_face = None
        self._pose_detector = None
        self._face_detector = None
        self._initialized = False
        
        # Detection parameters optimized for multi-range scenarios
        self._min_visibility = 0.5
        self._pose_weight = 0.6  # Weight for pose detection in combined confidence
        self._face_weight = 0.4  # Weight for face detection in combined confidence
        
        # Key landmarks for pose confidence calculation
        self._key_landmarks = [
            0,   # NOSE
            11,  # LEFT_SHOULDER 
            12,  # RIGHT_SHOULDER
            23,  # LEFT_HIP
            24,  # RIGHT_HIP
        ]
    
    def initialize(self) -> None:
        """
        Initialize both pose and face detection models.
        
        Raises:
            DetectorError: If MediaPipe initialization fails
        """
        if self._initialized:
            return  # Idempotent initialization
        
        try:
            # Initialize MediaPipe solutions
            self._mp_pose = mp.solutions.pose
            self._mp_face = mp.solutions.face_detection
            
            # Create pose detection instance
            # Optimized for close to medium range, full body detection
            self._pose_detector = self._mp_pose.Pose(
                static_image_mode=self.config.static_image_mode,
                model_complexity=self.config.model_complexity,
                enable_segmentation=self.config.enable_segmentation,
                min_detection_confidence=self.config.min_detection_confidence,
                min_tracking_confidence=self.config.min_tracking_confidence
            )
            
            # Create face detection instance  
            # Use full-range model (model_selection=1) for extended distance detection
            self._face_detector = self._mp_face.FaceDetection(
                model_selection=1,  # Full-range model for extended distance
                min_detection_confidence=self.config.min_detection_confidence
            )
            
            self._initialized = True
            logger.info("Multi-modal detector (pose + face) initialized successfully")
            
        except Exception as e:
            self._initialized = False
            raise DetectorError(
                "Failed to initialize multi-modal detector",
                original_error=e
            )
    
    def cleanup(self) -> None:
        """
        Clean up MediaPipe resources.
        
        Logs errors but does not raise exceptions to ensure cleanup always completes.
        """
        try:
            if self._pose_detector is not None:
                self._pose_detector.close()
                self._pose_detector = None
                
            if self._face_detector is not None:
                self._face_detector.close()
                self._face_detector = None
                
            self._mp_pose = None
            self._mp_face = None
            self._initialized = False
            
            logger.info("Multi-modal detector cleaned up successfully")
            
        except Exception as e:
            # Log error but don't raise - cleanup should always complete
            logger.error(f"Error during multi-modal detector cleanup: {e}")
            self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """
        Check if detector is properly initialized.
        
        Returns:
            True if detector is ready for detection, False otherwise
        """
        return (self._initialized and 
                self._pose_detector is not None and 
                self._face_detector is not None)
    
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Detect human presence using combined pose + face detection.
        
        Args:
            frame: Input frame as numpy array (H, W, C) in BGR format
            
        Returns:
            DetectionResult with combined human presence information
            
        Raises:
            DetectorError: If detection fails or detector not initialized
        """
        if not self.is_initialized:
            raise DetectorError("Detector not initialized. Call initialize() first.")
        
        # Validate frame format
        self._validate_frame(frame)
        
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Run both detectors
            pose_results = self._pose_detector.process(rgb_frame)
            face_results = self._face_detector.process(rgb_frame)
            
            # Process combined results
            return self._process_combined_detection(pose_results, face_results, frame.shape)
                
        except Exception as e:
            raise DetectorError(
                "Multi-modal detection processing failed",
                original_error=e
            )
    
    def _validate_frame(self, frame: np.ndarray) -> None:
        """
        Validate input frame format.
        
        Args:
            frame: Input frame to validate
            
        Raises:
            DetectorError: If frame format is invalid
        """
        if frame is None:
            raise DetectorError("Invalid frame format: frame is None")
        
        if not isinstance(frame, np.ndarray):
            raise DetectorError("Invalid frame format: frame must be numpy array")
        
        if frame.ndim != 3:
            raise DetectorError("Invalid frame format: frame must be 3-dimensional (H, W, C)")
        
        if frame.shape[2] != 3:
            raise DetectorError("Invalid frame format: frame must have 3 channels (BGR)")
        
        if frame.size == 0:
            raise DetectorError("Invalid frame format: frame is empty")
    
    def _process_combined_detection(self, pose_results, face_results, 
                                  frame_shape: Tuple[int, int, int]) -> DetectionResult:
        """
        Process combined pose + face detection results.
        
        Args:
            pose_results: MediaPipe pose detection results
            face_results: MediaPipe face detection results
            frame_shape: Shape of input frame (H, W, C)
            
        Returns:
            DetectionResult with combined analysis
        """
        height, width = frame_shape[:2]
        
        # Analyze pose detection
        pose_detected = pose_results.pose_landmarks is not None
        pose_confidence = 0.0
        pose_landmarks = []
        pose_bbox = None
        
        if pose_detected:
            pose_confidence = self._calculate_pose_confidence(pose_results.pose_landmarks)
            pose_landmarks = self._extract_pose_landmarks(pose_results.pose_landmarks)
            pose_bbox = self._calculate_pose_bounding_box(pose_landmarks, width, height)
        
        # Analyze face detection
        face_detected = (face_results.detections is not None and 
                        len(face_results.detections) > 0)
        face_confidence = 0.0
        face_bbox = None
        
        if face_detected:
            # Use highest confidence face detection
            best_face = max(face_results.detections, key=lambda d: d.score[0])
            face_confidence = best_face.score[0]
            face_bbox = self._extract_face_bounding_box(best_face, width, height)
        
        # Combined decision logic
        human_present = pose_detected or face_detected
        
        # Calculate combined confidence
        if pose_detected and face_detected:
            # Weighted average when both detectors agree
            combined_confidence = (pose_confidence * self._pose_weight + 
                                 face_confidence * self._face_weight)
        elif pose_detected:
            # Only pose detection
            combined_confidence = pose_confidence
        elif face_detected:
            # Only face detection  
            combined_confidence = face_confidence
        else:
            # No detection
            combined_confidence = 0.0
        
        # Determine primary bounding box (prefer pose for full body, face for distance)
        if pose_detected and face_detected:
            # Use pose bbox if confidence is high, otherwise face bbox
            primary_bbox = pose_bbox if pose_confidence > face_confidence else face_bbox
        elif pose_detected:
            primary_bbox = pose_bbox
        elif face_detected:
            primary_bbox = face_bbox
        else:
            primary_bbox = None
        
        # Create detection result
        return DetectionResult(
            human_present=human_present,
            confidence=combined_confidence,
            bounding_box=primary_bbox,
            landmarks=pose_landmarks if pose_landmarks else None
        )
    
    def _calculate_pose_confidence(self, pose_landmarks) -> float:
        """
        Calculate confidence score based on pose landmark visibility.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not pose_landmarks:
            return 0.0
        
        total_visibility = 0.0
        valid_landmarks = 0
        
        for landmark_idx in self._key_landmarks:
            if landmark_idx < len(pose_landmarks.landmark):
                landmark = pose_landmarks.landmark[landmark_idx]
                if landmark.visibility > self._min_visibility:
                    total_visibility += landmark.visibility
                    valid_landmarks += 1
        
        return total_visibility / len(self._key_landmarks) if valid_landmarks > 0 else 0.0
    
    def _extract_pose_landmarks(self, pose_landmarks) -> List[Tuple[float, float]]:
        """
        Extract normalized landmark coordinates.
        
        Args:
            pose_landmarks: MediaPipe pose landmarks
            
        Returns:
            List of (x, y) coordinate tuples, normalized to [0, 1]
        """
        if not pose_landmarks:
            return []
        
        landmarks = []
        for landmark in pose_landmarks.landmark:
            if landmark.visibility > self._min_visibility:
                # Clamp coordinates to valid [0, 1] range to handle MediaPipe edge cases
                x = max(0.0, min(1.0, landmark.x))
                y = max(0.0, min(1.0, landmark.y))
                landmarks.append((x, y))
        
        return landmarks
    
    def _calculate_pose_bounding_box(self, landmarks: List[Tuple[float, float]], 
                                   width: int, height: int) -> Optional[Tuple[int, int, int, int]]:
        """
        Calculate bounding box around pose landmarks.
        
        Args:
            landmarks: List of normalized (x, y) coordinates
            width: Frame width in pixels
            height: Frame height in pixels
            
        Returns:
            Bounding box as (x, y, w, h) or None if no landmarks
        """
        if not landmarks:
            return None
        
        # Convert normalized coordinates to pixel coordinates
        x_coords = [x * width for x, y in landmarks]
        y_coords = [y * height for x, y in landmarks]
        
        # Calculate bounding box with some padding
        min_x = max(0, int(min(x_coords)) - 10)
        max_x = min(width, int(max(x_coords)) + 10)
        min_y = max(0, int(min(y_coords)) - 10)
        max_y = min(height, int(max(y_coords)) + 10)
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
    
    def _extract_face_bounding_box(self, face_detection, width: int, height: int) -> Tuple[int, int, int, int]:
        """
        Extract bounding box from face detection.
        
        Args:
            face_detection: MediaPipe face detection result
            width: Frame width in pixels
            height: Frame height in pixels
            
        Returns:
            Bounding box as (x, y, w, h)
        """
        bbox = face_detection.location_data.relative_bounding_box
        
        # Convert normalized coordinates to pixel coordinates
        x = int(bbox.xmin * width)
        y = int(bbox.ymin * height)
        w = int(bbox.width * width)
        h = int(bbox.height * height)
        
        # Ensure coordinates are within frame bounds
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))
        
        return (x, y, w, h) 