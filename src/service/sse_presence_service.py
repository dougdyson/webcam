"""
SSE service for streaming presence change events.

This service provides Server-Sent Events (SSE) streaming specifically for 
human presence changes, allowing clients to receive real-time notifications
when someone enters or leaves the camera frame.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Set
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .events import EventPublisher, ServiceEvent, EventType


logger = logging.getLogger(__name__)


class SSEPresenceService:
    """
    SSE service for streaming presence change events.
    
    Provides a clean, focused service that:
    - Subscribes to PRESENCE_CHANGED events from the event system
    - Streams these events to connected SSE clients
    - Maintains separate event queues per client
    """
    
    def __init__(self):
        """Initialize the SSE presence service."""
        self.app = FastAPI(
            title="Presence SSE Service",
            description="Real-time presence change streaming via Server-Sent Events",
            version="1.0.0"
        )
        
        # Client management
        self._client_queues: Dict[str, asyncio.Queue] = {}
        self._active_clients: Set[str] = set()
        
        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
        
        logger.info("SSE Presence Service initialized")
    
    def _setup_middleware(self):
        """Setup CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Setup SSE streaming routes."""
        
        @self.app.get("/events/presence/{client_id}")
        async def stream_presence_events(client_id: str):
            """Stream presence change events to a specific client."""
            logger.info(f"New SSE client connected: {client_id}")
            
            # Create queue for this client
            queue = asyncio.Queue()
            self._client_queues[client_id] = queue
            self._active_clients.add(client_id)
            
            async def event_generator():
                try:
                    # Send initial connection event
                    init_data = {'connected': True, 'client_id': client_id}
                    yield f"data: {json.dumps(init_data)}\n\n"
                    
                    while client_id in self._active_clients:
                        try:
                            # Wait for events with timeout for keepalive
                            event = await asyncio.wait_for(queue.get(), timeout=30.0)
                            
                            if event is None:  # Shutdown signal
                                break
                            
                            # Format as SSE
                            yield f"data: {json.dumps(event)}\n\n"
                            
                        except asyncio.TimeoutError:
                            # Send keepalive
                            yield f"data: keepalive\n\n"
                            
                except asyncio.CancelledError:
                    logger.info(f"SSE stream cancelled for client: {client_id}")
                    raise
                finally:
                    # Cleanup
                    self._active_clients.discard(client_id)
                    if client_id in self._client_queues:
                        del self._client_queues[client_id]
                    logger.info(f"SSE client disconnected: {client_id}")
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "active_clients": len(self._active_clients),
                "timestamp": datetime.now().isoformat()
            }
    
    def subscribe_to_events(self, event_publisher: EventPublisher):
        """Subscribe to presence events from the event publisher."""
        # Subscribe to async events (since SSE needs async)
        event_publisher.subscribe_async(self._handle_presence_event)
        logger.info("Subscribed to presence events")
    
    async def _handle_presence_event(self, event: ServiceEvent):
        """Handle presence change events."""
        if event.event_type != EventType.PRESENCE_CHANGED:
            return
        
        # Format event data
        event_data = {
            "event_type": "presence_changed",
            "human_present": event.data.get("human_present", False),
            "confidence": event.data.get("confidence", 0.0),
            "timestamp": event.data.get("timestamp", datetime.now().isoformat())
        }
        
        # Send to all connected clients
        for client_id in list(self._active_clients):
            if client_id in self._client_queues:
                try:
                    await self._client_queues[client_id].put(event_data)
                except Exception as e:
                    logger.error(f"Error sending event to client {client_id}: {e}")