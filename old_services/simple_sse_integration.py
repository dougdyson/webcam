#!/usr/bin/env python3
"""
SIMPLE SSE GESTURE INTEGRATION
=============================

Practical guide for integrating gesture SSE events into your custom app.

QUICK INTEGRATION:
1. Start webcam service: python webcam_http_service.py
2. Connect to SSE: http://localhost:8766/events/gestures/your_client_id
3. Parse events and update your app state
"""

import requests
import json
import threading
import time
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

# ============================================================================
# DATA PAYLOAD FORMATS
# ============================================================================

"""
SSE EVENT PAYLOAD EXAMPLES:

1. GESTURE DETECTED:
event: gesture_detected
data: {
  "event_type": "gesture_detected",
  "timestamp": "2024-01-15T10:30:00.123456",
  "data": {
    "gesture_type": "hand_up",
    "confidence": 0.85,
    "hand": "right",
    "position": {
      "hand_x": 0.65,
      "hand_y": 0.25,
      "shoulder_reference_y": 0.45
    },
    "palm_facing_camera": true
  },
  "source": "webcam_detection"
}

2. GESTURE LOST:
event: gesture_lost
data: {
  "event_type": "gesture_lost",
  "timestamp": "2024-01-15T10:30:02.456789",
  "data": {
    "gesture_type": "hand_up",
    "duration_ms": 2333.333,
    "hand": "right"
  },
  "source": "webcam_detection"
}

3. HEARTBEAT (every 30s):
event: heartbeat
data: {
  "event_type": "heartbeat",
  "timestamp": "2024-01-15T10:30:30.000000",
  "data": {
    "active_connections": 3,
    "uptime_seconds": 1234.5
  },
  "source": "webcam_detection"
}
"""

# ============================================================================
# SIMPLE STATE MANAGEMENT
# ============================================================================

@dataclass
class GestureState:
    """Simple gesture state for your app."""
    is_gesture_active: bool = False
    gesture_type: Optional[str] = None
    confidence: float = 0.0
    hand: Optional[str] = None  # "left", "right", "both"
    last_detected: Optional[datetime] = None
    duration_ms: float = 0.0


class SimpleGestureIntegration:
    """Minimal SSE integration for custom apps."""
    
    def __init__(self, client_id: str, on_gesture_change: Optional[Callable[[GestureState], None]] = None):
        """
        Initialize gesture integration.
        
        Args:
            client_id: Unique identifier for your app
            on_gesture_change: Callback when gesture state changes
        """
        self.client_id = client_id
        self.sse_url = f"http://localhost:8766/events/gestures/{client_id}"
        self.on_gesture_change = on_gesture_change
        
        # State
        self.gesture_state = GestureState()
        self._connected = False
        self._thread = None
        
    def start(self):
        """Start listening for gesture events."""
        if self._connected:
            return
            
        self._connected = True
        self._thread = threading.Thread(target=self._sse_loop, daemon=True)
        self._thread.start()
        print(f"✅ Gesture integration started: {self.sse_url}")
        
    def stop(self):
        """Stop listening for gesture events."""
        self._connected = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("🛑 Gesture integration stopped")
        
    def get_state(self) -> GestureState:
        """Get current gesture state."""
        return self.gesture_state
        
    def is_gesture_active(self) -> bool:
        """Quick check if gesture is active."""
        return self.gesture_state.is_gesture_active
        
    def _sse_loop(self):
        """Main SSE listening loop."""
        while self._connected:
            try:
                print(f"📡 Connecting to SSE stream...")
                
                response = requests.get(
                    self.sse_url,
                    stream=True,
                    headers={'Accept': 'text/event-stream'},
                    timeout=(10, None)
                )
                response.raise_for_status()
                
                # Parse SSE stream
                for line in response.iter_lines(decode_unicode=True):
                    if not self._connected:
                        break
                        
                    if line and line.startswith('data:'):
                        try:
                            data = json.loads(line[5:].strip())
                            self._process_event(data)
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse SSE data: {e}")
                            
            except requests.RequestException as e:
                if self._connected:
                    print(f"❌ SSE connection error: {e}")
                    print("🔄 Reconnecting in 3 seconds...")
                    time.sleep(3)
                    
    def _process_event(self, data: dict):
        """Process incoming SSE event and update state."""
        event_type = data.get('event_type', '')
        event_data = data.get('data', {})
        
        if event_type == "gesture_detected":
            # Update state
            self.gesture_state.is_gesture_active = True
            self.gesture_state.gesture_type = event_data.get('gesture_type')
            self.gesture_state.confidence = event_data.get('confidence', 0.0)
            self.gesture_state.hand = event_data.get('hand')
            self.gesture_state.last_detected = datetime.fromisoformat(data.get('timestamp'))
            
            print(f"🤚 GESTURE DETECTED: {self.gesture_state.gesture_type} "
                  f"({self.gesture_state.confidence:.2f}) - {self.gesture_state.hand} hand")
            
            # Notify callback
            if self.on_gesture_change:
                self.on_gesture_change(self.gesture_state)
                
        elif event_type == "gesture_lost":
            # Update state
            self.gesture_state.is_gesture_active = False
            self.gesture_state.duration_ms = event_data.get('duration_ms', 0.0)
            
            print(f"👋 GESTURE LOST: {self.gesture_state.gesture_type} "
                  f"(duration: {self.gesture_state.duration_ms:.0f}ms)")
            
            # Notify callback
            if self.on_gesture_change:
                self.on_gesture_change(self.gesture_state)
                
        elif event_type == "heartbeat":
            # Optional: handle heartbeat
            connections = event_data.get('active_connections', 0)
            print(f"💓 Heartbeat: {connections} active connections")


# ============================================================================
# INTEGRATION EXAMPLES
# ============================================================================

def example_state_based_app():
    """Example: State-based app integration."""
    
    class MyApp:
        def __init__(self):
            self.app_paused = False
            self.processing_enabled = True
            
            # Setup gesture integration
            self.gestures = SimpleGestureIntegration(
                client_id="my_custom_app",
                on_gesture_change=self.handle_gesture_change
            )
            
        def start(self):
            """Start your app with gesture integration."""
            print("🚀 Starting my custom app...")
            self.gestures.start()
            
            # Your app main loop
            self.main_loop()
            
        def handle_gesture_change(self, state: GestureState):
            """Handle gesture state changes."""
            if state.is_gesture_active and state.gesture_type == "hand_up":
                self.pause_app()
            elif not state.is_gesture_active:
                self.resume_app()
                
        def pause_app(self):
            """Pause your app functionality."""
            self.app_paused = True
            self.processing_enabled = False
            print("⏸️ App paused by gesture")
            
        def resume_app(self):
            """Resume your app functionality."""
            self.app_paused = False
            self.processing_enabled = True
            print("▶️ App resumed")
            
        def main_loop(self):
            """Your app's main processing loop."""
            try:
                while True:
                    if not self.app_paused:
                        # Your app logic here
                        print(f"🔄 Processing... (paused: {self.app_paused})")
                        time.sleep(2)
                    else:
                        # App is paused, minimal processing
                        time.sleep(0.5)
                        
            except KeyboardInterrupt:
                print("🛑 Stopping app...")
                self.gestures.stop()
    
    # Run the example
    app = MyApp()
    app.start()


def example_simple_polling():
    """Example: Simple state polling."""
    
    def main():
        # Simple setup - just poll the state
        gestures = SimpleGestureIntegration(client_id="polling_app")
        gestures.start()
        
        try:
            while True:
                # Check gesture state
                if gestures.is_gesture_active():
                    print("🤚 Gesture is active - pausing my work")
                    # Your pause logic here
                else:
                    print("▶️ No gesture - doing my work")
                    # Your normal processing here
                    
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            print("🛑 Stopping...")
            gestures.stop()
    
    main()


def example_callback_based():
    """Example: Callback-based integration."""
    
    # Global state variable (or use class attribute)
    app_is_paused = False
    
    def on_gesture_change(state: GestureState):
        """Handle gesture changes."""
        global app_is_paused
        
        if state.is_gesture_active:
            app_is_paused = True
            print(f"🤚 PAUSED by {state.hand} hand gesture (confidence: {state.confidence:.2f})")
            # Your pause logic here
            
        else:
            app_is_paused = False
            print(f"▶️ RESUMED after {state.duration_ms:.0f}ms gesture")
            # Your resume logic here
    
    def main():
        # Setup with callback
        gestures = SimpleGestureIntegration(
            client_id="callback_app",
            on_gesture_change=on_gesture_change
        )
        gestures.start()
        
        try:
            # Your main app loop
            while True:
                if not app_is_paused:
                    print("🔄 Working...")
                    # Your app logic
                else:
                    print("😴 Paused...")
                    
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("🛑 Stopping...")
            gestures.stop()
    
    main()


# ============================================================================
# MINIMAL INTEGRATION (Just the essentials)
# ============================================================================

def minimal_example():
    """Absolute minimal integration example."""
    
    import requests
    import json
    import threading
    
    gesture_active = False  # Your state variable
    
    def listen_for_gestures():
        """Background thread to listen for gestures."""
        global gesture_active
        
        while True:
            try:
                response = requests.get(
                    "http://localhost:8766/events/gestures/minimal_app",
                    stream=True,
                    headers={'Accept': 'text/event-stream'},
                    timeout=(10, None)
                )
                
                for line in response.iter_lines(decode_unicode=True):
                    if line and line.startswith('data:'):
                        data = json.loads(line[5:].strip())
                        
                        if data.get('event_type') == "gesture_detected":
                            gesture_active = True
                            print("🤚 Gesture detected - pausing")
                            
                        elif data.get('event_type') == "gesture_lost":
                            gesture_active = False
                            print("▶️ Gesture lost - resuming")
                            
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(3)
    
    # Start listening in background
    threading.Thread(target=listen_for_gestures, daemon=True).start()
    
    # Your main app loop
    while True:
        if gesture_active:
            print("😴 App paused by gesture")
        else:
            print("🔄 App running normally")
        time.sleep(2)


# ============================================================================
# MAIN EXAMPLES
# ============================================================================

def main():
    """Run integration examples."""
    
    print("Simple SSE Gesture Integration Examples")
    print("=" * 45)
    print()
    print("1. State-based app (recommended)")
    print("2. Simple polling")
    print("3. Callback-based")
    print("4. Minimal example")
    print("5. Show data payload formats")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        example_state_based_app()
    elif choice == "2":
        example_simple_polling()
    elif choice == "3":
        example_callback_based()
    elif choice == "4":
        minimal_example()
    elif choice == "5":
        print(__doc__)  # Show the payload examples at the top
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main() 