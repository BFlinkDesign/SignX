"""Modern benchmarking module with clean API and proper typing.

This module provides functions for measuring execution time of work functions
and benchmarking multiple products with statistical analysis.
"""

import time
from statistics import mean
from typing import Any, Callable, Dict, Iterable


def measure_work(work: Callable[[], None]) -> float:
    """Measure the execution time of a single work function.

    Args:
        work: A callable that takes no arguments and returns None.

    Returns:
        Elapsed time in seconds as a float.

    Example:
        >>> def my_work():
        ...     time.sleep(0.001)
        >>> elapsed = measure_work(my_work)
        >>> elapsed >= 0.001
        True
    """
    start_time = time.perf_counter()
    work()
    end_time = time.perf_counter()
    return end_time - start_time


def measure_products(
    products: Iterable[str], iterations: int = 1000
) -> Dict[str, float]:
    """Benchmark multiple products with statistical analysis.

    Args:
        products: An iterable of product identifiers to benchmark.
        iterations: Number of iterations to run for each product.

    Returns:
        Dictionary mapping product names to average execution times.

    Example:
        >>> products = ['ProductA', 'ProductB']
        >>> results = measure_products(products, iterations=10)
        >>> all(time >= 0.0 for time in results.values())
        True
    """
    results = {}

    for product in products:
        times = []

        def product_work():
            """Simulate realistic product work."""
            # Simulate some computational work
            _ = sum(i * i for i in range(50))
            # Small sleep to simulate I/O or network operations
            time.sleep(0.0001)

        for _ in range(iterations):
            elapsed = measure_work(product_work)
            times.append(elapsed)

        # Calculate statistics
        avg_time = mean(times)
        results[product] = avg_time

    return results


def analyze_results(results: Dict[str, float]) -> Dict[str, Any]:
    """Analyze benchmark results and provide insights.

    Args:
        results: Dictionary of product names to execution times.

    Returns:
        Dictionary with analysis including fastest, slowest, and ratios.
    """
    if not results:
        return {}

    times = list(results.values())
    products = list(results.keys())

    min_time = min(times)
    max_time = max(times)
    avg_time = mean(times)

    fastest_product = products[times.index(min_time)]
    slowest_product = products[times.index(max_time)]

    analysis = {
        "fastest_product": fastest_product,
        "fastest_time": min_time,
        "slowest_product": slowest_product,
        "slowest_time": max_time,
        "average_time": avg_time,
        "performance_ratio": (
            max_time / min_time if min_time > 0 else float("inf")
        ),
        "total_products": len(results),
    }

    return analysis


def main():
    """Main runner for demonstrating the benchmarking functionality."""
    print("Running modern benchmark...")

    # Default products to benchmark
    products = ["ProductA", "ProductB", "ProductC", "ProductD"]
    iterations = 100

    print(
        f"Benchmarking {len(products)} products "
        f"with {iterations} iterations each..."
    )

    # Run benchmark
    results = measure_products(products, iterations)

    # Display results
    print("\nBenchmark Results:")
    print("-" * 40)
    for product, avg_time in sorted(results.items()):
        print(f"{product:<12}: {avg_time:.6f} seconds")

    # Analyze results
    analysis = analyze_results(results)
    if analysis:
        print("\nAnalysis:")
        print("-" * 40)
        print(
            f"Fastest: {analysis['fastest_product']} "
            f"({analysis['fastest_time']:.6f}s)"
        )
        print(
            f"Slowest: {analysis['slowest_product']} "
            f"({analysis['slowest_time']:.6f}s)"
        )
        print(f"Performance ratio: {analysis['performance_ratio']:.2f}x")
        print(f"Average time: {analysis['average_time']:.6f}s")


if __name__ == "__main__":
    main()
