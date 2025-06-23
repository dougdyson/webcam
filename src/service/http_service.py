"""
HTTP API service for webcam human detection.

Provides REST endpoints for simple presence detection integration,
particularly for speaker verification guard clauses.
"""
import logging
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import deque

from .events import ServiceEvent, EventType, EventPublisher

# FastAPI imports with graceful fallback
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = None
    JSONResponse = None
    CORSMiddleware = None
    uvicorn = None


class HTTPServiceError(Exception):
    """Exception for HTTP service errors."""
    pass


@dataclass
class HTTPServiceConfig:
    """Configuration for HTTP API service."""
    host: str = "localhost"
    port: int = 8767
    enable_history: bool = True
    history_limit: int = 1000
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not (1 <= self.port <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {self.port}")
        
        if self.history_limit <= 0:
            raise ValueError(f"History limit must be positive, got {self.history_limit}")


@dataclass
class PresenceStatus:
    """Current presence status data."""
    human_present: bool
    confidence: float
    last_detection: datetime
    detection_count: int = 0
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary for JSON response."""
        # Handle both datetime and float timestamp values
        if isinstance(self.last_detection, datetime):
            last_detection_str = self.last_detection.isoformat()
        elif isinstance(self.last_detection, (int, float)):
            last_detection_str = datetime.fromtimestamp(self.last_detection).isoformat()
        else:
            last_detection_str = datetime.now().isoformat()
            
        return {
            "human_present": self.human_present,
            "confidence": self.confidence,
            "last_detection": last_detection_str,
            "detection_count": self.detection_count,
            "uptime_seconds": self.uptime_seconds
        }


class HTTPDetectionService:
    """
    HTTP API service for webcam human detection.
    
    Provides REST endpoints for presence detection, particularly
    optimized for speaker verification guard clause integration.
    """
    
    def __init__(self, config: HTTPServiceConfig):
        """Initialize HTTP detection service."""
        if not FASTAPI_AVAILABLE:
            raise HTTPServiceError("FastAPI is required for HTTP service. Install with: pip install fastapi uvicorn")
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        
        # Initialize presence status
        self.current_status = PresenceStatus(
            human_present=False,
            confidence=0.0,
            last_detection=datetime.now()
        )
        
        # Initialize as running by default
        self._running = True
        self._event_publisher_subscribed = False
        
        # Detection history (if enabled)
        self.detection_history: deque = deque(maxlen=config.history_limit) if config.enable_history else None
        
        # NEW: Description service integration for Phase 4.1
        self._description_service = None
        
        # NEW: Gesture tracking for MediaPipe integration
        self.current_gesture_status = {
            "gesture_detected": False,
            "gesture_type": "None",
            "confidence": 0.0,
            "handedness": None,
            "last_gesture_time": None,
            "last_gesture_lost_time": None
        }
        
        # NEW: Description metrics tracking for Phase 4.2
        self._description_stats = {
            'total_descriptions': 0,
            'successful_descriptions': 0,
            'failed_descriptions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_processing_time_ms': 0.0,
            'total_processing_time_ms': 0
        }
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Webcam Detection HTTP API",
            description="HTTP API for human presence detection and AI descriptions",
            version="1.0.0"
        )
        
        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup CORS and other middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/presence")
        async def get_presence():
            """Get full presence status with all details."""
            # Use stored uptime_seconds from current_status
            return JSONResponse(content=self.current_status.to_dict())
        
        @self.app.get("/presence/simple")
        async def get_simple_presence():
            """Get simple boolean presence status (optimized for guard clauses)."""
            return JSONResponse(content={"human_present": self.current_status.human_present})
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time() - self.start_time
            }
            
            # Add description service health if available
            if self._description_service is not None:
                # Check if description service is functioning
                try:
                    # Simple availability check
                    if hasattr(self._description_service, 'ollama_client'):
                        client = self._description_service.ollama_client
                        is_available = getattr(client, 'is_available', lambda: True)()
                        
                        health_data["description_service"] = {
                            "available": is_available,
                            "status": "healthy" if is_available else "degraded",
                            "total_descriptions": self._description_stats.get('total_descriptions', 0),
                            "processing_errors": self._description_stats.get('failed_descriptions', 0)
                        }
                    else:
                        health_data["description_service"] = {
                            "available": True,
                            "status": "healthy",
                            "total_descriptions": self._description_stats.get('total_descriptions', 0),
                            "processing_errors": self._description_stats.get('failed_descriptions', 0)
                        }
                except Exception as e:
                    health_data["description_service"] = {
                        "available": False,
                        "status": "error",
                        "error": str(e),
                        "total_descriptions": self._description_stats.get('total_descriptions', 0),
                        "processing_errors": self._description_stats.get('failed_descriptions', 0)
                    }
            
            return JSONResponse(content=health_data)
        
        @self.app.get("/statistics")
        async def get_statistics():
            """Get detection statistics."""
            stats = {
                "total_detections": self.current_status.detection_count,
                "uptime_seconds": self.current_status.uptime_seconds,
                "current_presence": self.current_status.human_present,
                "current_confidence": self.current_status.confidence
            }
            
            # Add description statistics if description service is available
            if self._description_service is not None:
                # Calculate cache hit rate
                cache_hit_rate = 0.0
                total_cache_attempts = self._description_stats['cache_hits'] + self._description_stats['cache_misses']
                if total_cache_attempts > 0:
                    cache_hit_rate = self._description_stats['cache_hits'] / total_cache_attempts
                
                stats["description_stats"] = {
                    "total_descriptions": self._description_stats['total_descriptions'],
                    "successful_descriptions": self._description_stats['successful_descriptions'],
                    "failed_descriptions": self._description_stats['failed_descriptions'],
                    "processing_errors": self._description_stats['failed_descriptions'],  # Add processing_errors alias
                    "cache_hits": self._description_stats['cache_hits'],
                    "cache_misses": self._description_stats['cache_misses'],
                    "cache_hit_rate": round(cache_hit_rate, 3),
                    "average_processing_time_ms": round(self._description_stats['average_processing_time_ms'], 1)
                }
            
            return JSONResponse(content=stats)
        
        @self.app.get("/description/latest")
        async def get_latest_description():
            """Get latest AI description of the scene."""
            if self._description_service is None:
                raise HTTPException(status_code=503, detail="Description service not available")
            
            try:
                # Get latest description from the service
                latest_description = self._description_service.get_latest_description()
                
                if latest_description is None:
                    return JSONResponse(content={
                        "description": None,
                        "confidence": 0.0,
                        "timestamp": None,
                        "cached": False,
                        "status": "no_description"
                    })
                
                # Convert DescriptionResult to dictionary using its to_dict() method
                response_data = latest_description.to_dict()
                response_data["status"] = "available"
                
                return JSONResponse(content=response_data)
                
            except Exception as e:
                self.logger.error(f"Error getting latest description: {e}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "description": None,
                        "confidence": 0.0,
                        "timestamp": None,
                        "cached": False,
                        "status": "error",
                        "error": str(e)
                    }
                )
        
        # NEW: Gesture endpoints for MediaPipe integration
        @self.app.get("/gesture/latest")
        async def get_latest_gesture():
            """Get latest gesture status."""
            return JSONResponse(content=self.current_gesture_status.copy())
        
        @self.app.get("/gesture/status")
        async def get_gesture_status():
            """Get current gesture status (alias for /gesture/latest)."""
            return JSONResponse(content=self.current_gesture_status.copy())
        
        if self.config.enable_history:
            @self.app.get("/history")
            async def get_detection_history():
                """Get detection history."""
                return JSONResponse(content={"history": list(self.detection_history)})
        else:
            @self.app.get("/history")
            async def get_detection_history():
                """History endpoint when disabled."""
                raise HTTPException(status_code=404, detail="History not enabled")
    
    def setup_detection_integration(self, event_publisher: EventPublisher) -> None:
        """Setup integration with detection event publisher."""
        event_publisher.subscribe(self._handle_detection_event)
        self._event_publisher_subscribed = True
    
    def setup_description_integration(self, description_service) -> None:
        """Setup integration with Ollama description service."""
        self._description_service = description_service
        self.logger.info("Description service integrated with HTTP API")
    
    @property
    def description_service(self):
        """Get the description service instance."""
        return self._description_service
    
    def _handle_detection_event(self, event: ServiceEvent) -> None:
        """Handle detection events from the detection system."""
        try:
            if event.event_type in [EventType.PRESENCE_CHANGED, EventType.DETECTION_UPDATE]:
                data = event.data
                
                # Update current status
                if "human_present" in data:
                    self.current_status.human_present = data["human_present"]
                
                if "confidence" in data:
                    self.current_status.confidence = data["confidence"]
                
                self.current_status.last_detection = event.timestamp
                self.current_status.detection_count += 1
                self.current_status.uptime_seconds = time.time() - self.start_time
                
                # Add to history if enabled
                if self.detection_history is not None:
                    self.detection_history.append({
                        "timestamp": event.timestamp.isoformat(),
                        "human_present": self.current_status.human_present,
                        "confidence": self.current_status.confidence,
                        "event_type": event.event_type.value
                    })
                
                self.logger.debug(f"Updated presence status: {self.current_status.human_present}")
            
            # NEW: Handle gesture events for MediaPipe integration
            elif event.event_type == EventType.GESTURE_DETECTED:
                self._handle_gesture_detected_event(event)
            elif event.event_type == EventType.GESTURE_LOST:
                self._handle_gesture_lost_event(event)
            elif event.event_type == EventType.GESTURE_CONFIDENCE_UPDATE:
                self._handle_gesture_confidence_update_event(event)
            
            # NEW: Handle description events for Phase 4.2
            elif event.event_type in [EventType.DESCRIPTION_GENERATED, EventType.DESCRIPTION_FAILED, EventType.DESCRIPTION_CACHED]:
                self._handle_description_events(event)
        
        except Exception as e:
            self.logger.error(f"Error handling detection event: {e}")
    
    def _handle_gesture_detected_event(self, event: ServiceEvent) -> None:
        """Handle gesture detected events."""
        try:
            data = event.data
            self.current_gesture_status.update({
                "gesture_detected": True,
                "gesture_type": data.get("gesture_type", "None"),
                "confidence": data.get("confidence", 0.0),
                "handedness": data.get("handedness", data.get("hand")),  # Support both keys
                "last_gesture_time": event.timestamp.isoformat()
            })
            self.logger.debug(f"Gesture detected: {data.get('gesture_type')}")
        except Exception as e:
            self.logger.error(f"Error handling gesture detected event: {e}")
    
    def _handle_gesture_lost_event(self, event: ServiceEvent) -> None:
        """Handle gesture lost events."""
        try:
            data = event.data
            self.current_gesture_status.update({
                "gesture_detected": False,
                "gesture_type": "None",
                "confidence": 0.0,
                "handedness": None,
                "last_gesture_lost_time": event.timestamp.isoformat()
            })
            self.logger.debug(f"Gesture lost: {data.get('gesture_type', 'unknown')}")
        except Exception as e:
            self.logger.error(f"Error handling gesture lost event: {e}")
    
    def _handle_gesture_confidence_update_event(self, event: ServiceEvent) -> None:
        """Handle gesture confidence update events."""
        try:
            data = event.data
            if self.current_gesture_status["gesture_detected"]:
                self.current_gesture_status["confidence"] = data.get("confidence", 0.0)
                self.logger.debug(f"Gesture confidence updated: {data.get('confidence')}")
        except Exception as e:
            self.logger.error(f"Error handling gesture confidence update event: {e}")
    
    def _handle_description_events(self, event: ServiceEvent) -> None:
        """Handle description-related events and update metrics."""
        try:
            data = event.data
            
            if event.event_type == EventType.DESCRIPTION_GENERATED:
                # Update metrics for successful description
                self._description_stats['total_descriptions'] += 1
                self._description_stats['successful_descriptions'] += 1
                
                # Update processing time averages
                processing_time = data.get('processing_time_ms', 0)
                if processing_time > 0:
                    total_time = self._description_stats['total_processing_time_ms'] + processing_time
                    total_descriptions = self._description_stats['successful_descriptions']
                    self._description_stats['average_processing_time_ms'] = total_time / total_descriptions
                    self._description_stats['total_processing_time_ms'] = total_time
                
                # Track cache status
                if data.get('cached', False):
                    self._description_stats['cache_hits'] += 1
                else:
                    self._description_stats['cache_misses'] += 1
                
                self.logger.debug(f"Description generated: cached={data.get('cached', False)}")
            
            elif event.event_type == EventType.DESCRIPTION_FAILED:
                # Update failure metrics
                self._description_stats['total_descriptions'] += 1
                self._description_stats['failed_descriptions'] += 1
                
                self.logger.debug(f"Description failed: {data.get('error', 'Unknown error')}")
            
            elif event.event_type == EventType.DESCRIPTION_CACHED:
                # Track cache hits
                self._description_stats['cache_hits'] += 1
                
                self.logger.debug("Description served from cache")
        
        except Exception as e:
            self.logger.error(f"Error handling description event: {e}")
    
    async def start_server(self) -> None:
        """Start the HTTP server."""
        self.logger.info(f"Starting HTTP API service on {self.config.host}:{self.config.port}")
        
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        ) 
    
    # PRODUCTION INTEGRATION METHODS FOR PHASE 16.3
    
    def setup_event_integration(self, event_publisher: EventPublisher) -> None:
        """Setup integration with event publisher (alias for setup_detection_integration)."""
        self.setup_detection_integration(event_publisher)
    
    async def startup_with_validation(self) -> Dict[str, Any]:
        """Start up service with validation and return startup result."""
        import time
        start_time = time.time()
        
        try:
            # Validate configuration
            if not (1 <= self.config.port <= 65535):
                return {
                    "success": False,
                    "error": f"Invalid port: {self.config.port}",
                    "startup_time": time.time() - start_time
                }
            
            # Mark as running
            self._running = True
            
            return {
                "success": True,
                "startup_time": time.time() - start_time,
                "host": self.config.host,
                "port": self.config.port
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "startup_time": time.time() - start_time
            }
    
    async def graceful_shutdown_with_cleanup(self) -> Dict[str, Any]:
        """Gracefully shutdown service with cleanup."""
        import time
        shutdown_start = time.time()
        
        try:
            # Mark as not running
            self._running = False
            
            # Clear detection history if enabled
            if self.detection_history is not None:
                self.detection_history.clear()
            
            return {
                "success": True,
                "cleanup_completed": True,
                "shutdown_time": time.time() - shutdown_start
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "cleanup_completed": False,
                "shutdown_time": time.time() - shutdown_start
            }
    
    def is_subscribed_to_events(self) -> bool:
        """Check if service is subscribed to events."""
        # Check if we have an event handler setup
        return hasattr(self, '_event_publisher_subscribed') and self._event_publisher_subscribed
    
    def is_running(self) -> bool:
        """Check if service is running."""
        return getattr(self, '_running', False)
    
    def get_current_presence_status(self) -> PresenceStatus:
        """Get current presence status object."""
        return self.current_status
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        return {
            "status": "healthy" if self.is_running() else "stopped",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - self.start_time,
            "configuration": {
                "host": self.config.host,
                "port": self.config.port,
                "history_enabled": self.config.enable_history
            }
        } 