#!/usr/bin/env python3
"""
Webcam Detection Service with Gesture Recognition

This service provides:
1. Real-time human presence detection via HTTP API (port 8767)
2. Hand gesture recognition with SSE streaming (port 8766) 
3. Gesture detection ONLY when humans are detected (performance optimized)

Usage:
    python webcam_service.py

HTTP Endpoints (port 8767):
    GET /presence/simple  - Boolean presence check
    GET /presence         - Full detection status
    GET /health           - Service health check
    GET /statistics       - Performance metrics

SSE Endpoints (port 8766):
    GET /events/gestures/{client_id}  - Real-time gesture events

Integration:
    - Your other apps connect to SSE for real-time gesture events
    - Only get gesture events when human is present (optimized)
    - HTTP API still works for presence detection
"""
import asyncio
import time
import threading
import signal
import sys
import logging
from typing import Optional
from datetime import datetime

# Core detection system
from src.detection import create_detector
from src.detection.gesture_detector import GestureDetector
from src.camera import CameraManager
from src.camera.config import CameraConfig
from src.processing.enhanced_frame_processor import EnhancedFrameProcessor, EnhancedProcessorConfig
from src.processing.latest_frame_processor import LatestFrameProcessor
from src.processing.reference_manager import ReferenceManager
from src.processing.presence_gate import PresenceGate, PresenceGateConfig

# Service layer
from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
from src.service.sse_service import SSEDetectionService, SSEServiceConfig
from src.service.sse_presence_service import SSEPresenceService
from src.service.events import EventPublisher, EventType, ServiceEvent

# Ollama integration (NEW - Phase 6.2)
from src.utils.config import ConfigManager
from src.ollama.client import OllamaClient, OllamaConfig
from src.ollama.description_service import DescriptionService, DescriptionServiceConfig
from src.ollama.image_processing import OllamaImageProcessor
from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
from src.ollama.vision_verifier import VisionPresenceVerifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')  # Show info, warnings, and errors
logger = logging.getLogger(__name__)

class WebcamService:
    """
    Webcam Detection Service with Gesture Recognition
    
    Provides both human presence detection AND gesture recognition:
    - HTTP API on port 8767 for presence detection
    - SSE streaming on port 8766 for gesture events
    - Gesture detection only runs when humans are detected
    """
    
    def __init__(self):
        # Core components
        self.camera = None
        self.detector = None
        self.gesture_detector = None
        self.frame_processor = None
        self.latest_frame_processor = None  # NEW: Latest Frame Processor for migration
        self.event_publisher = EventPublisher()
        
        # Services
        self.http_service = None
        self.sse_service = None
        self.presence_sse_service = None
        
        # Ollama integration (NEW - Phase 6.2)
        self.config_manager = None
        self.ollama_config = None
        self.ollama_client = None
        self.ollama_image_processor = None
        self.description_service = None
        self.vision_verifier = None

        # State
        self.is_running = False
        self._shutdown_requested = False
        self._description_service_failed = False
        
        # Presence gating
        self.reference_manager: Optional[ReferenceManager] = None
        self.presence_gate: Optional[PresenceGate] = None
        self._gating_enabled: bool = False
        
    def initialize(self):
        """Initialize all components with proper error handling."""
        try:
            # Step 1: Initialize configuration
            self.config_manager = ConfigManager()
            detection_cfg = {}
            try:
                detection_cfg = self.config_manager.load_detection_config()
            except Exception:
                detection_cfg = {}
            
            # Step 2: Initialize camera (quiet)
            camera_config = CameraConfig()
            self.camera = CameraManager(camera_config)
            
            # Step 3: Initialize multimodal detector (quiet)
            self.detector = create_detector('multimodal')
            self.detector.initialize()
            
            # Step 4: Initialize gesture detector
            self.gesture_detector = GestureDetector()
            self.gesture_detector.initialize()
            
            # Step 4.5: Initialize Latest Frame Processor (NEW - Phase 2.2)
            self.latest_frame_processor = LatestFrameProcessor(
                camera_manager=self.camera,
                detector=self.detector
            )
            
            # Step 5: Vision verification backend selection
            # Read verifier_backend from detection config
            vision_cfg = {}
            if isinstance(detection_cfg, dict):
                vision_cfg = detection_cfg.get('gating', {}).get('vision_verification', {})
            verifier_backend = vision_cfg.get('verifier_backend', 'neural')

            neural_initialized = False
            if verifier_backend == 'neural':
                try:
                    from src.detection.neural_presence_verifier import (
                        NeuralPresenceVerifier,
                        NeuralPresenceVerifierConfig,
                    )
                    neural_cfg_section = vision_cfg.get('neural', {})
                    neural_config = NeuralPresenceVerifierConfig(
                        prototxt_path=neural_cfg_section.get(
                            'prototxt_path', 'models/MobileNetSSD_deploy.prototxt'),
                        caffemodel_path=neural_cfg_section.get(
                            'caffemodel_path', 'models/MobileNetSSD_deploy.caffemodel'),
                        confidence_threshold=float(neural_cfg_section.get(
                            'confidence_threshold', 0.5)),
                        input_size=tuple(neural_cfg_section.get('input_size', [300, 300])),
                        cache_ttl_seconds=30,
                    )
                    neural_verifier = NeuralPresenceVerifier(neural_config)
                    neural_verifier.initialize()
                    self.vision_verifier = neural_verifier
                    neural_initialized = True
                    logger.info("✓ Vision verification enabled with MobileNet-SSD (neural)")
                except FileNotFoundError as e:
                    logger.warning(f"⚠ Neural model not found ({e}), falling back to Ollama")
                except Exception as e:
                    logger.warning(f"⚠ Neural verifier init failed ({e}), falling back to Ollama")

            # Ollama fallback (or explicit ollama backend)
            if not neural_initialized:
                try:
                    self.ollama_config = self.config_manager.load_ollama_config()
                    client_config = self.ollama_config.get('client', {})
                    ollama_cfg = OllamaConfig(
                        model=client_config.get('model', 'qwen3-vl:2b-instruct-q4_K_M'),
                        base_url=client_config.get('base_url', 'http://localhost:11434'),
                        timeout=client_config.get('timeout_seconds', 40.0),
                        max_retries=client_config.get('max_retries', 2)
                    )
                    self.ollama_client = OllamaClient(ollama_cfg)
                    self.vision_verifier = VisionPresenceVerifier(
                        ollama_client=self.ollama_client,
                        cache_ttl_seconds=30
                    )
                    if self.ollama_client.is_available():
                        logger.info(f"✓ Vision verification enabled with {ollama_cfg.model} (ollama)")
                    else:
                        logger.warning("⚠ Ollama service not available - vision verification will fail")
                except Exception as e:
                    logger.warning(f"⚠ Failed to initialize vision verification: {e}")
                    self.ollama_client = None
                    self.vision_verifier = None

            # DescriptionService remains disabled (we only need verification)
            self.description_service = None
            self.ollama_image_processor = None
            self._description_service_failed = False
            
            # DISABLED: Initialize enhanced frame processor with BALANCED SETTINGS (prevent false positives but still work)
            # processor_config = EnhancedProcessorConfig(
            #     min_human_confidence_for_gesture=0.4,  # Lower - your 0.54 confidence should work
            #     min_gesture_confidence_threshold=0.8,  # HIGH but not extreme - 80% confidence required
            #     enable_gesture_detection=True,
            #     publish_gesture_events=True,
            #     performance_monitoring=True,
            #     gesture_detection_every_n_frames=2,    # Every 2nd frame - balance between speed and accuracy
            #     max_gesture_fps=10.0                   # Moderate rate
            # )
            
            # self.frame_processor = EnhancedFrameProcessor(
            #     detector=self.detector,
            #     gesture_detector=self.gesture_detector,
            #     event_publisher=self.event_publisher,
            #     config=processor_config
            # )
            
            # Initialize HTTP service (presence detection)
            http_config = HTTPServiceConfig(
                host="0.0.0.0",
                port=8767,
                enable_history=True,
                history_limit=100
            )
            self.http_service = HTTPDetectionService(http_config)
            self.http_service.setup_event_integration(self.event_publisher)
            
            # Description integration disabled - gesture-only mode
            # if self.description_service:
            #     self.http_service.setup_description_integration(self.description_service)
            
            # ENABLED: Initialize SSE service (gesture streaming)
            sse_config = SSEServiceConfig(
                host="0.0.0.0",
                port=8766,
                gesture_events_only=True,  # Only stream gesture events
                min_gesture_confidence=0.7,
                max_connections=20
            )
            self.sse_service = SSEDetectionService(sse_config)
            self.sse_service.setup_gesture_integration(self.event_publisher)
            
            # Initialize Presence SSE service
            self.presence_sse_service = SSEPresenceService()
            self.presence_sse_service.subscribe_to_events(self.event_publisher)
            
            # Presence gating (behind config flag)
            gating_cfg = detection_cfg.get('gating', {}) if isinstance(detection_cfg, dict) else {}
            self._gating_enabled = bool(gating_cfg.get('enabled', False))
            if self._gating_enabled:
                refs_cfg = detection_cfg.get('refs', {}) if isinstance(detection_cfg, dict) else {}
                max_refs = int(refs_cfg.get('max_per_bucket', 3))
                self.reference_manager = ReferenceManager(max_references=max_refs)
                pg_cfg = PresenceGateConfig(
                    gating_enabled=True,
                    phash_threshold_same=int(gating_cfg.get('phash_threshold_same', 10)),
                    ssim_threshold_same=float(gating_cfg.get('ssim_threshold_same', 0.90)),
                    enter_k=int(gating_cfg.get('hysteresis', {}).get('enter_k', 3)),
                    exit_l=int(gating_cfg.get('hysteresis', {}).get('exit_l', 5)),
                    cooldown_ms=int(gating_cfg.get('cooldown_ms', 1000)),
                    capture_stable_seconds=float(refs_cfg.get('capture_stable_seconds', 5.0)),
                    max_refs=max_refs,
                )
                self.presence_gate = PresenceGate(self.reference_manager, pg_cfg)

                # Vision verification gate (wraps PresenceGate)
                vision_cfg = gating_cfg.get('vision_verification', {})
                vision_enabled = bool(vision_cfg.get('enabled', False))

                if vision_enabled and self.vision_verifier:
                    from src.processing.vision_verification_gate import (
                        VisionVerificationGate,
                        VisionVerificationConfig
                    )

                    vv_config = VisionVerificationConfig(
                        max_blocks_per_session=int(vision_cfg.get('max_blocks_per_session', 3)),
                        recapture_on_block=bool(vision_cfg.get('recapture_on_block', True)),
                        verify_enter_only=bool(vision_cfg.get('verify_enter_only', True))
                    )

                    self.verification_gate = VisionVerificationGate(
                        presence_gate=self.presence_gate,
                        vision_verifier=self.vision_verifier,
                        config=vv_config
                    )
                    logger.info("✓ Vision verification gate enabled")
                else:
                    self.verification_gate = None
                    if vision_enabled and not self.vision_verifier:
                        logger.warning("⚠ Vision verification enabled but vision_verifier not available")
            else:
                self.verification_gate = None

        except Exception as e:
            logger.error(f"Failed to initialize enhanced service: {e}")
            # Clean up any partially initialized components
            self._cleanup_on_error()
            raise
    
    def _cleanup_on_error(self):
        """Clean up partially initialized components on error."""
        try:
            # Cleanup Ollama components
            if self.description_service and hasattr(self.description_service, 'cleanup'):
                self.description_service.cleanup()
            if self.ollama_client and hasattr(self.ollama_client, 'cleanup'):
                self.ollama_client.cleanup()
            if self.ollama_image_processor and hasattr(self.ollama_image_processor, 'cleanup'):
                self.ollama_image_processor.cleanup()
            
            # Cleanup existing components
            if self.gesture_detector and hasattr(self.gesture_detector, 'cleanup'):
                self.gesture_detector.cleanup()
            if self.detector and hasattr(self.detector, 'cleanup'):
                self.detector.cleanup()
            if self.camera and hasattr(self.camera, 'cleanup'):
                self.camera.cleanup()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
        finally:
            # Reset components to None
            self.camera = None
            self.detector = None
            self.gesture_detector = None
            self.frame_processor = None
            self.latest_frame_processor = None  # NEW: Clean up Latest Frame Processor
            self.http_service = None
            self.sse_service = None
            self.presence_sse_service = None
            # Reset Ollama components
            self.description_service = None
            self.ollama_client = None
            self.vision_verifier = None
            self.ollama_config = None
            self.config_manager = None
            self.ollama_image_processor = None
    
    def detection_loop(self):
        """Main detection loop with presence gating and vision verification."""
        last_status_print = 0
        detection_count = 0
        fps_target = 15
        frame_time = 1.0 / fps_target

        # Track presence for change detection
        last_presence_state = None
        
        while self.is_running and not self._shutdown_requested:
            try:
                # Get frame from camera
                frame = self.camera.get_frame()
                if frame is not None:
                    # Simple detection processing - Ollama disabled for gesture-only mode
                    human_result = self.latest_frame_processor.process_frame(frame)

                    # Apply presence gating (with optional vision verification)
                    gated_state = human_result.human_present
                    if self._gating_enabled:
                        try:
                            # Use verification gate if available, otherwise use presence gate
                            gate = self.verification_gate if self.verification_gate else self.presence_gate

                            if gate:
                                gated = gate.process(frame, human_result, timestamp_s=time.time())
                                gated_state = gated.human_present
                        except Exception:
                            # On gating errors, fall back to raw detection
                            gated_state = human_result.human_present
                    
                    detection_count += 1

                    # Gesture detection with clean status tracking
                    gesture_status = "None"
                    gesture_confidence = 0.0
                    
                    # Simple threshold check with shoulder validation
                    if gated_state and human_result.confidence > 0.6:
                        # Direct gesture detection with pose landmarks for shoulder reference
                        pose_landmarks = getattr(human_result, '_original_pose_landmarks', None)
                        
                        gesture_result = self.gesture_detector.detect_gestures(frame, pose_landmarks)
                        
                        if gesture_result and gesture_result.gesture_detected:
                            gesture_status = f"{gesture_result.gesture_type}"
                            gesture_confidence = gesture_result.confidence
                            
                            # ENABLED: Simple event publishing - BOTH sync and async for SSE
                            if self.sse_service:
                                try:
                                    event = ServiceEvent(
                                        event_type=EventType.GESTURE_DETECTED,
                                        data={
                                            "gesture_type": gesture_result.gesture_type,
                                            "confidence": gesture_result.confidence,
                                            "hand": gesture_result.hand
                                        },
                                        timestamp=datetime.now()
                                    )
                                    # Publish both sync AND async for SSE service
                                    self.event_publisher.publish(event)
                                    
                                    # CRITICAL: Also publish async for SSE service
                                    import asyncio
                                    try:
                                        loop = asyncio.get_event_loop()
                                        if loop.is_running():
                                            asyncio.create_task(self.event_publisher.publish_async(event))
                                    except RuntimeError:
                                        # No event loop running - create one
                                        asyncio.run(self.event_publisher.publish_async(event))
                                    
                                except Exception as e:
                                    logger.debug(f"Event publishing error: {e}")  # Use logger instead of print
                    
                    # Update HTTP service status (simple)
                    if self.http_service:
                        self.http_service.current_status.human_present = gated_state
                        self.http_service.current_status.confidence = human_result.confidence
                        self.http_service.current_status.last_detection = datetime.now()
                        self.http_service.current_status.detection_count += 1
                    
                    # Publish PRESENCE_CHANGED event when presence changes
                    if last_presence_state is not None and last_presence_state != gated_state:
                        try:
                            presence_event = ServiceEvent(
                                event_type=EventType.PRESENCE_CHANGED,
                                data={
                                    "human_present": gated_state,
                                    "confidence": human_result.confidence,
                                    "timestamp": datetime.now().isoformat()
                                },
                                timestamp=datetime.now()
                            )
                            self.event_publisher.publish(presence_event)
                            
                            # Also publish async for SSE
                            import asyncio
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    asyncio.create_task(self.event_publisher.publish_async(presence_event))
                            except RuntimeError:
                                asyncio.run(self.event_publisher.publish_async(presence_event))
                        except Exception as e:
                            logger.error(f"Error publishing presence event: {e}")
                    
                    last_presence_state = gated_state

                    # Print status update every 2 seconds (single updating line)
                    current_time = time.time()
                    if current_time - last_status_print >= 2.0:
                        status = "👤 HUMAN" if gated_state else "❌ NO HUMAN"
                        # Clean gesture display with current status
                        gesture_display = f"{gesture_status} ({gesture_confidence:.2f})" if gesture_confidence > 0 else gesture_status
                        # Add vision verification stats if enabled
                        if self.verification_gate:
                            stats = self.verification_gate.get_stats()
                            vision_status = f"VisionGate: {stats['total_verifications']} checks, {stats['total_blocks']} blocks"
                        else:
                            vision_status = "VisionGate: disabled"
                        print(f"\r{status} | Conf: {human_result.confidence:.2f} | Gesture: {gesture_display} | {vision_status} | Frames: {detection_count}", end='', flush=True)
                        last_status_print = current_time
                    
                    time.sleep(frame_time)
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Detection loop error: {e}")
                time.sleep(1)
        
        logger.info("Detection loop stopped")
    
    async def start_http_service(self):
        """Start HTTP service."""
        if self.http_service:
            try:
                import uvicorn
                config = uvicorn.Config(
                    self.http_service.app, 
                    host="0.0.0.0", 
                    port=8767,
                    log_level="warning"
                )
                server = uvicorn.Server(config)
                logger.info("🚀 HTTP service starting on http://localhost:8767")
                await server.serve()
            except Exception as e:
                logger.error(f"HTTP service error: {e}")
    
    async def start_sse_service(self):
        """Start SSE service."""
        if self.sse_service:
            try:
                import uvicorn
                config = uvicorn.Config(
                    self.sse_service.app,
                    host="0.0.0.0",
                    port=8766,
                    log_level="warning"
                )
                server = uvicorn.Server(config)
                logger.info("📡 SSE service starting on http://localhost:8766")
                await server.serve()
            except Exception as e:
                logger.error(f"SSE service error: {e}")
    
    async def start_presence_sse_service(self):
        """Start presence SSE service."""
        if self.presence_sse_service:
            try:
                import uvicorn
                config = uvicorn.Config(
                    self.presence_sse_service.app,
                    host="0.0.0.0",
                    port=8764,
                    log_level="warning"
                )
                server = uvicorn.Server(config)
                logger.info("🚀 Presence SSE service starting on http://localhost:8764")
                await server.serve()
            except Exception as e:
                logger.error(f"Presence SSE service error: {e}")
    
    async def run(self):
        """Run the enhanced service with all components."""
        try:
            # Initialize all components
            self.initialize()
            
            self.is_running = True
            
            # Start detection loop in background thread
            detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            detection_thread.start()
            
            # Start all three services concurrently
            await asyncio.gather(
                self.start_http_service(),
                self.start_sse_service(),
                self.start_presence_sse_service()
            )
            
        except Exception as e:
            logger.error(f"Service startup error: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Shutdown the service gracefully."""
        logger.info("🛑 Shutting down enhanced service...")
        self._shutdown_requested = True
        self.is_running = False
        
        # Cleanup Ollama components
        if self.description_service and hasattr(self.description_service, 'cleanup'):
            self.description_service.cleanup()
        if self.ollama_client and hasattr(self.ollama_client, 'cleanup'):
            self.ollama_client.cleanup()
        if self.ollama_image_processor and hasattr(self.ollama_image_processor, 'cleanup'):
            self.ollama_image_processor.cleanup()
        
        # Cleanup existing components
        if self.gesture_detector:
            self.gesture_detector.cleanup()
        if self.detector:
            self.detector.cleanup()
        if self.camera:
            self.camera.cleanup()
        
        # Set components to None
        self.description_service = None
        self.ollama_client = None
        self.ollama_image_processor = None
        self.gesture_detector = None
        self.detector = None
        self.camera = None
        self.latest_frame_processor = None  # NEW: Clean up Latest Frame Processor
        
        logger.info("✅ Enhanced service shutdown complete")
    
    def _process_single_frame(self, frame):
        """
        Process a single frame for end-to-end testing.
        
        This method provides a synchronous interface for testing the complete pipeline:
        Frame → Detection → [If Human] → Description Processing → Event Publishing
        
        Args:
            frame: The frame to process
            
        Returns:
            dict: Processing results including detection and description outcomes
        """
        if frame is None:
            return {"error": "Invalid frame"}
        
        results = {
            "detection_called": False,
            "human_detected": False,
            "confidence": 0.0,
            "description_called": False,
            "description_result": None,
            "events_published": []
        }
        
        try:
            # Step 1: Human detection (NEW: Use Latest Frame Processor for consistency - Phase 4.1)
            if self.latest_frame_processor:
                detection_result = self.latest_frame_processor.process_frame(frame)
                results["detection_called"] = True
                results["human_detected"] = detection_result.human_present
                results["confidence"] = detection_result.confidence
                
                # Step 2: Conditional description processing (only if human present with sufficient confidence)
                if detection_result.human_present and detection_result.confidence > 0.6 and self.description_service:
                    try:
                        # FIX: Create proper Snapshot object instead of passing raw frame
                        snapshot_metadata = SnapshotMetadata(
                            timestamp=datetime.now(),
                            confidence=detection_result.confidence,
                            human_present=detection_result.human_present,
                            detection_source="multimodal"
                        )
                        snapshot = Snapshot(frame=frame, metadata=snapshot_metadata)
                        
                        # Process snapshot for description (this should be sync for testing)
                        # Use asyncio.run for clean async handling in sync context
                        import asyncio
                        description_result = asyncio.run(
                            self.description_service.describe_snapshot(snapshot)
                        )
                        
                        results["description_called"] = True
                        results["description_result"] = description_result
                        
                        if description_result and hasattr(description_result, 'success') and description_result.success:
                            # Description processing successful - would normally publish events here
                            results["events_published"].append("DESCRIPTION_GENERATED")
                        else:
                            # Description processing failed - would normally publish error events
                            results["events_published"].append("DESCRIPTION_FAILED")
                            
                    except Exception as e:
                        # Description processing error
                        results["events_published"].append("DESCRIPTION_FAILED")
                        logger.debug(f"Description processing error: {e}")
                
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Frame processing error: {e}")
        
        return results
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self._shutdown_requested = True
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _load_room_layout(self):
        """Load room layout configuration from file for enhanced descriptions."""
        try:
            from pathlib import Path
            layout_file = Path(__file__).parent / "config" / "room_layout.txt"
            
            if layout_file.exists():
                with open(layout_file, 'r') as f:
                    room_layout = f.read().strip()
                    logger.info(f"✅ Room layout loaded ({len(room_layout)} chars)")
                    return room_layout
            else:
                logger.warning(f"⚠️ Room layout file not found at {layout_file}")
                return ""
        except Exception as e:
            logger.error(f"❌ Error loading room layout: {e}")
            return ""

def main():
    """Main entry point."""
    service = WebcamService()
    service.setup_signal_handlers()
    
    print("🎯 Webcam Detection Service with Gesture Recognition & Presence SSE")
    print("=" * 65)
    print("HTTP API: http://localhost:8767 (presence detection)")
    print("Gesture SSE: http://localhost:8766 (gesture events)")
    print("Presence SSE: http://localhost:8764 (presence changes)")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        print("\n🛑 Service stopped by user")
    except Exception as e:
        print(f"\n❌ Service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
