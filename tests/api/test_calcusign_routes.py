"""Smoke tests for CalcuSign route endpoints."""

import pytest


def test_routes_import():
    """Verify all route modules import without errors."""
    try:
        from apex.api.routes import projects, site, cabinets, poles, direct_burial, baseplate, pricing, submission
    except ImportError as e:
        pytest.fail(f"Failed to import routes: {e}")


def test_common_models_import():
    """Verify common models import."""
    try:
        from apex.api.common.models import SiteLoads, Cabinet, Unit, Exposure, MaterialSteel
    except ImportError as e:
        pytest.fail(f"Failed to import common models: {e}")


def test_project_models_import():
    """Verify project models import."""
    try:
        from apex.api.projects.models import ProjectMeta, ProjectPayload, ProjectEvent
    except ImportError as e:
        pytest.fail(f"Failed to import project models: {e}")


def test_schemas_helpers():
    """Verify envelope helpers work."""
    from apex.api.schemas import compute_confidence_from_margins, add_assumption

    margins = [1.5, 2.0, 1.8]
    conf = compute_confidence_from_margins(margins)
    assert 0.0 <= conf <= 1.0
    
    assumptions: list[str] = []
    add_assumption(assumptions, "Test")
    assert len(assumptions) == 1

