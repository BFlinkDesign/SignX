"""Unit tests for envelope utilities and confidence scoring."""

from __future__ import annotations

from apex.api.common.envelope import (
    calc_confidence,
    envelope_sha,
    extract_solver_warnings,
    round_floats,
)
from apex.api.schemas import (
    CodeVersionModel,
    ModelConfigModel,
    ResponseEnvelope,
    TraceDataModel,
    TraceModel,
)


class TestRoundFloats:
    """Test deterministic rounding of float values."""
    
    def test_simple_float(self):
        """Round single float to 3 decimal places."""
        result = round_floats(3.141592653589793)
        assert result == 3.142
    
    def test_float_in_dict(self):
        """Round floats in dictionary."""
        result = round_floats({"value": 3.14159, "count": 42})
        assert result == {"value": 3.142, "count": 42}
    
    def test_float_in_list(self):
        """Round floats in list."""
        result = round_floats([3.14159, 2.71828, 1.41421])
        assert result == [3.142, 2.718, 1.414]
    
    def test_nested_structure(self):
        """Round floats in nested dict/list structure."""
        data = {
            "items": [
                {"price": 19.99999, "quantity": 2},
                {"price": 29.49999, "quantity": 1},
            ]
        }
        result = round_floats(data)
        assert result == {
            "items": [
                {"price": 20.0, "quantity": 2},
                {"price": 29.5, "quantity": 1},
            ]
        }
    
    def test_custom_precision(self):
        """Round with custom precision."""
        result = round_floats(3.14159, precision=2)
        assert result == 3.14
    
    def test_non_float_unchanged(self):
        """Non-float values unchanged."""
        result = round_floats({"text": "hello", "number": 42})
        assert result == {"text": "hello", "number": 42}


class TestEnvelopeSha:
    """Test deterministic SHA256 computation."""
    
    def test_deterministic_sha(self):
        """Same inputs produce same SHA256."""
        trace = TraceModel(
            data=TraceDataModel(),
            code_version=CodeVersionModel(git_sha="abc123", dirty=False),
            model_config=ModelConfigModel(provider="test", model="test", temperature=0.0, max_tokens=100),
        )
        
        result = {"value": 3.142}
        envelope1 = ResponseEnvelope(result=result, assumptions=[], confidence=0.95, trace=trace)
        envelope2 = ResponseEnvelope(result=result, assumptions=[], confidence=0.95, trace=trace)
        
        sha1 = envelope_sha(envelope1)
        sha2 = envelope_sha(envelope2)
        
        assert sha1 == sha2
        assert len(sha1) == 64  # SHA256 hex length
    
    def test_different_inputs_different_sha(self):
        """Different inputs produce different SHA256."""
        trace = TraceModel(
            data=TraceDataModel(),
            code_version=CodeVersionModel(git_sha="abc123", dirty=False),
            model_config=ModelConfigModel(provider="test", model="test", temperature=0.0, max_tokens=100),
        )
        
        envelope1 = ResponseEnvelope(result={"value": 1.0}, assumptions=[], confidence=0.95, trace=trace)
        envelope2 = ResponseEnvelope(result={"value": 2.0}, assumptions=[], confidence=0.95, trace=trace)
        
        sha1 = envelope_sha(envelope1)
        sha2 = envelope_sha(envelope2)
        
        assert sha1 != sha2
    
    def test_dict_input(self):
        """Works with dict input instead of ResponseEnvelope."""
        payload = {"result": {"value": 3.142}}
        sha = envelope_sha(payload)
        
        assert sha is not None
        assert len(sha) == 64


class TestCalcConfidence:
    """Test confidence scoring from assumptions."""
    
    def test_no_assumptions(self):
        """No assumptions → maximum confidence."""
        confidence = calc_confidence(None)
        assert confidence == 1.0
    
    def test_empty_assumptions(self):
        """Empty assumptions → maximum confidence."""
        confidence = calc_confidence([])
        assert confidence == 1.0
    
    def test_single_warning(self):
        """Single warning → -0.1."""
        confidence = calc_confidence(["Warning: test"])
        assert confidence == 0.9
    
    def test_multiple_warnings(self):
        """Multiple warnings → cumulative -0.1 each."""
        confidence = calc_confidence(["Warning: a", "Warning: b", "Warning: c"])
        assert confidence == 0.7  # 1.0 - 0.3
    
    def test_fail_assumption(self):
        """Fail keyword → -0.3."""
        confidence = calc_confidence(["Check failed"])
        assert confidence == 0.7
    
    def test_abstain_assumption(self):
        """Abstain keyword → -0.5."""
        confidence = calc_confidence(["Cannot solve"])
        assert confidence == 0.5
    
    def test_no_feasible(self):
        """No feasible keyword → -0.4."""
        confidence = calc_confidence(["No feasible solutions"])
        assert confidence == 0.6
    
    def test_engineering_required(self):
        """Engineering review required → -0.3."""
        confidence = calc_confidence(["Engineering review required"])
        assert confidence == 0.7
    
    def test_mixed_assumptions(self):
        """Mixed assumptions apply all penalties."""
        confidence = calc_confidence([
            "Warning: minor issue",
            "Major check failed",
            "Engineering review required",
        ])
        assert confidence == 0.5  # 1.0 - 0.1 - 0.3 - 0.3
    
    def test_clamped_to_zero(self):
        """Confidence clamped to minimum 0.0."""
        confidence = calc_confidence([
            "Abstain",
            "Cannot solve",
            "Abstain",
            "Cannot solve",
        ])
        assert confidence == 0.0  # Would be -1.0, clamped to 0.0
    
    def test_case_insensitive(self):
        """Keywords match case-insensitively."""
        confidence1 = calc_confidence(["WARNING: test"])
        confidence2 = calc_confidence(["warning: test"])
        assert confidence1 == confidence2


class TestExtractSolverWarnings:
    """Test extraction of warnings from solver results."""
    
    def test_tuple_result_with_warnings(self):
        """Extract warnings from (result, warnings) tuple."""
        result = ({"value": 42}, ["Warning: test"])
        warnings = extract_solver_warnings(result)
        assert warnings == ["Warning: test"]
    
    def test_tuple_result_with_flags(self):
        """Extract from (result, warnings, flags) tuple."""
        result = (
            {"value": 42},
            ["Warning: a"],
            {"all_pass": False}
        )
        warnings = extract_solver_warnings(result)
        assert "Warning: a" in warnings
        assert "all_pass check failed" in warnings
    
    def test_dict_with_warnings_key(self):
        """Extract from dict with 'warnings' key."""
        result = {"value": 42, "warnings": ["Warning: test"]}
        warnings = extract_solver_warnings(result)
        assert warnings == ["Warning: test"]
    
    def test_dict_with_request_engineering_flag(self):
        """Extract from dict with request_engineering flag."""
        result = {"value": 42, "request_engineering": True}
        warnings = extract_solver_warnings(result)
        assert "Engineering review required" in warnings
    
    def test_dict_with_all_pass_false(self):
        """Extract from dict with all_pass=False."""
        result = {"value": 42, "all_pass": False}
        warnings = extract_solver_warnings(result)
        assert "Some checks failed" in warnings
    
    def test_empty_result(self):
        """Empty result → empty warnings."""
        warnings = extract_solver_warnings(None)
        assert warnings == []
    
    def test_non_tuple_non_dict(self):
        """Non-tuple, non-dict result → empty warnings."""
        warnings = extract_solver_warnings("string result")
        assert warnings == []
    
    def test_tuple_without_warnings(self):
        """Tuple without warnings → empty list."""
        result = ({"value": 42},)
        warnings = extract_solver_warnings(result)
        assert warnings == []


class TestEnvelopeIntegration:
    """Integration tests for envelope creation."""
    
    def test_make_envelope_with_confidence(self):
        """make_envelope uses calc_confidence for scoring."""
        from apex.api.common.models import make_envelope
        
        result1 = make_envelope(result={"test": True}, assumptions=[])
        assert result1.confidence == 1.0
        
        result2 = make_envelope(result={"test": True}, assumptions=["Warning: test"])
        assert result2.confidence == 0.9
    
    def test_make_envelope_with_content_sha(self):
        """make_envelope computes content_sha256."""
        from apex.api.common.models import make_envelope
        
        result = make_envelope(result={"value": 3.142})
        assert result.content_sha256 is not None
        assert len(result.content_sha256) == 64

