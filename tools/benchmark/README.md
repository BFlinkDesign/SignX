# Benchmark

[![CI Pipeline](https://github.com/EAGLE605/benchmark/workflows/CI%20Pipeline/badge.svg)](https://github.com/EAGLE605/benchmark/actions)
[![codecov](https://codecov.io/gh/EAGLE605/benchmark/branch/main/graph/badge.svg)](https://codecov.io/gh/EAGLE605/benchmark)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A modern, well-tested Python benchmarking tool for measuring and comparing product performance with comprehensive analysis and reporting capabilities.

## Features

- 🚀 **Clean, Typed API**: Modern Python with type hints and clear interfaces
- 📊 **Statistical Analysis**: Comprehensive performance analysis with ratios and insights
- 🧪 **Well Tested**: 80%+ test coverage with comprehensive unit tests
- 🔍 **Code Quality**: Automated linting, formatting, and type checking
- 📈 **Multiple Output Formats**: Save results to JSON, CSV, or console
- 🖥️ **CLI Interface**: Easy-to-use command-line tool
- ⚡ **CI/CD Ready**: GitHub Actions workflow for automated testing
- 📋 **Audit Script**: One-command code quality validation

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/EAGLE605/benchmark.git
cd benchmark

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Basic Usage

#### As a Python Module

```python
from benchmark.bench import measure_products, analyze_results

# Benchmark multiple products
results = measure_products(['ProductA', 'ProductB', 'ProductC'], iterations=100)
print(results)
# {'ProductA': 0.001234, 'ProductB': 0.001456, 'ProductC': 0.001123}

# Analyze the results
analysis = analyze_results(results)
print(f"Fastest: {analysis['fastest_product']} ({analysis['fastest_time']:.6f}s)")
print(f"Performance ratio: {analysis['performance_ratio']:.2f}x")
```

#### Using the CLI

```bash
# Basic benchmark with default products
python -m benchmark.cli

# Custom products with more iterations
python -m benchmark.cli -p ProductA ProductB ProductC -i 500

# Save results to files with verbose output
python -m benchmark.cli --json --csv --verbose

# Custom output directory
python -m benchmark.cli --output-dir ./my_results --json
```

#### CLI Options

```
usage: python -m benchmark.cli [-h] [-p PRODUCTS [PRODUCTS ...]] [-i ITERATIONS]
                               [--output-dir OUTPUT_DIR] [--json] [--csv] [-v] [--version]

options:
  -h, --help            show this help message and exit
  -p, --products        List of product names to benchmark
  -i, --iterations      Number of iterations per product (default: 100)
  --output-dir          Output directory for results (default: benchmark_results)
  --json               Save results to JSON format
  --csv                Save results to CSV format
  -v, --verbose        Enable verbose output
  --version            show program's version number and exit
```

## API Reference

### Core Functions

#### `measure_work(work: Callable[[], None]) -> float`

Measure the execution time of a single work function.

**Parameters:**
- `work`: A callable that takes no arguments and returns None

**Returns:**
- Elapsed time in seconds as a float

**Example:**
```python
def my_work():
    time.sleep(0.001)

elapsed = measure_work(my_work)
```

#### `measure_products(products: Iterable[str], iterations: int = 1000) -> Dict[str, float]`

Benchmark multiple products with statistical analysis.

**Parameters:**
- `products`: An iterable of product identifiers to benchmark
- `iterations`: Number of iterations to run for each product (default: 1000)

**Returns:**
- Dictionary mapping product names to average execution times

#### `analyze_results(results: Dict[str, float]) -> Dict[str, Any]`

Analyze benchmark results and provide insights.

**Parameters:**
- `results`: Dictionary of product names to execution times

**Returns:**
- Dictionary with analysis including fastest, slowest, ratios, and statistics

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=benchmark --cov-report=term-missing

# Run specific test file
pytest tests/test_bench.py -v
```

### Code Quality

```bash
# Run the audit script (linting + testing)
python scripts/audit.py

# Run with additional checks
python scripts/audit.py --with-mypy --with-coverage

# Individual tools
flake8 benchmark/ tests/ scripts/
mypy benchmark/
black benchmark/ tests/ scripts/
isort benchmark/ tests/ scripts/
```

### Project Structure

```
benchmark/
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI pipeline
├── benchmark/                  # Main package
│   ├── __init__.py            # Package initialization
│   ├── bench.py               # Core benchmarking functions
│   ├── bench_old.py           # Legacy code (reference)
│   └── cli.py                 # Command-line interface
├── tests/
│   ├── __init__.py
│   └── test_bench.py          # Comprehensive unit tests
├── scripts/
│   └── audit.py               # Code quality audit script
├── pyproject.toml             # Project configuration
├── requirements.txt           # Dependencies
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## Code Quality Standards

This project maintains high code quality standards:

- **Linting**: flake8 for style checking
- **Formatting**: black for consistent code formatting  
- **Import Sorting**: isort for organized imports
- **Type Checking**: mypy for static type analysis
- **Testing**: pytest with 80%+ coverage requirement
- **Security**: bandit and safety for security scanning

## Continuous Integration

The project uses GitHub Actions for CI/CD with the following checks:

- ✅ **Multi-Python Testing**: Tests against Python 3.8-3.12
- ✅ **Code Quality**: Linting, formatting, and type checking
- ✅ **Test Coverage**: Minimum 80% coverage requirement
- ✅ **Security Scanning**: Automated security vulnerability checks
- ✅ **Functional Testing**: CLI and module integration tests

## Legacy Code

The project includes `benchmark/bench_old.py` as a reference implementation showing the "before" state. This demonstrates:

- Poor variable naming and code organization
- Lack of type hints and documentation
- Hardcoded values and inflexible design
- Missing error handling and edge cases

Compare this with the modern implementation in `benchmark/bench.py` to see the improvements.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the audit script: `python scripts/audit.py`
5. Ensure all tests pass and code quality checks succeed
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Changelog

### v1.0.0 (2024)
- Initial release with modern benchmarking capabilities
- Comprehensive test suite with 80%+ coverage
- CLI interface with multiple output formats
- GitHub Actions CI/CD pipeline
- Code quality automation with audit script
- Full documentation and examples
