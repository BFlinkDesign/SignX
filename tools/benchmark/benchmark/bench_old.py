"""Legacy benchmarking code - kept for reference.

This is the original messy implementation that needs refactoring.
"""

import random
import time


def old_benchmark_function(products_list, num_iterations):
    """Old messy benchmark function with poor design."""
    results = {}

    # Poor variable naming and logic
    for p in products_list:
        total_time = 0
        for i in range(num_iterations):
            start = time.time()
            # Simulate some work - this is not realistic
            time.sleep(random.uniform(0.0001, 0.0005))  # Random sleep
            # More simulated work
            _ = sum(range(100))  # Use underscore for unused result
            end = time.time()
            total_time += end - start

        # Store average time
        results[p] = total_time / num_iterations

    return results


def run_benchmark():
    """Run the old benchmark with hardcoded values."""
    products = ["ProductA", "ProductB", "ProductC"]
    iterations = 100

    print("Running legacy benchmark...")
    results = old_benchmark_function(products, iterations)

    print("Results:")
    for product, avg_time in results.items():
        print(f"{product}: {avg_time:.6f} seconds")


if __name__ == "__main__":
    run_benchmark()
