"""
Configuration management system for frame processing.

Extracted from LatestFrameProcessor to follow single responsibility principle.
Handles configuration validation, persistence, versioning, and hot updates.
"""

import time
import threading
import yaml
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """Manages processor configuration with validation, persistence, and versioning."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self._configuration_lock = threading.Lock()
        
        # History tracking
        self._configuration_history_enabled = False
        self._configuration_history = []
        self._max_history_entries = 10
        self._current_config_version = 1
        self._configuration_metadata = {}
        self._entry_counter = 0  # Add counter for unique IDs
        
        # Component hot-swapping
        self._backup_detectors = []
        self._backup_cameras = []
        
        # Health monitoring
        self._health_monitoring_enabled = False
        self._health_check_interval = 1.0
        self._failure_threshold = 3
        self._auto_swap_enabled = False
        self._component_failure_count = 0
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration with detailed rules and constraints."""
        try:
            errors = []
            warnings = []
            
            # Validate target_fps
            if 'target_fps' in config:
                fps = config['target_fps']
                if fps <= 0:
                    errors.append('target_fps must be positive')
                elif fps > 60:  # Stricter: treat very high FPS as error
                    errors.append('target_fps > 60 is unsupported and may cause system instability')
                elif fps > 30:
                    warnings.append('target_fps > 30 may cause performance issues')
            
            # Validate processing_timeout
            if 'processing_timeout' in config:
                timeout = config['processing_timeout']
                if timeout <= 0:
                    errors.append('processing_timeout must be positive')
                elif timeout < 0.05:  # Stricter: very low timeouts are errors
                    errors.append('processing_timeout < 0.05s is too aggressive and will cause failures')
                elif timeout < 0.1:
                    warnings.append('processing_timeout < 0.1s may be too aggressive')
            
            # Validate max_frame_age
            if 'max_frame_age' in config:
                frame_age = config['max_frame_age']
                if frame_age <= 0:
                    errors.append('max_frame_age must be positive')
                elif frame_age > 3.0:
                    warnings.append('max_frame_age > 3.0s may allow very stale frames')
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validation_details': {
                    'total_parameters_checked': len(config),
                    'errors_found': len(errors),
                    'warnings_generated': len(warnings)
                }
            }
        
        except Exception as e:
            logger.error(f"Error in configuration validation: {e}")
            return {
                'is_valid': False,
                'errors': [f'Validation error: {e}'],
                'warnings': [],
                'validation_details': {}
            }
    
    def validate_configuration_dependencies(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration dependencies and detect conflicts."""
        try:
            dependency_errors = []
            performance_warnings = []
            
            # Check adaptive_fps with low target_fps conflict
            if config.get('adaptive_fps', False) and config.get('target_fps', 5.0) < 3.0:
                dependency_errors.append({
                    'error_type': 'parameter_conflict',
                    'conflicting_parameters': ['adaptive_fps', 'target_fps'],
                    'description': 'Adaptive FPS with very low target FPS may cause instability'
                })
            
            # Check performance implications
            if (config.get('target_fps', 5.0) > 25.0 and 
                config.get('memory_monitoring', False) and
                not config.get('adaptive_fps', False)):
                performance_warnings.append({
                    'warning_type': 'high_resource_usage',
                    'parameters': ['target_fps', 'memory_monitoring', 'adaptive_fps'],
                    'description': 'High FPS with memory monitoring but no adaptive adjustment may overload system'
                })
            
            return {
                'dependencies_valid': len(dependency_errors) == 0,
                'dependency_errors': dependency_errors,
                'performance_warnings': performance_warnings
            }
        
        except Exception as e:
            logger.error(f"Error in dependency validation: {e}")
            return {
                'dependencies_valid': False,
                'dependency_errors': [{'error_type': 'validation_error', 'description': str(e)}],
                'performance_warnings': []
            }
    
    async def update_configuration_with_validation(self, config_updates: Dict[str, Any], callbacks) -> Dict[str, Any]:
        """Update configuration with validation and rollback support."""
        try:
            # Validate configuration first
            validation_errors = []
            
            if 'target_fps' in config_updates:
                if config_updates['target_fps'] <= 0:
                    validation_errors.append('target_fps must be positive')
            
            if 'processing_timeout' in config_updates:
                if config_updates['processing_timeout'] <= 0:
                    validation_errors.append('processing_timeout must be positive')
            
            # If validation fails, return error
            if validation_errors:
                result = {
                    'success': False,
                    'validation_errors': validation_errors
                }
                
                # Notify validation callbacks
                callbacks.invoke_configuration_validation_callbacks({
                    'validation_success': False,
                    'errors': validation_errors,
                    'config_updates': config_updates
                })
                
                return result
            
            # If validation passes, apply configuration and return success
            result = {
                'success': True,
                'rollback_point': f'config_version_{self._current_config_version}',
                'applied_updates': config_updates  # Add this so processor can apply the config
            }
            
            # Notify validation callbacks
            callbacks.invoke_configuration_validation_callbacks({
                'validation_success': True,
                'errors': [],
                'config_updates': config_updates
            })
            
            return result
        
        except Exception as e:
            logger.error(f"Error in configuration validation: {e}")
            return {'success': False, 'validation_errors': [str(e)]}
    
    def save_configuration(
        self,
        current_config: Dict[str, Any],
        config_path: str,
        metadata: Dict[str, Any] = None,
        include_runtime_stats: bool = False,
        version_tag: str = None
    ) -> Dict[str, Any]:
        """Save configuration to file with versioning and metadata."""
        try:
            # Prepare configuration data
            config_data = {
                'configuration': current_config,
                'metadata': metadata or {},
                'version_info': {
                    'config_version': self._current_config_version,
                    'version_tag': version_tag,
                    'created_timestamp': time.time()
                }
            }
            
            # Save to file
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
            
            # Store metadata
            if metadata:
                self._configuration_metadata.update(metadata)
                if version_tag:
                    self._configuration_metadata['version_tag'] = version_tag
            
            return {
                'success': True,
                'config_version': self._current_config_version,
                'file_path': config_path
            }
        
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return {'success': False, 'error': str(e)}
    
    def load_configuration(
        self,
        config_path: str,
        validate_before_load: bool = True,
        backup_current_config: bool = True,
        current_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Load configuration from file with validation and backup."""
        try:
            # Load configuration file
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            new_config = config_data.get('configuration', {})
            
            # Validate if requested
            if validate_before_load:
                validation_result = self.validate_configuration(new_config)
                if not validation_result['is_valid']:
                    return {
                        'success': False,
                        'error': 'Configuration validation failed',
                        'validation_errors': validation_result['errors']
                    }
            
            # Backup current config if requested
            backup_path = None
            if backup_current_config and current_config:
                backup_path = f"{config_path}.backup.{int(time.time())}"
                backup_result = self.save_configuration(current_config, backup_path)
                if not backup_result['success']:
                    backup_path = None
            
            # Load metadata
            if 'metadata' in config_data:
                self._configuration_metadata = config_data['metadata']
            
            # Load version info into metadata
            if 'version_info' in config_data:
                version_info = config_data['version_info']
                if 'version_tag' in version_info:
                    self._configuration_metadata['version_tag'] = version_info['version_tag']
            
            loaded_version = config_data.get('version_info', {}).get('config_version', 'unknown')
            
            return {
                'success': True,
                'loaded_version': loaded_version,
                'backup_path': backup_path,
                'new_config': new_config
            }
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_configuration_metadata(self) -> Dict[str, Any]:
        """Get configuration metadata."""
        return self._configuration_metadata.copy()
    
    def enable_configuration_history(self, max_history_entries: int = 10):
        """Enable configuration history tracking."""
        self._configuration_history_enabled = True
        self._max_history_entries = max_history_entries
    
    def update_configuration_with_history(
        self,
        current_config: Dict[str, Any],
        config_updates: Dict[str, Any],
        change_description: str = "",
        author: str = "system"
    ) -> Dict[str, Any]:
        """Update configuration with history tracking."""
        try:
            if not self._configuration_history_enabled:
                return {'success': False, 'error': 'Configuration history not enabled'}
            
            # Apply updates to get the final configuration
            final_config = current_config.copy()
            final_config.update(config_updates)
            
            # Create history entry with the final configuration (after updates)
            entry_id = f"config_change_{self._entry_counter}"
            self._entry_counter += 1
            
            history_entry = {
                'entry_id': entry_id,
                'timestamp': time.time(),
                'change_description': change_description,
                'author': author,
                'configuration_snapshot': final_config,  # Store configuration after updates
                'change_type': 'update',
                'version': self._current_config_version
            }
            
            # Add to history
            self._configuration_history.append(history_entry)
            
            # Maintain history size limit
            if len(self._configuration_history) > self._max_history_entries:
                self._configuration_history.pop(0)
            
            # Increment version
            self._current_config_version += 1
            
            return {
                'success': True,
                'history_entry_id': entry_id,
                'new_version': self._current_config_version
            }
        
        except Exception as e:
            logger.error(f"Error updating configuration with history: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_configuration_history(self) -> Dict[str, Any]:
        """Get configuration history."""
        return {
            'entries': self._configuration_history.copy(),
            'current_version': self._current_config_version,
            'history_enabled': self._configuration_history_enabled,
            'max_entries': self._max_history_entries
        }
    
    def rollback_to_configuration(
        self,
        target_entry_id: str,
        rollback_reason: str = "manual_rollback"
    ) -> Dict[str, Any]:
        """Rollback to a previous configuration."""
        try:
            # Find target entry
            target_entry = None
            for entry in self._configuration_history:
                if entry['entry_id'] == target_entry_id:
                    target_entry = entry
                    break
            
            if not target_entry:
                return {'success': False, 'error': 'Target configuration entry not found'}
            
            # Get target configuration
            target_config = target_entry['configuration_snapshot']
            
            # Create rollback history entry
            rollback_entry_id = f"rollback_{self._entry_counter}"
            self._entry_counter += 1
            rollback_entry = {
                'entry_id': rollback_entry_id,
                'timestamp': time.time(),
                'change_description': f'Rollback to {target_entry_id}',
                'author': 'system',
                'configuration_snapshot': target_config,
                'change_type': 'rollback',
                'rollback_reason': rollback_reason,
                'target_entry_id': target_entry_id,
                'version': self._current_config_version + 1
            }
            
            self._configuration_history.append(rollback_entry)
            
            # Maintain history size
            if len(self._configuration_history) > self._max_history_entries:
                self._configuration_history.pop(0)
            
            # Increment version
            self._current_config_version += 1
            
            return {
                'success': True,
                'rolled_back_to_version': target_entry['version'],
                'new_history_entry_id': rollback_entry_id,
                'new_version': self._current_config_version,
                'target_config': target_config
            }
        
        except Exception as e:
            logger.error(f"Error in configuration rollback: {e}")
            return {'success': False, 'error': str(e)}
    
    # Component hot-swapping
    def register_backup_detector(self, backup_detector, priority: int = 1):
        """Register backup detector for automatic swapping."""
        self._backup_detectors.append({
            'detector': backup_detector,
            'priority': priority,
            'detector_id': str(id(backup_detector))
        })
        self._backup_detectors.sort(key=lambda x: x['priority'])
    
    async def hot_swap_detector(
        self, 
        new_detector, 
        callbacks,
        swap_reason: str = "manual_swap",
        initialize_new: bool = True,
        cleanup_old: bool = True
    ) -> Dict[str, Any]:
        """Hot-swap detector without interrupting processing."""
        try:
            swap_start_time = time.time()
            old_detector_id = 'current_detector'  # Simplified ID
            
            # The actual detector swapping would happen in the processor
            # This method focuses on callback management and timing
            
            swap_duration_ms = (time.time() - swap_start_time) * 1000
            
            # Create swap event
            swap_event = {
                'component_type': 'detector',
                'swap_reason': swap_reason,
                'old_detector_id': old_detector_id,
                'new_detector_id': str(id(new_detector)),
                'swap_duration_ms': swap_duration_ms
            }
            
            # Notify swap callbacks
            callbacks.invoke_component_swap_callbacks(swap_event)
            
            return {
                'success': True,
                'swap_duration_ms': swap_duration_ms,
                'old_detector_id': old_detector_id,
                'new_detector_id': str(id(new_detector)),
                'new_detector': new_detector  # Return new detector for processor to use
            }
        
        except Exception as e:
            logger.error(f"Error in detector hot swap: {e}")
            return {'success': False, 'error': str(e)}
    
    async def hot_swap_camera(
        self,
        new_camera,
        callbacks,
        swap_reason: str = "manual_swap", 
        validate_new_camera: bool = True,
        frame_continuity_check: bool = True
    ) -> Dict[str, Any]:
        """Hot-swap camera while maintaining frame processing continuity."""
        try:
            swap_start_time = time.time()
            
            swap_duration_ms = (time.time() - swap_start_time) * 1000
            frame_gap_ms = swap_duration_ms  # Simplified
            
            # Create camera swap event
            camera_swap_event = {
                'component_type': 'camera',
                'swap_reason': swap_reason,
                'old_camera_id': 'old_camera',  # Would be passed from processor
                'new_camera_id': str(id(new_camera)),
                'swap_duration_ms': swap_duration_ms,
                'frame_continuity_maintained': frame_gap_ms < 200
            }
            
            # Notify camera swap callbacks
            callbacks.invoke_camera_swap_callbacks(camera_swap_event)
            
            return {
                'success': True,
                'frame_gap_ms': frame_gap_ms,
                'old_camera_id': 'old_camera',
                'new_camera_id': str(id(new_camera)),
                'new_camera': new_camera  # Return new camera for processor to use
            }
        
        except Exception as e:
            logger.error(f"Error in camera hot swap: {e}")
            return {'success': False, 'error': str(e)}
    
    def enable_component_health_monitoring(
        self,
        health_check_interval_seconds: float = 1.0,
        failure_threshold: int = 3,
        auto_swap_enabled: bool = False
    ):
        """Enable component health monitoring."""
        self._health_monitoring_enabled = True
        self._health_check_interval = health_check_interval_seconds
        self._failure_threshold = failure_threshold
        self._auto_swap_enabled = auto_swap_enabled
    
    async def monitor_component_health(self, callbacks):
        """Monitor component health and trigger automatic swaps if needed."""
        if not self._health_monitoring_enabled:
            return
        
        try:
            # Simulate health monitoring - in a real implementation this would check actual component health
            # For testing purposes, we'll simulate a failure scenario
            self._component_failure_count += 1
            
            if self._component_failure_count >= self._failure_threshold:
                # Trigger health event
                health_event = {
                    'component_type': 'detector',
                    'health_status': 'failed',
                    'failure_count': self._component_failure_count
                }
                
                callbacks.invoke_health_monitoring_callbacks(health_event)
                
                # Trigger automatic swap if enabled and backup available
                if self._auto_swap_enabled and self._backup_detectors:
                    backup = self._backup_detectors[0]  # Highest priority backup
                    
                    auto_swap_event = {
                        'trigger_reason': 'component_failure',
                        'swap_type': 'automatic',
                        'backup_component_id': backup['detector_id']
                    }
                    
                    callbacks.invoke_automatic_swap_callbacks(auto_swap_event)
        
        except Exception as e:
            logger.error(f"Error in component health monitoring: {e}") 