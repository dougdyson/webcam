import time
from unittest.mock import Mock, patch
import numpy as np
from src.camera.manager import CameraManager
from src.camera.config import CameraConfig

# Test the timing manually
config = CameraConfig()

with patch('cv2.VideoCapture') as mock_cv2:
    mock_cap1 = Mock()
    mock_cap2 = Mock()
    mock_cap3 = Mock()
    
    mock_cap1.isOpened.return_value = True
    mock_cap1.read.return_value = (False, None)
    mock_cap1.get.side_effect = lambda prop: {2: 640, 3: 480, 5: 30.0}.get(prop, 0)
    mock_cap1.set.return_value = True
    mock_cap1.release.return_value = None
    
    mock_cap2.isOpened.return_value = False
    mock_cap2.get.side_effect = lambda prop: {2: 640, 3: 480, 5: 30.0}.get(prop, 0)
    mock_cap2.set.return_value = True
    mock_cap2.release.return_value = None
    
    mock_cap3.isOpened.return_value = True
    mock_cap3.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mock_cap3.get.side_effect = lambda prop: {2: 640, 3: 480, 5: 30.0}.get(prop, 0)
    mock_cap3.set.return_value = True
    
    mock_cv2.side_effect = [mock_cap1, mock_cap2, mock_cap3]
    
    manager = CameraManager(config)
    
    start_time = time.time()
    print('Making first call...')
    frame1 = manager.get_frame()
    print(f'First call result: {frame1 is not None}')
    
    print('Waiting 0.01 seconds...')
    time.sleep(0.01)
    
    print('Making second call...')
    frame2 = manager.get_frame()
    print(f'Second call result: {frame2 is not None}')
    
    elapsed = time.time() - start_time
    print(f'Total elapsed: {elapsed:.3f}s')
    
    stats = manager.get_statistics()
    print(f'Total reconnection attempts: {stats["total_reconnection_attempts"]}') 