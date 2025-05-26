"""
Service Integration Patterns for Webcam Human Detection
======================================================

This file contains comprehensive code samples for exposing the human detection
system as a service that other applications can consume. Patterns include:

1. WebSocket Server (Real-time bidirectional communication)
2. Server-Sent Events (SSE) (Real-time server-to-client streaming)
3. Simple HTTP API (REST-like for polling)
4. Background Service Manager (Service lifecycle management)
5. Enhanced Production Service (HTTP + Gesture Recognition + SSE)

RECOMMENDED PRODUCTION SERVICE:
Start with: conda activate webcam && python webcam_enhanced_service.py

Features:
- HTTP API (port 8767): Human presence detection with REST endpoints
- SSE Events (port 8766): Real-time gesture streaming  
- Gesture Recognition: Hand up detection with palm analysis
- Clean Console Output: Single updating status line (no scroll spam)

Console Output Example:
🎥 Frame 1250 | 👤 Human: YES (conf: 0.72) | 🖐️ Gesture: hand_up (conf: 0.95) | FPS: 28.5

Use Cases:
- Speaker verification guard clause integration
- Real-time presence monitoring dashboards
- Home automation system integration
- Multi-application presence sharing
- Voice bot gesture control (hand up to pause/stop)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json
import logging
import weakref
from enum import Enum
import time

# FastAPI and WebSocket imports (external dependencies)
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
    from fastapi.responses import StreamingResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Detection system imports (internal)
from src.detection.result import DetectionResult


# ============================================================================
# Service Event System
# ============================================================================

class EventType(Enum):
    """Types of events that can be published by the detection service."""
    PRESENCE_CHANGED = "presence_changed"
    DETECTION_UPDATE = "detection_update"
    CONFIDENCE_ALERT = "confidence_alert"
    SYSTEM_STATUS = "system_status"
    ERROR_OCCURRED = "error_occurred"
    GESTURE_DETECTED = "gesture_detected"
    GESTURE_LOST = "gesture_lost"
    GESTURE_CONFIDENCE_UPDATE = "gesture_confidence_update"


@dataclass
class ServiceEvent:
    """Event data structure for service communications."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "webcam_detection"
    event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source": self.source,
            "event_id": self.event_id
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


class EventPublisher:
    """Publisher for detection events with multiple subscriber support."""
    
    def __init__(self):
        self._subscribers: List[Callable[[ServiceEvent], None]] = []
        self._async_subscribers: List[Callable[[ServiceEvent], Any]] = []
        self.logger = logging.getLogger(__name__)
    
    def subscribe(self, callback: Callable[[ServiceEvent], None]) -> None:
        """Subscribe to events with synchronous callback."""
        self._subscribers.append(callback)
    
    def subscribe_async(self, callback: Callable[[ServiceEvent], Any]) -> None:
        """Subscribe to events with asynchronous callback."""
        self._async_subscribers.append(callback)
    
    def publish(self, event: ServiceEvent) -> None:
        """Publish event to all subscribers."""
        # Synchronous subscribers
        for callback in self._subscribers:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in sync subscriber: {e}")
        
        # Asynchronous subscribers (run in background)
        for callback in self._async_subscribers:
            try:
                asyncio.create_task(callback(event))
            except Exception as e:
                self.logger.error(f"Error in async subscriber: {e}")


# ============================================================================
# WebSocket Service Implementation
# ============================================================================

class WebSocketConnectionManager:
    """Manages WebSocket connections for real-time detection updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket, client_id: str, 
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_metadata[client_id] = metadata or {}
        self.logger.info(f"WebSocket client connected: {client_id}")
    
    def disconnect(self, client_id: str) -> None:
        """Remove WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_metadata[client_id]
            self.logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def send_to_client(self, client_id: str, event: ServiceEvent) -> bool:
        """Send event to specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(event.to_json())
                return True
            except Exception as e:
                self.logger.error(f"Error sending to client {client_id}: {e}")
                self.disconnect(client_id)
        return False
    
    async def broadcast(self, event: ServiceEvent) -> int:
        """Broadcast event to all connected clients."""
        sent_count = 0
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(event.to_json())
                sent_count += 1
            except Exception as e:
                self.logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
        
        return sent_count


@dataclass
class WebSocketServiceConfig:
    """Configuration for WebSocket service."""
    host: str = "localhost"
    port: int = 8765
    max_connections: int = 100
    heartbeat_interval: float = 30.0
    connection_timeout: float = 60.0


class WebSocketDetectionService:
    """WebSocket service for real-time detection sharing."""
    
    def __init__(self, config: WebSocketServiceConfig):
        self.config = config
        self.app = FastAPI(title="Webcam Detection WebSocket Service")
        self.connection_manager = WebSocketConnectionManager()
        self.event_publisher = EventPublisher()
        self.logger = logging.getLogger(__name__)
        self._setup_routes()
        self._setup_middleware()
    
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
        """Setup WebSocket and HTTP routes."""
        
        @self.app.websocket("/ws/{client_id}")
        async def websocket_endpoint(websocket: WebSocket, client_id: str):
            await self.connection_manager.connect(websocket, client_id)
            try:
                while True:
                    # Keep connection alive and handle client messages
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    await self._handle_client_message(client_id, message)
            except WebSocketDisconnect:
                self.connection_manager.disconnect(client_id)
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "connections": len(self.connection_manager.active_connections),
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/clients")
        async def list_clients():
            return {
                "clients": list(self.connection_manager.active_connections.keys()),
                "count": len(self.connection_manager.active_connections)
            }
    
    async def _handle_client_message(self, client_id: str, message: Dict[str, Any]):
        """Handle messages from WebSocket clients."""
        msg_type = message.get("type")
        
        if msg_type == "ping":
            # Respond to ping with pong
            pong_event = ServiceEvent(
                event_type=EventType.SYSTEM_STATUS,
                data={"type": "pong", "client_id": client_id}
            )
            await self.connection_manager.send_to_client(client_id, pong_event)
        
        elif msg_type == "subscribe":
            # Handle subscription to specific event types
            event_types = message.get("event_types", [])
            metadata = self.connection_manager.connection_metadata[client_id]
            metadata["subscribed_events"] = event_types
            self.logger.info(f"Client {client_id} subscribed to: {event_types}")
    
    def setup_detection_integration(self, event_publisher: EventPublisher):
        """Integrate with detection system event publisher."""
        event_publisher.subscribe_async(self._handle_detection_event)
    
    async def _handle_detection_event(self, event: ServiceEvent):
        """Handle detection events and broadcast to WebSocket clients."""
        await self.connection_manager.broadcast(event)
    
    async def start_server(self):
        """Start the WebSocket server."""
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


# ============================================================================
# Server-Sent Events (SSE) Implementation
# ============================================================================

class SSEConnectionManager:
    """Manages Server-Sent Events connections."""
    
    def __init__(self):
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_stream(self, client_id: str, metadata: Optional[Dict[str, Any]] = None) -> asyncio.Queue:
        """Create new SSE stream for client."""
        queue = asyncio.Queue()
        self.active_streams[client_id] = queue
        self.connection_metadata[client_id] = metadata or {}
        self.logger.info(f"SSE stream created: {client_id}")
        return queue
    
    def close_stream(self, client_id: str):
        """Close SSE stream."""
        if client_id in self.active_streams:
            del self.active_streams[client_id]
            del self.connection_metadata[client_id]
            self.logger.info(f"SSE stream closed: {client_id}")
    
    async def send_to_stream(self, client_id: str, event: ServiceEvent) -> bool:
        """Send event to specific SSE stream."""
        if client_id in self.active_streams:
            try:
                await self.active_streams[client_id].put(event)
                return True
            except Exception as e:
                self.logger.error(f"Error sending to SSE stream {client_id}: {e}")
                self.close_stream(client_id)
        return False
    
    async def broadcast_to_streams(self, event: ServiceEvent) -> int:
        """Broadcast event to all SSE streams."""
        sent_count = 0
        
        for client_id, queue in self.active_streams.items():
            try:
                await queue.put(event)
                sent_count += 1
            except Exception as e:
                self.logger.error(f"Error broadcasting to SSE stream {client_id}: {e}")
        
        return sent_count


@dataclass
class SSEServiceConfig:
    """Configuration for Server-Sent Events service."""
    host: str = "localhost"
    port: int = 8766
    heartbeat_interval: float = 30.0
    max_connections: int = 100


class SSEDetectionService:
    """Server-Sent Events service for real-time detection streaming."""
    
    def __init__(self, config: SSEServiceConfig):
        self.config = config
        self.app = FastAPI(title="Webcam Detection SSE Service")
        self.connection_manager = SSEConnectionManager()
        self.event_publisher = EventPublisher()
        self.logger = logging.getLogger(__name__)
        self._setup_routes()
        self._setup_middleware()
    
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
        """Setup SSE and HTTP routes."""
        
        @self.app.get("/events/{client_id}")
        async def sse_endpoint(client_id: str, request: Request):
            """Server-Sent Events endpoint."""
            queue = self.connection_manager.create_stream(client_id)
            
            async def event_stream():
                try:
                    while True:
                        # Check if client is still connected
                        if await request.is_disconnected():
                            break
                        
                        try:
                            # Wait for event with timeout for heartbeat
                            event = await asyncio.wait_for(
                                queue.get(), 
                                timeout=self.config.heartbeat_interval
                            )
                            yield f"data: {event.to_json()}\\n\\n"
                        except asyncio.TimeoutError:
                            # Send heartbeat
                            heartbeat = ServiceEvent(
                                event_type=EventType.SYSTEM_STATUS,
                                data={"type": "heartbeat"}
                            )
                            yield f"data: {heartbeat.to_json()}\\n\\n"
                        
                except Exception as e:
                    self.logger.error(f"SSE stream error for {client_id}: {e}")
                finally:
                    self.connection_manager.close_stream(client_id)
            
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "active_streams": len(self.connection_manager.active_streams),
                "timestamp": datetime.now().isoformat()
            }
    
    def setup_detection_integration(self, event_publisher: EventPublisher):
        """Integrate with detection system event publisher."""
        event_publisher.subscribe_async(self._handle_detection_event)
    
    async def _handle_detection_event(self, event: ServiceEvent):
        """Handle detection events and broadcast to SSE streams."""
        await self.connection_manager.broadcast_to_streams(event)
    
    async def start_server(self):
        """Start the SSE server."""
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


# ============================================================================
# Simple HTTP API Service
# ============================================================================

@dataclass
class PresenceStatus:
    """Current presence status data."""
    human_present: bool
    confidence: float
    last_detection: datetime
    detection_count: int = 0
    uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "human_present": self.human_present,
            "confidence": self.confidence,
            "last_detection": self.last_detection.isoformat(),
            "detection_count": self.detection_count,
            "uptime_seconds": self.uptime_seconds
        }


@dataclass
class HTTPServiceConfig:
    """Configuration for HTTP API service."""
    host: str = "localhost"
    port: int = 8767
    enable_history: bool = True
    history_limit: int = 1000


class HTTPDetectionService:
    """Simple HTTP API service for presence polling."""
    
    def __init__(self, config: HTTPServiceConfig):
        self.config = config
        self.app = FastAPI(title="Webcam Detection HTTP API")
        self.current_status = PresenceStatus(
            human_present=False,
            confidence=0.0,
            last_detection=datetime.now()
        )
        self.detection_history: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.logger = logging.getLogger(__name__)
        self._setup_routes()
        self._setup_middleware()
    
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
        """Setup HTTP API routes."""
        
        @self.app.get("/presence")
        async def get_presence():
            """Get current presence status."""
            self.current_status.uptime_seconds = (
                datetime.now() - self.start_time
            ).total_seconds()
            return self.current_status.to_dict()
        
        @self.app.get("/presence/simple")
        async def get_simple_presence():
            """Get simple boolean presence status."""
            return {"human_present": self.current_status.human_present}
        
        @self.app.get("/history")
        async def get_detection_history():
            """Get recent detection history."""
            if not self.config.enable_history:
                return {"error": "History not enabled"}
            return {
                "history": self.detection_history,
                "count": len(self.detection_history)
            }
        
        @self.app.get("/statistics")
        async def get_statistics():
            """Get detection statistics."""
            uptime = (datetime.now() - self.start_time).total_seconds()
            return {
                "uptime_seconds": uptime,
                "detection_count": self.current_status.detection_count,
                "current_confidence": self.current_status.confidence,
                "history_size": len(self.detection_history),
                "last_detection": self.current_status.last_detection.isoformat()
            }
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "uptime": (datetime.now() - self.start_time).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
    
    def setup_detection_integration(self, event_publisher: EventPublisher):
        """Integrate with detection system event publisher."""
        event_publisher.subscribe(self._handle_detection_event)
    
    def _handle_detection_event(self, event: ServiceEvent):
        """Handle detection events and update status."""
        if event.event_type == EventType.DETECTION_UPDATE:
            data = event.data
            self.current_status.human_present = data.get("human_present", False)
            self.current_status.confidence = data.get("confidence", 0.0)
            self.current_status.last_detection = event.timestamp
            self.current_status.detection_count += 1
            
            # Add to history if enabled
            if self.config.enable_history:
                history_entry = {
                    "timestamp": event.timestamp.isoformat(),
                    "human_present": self.current_status.human_present,
                    "confidence": self.current_status.confidence
                }
                self.detection_history.append(history_entry)
                
                # Trim history if needed
                if len(self.detection_history) > self.config.history_limit:
                    self.detection_history.pop(0)
    
    async def start_server(self):
        """Start the HTTP API server."""
        config = uvicorn.Config(
            self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


# ============================================================================
# Detection Service Integration
# ============================================================================

class DetectionServiceManager:
    """Manages multiple service types and integrates with detection system."""
    
    def __init__(self):
        self.event_publisher = EventPublisher()
        self.services: Dict[str, Any] = {}
        self.running_services: List[asyncio.Task] = []
        self.logger = logging.getLogger(__name__)
    
    def add_websocket_service(self, config: WebSocketServiceConfig) -> WebSocketDetectionService:
        """Add WebSocket service."""
        service = WebSocketDetectionService(config)
        service.setup_detection_integration(self.event_publisher)
        self.services["websocket"] = service
        return service
    
    def add_sse_service(self, config: SSEServiceConfig) -> SSEDetectionService:
        """Add Server-Sent Events service."""
        service = SSEDetectionService(config)
        service.setup_detection_integration(self.event_publisher)
        self.services["sse"] = service
        return service
    
    def add_http_service(self, config: HTTPServiceConfig) -> HTTPDetectionService:
        """Add HTTP API service."""
        service = HTTPDetectionService(config)
        service.setup_detection_integration(self.event_publisher)
        self.services["http"] = service
        return service
    
    async def start_all_services(self):
        """Start all configured services."""
        for service_name, service in self.services.items():
            self.logger.info(f"Starting {service_name} service...")
            task = asyncio.create_task(service.start_server())
            self.running_services.append(task)
        
        self.logger.info(f"Started {len(self.services)} services")
    
    async def stop_all_services(self):
        """Stop all running services."""
        for task in self.running_services:
            task.cancel()
        
        await asyncio.gather(*self.running_services, return_exceptions=True)
        self.running_services.clear()
        self.logger.info("All services stopped")
    
    def publish_detection_result(self, detection_result: DetectionResult):
        """Publish detection result as service event."""
        event = ServiceEvent(
            event_type=EventType.DETECTION_UPDATE,
            data={
                "human_present": detection_result.human_present,
                "confidence": detection_result.confidence,
                "bounding_box": detection_result.bounding_box,
                "landmarks": detection_result.landmarks,
                "timestamp": detection_result.timestamp.isoformat()
            }
        )
        self.event_publisher.publish(event)
    
    def publish_presence_change(self, human_present: bool, confidence: float):
        """Publish presence state change."""
        event = ServiceEvent(
            event_type=EventType.PRESENCE_CHANGED,
            data={
                "human_present": human_present,
                "confidence": confidence,
                "previous_state": not human_present  # Simple toggle for demo
            }
        )
        self.event_publisher.publish(event)


# ============================================================================
# Usage Examples
# ============================================================================

async def example_websocket_service():
    """Example: WebSocket service setup and usage."""
    config = WebSocketServiceConfig(host="localhost", port=8765)
    service = WebSocketDetectionService(config)
    
    # Would integrate with detection system like this:
    # detection_app.add_detection_callback(service.handle_detection_result)
    
    await service.start_server()


async def example_sse_service():
    """Example: Server-Sent Events service setup."""
    config = SSEServiceConfig(host="localhost", port=8766)
    service = SSEDetectionService(config)
    
    await service.start_server()


async def example_multi_service_setup():
    """Example: Running multiple services simultaneously."""
    manager = DetectionServiceManager()
    
    # Add all service types
    manager.add_websocket_service(WebSocketServiceConfig(port=8765))
    manager.add_sse_service(SSEServiceConfig(port=8766))
    manager.add_http_service(HTTPServiceConfig(port=8767))
    
    # Start all services
    await manager.start_all_services()
    
    # Simulate detection results
    from src.detection.result import DetectionResult
    import time
    
    for i in range(10):
        detection = DetectionResult(
            human_present=i % 2 == 0,
            confidence=0.8 + (i * 0.02),
            bounding_box=[100, 100, 200, 300],
            landmarks=[]
        )
        manager.publish_detection_result(detection)
        await asyncio.sleep(2)
    
    await manager.stop_all_services()


# ============================================================================
# Client Examples (for testing)
# ============================================================================

async def example_websocket_client():
    """Example WebSocket client for testing."""
    import websockets
    
    uri = "ws://localhost:8765/ws/test_client"
    
    async with websockets.connect(uri) as websocket:
        # Send subscription message
        subscribe_msg = {
            "type": "subscribe",
            "event_types": ["presence_changed", "detection_update"]
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        # Listen for events
        while True:
            message = await websocket.recv()
            event_data = json.loads(message)
            print(f"Received: {event_data}")


async def example_sse_client():
    """Example Server-Sent Events client."""
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8766/events/test_client') as resp:
            async for line in resp.content:
                if line.startswith(b'data: '):
                    event_data = json.loads(line[6:])
                    print(f"SSE Received: {event_data}")


def example_http_client():
    """Example HTTP client for polling."""
    import requests
    import time
    
    while True:
        response = requests.get("http://localhost:8767/presence")
        if response.status_code == 200:
            presence_data = response.json()
            print(f"Presence: {presence_data['human_present']} "
                  f"(confidence: {presence_data['confidence']})")
        
        time.sleep(1)  # Poll every second


# ============================================================================
# GESTURE RECOGNITION + SSE INTEGRATION PATTERNS
# ============================================================================

@dataclass
class GestureResult:
    """Result of gesture detection analysis."""
    gesture_detected: bool
    gesture_type: Optional[str] = None  # "hand_up", "hand_down", etc.
    confidence: float = 0.0
    hand: Optional[str] = None  # "left", "right", "both"
    position: Optional[Dict[str, float]] = None
    palm_facing_camera: bool = False
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "gesture_detected": self.gesture_detected,
            "gesture_type": self.gesture_type,
            "confidence": self.confidence,
            "hand": self.hand,
            "position": self.position,
            "palm_facing_camera": self.palm_facing_camera,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat()
        }


class GestureEventPublisher:
    """Enhanced EventPublisher with gesture-specific events."""
    
    def __init__(self):
        self.base_publisher = EventPublisher()
        self.gesture_subscribers: List[Callable[[ServiceEvent], Any]] = []
        
    def subscribe_to_gestures(self, callback: Callable[[ServiceEvent], Any]) -> None:
        """Subscribe specifically to gesture events."""
        def gesture_filter(event: ServiceEvent):
            if event.event_type in [
                EventType.GESTURE_DETECTED,
                EventType.GESTURE_LOST,
                EventType.GESTURE_CONFIDENCE_UPDATE
            ]:
                return callback(event)
        
        self.base_publisher.subscribe_async(gesture_filter)
    
    def publish_gesture_detected(self, gesture_result: GestureResult) -> None:
        """Publish gesture detection event."""
        event = ServiceEvent(
            event_type=EventType.GESTURE_DETECTED,
            data=gesture_result.to_dict()
        )
        self.base_publisher.publish(event)
    
    def publish_gesture_lost(self, last_gesture_type: str, duration_ms: float) -> None:
        """Publish gesture lost event."""
        event = ServiceEvent(
            event_type=EventType.GESTURE_LOST,
            data={
                "last_gesture_type": last_gesture_type,
                "duration_ms": duration_ms
            }
        )
        self.base_publisher.publish(event)


class SSEGestureService:
    """Server-Sent Events service specifically for gesture streaming."""
    
    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.app = FastAPI(title="Gesture Detection SSE Service")
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.client_metadata: Dict[str, Dict] = {}
        self.gesture_publisher = GestureEventPublisher()
        self.logger = logging.getLogger(__name__)
        self._setup_routes()
        self._setup_middleware()
    
    def _setup_middleware(self):
        """Setup CORS for web client access."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup SSE endpoints."""
        
        @self.app.get("/events/gestures/{client_id}")
        async def gesture_stream(client_id: str, request: Request):
            """Main SSE endpoint for gesture events."""
            
            # Create client stream
            event_queue = asyncio.Queue(maxsize=100)
            self.active_streams[client_id] = event_queue
            self.client_metadata[client_id] = {
                "connected_at": datetime.now(),
                "events_sent": 0
            }
            
            self.logger.info(f"SSE client connected: {client_id}")
            
            async def event_stream():
                try:
                    # Send initial connection event
                    yield self._format_sse_event("connected", {
                        "client_id": client_id,
                        "timestamp": datetime.now().isoformat(),
                        "service": "gesture_detection"
                    })
                    
                    # Send heartbeat every 30 seconds
                    last_heartbeat = time.time()
                    
                    while True:
                        try:
                            # Check for client disconnect
                            if await request.is_disconnected():
                                break
                            
                            # Send heartbeat if needed
                            current_time = time.time()
                            if current_time - last_heartbeat > 30:
                                yield self._format_sse_event("heartbeat", {
                                    "timestamp": datetime.now().isoformat()
                                })
                                last_heartbeat = current_time
                            
                            # Wait for events with timeout
                            try:
                                event_data = await asyncio.wait_for(
                                    event_queue.get(), timeout=1.0
                                )
                                yield self._format_sse_event(
                                    event_data["event_type"],
                                    event_data["data"]
                                )
                                self.client_metadata[client_id]["events_sent"] += 1
                                
                            except asyncio.TimeoutError:
                                # No events, continue loop for heartbeat check
                                continue
                                
                        except Exception as e:
                            self.logger.error(f"Error in event stream for {client_id}: {e}")
                            break
                            
                except Exception as e:
                    self.logger.error(f"SSE stream error for {client_id}: {e}")
                    
                finally:
                    # Cleanup
                    if client_id in self.active_streams:
                        del self.active_streams[client_id]
                    if client_id in self.client_metadata:
                        del self.client_metadata[client_id]
                    self.logger.info(f"SSE client disconnected: {client_id}")
            
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "gesture_sse",
                "active_connections": len(self.active_streams),
                "uptime": time.time()
            }
        
        @self.app.get("/clients")
        async def list_clients():
            """List active SSE clients."""
            return {
                "active_clients": len(self.active_streams),
                "clients": {
                    client_id: {
                        "connected_at": metadata["connected_at"].isoformat(),
                        "events_sent": metadata["events_sent"]
                    }
                    for client_id, metadata in self.client_metadata.items()
                }
            }
    
    def _format_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format data as Server-Sent Event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    def setup_gesture_integration(self, gesture_publisher: GestureEventPublisher):
        """Connect to gesture detection events."""
        gesture_publisher.subscribe_to_gestures(self._handle_gesture_event)
    
    async def _handle_gesture_event(self, event: ServiceEvent):
        """Handle incoming gesture events and broadcast to SSE clients."""
        if not self.active_streams:
            return  # No clients connected
        
        event_data = {
            "event_type": event.event_type.value,
            "data": event.data,
            "timestamp": event.timestamp.isoformat()
        }
        
        # Broadcast to all connected clients
        disconnected_clients = []
        for client_id, event_queue in self.active_streams.items():
            try:
                if event_queue.full():
                    # Remove oldest event to make room
                    try:
                        event_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                
                event_queue.put_nowait(event_data)
                
            except Exception as e:
                self.logger.error(f"Error sending to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Cleanup disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.active_streams:
                del self.active_streams[client_id]
            if client_id in self.client_metadata:
                del self.client_metadata[client_id]
    
    async def start_server(self):
        """Start the SSE service."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


# ============================================================================
# EXAMPLE USAGE PATTERNS
# ============================================================================

async def example_gesture_sse_service():
    """Example of setting up gesture detection with SSE streaming."""
    
    # 1. Setup gesture detection (mock)
    gesture_publisher = GestureEventPublisher()
    
    # 2. Setup SSE service
    sse_service = SSEGestureService(host="localhost", port=8766)
    sse_service.setup_gesture_integration(gesture_publisher)
    
    # 3. Simulate gesture detection events
    async def simulate_gestures():
        await asyncio.sleep(2)  # Wait for service to start
        
        # Simulate hand up gesture
        gesture_result = GestureResult(
            gesture_detected=True,
            gesture_type="hand_up",
            confidence=0.85,
            hand="right",
            palm_facing_camera=True,
            duration_ms=1500
        )
        gesture_publisher.publish_gesture_detected(gesture_result)
        
        await asyncio.sleep(3)
        
        # Simulate gesture lost
        gesture_publisher.publish_gesture_lost("hand_up", 1500)
    
    # 4. Run service and simulation
    await asyncio.gather(
        sse_service.start_server(),
        simulate_gestures()
    )


def example_sse_client_javascript():
    """JavaScript client example for SSE gesture events."""
    
    js_code = """
    // JavaScript SSE client for gesture events
    class GestureSSEClient {
        constructor(clientId = 'web_dashboard') {
            this.clientId = clientId;
            this.url = `http://localhost:8766/events/gestures/${clientId}`;
            this.eventSource = null;
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;
        }
        
        connect() {
            this.eventSource = new EventSource(this.url);
            
            this.eventSource.onopen = (event) => {
                console.log('Connected to gesture SSE stream');
                this.reconnectAttempts = 0;
            };
            
            this.eventSource.addEventListener('connected', (event) => {
                const data = JSON.parse(event.data);
                console.log('SSE connection established:', data);
            });
            
            this.eventSource.addEventListener('gesture_detected', (event) => {
                const data = JSON.parse(event.data);
                this.handleGestureDetected(data);
            });
            
            this.eventSource.addEventListener('gesture_lost', (event) => {
                const data = JSON.parse(event.data);
                this.handleGestureLost(data);
            });
            
            this.eventSource.addEventListener('heartbeat', (event) => {
                console.log('Heartbeat received');
            });
            
            this.eventSource.onerror = (event) => {
                console.error('SSE connection error:', event);
                this.handleReconnect();
            };
        }
        
        handleGestureDetected(data) {
            console.log('Gesture detected:', data);
            
            // Update UI
            const gestureDisplay = document.getElementById('gesture-status');
            if (gestureDisplay) {
                gestureDisplay.textContent = `Gesture: ${data.gesture_type} (${data.confidence})`;
                gestureDisplay.className = 'gesture-active';
            }
            
            // Trigger custom events
            window.dispatchEvent(new CustomEvent('gestureDetected', {
                detail: data
            }));
        }
        
        handleGestureLost(data) {
            console.log('Gesture lost:', data);
            
            // Update UI
            const gestureDisplay = document.getElementById('gesture-status');
            if (gestureDisplay) {
                gestureDisplay.textContent = 'No gesture';
                gestureDisplay.className = 'gesture-inactive';
            }
            
            // Trigger custom events
            window.dispatchEvent(new CustomEvent('gestureLost', {
                detail: data
            }));
        }
        
        handleReconnect() {
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff
                
                console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
                
                setTimeout(() => {
                    this.disconnect();
                    this.connect();
                }, delay);
            } else {
                console.error('Max reconnection attempts reached');
            }
        }
        
        disconnect() {
            if (this.eventSource) {
                this.eventSource.close();
                this.eventSource = null;
            }
        }
    }
    
    // Usage
    const gestureClient = new GestureSSEClient('dashboard_001');
    gestureClient.connect();
    
    // Listen for custom gesture events
    window.addEventListener('gestureDetected', (event) => {
        console.log('Custom gesture event:', event.detail);
        // Your application logic here
    });
    """
    
    return js_code


def example_python_sse_client():
    """Python client example for testing SSE gesture events."""
    
    python_code = """
    import requests
    import json
    import time
    from typing import Iterator
    
    class GestureSSEClient:
        def __init__(self, client_id: str = "python_client"):
            self.client_id = client_id
            self.url = f"http://localhost:8766/events/gestures/{client_id}"
            
        def connect(self) -> Iterator[dict]:
            \"""Connect to SSE stream and yield events.\"""
            try:
                response = requests.get(
                    self.url,
                    stream=True,
                    headers={'Accept': 'text/event-stream'},
                    timeout=(10, None)  # 10s connect, no read timeout
                )
                response.raise_for_status()
                
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        if line.startswith('event:'):
                            event_type = line[6:].strip()
                        elif line.startswith('data:'):
                            try:
                                data = json.loads(line[5:].strip())
                                yield {
                                    'event_type': event_type,
                                    'data': data
                                }
                            except json.JSONDecodeError:
                                continue
                                
            except requests.exceptions.RequestException as e:
                print(f"SSE connection error: {e}")
                
        def test_connection(self):
            \"""Test SSE connection and print events.\"""
            print(f"Connecting to {self.url}")
            
            for event in self.connect():
                print(f"Event: {event['event_type']}")
                print(f"Data: {event['data']}")
                print("-" * 40)
                
                if event['event_type'] == 'gesture_detected':
                    self.handle_gesture_detected(event['data'])
                elif event['event_type'] == 'gesture_lost':
                    self.handle_gesture_lost(event['data'])
                    
        def handle_gesture_detected(self, data: dict):
            \"""Handle gesture detection event.\"""
            gesture_type = data.get('gesture_type', 'unknown')
            confidence = data.get('confidence', 0)
            hand = data.get('hand', 'unknown')
            
            print(f"🖐️  Gesture detected: {gesture_type} ({hand} hand, {confidence:.2f} confidence)")
            
        def handle_gesture_lost(self, data: dict):
            \"""Handle gesture lost event.\"""
            duration = data.get('duration_ms', 0)
            print(f"👋 Gesture ended (duration: {duration}ms)")
    
    # Usage
    if __name__ == "__main__":
        client = GestureSSEClient("test_client_001")
        client.test_connection()
    """
    
    return python_code


def example_production_integration():
    """Example of production-ready gesture + SSE integration."""
    
    class ProductionGestureService:
        """Production-ready gesture detection with SSE streaming."""
        
        def __init__(self):
            self.gesture_publisher = GestureEventPublisher()
            self.sse_service = SSEGestureService()
            self.http_service = None  # Existing HTTP service
            self.logger = logging.getLogger(__name__)
            
        async def start_services(self):
            """Start all services simultaneously."""
            
            # Connect SSE to gesture events
            self.sse_service.setup_gesture_integration(self.gesture_publisher)
            
            # Start services concurrently
            await asyncio.gather(
                self.sse_service.start_server(),
                self.run_gesture_detection(),
                return_exceptions=True
            )
            
        async def run_gesture_detection(self):
            """Mock gesture detection loop."""
            while True:
                try:
                    # In real implementation, this would be connected to:
                    # - Camera frame processing
                    # - MediaPipe hands detection
                    # - Gesture classification
                    
                    await asyncio.sleep(2)
                    
                    # Simulate gesture detection
                    if time.time() % 10 < 5:  # 50% of the time
                        gesture_result = GestureResult(
                            gesture_detected=True,
                            gesture_type="hand_up",
                            confidence=0.8 + (time.time() % 1) * 0.2,
                            hand="right",
                            palm_facing_camera=True,
                            duration_ms=2000
                        )
                        self.gesture_publisher.publish_gesture_detected(gesture_result)
                    else:
                        self.gesture_publisher.publish_gesture_lost("hand_up", 2000)
                        
                except Exception as e:
                    self.logger.error(f"Error in gesture detection: {e}")
                    await asyncio.sleep(1)
    
    return ProductionGestureService


if __name__ == "__main__":
    print("Gesture + SSE Service Patterns")
    print("1. Run example gesture SSE service")
    print("2. Show JavaScript client code")
    print("3. Show Python client code")
    print("4. Run production integration example")
    
    choice = input("Enter choice (1-4): ")
    
    if choice == "1":
        asyncio.run(example_gesture_sse_service())
    elif choice == "2":
        print(example_sse_client_javascript())
    elif choice == "3":
        print(example_python_sse_client())
    elif choice == "4":
        service = example_production_integration()
        asyncio.run(service.start_services())
    else:
        print("Invalid choice") 