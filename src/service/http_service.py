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
        
        # Detection history (if enabled)
        self.detection_history: deque = deque(maxlen=config.history_limit) if config.enable_history else None
        
        # Create FastAPI app
        self.app = FastAPI(
            title="Webcam Detection HTTP API",
            description="HTTP API for human presence detection",
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
            return JSONResponse(content={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": time.time() - self.start_time
            })
        
        @self.app.get("/statistics")
        async def get_statistics():
            """Get detection statistics."""
            return JSONResponse(content={
                "total_detections": self.current_status.detection_count,
                "uptime_seconds": self.current_status.uptime_seconds,
                "current_presence": self.current_status.human_present,
                "current_confidence": self.current_status.confidence
            })
        
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
        
        except Exception as e:
            self.logger.error(f"Error handling detection event: {e}")
    
    async def start_server(self) -> None:
        """Start the HTTP server."""
        self.logger.info(f"Starting HTTP API service on {self.config.host}:{self.config.port}")
        
        uvicorn.run(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        ) 