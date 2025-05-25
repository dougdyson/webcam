"""
Service event system for webcam human detection.

Provides event-driven architecture for decoupled service communication.
"""
import json
import logging
import asyncio
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Callable, Awaitable, Union


class EventType(Enum):
    """Types of service events."""
    PRESENCE_CHANGED = "presence_changed"
    DETECTION_UPDATE = "detection_update"
    CONFIDENCE_ALERT = "confidence_alert"
    SYSTEM_STATUS = "system_status"
    ERROR_OCCURRED = "error_occurred"


class ServiceEventError(Exception):
    """Exception for service event errors."""
    pass


@dataclass
class ServiceEvent:
    """
    Service event for communication between detection system and services.
    """
    event_type: EventType
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None
    source: str = "webcam_detection"
    event_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_json(self) -> str:
        """Serialize event to JSON string."""
        data = asdict(self)
        # Convert EventType enum to string value
        data['event_type'] = self.event_type.value
        # Convert datetime to ISO string
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ServiceEvent':
        """Deserialize event from JSON string."""
        data = json.loads(json_str)
        
        # Convert string back to EventType enum
        event_type_str = data['event_type']
        event_type = EventType(event_type_str)
        
        # Convert ISO string back to datetime
        timestamp_str = data['timestamp']
        timestamp = datetime.fromisoformat(timestamp_str)
        
        return cls(
            event_type=event_type,
            data=data['data'],
            timestamp=timestamp,
            source=data.get('source', 'webcam_detection'),
            event_id=data.get('event_id')
        )
    
    def __eq__(self, other):
        """Compare events for equality."""
        if not isinstance(other, ServiceEvent):
            return False
        return (
            self.event_type == other.event_type and
            self.data == other.data and
            self.timestamp == other.timestamp and
            self.source == other.source and
            self.event_id == other.event_id
        )
    
    def __str__(self):
        """String representation of event."""
        return f"ServiceEvent({self.event_type.value}, {self.data})"


class EventPublisher:
    """
    Event publisher for managing subscribers and publishing events.
    
    Supports both synchronous and asynchronous subscribers with error isolation.
    """
    
    def __init__(self):
        """Initialize the event publisher."""
        self.subscribers: List[Callable[[ServiceEvent], None]] = []
        self.async_subscribers: List[Callable[[ServiceEvent], Awaitable[None]]] = []
        self.logger = logging.getLogger(__name__)
    
    def subscribe(self, callback: Callable[[ServiceEvent], None]) -> None:
        """Subscribe to events with synchronous callback."""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[ServiceEvent], None]) -> None:
        """Unsubscribe from events."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def subscribe_async(self, callback: Callable[[ServiceEvent], Awaitable[None]]) -> None:
        """Subscribe to events with asynchronous callback."""
        if callback not in self.async_subscribers:
            self.async_subscribers.append(callback)
    
    def unsubscribe_async(self, callback: Callable[[ServiceEvent], Awaitable[None]]) -> None:
        """Unsubscribe from async events."""
        if callback in self.async_subscribers:
            self.async_subscribers.remove(callback)
    
    def publish(self, event: ServiceEvent) -> None:
        """Publish event to all synchronous subscribers."""
        for callback in self.subscribers:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"Error in subscriber callback: {e}")
                # Continue with other subscribers - error isolation
    
    async def publish_async(self, event: ServiceEvent) -> None:
        """Publish event to all subscribers (sync and async)."""
        # Publish to sync subscribers first
        self.publish(event)
        
        # Publish to async subscribers
        for callback in self.async_subscribers:
            try:
                await callback(event)
            except Exception as e:
                self.logger.error(f"Error in async subscriber callback: {e}")
                # Continue with other subscribers - error isolation 