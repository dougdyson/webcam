"""
CLI application entry point for webcam human detection system.

This module provides the CLIApp class that coordinates the complete
command-line interface workflow from argument parsing to application
execution.
"""

import asyncio
import sys
from typing import List, Optional

from .parser import CommandParser, CLIError
from .main import MainApp, MainAppError


class CLIApp:
    """Command-line interface application coordinator."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.parser = CommandParser()
        self.main_app: Optional[MainApp] = None
    
    def initialize(self, argv: List[str]) -> None:
        """
        Initialize application with command-line arguments.
        
        Args:
            argv: Command-line arguments to parse
            
        Raises:
            CLIError: If initialization fails
            SystemExit: For --help, --version (success), or parsing errors
        """
        try:
            args = self.parser.parse(argv)
            config = self.parser.args_to_config(args)
            self.main_app = MainApp(config)
        except CLIError:
            raise
        except SystemExit:
            # Re-raise SystemExit for --help, --version, or argument errors
            raise
        except Exception as e:
            raise CLIError(f"Initialization failed: {e}")
    
    def run(self, argv: Optional[List[str]] = None) -> int:
        """
        Run the CLI application.
        
        Args:
            argv: Command-line arguments (defaults to sys.argv[1:])
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        if argv is None:
            argv = sys.argv[1:]
        
        try:
            # Initialize application (this will handle --help, --version, etc.)
            self.initialize(argv)
            
            if self.main_app is None:
                raise CLIError("Application not initialized")
            
            # Initialize and run main application
            self.main_app.initialize()
            self.main_app.setup_signal_handlers()
            
            # Run the application - handle both real and mocked runs
            app_run = self.main_app.run()
            if asyncio.iscoroutine(app_run):
                # Real coroutine - use asyncio.run
                asyncio.run(app_run)
            # If it's a mock, app_run will not be a coroutine and we don't need to await it
            
            return 0
            
        except CLIError as e:
            print(f"Error: {e}", file=sys.stderr)
            return e.exit_code
        except SystemExit as e:
            # Handle --help and --version which cause SystemExit
            if e.code == 0:
                return 0  # Success for --help, --version
            return e.code  # Error exit code
        except KeyboardInterrupt:
            print("\nInterrupted by user", file=sys.stderr)
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return 1


def main() -> int:
    """
    Main entry point for the application.
    
    Returns:
        Exit code
    """
    cli_app = CLIApp()
    return cli_app.run(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main()) 