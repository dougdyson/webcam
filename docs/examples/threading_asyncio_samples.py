"""
Threading and AsyncIO Sample Code for Webcam Processing

This file contains starter code and examples for threading, asyncio, and 
queue management patterns used in the webcam detection pipeline.
"""

import asyncio
import threading
import time
import cv2
import numpy as np
from queue import Queue, Empty, Full
from typing import Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor
import logging


def basic_threading_example():
    """Basic threading example for camera capture."""
    
    class CameraThread:
        def __init__(self, device_id: int = 0):
            self.device_id = device_id
            self.cap = None
            self.frame = None
            self.running = False
            self.thread = None
            self.lock = threading.Lock()
        
        def start(self):
            """Start camera capture thread."""
            self.cap = cv2.VideoCapture(self.device_id)
            if not self.cap.isOpened():
                raise RuntimeError("Cannot open camera")
            
            self.running = True
            self.thread = threading.Thread(target=self._capture_loop)
            self.thread.start()
            print("Camera thread started")
        
        def stop(self):
            """Stop camera capture thread."""
            self.running = False
            if self.thread:
                self.thread.join()
            if self.cap:
                self.cap.release()
            print("Camera thread stopped")
        
        def _capture_loop(self):
            """Main capture loop running in thread."""
            while self.running:
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.frame = frame.copy()
                time.sleep(0.033)  # ~30 FPS
        
        def get_frame(self) -> Optional[np.ndarray]:
            """Get latest frame (thread-safe)."""
            with self.lock:
                return self.frame.copy() if self.frame is not None else None
    
    # Usage example
    camera = CameraThread(0)
    camera.start()
    
    try:
        for i in range(100):  # Capture 100 frames
            frame = camera.get_frame()
            if frame is not None:
                print(f"Frame {i}: {frame.shape}")
                cv2.imshow('Threaded Camera', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            time.sleep(0.1)
    finally:
        camera.stop()
        cv2.destroyAllWindows()


def producer_consumer_queue():
    """Producer-consumer pattern with queues."""
    
    class FrameProducer:
        """Produces frames from camera."""
        
        def __init__(self, frame_queue: Queue, device_id: int = 0):
            self.frame_queue = frame_queue
            self.device_id = device_id
            self.running = False
            self.thread = None
        
        def start(self):
            """Start frame production."""
            self.running = True
            self.thread = threading.Thread(target=self._produce_frames)
            self.thread.start()
        
        def stop(self):
            """Stop frame production."""
            self.running = False
            if self.thread:
                self.thread.join()
        
        def _produce_frames(self):
            """Produce frames and add to queue."""
            cap = cv2.VideoCapture(self.device_id)
            frame_count = 0
            
            while self.running:
                ret, frame = cap.read()
                if ret:
                    try:
                        # Add frame to queue (non-blocking)
                        self.frame_queue.put((frame_count, frame), timeout=0.1)
                        frame_count += 1
                        print(f"Produced frame {frame_count}")
                    except Full:
                        print("Frame queue is full, dropping frame")
                
                time.sleep(0.033)  # ~30 FPS
            
            cap.release()
    
    class FrameConsumer:
        """Consumes frames from queue for processing."""
        
        def __init__(self, frame_queue: Queue, result_queue: Queue):
            self.frame_queue = frame_queue
            self.result_queue = result_queue
            self.running = False
            self.thread = None
        
        def start(self):
            """Start frame consumption."""
            self.running = True
            self.thread = threading.Thread(target=self._consume_frames)
            self.thread.start()
        
        def stop(self):
            """Stop frame consumption."""
            self.running = False
            if self.thread:
                self.thread.join()
        
        def _consume_frames(self):
            """Consume and process frames."""
            while self.running:
                try:
                    frame_id, frame = self.frame_queue.get(timeout=1.0)
                    
                    # Simulate processing (human detection)
                    time.sleep(0.05)  # 50ms processing time
                    
                    # Mock detection result
                    human_detected = np.random.random() > 0.5
                    
                    result = {
                        'frame_id': frame_id,
                        'human_detected': human_detected,
                        'timestamp': time.time()
                    }
                    
                    self.result_queue.put(result)
                    print(f"Processed frame {frame_id}: Human={human_detected}")
                    
                except Empty:
                    continue
    
    # Usage example
    frame_queue = Queue(maxsize=10)
    result_queue = Queue(maxsize=20)
    
    producer = FrameProducer(frame_queue, device_id=0)
    consumer = FrameConsumer(frame_queue, result_queue)
    
    try:
        producer.start()
        consumer.start()
        
        # Monitor results
        for _ in range(50):
            try:
                result = result_queue.get(timeout=1.0)
                print(f"Result: Frame {result['frame_id']} - {result}")
            except Empty:
                print("No results available")
        
    finally:
        producer.stop()
        consumer.stop()


async def async_frame_processing():
    """AsyncIO example for frame processing."""
    
    class AsyncFrameProcessor:
        def __init__(self):
            self.frame_queue = asyncio.Queue(maxsize=10)
            self.result_queue = asyncio.Queue(maxsize=20)
            self.running = False
        
        async def capture_frames(self, device_id: int = 0):
            """Async frame capture coroutine."""
            cap = cv2.VideoCapture(device_id)
            frame_count = 0
            
            try:
                while self.running:
                    ret, frame = cap.read()
                    if ret:
                        try:
                            await asyncio.wait_for(
                                self.frame_queue.put((frame_count, frame)), 
                                timeout=0.1
                            )
                            frame_count += 1
                            print(f"Captured frame {frame_count}")
                        except asyncio.TimeoutError:
                            print("Frame queue full, dropping frame")
                    
                    await asyncio.sleep(0.033)  # ~30 FPS
            finally:
                cap.release()
        
        async def process_frames(self):
            """Async frame processing coroutine."""
            while self.running:
                try:
                    frame_id, frame = await asyncio.wait_for(
                        self.frame_queue.get(), timeout=1.0
                    )
                    
                    # Simulate async processing
                    await asyncio.sleep(0.05)  # 50ms processing
                    
                    result = {
                        'frame_id': frame_id,
                        'human_detected': np.random.random() > 0.5,
                        'timestamp': time.time()
                    }
                    
                    await self.result_queue.put(result)
                    print(f"Processed frame {frame_id}")
                    
                except asyncio.TimeoutError:
                    continue
        
        async def monitor_results(self, duration: float = 10.0):
            """Monitor processing results."""
            start_time = time.time()
            
            while time.time() - start_time < duration:
                try:
                    result = await asyncio.wait_for(
                        self.result_queue.get(), timeout=1.0
                    )
                    print(f"Result: {result}")
                except asyncio.TimeoutError:
                    print("No results available")
        
        async def run(self, duration: float = 10.0):
            """Run the complete async pipeline."""
            self.running = True
            
            # Start all coroutines concurrently
            await asyncio.gather(
                self.capture_frames(),
                self.process_frames(),
                self.monitor_results(duration),
                return_exceptions=True
            )
            
            self.running = False
    
    # Usage
    processor = AsyncFrameProcessor()
    await processor.run(duration=5.0)


def thread_pool_processing():
    """Thread pool example for parallel processing."""
    
    class ThreadPoolProcessor:
        def __init__(self, max_workers: int = 4):
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
            self.frame_queue = Queue(maxsize=20)
            self.result_queue = Queue(maxsize=50)
            self.running = False
            
        def process_frame(self, frame_data: tuple) -> dict:
            """Process a single frame (CPU intensive task)."""
            frame_id, frame = frame_data
            
            # Simulate processing
            time.sleep(0.1)  # 100ms processing
            
            # Mock detection
            human_detected = np.random.random() > 0.5
            
            return {
                'frame_id': frame_id,
                'human_detected': human_detected,
                'processing_time': 0.1,
                'timestamp': time.time()
            }
        
        def frame_callback(self, future):
            """Callback for completed frame processing."""
            try:
                result = future.result()
                self.result_queue.put(result)
                print(f"Completed frame {result['frame_id']}")
            except Exception as e:
                print(f"Frame processing error: {e}")
        
        def start_processing(self):
            """Start the processing pipeline."""
            self.running = True
            
            def processing_loop():
                while self.running:
                    try:
                        frame_data = self.frame_queue.get(timeout=1.0)
                        
                        # Submit to thread pool
                        future = self.executor.submit(self.process_frame, frame_data)
                        future.add_done_callback(self.frame_callback)
                        
                    except Empty:
                        continue
            
            # Start processing in separate thread
            self.processing_thread = threading.Thread(target=processing_loop)
            self.processing_thread.start()
        
        def stop_processing(self):
            """Stop the processing pipeline."""
            self.running = False
            
            if hasattr(self, 'processing_thread'):
                self.processing_thread.join()
            
            self.executor.shutdown(wait=True)
        
        def add_frame(self, frame_id: int, frame: np.ndarray):
            """Add frame for processing."""
            try:
                self.frame_queue.put((frame_id, frame), timeout=0.1)
            except Full:
                print(f"Queue full, dropping frame {frame_id}")
        
        def get_result(self) -> Optional[dict]:
            """Get processing result."""
            try:
                return self.result_queue.get_nowait()
            except Empty:
                return None
    
    # Usage example
    processor = ThreadPoolProcessor(max_workers=2)
    processor.start_processing()
    
    # Simulate adding frames
    cap = cv2.VideoCapture(0)
    
    try:
        for frame_id in range(20):
            ret, frame = cap.read()
            if ret:
                processor.add_frame(frame_id, frame)
                
                # Check for results
                result = processor.get_result()
                if result:
                    print(f"Got result: {result}")
                
            time.sleep(0.1)
    
    finally:
        cap.release()
        processor.stop_processing()


def frame_queue_with_overflow():
    """Advanced frame queue with overflow handling."""
    
    class AdvancedFrameQueue:
        def __init__(self, max_size: int = 10):
            self.queue = Queue(maxsize=max_size)
            self.lock = threading.Lock()
            self.dropped_frames = 0
            self.total_frames = 0
            
        def put_frame(self, frame: np.ndarray, frame_id: int = None) -> bool:
            """Add frame to queue with overflow handling."""
            with self.lock:
                self.total_frames += 1
                
                try:
                    # Try to add frame
                    frame_data = {
                        'frame': frame,
                        'frame_id': frame_id or self.total_frames,
                        'timestamp': time.time()
                    }
                    
                    self.queue.put_nowait(frame_data)
                    return True
                    
                except Full:
                    # Queue is full, drop oldest frame
                    try:
                        dropped = self.queue.get_nowait()
                        self.queue.put_nowait(frame_data)
                        self.dropped_frames += 1
                        print(f"Dropped frame {dropped['frame_id']} to make room")
                        return True
                    except:
                        self.dropped_frames += 1
                        return False
        
        def get_frame(self, timeout: float = 1.0) -> Optional[dict]:
            """Get frame from queue."""
            try:
                return self.queue.get(timeout=timeout)
            except Empty:
                return None
        
        def get_stats(self) -> dict:
            """Get queue statistics."""
            with self.lock:
                return {
                    'queue_size': self.queue.qsize(),
                    'total_frames': self.total_frames,
                    'dropped_frames': self.dropped_frames,
                    'drop_rate': self.dropped_frames / max(self.total_frames, 1)
                }
        
        def clear(self):
            """Clear the queue."""
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except Empty:
                    break
    
    # Usage example
    queue = AdvancedFrameQueue(max_size=5)
    
    # Simulate high frame rate input
    for i in range(20):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        success = queue.put_frame(frame, frame_id=i)
        print(f"Frame {i}: {'Added' if success else 'Failed'}")
        
        # Occasionally consume frames
        if i % 3 == 0:
            frame_data = queue.get_frame(timeout=0.1)
            if frame_data:
                print(f"Consumed frame {frame_data['frame_id']}")
    
    print("Final stats:", queue.get_stats())


async def mixed_threading_asyncio():
    """Example combining threading for I/O and asyncio for processing."""
    
    class HybridProcessor:
        def __init__(self):
            self.frame_queue = Queue(maxsize=10)  # Thread-safe queue
            self.result_queue = asyncio.Queue(maxsize=20)  # Async queue
            self.running = False
        
        def camera_thread(self):
            """Camera capture in separate thread."""
            cap = cv2.VideoCapture(0)
            frame_count = 0
            
            while self.running:
                ret, frame = cap.read()
                if ret:
                    try:
                        self.frame_queue.put((frame_count, frame), timeout=0.1)
                        frame_count += 1
                    except Full:
                        print("Frame queue full")
                
                time.sleep(0.033)  # 30 FPS
            
            cap.release()
        
        async def async_processor(self):
            """Async frame processing."""
            while self.running:
                try:
                    # Get frame from thread-safe queue
                    frame_id, frame = self.frame_queue.get(timeout=1.0)
                    
                    # Async processing
                    await asyncio.sleep(0.05)  # Simulate async work
                    
                    result = {
                        'frame_id': frame_id,
                        'human_detected': np.random.random() > 0.5,
                        'timestamp': time.time()
                    }
                    
                    await self.result_queue.put(result)
                    
                except Empty:
                    await asyncio.sleep(0.01)
        
        async def result_monitor(self):
            """Monitor results asynchronously."""
            while self.running:
                try:
                    result = await asyncio.wait_for(
                        self.result_queue.get(), timeout=1.0
                    )
                    print(f"Result: Frame {result['frame_id']} - {result['human_detected']}")
                except asyncio.TimeoutError:
                    continue
        
        async def run(self, duration: float = 10.0):
            """Run hybrid processing system."""
            self.running = True
            
            # Start camera thread
            camera_thread = threading.Thread(target=self.camera_thread)
            camera_thread.start()
            
            try:
                # Run async tasks
                await asyncio.wait_for(
                    asyncio.gather(
                        self.async_processor(),
                        self.result_monitor()
                    ),
                    timeout=duration
                )
            except asyncio.TimeoutError:
                print("Processing complete")
            finally:
                self.running = False
                camera_thread.join()
    
    # Usage
    processor = HybridProcessor()
    await processor.run(duration=5.0)


def performance_monitoring():
    """Performance monitoring for threaded/async processing."""
    
    class PerformanceMonitor:
        def __init__(self):
            self.metrics = {
                'frames_processed': 0,
                'processing_times': [],
                'queue_sizes': [],
                'memory_usage': []
            }
            self.lock = threading.Lock()
        
        def record_frame_processed(self, processing_time: float):
            """Record frame processing metrics."""
            with self.lock:
                self.metrics['frames_processed'] += 1
                self.metrics['processing_times'].append(processing_time)
                
                # Keep only recent measurements
                if len(self.metrics['processing_times']) > 100:
                    self.metrics['processing_times'] = self.metrics['processing_times'][-100:]
        
        def record_queue_size(self, size: int):
            """Record queue size."""
            with self.lock:
                self.metrics['queue_sizes'].append(size)
                if len(self.metrics['queue_sizes']) > 100:
                    self.metrics['queue_sizes'] = self.metrics['queue_sizes'][-100:]
        
        def get_stats(self) -> dict:
            """Get performance statistics."""
            with self.lock:
                if not self.metrics['processing_times']:
                    return {'fps': 0, 'avg_processing_time': 0}
                
                avg_time = sum(self.metrics['processing_times']) / len(self.metrics['processing_times'])
                max_time = max(self.metrics['processing_times'])
                fps = len(self.metrics['processing_times']) / sum(self.metrics['processing_times'])
                
                return {
                    'frames_processed': self.metrics['frames_processed'],
                    'fps': fps,
                    'avg_processing_time': avg_time,
                    'max_processing_time': max_time,
                    'avg_queue_size': sum(self.metrics['queue_sizes']) / max(len(self.metrics['queue_sizes']), 1)
                }
    
    # Usage in processing loop
    monitor = PerformanceMonitor()
    
    def processing_function(frame):
        start_time = time.time()
        
        # Simulate processing
        time.sleep(0.05)
        
        processing_time = time.time() - start_time
        monitor.record_frame_processed(processing_time)
        
        return True  # Mock result
    
    # Simulate processing
    for i in range(20):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        processing_function(frame)
        
        if i % 5 == 0:
            stats = monitor.get_stats()
            print(f"Stats: {stats}")


if __name__ == "__main__":
    print("Threading and AsyncIO Sample Code")
    print("1. Basic threading example")
    print("2. Producer-consumer queue")
    print("3. Thread pool processing")
    print("4. Frame queue with overflow")
    print("5. Performance monitoring")
    print("6. Async frame processing (requires await)")
    print("7. Mixed threading/asyncio (requires await)")
    
    choice = input("Enter choice (1-7): ")
    
    if choice == "1":
        basic_threading_example()
    elif choice == "2":
        producer_consumer_queue()
    elif choice == "3":
        thread_pool_processing()
    elif choice == "4":
        frame_queue_with_overflow()
    elif choice == "5":
        performance_monitoring()
    elif choice == "6":
        print("Run: asyncio.run(async_frame_processing())")
    elif choice == "7":
        print("Run: asyncio.run(mixed_threading_asyncio())")
    else:
        print("Invalid choice") 