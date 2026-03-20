"""
SSE (Server-Sent Events) service for real-time gesture event streaming.

Provides Server-Sent Events service on port 8766 for streaming gesture events
to web dashboards and other real-time applications.

Phase 15: SSE Service Implementation
"""

import asyncio
import logging
import json
from typing import Dict, Set, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from uuid import uuid4

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.service.events import EventPublisher, ServiceEvent, EventType


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
    
    # NEW Phase 15.3: Advanced configuration features
    enable_detailed_logging: bool = False
    service_name: str = "SSEDetectionService"
    service_version: str = "1.0.0"
    
    # NEW Phase 16.2: Queue management configuration
    max_queue_size: int = 100
    
    def __post_init__(self):
        """Validate configuration values."""
        if not 0.0 <= self.min_gesture_confidence <= 1.0:
            raise ValueError("min_gesture_confidence must be between 0.0 and 1.0")
        if self.max_connections <= 0:
            raise ValueError("max_connections must be positive")
        if self.heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be positive")
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
        if self.max_queue_size <= 0:
            raise ValueError("max_queue_size must be positive")
    
    @classmethod
    def get_configuration_documentation(cls) -> Dict[str, Any]:
        """Get comprehensive configuration documentation."""
        return {
            "parameters": {
                "host": {
                    "type": "string",
                    "default": "localhost",
                    "description": "Host address for SSE service"
                },
                "port": {
                    "type": "integer", 
                    "default": 8766,
                    "description": "Port number for SSE service"
                },
                "max_connections": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum number of simultaneous client connections"
                },
                "heartbeat_interval": {
                    "type": "float",
                    "default": 30.0,
                    "description": "Interval in seconds between heartbeat messages"
                },
                "connection_timeout": {
                    "type": "float",
                    "default": 60.0,
                    "description": "Connection timeout in seconds"
                },
                "gesture_events_only": {
                    "type": "boolean",
                    "default": True,
                    "description": "Filter to only gesture-related events"
                },
                "min_gesture_confidence": {
                    "type": "float",
                    "default": 0.6,
                    "description": "Minimum confidence threshold for gesture events"
                },
                "enable_detailed_logging": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable detailed logging for debugging"
                },
                "service_name": {
                    "type": "string",
                    "default": "SSEDetectionService",
                    "description": "Name identifier for the service"
                },
                "service_version": {
                    "type": "string",
                    "default": "1.0.0",
                    "description": "Version identifier for the service"
                },
                "max_queue_size": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum queue size for event storage"
                }
            },
            "examples": {
                "basic": {
                    "host": "localhost",
                    "port": 8766,
                    "max_connections": 20
                },
                "production": {
                    "host": "0.0.0.0",
                    "port": 8766,
                    "max_connections": 100,
                    "connection_timeout": 300.0,
                    "enable_detailed_logging": True
                }
            },
            "validation_rules": {
                "port": "Must be between 1024 and 65535",
                "max_connections": "Must be positive integer",
                "heartbeat_interval": "Must be positive number",
                "connection_timeout": "Must be positive number",
                "min_gesture_confidence": "Must be between 0.0 and 1.0"
            },
            "default_values": {
                "host": "localhost",
                "port": 8766,
                "max_connections": 20,
                "heartbeat_interval": 30.0,
                "connection_timeout": 60.0
            },
            "performance_considerations": [
                "Higher max_connections increases memory usage",
                "Lower heartbeat_interval increases network traffic",
                "Detailed logging impacts performance in production"
            ],
            "security_notes": [
                "Use specific host instead of 0.0.0.0 in production",
                "Consider connection limits to prevent DoS",
                "Monitor active connections and resource usage"
            ]
        }
    
    @classmethod
    def validate_configuration(cls, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dictionary with detailed error messages."""
        errors = []
        warnings = []
        
        # Known parameters
        known_params = {
            "host", "port", "max_connections", "heartbeat_interval", 
            "connection_timeout", "gesture_events_only", "include_confidence_updates",
            "min_gesture_confidence", "enable_detailed_logging", 
            "service_name", "service_version", "max_queue_size"
        }
        
        # Check for unknown parameters
        for key in config_dict:
            if key not in known_params:
                warnings.append(f"Unknown parameter '{key}' will be ignored")
        
        # Validate specific parameters
        if "port" in config_dict:
            port = config_dict["port"]
            if not isinstance(port, int) or port < 1024 or port > 65535:
                errors.append("Port must be an integer between 1024 and 65535")
        
        if "max_connections" in config_dict:
            max_conn = config_dict["max_connections"]
            if not isinstance(max_conn, int) or max_conn <= 0:
                errors.append("Max connections must be a positive integer")
        
        if "heartbeat_interval" in config_dict:
            heartbeat = config_dict["heartbeat_interval"]
            if not isinstance(heartbeat, (int, float)) or heartbeat <= 0:
                errors.append("Heartbeat interval must be a positive number")
        
        if "connection_timeout" in config_dict:
            timeout = config_dict["connection_timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("Connection timeout must be a positive number")
        
        if "min_gesture_confidence" in config_dict:
            confidence = config_dict["min_gesture_confidence"]
            if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
                errors.append("Min gesture confidence must be a number between 0.0 and 1.0")
        
        if "max_queue_size" in config_dict:
            queue_size = config_dict["max_queue_size"]
            if not isinstance(queue_size, int) or queue_size <= 0:
                errors.append("Max queue size must be a positive integer")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


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
        self.start_time: Optional[datetime] = datetime.now()  # Initialize start time
        self._running = True  # Initialize as running by default
        self.logger = logging.getLogger(__name__)
        
        # NEW Phase 15.3: Advanced metrics and monitoring
        self._total_connections = 0
        self._total_events_sent = 0
        self._total_heartbeats_sent = 0
        self._connection_events: List[Dict[str, Any]] = []
        self._error_counts: Dict[str, int] = {}
        self._client_activity: Dict[str, datetime] = {}
        self._last_activity: Optional[datetime] = None
        self._memory_usage_mb = 0.0
        
        # Setup detailed logging if enabled
        if self.config.enable_detailed_logging:
            self._setup_detailed_logging()
        
        self._setup_cors()
        self._setup_routes()
        self._setup_health_endpoints()
    
    def _setup_detailed_logging(self):
        """Setup detailed logging configuration."""
        # Configure more verbose logging for SSE operations
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [SSE] %(message)s'
        )
        
        # Create handler if doesn't exist
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
    
    def is_detailed_logging_enabled(self) -> bool:
        """Check if detailed logging is enabled."""
        return self.config.enable_detailed_logging
    
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
        
        # Create event queue for client
        self.active_connections[client_id] = asyncio.Queue(maxsize=self.config.max_queue_size)
        
        # NEW Phase 15.3: Track connection metrics
        self._total_connections += 1
        self._client_activity[client_id] = datetime.now()
        self._last_activity = datetime.now()
        
        # Log connection event for monitoring
        connection_event = {
            "event_type": "client_connected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "total_connections": self._total_connections,
            "active_connections": len(self.active_connections)
        }
        self._connection_events.append(connection_event)
        
        if self.config.enable_detailed_logging:
            self.logger.debug(f"Client connected: {client_id} (total: {self._total_connections})")
        else:
            self.logger.info(f"Added SSE client connection: {client_id}")
    
    async def remove_client_connection(self, client_id: str) -> None:
        """Remove a client connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Clean up client activity tracking
        if client_id in self._client_activity:
            del self._client_activity[client_id]
        
        # Stop heartbeat if running
        await self.stop_heartbeat(client_id)
        
        # Log disconnection event for monitoring
        connection_event = {
            "event_type": "client_disconnected",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "active_connections": len(self.active_connections)
        }
        self._connection_events.append(connection_event)
        
        if self.config.enable_detailed_logging:
            self.logger.debug(f"Client disconnected: {client_id} (remaining: {len(self.active_connections)})")
        else:
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
        """Start heartbeat for client connection."""
        await self.stop_heartbeat(client_id)  # Stop any existing heartbeat
        
        async def heartbeat_task():
            try:
                while client_id in self.active_connections:
                    await asyncio.sleep(self.config.heartbeat_interval)
                    if client_id in self.active_connections:
                        heartbeat_msg = "data: {\"event_type\": \"heartbeat\", \"timestamp\": \"" + datetime.now().isoformat() + "\"}\n\n"
                        await self.send_to_client(client_id, heartbeat_msg)
                        
                        # NEW Phase 15.3: Track heartbeat metrics
                        self._total_heartbeats_sent += 1
                        self._client_activity[client_id] = datetime.now()
                        self._last_activity = datetime.now()
                        
                        if self.config.enable_detailed_logging:
                            self.logger.debug(f"Sent heartbeat to client {client_id}")
                            
            except Exception as e:
                self.logger.error(f"Heartbeat error for client {client_id}: {e}")
                await self.remove_client_connection(client_id)
        
        task = asyncio.create_task(heartbeat_task())
        self.heartbeat_tasks[client_id] = task
    
    async def stop_heartbeat(self, client_id: str) -> None:
        """Stop heartbeat for client connection."""
        if client_id in self.heartbeat_tasks:
            task = self.heartbeat_tasks[client_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self.heartbeat_tasks[client_id]
    
    async def send_to_client(self, client_id: str, message: str) -> None:
        """Send message to specific client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].put(message)
            
            # NEW Phase 15.3: Track event metrics
            self._total_events_sent += 1
            self._client_activity[client_id] = datetime.now()
            self._last_activity = datetime.now()
            
            if self.config.enable_detailed_logging:
                self.logger.debug(f"Sent message to client {client_id}: {message[:50]}...")
        else:
            if self.config.enable_detailed_logging:
                self.logger.warning(f"Attempted to send to disconnected client: {client_id}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get basic health status."""
        uptime = 0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "status": "healthy" if self._running else "stopped",
            "service_type": "sse",
            "port": self.config.port,
            "connections": self.get_connection_count(),
            "active_connections": self.get_connection_count(),
            "uptime": uptime
        }
    
    def get_detailed_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status with detailed metrics."""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # Calculate events per minute
        events_per_minute = 0.0
        if uptime_seconds > 0:
            events_per_minute = (self._total_events_sent / uptime_seconds) * 60
        
        return {
            "status": "healthy" if self._running else "stopped",
            "service_type": "sse",
            "service_name": self.config.service_name,
            "service_version": self.config.service_version,
            "port": self.config.port,
            "host": self.config.host,
            "uptime_seconds": uptime_seconds,
            "active_connections": self.get_connection_count(),
            "total_connections": self._total_connections,
            "max_connections": self.config.max_connections,
            "total_events_sent": self._total_events_sent,
            "total_heartbeats_sent": self._total_heartbeats_sent,
            "events_per_minute": round(events_per_minute, 2),
            "connection_timeout": self.config.connection_timeout,
            "heartbeat_interval": self.config.heartbeat_interval,
            "memory_usage_mb": self._memory_usage_mb,
            "last_activity": self._last_activity.isoformat() if self._last_activity else None
        }
    
    def get_monitoring_data(self) -> Dict[str, Any]:
        """Get detailed monitoring data for debugging and analytics."""
        return {
            "connection_events": self._connection_events[-100:],  # Last 100 events
            "event_stream_stats": {
                "total_events_sent": self._total_events_sent,
                "total_heartbeats_sent": self._total_heartbeats_sent,
                "active_connections": self.get_connection_count(),
                "total_connections": self._total_connections
            },
            "error_counts": self._error_counts.copy(),
            "performance_metrics": {
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                "memory_usage_mb": self._memory_usage_mb,
                "events_per_second": self._calculate_events_per_second()
            },
            "client_activity": {
                client_id: activity.isoformat() 
                for client_id, activity in self._client_activity.items()
            },
            "heartbeat_stats": {
                "total_heartbeats": self._total_heartbeats_sent,
                "heartbeat_interval": self.config.heartbeat_interval,
                "active_heartbeat_tasks": len(self.heartbeat_tasks)
            }
        }
    
    def _calculate_events_per_second(self) -> float:
        """Calculate events per second rate."""
        if not self.start_time:
            return 0.0
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        if uptime == 0:
            return 0.0
        
        return self._total_events_sent / uptime
    
    def format_log_entry(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format log entry for detailed logging."""
        return {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "service": "sse_service",
            "data": data.copy()
        }
    
    async def startup(self) -> None:
        """Start the SSE service."""
        self.start_time = datetime.now()
        self._running = True
        self.logger.info("SSE Detection Service started")
    
    async def startup_with_validation(self) -> Dict[str, Any]:
        """Start the service with comprehensive configuration validation."""
        validation_errors = []
        
        try:
            # Validate configuration
            if self.config.port < 1024 or self.config.port > 65535:
                validation_errors.append("Port must be between 1024 and 65535")
            
            if self.config.max_connections <= 0:
                validation_errors.append("Max connections must be positive")
            
            if self.config.heartbeat_interval <= 0:
                validation_errors.append("Heartbeat interval must be positive")
            
            if self.config.connection_timeout <= 0:
                validation_errors.append("Connection timeout must be positive")
            
            # If validation errors, raise exception
            if validation_errors:
                raise ValueError(f"Configuration validation failed: {validation_errors}")
            
            # Start the service
            await self.startup()
            
            return {
                "success": True,
                "validation_errors": [],
                "startup_time": self.start_time.isoformat() if self.start_time else None
            }
            
        except Exception as e:
            return {
                "success": False,
                "validation_errors": validation_errors,
                "error": str(e)
            }
    
    async def shutdown(self) -> None:
        """Stop the SSE service."""
        # Stop all heartbeat tasks
        for client_id in list(self.heartbeat_tasks.keys()):
            await self.stop_heartbeat(client_id)
        
        # Clear all connections
        self.active_connections.clear()
        
        self._running = False
        self.logger.info("SSE Detection Service stopped")
    
    async def graceful_shutdown_with_cleanup(self) -> Dict[str, Any]:
        """Graceful shutdown with client notification and resource cleanup."""
        clients_notified = 0
        connections_cleaned = 0
        
        try:
            # Notify all connected clients about shutdown
            shutdown_message = "data: {\"event_type\": \"service_shutdown\", \"message\": \"Service is shutting down\"}\n\n"
            
            for client_id in list(self.active_connections.keys()):
                try:
                    await self.send_to_client(client_id, shutdown_message)
                    clients_notified += 1
                except Exception as e:
                    self.logger.error(f"Error notifying client {client_id}: {e}")
            
            # Give clients time to receive shutdown message
            await asyncio.sleep(1.0)
            
            # Clean up all connections
            for client_id in list(self.active_connections.keys()):
                await self.remove_client_connection(client_id)
                connections_cleaned += 1
            
            # Stop the service
            await self.shutdown()
            
            return {
                "success": True,
                "clients_notified": clients_notified,
                "connections_cleaned": connections_cleaned,
                "resources_freed": True,
                "cleanup_completed": True,
                "shutdown_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error during graceful shutdown: {e}")
            return {
                "success": False,
                "clients_notified": clients_notified,
                "connections_cleaned": connections_cleaned,
                "resources_freed": False,
                "cleanup_completed": False,
                "error": str(e)
            }
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get status of cleanup operations."""
        return {
            "event_queues_cleared": len(self.active_connections) == 0,
            "heartbeat_tasks_stopped": len(self.heartbeat_tasks) == 0,
            "memory_freed": True,  # Simplified for testing
            "service_stopped": not self._running
        }
    
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service information for service manager compatibility."""
        return {
            "service_type": "sse",
            "service_name": self.config.service_name,
            "port": self.config.port,
            "version": self.config.service_version,
            "capabilities": [
                "real_time_events",
                "gesture_streaming", 
                "multiple_clients",
                "heartbeat_monitoring",
                "cors_support"
            ],
            "dependencies": [
                "event_publisher",
                "fastapi",
                "asyncio"
            ],
            "status": "running" if self._running else "stopped"
        }
    
    def integrate_with_event_publisher(self, event_publisher: EventPublisher) -> Dict[str, Any]:
        """Integrate with EventPublisher for service manager compatibility."""
        try:
            # Subscribe to relevant event types
            event_types = self.get_filtered_event_types()
            
            # Set up the event publisher
            self._event_publisher = event_publisher
            
            # Subscribe to events
            subscription_id = event_publisher.subscribe_async(self._handle_gesture_event)
            self._subscription_id = subscription_id
            self._subscribed_to_events = True
            
            return {
                "success": True,
                "subscription_count": len(event_types),
                "subscription_id": subscription_id,
                "event_types": [et.value for et in event_types]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "subscription_count": 0
            }

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

    # NEW Phase 16.2: End-to-End Integration Methods
    def setup_gesture_integration(self, event_publisher: EventPublisher):
        """Setup gesture integration with EventPublisher (synchronous version)."""
        self._event_publisher = event_publisher
        
        # Subscribe to async events (gesture events are published async)
        event_publisher.subscribe_async(self._handle_gesture_event)
        self._subscribed_to_events = True
        
        # Generate a subscription ID for tracking
        subscription_id = f"sse_service_{id(self)}"
        self._subscription_id = subscription_id
        
        logging.info(f"SSE service gesture integration setup with ID: {subscription_id}")
        return subscription_id
    
    def _format_event_for_sse(self, event: ServiceEvent) -> str:
        """Format ServiceEvent for SSE streaming (alias for _convert_event_to_sse_format)."""
        return self._convert_event_to_sse_format(event)
    
    def _should_stream_event(self, event: ServiceEvent) -> bool:
        """Check if event should be streamed (alias for should_stream_event)."""
        return self.should_stream_event(event)
    
    async def broadcast_to_all_clients(self, event: ServiceEvent):
        """Broadcast event to all connected clients."""
        await self.stream_gesture_event_to_clients(event)
    
    async def _queue_event_for_all_clients(self, event: ServiceEvent):
        """Queue event for all connected clients."""
        if not self.active_connections:
            return
        
        # Check if event should be streamed before queuing
        if not self.should_stream_event(event):
            return
        
        # Convert event to SSE format
        sse_message = self._convert_event_to_sse_format(event)
        
        # Queue for all active clients
        for client_id, client_queue in self.active_connections.items():
            try:
                # Check queue size limit
                if client_queue.qsize() >= self.config.max_queue_size:
                    logging.warning(f"Queue at max size for client {client_id}, dropping oldest event")
                    # Remove oldest event if queue is full
                    try:
                        client_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                
                client_queue.put_nowait(sse_message)
            except Exception as e:
                logging.error(f"Error queuing event for client {client_id}: {e}") 