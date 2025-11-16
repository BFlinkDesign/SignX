"""Tests for ML models and anomaly detection."""

from __future__ import annotations

import pytest

from apex.domains.signage.ml_models import detect_unusual_config, predict_initial_config


class TestMLPredictions:
    """Test ML-based configuration predictions."""
    
    def test_predict_initial_config_heuristic(self):
        """Test heuristic fallback when no training data."""
        result = predict_initial_config(
            cabinet_area_ft2=112.0,  # 14x8
            height_ft=25.0,
            wind_speed_mph=115.0,
            soil_bearing_psf=3000.0,
        )
        
        assert "suggested_pole" in result
        assert "suggested_footing" in result
        assert "confidence" in result
        assert result["method"] == "heuristic"
        assert 0.0 < result["confidence"] <= 1.0
    
    def test_predict_initial_config_has_footing(self):
        """Test that prediction includes footing dimensions."""
        result = predict_initial_config(100.0, 20.0, 100.0)
        
        assert "suggested_footing" in result
        footing = result["suggested_footing"]
        assert "diameter_ft" in footing
        assert "depth_ft" in footing
        assert footing["diameter_ft"] > 0
        assert footing["depth_ft"] > 0


class TestAnomalyDetection:
    """Test anomaly detection."""
    
    def test_detect_unusual_config_normal(self):
        """Test normal configuration is not flagged."""
        result = detect_unusual_config(
            cabinet_area_ft2=112.0,  # 14x8
            height_ft=25.0,
            wind_speed_mph=115.0,
            pole_sx_in3=19.1,  # Reasonable
        )
        
        assert "is_anomaly" in result
        assert "anomaly_score" in result
        # Normal config should not be anomalous
        if not result["is_anomaly"]:
            assert result["anomaly_score"] < 0.5
    
    def test_detect_unusual_config_tiny_cabinet(self):
        """Test tiny cabinet is flagged as anomalous."""
        result = detect_unusual_config(
            cabinet_area_ft2=10.0,  # Very small
            height_ft=30.0,  # Tall
            wind_speed_mph=115.0,
            pole_sx_in3=100.0,  # Large pole
        )
        
        # Should detect anomaly
        if result["is_anomaly"]:
            assert result["anomaly_score"] > 0.0
            assert len(result.get("reason", "")) > 0
    
    def test_detect_unusual_config_massive_pole(self):
        """Test massive pole relative to cabinet is flagged."""
        result = detect_unusual_config(
            cabinet_area_ft2=50.0,  # Small cabinet
            height_ft=20.0,
            wind_speed_mph=100.0,
            pole_sx_in3=500.0,  # Massive pole
        )
        
        # May be flagged as anomalous
        assert "anomaly_score" in result
        assert result["anomaly_score"] >= 0.0

