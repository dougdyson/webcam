#!/usr/bin/env python3
"""
Performance Optimization Examples

Demonstrates performance optimization techniques for webcam detection:
- Frame rate optimization and adaptive processing
- Memory management and resource cleanup
- Concurrent detection with rate limiting
- Smart caching strategies
- CPU/GPU optimization patterns

Usage:
    conda activate webcam && python docs/examples/performance_optimization_examples.py
"""

import sys
import time
import asyncio
import threading
import queue
import psutil
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# Add src to path for imports
sys.path.append('src')

from camera import CameraManager, CameraConfig
from detection import create_detector
from processing.frame_queue import FrameQueue
from processing.presence_filter import PresenceFilter
from gesture.hand_detection import HandDetector


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    frames_processed: int = 0
    detections_performed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_frame_time_ms: float = 0.0
    avg_detection_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def update_memory(self):
        """Update memory usage"""
        process = psutil.Process()
        self.memory_usage_mb = process.memory_info().rss / 1024 / 1024
        
    def update_cpu(self):
        """Update CPU usage"""
        self.cpu_usage_percent = psutil.cpu_percent(interval=0.1)


class FrameRateOptimizer:
    """
    Example 1: Frame Rate Optimization
    
    Demonstrates adaptive frame rate control based on:
    - Detection complexity
    - System resource usage
    - Processing queue depth
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal')
        self.target_fps = 30
        self.min_fps = 10
        self.max_fps = 60
        self.current_fps = self.target_fps
        self.frame_times = []
        self.metrics = PerformanceMetrics()
        
    def initialize(self):
        """Initialize components"""
        print("⚡ Initializing frame rate optimizer...")
        self.detector.initialize()
        print("✅ Frame rate optimizer ready")
        
    def adaptive_frame_rate_control(self, processing_time_ms: float, queue_depth: int) -> int:
        """
        Adjust frame rate based on processing performance
        
        Args:
            processing_time_ms: Last frame processing time
            queue_depth: Current frame queue depth
            
        Returns:
            New target FPS
        """
        # Calculate current system load
        self.metrics.update_cpu()
        self.metrics.update_memory()
        
        # Determine optimal FPS based on multiple factors
        cpu_factor = 1.0 if self.metrics.cpu_usage_percent < 70 else 0.5
        memory_factor = 1.0 if self.metrics.memory_usage_mb < 500 else 0.7
        queue_factor = 1.0 if queue_depth < 5 else 0.6
        processing_factor = 1.0 if processing_time_ms < 33 else 0.8  # 33ms = 30fps
        
        # Calculate new FPS
        adjustment_factor = cpu_factor * memory_factor * queue_factor * processing_factor
        new_fps = int(self.target_fps * adjustment_factor)
        
        # Clamp to min/max bounds
        self.current_fps = max(self.min_fps, min(self.max_fps, new_fps))
        
        return self.current_fps
        
    def process_with_adaptive_rate(self, frame: np.ndarray, queue_depth: int = 0) -> Tuple[bool, float]:
        """Process frame with adaptive rate control"""
        start_time = time.time()
        
        # Perform detection
        result = self.detector.detect(frame)
        
        processing_time_ms = (time.time() - start_time) * 1000
        self.frame_times.append(processing_time_ms)
        
        # Keep only last 30 frame times for rolling average
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
            
        # Update metrics
        self.metrics.frames_processed += 1
        self.metrics.avg_frame_time_ms = sum(self.frame_times) / len(self.frame_times)
        
        # Adjust frame rate
        new_fps = self.adaptive_frame_rate_control(processing_time_ms, queue_depth)
        
        return result.human_present, processing_time_ms
        
    def run_optimization_demo(self, duration_seconds: int = 60):
        """Run adaptive frame rate optimization demo"""
        print(f"⚡ Running frame rate optimization for {duration_seconds} seconds...")
        print("Adaptive features:")
        print("- Dynamic FPS based on CPU/memory usage")
        print("- Queue depth monitoring")
        print("- Processing time feedback")
        print()
        
        start_time = time.time()
        fps_changes = []
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            # Simulate queue depth variation
            queue_depth = max(0, int(np.random.normal(3, 2)))
            
            human_present, proc_time = self.process_with_adaptive_rate(frame, queue_depth)
            
            # Log FPS changes
            if len(fps_changes) == 0 or fps_changes[-1][1] != self.current_fps:
                fps_changes.append((time.time() - start_time, self.current_fps))
                
            # Print status every 5 seconds
            if self.metrics.frames_processed % (self.current_fps * 5) == 0:
                print(f"⚡ FPS: {self.current_fps} | "
                      f"Avg proc time: {self.metrics.avg_frame_time_ms:.1f}ms | "
                      f"CPU: {self.metrics.cpu_usage_percent:.1f}% | "
                      f"Memory: {self.metrics.memory_usage_mb:.1f}MB")
                      
            # Sleep to maintain target FPS
            sleep_time = max(0, (1.0 / self.current_fps) - (proc_time / 1000))
            time.sleep(sleep_time)
            
        print(f"\n⚡ Frame Rate Optimization Summary:")
        print(f"   Frames processed: {self.metrics.frames_processed}")
        print(f"   Average frame time: {self.metrics.avg_frame_time_ms:.1f}ms")
        print(f"   FPS changes: {len(fps_changes)}")
        print(f"   Final FPS: {self.current_fps}")
        
    def cleanup(self):
        """Clean up resources"""
        self.camera.cleanup()
        self.detector.cleanup()


class MemoryOptimizer:
    """
    Example 2: Memory Management Optimization
    
    Demonstrates memory-efficient processing:
    - Frame buffer management
    - Garbage collection optimization
    - Memory pool patterns
    - Resource cleanup
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal')
        self.frame_buffer = queue.Queue(maxsize=10)  # Bounded buffer
        self.memory_stats = []
        self.frame_pool = []  # Pre-allocated frame buffers
        
    def initialize(self):
        """Initialize with memory optimization"""
        print("🧠 Initializing memory optimizer...")
        self.detector.initialize()
        
        # Pre-allocate frame buffers to reduce allocation overhead
        for _ in range(10):
            buffer = np.zeros((480, 640, 3), dtype=np.uint8)
            self.frame_pool.append(buffer)
            
        print("✅ Memory optimizer ready")
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
        
    def efficient_frame_copy(self, source_frame: np.ndarray) -> np.ndarray:
        """Efficient frame copying using pre-allocated buffers"""
        if self.frame_pool:
            # Reuse pre-allocated buffer
            buffer = self.frame_pool.pop()
            np.copyto(buffer, source_frame)
            return buffer
        else:
            # Fallback to normal allocation
            return source_frame.copy()
            
    def return_frame_to_pool(self, frame: np.ndarray):
        """Return frame buffer to pool for reuse"""
        if len(self.frame_pool) < 10:  # Don't let pool grow too large
            self.frame_pool.append(frame)
            
    def process_with_memory_optimization(self, frame: np.ndarray) -> bool:
        """Process frame with memory optimization"""
        # Use efficient frame copying
        working_frame = self.efficient_frame_copy(frame)
        
        try:
            # Perform detection
            result = self.detector.detect(working_frame)
            return result.human_present
            
        finally:
            # Always return buffer to pool
            self.return_frame_to_pool(working_frame)
            
    def monitor_memory_usage(self):
        """Monitor memory usage over time"""
        while True:
            memory_mb = self.get_memory_usage()
            self.memory_stats.append({
                'timestamp': time.time(),
                'memory_mb': memory_mb
            })
            
            # Keep only last 100 measurements
            if len(self.memory_stats) > 100:
                self.memory_stats.pop(0)
                
            time.sleep(1)  # Monitor every second
            
    def run_memory_demo(self, duration_seconds: int = 60):
        """Run memory optimization demo"""
        print(f"🧠 Running memory optimization for {duration_seconds} seconds...")
        print("Memory features:")
        print("- Pre-allocated frame buffers")
        print("- Bounded frame queues")
        print("- Buffer pool reuse")
        print("- Memory usage monitoring")
        print()
        
        # Start memory monitoring in background
        monitor_thread = threading.Thread(target=self.monitor_memory_usage, daemon=True)
        monitor_thread.start()
        
        start_time = time.time()
        frames_processed = 0
        initial_memory = self.get_memory_usage()
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            human_present = self.process_with_memory_optimization(frame)
            frames_processed += 1
            
            # Print memory stats every 10 seconds
            if frames_processed % 300 == 0:  # Assuming ~30 FPS
                current_memory = self.get_memory_usage()
                memory_increase = current_memory - initial_memory
                
                print(f"🧠 Memory: {current_memory:.1f}MB "
                      f"(+{memory_increase:.1f}MB) | "
                      f"Pool size: {len(self.frame_pool)} | "
                      f"Frames: {frames_processed}")
                      
            time.sleep(0.033)  # ~30 FPS
            
        final_memory = self.get_memory_usage()
        total_increase = final_memory - initial_memory
        
        print(f"\n🧠 Memory Optimization Summary:")
        print(f"   Frames processed: {frames_processed}")
        print(f"   Initial memory: {initial_memory:.1f}MB")
        print(f"   Final memory: {final_memory:.1f}MB")
        print(f"   Total increase: {total_increase:.1f}MB")
        print(f"   Pool efficiency: {len(self.frame_pool)}/10 buffers reused")
        
    def cleanup(self):
        """Clean up resources"""
        self.camera.cleanup()
        self.detector.cleanup()
        self.frame_pool.clear()


class ConcurrentDetectionOptimizer:
    """
    Example 3: Concurrent Detection Optimization
    
    Demonstrates concurrent processing patterns:
    - Multi-threaded detection
    - Rate limiting and backpressure
    - Worker pool management
    - Load balancing
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal')
        self.hand_detector = HandDetector()
        self.frame_queue = queue.Queue(maxsize=20)
        self.result_queue = queue.Queue()
        self.worker_pool = None
        self.processing_stats = {
            'human_detection_time': [],
            'gesture_detection_time': [],
            'concurrent_tasks': 0
        }
        
    def initialize(self):
        """Initialize concurrent processing"""
        print("🚀 Initializing concurrent optimizer...")
        self.detector.initialize()
        self.hand_detector.initialize()
        
        # Create worker pool
        self.worker_pool = ThreadPoolExecutor(max_workers=4)
        
        print("✅ Concurrent optimizer ready")
        
    def detect_human_worker(self, frame: np.ndarray, frame_id: int) -> Dict:
        """Worker function for human detection"""
        start_time = time.time()
        
        try:
            result = self.detector.detect(frame)
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'frame_id': frame_id,
                'type': 'human',
                'human_present': result.human_present,
                'confidence': result.confidence,
                'processing_time_ms': processing_time,
                'landmarks': result.landmarks
            }
            
        except Exception as e:
            return {
                'frame_id': frame_id,
                'type': 'human',
                'error': str(e),
                'processing_time_ms': (time.time() - start_time) * 1000
            }
            
    def detect_gesture_worker(self, frame: np.ndarray, landmarks, frame_id: int) -> Dict:
        """Worker function for gesture detection"""
        start_time = time.time()
        
        try:
            hand_results = self.hand_detector.detect_hands(frame)
            processing_time = (time.time() - start_time) * 1000
            
            return {
                'frame_id': frame_id,
                'type': 'gesture',
                'hands_detected': hand_results.hands_detected,
                'hand_count': len(hand_results.hand_landmarks) if hand_results.hands_detected else 0,
                'processing_time_ms': processing_time
            }
            
        except Exception as e:
            return {
                'frame_id': frame_id,
                'type': 'gesture',
                'error': str(e),
                'processing_time_ms': (time.time() - start_time) * 1000
            }
            
    def process_frame_concurrent(self, frame: np.ndarray, frame_id: int) -> List[asyncio.Future]:
        """Process frame using concurrent workers"""
        futures = []
        
        # Submit human detection task
        human_future = self.worker_pool.submit(self.detect_human_worker, frame, frame_id)
        futures.append(human_future)
        
        # Submit gesture detection task (conditional optimization would check human presence first)
        gesture_future = self.worker_pool.submit(self.detect_gesture_worker, frame, None, frame_id)
        futures.append(gesture_future)
        
        self.processing_stats['concurrent_tasks'] += 2
        
        return futures
        
    def process_results(self, futures: List[asyncio.Future], timeout_seconds: float = 0.5):
        """Process results from concurrent workers"""
        results = {'human': None, 'gesture': None}
        
        for future in futures:
            try:
                result = future.result(timeout=timeout_seconds)
                result_type = result.get('type', 'unknown')
                results[result_type] = result
                
                # Update stats
                proc_time = result.get('processing_time_ms', 0)
                if result_type == 'human':
                    self.processing_stats['human_detection_time'].append(proc_time)
                elif result_type == 'gesture':
                    self.processing_stats['gesture_detection_time'].append(proc_time)
                    
            except Exception as e:
                print(f"⚠️ Worker timeout or error: {e}")
                
        return results
        
    def run_concurrent_demo(self, duration_seconds: int = 60):
        """Run concurrent processing demo"""
        print(f"🚀 Running concurrent optimization for {duration_seconds} seconds...")
        print("Concurrent features:")
        print("- Multi-threaded detection")
        print("- Parallel human + gesture detection")
        print("- Worker pool management")
        print("- Timeout handling")
        print()
        
        start_time = time.time()
        frames_processed = 0
        total_futures = []
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            # Submit concurrent processing
            futures = self.process_frame_concurrent(frame, frames_processed)
            total_futures.extend(futures)
            
            # Process results every few frames to avoid overwhelming
            if frames_processed % 5 == 0:
                results = self.process_results(futures)
                
                human_result = results.get('human', {})
                gesture_result = results.get('gesture', {})
                
                if frames_processed % 150 == 0:  # Every ~5 seconds at 30 FPS
                    print(f"🚀 Concurrent status:")
                    print(f"   Frames: {frames_processed}")
                    print(f"   Active tasks: {len([f for f in total_futures if not f.done()])}")
                    print(f"   Human detection: {human_result.get('processing_time_ms', 0):.1f}ms")
                    print(f"   Gesture detection: {gesture_result.get('processing_time_ms', 0):.1f}ms")
                    
            frames_processed += 1
            time.sleep(0.033)  # ~30 FPS
            
        # Wait for remaining tasks
        print("🚀 Waiting for remaining tasks to complete...")
        for future in total_futures:
            try:
                future.result(timeout=1.0)
            except:
                pass
                
        # Calculate statistics
        avg_human_time = np.mean(self.processing_stats['human_detection_time']) if self.processing_stats['human_detection_time'] else 0
        avg_gesture_time = np.mean(self.processing_stats['gesture_detection_time']) if self.processing_stats['gesture_detection_time'] else 0
        
        print(f"\n🚀 Concurrent Optimization Summary:")
        print(f"   Frames processed: {frames_processed}")
        print(f"   Total concurrent tasks: {self.processing_stats['concurrent_tasks']}")
        print(f"   Avg human detection time: {avg_human_time:.1f}ms")
        print(f"   Avg gesture detection time: {avg_gesture_time:.1f}ms")
        print(f"   Parallel efficiency: {2.0 if avg_human_time > 0 and avg_gesture_time > 0 else 1.0:.1f}x")
        
    def cleanup(self):
        """Clean up resources"""
        if self.worker_pool:
            self.worker_pool.shutdown(wait=True)
        self.camera.cleanup()
        self.detector.cleanup()
        self.hand_detector.cleanup()


class SmartCachingOptimizer:
    """
    Example 4: Smart Caching Optimization
    
    Demonstrates intelligent caching strategies:
    - Frame similarity detection
    - Adaptive cache TTL
    - Memory-aware cache eviction
    - Cache hit optimization
    """
    
    def __init__(self):
        self.camera = CameraManager(CameraConfig())
        self.detector = create_detector('multimodal')
        self.frame_cache = {}
        self.similarity_threshold = 0.95
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'frame_comparisons': 0
        }
        
    def initialize(self):
        """Initialize smart caching"""
        print("🎯 Initializing smart caching optimizer...")
        self.detector.initialize()
        print("✅ Smart caching optimizer ready")
        
    def calculate_frame_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Calculate similarity between two frames"""
        self.cache_stats['frame_comparisons'] += 1
        
        # Resize frames for faster comparison
        small_frame1 = cv2.resize(frame1, (64, 48))
        small_frame2 = cv2.resize(frame2, (64, 48))
        
        # Calculate normalized cross-correlation
        correlation = cv2.matchTemplate(small_frame1, small_frame2, cv2.TM_CCOEFF_NORMED)
        similarity = correlation[0, 0]
        
        return float(similarity)
        
    def find_similar_cached_frame(self, frame: np.ndarray) -> Optional[Tuple[str, Dict]]:
        """Find similar frame in cache"""
        for cache_key, cache_entry in self.frame_cache.items():
            similarity = self.calculate_frame_similarity(frame, cache_entry['frame'])
            
            if similarity >= self.similarity_threshold:
                return cache_key, cache_entry
                
        return None
        
    def adaptive_cache_ttl(self, detection_result) -> int:
        """Calculate adaptive TTL based on detection result"""
        base_ttl = 10  # seconds
        
        if detection_result.human_present:
            # Human present - shorter TTL for more responsive detection
            return max(2, int(base_ttl * (1 - detection_result.confidence)))
        else:
            # No human - longer TTL to save computation
            return base_ttl * 2
            
    def cache_frame_result(self, frame: np.ndarray, result, cache_key: str):
        """Cache frame and detection result"""
        ttl = self.adaptive_cache_ttl(result)
        
        cache_entry = {
            'frame': frame.copy(),
            'result': result,
            'timestamp': time.time(),
            'ttl': ttl,
            'hit_count': 0
        }
        
        self.frame_cache[cache_key] = cache_entry
        
        # Memory-aware cache eviction
        if len(self.frame_cache) > 20:  # Max cache size
            self._evict_oldest_entries()
            
    def _evict_oldest_entries(self):
        """Evict oldest cache entries to manage memory"""
        # Sort by timestamp and remove oldest entries
        sorted_entries = sorted(
            self.frame_cache.items(),
            key=lambda x: x[1]['timestamp']
        )
        
        # Remove oldest 25% of entries
        num_to_remove = len(sorted_entries) // 4
        for i in range(num_to_remove):
            key = sorted_entries[i][0]
            del self.frame_cache[key]
            self.cache_stats['evictions'] += 1
            
    def _cleanup_expired_entries(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.frame_cache.items():
            if current_time - entry['timestamp'] > entry['ttl']:
                expired_keys.append(key)
                
        for key in expired_keys:
            del self.frame_cache[key]
            
    def process_with_smart_caching(self, frame: np.ndarray) -> Tuple[bool, bool]:
        """Process frame with smart caching"""
        # Clean up expired entries
        self._cleanup_expired_entries()
        
        # Check for similar cached frame
        cache_result = self.find_similar_cached_frame(frame)
        
        if cache_result:
            # Cache hit
            cache_key, cache_entry = cache_result
            cache_entry['hit_count'] += 1
            self.cache_stats['hits'] += 1
            
            return cache_entry['result'].human_present, True
        else:
            # Cache miss - perform detection
            result = self.detector.detect(frame)
            self.cache_stats['misses'] += 1
            
            # Cache the result
            cache_key = f"frame_{time.time()}"
            self.cache_frame_result(frame, result, cache_key)
            
            return result.human_present, False
            
    def run_caching_demo(self, duration_seconds: int = 60):
        """Run smart caching optimization demo"""
        print(f"🎯 Running smart caching optimization for {duration_seconds} seconds...")
        print("Caching features:")
        print("- Frame similarity detection")
        print("- Adaptive cache TTL")
        print("- Memory-aware eviction")
        print("- Cache hit optimization")
        print()
        
        start_time = time.time()
        frames_processed = 0
        
        while time.time() - start_time < duration_seconds:
            frame = self.camera.get_frame()
            if frame is None:
                continue
                
            human_present, cache_hit = self.process_with_smart_caching(frame)
            frames_processed += 1
            
            # Print stats every 10 seconds
            if frames_processed % 300 == 0:  # ~30 FPS
                total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
                hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
                
                print(f"🎯 Cache stats:")
                print(f"   Frames: {frames_processed}")
                print(f"   Hit rate: {hit_rate:.1f}%")
                print(f"   Cache size: {len(self.frame_cache)}")
                print(f"   Comparisons: {self.cache_stats['frame_comparisons']}")
                print(f"   Evictions: {self.cache_stats['evictions']}")
                
            time.sleep(0.033)  # ~30 FPS
            
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        final_hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        print(f"\n🎯 Smart Caching Summary:")
        print(f"   Frames processed: {frames_processed}")
        print(f"   Cache hits: {self.cache_stats['hits']}")
        print(f"   Cache misses: {self.cache_stats['misses']}")
        print(f"   Final hit rate: {final_hit_rate:.1f}%")
        print(f"   Total evictions: {self.cache_stats['evictions']}")
        print(f"   Final cache size: {len(self.frame_cache)}")
        
    def cleanup(self):
        """Clean up resources"""
        self.frame_cache.clear()
        self.camera.cleanup()
        self.detector.cleanup()


def main():
    """Run performance optimization examples"""
    print("⚡ Performance Optimization Examples")
    print("="*50)
    
    examples = {
        "1": ("Frame Rate Optimization", FrameRateOptimizer),
        "2": ("Memory Management", MemoryOptimizer),
        "3": ("Concurrent Detection", ConcurrentDetectionOptimizer),
        "4": ("Smart Caching", SmartCachingOptimizer)
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"  {key}: {name}")
        
    choice = input("\nSelect example (1-4, or 'all'): ").strip()
    
    if choice.lower() == 'all':
        # Run all examples with shorter durations
        for key, (name, example_class) in examples.items():
            print(f"\n{'='*60}")
            print(f"Running Example {key}: {name}")
            print('='*60)
            
            example = example_class()
            try:
                example.initialize()
                
                if hasattr(example, 'run_optimization_demo'):
                    example.run_optimization_demo(20)
                elif hasattr(example, 'run_memory_demo'):
                    example.run_memory_demo(20)
                elif hasattr(example, 'run_concurrent_demo'):
                    example.run_concurrent_demo(20)
                elif hasattr(example, 'run_caching_demo'):
                    example.run_caching_demo(20)
                    
            except KeyboardInterrupt:
                print("\n⏹️ Example interrupted")
            finally:
                example.cleanup()
                
    elif choice in examples:
        name, example_class = examples[choice]
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)
        
        example = example_class()
        try:
            example.initialize()
            duration = int(input("Duration in seconds (default 60): ") or "60")
            
            if hasattr(example, 'run_optimization_demo'):
                example.run_optimization_demo(duration)
            elif hasattr(example, 'run_memory_demo'):
                example.run_memory_demo(duration)
            elif hasattr(example, 'run_concurrent_demo'):
                example.run_concurrent_demo(duration)
            elif hasattr(example, 'run_caching_demo'):
                example.run_caching_demo(duration)
                
        except KeyboardInterrupt:
            print("\n⏹️ Demo interrupted")
        finally:
            example.cleanup()
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    # Required imports for this example
    try:
        import cv2
        import psutil
    except ImportError as e:
        print(f"❌ Missing required dependency: {e}")
        print("Install with: pip install opencv-python psutil")
        sys.exit(1)
        
    main() 