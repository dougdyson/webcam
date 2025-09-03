#!/usr/bin/env python3
"""
Enhanced Room System Test Runner

Quick script to run all tests for the enhanced room system changes.
This tests all the improvements we made to the webcam description system
for conversational AI integration.

Usage:
    python run_enhanced_room_tests.py [--verbose] [--specific TEST_NAME]
"""
import sys
import subprocess
import argparse
from pathlib import Path

def run_test_command(test_path, verbose=False):
    """Run a specific test with pytest."""
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    cmd.append(test_path)
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="Run enhanced room system tests")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Run tests in verbose mode")
    parser.add_argument("--specific", "-s", type=str,
                       help="Run specific test module")
    
    args = parser.parse_args()
    
    # Test modules for enhanced room system
    test_modules = [
        "tests/test_enhanced_room_system.py",
        "tests/test_ollama/test_enhanced_room_prompts.py",
        "tests/test_service/test_http_room_layout_integration.py",
        "tests/test_integration/test_room_layout_configuration.py",
        "tests/test_utils/test_room_photo_scripts.py"
    ]
    
    print("Enhanced Room System Test Runner")
    print("=" * 50)
    print()
    
    if args.specific:
        # Run specific test
        specific_test = args.specific
        if not specific_test.startswith("tests/"):
            specific_test = f"tests/{specific_test}"
        if not specific_test.endswith(".py"):
            specific_test = f"{specific_test}.py"
            
        print(f"Running specific test: {specific_test}")
        success = run_test_command(specific_test, args.verbose)
        
        if success:
            print(f"✅ {specific_test} PASSED")
        else:
            print(f"❌ {specific_test} FAILED")
            return 1
    else:
        # Run all tests
        print("Running all enhanced room system tests...")
        print()
        
        results = {}
        
        for test_module in test_modules:
            test_path = Path(test_module)
            
            if test_path.exists():
                print(f"Running {test_module}...")
                success = run_test_command(str(test_path), args.verbose)
                results[test_module] = success
                
                if success:
                    print(f"✅ {test_module} PASSED")
                else:
                    print(f"❌ {test_module} FAILED")
                print()
            else:
                print(f"⚠️  {test_module} not found, skipping...")
                results[test_module] = None
        
        # Summary
        print("Test Results Summary:")
        print("=" * 30)
        
        passed = 0
        failed = 0
        skipped = 0
        
        for test_module, result in results.items():
            if result is True:
                print(f"✅ {test_module}")
                passed += 1
            elif result is False:
                print(f"❌ {test_module}")
                failed += 1
            else:
                print(f"⚠️  {test_module} (skipped)")
                skipped += 1
        
        print()
        print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
        
        if failed > 0:
            print()
            print("Some tests failed. Please check the output above for details.")
            return 1
        elif passed == 0:
            print()
            print("No tests were run. Please check that test files exist.")
            return 1
        else:
            print()
            print("All tests passed! 🎉")
            return 0

if __name__ == "__main__":
    sys.exit(main()) 