"""
Command-line argument parsing for webcam human detection system.

This module provides the CommandParser class that handles parsing and
validation of command-line arguments, converting them to application
configuration.
"""

import argparse
import sys
from typing import List, Optional

from .main import MainAppConfig


class CLIError(Exception):
    """Exception raised by CLI operations."""
    
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class CommandParser:
    """Command-line argument parser with validation."""
    
    def __init__(self):
        """Initialize the command parser."""
        self.parser = argparse.ArgumentParser(
            prog='webcam-detect',
            description='Webcam Human Detection System - Real-time human presence detection using computer vision',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  webcam-detect --profile default
  webcam-detect --profile high_quality --verbose
  webcam-detect --confidence-threshold 0.8 --max-runtime 300
  webcam-detect --log-level DEBUG --log-file detection.log
            """
        )
        self._setup_arguments()
    
    def _setup_arguments(self) -> None:
        """Set up command-line arguments."""
        
        # Camera profile
        self.parser.add_argument(
            '--profile',
            default='default',
            choices=['default', 'high_quality', 'low_latency', 'debug'],
            help='Camera profile to use (default: %(default)s)'
        )
        
        # Logging options
        self.parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose output'
        )
        
        self.parser.add_argument(
            '--log-level',
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Set logging level (default: %(default)s)'
        )
        
        self.parser.add_argument(
            '--log-file',
            help='Log file path (default: console only)'
        )
        
        # Detection options
        self.parser.add_argument(
            '--detector-type',
            default='multimodal',
            choices=['mediapipe', 'multimodal', 'pose', 'pose_face'],
            help='Detection algorithm to use: multimodal (pose+face, best range), mediapipe (pose only), pose (alias for mediapipe), pose_face (alias for multimodal) (default: %(default)s)'
        )
        
        self.parser.add_argument(
            '--confidence-threshold',
            type=float,
            default=0.5,
            help='Minimum confidence threshold for detection (0.0-1.0, default: %(default)s)'
        )
        
        # Runtime options
        self.parser.add_argument(
            '--max-runtime',
            type=int,
            help='Maximum runtime in seconds (default: unlimited)'
        )
        
        # Display options
        self.parser.add_argument(
            '--no-display',
            action='store_true',
            help='Disable real-time display output'
        )
        
        # Configuration
        self.parser.add_argument(
            '--config-file',
            help='Custom configuration file path'
        )
        
        # Version
        self.parser.add_argument(
            '--version',
            action='version',
            version='%(prog)s 1.0.0'
        )
    
    def parse(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command-line arguments with validation.
        
        Args:
            args: List of arguments to parse (defaults to sys.argv)
            
        Returns:
            Parsed arguments namespace
            
        Raises:
            CLIError: If arguments are invalid
            SystemExit: For --help, --version (with code 0)
        """
        try:
            parsed_args = self.parser.parse_args(args)
            self._validate_arguments(parsed_args)
            return parsed_args
        except argparse.ArgumentError as e:
            raise CLIError(f"Invalid argument: {e}")
        except SystemExit as e:
            # Re-raise SystemExit for --help (0) and --version (0)
            # Convert argument errors (2) to CLIError
            if e.code == 0:
                raise  # --help, --version
            else:
                raise CLIError("Invalid command line arguments", exit_code=e.code)
    
    def _validate_arguments(self, args: argparse.Namespace) -> None:
        """
        Validate parsed arguments.
        
        Args:
            args: Parsed arguments to validate
            
        Raises:
            CLIError: If validation fails
        """
        # Validate confidence threshold
        if not 0.0 <= args.confidence_threshold <= 1.0:
            raise CLIError(
                f"Confidence threshold must be between 0.0 and 1.0, got {args.confidence_threshold}"
            )
        
        # Validate max runtime
        if args.max_runtime is not None and args.max_runtime <= 0:
            raise CLIError(
                f"Max runtime must be positive, got {args.max_runtime}"
            )
    
    def get_help(self) -> str:
        """
        Get help text for the parser.
        
        Returns:
            Help text string
        """
        return self.parser.format_help()
    
    def args_to_config(self, args: argparse.Namespace) -> MainAppConfig:
        """
        Convert parsed arguments to MainAppConfig.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            MainAppConfig instance
        """
        return MainAppConfig(
            camera_profile=args.profile,
            detector_type=args.detector_type,
            detection_confidence_threshold=args.confidence_threshold,
            log_level=args.log_level,
            log_file=args.log_file,
            enable_logging=True,  # Always enable logging
            enable_display=not args.no_display,
            max_runtime_seconds=args.max_runtime,
            config_file=args.config_file
        ) 