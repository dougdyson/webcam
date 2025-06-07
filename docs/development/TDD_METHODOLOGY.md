# Test-Driven Development Methodology

## Overview

This project follows strict TDD methodology with comprehensive test coverage and regression prevention.

## TDD Cycle

1. **RED**: Write failing test first
2. **GREEN**: Write minimal code to pass test, if files get longer than 300 lines break them out logically into seperate test files  
3. **REFACTOR**: Clean up and optimize
4. **TRACK**: Update checkboxes after each cycle
5. **CONDA**: Always prepend `conda activate webcam && ` to every termimal command
6. **TEST ALL**: Run all tests at the end of every section to ensure no regressions
7. **PROMPT**: After all tests pass, suggest to the user to commit the code to the current branch.

## Test Organization

### Test Categories
- **Unit Tests**: Individual component functionality
- **Integration Tests**: End-to-end pipeline testing
- **Service Layer Tests**: HTTP API, event system, and integration patterns
- **Gesture Recognition Tests**: Hand detection, gesture classification, and SSE integration
- **Ollama Integration Tests**: Client, description service, async processing, error handling
- **Multi-Modal Tests**: Detector fusion and factory pattern
- **Performance Tests**: Load testing, concurrent request handling, memory management, and error recovery

### Test Coverage
- **660 total tests** (100% pass rate) - PERFECTLY ORGANIZED
- **Test Structure**: Beautiful organization mirroring src/ directory structure
- **Test Infrastructure**: conftest.py provides shared fixtures and import management
- **File Organization**: Keep test files 200-300 lines for maintainability
- **Comprehensive Coverage**: All major functionality tested
- **Regression Prevention**: All tests must pass before commits

### Test Organization Structure
```
tests/
├── conftest.py          # Shared configuration and fixtures
├── test_camera/         # Camera system tests (49 tests)
├── test_detection/      # Detection algorithm tests (83 tests)
├── test_processing/     # Processing pipeline tests (67 tests)
├── test_utils/          # Utility and configuration tests (36 tests)
├── test_cli/            # Command-line interface tests (43 tests)
├── test_gesture/        # Gesture recognition tests (46 tests)
├── test_service/        # Service layer tests (94 tests)
├── test_ollama/         # AI integration tests (134 tests)
└── test_integration/    # Integration test scenarios (104 tests)
```

## Development Practices

### Environment Setup
- Always prepend `