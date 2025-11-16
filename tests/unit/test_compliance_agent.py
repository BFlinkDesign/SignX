from __future__ import annotations

from contracts.compliance import ComplianceCheckRequest
from svcs.agent_compliance.main import check_ip_similarity, standards_tags, safety_checks, sign_checksum, load_patents


def test_ip_overlap_flag():
    patents = load_patents()
    flag, meta = check_ip_similarity("press fit shaft hub assembly tolerance analysis method", patents)
    assert isinstance(flag, bool)


def test_standards_tagging():
    tags = standards_tags("GD&T per ASME with datum references")
    assert "ASME Y14.5" in tags


def test_safety_missing_factor():
    flag, meta = safety_checks({"load": 1000}, {"result": 1})
    assert flag is True


def test_checksum_deterministic():
    c1 = sign_checksum({"a": 1, "b": 2})
    c2 = sign_checksum({"b": 2, "a": 1})
    assert c1 == c2


