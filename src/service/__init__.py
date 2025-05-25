"""
Service layer for webcam human detection.

This module provides service integration capabilities including:
- Event system for decoupled communication
- HTTP API for simple guard clause integration
- WebSocket service for real-time applications
- Server-Sent Events for streaming applications
"""

from .events import ServiceEvent, EventType, EventPublisher, ServiceEventError
from .http_service import HTTPDetectionService, HTTPServiceConfig, PresenceStatus, HTTPServiceError

__all__ = [
    # Event system
    'ServiceEvent',
    'EventType', 
    'EventPublisher',
    'ServiceEventError',
    # HTTP service
    'HTTPDetectionService',
    'HTTPServiceConfig',
    'PresenceStatus',
    'HTTPServiceError'
] 