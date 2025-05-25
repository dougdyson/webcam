"""
Base service class providing common functionality for all service types.
"""

import logging
import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ServiceMetrics:
    """Service performance and health metrics."""
    total_requests: int = 0
    total_errors: int = 0
    avg_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    error_rate: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_request_time: Optional[datetime] = None
    
    def update_request(self, response_time_ms: float, error: bool = False):
        """Update metrics with new request data."""
        self.total_requests += 1
        if error:
            self.total_errors += 1
            
        # Update rolling average response time
        if self.total_requests == 1:
            self.avg_response_time_ms = response_time_ms
        else:
            # Exponential moving average with alpha=0.1
            alpha = 0.1
            self.avg_response_time_ms = (
                alpha * response_time_ms + 
                (1 - alpha) * self.avg_response_time_ms
            )
            
        # Calculate rates
        elapsed_time = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        if elapsed_time > 0:
            self.requests_per_second = self.total_requests / elapsed_time
            self.error_rate = self.total_errors / self.total_requests
            
        self.last_request_time = datetime.now(timezone.utc)


class BaseService(ABC):
    """Base class for all service implementations."""
    
    def __init__(self, detection_service=None, config: Optional[Dict[str, Any]] = None):
        self.detection_service = detection_service
        self.config = self._load_config(config or {})
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = ServiceMetrics()
        self.is_running = False
        self._lock = threading.RLock()
        
        # Common configuration
        self.host = self.config.get('host', 'localhost')
        self.port = self.config.get('port', self._get_default_port())
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        self.timeout = self.config.get('timeout', 30)
        
        # Validate configuration
        self._validate_config()
        
    @abstractmethod
    def _get_default_port(self) -> int:
        """Get the default port for this service type."""
        pass
        
    @abstractmethod
    def start(self):
        """Start the service."""
        pass
        
    @abstractmethod  
    def stop(self, timeout: Optional[float] = None):
        """Stop the service."""
        pass
        
    def _load_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Load and merge configuration from various sources."""
        # Start with defaults
        default_config = {
            'host': 'localhost',
            'confidence_threshold': 0.5,
            'timeout': 30,
            'cors_enabled': False,
            'rate_limit': 10,
            'cache_duration_ms': 0,  # No caching by default
            'detection_timeout_ms': 5000,  # 5 second detection timeout
            'rate_limit_per_second': 10
        }
        
        # Merge with provided config
        merged_config = {**default_config, **config}
        
        return merged_config
        
    def _validate_config(self):
        """Validate service configuration."""
        if not (1024 <= self.port <= 65535):
            raise ValueError("Port must be between 1024 and 65535")
            
        if not isinstance(self.host, str) or not self.host:
            raise ValueError("Invalid host format")
            
        rate_limit = self.config.get('rate_limit', 10)
        if rate_limit <= 0:
            raise ValueError("Rate limit must be positive")
            
    def update_config(self, new_config: Dict[str, Any]):
        """Update service configuration at runtime."""
        with self._lock:
            self.config.update(new_config)
            
            # Update commonly used config values
            self.host = self.config.get('host', self.host)
            self.port = self.config.get('port', self.port)
            self.confidence_threshold = self.config.get('confidence_threshold', self.confidence_threshold)
            self.timeout = self.config.get('timeout', self.timeout)
            
            # Re-validate
            self._validate_config()
            
            self.logger.info(f"Configuration updated: {new_config}")
            
    def save_config(self):
        """Save current configuration to file (stub for implementation)."""
        # Implementation would depend on config file format
        self.logger.info("Configuration saved (stub)")
        
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        with self._lock:
            return {
                'total_requests': self.metrics.total_requests,
                'total_errors': self.metrics.total_errors,
                'avg_response_time_ms': self.metrics.avg_response_time_ms,
                'requests_per_second': self.metrics.requests_per_second,
                'error_rate': self.metrics.error_rate,
                'uptime_seconds': (
                    datetime.now(timezone.utc) - self.metrics.start_time
                ).total_seconds(),
                'last_request_time': self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None
            }
            
    def check_detection_health(self) -> Dict[str, Any]:
        """Check the health of the detection system."""
        if not self.detection_service:
            return {
                'camera_connected': False,
                'detection_active': False,
                'last_detection_time': None,
                'error': 'No detection service configured'
            }
            
        try:
            # Try to get status from detection service
            if hasattr(self.detection_service, 'get_status'):
                status = self.detection_service.get_status()
                return {
                    'camera_connected': True,
                    'detection_active': status.get('status') == 'active',
                    'last_detection_time': datetime.now(timezone.utc).isoformat(),
                    'fps': status.get('fps', 0)
                }
            else:
                # Basic health check - try a detection
                try:
                    self.detection_service.detect_person()
                    return {
                        'camera_connected': True,
                        'detection_active': True,
                        'last_detection_time': datetime.now(timezone.utc).isoformat()
                    }
                except Exception as e:
                    return {
                        'camera_connected': False,
                        'detection_active': False,
                        'last_detection_time': None,
                        'error': str(e)
                    }
                    
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                'camera_connected': False,
                'detection_active': False,
                'last_detection_time': None,
                'error': str(e)
            }
            
    def _safe_detect_person(self) -> Dict[str, Any]:
        """Safely perform person detection with error handling."""
        start_time = time.time()
        
        try:
            if not self.detection_service:
                return {
                    'present': False,
                    'confidence': 0.0,
                    'detection_type': 'unavailable',
                    'error': 'Detection service unavailable',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
            # Perform detection
            present, confidence, detection_type = self.detection_service.detect_person()
            
            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                present = False
                
            response = {
                'present': present,
                'confidence': confidence,
                'detection_type': detection_type,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Update metrics
            processing_time_ms = (time.time() - start_time) * 1000
            self.metrics.update_request(processing_time_ms, error=False)
            
            return response
            
        except RuntimeError as e:
            error_msg = "Detection unavailable"
            if "Camera" in str(e):
                error_msg = "Camera error"
            elif "timeout" in str(e).lower():
                error_msg = "Detection timeout"
                
            response = {
                'present': False,
                'confidence': 0.0,
                'detection_type': 'error',
                'error': error_msg,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            processing_time_ms = (time.time() - start_time) * 1000
            self.metrics.update_request(processing_time_ms, error=True)
            
            return response
            
        except MemoryError:
            response = {
                'present': False,
                'confidence': 0.0,
                'detection_type': 'error',
                'error': 'System resource exhausted',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            processing_time_ms = (time.time() - start_time) * 1000
            self.metrics.update_request(processing_time_ms, error=True)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Unexpected detection error: {e}")
            
            response = {
                'present': False,
                'confidence': 0.0,
                'detection_type': 'error',
                'error': 'Detection system error',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            processing_time_ms = (time.time() - start_time) * 1000
            self.metrics.update_request(processing_time_ms, error=True)
            
            return response 