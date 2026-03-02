"""Unit tests for the CLI module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from benchmark.cli import (
    create_output_directory,
    generate_filename,
    main,
    run_benchmark_cli,
    save_to_csv,
    save_to_json,
)


class TestOutputHelpers:
    """Test cases for output helper functions."""

    def test_create_output_directory(self):
        """Test creating output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "test_output"
            result_path = create_output_directory(str(base_path))

            assert result_path.exists()
            assert result_path.is_dir()
            assert result_path.name == "test_output"

    def test_generate_filename_with_timestamp(self):
        """Test filename generation with timestamp."""
        filename = generate_filename("json", timestamp=True)

        assert filename.startswith("benchmark_results_")
        assert filename.endswith(".json")
        assert len(filename) > 20  # Should have timestamp

    def test_generate_filename_without_timestamp(self):
        """Test filename generation without timestamp."""
        filename = generate_filename("csv", timestamp=False)

        assert filename == "benchmark_results.csv"

    def test_save_to_json(self):
        """Test saving data to JSON format."""
        test_data = {
            "results": {"ProductA": 0.001, "ProductB": 0.002},
            "metadata": {"timestamp": "2024-01-01T00:00:00"},
        }

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            save_to_json(test_data, tmp_path)

            # Verify file was created and contains correct data
            assert tmp_path.exists()
            with open(tmp_path) as f:
                loaded_data = json.load(f)

            assert loaded_data == test_data
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_save_to_csv_basic(self):
        """Test saving results to CSV format."""
        results = {"ProductA": 0.001, "ProductB": 0.002}

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            save_to_csv(results, tmp_path)

            # Verify file was created
            assert tmp_path.exists()

            # Read and verify content
            content = tmp_path.read_text()
            lines = content.strip().split("\n")

            assert len(lines) >= 3  # Header + 2 data rows
            assert "Product,Execution_Time_Seconds,Rank" in lines[0]
            assert "ProductA" in content
            assert "ProductB" in content
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_save_to_csv_with_analysis(self):
        """Test saving results to CSV with analysis data."""
        results = {"ProductA": 0.001, "ProductB": 0.002}
        analysis = {
            "fastest_product": "ProductA",
            "fastest_time": 0.001,
            "slowest_product": "ProductB",
            "slowest_time": 0.002,
            "performance_ratio": 2.0,
            "average_time": 0.0015,
        }

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            save_to_csv(results, tmp_path, analysis)

            content = tmp_path.read_text()

            # Check that analysis data is included
            assert "Analysis,Value" in content
            assert "Fastest_Product,ProductA" in content
            assert "Performance_Ratio,2.0" in content
        finally:
            tmp_path.unlink(missing_ok=True)


class TestRunBenchmarkCli:
    """Test cases for the main CLI function."""

    def test_run_benchmark_cli_basic(self, capsys):
        """Test basic CLI benchmark execution."""
        products = ["TestProduct1", "TestProduct2"]

        with tempfile.TemporaryDirectory() as tmpdir:
            run_benchmark_cli(
                products=products,
                iterations=5,
                output_dir=tmpdir,
                save_json=False,
                save_csv=False,
                verbose=False,
            )

        captured = capsys.readouterr()
        assert "Running benchmark..." in captured.out
        assert "Benchmark Results:" in captured.out
        assert "TestProduct1" in captured.out
        assert "TestProduct2" in captured.out

    def test_run_benchmark_cli_verbose(self, capsys):
        """Test CLI with verbose output."""
        products = ["TestProduct"]

        with tempfile.TemporaryDirectory() as tmpdir:
            run_benchmark_cli(
                products=products,
                iterations=3,
                output_dir=tmpdir,
                save_json=False,
                save_csv=False,
                verbose=True,
            )

        captured = capsys.readouterr()
        assert "Starting benchmark with" in captured.out
        assert "Running 3 iterations" in captured.out
        assert "Analysis:" in captured.out

    def test_run_benchmark_cli_save_json(self):
        """Test CLI with JSON output."""
        products = ["TestProduct"]

        with tempfile.TemporaryDirectory() as tmpdir:
            run_benchmark_cli(
                products=products,
                iterations=2,
                output_dir=tmpdir,
                save_json=True,
                save_csv=False,
                verbose=False,
            )

            # Check that JSON file was created
            output_dir = Path(tmpdir)
            json_files = list(output_dir.glob("*.json"))
            assert len(json_files) == 1

            # Verify JSON content
            with open(json_files[0]) as f:
                data = json.load(f)

            assert "metadata" in data
            assert "results" in data
            assert "analysis" in data
            assert "TestProduct" in data["results"]

    def test_run_benchmark_cli_save_csv(self):
        """Test CLI with CSV output."""
        products = ["TestProduct"]

        with tempfile.TemporaryDirectory() as tmpdir:
            run_benchmark_cli(
                products=products,
                iterations=2,
                output_dir=tmpdir,
                save_json=False,
                save_csv=True,
                verbose=False,
            )

            # Check that CSV file was created
            output_dir = Path(tmpdir)
            csv_files = list(output_dir.glob("*.csv"))
            assert len(csv_files) == 1

            # Verify CSV content
            content = csv_files[0].read_text()
            assert "Product,Execution_Time_Seconds,Rank" in content
            assert "TestProduct" in content


class TestCliMain:
    """Test cases for the main CLI entry point."""

    def test_main_help(self):
        """Test CLI help output."""
        with patch("sys.argv", ["benchmark-cli", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Help should exit with code 0
            assert exc_info.value.code == 0

    def test_main_version(self):
        """Test CLI version output."""
        with patch("sys.argv", ["benchmark-cli", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Version should exit with code 0
            assert exc_info.value.code == 0

    def test_main_invalid_iterations(self, capsys):
        """Test CLI with invalid iteration count."""
        with patch("sys.argv", ["benchmark-cli", "-i", "0"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with error code
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "iterations must be positive" in captured.err

    def test_main_empty_products(self, capsys):
        """Test CLI with empty products list."""
        with patch("sys.argv", ["benchmark-cli", "-p"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Should exit with error code due to argument parsing
            assert exc_info.value.code == 2

    def test_main_keyboard_interrupt(self):
        """Test CLI handling of keyboard interrupt."""
        with patch("sys.argv", ["benchmark-cli", "-i", "1000"]):
            with patch(
                "benchmark.cli.run_benchmark_cli",
                side_effect=KeyboardInterrupt,
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 130

    def test_main_exception_handling(self, capsys):
        """Test CLI handling of general exceptions."""
        with patch("sys.argv", ["benchmark-cli", "-i", "5"]):
            with patch(
                "benchmark.cli.run_benchmark_cli",
                side_effect=RuntimeError("Test error"),
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error during benchmark: Test error" in captured.err

    def test_main_exception_handling_verbose(self, capsys):
        """Test CLI exception handling with verbose output."""
        with patch("sys.argv", ["benchmark-cli", "-i", "5", "--verbose"]):
            with patch(
                "benchmark.cli.run_benchmark_cli",
                side_effect=RuntimeError("Test error"),
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error during benchmark: Test error" in captured.err

    def test_main_basic_run(self):
        """Test basic CLI execution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "sys.argv",
                [
                    "benchmark-cli",
                    "-p",
                    "TestProd1",
                    "TestProd2",
                    "-i",
                    "3",
                    "--output-dir",
                    tmpdir,
                ],
            ):
                try:
                    main()
                except SystemExit as e:
                    # Should complete successfully
                    assert e.code in (0, None)

    def test_main_with_json_output(self):
        """Test CLI with JSON output option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "sys.argv",
                [
                    "benchmark-cli",
                    "-p",
                    "TestProduct",
                    "-i",
                    "2",
                    "--output-dir",
                    tmpdir,
                    "--json",
                ],
            ):
                try:
                    main()
                except SystemExit as e:
                    assert e.code in (0, None)

                # Verify JSON file was created
                output_files = list(Path(tmpdir).glob("*.json"))
                assert len(output_files) == 1

    def test_main_no_output_format_message(self, capsys):
        """Test CLI message when no output format specified with verbose."""
        with patch("sys.argv", ["benchmark-cli", "-i", "2", "--verbose"]):
            try:
                main()
            except SystemExit:
                pass

        captured = capsys.readouterr()
        assert "showing results on console only" in captured.out
