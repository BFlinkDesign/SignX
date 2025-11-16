"""Tests for batch processing."""

from __future__ import annotations

import time

import pytest

from apex.domains.signage.batch import ProjectConfig, solve_batch
from apex.domains.signage.models import Cabinet, SiteLoads


class TestBatchProcessing:
    """Test batch processing."""
    
    def test_solve_batch_single(self):
        """Test batch with single project."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        config = ProjectConfig(
            project_id="test1",
            site=site,
            cabinets=[{"width_ft": 14.0, "height_ft": 8.0, "weight_psf": 10.0}],
            height_ft=25.0,
        )
        
        results = solve_batch([config])
        
        assert len(results) == 1
        assert results[0]["project_id"] == "test1"
        assert results[0]["error"] is None
        assert results[0]["result"] is not None
    
    def test_solve_batch_multiple(self):
        """Test batch with multiple projects."""
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        configs = [
            ProjectConfig(
                project_id=f"test{i}",
                site=site,
                cabinets=[{"width_ft": 10.0 + i, "height_ft": 6.0, "weight_psf": 10.0}],
                height_ft=20.0,
            )
            for i in range(5)
        ]
        
        results = solve_batch(configs)
        
        assert len(results) == 5
        assert all(r["error"] is None for r in results)
        assert all(r["result"] is not None for r in results)
    
    def test_solve_batch_performance(self):
        """Test that batch processes 100 projects in <10s."""
        site = SiteLoads(wind_speed_mph=100.0, exposure="C")
        configs = [
            ProjectConfig(
                project_id=f"perf{i}",
                site=site,
                cabinets=[{"width_ft": 10.0, "height_ft": 6.0, "weight_psf": 10.0}],
                height_ft=20.0,
            )
            for i in range(100)
        ]
        
        start = time.perf_counter()
        results = solve_batch(configs, n_workers=4)
        elapsed = time.perf_counter() - start
        
        assert elapsed < 10.0  # Target: <10s for 100 projects
        assert len(results) == 100
        assert all(r["error"] is None for r in results)
    
    def test_solve_batch_progress_callback(self):
        """Test progress callback."""
        callback_calls = []
        
        def progress_cb(total, completed, failed):
            callback_calls.append((total, completed, failed))
        
        site = SiteLoads(wind_speed_mph=115.0, exposure="C")
        configs = [
            ProjectConfig(
                project_id=f"cb{i}",
                site=site,
                cabinets=[{"width_ft": 10.0, "height_ft": 6.0, "weight_psf": 10.0}],
                height_ft=20.0,
            )
            for i in range(20)
        ]
        
        solve_batch(configs, progress_callback=progress_cb, n_workers=2)
        
        assert len(callback_calls) > 0
        # Should be called multiple times during processing
        assert any(completed > 0 for _, completed, _ in callback_calls)

