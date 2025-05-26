"""
MediaPipe hands integration for gesture recognition.

Provides hand detection and landmark extraction using MediaPipe hands solution.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Any, List, Tuple, Optional
from .result import HandDetectionResult


class HandDetector:
    """
    Hand detection using MediaPipe hands solution.
    
    Detects hand landmarks and provides utilities for gesture recognition.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize hand detector with MediaPipe hands.
        
        Args:
            config: Configuration dictionary with MediaPipe parameters
            
        Raises:
            ValueError: If configuration values are invalid
        """
        # Configuration with AGGRESSIVE defaults for better detection
        self.max_num_hands = config.get('max_num_hands', 2)
        self.min_detection_confidence = config.get('min_detection_confidence', 0.3)  # LOWERED from 0.7
        self.min_tracking_confidence = config.get('min_tracking_confidence', 0.3)   # LOWERED from 0.5
        self.model_complexity = config.get('model_complexity', 1)
        
        # Validate configuration
        self._validate_config()
        
        # Initialize MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = None
        self._initialized = False
        
        # Initialize MediaPipe hands solution
        self._setup_mediapipe()
    
    def _validate_config(self):
        """Validate configuration parameters."""
        if self.max_num_hands <= 0:
            raise ValueError("max_num_hands must be positive")
        
        if not 0.0 <= self.min_detection_confidence <= 1.0:
            raise ValueError("min_detection_confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= self.min_tracking_confidence <= 1.0:
            raise ValueError("min_tracking_confidence must be between 0.0 and 1.0")
        
        if self.model_complexity not in [0, 1, 2]:
            raise ValueError("model_complexity must be 0, 1, or 2")
    
    def _setup_mediapipe(self):
        """Initialize MediaPipe hands solution."""
        try:
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self.max_num_hands,
                model_complexity=self.model_complexity,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence
            )
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize MediaPipe hands: {e}")
    
    def detect_hands(self, frame: np.ndarray) -> HandDetectionResult:
        """
        Detect hands in the given frame.
        
        Args:
            frame: Input frame (RGB format, shape: H x W x 3)
            
        Returns:
            HandDetectionResult with detection information
            
        Raises:
            ValueError: If frame is invalid
            RuntimeError: If detector is not initialized
        """
        # Input validation
        if frame is None:
            raise ValueError("Frame cannot be None")
        
        if frame.size == 0:
            raise ValueError("Frame cannot be empty")
        
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            raise ValueError("Frame must be 3-channel RGB")
        
        if not self._initialized:
            raise RuntimeError("Hand detector not initialized")
        
        # Process frame with MediaPipe
        try:
            # Convert BGR to RGB if needed (MediaPipe expects RGB)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)
            
            # Parse results
            if results.multi_hand_landmarks:
                return HandDetectionResult(
                    hands_detected=True,
                    num_hands=len(results.multi_hand_landmarks),
                    hand_landmarks=list(results.multi_hand_landmarks),
                    confidence=self._calculate_detection_confidence(results)
                )
            else:
                return HandDetectionResult(
                    hands_detected=False,
                    num_hands=0,
                    hand_landmarks=[],
                    confidence=0.0
                )
                
        except Exception as e:
            # Return no detection on error
            return HandDetectionResult(
                hands_detected=False,
                num_hands=0,
                hand_landmarks=[],
                confidence=0.0
            )
    
    def extract_landmarks(self, hand_landmarks) -> List[Any]:
        """
        Extract landmarks from MediaPipe hand landmarks.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks object
            
        Returns:
            List of 21 landmarks with x, y, z coordinates
        """
        if not hand_landmarks or not hasattr(hand_landmarks, 'landmark'):
            return []
        
        return list(hand_landmarks.landmark)
    
    def calculate_palm_normal(self, hand_landmarks) -> np.ndarray:
        """
        Calculate palm normal vector for orientation detection.
        
        Uses three points on palm to calculate normal vector:
        - Wrist (0)
        - Index finger MCP (5) 
        - Pinky MCP (17)
        
        Args:
            hand_landmarks: MediaPipe hand landmarks object
            
        Returns:
            3D unit normal vector indicating palm orientation
        """
        if not hand_landmarks or not hasattr(hand_landmarks, 'landmark'):
            return np.array([0.0, 0.0, 1.0])  # Default facing camera
        
        landmarks = hand_landmarks.landmark
        
        # Get three points on palm
        wrist = np.array([landmarks[0].x, landmarks[0].y, landmarks[0].z])
        index_mcp = np.array([landmarks[5].x, landmarks[5].y, landmarks[5].z])
        pinky_mcp = np.array([landmarks[17].x, landmarks[17].y, landmarks[17].z])
        
        # Calculate two vectors on palm plane
        v1 = index_mcp - wrist
        v2 = pinky_mcp - wrist
        
        # Calculate normal vector (cross product)
        normal = np.cross(v1, v2)
        
        # Normalize to unit vector
        magnitude = np.linalg.norm(normal)
        if magnitude > 0:
            normal = normal / magnitude
        else:
            normal = np.array([0.0, 0.0, 1.0])  # Default
        
        return normal
    
    def get_hand_center(self, hand_landmarks) -> Tuple[float, float]:
        """
        Get hand center coordinates using middle finger MCP.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks object
            
        Returns:
            (x, y) coordinates of hand center
        """
        if not hand_landmarks or not hasattr(hand_landmarks, 'landmark'):
            return (0.5, 0.5)  # Default center
        
        # Middle finger MCP (landmark 9) is good hand center reference
        middle_mcp = hand_landmarks.landmark[9]
        return (float(middle_mcp.x), float(middle_mcp.y))
    
    def _calculate_detection_confidence(self, results) -> float:
        """
        Calculate overall detection confidence.
        
        Args:
            results: MediaPipe detection results
            
        Returns:
            Average confidence score
        """
        if not results.multi_hand_landmarks:
            return 0.0
        
        # For now, return a default confidence based on number of hands detected
        # In a more sophisticated implementation, this could use hand landmark visibility
        num_hands = len(results.multi_hand_landmarks)
        return min(1.0, 0.7 + (num_hands * 0.1))  # Base 0.7, +0.1 per hand
    
    def _is_initialized(self) -> bool:
        """Check if detector is initialized."""
        return self._initialized and self.hands is not None
    
    def cleanup(self):
        """Release MediaPipe resources."""
        if self.hands is not None:
            self.hands.close()
            self.hands = None
        self._initialized = False 