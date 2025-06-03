"""
Tests for logging configuration and utilities.
"""
import pytest
import os
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, Mock

from src.utils.logger import LoggerManager, LoggerError


class TestLoggerManager:
    """Test cases for LoggerManager class."""
    
    def test_logger_manager_creates_default_config(self):
        """Should create logger with default configuration."""
        logger_manager = LoggerManager()
        logger = logger_manager.get_logger('test')
        
        assert logger is not None
        assert logger.name == 'test'
        assert logger.level == logging.INFO
    
    def test_logger_manager_loads_from_config(self):
        """Should load logger configuration from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
logging:
  level: DEBUG
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  handlers:
    console:
      enabled: true
      level: INFO
    file:
      enabled: true
      level: DEBUG
      filename: 'webcam.log'
""")
            config_file = f.name
        
        try:
            logger_manager = LoggerManager(config_file=config_file)
            logger = logger_manager.get_logger('test')
            
            assert logger.level == logging.DEBUG
            assert len(logger.handlers) >= 1
        finally:
            os.unlink(config_file)
    
    def test_logger_manager_handles_missing_config(self):
        """Should handle missing configuration file gracefully."""
        with pytest.raises(LoggerError):
            LoggerManager(config_file='nonexistent.yaml')
    
    def test_logger_manager_creates_file_handler(self):
        """Should create file handler when configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            logger_manager = LoggerManager()
            logger = logger_manager.configure_file_logging('test', str(log_file))
            
            assert logger is not None
            # Check that file handler was added
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            assert len(file_handlers) > 0
    
    def test_logger_manager_creates_console_handler(self):
        """Should create console handler when configured."""
        logger_manager = LoggerManager()
        logger = logger_manager.configure_console_logging('test')
        
        assert logger is not None
        # Check that console handler was added
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0
    
    def test_logger_manager_formats_messages(self):
        """Should format log messages according to configuration."""
        logger_manager = LoggerManager()
        logger = logger_manager.get_logger('test')
        
        # Check that formatter is set
        for handler in logger.handlers:
            assert handler.formatter is not None
    
    def test_logger_manager_handles_log_levels(self):
        """Should properly handle different log levels."""
        logger_manager = LoggerManager()
        
        # Test different levels
        debug_logger = logger_manager.get_logger('debug', level='DEBUG')
        info_logger = logger_manager.get_logger('info', level='INFO')
        warning_logger = logger_manager.get_logger('warning', level='WARNING')
        
        assert debug_logger.level == logging.DEBUG
        assert info_logger.level == logging.INFO
        assert warning_logger.level == logging.WARNING
    
    def test_logger_error_inherits_from_exception(self):
        """LoggerError should inherit from Exception."""
        error = LoggerError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestLoggerIntegration:
    """Integration tests for logger functionality."""
    
    def test_logger_writes_to_file(self):
        """Should write log messages to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            logger_manager = LoggerManager()
            logger = logger_manager.configure_file_logging('test', str(log_file))
            
            test_message = "Test log message"
            logger.info(test_message)
            
            # Force flush
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
            
            assert log_file.exists()
            content = log_file.read_text()
            assert test_message in content
    
    def test_logger_rotates_files(self):
        """Should rotate log files when size limit reached."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / 'test.log'
            
            logger_manager = LoggerManager()
            logger = logger_manager.configure_rotating_file_logging(
                'test', 
                str(log_file), 
                max_bytes=1024,  # Small size for testing
                backup_count=3
            )
            
            # Write enough data to trigger rotation
            large_message = "A" * 500  # 500 chars
            for i in range(5):  # Write 2500 chars total
                logger.info(f"{large_message} - Message {i}")
            
            # Force flush
            for handler in logger.handlers:
                if hasattr(handler, 'doRollover'):
                    handler.flush()
            
            # Should have created backup files
            backup_files = list(Path(temp_dir).glob('test.log.*'))
            assert len(backup_files) > 0 or log_file.stat().st_size < 2500 