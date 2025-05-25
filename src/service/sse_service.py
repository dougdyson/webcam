"""
SSE (Server-Sent Events) service for real-time gesture event streaming.

Provides Server-Sent Events service on port 8766 for streaming gesture events
to web dashboards and other real-time applications.
"""

import asyncio
import logging
import json
from typing import Dict, Set, Optional, Any
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
    heartbeat_interval: float = 30.0  # seconds
    connection_timeout: float = 60.0  # seconds
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.port <= 0 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        if self.max_connections < 0:
            raise ValueError("Max connections cannot be negative")
        if self.heartbeat_interval <= 0:
            raise ValueError("Heartbeat interval must be positive")


class SSEDetectionService:
    """
    Server-Sent Events service for real-time gesture event streaming.
    
    Provides SSE endpoints for streaming gesture events to web clients
    with connection management, heartbeat, and CORS support.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8766, 
                 config: Optional[SSEServiceConfig] = None,
                 heartbeat_interval: float = 30.0):
        """
        Initialize SSE service.
        
        Args:
            host: Host to bind to
            port: Port to bind to  
            config: Service configuration
            heartbeat_interval: Heartbeat interval in seconds
        """
        if config:
            self.host = config.host
            self.port = config.port
            self.max_connections = config.max_connections
            self.heartbeat_interval = config.heartbeat_interval
        else:
            self.host = host
            self.port = port
            self.max_connections = 20
            self.heartbeat_interval = heartbeat_interval
        
        # Service state
        self.app = FastAPI(title="Webcam Detection SSE Service")
        self.active_connections: Dict[str, asyncio.Queue] = {}
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.start_time: Optional[datetime] = None
        self._running = False
        
        # Setup middleware and routes
        self._setup_cors()
        self._setup_routes()
        
        self.logger = logging.getLogger(__name__)
    
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
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return self.get_health_status()
    
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
        if len(self.active_connections) >= self.max_connections:
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
                    await asyncio.sleep(self.heartbeat_interval)
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
            "port": self.port,
            "connections": len(self.active_connections),
            "uptime": uptime_seconds
        }
    
    async def startup(self) -> None:
        """Start the SSE service."""
        self.start_time = datetime.now()
        self._running = True
        self.logger.info(f"SSE service started on {self.host}:{self.port}")
    
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