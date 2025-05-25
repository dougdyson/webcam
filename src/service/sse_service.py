"""
SSE (Server-Sent Events) service for real-time gesture event streaming.

Provides Server-Sent Events service on port 8766 for streaming gesture events
to web dashboards and other real-time applications.
"""

import asyncio
import logging
import json
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .events import EventPublisher, ServiceEvent, EventType


@dataclass
class SSEServiceConfig:
    """Configuration for SSE service."""
    host: str = "localhost"
    port: int = 8766
    max_connections: int = 20
    heartbeat_interval: float = 30.0
    connection_timeout: float = 60.0
    
    # NEW: Event filtering configuration
    gesture_events_only: bool = True
    include_confidence_updates: bool = True
    min_gesture_confidence: float = 0.6
    
    def __post_init__(self):
        """Validate configuration values."""
        if not 0.0 <= self.min_gesture_confidence <= 1.0:
            raise ValueError("min_gesture_confidence must be between 0.0 and 1.0")
        if self.max_connections <= 0:
            raise ValueError("max_connections must be positive")
        if self.heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be positive")


class SSEDetectionService:
    """
    Server-Sent Events service for real-time gesture event streaming.
    
    Provides SSE endpoints for streaming gesture events to web clients
    with connection management, heartbeat, and CORS support.
    """
    
    def __init__(self, config: Optional[SSEServiceConfig] = None):
        """Initialize SSE service."""
        self.config = config or SSEServiceConfig()
        self.app = FastAPI(title="SSE Detection Service")
        self.active_connections: Dict[str, asyncio.Queue] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
        # NEW: Event Publisher integration
        self._event_publisher = None
        self._subscription_id = None
        self._subscribed_to_events = False
        
        # Service state
        self.start_time: Optional[datetime] = None
        self._running = False
        self.logger = logging.getLogger(__name__)
        
        self._setup_cors()
        self._setup_routes()
        self._setup_health_endpoints()
    
    def _setup_cors(self):
        """Setup CORS middleware for web dashboard integration."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["GET"],
            allow_headers=["*"],
            allow_credentials=True
        )
        # Store CORS info for inspection
        self._cors_configured = True
    
    def _setup_routes(self):
        """Setup SSE routes."""
        
        @self.app.get("/events/gestures/{client_id}")
        async def gesture_events_stream(client_id: str, request: Request):
            """SSE endpoint for gesture event streaming."""
            return await self._handle_sse_connection(client_id, request)
    
    async def _handle_sse_connection(self, client_id: str, request: Request) -> StreamingResponse:
        """Handle SSE connection for a client."""
        # Add client connection
        await self.add_client_connection(client_id)
        
        # Start heartbeat
        await self.start_heartbeat(client_id)
        
        try:
            # Create event generator
            event_stream = self._generate_events(client_id, request)
            
            # Return streaming response with SSE headers
            return StreamingResponse(
                event_stream,
                media_type="text/event-stream",
                headers=self.get_sse_headers()
            )
        except Exception as e:
            self.logger.error(f"Error handling SSE connection for {client_id}: {e}")
            await self.remove_client_connection(client_id)
            raise HTTPException(status_code=500, detail="SSE connection error")
    
    async def _generate_events(self, client_id: str, request: Request):
        """Generate SSE events for a client."""
        queue = self.active_connections.get(client_id)
        if not queue:
            return
        
        try:
            while True:
                # Check if client is still connected
                if await request.is_disconnected():
                    await self.handle_client_disconnection(client_id)
                    break
                
                try:
                    # Wait for event or timeout
                    event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event_data
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield "data: keepalive\n\n"
                except Exception as e:
                    self.logger.error(f"Error generating events for {client_id}: {e}")
                    break
        finally:
            await self.remove_client_connection(client_id)
    
    async def add_client_connection(self, client_id: str) -> None:
        """Add a client connection."""
        if len(self.active_connections) >= self.config.max_connections:
            raise HTTPException(status_code=429, detail="Too many connections")
        
        self.active_connections[client_id] = asyncio.Queue()
        self.logger.info(f"Added SSE client connection: {client_id}")
    
    async def remove_client_connection(self, client_id: str) -> None:
        """Remove a client connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Stop heartbeat if running
        await self.stop_heartbeat(client_id)
        
        self.logger.info(f"Removed SSE client connection: {client_id}")
    
    async def is_client_connected(self, client_id: str, request: Request) -> bool:
        """Check if client is still connected."""
        if client_id not in self.active_connections:
            return False
        
        return not await request.is_disconnected()
    
    async def handle_client_disconnection(self, client_id: str) -> None:
        """Handle client disconnection cleanup."""
        await self.remove_client_connection(client_id)
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_sse_headers(self) -> Dict[str, str]:
        """Get SSE response headers."""
        return {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "allow_origins": ["*"],
            "allow_methods": ["GET"],
            "allow_headers": ["*"]
        }
    
    async def start_heartbeat(self, client_id: str) -> None:
        """Start heartbeat for a client."""
        # Ensure client connection exists
        if client_id not in self.active_connections:
            self.active_connections[client_id] = asyncio.Queue()
        
        async def heartbeat_task():
            while client_id in self.active_connections:
                try:
                    await asyncio.sleep(self.config.heartbeat_interval)
                    if client_id in self.active_connections:
                        queue = self.active_connections[client_id]
                        await queue.put("data: heartbeat\n\n")
                except Exception as e:
                    self.logger.error(f"Heartbeat error for {client_id}: {e}")
                    break
        
        if client_id not in self.heartbeat_tasks:
            task = asyncio.create_task(heartbeat_task())
            self.heartbeat_tasks[client_id] = task
    
    async def stop_heartbeat(self, client_id: str) -> None:
        """Stop heartbeat for a client."""
        if client_id in self.heartbeat_tasks:
            task = self.heartbeat_tasks[client_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.heartbeat_tasks[client_id]
    
    async def send_to_client(self, client_id: str, message: str) -> None:
        """Send message to specific client."""
        if client_id in self.active_connections:
            queue = self.active_connections[client_id]
            await queue.put(message)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "status": "healthy" if self._running else "stopped",
            "service_type": "sse",
            "port": self.config.port,
            "connections": len(self.active_connections),
            "uptime": uptime_seconds
        }
    
    async def startup(self) -> None:
        """Start the SSE service."""
        self.start_time = datetime.now()
        self._running = True
        self.logger.info(f"SSE service started on {self.config.host}:{self.config.port}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the SSE service."""
        self._running = False
        
        # Remove all connections
        for client_id in list(self.active_connections.keys()):
            await self.remove_client_connection(client_id)
        
        self.logger.info("SSE service shutdown complete")
    
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running 

    # NEW: Event Publisher Integration Methods
    async def subscribe_to_events(self, event_publisher: EventPublisher) -> str:
        """Subscribe to EventPublisher for gesture events."""
        self._event_publisher = event_publisher
        
        # Subscribe to async events (gesture events are published async)
        event_publisher.subscribe_async(self._handle_gesture_event)
        self._subscribed_to_events = True
        
        # Generate a subscription ID for tracking
        subscription_id = f"sse_service_{id(self)}"
        self._subscription_id = subscription_id
        
        logging.info(f"SSE service subscribed to events with ID: {subscription_id}")
        return subscription_id
    
    def is_subscribed_to_events(self) -> bool:
        """Check if service is subscribed to events."""
        return self._subscribed_to_events
    
    async def _handle_gesture_event(self, event: ServiceEvent):
        """Handle gesture events from EventPublisher."""
        try:
            # Filter events based on configuration
            if self.should_stream_event(event):
                await self.stream_gesture_event_to_clients(event)
        except Exception as e:
            logging.error(f"Error handling gesture event: {e}")
    
    # NEW: Event Filtering Methods
    def get_filtered_event_types(self) -> List[EventType]:
        """Get list of event types to stream based on configuration."""
        if self.config.gesture_events_only:
            gesture_types = [
                EventType.GESTURE_DETECTED,
                EventType.GESTURE_LOST
            ]
            
            if self.config.include_confidence_updates:
                gesture_types.append(EventType.GESTURE_CONFIDENCE_UPDATE)
            
            return gesture_types
        else:
            # If not gesture-only, include all event types
            return list(EventType)
    
    def should_stream_event(self, event: ServiceEvent) -> bool:
        """Determine if event should be streamed to clients."""
        # Check event type filter
        filtered_types = self.get_filtered_event_types()
        if event.event_type not in filtered_types:
            return False
        
        # Check confidence threshold for gesture events
        if event.event_type in [EventType.GESTURE_DETECTED, EventType.GESTURE_CONFIDENCE_UPDATE]:
            confidence = event.data.get("confidence", 1.0)
            if confidence < self.config.min_gesture_confidence:
                return False
        
        return True
    
    # NEW: Gesture Event Streaming Methods
    async def stream_gesture_event_to_clients(self, event: ServiceEvent):
        """Stream gesture event to all connected clients."""
        if not self.active_connections:
            return
        
        # IMPORTANT: Check if event should be streamed before converting and sending
        if not self.should_stream_event(event):
            return
        
        # Convert event to SSE format
        sse_message = self._convert_event_to_sse_format(event)
        
        # Stream to all active clients
        disconnected_clients = []
        
        for client_id, client_queue in self.active_connections.items():
            try:
                client_queue.put_nowait(sse_message)
            except asyncio.QueueFull:
                logging.warning(f"Queue full for client {client_id}, dropping event")
            except Exception as e:
                logging.error(f"Error streaming to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.remove_client_connection(client_id)
    
    def _convert_event_to_sse_format(self, event: ServiceEvent) -> str:
        """Convert ServiceEvent to SSE message format."""
        # Map event types to SSE event names
        sse_event_name = event.event_type.value.replace("_", "_")
        
        # Create SSE message
        sse_data = {
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data,
            "source": event.source
        }
        
        if event.event_id:
            sse_data["event_id"] = event.event_id
        
        return f"event: {sse_event_name}\ndata: {json.dumps(sse_data)}\n\n"

    def _setup_health_endpoints(self):
        """Setup health check endpoints."""
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return self.get_health_status() 