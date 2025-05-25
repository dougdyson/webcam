#!/usr/bin/env python3
"""
VOICE LIBRARY INTEGRATION EXAMPLES
=================================

Specific examples for integrating gesture recognition with popular voice libraries:
- speech_recognition + pyttsx3
- OpenAI Whisper + ElevenLabs
- Azure Speech Services
- Google Cloud Speech

Each example shows how to pause/resume on hand up gestures.
"""

import requests
import json
import threading
import time
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Base Gesture Integration Class (Reusable)
# ============================================================================

class GestureIntegration:
    """Reusable gesture integration for any voice library."""
    
    def __init__(self, client_id="voice_app", on_pause=None, on_resume=None):
        self.client_id = client_id
        self.sse_url = f"http://localhost:8766/events/gestures/{client_id}"
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.is_paused = False
        self.is_connected = False
        self.sse_thread = None
        
    def start(self):
        """Start gesture monitoring."""
        self.is_connected = True
        self.sse_thread = threading.Thread(target=self._sse_listener, daemon=True)
        self.sse_thread.start()
        
    def stop(self):
        """Stop gesture monitoring."""
        self.is_connected = False
        
    def _sse_listener(self):
        """Listen for SSE gesture events."""
        while self.is_connected:
            try:
                response = requests.get(
                    self.sse_url,
                    stream=True,
                    headers={'Accept': 'text/event-stream'},
                    timeout=(10, None)
                )
                
                for line in response.iter_lines(decode_unicode=True):
                    if not self.is_connected:
                        break
                        
                    if line and line.startswith('data:'):
                        try:
                            data = json.loads(line[5:].strip())
                            self._handle_event(data)
                        except json.JSONDecodeError:
                            continue
                            
            except requests.RequestException:
                if self.is_connected:
                    time.sleep(3)  # Reconnect delay
                    
    def _handle_event(self, data):
        """Handle gesture events."""
        event_type = data.get('event_type', '')
        gesture_type = data.get('gesture_type', '')
        
        if event_type == "gesture_detected" and gesture_type == "hand_up":
            if not self.is_paused:
                self.is_paused = True
                if self.on_pause:
                    self.on_pause()
                    
        elif event_type == "gesture_lost":
            if self.is_paused:
                self.is_paused = False
                if self.on_resume:
                    self.on_resume()


# ============================================================================
# Speech Recognition + pyttsx3 Integration
# ============================================================================

def speech_recognition_pyttsx3_example():
    """Integration with speech_recognition and pyttsx3 libraries."""
    
    code_example = '''
# Install: pip install speechrecognition pyttsx3 pyaudio
import speech_recognition as sr
import pyttsx3
import threading
from voice_library_examples import GestureIntegration

class SpeechRecognitionVoiceBot:
    def __init__(self):
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize text-to-speech
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 150)  # Speed
        self.tts.setProperty('volume', 0.8)  # Volume
        
        # State
        self.is_listening = False
        self.is_speaking = False
        
        # Setup gesture integration
        self.gesture = GestureIntegration(
            client_id="speechrec_bot",
            on_pause=self.pause_voice_processing,
            on_resume=self.resume_voice_processing
        )
        
    def start(self):
        """Start the voice bot."""
        print("🚀 Starting Speech Recognition Voice Bot")
        self.gesture.start()
        self.main_loop()
        
    def pause_voice_processing(self):
        """Pause on hand up gesture."""
        print("🤚 PAUSED: Hand up detected")
        
        # Stop current speech
        if self.is_speaking:
            self.tts.stop()
            
        # Note: speech_recognition doesn't have a clean pause,
        # so we use a flag to skip processing
        
    def resume_voice_processing(self):
        """Resume when gesture ends."""
        print("▶️ RESUMED: Hand down")
        
    def speak(self, text):
        """Speak text if not paused."""
        if self.gesture.is_paused:
            print(f"🔇 Speech blocked: {text}")
            return
            
        self.is_speaking = True
        print(f"🗣️ Speaking: {text}")
        self.tts.say(text)
        self.tts.runAndWait()
        self.is_speaking = False
        
    def listen(self):
        """Listen for speech if not paused."""
        if self.gesture.is_paused:
            return None
            
        try:
            self.is_listening = True
            print("👂 Listening...")
            
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=2.0)
                
            text = self.recognizer.recognize_google(audio)
            print(f"👤 Heard: {text}")
            return text
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("❓ Could not understand")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return None
        finally:
            self.is_listening = False
            
    def main_loop(self):
        """Main conversation loop."""
        self.speak("Hello! I'm your voice assistant. Try making hand gestures!")
        
        while True:
            try:
                text = self.listen()
                if text:
                    response = f"You said: {text}"
                    self.speak(response)
                    
            except KeyboardInterrupt:
                print("👋 Goodbye!")
                break
                
        self.gesture.stop()

# Usage
if __name__ == "__main__":
    bot = SpeechRecognitionVoiceBot()
    bot.start()
    '''
    
    return code_example


# ============================================================================
# OpenAI Whisper + ElevenLabs Integration
# ============================================================================

def whisper_elevenlabs_example():
    """Integration with OpenAI Whisper and ElevenLabs TTS."""
    
    code_example = '''
# Install: pip install openai-whisper elevenlabs pyaudio numpy
import whisper
import pyaudio
import numpy as np
from elevenlabs import generate, play, set_api_key
from voice_library_examples import GestureIntegration
import threading
import queue

class WhisperElevenLabsBot:
    def __init__(self, elevenlabs_api_key):
        # Initialize Whisper
        self.whisper_model = whisper.load_model("base")
        
        # Initialize ElevenLabs
        set_api_key(elevenlabs_api_key)
        self.voice_name = "Bella"  # Or your preferred voice
        
        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.audio_queue = queue.Queue()
        
        # State
        self.is_recording = False
        self.current_stream = None
        
        # Setup gesture integration
        self.gesture = GestureIntegration(
            client_id="whisper_bot",
            on_pause=self.pause_audio,
            on_resume=self.resume_audio
        )
        
    def start(self):
        """Start the voice bot."""
        print("🚀 Starting Whisper + ElevenLabs Voice Bot")
        self.gesture.start()
        self.start_recording()
        self.main_loop()
        
    def pause_audio(self):
        """Pause on hand up gesture."""
        print("🤚 PAUSED: Hand up detected")
        self.stop_recording()
        
    def resume_audio(self):
        """Resume when gesture ends."""
        print("▶️ RESUMED: Hand down")
        self.start_recording()
        
    def start_recording(self):
        """Start audio recording."""
        if not self.is_recording and not self.gesture.is_paused:
            self.is_recording = True
            self.current_stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            self.current_stream.start_stream()
            print("🎤 Recording started")
            
    def stop_recording(self):
        """Stop audio recording."""
        if self.is_recording:
            self.is_recording = False
            if self.current_stream:
                self.current_stream.stop_stream()
                self.current_stream.close()
                self.current_stream = None
            print("🔇 Recording stopped")
            
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio input callback."""
        if self.is_recording and not self.gesture.is_paused:
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            self.audio_queue.put(audio_data)
        return (None, pyaudio.paContinue)
        
    def speak(self, text):
        """Speak using ElevenLabs if not paused."""
        if self.gesture.is_paused:
            print(f"🔇 Speech blocked: {text}")
            return
            
        print(f"🗣️ Speaking: {text}")
        try:
            audio = generate(
                text=text,
                voice=self.voice_name,
                model="eleven_monolingual_v1"
            )
            play(audio)
        except Exception as e:
            print(f"❌ TTS error: {e}")
            
    def process_audio_buffer(self):
        """Process accumulated audio with Whisper."""
        if self.audio_queue.empty() or self.gesture.is_paused:
            return None
            
        # Collect audio chunks
        audio_data = []
        while not self.audio_queue.empty():
            audio_data.append(self.audio_queue.get())
            
        if not audio_data:
            return None
            
        # Combine and process with Whisper
        combined_audio = np.concatenate(audio_data)
        
        try:
            result = self.whisper_model.transcribe(combined_audio)
            text = result["text"].strip()
            
            if text:
                print(f"👤 Heard: {text}")
                return text
                
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            
        return None
        
    def main_loop(self):
        """Main conversation loop."""
        self.speak("Hello! I'm powered by Whisper and ElevenLabs. Try hand gestures!")
        
        while True:
            try:
                time.sleep(2)  # Process every 2 seconds
                
                text = self.process_audio_buffer()
                if text:
                    response = f"I heard you say: {text}"
                    self.speak(response)
                    
            except KeyboardInterrupt:
                print("👋 Goodbye!")
                break
                
        self.stop_recording()
        self.gesture.stop()

# Usage
if __name__ == "__main__":
    api_key = "your_elevenlabs_api_key"  # Get from elevenlabs.io
    bot = WhisperElevenLabsBot(api_key)
    bot.start()
    '''
    
    return code_example


# ============================================================================
# Azure Speech Services Integration
# ============================================================================

def azure_speech_example():
    """Integration with Azure Speech Services."""
    
    code_example = '''
# Install: pip install azure-cognitiveservices-speech
import azure.cognitiveservices.speech as speechsdk
from voice_library_examples import GestureIntegration
import threading

class AzureSpeechBot:
    def __init__(self, speech_key, speech_region):
        # Initialize Azure Speech
        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key, 
            region=speech_region
        )
        speech_config.speech_recognition_language = "en-US"
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        
        # Create recognizer and synthesizer
        self.speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)
        self.speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        
        # State
        self.is_listening = False
        self.current_recognition = None
        
        # Setup gesture integration
        self.gesture = GestureIntegration(
            client_id="azure_bot",
            on_pause=self.pause_speech,
            on_resume=self.resume_speech
        )
        
    def start(self):
        """Start the voice bot."""
        print("🚀 Starting Azure Speech Voice Bot")
        self.gesture.start()
        self.main_loop()
        
    def pause_speech(self):
        """Pause on hand up gesture."""
        print("🤚 PAUSED: Hand up detected")
        
        # Stop current recognition
        if self.current_recognition:
            try:
                self.current_recognition.stop_continuous_recognition()
            except:
                pass
                
    def resume_speech(self):
        """Resume when gesture ends."""
        print("▶️ RESUMED: Hand down")
        
    def speak(self, text):
        """Speak using Azure TTS if not paused."""
        if self.gesture.is_paused:
            print(f"🔇 Speech blocked: {text}")
            return
            
        print(f"🗣️ Speaking: {text}")
        try:
            result = self.speech_synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print("✅ Speech synthesis completed")
            else:
                print(f"❌ Speech synthesis failed: {result.reason}")
                
        except Exception as e:
            print(f"❌ TTS error: {e}")
            
    def listen(self):
        """Listen for speech if not paused."""
        if self.gesture.is_paused:
            return None
            
        try:
            print("👂 Listening...")
            self.is_listening = True
            
            result = self.speech_recognizer.recognize_once()
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print(f"👤 Heard: {result.text}")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("❓ No speech recognized")
            elif result.reason == speechsdk.ResultReason.Canceled:
                print("❌ Recognition canceled")
                
        except Exception as e:
            print(f"❌ Recognition error: {e}")
        finally:
            self.is_listening = False
            
        return None
        
    def main_loop(self):
        """Main conversation loop."""
        self.speak("Hello! I'm powered by Azure Speech Services. Try hand gestures!")
        
        while True:
            try:
                text = self.listen()
                if text:
                    response = f"You said: {text}"
                    self.speak(response)
                    
            except KeyboardInterrupt:
                print("👋 Goodbye!")
                break
                
        self.gesture.stop()

# Usage
if __name__ == "__main__":
    speech_key = "your_azure_speech_key"
    speech_region = "your_azure_region"  # e.g., "eastus"
    
    bot = AzureSpeechBot(speech_key, speech_region)
    bot.start()
    '''
    
    return code_example


# ============================================================================
# Google Cloud Speech Integration
# ============================================================================

def google_cloud_speech_example():
    """Integration with Google Cloud Speech-to-Text and Text-to-Speech."""
    
    code_example = '''
# Install: pip install google-cloud-speech google-cloud-texttospeech pyaudio
from google.cloud import speech
from google.cloud import texttospeech
import pyaudio
import io
from voice_library_examples import GestureIntegration

class GoogleCloudSpeechBot:
    def __init__(self):
        # Initialize Google Cloud clients
        self.speech_client = speech.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
        
        # Configure speech recognition
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        
        # Configure text-to-speech
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
            name="en-US-Wavenet-F"
        )
        
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )
        
        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.sample_rate = 16000
        self.chunk_size = 1024
        
        # Setup gesture integration
        self.gesture = GestureIntegration(
            client_id="gcloud_bot",
            on_pause=self.pause_audio,
            on_resume=self.resume_audio
        )
        
    def start(self):
        """Start the voice bot."""
        print("🚀 Starting Google Cloud Speech Voice Bot")
        self.gesture.start()
        self.main_loop()
        
    def pause_audio(self):
        """Pause on hand up gesture."""
        print("🤚 PAUSED: Hand up detected")
        
    def resume_audio(self):
        """Resume when gesture ends."""
        print("▶️ RESUMED: Hand down")
        
    def speak(self, text):
        """Speak using Google Cloud TTS if not paused."""
        if self.gesture.is_paused:
            print(f"🔇 Speech blocked: {text}")
            return
            
        print(f"🗣️ Speaking: {text}")
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=self.voice,
                audio_config=self.audio_config
            )
            
            # Play the audio
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True
            )
            
            stream.write(response.audio_content)
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"❌ TTS error: {e}")
            
    def listen(self):
        """Listen for speech if not paused."""
        if self.gesture.is_paused:
            return None
            
        try:
            print("👂 Listening...")
            
            # Record audio
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            frames = []
            for _ in range(0, int(self.sample_rate / self.chunk_size * 3)):  # 3 seconds
                if self.gesture.is_paused:
                    break
                data = stream.read(self.chunk_size)
                frames.append(data)
                
            stream.stop_stream()
            stream.close()
            
            if not frames or self.gesture.is_paused:
                return None
                
            # Convert to Google Cloud format
            audio_data = b''.join(frames)
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Recognize speech
            response = self.speech_client.recognize(
                config=self.config,
                audio=audio
            )
            
            for result in response.results:
                text = result.alternatives[0].transcript
                print(f"👤 Heard: {text}")
                return text
                
        except Exception as e:
            print(f"❌ Recognition error: {e}")
            
        return None
        
    def main_loop(self):
        """Main conversation loop."""
        self.speak("Hello! I'm powered by Google Cloud Speech. Try hand gestures!")
        
        while True:
            try:
                text = self.listen()
                if text:
                    response = f"You said: {text}"
                    self.speak(response)
                    
            except KeyboardInterrupt:
                print("👋 Goodbye!")
                break
                
        self.gesture.stop()

# Usage
if __name__ == "__main__":
    # Note: Requires GOOGLE_APPLICATION_CREDENTIALS environment variable
    # export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
    
    bot = GoogleCloudSpeechBot()
    bot.start()
    '''
    
    return code_example


# ============================================================================
# Main Examples
# ============================================================================

def main():
    """Show all integration examples."""
    
    print("Voice Library Integration Examples")
    print("=" * 40)
    print()
    
    examples = {
        "1": ("Speech Recognition + pyttsx3", speech_recognition_pyttsx3_example),
        "2": ("OpenAI Whisper + ElevenLabs", whisper_elevenlabs_example),
        "3": ("Azure Speech Services", azure_speech_example),
        "4": ("Google Cloud Speech", google_cloud_speech_example),
    }
    
    for key, (name, _) in examples.items():
        print(f"{key}. {name}")
    
    print("\nEnter choice (1-4) or 'all' to see all examples:")
    choice = input().strip()
    
    if choice == "all":
        for name, func in examples.values():
            print(f"\n{'='*60}")
            print(f"EXAMPLE: {name}")
            print(f"{'='*60}")
            print(func())
            
    elif choice in examples:
        name, func = examples[choice]
        print(f"\n{'='*60}")
        print(f"EXAMPLE: {name}")
        print(f"{'='*60}")
        print(func())
        
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main() 