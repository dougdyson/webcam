"""
Service layer for webcam detection system.
Provides HTTP API, WebSocket, and Server-Sent Events interfaces.
"""

from .http_service import HTTPService
from .base_service import BaseService

__all__ = ['HTTPService', 'BaseService'] 