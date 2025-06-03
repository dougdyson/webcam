# Test-Driven Development Methodology

## Overview

This project follows strict TDD methodology with comprehensive test coverage and regression prevention.

## TDD Cycle

1. **RED**: Write failing test first
2. **GREEN**: Write minimal code to pass test  
3. **REFACTOR**: Clean up and optimize
4. **TRACK**: Update checkboxes after each cycle
5. **TEST ALL**: Run all tests at the end of every section to ensure no regressions

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
- **637 total tests** (100% pass rate)
- **File Organization**: Keep test files 200-300 lines for maintainability
- **Comprehensive Coverage**: All major functionality tested
- **Regression Prevention**: All tests must pass before commits

## Development Practices

### Environment Setup
- Always prepend `conda activate webcam && ` to terminal commands
- Use virtual environment isolation for all dependencies
- Ensure all processing remains local (no cloud dependencies)

### Code Quality
- Use Python 3.10+ features where appropriate
- Write clear, concise docstrings for all public functions, classes, and modules
- Use type hints extensively for function signatures, variables, and class members
- Format Python code according to PEP 8 guidelines
- Use f-strings for all string formatting

### Error Handling
- Implement robust error handling around camera access and frame processing
- Handle camera disconnection, permission issues, and hardware failures gracefully
- Test different lighting conditions and scenarios with sample images/videos

For detailed TDD plans for specific features, see `TDD_PLAN.md` and `TDD_OLLAMA_DESCRIPTION_PLAN.md`. 