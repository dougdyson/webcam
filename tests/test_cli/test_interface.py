"""
Tests for CLI interface - Command-line argument parsing and application entry point.

This module tests the command-line interface that provides the main entry
point for users to run the webcam human detection system with various
configuration options.
"""

import sys
import argparse
from unittest.mock import Mock, patch, AsyncMock
import pytest
import io
import contextlib
import subprocess
import tempfile
import os

from src.cli.parser import CommandParser, CLIError
from src.cli.main import MainApp, MainAppConfig


class TestCommandParser:
    """Test command-line argument parsing and validation."""

    def test_command_parser_creation(self):
        """Should create CommandParser with default configuration."""
        parser = CommandParser()
        
        assert parser is not None
        assert hasattr(parser, 'parser')
        assert isinstance(parser.parser, argparse.ArgumentParser)

    def test_command_parser_default_args(self):
        """Should parse default arguments correctly."""
        parser = CommandParser()
        args = parser.parse(['--profile', 'default'])
        
        assert args.profile == 'default'
        assert args.verbose is False
        assert args.log_level == 'INFO'
        assert args.confidence_threshold == 0.5
        assert args.max_runtime is None

    def test_command_parser_all_options(self):
        """Should parse all command-line options."""
        parser = CommandParser()
        args = parser.parse([
            '--profile', 'high_quality',
            '--verbose',
            '--log-level', 'DEBUG',
            '--confidence-threshold', '0.8',
            '--max-runtime', '300',
            '--log-file', 'app.log',
            '--no-display',
            '--config-file', 'custom_config.yaml'
        ])
        
        assert args.profile == 'high_quality'
        assert args.verbose is True
        assert args.log_level == 'DEBUG'
        assert args.confidence_threshold == 0.8
        assert args.max_runtime == 300
        assert args.log_file == 'app.log'
        assert args.no_display is True
        assert args.config_file == 'custom_config.yaml'

    def test_command_parser_help_text(self):
        """Should provide helpful usage information."""
        parser = CommandParser()
        
        # Should not raise when getting help
        help_text = parser.get_help()
        assert 'webcam human detection' in help_text.lower()
        assert 'profile' in help_text
        assert 'confidence' in help_text

    def test_command_parser_validation_confidence_threshold(self):
        """Should validate confidence threshold range."""
        parser = CommandParser()
        
        # Valid range
        args = parser.parse(['--confidence-threshold', '0.7'])
        assert args.confidence_threshold == 0.7
        
        # Invalid range - should raise error
        with pytest.raises(CLIError):
            parser.parse(['--confidence-threshold', '1.5'])
        
        with pytest.raises(CLIError):
            parser.parse(['--confidence-threshold', '-0.1'])

    def test_command_parser_validation_log_level(self):
        """Should validate log level options."""
        parser = CommandParser()
        
        # Valid log levels
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            args = parser.parse(['--log-level', level])
            assert args.log_level == level
        
        # Invalid log level
        with pytest.raises(CLIError):
            parser.parse(['--log-level', 'INVALID'])

    def test_command_parser_validation_max_runtime(self):
        """Should validate max runtime parameter."""
        parser = CommandParser()
        
        # Valid runtime
        args = parser.parse(['--max-runtime', '60'])
        assert args.max_runtime == 60
        
        # Invalid runtime
        with pytest.raises(CLIError):
            parser.parse(['--max-runtime', '-10'])

    def test_command_parser_profile_options(self):
        """Should handle different camera profiles."""
        parser = CommandParser()
        
        for profile in ['default', 'high_quality', 'low_latency', 'debug']:
            args = parser.parse(['--profile', profile])
            assert args.profile == profile

    def test_command_parser_unknown_args(self):
        """Should handle unknown arguments gracefully."""
        parser = CommandParser()
        
        with pytest.raises(CLIError):
            parser.parse(['--unknown-option', 'value'])

    def test_command_parser_config_to_main_app_config(self):
        """Should convert CLI args to MainAppConfig."""
        parser = CommandParser()
        args = parser.parse([
            '--profile', 'high_quality',
            '--confidence-threshold', '0.8',
            '--log-level', 'DEBUG',
            '--max-runtime', '600'
        ])
        
        config = parser.args_to_config(args)
        
        assert isinstance(config, MainAppConfig)
        assert config.camera_profile == 'high_quality'
        assert config.detection_confidence_threshold == 0.8
        assert config.log_level == 'DEBUG'
        assert config.max_runtime_seconds == 600


class TestCLIApplication:
    """Test CLI application entry point and integration."""

    @patch('src.cli.parser.CommandParser')
    @patch('src.cli.main.MainApp')
    def test_cli_app_initialization(self, mock_main_app, mock_parser):
        """Should initialize CLI application with parsed arguments."""
        from src.cli.app import CLIApp
        
        # Mock parser and args
        mock_args = Mock()
        mock_args.profile = 'default'
        mock_args.verbose = False
        mock_parser.return_value.parse.return_value = mock_args
        mock_parser.return_value.args_to_config.return_value = MainAppConfig()
        
        # Create CLI app
        cli_app = CLIApp()
        cli_app.initialize(['--profile', 'default'])
        
        # Should parse arguments and create MainApp
        mock_parser.return_value.parse.assert_called_once()
        mock_main_app.assert_called_once()

    @patch('src.cli.app.MainApp')
    def test_cli_app_run_with_valid_args(self, mock_main_app):
        """Should run application with valid arguments."""
        from src.cli.app import CLIApp
        
        # Mock successful app execution
        mock_app_instance = mock_main_app.return_value
        mock_app_instance.initialize = Mock()
        mock_app_instance.setup_signal_handlers = Mock()
        mock_app_instance.run = AsyncMock()
        
        cli_app = CLIApp()
        result = cli_app.run(['--profile', 'default'])
        
        # Should initialize and run MainApp
        mock_app_instance.initialize.assert_called_once()
        mock_app_instance.setup_signal_handlers.assert_called_once()
        mock_app_instance.run.assert_called_once()
        assert result == 0

    def test_cli_app_handles_parse_errors(self):
        """Should handle command-line parsing errors gracefully."""
        import subprocess
        import sys
        
        # Test with subprocess to avoid pytest interference
        result = subprocess.run([
            sys.executable, '-c',
            'from src.cli.app import CLIApp; '
            'import sys; '
            'sys.exit(CLIApp().run(["--invalid-option"]))'
        ], capture_output=True, cwd='.')
        
        # Should return correct argparse error exit code
        assert result.returncode == 2

    @patch('src.cli.app.MainApp')
    def test_cli_app_handles_application_errors(self, mock_main_app):
        """Should handle application runtime errors gracefully."""
        from src.cli.app import CLIApp
        
        # Mock application error during run
        mock_app_instance = mock_main_app.return_value
        mock_app_instance.initialize = Mock(side_effect=Exception("Runtime error"))
        
        cli_app = CLIApp()
        result = cli_app.run(['--profile', 'default'])
        
        # Should return error exit code
        assert result == 1

    @patch('sys.argv', ['webcam-detect', '--profile', 'default', '--verbose'])
    @patch('src.cli.app.CLIApp')
    def test_main_entry_point(self, mock_cli_app):
        """Should provide main entry point for application."""
        from src.cli.app import main
        
        # Mock CLI app
        mock_app_instance = mock_cli_app.return_value
        mock_app_instance.run.return_value = 0
        
        # Call main entry point
        result = main()
        
        # Should create and run CLI app with sys.argv
        mock_cli_app.assert_called_once()
        mock_app_instance.run.assert_called_once_with(['--profile', 'default', '--verbose'])
        assert result == 0

    def test_cli_app_version_display(self):
        """Should display version information when requested."""
        from src.cli.app import CLIApp
        
        cli_app = CLIApp()
        
        # Capture actual output using pytest's capsys or just test return code
        result = cli_app.run(['--version'])
        
        # Should exit successfully - version is printed by argparse
        assert result == 0


class TestCLIError:
    """Test CLI error handling and exception management."""

    def test_cli_error_creation(self):
        """Should create CLIError with message."""
        error = CLIError("Invalid command line arguments")
        
        assert str(error) == "Invalid command line arguments"
        assert isinstance(error, Exception)

    def test_cli_error_with_exit_code(self):
        """Should support custom exit codes."""
        error = CLIError("Parse error", exit_code=2)
        
        assert str(error) == "Parse error"
        assert error.exit_code == 2

    def test_cli_error_inheritance(self):
        """Should inherit from Exception."""
        error = CLIError("Test error")
        assert isinstance(error, Exception)


class TestCLIIntegration:
    """Integration tests for complete CLI workflow."""

    @patch('src.cli.app.MainApp')
    def test_complete_cli_workflow(self, mock_main_app):
        """Should handle complete CLI workflow from args to execution."""
        # Setup mocks for MainApp only
        mock_app_instance = mock_main_app.return_value
        mock_app_instance.initialize = Mock()
        mock_app_instance.setup_signal_handlers = Mock()
        # Use regular Mock instead of AsyncMock to avoid coroutine issues
        mock_app_instance.run = Mock(return_value=None)
        mock_app_instance.get_statistics.return_value = {
            'frames_processed': 100,
            'uptime_seconds': 10.0
        }
        
        # Run CLI workflow
        from src.cli.app import CLIApp
        cli_app = CLIApp()
        result = cli_app.run(['--profile', 'default', '--verbose'])
        
        # Should complete successfully
        assert result == 0
        mock_app_instance.initialize.assert_called_once()
        mock_app_instance.run.assert_called_once()

    def test_cli_help_integration(self):
        """Should provide comprehensive help text."""
        import subprocess
        import sys
        import tempfile
        import os
        
        # Create a temporary script to run the CLI help command
        script_content = '''
import sys
import os
sys.path.insert(0, os.getcwd())

from src.cli.app import CLIApp

try:
    result = CLIApp().run(["--help"])
    sys.exit(result)
except SystemExit as e:
    sys.exit(e.code)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Test with subprocess to avoid pytest interference
            result = subprocess.run([
                sys.executable, script_path
            ], capture_output=True, cwd='.', text=True)
            
            # Should display help and exit successfully
            assert result.returncode == 0
            assert 'Webcam Human Detection System' in result.stdout
            assert 'profile' in result.stdout
            assert 'confidence-threshold' in result.stdout
        finally:
            os.unlink(script_path) 