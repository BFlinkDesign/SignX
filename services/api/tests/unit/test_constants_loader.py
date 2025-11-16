"""Unit tests for constants pack loading."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from apex.api.common.constants import load_constants_packs, get_constants, get_pack_metadata, get_constants_version_string, ConstantsPack


class TestConstantsLoader:
    """Test constants pack loading and versioning."""
    
    def test_load_yaml_pack(self, tmp_path):
        """Load YAML pack and compute SHA256."""
        # Create test YAML pack
        pack_file = tmp_path / "test_pack_v1.yaml"
        pack_data = {
            "version": "v1",
            "constants": {
                "k_factor": 0.15,
                "soil_bearing": 3000.0,
            }
        }
        with pack_file.open("w") as f:
            yaml.dump(pack_data, f)
        
        # Load pack
        packs = load_constants_packs(tmp_path)
        
        assert "test_pack" in packs
        pack = packs["test_pack"]
        assert pack.name == "test_pack"
        assert pack.version == "v1"
        assert pack.sha256 is not None
        assert len(pack.sha256) == 64  # SHA256 hex length
    
    def test_version_string_format(self, tmp_path):
        """Version string formatted correctly."""
        # Create multiple packs
        for name in ["pricing", "exposure"]:
            pack_file = tmp_path / f"{name}_v1.yaml"
            with pack_file.open("w") as f:
                yaml.dump({"version": "v1"}, f)
        
        # Load and format version string
        load_constants_packs(tmp_path)
        version_str = get_constants_version_string()
        
        assert "pricing:v1:" in version_str
        assert "exposure:v1:" in version_str
        assert version_str.count(",") == 1  # Two packs, one comma
    
    def test_get_pack_metadata(self, tmp_path):
        """Get metadata for loaded packs."""
        # Create pack with source reference
        pack_file = tmp_path / "asce_v1.yaml"
        pack_data = {
            "version": "v1",
            "source": "ASCE 7-16 Table 26.10-1",
            "constants": {"kz": 0.85}
        }
        with pack_file.open("w") as f:
            yaml.dump(pack_data, f)
        
        # Load and get metadata
        load_constants_packs(tmp_path)
        metadata = get_pack_metadata()
        
        assert "asce" in metadata
        assert metadata["asce"]["version"] == "v1"
        assert metadata["asce"]["sha256"] is not None
        assert "ASCE 7-16" in metadata["asce"]["refs"]
    
    def test_get_constants(self, tmp_path):
        """Get specific constants pack by name."""
        # Create pack
        pack_file = tmp_path / "pricing_v2.yaml"
        pack_data = {"version": "v2", "rates": {"base": 200}}
        with pack_file.open("w") as f:
            yaml.dump(pack_data, f)
        
        # Load and fetch
        load_constants_packs(tmp_path)
        constants = get_constants("pricing")
        
        assert constants is not None
        assert constants["version"] == "v2"
        assert constants["rates"]["base"] == 200
    
    def test_missing_pack_returns_none(self):
        """Missing pack returns None gracefully."""
        result = get_constants("nonexistent_pack")
        assert result is None
    
    def test_parse_version_from_filename(self, tmp_path):
        """Version parsed correctly from filename."""
        # Test v1
        pack_file = tmp_path / "test_v1.yaml"
        with pack_file.open("w") as f:
            yaml.dump({}, f)
        packs = load_constants_packs(tmp_path)
        assert packs["test"].version == "v1"
        
        # Test v2
        pack_file = tmp_path / "test_v2.yaml"
        with pack_file.open("w") as f:
            yaml.dump({}, f)
        packs = load_constants_packs(tmp_path)
        assert packs["test"].version == "v2"
    
    def test_sha256_deterministic(self, tmp_path):
        """Same file produces same SHA256."""
        pack_file = tmp_path / "stable_v1.yaml"
        pack_data = {"version": "v1", "value": 42}
        
        # Write twice
        with pack_file.open("w") as f:
            yaml.dump(pack_data, f)
        
        with pack_file.open("rb") as f:
            first_sha = load_constants_packs(tmp_path)["stable"].sha256
        
        # Reload should produce same SHA
        second_sha = load_constants_packs(tmp_path)["stable"].sha256
        
        assert first_sha == second_sha
    
    def test_handles_missing_dir_gracefully(self):
        """Missing constants directory handled gracefully."""
        result = load_constants_packs(Path("/nonexistent/dir"))
        assert result == {}


class TestConstantsPack:
    """Test ConstantsPack class directly."""
    
    def test_constructor(self):
        """ConstantsPack created correctly."""
        pack = ConstantsPack(
            name="test",
            version="v1",
            sha256="abc123" * 10,  # 60 chars
            data={"key": "value"}
        )
        assert pack.name == "test"
        assert pack.version == "v1"
        assert pack.sha256 == "abc123" * 10
        assert pack.data == {"key": "value"}
    
    def test_repr(self):
        """String representation shows truncated SHA."""
        pack = ConstantsPack("test", "v1", "abc123" * 10, {})
        repr_str = str(pack)
        assert "test" in repr_str
        assert "v1" in repr_str
        assert len(repr_str) < 100  # Truncated

