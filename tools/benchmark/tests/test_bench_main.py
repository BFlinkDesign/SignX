"""Tests for main execution functions in bench.py."""

from benchmark.bench import main


class TestBenchMain:
    """Test cases for the main function in bench.py."""

    def test_main_execution(self, capsys):
        """Test main function execution."""
        main()

        captured = capsys.readouterr()
        assert "Running modern benchmark..." in captured.out
        assert "Benchmarking" in captured.out
        assert "ProductA" in captured.out
        assert "ProductB" in captured.out
        assert "ProductC" in captured.out
        assert "ProductD" in captured.out
        assert "Analysis:" in captured.out
        assert "Fastest:" in captured.out
        assert "Slowest:" in captured.out

    def test_main_output_format(self, capsys):
        """Test main function output formatting."""
        main()

        captured = capsys.readouterr()
        output_lines = captured.out.split("\n")

        # Check for proper formatting
        benchmark_results_found = False
        analysis_found = False

        for line in output_lines:
            if "Benchmark Results:" in line:
                benchmark_results_found = True
            if "Analysis:" in line:
                analysis_found = True

        assert benchmark_results_found
        assert analysis_found

    def test_main_with_mock_products(self):
        """Test main function behavior is consistent."""
        # Run main twice and verify it doesn't crash
        main()
        main()  # Should work consistently

        # No exception should be raised
