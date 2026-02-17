"""Smoke tests for the SIGNX agent framework (FSQueue-based agents).

Each test verifies:
  - The module imports cleanly
  - Required entry points (process_file / main / INBOX_DIR) exist
  - Envelope format from validate_and_wrap produces expected keys
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Dict

import pytest

# Ensure repo root is on sys.path so svcs.* and contracts.* resolve.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import(dotted: str) -> ModuleType:
    """Import a dotted module path, returning the module object."""
    return importlib.import_module(dotted)


ENVELOPE_REQUIRED_KEYS = {"result", "trace", "provenance", "data_sha256", "schema_version"}


def _assert_envelope(env: Dict[str, Any]) -> None:
    """Verify an envelope produced by validate_and_wrap has the expected top-level keys."""
    missing = ENVELOPE_REQUIRED_KEYS - set(env.keys())
    assert not missing, f"Envelope missing keys: {missing}"
    assert isinstance(env["result"], dict), "envelope['result'] must be a dict"
    assert isinstance(env["trace"], dict), "envelope['trace'] must be a dict"
    assert isinstance(env["provenance"], dict), "envelope['provenance'] must be a dict"
    assert isinstance(env["data_sha256"], str) and len(env["data_sha256"]) == 64, (
        "envelope['data_sha256'] must be a 64-char hex string"
    )


# ---------------------------------------------------------------------------
# agent_cad
# ---------------------------------------------------------------------------

class TestAgentCad:
    def test_import(self):
        mod = _import("svcs.agent_cad.main")
        assert mod is not None

    def test_has_process_file(self):
        mod = _import("svcs.agent_cad.main")
        assert callable(getattr(mod, "process_file", None)), "agent_cad must expose process_file()"

    def test_has_main(self):
        mod = _import("svcs.agent_cad.main")
        assert callable(getattr(mod, "main", None)), "agent_cad must expose main()"

    def test_queue_name_in_main_source(self):
        """Verify the queue sub-directory is 'cad' (checked via source)."""
        mod = _import("svcs.agent_cad.main")
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert '"cad"' in src or "'cad'" in src or "/ \"cad\"" in src or '/ "cad"' in src or "queue/cad" in src.replace("\\", "/"), (
            "Expected 'cad' queue path reference in agent_cad/main.py"
        )


# ---------------------------------------------------------------------------
# agent_compliance
# ---------------------------------------------------------------------------

class TestAgentCompliance:
    def test_import(self):
        mod = _import("svcs.agent_compliance.main")
        assert mod is not None

    def test_has_process_file(self):
        mod = _import("svcs.agent_compliance.main")
        assert callable(getattr(mod, "process_file", None))

    def test_has_main(self):
        mod = _import("svcs.agent_compliance.main")
        assert callable(getattr(mod, "main", None))

    def test_uses_fsqueue(self):
        from svcs.common.fsqueue import FSQueue
        mod = _import("svcs.agent_compliance.main")
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "FSQueue" in src


# ---------------------------------------------------------------------------
# agent_dfma
# ---------------------------------------------------------------------------

class TestAgentDfma:
    def test_import(self):
        mod = _import("svcs.agent_dfma.main")
        assert mod is not None

    def test_has_process_file(self):
        mod = _import("svcs.agent_dfma.main")
        assert callable(getattr(mod, "process_file", None))

    def test_has_main(self):
        mod = _import("svcs.agent_dfma.main")
        assert callable(getattr(mod, "main", None))

    def test_evaluate_function_exists(self):
        mod = _import("svcs.agent_dfma.main")
        assert callable(getattr(mod, "evaluate", None)), "agent_dfma must expose evaluate()"

    def test_evaluate_sheet_metal_violation(self):
        """Deterministic: r_over_t < 1.0 → min_bend_radius_violation."""
        from contracts.dfma import DFMAEvaluateRequest
        mod = _import("svcs.agent_dfma.main")
        req = DFMAEvaluateRequest(
            task_id="smoke-dfma-1",
            description="test bracket",
            process="sheet_metal",
            params={"r_over_t": 0.5, "hole_edge_multiple": 2.0, "quantity": 10},
        )
        violations, suggestions, cost, score = mod.evaluate(req)
        assert "min_bend_radius_violation" in violations
        assert any("bend radius" in s.lower() for s in suggestions)


# ---------------------------------------------------------------------------
# agent_eval
# ---------------------------------------------------------------------------

class TestAgentEval:
    def test_import(self):
        """INBOX_DIR must be defined and import must succeed."""
        mod = _import("svcs.agent_eval.main")
        assert mod is not None

    def test_has_inbox_dir(self):
        mod = _import("svcs.agent_eval.main")
        assert hasattr(mod, "INBOX_DIR"), "agent_eval must define INBOX_DIR"
        assert isinstance(mod.INBOX_DIR, Path)

    def test_inbox_dir_path(self):
        mod = _import("svcs.agent_eval.main")
        # Should be queue/eval/inbox
        parts = mod.INBOX_DIR.parts
        assert "eval" in parts, f"Expected 'eval' in INBOX_DIR path: {mod.INBOX_DIR}"
        assert "inbox" in parts, f"Expected 'inbox' in INBOX_DIR path: {mod.INBOX_DIR}"

    def test_has_main(self):
        mod = _import("svcs.agent_eval.main")
        assert callable(getattr(mod, "main", None))

    def test_has_process_one_envelope(self):
        mod = _import("svcs.agent_eval.main")
        assert callable(getattr(mod, "process_one_envelope", None)), (
            "agent_eval must expose process_one_envelope()"
        )

    def test_has_drop_payload(self):
        mod = _import("svcs.agent_eval.main")
        assert callable(getattr(mod, "drop_payload", None))


# ---------------------------------------------------------------------------
# agent_materials
# ---------------------------------------------------------------------------

class TestAgentMaterials:
    def test_import(self):
        mod = _import("svcs.agent_materials.main")
        assert mod is not None

    def test_has_process_file(self):
        mod = _import("svcs.agent_materials.main")
        assert callable(getattr(mod, "process_file", None))

    def test_has_main(self):
        mod = _import("svcs.agent_materials.main")
        assert callable(getattr(mod, "main", None))

    def test_has_status_path(self):
        mod = _import("svcs.agent_materials.main")
        assert hasattr(mod, "STATUS_PATH"), "agent_materials must define STATUS_PATH"

    def test_load_candidates_fallback(self):
        """Fallback dataset must return at least 1 candidate when no CSV present."""
        mod = _import("svcs.agent_materials.main")
        candidates = mod.load_candidates()
        assert len(candidates) >= 1
        assert all(hasattr(c, "name") for c in candidates)
        assert all(hasattr(c, "yield_mpa") for c in candidates)


# ---------------------------------------------------------------------------
# agent_parts
# ---------------------------------------------------------------------------

class TestAgentParts:
    def test_import(self):
        mod = _import("svcs.agent_parts.main")
        assert mod is not None

    def test_has_process_file(self):
        mod = _import("svcs.agent_parts.main")
        assert callable(getattr(mod, "process_file", None))

    def test_has_main(self):
        mod = _import("svcs.agent_parts.main")
        assert callable(getattr(mod, "main", None))

    def test_load_catalogs_fallback(self):
        """Fallback catalog must return at least 1 row."""
        mod = _import("svcs.agent_parts.main")
        rows = mod.load_catalogs()
        assert len(rows) >= 1


# ---------------------------------------------------------------------------
# agent_signs
# ---------------------------------------------------------------------------

class TestAgentSigns:
    def test_import(self):
        mod = _import("svcs.agent_signs.main")
        assert mod is not None

    def test_has_process_file(self):
        mod = _import("svcs.agent_signs.main")
        assert callable(getattr(mod, "process_file", None))

    def test_has_main(self):
        mod = _import("svcs.agent_signs.main")
        assert callable(getattr(mod, "main", None))

    def test_queue_name_signs(self):
        mod = _import("svcs.agent_signs.main")
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "signs" in src, "Expected 'signs' queue reference in agent_signs/main.py"


# ---------------------------------------------------------------------------
# agent_stackup
# ---------------------------------------------------------------------------

class TestAgentStackup:
    def test_import(self):
        mod = _import("svcs.agent_stackup.main")
        assert mod is not None

    def test_has_process_file(self):
        mod = _import("svcs.agent_stackup.main")
        assert callable(getattr(mod, "process_file", None))

    def test_has_main(self):
        mod = _import("svcs.agent_stackup.main")
        assert callable(getattr(mod, "main", None))

    def test_cp_cpk_function(self):
        mod = _import("svcs.agent_stackup.main")
        assert callable(getattr(mod, "cp_cpk", None)), "agent_stackup must expose cp_cpk()"

    def test_cp_cpk_symmetric(self):
        """Deterministic: symmetric spec → cp == cpk (on-center)."""
        mod = _import("svcs.agent_stackup.main")
        cp, cpk = mod.cp_cpk(mean=15.0, sigma=1.0, lower=12.0, upper=18.0)
        assert cp is not None and cpk is not None
        assert abs(cp - 1.0) < 1e-9, f"Expected cp=1.0, got {cp}"
        assert abs(cpk - 1.0) < 1e-9, f"Expected cpk=1.0, got {cpk}"

    def test_has_status_path(self):
        mod = _import("svcs.agent_stackup.main")
        assert hasattr(mod, "STATUS_PATH")


# ---------------------------------------------------------------------------
# agent_translator
# ---------------------------------------------------------------------------

class TestAgentTranslator:
    def test_import(self):
        mod = _import("svcs.agent_translator.main")
        assert mod is not None

    def test_has_main(self):
        mod = _import("svcs.agent_translator.main")
        assert callable(getattr(mod, "main", None))

    def test_sha_helper(self):
        mod = _import("svcs.agent_translator.main")
        assert callable(getattr(mod, "_sha", None)), "agent_translator must expose _sha()"
        result = mod._sha("hello")
        assert isinstance(result, str) and len(result) == 64

    def test_scan_contracts_callable(self):
        mod = _import("svcs.agent_translator.main")
        assert callable(getattr(mod, "_scan_contracts", None))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def test_import(self):
        mod = _import("svcs.orchestrator.main")
        assert mod is not None

    def test_has_main(self):
        mod = _import("svcs.orchestrator.main")
        assert callable(getattr(mod, "main", None))

    def test_has_enqueue_demo_tasks(self):
        mod = _import("svcs.orchestrator.main")
        assert callable(getattr(mod, "enqueue_demo_tasks", None)), (
            "orchestrator must expose enqueue_demo_tasks()"
        )

    def test_has_export_json_schemas(self):
        mod = _import("svcs.orchestrator.main")
        assert callable(getattr(mod, "export_json_schemas", None)), (
            "orchestrator must expose export_json_schemas()"
        )

    def test_has_synthesize_report(self):
        mod = _import("svcs.orchestrator.main")
        assert callable(getattr(mod, "synthesize_report", None)), (
            "orchestrator must expose synthesize_report()"
        )

    def test_exit_codes_defined(self):
        mod = _import("svcs.orchestrator.main")
        assert hasattr(mod, "EXIT_OK") and mod.EXIT_OK == 0
        assert hasattr(mod, "EXIT_INTEGRITY") and mod.EXIT_INTEGRITY == 2
        assert hasattr(mod, "EXIT_COMPLETENESS") and mod.EXIT_COMPLETENESS == 3
        assert hasattr(mod, "EXIT_ORDERING") and mod.EXIT_ORDERING == 4

    def test_queue_dir_defined(self):
        mod = _import("svcs.orchestrator.main")
        assert hasattr(mod, "QUEUE_DIR")
        assert isinstance(mod.QUEUE_DIR, Path)

    def test_envelope_dataclass(self):
        mod = _import("svcs.orchestrator.main")
        Envelope = mod.Envelope
        env = Envelope(task_id="t1", agent="test", type="request", payload={"x": 1})
        assert env.task_id == "t1"
        assert env.agent == "test"
        assert env.payload == {"x": 1}


# ---------------------------------------------------------------------------
# validate_and_wrap envelope contract
# ---------------------------------------------------------------------------

class TestEnvelopeContract:
    """Verify the envelope produced by validate_and_wrap meets the expected schema."""

    def test_envelope_keys_from_materials_agent(self):
        """Run a full materials process_file flow with a minimal temp inbox file."""
        import json
        import tempfile
        from pathlib import Path

        mod = _import("svcs.agent_materials.main")

        payload = {
            "task_id": "smoke-mat-env-1",
            "application": "outdoor bracket",
            "key_requirements": ["corrosion"],
            "min_yield_mpa": 200.0,
            "weights": {"cost": 0.3, "strength": 0.5, "corrosion": 0.2},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            inbox = root / "queue" / "materials" / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            task_file = inbox / "smoke-mat-env-1.json"
            task_file.write_text(json.dumps(payload), encoding="utf-8")

            # process_file(root, path) — should produce output under runs/
            mod.process_file(root, task_file)

            # Locate output envelope
            out_dir = root / "runs" / "smoke-mat-env-1" / "out"
            out_files = list(out_dir.glob("*.json"))
            assert out_files, f"No output file found under {out_dir}"
            envelope = json.loads(out_files[0].read_text(encoding="utf-8"))
            _assert_envelope(envelope)

    def test_envelope_keys_from_stackup_agent(self):
        """Run stackup process_file to verify envelope format."""
        import json
        import tempfile
        from pathlib import Path

        mod = _import("svcs.agent_stackup.main")

        payload = {
            "task_id": "smoke-stk-env-1",
            "description": "test stack",
            "features": [
                {"name": "a", "nominal": 10.0, "tol_plus": 0.1, "tol_minus": 0.1, "distribution": "normal"},
                {"name": "b", "nominal": 5.0, "tol_plus": 0.05, "tol_minus": 0.05, "distribution": "normal"},
            ],
            "sample_size": 1000,
            "lower_spec": 14.5,
            "upper_spec": 15.5,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            inbox = root / "queue" / "stackup" / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            task_file = inbox / "smoke-stk-env-1.json"
            task_file.write_text(json.dumps(payload), encoding="utf-8")

            mod.process_file(root, task_file)

            out_dir = root / "runs" / "smoke-stk-env-1" / "out"
            out_files = list(out_dir.glob("*.json"))
            assert out_files, f"No output file found under {out_dir}"
            envelope = json.loads(out_files[0].read_text(encoding="utf-8"))
            _assert_envelope(envelope)


# ---------------------------------------------------------------------------
# FSQueue smoke
# ---------------------------------------------------------------------------

class TestFSQueue:
    def test_import(self):
        from svcs.common.fsqueue import FSQueue
        assert FSQueue is not None

    def test_init_creates_dirs(self, tmp_path):
        from svcs.common.fsqueue import FSQueue
        q = FSQueue(
            tmp_path / "inbox",
            tmp_path / "wip",
            tmp_path / "out",
        )
        assert (tmp_path / "inbox").is_dir()
        assert (tmp_path / "wip").is_dir()
        assert (tmp_path / "out").is_dir()

    def test_poll_empty(self, tmp_path):
        from svcs.common.fsqueue import FSQueue
        q = FSQueue(tmp_path / "inbox", tmp_path / "wip", tmp_path / "out")
        assert list(q.poll()) == []

    def test_poll_finds_json(self, tmp_path):
        import json
        from svcs.common.fsqueue import FSQueue
        inbox = tmp_path / "inbox"
        q = FSQueue(inbox, tmp_path / "wip", tmp_path / "out")
        (inbox / "task1.json").write_text(json.dumps({"task_id": "t1"}))
        results = list(q.poll())
        assert len(results) == 1
        assert results[0].name == "task1.json"
