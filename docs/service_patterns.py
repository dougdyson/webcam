"""
Service Integration Patterns for Webcam Human Detection
======================================================

This file contains comprehensive code samples for exposing the human detection
system as a service that other applications can consume. Patterns include:

1. WebSocket Server (Real-time bidirectional communication)
2. Server-Sent Events (SSE) (Real-time server-to-client streaming)
3. Simple HTTP API (REST-like for polling)
4. Background Service Manager (Service lifecycle management)

Use Cases:
- Speaker verification guard clause integration
- Real-time presence monitoring dashboards
- Home automation system integration
- Multi-application presence sharing
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


if __name__ == "__main__":
    # Example usage
    if FASTAPI_AVAILABLE:
        asyncio.run(example_multi_service_setup())
    else:
        print("FastAPI not available. Install with: pip install fastapi uvicorn") 