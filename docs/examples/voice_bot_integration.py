"""
Voice Bot Integration Guide for Webcam Gesture Recognition
========================================================

This guide shows you how to integrate the webcam gesture recognition system
(specifically the "hand up" gesture) into your voice bot application using
Server-Sent Events (SSE) for real-time gesture detection.

QUICK START:
1. Start enhanced webcam service: conda activate webcam && python webcam_service.py
2. Use VoiceBotGestureIntegration class in your voice bot
3. Connect to SSE: http://localhost:8766/events/gestures/your_client_id
4. Handle gesture_detected events to pause/stop voice processing

FEATURES:
- HTTP API (port 8767): Human presence detection
- SSE Events (port 8766): Real-time gesture streaming  
- Gesture Recognition: Hand up detection with palm analysis
- Clean Console Output: Single updating status line (no scroll spam)

Console Output Example:
🎥 Frame 1250 | 👤 Human: YES (conf: 0.72) | 🖐️ Gesture: hand_up (conf: 0.95) | FPS: 28.5

Use Cases:
- "Hand up" gesture to pause voice assistant
- Stop/interrupt ongoing speech synthesis
- Pause audio processing during gestures
- Visual confirmation for voice commands
"""

import asyncio
import json
import logging
import threading
import time
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import queue

# SSE client libraries
try:
    import requests
    import sseclient  # pip install sseclient-py
    SSECLIENT_AVAILABLE = True
except ImportError:
    SSECLIENT_AVAILABLE = False

try:
    import httpx  # For async requests
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# ============================================================================
# Voice Bot Integration Classes
# ============================================================================

@dataclass
class GestureEvent:
    """Gesture event from SSE stream."""
    event_type: str  # "gesture_detected", "gesture_lost"
    gesture_type: str  # "hand_up"
    confidence: float
    hand: str  # "left", "right", "both"
    timestamp: datetime
    duration_ms: float = 0.0
    
    @classmethod
    def from_sse_data(cls, data: Dict[str, Any]) -> 'GestureEvent':
        """Create GestureEvent from SSE data."""
        return cls(
            event_type=data.get('event_type', 'unknown'),
            gesture_type=data.get('gesture_type', 'unknown'),
            confidence=data.get('confidence', 0.0),
            hand=data.get('hand', 'unknown'),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
            duration_ms=data.get('duration_ms', 0.0)
        )


class VoiceBotGestureIntegration:
    """Main integration class for connecting gesture detection to voice bot."""
    
    def __init__(self, 
                 client_id: str = "voice_bot",
                 gesture_service_url: str = "http://localhost:8766",
                 on_gesture_detected: Optional[Callable[[GestureEvent], None]] = None,
                 on_gesture_lost: Optional[Callable[[GestureEvent], None]] = None):
        """
        Initialize voice bot gesture integration.
        
        Args:
            client_id: Unique client identifier for SSE connection
            gesture_service_url: URL of the gesture SSE service
            on_gesture_detected: Callback when gesture is detected
            on_gesture_lost: Callback when gesture is lost
        """
        self.client_id = client_id
        self.gesture_service_url = gesture_service_url
        self.sse_url = f"{gesture_service_url}/events/gestures/{client_id}"
        
        # Callbacks
        self.on_gesture_detected = on_gesture_detected
        self.on_gesture_lost = on_gesture_lost
        
        # State
        self.is_connected = False
        self.current_gesture = None
        self.sse_thread = None
        self.event_queue = queue.Queue()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start gesture detection integration."""
        if self.is_connected:
            self.logger.warning("Already connected to gesture service")
            return
            
        self.logger.info(f"Starting gesture integration for voice bot: {self.client_id}")
        
        # Start SSE connection in separate thread
        self.sse_thread = threading.Thread(target=self._sse_listener, daemon=True)
        self.sse_thread.start()
        
        # Start event processor
        self.is_connected = True
        
    def stop(self):
        """Stop gesture detection integration."""
        self.logger.info("Stopping gesture integration")
        self.is_connected = False
        
        if self.sse_thread and self.sse_thread.is_alive():
            self.sse_thread.join(timeout=2.0)
            
    def _sse_listener(self):
        """SSE listener thread function."""
        while self.is_connected:
            try:
                self.logger.info(f"Connecting to SSE: {self.sse_url}")
                
                response = requests.get(
                    self.sse_url,
                    stream=True,
                    headers={'Accept': 'text/event-stream'},
                    timeout=(10, None)  # 10s connect, no read timeout
                )
                response.raise_for_status()
                
                # Parse SSE stream
                for line in response.iter_lines(decode_unicode=True):
                    if not self.is_connected:
                        break
                        
                    if line:
                        if line.startswith('event:'):
                            event_type = line[6:].strip()
                        elif line.startswith('data:'):
                            try:
                                data = json.loads(line[5:].strip())
                                self._handle_sse_event(event_type, data)
                            except json.JSONDecodeError as e:
                                self.logger.error(f"Failed to parse SSE data: {e}")
                                
            except requests.exceptions.RequestException as e:
                if self.is_connected:
                    self.logger.error(f"SSE connection error: {e}")
                    self.logger.info("Reconnecting in 5 seconds...")
                    time.sleep(5)
                    
    def _handle_sse_event(self, event_type: str, data: Dict[str, Any]):
        """Handle incoming SSE event."""
        try:
            gesture_event = GestureEvent.from_sse_data(data)
            
            if event_type == "gesture_detected":
                self.current_gesture = gesture_event
                self.logger.info(f"Gesture detected: {gesture_event.gesture_type} ({gesture_event.confidence:.2f})")
                
                if self.on_gesture_detected:
                    self.on_gesture_detected(gesture_event)
                    
            elif event_type == "gesture_lost":
                if self.current_gesture:
                    self.logger.info(f"Gesture lost: {self.current_gesture.gesture_type} (duration: {data.get('duration_ms', 0)}ms)")
                
                if self.on_gesture_lost:
                    self.on_gesture_lost(gesture_event)
                    
                self.current_gesture = None
                
        except Exception as e:
            self.logger.error(f"Error handling gesture event: {e}")
            
    def is_gesture_active(self) -> bool:
        """Check if a gesture is currently detected."""
        return self.current_gesture is not None
        
    def get_current_gesture(self) -> Optional[GestureEvent]:
        """Get current gesture if any."""
        return self.current_gesture


# ============================================================================
# Voice Bot Example Implementations
# ============================================================================

class SimpleVoiceBot:
    """Example voice bot with gesture integration."""
    
    def __init__(self):
        self.is_speaking = False
        self.is_listening = False
        self.speech_paused = False
        
        # Setup gesture integration
        self.gesture_integration = VoiceBotGestureIntegration(
            client_id="simple_voice_bot",
            on_gesture_detected=self.on_gesture_detected,
            on_gesture_lost=self.on_gesture_lost
        )
        
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start the voice bot with gesture detection."""
        self.logger.info("Starting voice bot with gesture detection")
        self.gesture_integration.start()
        
    def stop(self):
        """Stop the voice bot."""
        self.logger.info("Stopping voice bot")
        self.gesture_integration.stop()
        
    def on_gesture_detected(self, gesture_event: GestureEvent):
        """Handle gesture detection - pause voice processing."""
        if gesture_event.gesture_type == "hand_up":
            self.logger.info("Hand up detected - pausing voice bot")
            self.pause_speech()
            self.pause_listening()
            
    def on_gesture_lost(self, gesture_event: GestureEvent):
        """Handle gesture lost - resume voice processing."""
        self.logger.info("Hand down detected - resuming voice bot")
        self.resume_speech()
        self.resume_listening()
        
    def pause_speech(self):
        """Pause ongoing speech synthesis."""
        if self.is_speaking:
            self.speech_paused = True
            self.logger.info("🤚 Speech paused by gesture")
            # Your speech synthesis pause code here
            # e.g., pyttsx3_engine.stop()
            
    def resume_speech(self):
        """Resume speech synthesis."""
        if self.speech_paused:
            self.speech_paused = False
            self.logger.info("🗣️ Speech resumed")
            # Your speech synthesis resume code here
            
    def pause_listening(self):
        """Pause audio input processing."""
        if self.is_listening:
            self.logger.info("👂 Listening paused by gesture")
            # Your audio input pause code here
            # e.g., microphone.stop_listening()
            
    def resume_listening(self):
        """Resume audio input processing."""
        self.logger.info("👂 Listening resumed")
        # Your audio input resume code here
        
    def speak(self, text: str):
        """Speak text (mock implementation)."""
        if not self.speech_paused:
            self.is_speaking = True
            self.logger.info(f"Speaking: {text}")
            # Your TTS implementation here
            time.sleep(2)  # Mock speaking time
            self.is_speaking = False
            
    def listen(self) -> str:
        """Listen for voice input (mock implementation)."""
        if not self.gesture_integration.is_gesture_active():
            self.is_listening = True
            self.logger.info("Listening for voice input...")
            # Your STT implementation here
            time.sleep(1)  # Mock listening time
            self.is_listening = False
            return "Hello"  # Mock input
        return ""


class AdvancedVoiceBot:
    """Advanced voice bot with sophisticated gesture handling."""
    
    def __init__(self):
        self.conversation_state = "idle"  # idle, listening, speaking, processing
        self.gesture_timeout = 5.0  # Resume after 5 seconds of no gesture
        self.last_gesture_time = None
        
        # Setup gesture integration
        self.gesture_integration = VoiceBotGestureIntegration(
            client_id="advanced_voice_bot",
            on_gesture_detected=self.on_gesture_detected,
            on_gesture_lost=self.on_gesture_lost
        )
        
        # Audio processing components (mock)
        self.audio_processor = None
        self.speech_synthesizer = None
        self.conversation_manager = None
        
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start advanced voice bot."""
        self.logger.info("Starting advanced voice bot with gesture detection")
        self.gesture_integration.start()
        self._start_gesture_timeout_monitor()
        
    def stop(self):
        """Stop advanced voice bot."""
        self.gesture_integration.stop()
        
    def _start_gesture_timeout_monitor(self):
        """Monitor gesture timeout in background."""
        def timeout_monitor():
            while True:
                if (self.last_gesture_time and 
                    time.time() - self.last_gesture_time > self.gesture_timeout):
                    self._handle_gesture_timeout()
                    self.last_gesture_time = None
                time.sleep(1.0)
                
        threading.Thread(target=timeout_monitor, daemon=True).start()
        
    def on_gesture_detected(self, gesture_event: GestureEvent):
        """Advanced gesture handling with context awareness."""
        self.last_gesture_time = time.time()
        
        if gesture_event.gesture_type == "hand_up":
            if self.conversation_state == "speaking":
                self._interrupt_speech(gesture_event)
            elif self.conversation_state == "listening":
                self._pause_listening(gesture_event)
            elif self.conversation_state == "processing":
                self._cancel_processing(gesture_event)
                
    def on_gesture_lost(self, gesture_event: GestureEvent):
        """Handle gesture lost with smart resume logic."""
        # Don't immediately resume - wait for timeout or explicit resume
        self.logger.info(f"Gesture lost, will auto-resume in {self.gesture_timeout}s")
        
    def _interrupt_speech(self, gesture_event: GestureEvent):
        """Interrupt ongoing speech with gesture context."""
        self.logger.info(f"🤚 Speech interrupted by {gesture_event.hand} hand gesture")
        self.conversation_state = "paused"
        
        # Store speech state for potential resume
        # Your speech interruption logic here
        
    def _pause_listening(self, gesture_event: GestureEvent):
        """Pause listening with gesture context."""
        self.logger.info(f"👂 Listening paused by {gesture_event.hand} hand gesture")
        self.conversation_state = "paused"
        
        # Your listening pause logic here
        
    def _cancel_processing(self, gesture_event: GestureEvent):
        """Cancel ongoing processing."""
        self.logger.info("⚙️ Processing cancelled by gesture")
        self.conversation_state = "cancelled"
        
        # Your processing cancellation logic here
        
    def _handle_gesture_timeout(self):
        """Handle gesture timeout - auto resume."""
        if self.conversation_state == "paused":
            self.logger.info("⏰ Gesture timeout - auto resuming voice bot")
            self.conversation_state = "idle"
            # Your auto-resume logic here


# ============================================================================
# Integration with Popular Voice Libraries
# ============================================================================

def integrate_with_speechrecognition():
    """Example integration with speech_recognition library."""
    
    example_code = '''
import speech_recognition as sr
import pyttsx3
from voice_bot_integration import VoiceBotGestureIntegration

class SpeechRecognitionBot:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts = pyttsx3.init()
        self.is_paused = False
        
        # Setup gesture integration
        self.gesture_integration = VoiceBotGestureIntegration(
            client_id="speechrec_bot",
            on_gesture_detected=self.pause_voice_processing,
            on_gesture_lost=self.resume_voice_processing
        )
        
    def start(self):
        self.gesture_integration.start()
        self.listen_continuously()
        
    def pause_voice_processing(self, gesture_event):
        """Pause on hand up gesture."""
        self.is_paused = True
        self.tts.stop()  # Stop TTS
        print("🤚 Voice processing paused by gesture")
        
    def resume_voice_processing(self, gesture_event):
        """Resume when gesture ends."""
        self.is_paused = False
        print("🗣️ Voice processing resumed")
        
    def listen_continuously(self):
        """Main listening loop with gesture awareness."""
        while True:
            if not self.is_paused:
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, timeout=1.0)
                    
                    text = self.recognizer.recognize_google(audio)
                    self.process_speech(text)
                    
                except sr.WaitTimeoutError:
                    pass  # Normal timeout
                except sr.UnknownValueError:
                    pass  # Could not understand
                    
    def process_speech(self, text):
        """Process recognized speech."""
        if not self.is_paused:
            response = f"You said: {text}"
            self.tts.say(response)
            self.tts.runAndWait()
    '''
    
    return example_code


def integrate_with_openai_whisper():
    """Example integration with OpenAI Whisper."""
    
    example_code = '''
import whisper
import pyaudio
import numpy as np
from voice_bot_integration import VoiceBotGestureIntegration

class WhisperVoiceBot:
    def __init__(self):
        self.model = whisper.load_model("base")
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.current_stream = None
        
        # Setup gesture integration
        self.gesture_integration = VoiceBotGestureIntegration(
            client_id="whisper_bot",
            on_gesture_detected=self.on_gesture_stop,
            on_gesture_lost=self.on_gesture_resume
        )
        
    def start(self):
        self.gesture_integration.start()
        self.start_recording()
        
    def on_gesture_stop(self, gesture_event):
        """Stop recording on hand up."""
        if self.is_recording:
            print("🤚 Recording stopped by gesture")
            self.stop_recording()
            
    def on_gesture_resume(self, gesture_event):
        """Resume recording when gesture ends."""
        if not self.is_recording:
            print("🎤 Recording resumed")
            self.start_recording()
            
    def start_recording(self):
        """Start audio recording."""
        self.is_recording = True
        self.current_stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )
        
    def stop_recording(self):
        """Stop audio recording."""
        self.is_recording = False
        if self.current_stream:
            self.current_stream.stop_stream()
            self.current_stream.close()
    '''
    
    return example_code


# ============================================================================
# HTTP Fallback Integration (if SSE not available)
# ============================================================================

class HTTPGesturePolling:
    """Fallback gesture detection via HTTP polling."""
    
    def __init__(self, 
                 gesture_service_url: str = "http://localhost:8767",
                 poll_interval: float = 0.1,
                 on_gesture_detected: Optional[Callable[[Dict], None]] = None):
        """
        Initialize HTTP gesture polling.
        
        Args:
            gesture_service_url: Base URL of HTTP service
            poll_interval: How often to check for gestures (seconds)
            on_gesture_detected: Callback for gesture detection
        """
        self.gesture_service_url = gesture_service_url
        self.poll_interval = poll_interval
        self.on_gesture_detected = on_gesture_detected
        
        self.is_polling = False
        self.last_gesture_state = False
        self.polling_thread = None
        
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start gesture polling."""
        self.is_polling = True
        self.polling_thread = threading.Thread(target=self._poll_gestures, daemon=True)
        self.polling_thread.start()
        
    def stop(self):
        """Stop gesture polling."""
        self.is_polling = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2.0)
            
    def _poll_gestures(self):
        """Polling loop for gesture detection."""
        while self.is_polling:
            try:
                # Check presence first
                response = requests.get(
                    f"{self.gesture_service_url}/presence/simple",
                    timeout=1.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    human_present = data.get("human_present", False)
                    
                    # Simplified gesture detection via presence
                    # In real implementation, you'd have a gesture-specific endpoint
                    if human_present and not self.last_gesture_state:
                        # Human appeared - potential gesture start
                        if self.on_gesture_detected:
                            self.on_gesture_detected({
                                "gesture_type": "presence_detected",
                                "confidence": data.get("confidence", 0.0),
                                "timestamp": datetime.now().isoformat()
                            })
                            
                    self.last_gesture_state = human_present
                    
            except requests.RequestException as e:
                self.logger.error(f"Gesture polling error: {e}")
                
            time.sleep(self.poll_interval)


# ============================================================================
# Production Integration Examples
# ============================================================================

class ProductionVoiceBotIntegration:
    """Production-ready voice bot integration with error handling."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "gesture_service_url": "http://localhost:8766",
            "client_id": "production_voice_bot",
            "auto_resume_timeout": 10.0,
            "max_reconnect_attempts": 5,
            "health_check_interval": 30.0
        }
        
        self.gesture_integration = None
        self.http_fallback = None
        self.health_check_thread = None
        self.is_running = False
        
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """Start production voice bot with robust error handling."""
        self.is_running = True
        
        try:
            # Try SSE first
            self.gesture_integration = VoiceBotGestureIntegration(
                client_id=self.config["client_id"],
                gesture_service_url=self.config["gesture_service_url"],
                on_gesture_detected=self.handle_gesture_detected,
                on_gesture_lost=self.handle_gesture_lost
            )
            self.gesture_integration.start()
            
            # Start health monitoring
            self._start_health_monitoring()
            
            self.logger.info("Production voice bot started with SSE gesture detection")
            
        except Exception as e:
            self.logger.error(f"SSE failed, falling back to HTTP: {e}")
            self._start_http_fallback()
            
    def _start_http_fallback(self):
        """Start HTTP polling as fallback."""
        self.http_fallback = HTTPGesturePolling(
            gesture_service_url=self.config["gesture_service_url"].replace(":8766", ":8767"),
            on_gesture_detected=self.handle_gesture_detected
        )
        self.http_fallback.start()
        
    def _start_health_monitoring(self):
        """Monitor gesture service health."""
        def health_monitor():
            while self.is_running:
                try:
                    # Check service health
                    response = requests.get(
                        f"{self.config['gesture_service_url']}/health",
                        timeout=5.0
                    )
                    
                    if response.status_code != 200:
                        self.logger.warning("Gesture service health check failed")
                        
                except Exception as e:
                    self.logger.error(f"Health check error: {e}")
                    
                time.sleep(self.config["health_check_interval"])
                
        self.health_check_thread = threading.Thread(target=health_monitor, daemon=True)
        self.health_check_thread.start()
        
    def handle_gesture_detected(self, gesture_event):
        """Production gesture handling with logging."""
        self.logger.info(f"Gesture detected in production: {gesture_event}")
        # Your production gesture handling here
        
    def handle_gesture_lost(self, gesture_event):
        """Production gesture lost handling."""
        self.logger.info(f"Gesture lost in production: {gesture_event}")
        # Your production gesture lost handling here
        
    def stop(self):
        """Stop production voice bot."""
        self.is_running = False
        
        if self.gesture_integration:
            self.gesture_integration.stop()
            
        if self.http_fallback:
            self.http_fallback.stop()


# ============================================================================
# Main Example and Testing
# ============================================================================

def main():
    """Main example showing voice bot integration."""
    
    print("Voice Bot Gesture Integration Examples")
    print("=====================================")
    print()
    
    print("1. Simple Voice Bot Example")
    print("2. Advanced Voice Bot Example")
    print("3. Production Integration Example")
    print("4. HTTP Fallback Example")
    print("5. Show Integration Code Examples")
    
    choice = input("\nEnter choice (1-5): ")
    
    if choice == "1":
        # Simple voice bot example
        bot = SimpleVoiceBot()
        bot.start()
        
        try:
            # Simulate voice bot operation
            for i in range(10):
                print(f"\n--- Voice Bot Cycle {i+1} ---")
                bot.speak(f"This is message {i+1}")
                response = bot.listen()
                print(f"User said: {response}")
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\nStopping voice bot...")
        finally:
            bot.stop()
            
    elif choice == "2":
        # Advanced voice bot example
        bot = AdvancedVoiceBot()
        bot.start()
        
        try:
            print("Advanced voice bot running... Press Ctrl+C to stop")
            print("Try making hand up gestures to see the interaction!")
            
            while True:
                time.sleep(1)
                print(f"Bot state: {bot.conversation_state}, Gesture active: {bot.gesture_integration.is_gesture_active()}")
                
        except KeyboardInterrupt:
            print("\nStopping advanced voice bot...")
        finally:
            bot.stop()
            
    elif choice == "3":
        # Production integration example
        bot = ProductionVoiceBotIntegration()
        bot.start()
        
        try:
            print("Production voice bot running... Press Ctrl+C to stop")
            while True:
                time.sleep(5)
                print("Production bot running with health monitoring...")
                
        except KeyboardInterrupt:
            print("\nStopping production voice bot...")
        finally:
            bot.stop()
            
    elif choice == "4":
        # HTTP fallback example
        def gesture_callback(gesture_data):
            print(f"HTTP Gesture detected: {gesture_data}")
            
        polling = HTTPGesturePolling(on_gesture_detected=gesture_callback)
        polling.start()
        
        try:
            print("HTTP gesture polling running... Press Ctrl+C to stop")
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\nStopping HTTP polling...")
        finally:
            polling.stop()
            
    elif choice == "5":
        # Show code examples
        print("\n=== Speech Recognition Integration ===")
        print(integrate_with_speechrecognition())
        
        print("\n=== OpenAI Whisper Integration ===")
        print(integrate_with_openai_whisper())
        
    else:
        print("Invalid choice")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main() 