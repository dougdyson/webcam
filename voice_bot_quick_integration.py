#!/usr/bin/env python3
"""
QUICK VOICE BOT INTEGRATION EXAMPLE
==================================

This is a minimal, practical example of how to integrate the webcam gesture 
recognition SSE service into your voice bot application.

STEPS TO USE:
1. Start webcam service: python webcam_http_service.py
2. Run this script: python voice_bot_quick_integration.py
3. Make hand up gestures to pause/resume the voice bot

The hand up gesture will:
- Pause ongoing speech synthesis
- Stop listening for voice input
- Resume when hand goes down
"""

import requests
import json
import threading
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QuickVoiceBotIntegration:
    """Minimal voice bot integration with gesture recognition."""
    
    def __init__(self, client_id="my_voice_bot"):
        self.client_id = client_id
        self.sse_url = f"http://localhost:8766/events/gestures/{client_id}"
        
        # Voice bot state
        self.is_paused = False
        self.is_speaking = False
        self.is_listening = False
        
        # SSE connection
        self.is_connected = False
        self.sse_thread = None
        
    def start(self):
        """Start gesture integration."""
        logger.info("🚀 Starting voice bot with gesture detection")
        
        # Start SSE listener in background
        self.is_connected = True
        self.sse_thread = threading.Thread(target=self._listen_for_gestures, daemon=True)
        self.sse_thread.start()
        
        logger.info("✅ Gesture integration active")
        logger.info("👆 Make a 'hand up' gesture to pause voice processing")
        
    def stop(self):
        """Stop gesture integration."""
        self.is_connected = False
        if self.sse_thread:
            self.sse_thread.join(timeout=2.0)
        logger.info("🛑 Gesture integration stopped")
        
    def _listen_for_gestures(self):
        """Background thread to listen for SSE gesture events."""
        while self.is_connected:
            try:
                logger.info(f"📡 Connecting to gesture stream: {self.sse_url}")
                
                response = requests.get(
                    self.sse_url,
                    stream=True,
                    headers={'Accept': 'text/event-stream'},
                    timeout=(10, None)
                )
                response.raise_for_status()
                
                # Parse SSE events
                for line in response.iter_lines(decode_unicode=True):
                    if not self.is_connected:
                        break
                        
                    if line and line.startswith('data:'):
                        try:
                            data = json.loads(line[5:].strip())
                            self._handle_gesture_event(data)
                        except json.JSONDecodeError:
                            continue
                            
            except requests.RequestException as e:
                if self.is_connected:
                    logger.error(f"❌ SSE connection error: {e}")
                    logger.info("🔄 Reconnecting in 3 seconds...")
                    time.sleep(3)
                    
    def _handle_gesture_event(self, data):
        """Handle incoming gesture events."""
        event_type = data.get('event_type', '')
        gesture_type = data.get('gesture_type', '')
        confidence = data.get('confidence', 0)
        
        if event_type == "gesture_detected" and gesture_type == "hand_up":
            logger.info(f"🤚 GESTURE DETECTED: Hand up (confidence: {confidence:.2f})")
            self.pause_voice_bot()
            
        elif event_type == "gesture_lost":
            logger.info("👋 GESTURE LOST: Hand down")
            self.resume_voice_bot()
            
    def pause_voice_bot(self):
        """Pause voice bot on gesture detection."""
        if not self.is_paused:
            self.is_paused = True
            logger.info("⏸️  VOICE BOT PAUSED")
            
            # Your pause logic here:
            # - Stop text-to-speech: tts_engine.stop()
            # - Pause audio recording: microphone.stop()
            # - Interrupt processing: cancel_current_task()
            
    def resume_voice_bot(self):
        """Resume voice bot when gesture ends."""
        if self.is_paused:
            self.is_paused = False
            logger.info("▶️  VOICE BOT RESUMED")
            
            # Your resume logic here:
            # - Resume text-to-speech: tts_engine.resume()
            # - Restart audio recording: microphone.start()
            # - Continue processing: resume_task()
            
    def speak(self, text):
        """Mock speech synthesis (replace with your TTS)."""
        if self.is_paused:
            logger.info(f"🔇 Speech blocked by gesture: '{text}'")
            return
            
        self.is_speaking = True
        logger.info(f"🗣️  Speaking: '{text}'")
        
        # Mock speaking (replace with your TTS implementation)
        # Example: pyttsx3_engine.say(text); pyttsx3_engine.runAndWait()
        time.sleep(2)  # Simulate speech duration
        
        self.is_speaking = False
        
    def listen(self):
        """Mock voice input (replace with your STT)."""
        if self.is_paused:
            logger.info("🔇 Listening blocked by gesture")
            return ""
            
        self.is_listening = True
        logger.info("👂 Listening for voice input...")
        
        # Mock listening (replace with your STT implementation)
        # Example: speech_recognition.recognize_google(audio)
        time.sleep(1)  # Simulate listening duration
        
        self.is_listening = False
        return "Hello"  # Mock user input


def main():
    """Main example demonstrating voice bot integration."""
    
    # Check if webcam service is running
    try:
        response = requests.get("http://localhost:8766/health", timeout=2)
        if response.status_code != 200:
            logger.error("❌ Webcam gesture service not responding")
            logger.info("💡 Please start: python webcam_http_service.py")
            return
    except requests.RequestException:
        logger.error("❌ Cannot connect to webcam gesture service")
        logger.info("💡 Please start: python webcam_http_service.py")
        return
        
    # Create and start voice bot with gesture integration
    voice_bot = QuickVoiceBotIntegration(client_id="demo_voice_bot")
    voice_bot.start()
    
    try:
        # Simulate voice bot conversation loop
        logger.info("\n🎙️  Starting voice bot simulation...")
        logger.info("👆 Try making hand up gestures to see them pause the bot!\n")
        
        for i in range(20):
            print(f"\n--- Voice Bot Cycle {i+1} ---")
            
            # Simulate speaking
            voice_bot.speak(f"This is message number {i+1}. I'm talking now.")
            
            # Simulate listening
            user_input = voice_bot.listen()
            if user_input:
                logger.info(f"👤 User said: '{user_input}'")
            
            # Show current state
            status = "PAUSED 🤚" if voice_bot.is_paused else "ACTIVE ▶️"
            logger.info(f"📊 Status: {status}")
            
            time.sleep(1)  # Brief pause between cycles
            
    except KeyboardInterrupt:
        logger.info("\n👋 Stopping voice bot...")
    finally:
        voice_bot.stop()


if __name__ == "__main__":
    print("🎤 Quick Voice Bot Gesture Integration")
    print("=" * 40)
    print()
    print("This demonstrates real-time gesture control of a voice bot.")
    print("Make 'hand up' gestures to pause/resume voice processing.")
    print()
    
    main() 