#!/usr/bin/env python3

from src.cli.app import CLIApp

def test_cli_behavior():
    print("Testing CLI behavior...")
    app = CLIApp()
    
    print("1. Testing invalid option:")
    try:
        result = app.run(['--invalid-option'])
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Exception: {type(e).__name__}: {e}")
    
    print("\n2. Testing valid option:")
    try:
        # Use mock to prevent actual app running
        import unittest.mock
        with unittest.mock.patch('src.cli.app.MainApp') as mock_app:
            mock_instance = mock_app.return_value
            mock_instance.initialize.return_value = None
            mock_instance.setup_signal_handlers.return_value = None
            mock_instance.run.return_value = None
            
            result = app.run(['--profile', 'default'])
            print(f"   Result: {result}")
    except Exception as e:
        print(f"   Exception: {type(e).__name__}: {e}")

if __name__ == '__main__':
    test_cli_behavior() 