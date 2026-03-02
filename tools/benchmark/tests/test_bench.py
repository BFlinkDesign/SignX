"""Unit tests for the benchmarking module."""

import time

import pytest

from benchmark.bench import analyze_results, measure_products, measure_work


class TestMeasureWork:
    """Test cases for the measure_work function."""

    def test_measure_work_basic(self):
        """Test basic functionality of measure_work."""

        def quick_work():
            time.sleep(0.001)  # 1ms

        elapsed = measure_work(quick_work)
        assert elapsed >= 0.001  # Should be at least 1ms
        assert elapsed < 0.1  # Should be reasonable

    def test_measure_work_zero_time(self):
        """Test measure_work with minimal work."""

        def no_work():
            pass

        elapsed = measure_work(no_work)
        assert elapsed >= 0.0  # Time should be non-negative
        assert elapsed < 0.001  # Should be very fast

    def test_measure_work_with_computation(self):
        """Test measure_work with computational work."""

        def computational_work():
            _ = sum(i * i for i in range(1000))

        elapsed = measure_work(computational_work)
        assert elapsed >= 0.0
        assert isinstance(elapsed, float)


class TestMeasureProducts:
    """Test cases for the measure_products function."""

    def test_measure_products_basic(self):
        """Test basic functionality of measure_products."""
        products = ["ProductA", "ProductB"]
        results = measure_products(products, iterations=5)

        assert len(results) == 2
        assert "ProductA" in results
        assert "ProductB" in results
        assert all(time >= 0.0 for time in results.values())
        assert all(isinstance(time, float) for time in results.values())

    def test_measure_products_empty_list(self):
        """Test measure_products with empty product list."""
        results = measure_products([], iterations=10)
        assert results == {}

    def test_measure_products_single_product(self):
        """Test measure_products with single product."""
        products = ["SingleProduct"]
        results = measure_products(products, iterations=3)

        assert len(results) == 1
        assert "SingleProduct" in results
        assert results["SingleProduct"] >= 0.0

    def test_measure_products_zero_iterations(self):
        """Test measure_products with zero iterations."""
        products = ["ProductA"]

        # Zero iterations should result in mean of empty list error
        with pytest.raises(Exception):  # statistics.StatisticsError
            measure_products(products, iterations=0)

    def test_measure_products_many_iterations(self):
        """Test measure_products with many iterations for stability."""
        products = ["ProductA", "ProductB"]
        results = measure_products(products, iterations=50)

        assert len(results) == 2
        # With more iterations, results should be more stable
        assert all(time >= 0.0 for time in results.values())

    def test_measure_products_different_iteration_counts(self):
        """Test that different iteration counts affect precision."""
        products = ["ProductA"]

        # Test with different iteration counts
        results_few = measure_products(products, iterations=2)
        results_many = measure_products(products, iterations=20)

        assert len(results_few) == len(results_many) == 1
        # Both should give reasonable results
        assert results_few["ProductA"] >= 0.0
        assert results_many["ProductA"] >= 0.0


class TestAnalyzeResults:
    """Test cases for the analyze_results function."""

    def test_analyze_results_basic(self):
        """Test basic functionality of analyze_results."""
        results = {
            "FastProduct": 0.001,
            "SlowProduct": 0.003,
            "MediumProduct": 0.002,
        }

        analysis = analyze_results(results)

        assert analysis["fastest_product"] == "FastProduct"
        assert analysis["fastest_time"] == 0.001
        assert analysis["slowest_product"] == "SlowProduct"
        assert analysis["slowest_time"] == 0.003
        assert analysis["total_products"] == 3
        assert analysis["performance_ratio"] == 3.0  # 0.003 / 0.001

    def test_analyze_results_empty(self):
        """Test analyze_results with empty results."""
        analysis = analyze_results({})
        assert analysis == {}

    def test_analyze_results_single_product(self):
        """Test analyze_results with single product."""
        results = {"OnlyProduct": 0.005}
        analysis = analyze_results(results)

        assert analysis["fastest_product"] == "OnlyProduct"
        assert analysis["slowest_product"] == "OnlyProduct"
        assert analysis["fastest_time"] == 0.005
        assert analysis["slowest_time"] == 0.005
        assert analysis["performance_ratio"] == 1.0
        assert analysis["total_products"] == 1

    def test_analyze_results_zero_time(self):
        """Test analyze_results with zero minimum time."""
        results = {"ZeroProduct": 0.0, "NormalProduct": 0.002}

        analysis = analyze_results(results)

        assert analysis["fastest_product"] == "ZeroProduct"
        assert analysis["fastest_time"] == 0.0
        assert analysis["performance_ratio"] == float("inf")

    def test_analyze_results_identical_times(self):
        """Test analyze_results when all products have identical times."""
        results = {"Product1": 0.002, "Product2": 0.002, "Product3": 0.002}

        analysis = analyze_results(results)

        assert analysis["fastest_time"] == 0.002
        assert analysis["slowest_time"] == 0.002
        assert analysis["performance_ratio"] == 1.0
        assert analysis["average_time"] == 0.002
        assert analysis["total_products"] == 3


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_workflow(self):
        """Test the complete benchmarking workflow."""
        # Step 1: Define products
        products = ["ProductA", "ProductB", "ProductC"]

        # Step 2: Run benchmark
        results = measure_products(products, iterations=10)

        # Step 3: Analyze results
        analysis = analyze_results(results)

        # Verify results
        assert len(results) == 3
        assert all(product in results for product in products)
        assert all(time >= 0.0 for time in results.values())

        # Verify analysis
        assert analysis["total_products"] == 3
        assert analysis["fastest_product"] in products
        assert analysis["slowest_product"] in products
        assert analysis["performance_ratio"] >= 1.0
        assert analysis["average_time"] >= 0.0

    def test_measure_work_consistency(self):
        """Test that measure_work gives consistent results for similar work."""

        def consistent_work():
            _ = sum(range(100))

        # Measure multiple times
        times = [measure_work(consistent_work) for _ in range(5)]

        # All should be reasonable and similar
        assert all(time >= 0.0 for time in times)
        assert max(times) / min(times) < 10  # Not too variable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
