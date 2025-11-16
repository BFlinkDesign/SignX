"""Integration tests for CAD export API endpoints."""

import pytest
from fastapi.testclient import TestClient
from apex.api.main import app


client = TestClient(app)


class TestCADExportFoundation:
    """Test suite for foundation plan CAD export endpoint."""

    def test_export_foundation_dxf_basic(self):
        """Test basic DXF export with minimal parameters."""
        request = {
            "foundation_type": "direct_burial",
            "diameter_ft": 3.0,
            "depth_ft": 6.0,
            "fc_ksi": 3.0,
            "fy_ksi": 60.0,
            "cover_in": 3.0,
            "format": "dxf",
            "scale": "1/4\"=1'-0\"",
            "project_name": "Test Project",
            "drawing_number": "FND-001",
        }

        response = client.post("/api/cad/export/foundation", json=request)

        assert response.status_code == 200, f"Response: {response.json()}"

        data = response.json()

        # Verify envelope structure
        assert data["ok"] is True
        assert "result" in data
        assert "trace" in data
        assert "assumptions" in data
        assert "confidence" in data

        # Verify result content
        result = data["result"]
        assert result["filename"].endswith(".dxf")
        assert result["format"] == "dxf"
        assert result["file_size_bytes"] > 0
        assert result["num_entities"] > 0
        assert len(result["layers"]) > 0

        # Verify artifacts in trace
        assert "artifacts" in data["trace"]["data"]
        artifacts = data["trace"]["data"]["artifacts"]
        assert len(artifacts) == 1
        assert artifacts[0]["type"] == "cad_drawing"
        assert artifacts[0]["format"] == "dxf"
        assert len(artifacts[0]["base64_data"]) > 0

    def test_export_foundation_with_anchor_bolts(self):
        """Test DXF export with anchor bolt layout."""
        request = {
            "foundation_type": "pier_and_grade_beam",
            "diameter_ft": 4.0,
            "depth_ft": 8.0,
            "fc_ksi": 4.0,
            "fy_ksi": 60.0,
            "cover_in": 3.0,
            "anchor_layout": {
                "num_bolts": 8,
                "bolt_diameter_in": 1.0,
                "bolt_circle_diameter_ft": 2.5,
                "projection_in": 12.0,
                "embedment_in": 18.0,
            },
            "format": "dxf",
            "scale": "1/2\"=1'-0\"",
            "project_name": "Anchor Bolt Test",
            "drawing_number": "FND-002",
            "engineer": "John Doe, P.E.",
        }

        response = client.post("/api/cad/export/foundation", json=request)

        assert response.status_code == 200

        data = response.json()
        result = data["result"]

        # Should have more entities with anchor bolts
        assert result["num_entities"] > 50  # Plan + section + rebar + anchors

        # Check assumptions mention anchor bolts
        assumptions = data["assumptions"]
        anchor_assumption = [a for a in assumptions if "Anchor bolts" in a]
        assert len(anchor_assumption) > 0

    def test_export_foundation_different_scales(self):
        """Test export with different drawing scales."""
        scales = ["1/4\"=1'-0\"", "1/2\"=1'-0\"", "1\"=1'-0\"", "3\"=1'-0\""]

        for scale in scales:
            request = {
                "foundation_type": "direct_burial",
                "diameter_ft": 3.0,
                "depth_ft": 6.0,
                "format": "dxf",
                "scale": scale,
            }

            response = client.post("/api/cad/export/foundation", json=request)

            assert response.status_code == 200, f"Failed for scale: {scale}"

            data = response.json()
            assumptions = data["assumptions"]

            # Verify scale is mentioned in assumptions
            scale_assumption = [a for a in assumptions if scale in a]
            assert len(scale_assumption) > 0, f"Scale {scale} not in assumptions"

    def test_export_foundation_invalid_type(self):
        """Test validation error for invalid foundation type."""
        request = {
            "foundation_type": "invalid_type",
            "diameter_ft": 3.0,
            "depth_ft": 6.0,
        }

        response = client.post("/api/cad/export/foundation", json=request)

        assert response.status_code == 400
        assert "Invalid foundation type" in response.json()["detail"]

    def test_export_foundation_invalid_diameter(self):
        """Test validation error for invalid diameter."""
        request = {
            "foundation_type": "direct_burial",
            "diameter_ft": -1.0,  # Negative diameter
            "depth_ft": 6.0,
        }

        response = client.post("/api/cad/export/foundation", json=request)

        assert response.status_code == 422  # Pydantic validation error

    def test_export_foundation_dwg_format(self):
        """Test DWG format export (placeholder)."""
        request = {
            "foundation_type": "direct_burial",
            "diameter_ft": 3.0,
            "depth_ft": 6.0,
            "format": "dwg",
        }

        response = client.post("/api/cad/export/foundation", json=request)

        # DWG is a placeholder, should still return success
        assert response.status_code == 200

        data = response.json()
        result = data["result"]
        assert result["format"] == "dwg"

    def test_download_foundation_dxf(self):
        """Test direct download endpoint (no envelope)."""
        request = {
            "foundation_type": "direct_burial",
            "diameter_ft": 3.0,
            "depth_ft": 6.0,
            "format": "dxf",
        }

        response = client.post("/api/cad/download/foundation", json=request)

        assert response.status_code == 200

        # Should be binary DXF content, not JSON
        assert response.headers["content-type"] == "application/dxf"
        assert "attachment" in response.headers["content-disposition"]
        assert ".dxf" in response.headers["content-disposition"]

        # Should have custom headers
        assert "x-file-size" in response.headers
        assert "x-cad-format" in response.headers
        assert response.headers["x-cad-format"] == "DXF"

        # Content should be binary
        assert len(response.content) > 0

    def test_determinism_multiple_calls(self):
        """Test that identical requests produce identical results."""
        request = {
            "foundation_type": "direct_burial",
            "diameter_ft": 3.5,
            "depth_ft": 7.0,
            "fc_ksi": 3.5,
            "format": "dxf",
            "scale": "1/4\"=1'-0\"",
        }

        # Call endpoint twice
        response1 = client.post("/api/cad/export/foundation", json=request)
        response2 = client.post("/api/cad/export/foundation", json=request)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Results should be identical (deterministic)
        assert data1["result"]["file_size_bytes"] == data2["result"]["file_size_bytes"]
        assert data1["result"]["num_entities"] == data2["result"]["num_entities"]
        assert data1["result"]["layers"] == data2["result"]["layers"]

    def test_confidence_score_with_warnings(self):
        """Test that confidence score adjusts when warnings are present."""
        # Note: Current implementation may not generate warnings easily
        # This is a placeholder test for when warning logic is added
        request = {
            "foundation_type": "direct_burial",
            "diameter_ft": 3.0,
            "depth_ft": 6.0,
        }

        response = client.post("/api/cad/export/foundation", json=request)

        assert response.status_code == 200

        data = response.json()

        # Should have high confidence (no warnings expected)
        assert data["confidence"] >= 0.95


class TestCADExportValidation:
    """Test validation and error handling."""

    def test_missing_required_fields(self):
        """Test validation error for missing required fields."""
        request = {
            "foundation_type": "direct_burial",
            # Missing diameter_ft and depth_ft
        }

        response = client.post("/api/cad/export/foundation", json=request)

        assert response.status_code == 422  # Pydantic validation error

    def test_anchor_bolt_validation(self):
        """Test validation for anchor bolt parameters."""
        request = {
            "foundation_type": "direct_burial",
            "diameter_ft": 3.0,
            "depth_ft": 6.0,
            "anchor_layout": {
                "num_bolts": 3,  # Too few bolts (min 4)
                "bolt_diameter_in": 1.0,
                "bolt_circle_diameter_ft": 2.5,
                "projection_in": 12.0,
                "embedment_in": 18.0,
            },
        }

        response = client.post("/api/cad/export/foundation", json=request)

        assert response.status_code == 422  # Pydantic validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
