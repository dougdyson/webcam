#!/usr/bin/env python3

def test_parse_error_direct():
    """Test parse error handling directly."""
    from src.cli.app import CLIApp
    
    print("Testing parse error handling...")
    cli_app = CLIApp()
    result = cli_app.run(['--invalid-option'])
    print(f"Result: {result}")
    assert result == 2, f"Expected 2, got {result}"
    print("Parse error test: PASSED")

def test_help_output():
    """Test help output capture."""
    from src.cli.app import CLIApp
    import io
    import contextlib
    
    print("Testing help output...")
    cli_app = CLIApp()
    
    # Try different capture methods
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
        result = cli_app.run(['--help'])
    
    stdout_content = stdout_capture.getvalue()
    stderr_content = stderr_capture.getvalue()
    
    print(f"Result: {result}")
    print(f"Stdout length: {len(stdout_content)}")
    print(f"Stderr length: {len(stderr_content)}")
    
    if stdout_content:
        print(f"Stdout first 100 chars: {stdout_content[:100]}")
    if stderr_content:
        print(f"Stderr first 100 chars: {stderr_content[:100]}")

if __name__ == '__main__':
    print("=== Direct Testing ===")
    test_parse_error_direct()
    print("\n=== Help Output Testing ===")
    test_help_output() 