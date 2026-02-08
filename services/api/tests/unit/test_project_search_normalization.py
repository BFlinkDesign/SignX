from datetime import UTC, datetime

from apex.api.db import Project
from apex.api.routes.projects import _coerce_search_record, _serialize_project_model


def _make_project(**overrides) -> Project:
    """Create a minimal ``Project`` instance for serialization tests."""

    now = datetime(2024, 1, 1, tzinfo=UTC)
    defaults = {
        "project_id": "proj-1",
        "account_id": "acct-1",
        "name": "Demo",
        "customer": "Acme",
        "description": None,
        "site_name": None,
        "street": None,
        "status": "draft",
        "created_by": "user",
        "updated_by": "user",
        "created_at": overrides.get("created_at", now),
        "updated_at": overrides.get("updated_at", now),
        "etag": None,
        "constants_version": None,
        "content_sha256": None,
        "confidence": None,
    }
    defaults.update(overrides)
    return Project(**defaults)


def test_serialize_project_model_matches_coerce_with_datetime():
    project = _make_project()
    serialized = _serialize_project_model(project)

    raw = {
        "project_id": project.project_id,
        "name": project.name,
        "status": project.status,
        "customer": project.customer,
        "created_at": project.created_at,
    }

    coerced = _coerce_search_record(raw)

    assert coerced == serialized


def test_coerce_handles_missing_optional_fields():
    raw = {"project_id": "proj-2", "name": "Missing", "status": "draft"}
    coerced = _coerce_search_record(raw)

    assert coerced["project_id"] == "proj-2"
    assert coerced["customer"] is None
    assert coerced["created_at"] is None


def test_coerce_preserves_iso_strings():
    iso_value = "2024-01-02T15:04:05+00:00"
    raw = {
        "project_id": "proj-3",
        "name": "ISO",
        "status": "draft",
        "customer": "Acme",
        "created_at": iso_value,
    }
    coerced = _coerce_search_record(raw)

    assert coerced["created_at"] == iso_value

