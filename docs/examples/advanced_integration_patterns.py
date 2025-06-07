#!/usr/bin/env python3
"""
Advanced Integration Patterns

Real-world integration examples for webcam detection system:
- Smart home automation triggers
- Real-time web dashboard integration
- Microservice architecture patterns
- Production monitoring and alerting

Usage:
    conda activate webcam && python docs/examples/advanced_integration_patterns.py
"""

import sys
import json
import time
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

# Add src to path for imports
sys.path.append('src')

from service.events import EventPublisher, ServiceEvent, EventType
from service.http_service import HTTPDetectionService
from service.sse_service import SSEDetectionService

@dataclass
class SmartHomeConfig:
    """Configuration for smart home integration"""
    home_assistant_url: str = "http://localhost:8123"
    home_assistant_token: str = ""
    phillips_hue_bridge: str = "192.168.1.100"
    sonos_speaker: str = "192.168.1.101"
    cooking_timer_webhook: str = "http://localhost:3000/webhook/timer"


class SmartHomeIntegration:
    """
    Example 1: Smart Home Automation Integration
    
    Demonstrates integration with popular smart home platforms:
    - Home Assistant automation triggers
    - Phillips Hue lighting control
    - Sonos speaker control
    - Cooking timer management
    """
    
    def __init__(self, config: SmartHomeConfig):
        self.config = config
        self.event_publisher = EventPublisher()
        self.automation_state = {
            "kitchen_occupied": False,
            "cooking_timer_active": False,
            "lights_adjusted": False,
            "music_playing": False
        }
        
    def initialize(self):
        """Initialize smart home connections"""
        print("🏠 Initializing smart home integration...")
        
        # Subscribe to webcam detection events
        self.event_publisher.subscribe(EventType.PRESENCE_CHANGED, self._handle_presence_change)
        self.event_publisher.subscribe(EventType.GESTURE_DETECTED, self._handle_gesture)
        
        print("✅ Smart home integration ready")
        
    async def _handle_presence_change(self, event: ServiceEvent):
        """Handle human presence changes for automation"""
        presence_data = event.data
        human_present = presence_data.get("human_present", False)
        confidence = presence_data.get("confidence", 0.0)
        
        if human_present and confidence > 0.7:
            await self._trigger_kitchen_entry()
            self.automation_state["kitchen_occupied"] = True
        elif not human_present:
            await self._trigger_kitchen_exit()
            self.automation_state["kitchen_occupied"] = False
            
    async def _handle_gesture(self, event: ServiceEvent):
        """Handle gesture detection for smart controls"""
        gesture_data = event.data
        gesture_type = gesture_data.get("gesture_type", "")
        confidence = gesture_data.get("confidence", 0.0)
        
        if confidence > 0.8:
            if gesture_type == "Thumb_Up":
                await self._start_cooking_timer()
            elif gesture_type == "Open_Palm":
                await self._stop_cooking_timer()
            elif gesture_type == "Victory":
                await self._toggle_music()
                
    async def _trigger_kitchen_entry(self):
        """Automation: Someone entered the kitchen"""
        print("🏠 Kitchen entry detected - triggering automations...")
        
        # Turn on kitchen lights
        await self._control_lights(brightness=80, color="warm_white")
        
        # Start ambient music if evening
        current_hour = datetime.now().hour
        if 17 <= current_hour <= 22:  # Evening hours
            await self._control_music("start", volume=30)
            
        # Send Home Assistant webhook
        await self._send_home_assistant_event("kitchen_occupied", {"occupied": True})
        
    async def _trigger_kitchen_exit(self):
        """Automation: Kitchen is empty"""
        print("🏠 Kitchen exit detected - cleaning up automations...")
        
        # Dim lights after 5 minutes (would use delayed automation)
        await self._control_lights(brightness=20, color="soft_white")
        
        # Stop cooking timer if no gesture interaction
        if self.automation_state["cooking_timer_active"]:
            await asyncio.sleep(300)  # 5 minute delay
            if not self.automation_state["kitchen_occupied"]:
                await self._stop_cooking_timer()
                
        # Send Home Assistant webhook
        await self._send_home_assistant_event("kitchen_occupied", {"occupied": False})
        
    async def _start_cooking_timer(self):
        """Start cooking timer with thumbs up gesture"""
        print("👍 Thumbs up detected - starting 20-minute cooking timer")
        
        timer_data = {
            "duration_minutes": 20,
            "started_at": datetime.now().isoformat(),
            "trigger": "gesture_thumbs_up"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.config.cooking_timer_webhook,
                    json=timer_data,
                    timeout=5.0
                )
            self.automation_state["cooking_timer_active"] = True
            
        except Exception as e:
            print(f"❌ Failed to start cooking timer: {e}")
            
    async def _stop_cooking_timer(self):
        """Stop cooking timer with stop gesture"""
        print("🛑 Stop gesture detected - canceling cooking timer")
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.delete(
                    f"{self.config.cooking_timer_webhook}/active",
                    timeout=5.0
                )
            self.automation_state["cooking_timer_active"] = False
            
        except Exception as e:
            print(f"❌ Failed to stop cooking timer: {e}")
            
    async def _control_lights(self, brightness: int, color: str):
        """Control Phillips Hue lights"""
        if not self.config.phillips_hue_bridge:
            return
            
        light_command = {
            "on": True,
            "bri": int(brightness * 2.54),  # Convert to 0-254 range
            "ct": 366 if color == "warm_white" else 153  # Color temperature
        }
        
        try:
            # This would integrate with actual Hue API
            print(f"💡 Setting kitchen lights: {brightness}% brightness, {color}")
            self.automation_state["lights_adjusted"] = True
            
        except Exception as e:
            print(f"❌ Failed to control lights: {e}")
            
    async def _control_music(self, action: str, volume: int = 50):
        """Control Sonos speaker"""
        if not self.config.sonos_speaker:
            return
            
        try:
            if action == "start":
                print(f"🎵 Starting ambient music at {volume}% volume")
                self.automation_state["music_playing"] = True
            elif action == "stop":
                print("🔇 Stopping music")
                self.automation_state["music_playing"] = False
            elif action == "toggle":
                new_state = not self.automation_state["music_playing"]
                print(f"🎵 {'Starting' if new_state else 'Stopping'} music")
                self.automation_state["music_playing"] = new_state
                
        except Exception as e:
            print(f"❌ Failed to control music: {e}")
            
    async def _toggle_music(self):
        """Toggle music with victory gesture"""
        print("✌️ Victory gesture detected - toggling music")
        await self._control_music("toggle")
        
    async def _send_home_assistant_event(self, event_type: str, data: Dict):
        """Send event to Home Assistant webhook"""
        if not self.config.home_assistant_url:
            return
            
        webhook_url = f"{self.config.home_assistant_url}/api/webhook/webcam_detection"
        payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    webhook_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.config.home_assistant_token}"},
                    timeout=5.0
                )
            print(f"🏠 Sent Home Assistant event: {event_type}")
            
        except Exception as e:
            print(f"❌ Failed to send Home Assistant event: {e}")
            
    def get_automation_status(self) -> Dict:
        """Get current automation state"""
        return {
            "timestamp": datetime.now().isoformat(),
            "automation_state": self.automation_state.copy(),
            "integrations": {
                "home_assistant": bool(self.config.home_assistant_url),
                "hue_lights": bool(self.config.phillips_hue_bridge),
                "sonos_speaker": bool(self.config.sonos_speaker),
                "cooking_timer": bool(self.config.cooking_timer_webhook)
            }
        }
        
    async def run_demo(self, duration_seconds: int = 60):
        """Run smart home integration demo"""
        print(f"🏠 Running smart home demo for {duration_seconds} seconds...")
        print("Demo automations:")
        print("- Kitchen entry: Turn on lights, start music (evening)")
        print("- Thumbs up: Start 20-minute cooking timer")
        print("- Stop gesture: Cancel cooking timer")
        print("- Victory: Toggle music")
        print("- Kitchen exit: Dim lights, cleanup timers")
        print()
        
        start_time = time.time()
        event_count = 0
        
        # Simulate some events for demo
        demo_events = [
            (5, "presence", {"human_present": True, "confidence": 0.85}),
            (10, "gesture", {"gesture_type": "Thumb_Up", "confidence": 0.9}),
            (25, "gesture", {"gesture_type": "Victory", "confidence": 0.8}),
            (40, "gesture", {"gesture_type": "Open_Palm", "confidence": 0.9}),
            (55, "presence", {"human_present": False, "confidence": 0.3})
        ]
        
        for event_time, event_type, event_data in demo_events:
            await asyncio.sleep(event_time - (time.time() - start_time))
            
            if event_type == "presence":
                event = ServiceEvent(EventType.PRESENCE_CHANGED, event_data)
                await self._handle_presence_change(event)
            elif event_type == "gesture":
                event = ServiceEvent(EventType.GESTURE_DETECTED, event_data)
                await self._handle_gesture(event)
                
            event_count += 1
            
        # Wait for remaining time
        remaining_time = duration_seconds - (time.time() - start_time)
        if remaining_time > 0:
            await asyncio.sleep(remaining_time)
            
        print(f"\n📊 Smart Home Demo Summary:")
        print(f"   Events processed: {event_count}")
        status = self.get_automation_status()
        print(f"   Final automation state: {status['automation_state']}")


class WebDashboardIntegration:
    """
    Example 2: Real-time Web Dashboard Integration
    
    Demonstrates building a real-time web dashboard using SSE streaming:
    - Live detection status
    - Gesture event feed
    - Performance metrics
    - Historical data visualization
    """
    
    def __init__(self):
        self.detection_history = []
        self.gesture_history = []
        self.performance_metrics = {
            "total_detections": 0,
            "total_gestures": 0,
            "uptime_start": datetime.now(),
            "last_detection": None
        }
        
    def initialize(self):
        """Initialize dashboard data collection"""
        print("📊 Initializing web dashboard integration...")
        
        # This would connect to actual SSE service
        print("✅ Dashboard integration ready")
        
    async def connect_to_sse_stream(self, client_id: str = "dashboard") -> None:
        """Connect to SSE stream for real-time updates"""
        sse_url = f"http://localhost:8766/events/gestures/{client_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(sse_url) as response:
                    print(f"📡 Connected to SSE stream: {sse_url}")
                    
                    async for line in response.content:
                        if line:
                            await self._process_sse_event(line.decode('utf-8'))
                            
        except Exception as e:
            print(f"❌ SSE connection failed: {e}")
            
    async def _process_sse_event(self, line: str):
        """Process incoming SSE event"""
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])  # Remove "data: " prefix
                event_type = data.get("event_type", "")
                
                if event_type == "GESTURE_DETECTED":
                    await self._handle_dashboard_gesture(data)
                elif event_type == "PRESENCE_CHANGED":
                    await self._handle_dashboard_presence(data)
                    
            except json.JSONDecodeError:
                pass  # Ignore malformed events
                
    async def _handle_dashboard_gesture(self, data: Dict):
        """Handle gesture event for dashboard"""
        gesture_event = {
            "timestamp": datetime.now().isoformat(),
            "gesture_type": data.get("gesture_type", ""),
            "confidence": data.get("confidence", 0.0),
            "hand": data.get("hand", "unknown")
        }
        
        self.gesture_history.append(gesture_event)
        self.performance_metrics["total_gestures"] += 1
        
        # Keep only last 100 gesture events
        if len(self.gesture_history) > 100:
            self.gesture_history.pop(0)
            
        print(f"📊 Dashboard: {gesture_event['gesture_type']} gesture ({gesture_event['confidence']:.2f})")
        
    async def _handle_dashboard_presence(self, data: Dict):
        """Handle presence event for dashboard"""
        presence_event = {
            "timestamp": datetime.now().isoformat(),
            "human_present": data.get("human_present", False),
            "confidence": data.get("confidence", 0.0)
        }
        
        self.detection_history.append(presence_event)
        
        if presence_event["human_present"]:
            self.performance_metrics["total_detections"] += 1
            self.performance_metrics["last_detection"] = presence_event["timestamp"]
            
        # Keep only last 1000 detection events
        if len(self.detection_history) > 1000:
            self.detection_history.pop(0)
            
        print(f"📊 Dashboard: {'Human present' if presence_event['human_present'] else 'No human'} "
              f"({presence_event['confidence']:.2f})")
              
    def get_dashboard_data(self) -> Dict:
        """Get current dashboard data"""
        uptime_seconds = (datetime.now() - self.performance_metrics["uptime_start"]).total_seconds()
        
        # Calculate recent activity (last 5 minutes)
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        recent_gestures = [
            g for g in self.gesture_history
            if datetime.fromisoformat(g["timestamp"]) > five_minutes_ago
        ]
        
        recent_detections = [
            d for d in self.detection_history
            if datetime.fromisoformat(d["timestamp"]) > five_minutes_ago and d["human_present"]
        ]
        
        return {
            "current_status": {
                "uptime_seconds": int(uptime_seconds),
                "last_detection": self.performance_metrics["last_detection"],
                "service_healthy": True
            },
            "statistics": {
                "total_detections": self.performance_metrics["total_detections"],
                "total_gestures": self.performance_metrics["total_gestures"],
                "recent_gestures_5min": len(recent_gestures),
                "recent_detections_5min": len(recent_detections)
            },
            "recent_events": {
                "gestures": self.gesture_history[-10:],  # Last 10 gestures
                "detections": self.detection_history[-20:]  # Last 20 detections
            },
            "gesture_breakdown": self._get_gesture_breakdown()
        }
        
    def _get_gesture_breakdown(self) -> Dict[str, int]:
        """Get gesture type breakdown"""
        breakdown = {}
        for gesture in self.gesture_history:
            gesture_type = gesture["gesture_type"]
            breakdown[gesture_type] = breakdown.get(gesture_type, 0) + 1
        return breakdown
        
    async def simulate_dashboard_updates(self, duration_seconds: int = 60):
        """Simulate dashboard with live updates"""
        print(f"📊 Simulating dashboard for {duration_seconds} seconds...")
        print("Dashboard features:")
        print("- Real-time detection status")
        print("- Live gesture feed")
        print("- Performance metrics")
        print("- Historical data")
        print()
        
        # Simulate events
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # Simulate some detection data
            await self._handle_dashboard_presence({
                "human_present": True,
                "confidence": 0.85
            })
            
            await asyncio.sleep(2)
            
            # Simulate gesture
            gestures = ["Thumb_Up", "Victory", "Open_Palm", "Pointing_Up"]
            import random
            gesture = random.choice(gestures)
            
            await self._handle_dashboard_gesture({
                "gesture_type": gesture,
                "confidence": random.uniform(0.7, 0.95),
                "hand": random.choice(["left", "right"])
            })
            
            await asyncio.sleep(3)
            
            # Print dashboard summary every 10 seconds
            if int(time.time() - start_time) % 10 == 0:
                data = self.get_dashboard_data()
                print(f"\n📊 Dashboard Update:")
                print(f"   Uptime: {data['current_status']['uptime_seconds']}s")
                print(f"   Total detections: {data['statistics']['total_detections']}")
                print(f"   Total gestures: {data['statistics']['total_gestures']}")
                print(f"   Recent activity (5min): {data['statistics']['recent_gestures_5min']} gestures")
                
        final_data = self.get_dashboard_data()
        print(f"\n📊 Dashboard Demo Summary:")
        print(f"   Final statistics: {final_data['statistics']}")
        print(f"   Gesture breakdown: {final_data['gesture_breakdown']}")


class MicroserviceIntegration:
    """
    Example 3: Microservice Architecture Integration
    
    Demonstrates how to integrate webcam detection into a microservice architecture:
    - Health check endpoints
    - Circuit breaker patterns
    - Load balancing considerations
    - Service discovery integration
    """
    
    def __init__(self):
        self.service_registry = {}
        self.health_status = "healthy"
        self.circuit_breaker_state = "closed"  # closed, open, half-open
        self.failure_count = 0
        self.last_failure_time = None
        
    def initialize(self):
        """Initialize microservice integration"""
        print("🔧 Initializing microservice integration...")
        
        # Register with service discovery
        self._register_service()
        
        print("✅ Microservice integration ready")
        
    def _register_service(self):
        """Register service with discovery system"""
        service_config = {
            "service_name": "webcam-detection",
            "version": "3.0.0",
            "endpoints": {
                "health": "http://localhost:8767/health",
                "presence": "http://localhost:8767/presence",
                "gestures": "http://localhost:8766/events/gestures",
                "metrics": "http://localhost:8767/statistics"
            },
            "capabilities": [
                "human_detection",
                "gesture_recognition",
                "real_time_streaming",
                "ai_descriptions"
            ],
            "dependencies": ["camera", "mediapipe", "ollama?"]
        }
        
        self.service_registry["webcam-detection"] = service_config
        print(f"🔧 Service registered: {service_config['service_name']}")
        
    async def health_check_with_circuit_breaker(self) -> Dict:
        """Enhanced health check with circuit breaker pattern"""
        if self.circuit_breaker_state == "open":
            # Check if we should try half-open
            if (self.last_failure_time and 
                time.time() - self.last_failure_time > 30):  # 30 second timeout
                self.circuit_breaker_state = "half-open"
            else:
                return {
                    "status": "circuit_breaker_open",
                    "healthy": False,
                    "circuit_state": self.circuit_breaker_state,
                    "failure_count": self.failure_count
                }
                
        try:
            # Perform actual health check
            health_response = await self._perform_health_check()
            
            if health_response["healthy"]:
                # Reset circuit breaker on success
                if self.circuit_breaker_state == "half-open":
                    self.circuit_breaker_state = "closed"
                    self.failure_count = 0
                    print("🔧 Circuit breaker reset to closed")
                    
                return health_response
            else:
                raise Exception("Health check failed")
                
        except Exception as e:
            return await self._handle_health_check_failure(e)
            
    async def _perform_health_check(self) -> Dict:
        """Perform detailed health check"""
        try:
            # Check webcam detection service
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:8767/health", timeout=5.0) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            "status": "healthy",
                            "healthy": True,
                            "circuit_state": self.circuit_breaker_state,
                            "components": {
                                "http_service": True,
                                "camera": True,  # Would check actual camera
                                "detection": True,  # Would check detection models
                                "ollama": data.get("ollama_available", False)
                            },
                            "metrics": data
                        }
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
        except Exception as e:
            raise Exception(f"Health check failed: {e}")
            
    async def _handle_health_check_failure(self, error: Exception) -> Dict:
        """Handle health check failure with circuit breaker logic"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        # Open circuit breaker after 3 failures
        if self.failure_count >= 3 and self.circuit_breaker_state == "closed":
            self.circuit_breaker_state = "open"
            print(f"🔧 Circuit breaker opened after {self.failure_count} failures")
            
        return {
            "status": "unhealthy",
            "healthy": False,
            "circuit_state": self.circuit_breaker_state,
            "failure_count": self.failure_count,
            "error": str(error),
            "last_failure": self.last_failure_time
        }
        
    def get_service_metadata(self) -> Dict:
        """Get service metadata for discovery"""
        return {
            "service_info": self.service_registry.get("webcam-detection", {}),
            "runtime_info": {
                "uptime_seconds": int(time.time()),  # Would track actual uptime
                "health_status": self.health_status,
                "circuit_breaker_state": self.circuit_breaker_state,
                "failure_count": self.failure_count
            },
            "load_balancer_weights": {
                "cpu_usage": 0.3,  # Would get actual CPU usage
                "memory_usage": 0.2,  # Would get actual memory usage
                "active_connections": 5,  # Would get actual connection count
                "response_time_ms": 45  # Would track actual response times
            }
        }
        
    async def simulate_microservice_monitoring(self, duration_seconds: int = 60):
        """Simulate microservice monitoring and discovery"""
        print(f"🔧 Simulating microservice monitoring for {duration_seconds} seconds...")
        print("Microservice features:")
        print("- Service discovery registration")
        print("- Health checks with circuit breaker")
        print("- Load balancing metadata")
        print("- Failure recovery patterns")
        print()
        
        start_time = time.time()
        health_checks = 0
        
        while time.time() - start_time < duration_seconds:
            # Perform health check every 5 seconds
            health_result = await self.health_check_with_circuit_breaker()
            health_checks += 1
            
            print(f"🏥 Health check #{health_checks}: {health_result['status']} "
                  f"(circuit: {health_result.get('circuit_state', 'unknown')})")
                  
            # Simulate occasional failures to test circuit breaker
            if health_checks == 3:
                print("🚨 Simulating service failure...")
                self.failure_count = 3
                self.circuit_breaker_state = "open"
                self.last_failure_time = time.time()
                
            # Show service metadata
            if health_checks % 3 == 0:
                metadata = self.get_service_metadata()
                print(f"📋 Service metadata: {metadata['runtime_info']}")
                
            await asyncio.sleep(5)
            
        print(f"\n🔧 Microservice Demo Summary:")
        print(f"   Health checks performed: {health_checks}")
        print(f"   Final circuit state: {self.circuit_breaker_state}")
        print(f"   Failure count: {self.failure_count}")


async def main():
    """Run advanced integration examples"""
    print("🚀 Advanced Integration Patterns")
    print("="*50)
    
    examples = {
        "1": ("Smart Home Automation", SmartHomeIntegration),
        "2": ("Web Dashboard Integration", WebDashboardIntegration),
        "3": ("Microservice Architecture", MicroserviceIntegration)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}: {name}")
        
    choice = input("\nSelect example (1-3, or 'all'): ").strip()
    
    if choice.lower() == 'all':
        # Run all examples
        for key, (name, example_class) in examples.items():
            print(f"\n{'='*60}")
            print(f"Running Example {key}: {name}")
            print('='*60)
            
            if example_class == SmartHomeIntegration:
                config = SmartHomeConfig()
                example = example_class(config)
            else:
                example = example_class()
                
            try:
                example.initialize()
                
                if hasattr(example, 'run_demo'):
                    await example.run_demo(20)
                elif hasattr(example, 'simulate_dashboard_updates'):
                    await example.simulate_dashboard_updates(20)
                elif hasattr(example, 'simulate_microservice_monitoring'):
                    await example.simulate_microservice_monitoring(20)
                    
            except KeyboardInterrupt:
                print("\n⏹️ Example interrupted")
                
    elif choice in examples:
        name, example_class = examples[choice]
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)
        
        if example_class == SmartHomeIntegration:
            config = SmartHomeConfig()
            example = example_class(config)
        else:
            example = example_class()
            
        try:
            example.initialize()
            duration = int(input("Duration in seconds (default 60): ") or "60")
            
            if hasattr(example, 'run_demo'):
                await example.run_demo(duration)
            elif hasattr(example, 'simulate_dashboard_updates'):
                await example.simulate_dashboard_updates(duration)
            elif hasattr(example, 'simulate_microservice_monitoring'):
                await example.simulate_microservice_monitoring(duration)
                
        except KeyboardInterrupt:
            print("\n⏹️ Demo interrupted")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    asyncio.run(main()) 