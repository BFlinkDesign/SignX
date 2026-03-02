# Contributing to Work Order Parser

Thank you for your interest in contributing to Work Order Parser! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the Issues section
2. Use the bug report template when creating a new issue
3. Include detailed steps to reproduce the bug
4. Include screenshots if applicable
5. Specify your environment (OS, Python version, etc.)

### Suggesting Features

1. Check if the feature has already been suggested
2. Use the feature request template
3. Provide a clear description of the feature
4. Explain why this feature would be useful
5. Include any relevant examples or mockups

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature/fix
3. Make your changes
4. Run tests and ensure they pass
5. Update documentation if necessary
6. Submit a pull request

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/EAGLE605/work-order-parser.git
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv311
   .venv311\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all functions and classes
- Keep functions small and focused
- Write unit tests for new features

## Testing

1. Run the test suite:
   ```bash
   pytest
   ```

2. Run linting:
   ```bash
   flake8
   ```

3. Run type checking:
   ```bash
   mypy .
   ```

## Documentation

- Update README.md if needed
- Add docstrings to new functions/classes
- Update HOW TO USE.txt for user-facing changes
- Comment complex code sections

## Release Process

1. Update version number
2. Update changelog
3. Create release notes
4. Tag the release
5. Build and test the release
6. Deploy the release

## Questions?

Feel free to open an issue for any questions about contributing. 