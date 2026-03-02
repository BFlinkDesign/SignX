"""Command-line interface for the benchmark package.

Provides a CLI tool for running benchmarks and saving results to
various formats.
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .bench import analyze_results, measure_products


def save_to_json(data: Dict[str, Any], filepath: Path) -> None:
    """Save benchmark data to JSON format.

    Args:
        data: Dictionary containing benchmark results and metadata
        filepath: Path where to save the JSON file
    """
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"✅ Results saved to JSON: {filepath}")


def save_to_csv(
    results: Dict[str, float],
    filepath: Path,
    analysis: Optional[Dict[str, Any]] = None,
) -> None:
    """Save benchmark results to CSV format.

    Args:
        results: Dictionary of product names to execution times
        filepath: Path where to save the CSV file
        analysis: Optional analysis data to include
    """
    with open(filepath, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        # Write header
        writer.writerow(["Product", "Execution_Time_Seconds", "Rank"])

        # Sort by execution time for ranking
        sorted_results = sorted(results.items(), key=lambda x: x[1])

        # Write data rows
        for rank, (product, time) in enumerate(sorted_results, 1):
            writer.writerow([product, time, rank])

        # Add analysis as additional rows if provided
        if analysis:
            writer.writerow([])  # Empty row separator
            writer.writerow(["Analysis", "Value"])
            writer.writerow(
                ["Fastest_Product", analysis.get("fastest_product", "N/A")]
            )
            writer.writerow(
                ["Fastest_Time", analysis.get("fastest_time", "N/A")]
            )
            writer.writerow(
                ["Slowest_Product", analysis.get("slowest_product", "N/A")]
            )
            writer.writerow(
                ["Slowest_Time", analysis.get("slowest_time", "N/A")]
            )
            writer.writerow(
                ["Performance_Ratio", analysis.get("performance_ratio", "N/A")]
            )
            writer.writerow(
                ["Average_Time", analysis.get("average_time", "N/A")]
            )

    print(f"✅ Results saved to CSV: {filepath}")


def create_output_directory(base_dir: str = "benchmark_results") -> Path:
    """Create output directory for benchmark results.

    Args:
        base_dir: Base directory name for results

    Returns:
        Path object for the created directory
    """
    output_dir = Path(base_dir)
    output_dir.mkdir(exist_ok=True)
    return output_dir


def generate_filename(format_type: str, timestamp: bool = True) -> str:
    """Generate filename for benchmark results.

    Args:
        format_type: File format ('json' or 'csv')
        timestamp: Whether to include timestamp in filename

    Returns:
        Generated filename string
    """
    if timestamp:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"benchmark_results_{ts}.{format_type}"
    else:
        return f"benchmark_results.{format_type}"


def run_benchmark_cli(
    products: list,
    iterations: int,
    output_dir: str,
    save_json: bool,
    save_csv: bool,
    verbose: bool,
) -> None:
    """Run benchmark from CLI with specified parameters.

    Args:
        products: List of product names to benchmark
        iterations: Number of iterations per product
        output_dir: Directory to save results
        save_json: Whether to save JSON output
        save_csv: Whether to save CSV output
        verbose: Whether to print verbose output
    """
    if verbose:
        print(f"🚀 Starting benchmark with {len(products)} products")
        print(f"📊 Running {iterations} iterations per product")
        print(f"📁 Output directory: {output_dir}")

    # Run the benchmark
    print("⏱️  Running benchmark...")
    results = measure_products(products, iterations)

    # Analyze results
    analysis = analyze_results(results)

    # Display results to console
    print("\n📈 Benchmark Results:")
    print("-" * 50)
    for product, time in sorted(results.items(), key=lambda x: x[1]):
        print(f"{product:<20}: {time:.6f} seconds")

    if analysis and verbose:
        print("\n📊 Analysis:")
        print("-" * 50)
        print(
            f"🏆 Fastest: {analysis['fastest_product']} "
            f"({analysis['fastest_time']:.6f}s)"
        )
        print(
            f"🐌 Slowest: {analysis['slowest_product']} "
            f"({analysis['slowest_time']:.6f}s)"
        )
        print(f"📊 Ratio: {analysis['performance_ratio']:.2f}x")
        print(f"📈 Average: {analysis['average_time']:.6f}s")

    # Save results if requested
    if save_json or save_csv:
        output_path = create_output_directory(output_dir)

        # Prepare data for saving
        timestamp = datetime.now().isoformat()
        full_data = {
            "metadata": {
                "timestamp": timestamp,
                "products_count": len(products),
                "iterations_per_product": iterations,
                "total_measurements": len(products) * iterations,
            },
            "results": results,
            "analysis": analysis,
        }

        if save_json:
            json_file = output_path / generate_filename("json")
            save_to_json(full_data, json_file)

        if save_csv:
            csv_file = output_path / generate_filename("csv")
            save_to_csv(results, csv_file, analysis)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark products and save results to various formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic benchmark with default products
  %(prog)s

  # Custom products with more iterations
  %(prog)s -p ProductA ProductB ProductC -i 500

  # Save to both JSON and CSV with verbose output
  %(prog)s --json --csv --verbose

  # Custom output directory
  %(prog)s --output-dir ./my_results --json
        """,
    )

    parser.add_argument(
        "-p",
        "--products",
        nargs="+",
        default=["ProductA", "ProductB", "ProductC", "ProductD"],
        help=(
            "List of product names to benchmark "
            "(default: ProductA ProductB ProductC ProductD)"
        ),
    )

    parser.add_argument(
        "-i",
        "--iterations",
        type=int,
        default=100,
        help="Number of iterations per product (default: 100)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="benchmark_results",
        help="Output directory for results (default: benchmark_results)",
    )

    parser.add_argument(
        "--json", action="store_true", help="Save results to JSON format"
    )

    parser.add_argument(
        "--csv", action="store_true", help="Save results to CSV format"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--version", action="version", version="benchmark 1.0.0"
    )

    args = parser.parse_args()

    # Validation
    if args.iterations <= 0:
        print("❌ Error: iterations must be positive", file=sys.stderr)
        sys.exit(1)

    if not args.products:
        print(
            "❌ Error: at least one product must be specified", file=sys.stderr
        )
        sys.exit(1)

    # If no output format specified, default to console only
    if not args.json and not args.csv:
        if args.verbose:
            print(
                "ℹ️  No output format specified, "
                "showing results on console only"
            )

    try:
        run_benchmark_cli(
            products=args.products,
            iterations=args.iterations,
            output_dir=args.output_dir,
            save_json=args.json,
            save_csv=args.csv,
            verbose=args.verbose,
        )

        print("\n✨ Benchmark completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error during benchmark: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
