from __future__ import annotations

import json
import os
import subprocess
from statistics import median
from typing import Any, Dict, List, Mapping

from fastapi import FastAPI, HTTPException, Response
import logging

logger = logging.getLogger(__name__)

# Import local models and scorers with fallbacks to path-based import
try:
    from .models import (
        MaterialPickRequest,
        MaterialPickResponse,
        RankedMaterial as ApiRankedMaterial,
        Contribution,
        Trace,
        export_json_schema,
        SCHEMA_VERSION,
    )  # type: ignore
    from .score.weighted import compute_weighted_numeric_score, normalize_property_values  # type: ignore
    from .score.qualitative import compute_qualitative_score, DEFAULT_QUALITATIVE_SCALE  # type: ignore
except Exception:  # noqa: BLE001 - import shim for direct file loading in tests
    import importlib.util
    import sys

    _BASE_DIR = os.path.dirname(__file__)
    _SCORE_DIR = os.path.join(_BASE_DIR, "score")
    if _SCORE_DIR not in sys.path:
        sys.path.insert(0, _SCORE_DIR)
    _MODELS_PATH = os.path.join(_BASE_DIR, "models.py")
    models_spec = importlib.util.spec_from_file_location("materials_models", _MODELS_PATH)
    if models_spec and models_spec.loader:
        models_mod = importlib.util.module_from_spec(models_spec)
        models_spec.loader.exec_module(models_mod)  # type: ignore[attr-defined]
        MaterialPickRequest = models_mod.MaterialPickRequest  # type: ignore[attr-defined]
        MaterialPickResponse = models_mod.MaterialPickResponse  # type: ignore[attr-defined]
        ApiRankedMaterial = models_mod.RankedMaterial  # type: ignore[attr-defined]
        Contribution = models_mod.Contribution  # type: ignore[attr-defined]
        Trace = models_mod.Trace  # type: ignore[attr-defined]
        export_json_schema = models_mod.export_json_schema  # type: ignore[attr-defined]
        SCHEMA_VERSION = models_mod.SCHEMA_VERSION  # type: ignore[attr-defined]
    weighted_spec = importlib.util.spec_from_file_location(
        "weighted", os.path.join(_SCORE_DIR, "weighted.py")
    )
    if weighted_spec and weighted_spec.loader:
        weighted = importlib.util.module_from_spec(weighted_spec)
        weighted_spec.loader.exec_module(weighted)
        compute_weighted_numeric_score = weighted.compute_weighted_numeric_score  # type: ignore[attr-defined]
        normalize_property_values = weighted.normalize_property_values  # type: ignore[attr-defined]
    qualitative_spec = importlib.util.spec_from_file_location(
        "qualitative", os.path.join(_SCORE_DIR, "qualitative.py")
    )
    if qualitative_spec and qualitative_spec.loader:
        qualitative = importlib.util.module_from_spec(qualitative_spec)
        qualitative_spec.loader.exec_module(qualitative)
        compute_qualitative_score = qualitative.compute_qualitative_score  # type: ignore[attr-defined]
        DEFAULT_QUALITATIVE_SCALE = qualitative.DEFAULT_QUALITATIVE_SCALE  # type: ignore[attr-defined]


app = FastAPI(title="APEX Materials Service", version="0.1.0")


def _git_metadata() -> Dict[str, Any]:
    def _run(cmd: list[str]) -> str:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            return out.decode().strip()
        except Exception as e:
            logger.warning("Exception in main.py: %s", str(e))
            return "unknown"

    sha = _run(["git", "rev-parse", "--short", "HEAD"]) or "unknown"
    dirty_out = _run(["git", "status", "--porcelain"]) or ""
    dirty = bool(dirty_out and dirty_out != "unknown")
    return {"git_sha": sha, "dirty": dirty, "build_id": None}


def _make_reasoning(ranked: List[ApiRankedMaterial], low_contrib_features: List[str]) -> str:
    top = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else top
    top_feats = sorted(top.contributions, key=lambda c: c.contribution, reverse=True)[:3]
    keys = ", ".join([f"{c.name}={c.contribution:.1f}" for c in top_feats]) if top_feats else "minimal data"
    trade = f" Trade-offs: low contribution from {', '.join(low_contrib_features)}." if low_contrib_features else ""
    return (
        f"Top choice is {top.name} (score={top.score:.1f}). Key contributors: {keys}. "
        f"Runner-up: {runner.name} (score={runner.score:.1f})." + trade
    )


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def schema() -> Dict[str, object]:
    return export_json_schema()


@app.post("/pick", response_model=MaterialPickResponse)
def pick_materials(req: MaterialPickRequest, response: Response) -> MaterialPickResponse:
    if not req.materials:
        raise HTTPException(status_code=422, detail="No materials provided")

    # Guard: units accepted set; convert to SI internally (minimal set)
    if req.units.stress not in {"MPa", "Pa"}:
        raise HTTPException(status_code=422, detail="units.stress must be one of: MPa, Pa")
    if req.units.density not in {"g/cm^3", "kg/m^3"}:
        raise HTTPException(status_code=422, detail="units.density must be one of: g/cm^3, kg/m^3")
    if req.units.cost not in {"USD/kg"}:
        raise HTTPException(status_code=422, detail="units.cost must be: USD/kg")

    # Numeric properties in scope and their direction
    numeric_keys = ["yield_strength", "density", "cost", "fatigue"]
    higher_is_better: Dict[str, bool] = {
        "yield_strength": True,
        "density": False,
        "cost": False,
        "fatigue": True,
    }

    # Build weights dict from model; compute total and normalize
    declared_weights: Dict[str, float] = {
        "yield_strength": float(req.weights.yield_strength),
        "density": float(req.weights.density),
        "cost": float(req.weights.cost),
        "fatigue": float(req.weights.fatigue),
        "corrosion": float(req.weights.corrosion),
    }
    total_declared = sum(w for w in declared_weights.values() if w > 0)
    if total_declared <= 0:
        raise HTTPException(status_code=422, detail="All weights are zero; set at least one > 0")
    # Normalize weights to sum to 1.0
    weights_norm = {k: (v / total_declared) if v > 0 else 0.0 for k, v in declared_weights.items()}
    assumptions: List[str] = []
    if abs(total_declared - 1.0) > 1e-6:
        assumptions.append(f"Normalized weights by factor 1/{total_declared:.6f} to sum to 1.0")

    # Synthetic mapping: environment synonyms -> corrosion emphasis/provenance note
    mapping_notes: List[str] = []
    if req.constraints.environment:
        env = req.constraints.environment.lower()
        if any(key in env for key in ["marine", "salt-spray", "cres"]):
            mapping_notes.append("mapped 'marine' -> corrosion=excellent via qualitative table v0.1")

    # Convert values to SI where applicable (yield_strength to Pa, density to kg/m^3)
    def _convert(key: str, value: float) -> float:
        if key == "yield_strength" and req.units.stress == "MPa":
            return value * 1_000_000.0
        if key == "density" and req.units.density == "g/cm^3":
            return value * 1000.0
        return value

    # Validate and build numeric and qualitative dicts
    numeric_dicts: List[Dict[str, float]] = []
    qual_dicts: List[Dict[str, str]] = []
    imputed_qual: List[str] = []
    for idx, m in enumerate(req.materials):
        # Negative guard
        for k, v in m.properties.items():
            if v < 0:
                raise HTTPException(status_code=422, detail=f"materials[{idx}].properties.{k} must be >= 0")
        # Convert
        props_si: Dict[str, float] = {k: _convert(k, float(v)) for k, v in m.properties.items()}
        numeric_dicts.append(props_si)
        qmap = dict(m.qualities)
        # Impute corrosion neutral if missing
        if "corrosion" not in qmap:
            qmap["corrosion"] = "neutral"
            imputed_qual.append(m.id)
        qual_dicts.append(qmap)

    if imputed_qual:
        assumptions.append("Imputed 'corrosion=neutral' for: " + ", ".join(imputed_qual))
    if mapping_notes:
        assumptions.extend(mapping_notes)

    # Numeric scoring
    numeric_weights = {k: weights_norm.get(k, 0.0) for k in numeric_keys}
    num_scores = compute_weighted_numeric_score(
        numeric_properties=numeric_dicts,
        weights=numeric_weights,
        higher_is_better=higher_is_better,
    )

    # Qualitative scoring (only corrosion)
    qual_weights = {"corrosion": weights_norm.get("corrosion", 0.0)}
    scale = dict(DEFAULT_QUALITATIVE_SCALE)
    scale.setdefault("neutral", 0.5)
    qual_scores = compute_qualitative_score(
        qualitative_properties=qual_dicts,
        weights=qual_weights,
        scale=scale,
    )

    # Effective weights: skip features with zero variance/missing everywhere
    effective_numeric_weight = 0.0
    for prop_name, w in numeric_weights.items():
        if w <= 0:
            continue
        norm_map = normalize_property_values(
            materials=numeric_dicts,
            property_name=prop_name,
            higher_is_better=higher_is_better.get(prop_name, True),
        )
        if any(v != 0.0 for v in norm_map.values()):
            effective_numeric_weight += float(w)
    effective_qual_weight = 0.0
    for w in [qual_weights.get("corrosion", 0.0)]:
        if w > 0:
            effective_qual_weight += float(w)

    total_eff = effective_numeric_weight + effective_qual_weight

    # Combine
    combined_0_1: List[float] = []
    for i in range(len(req.materials)):
        n = num_scores[i] if i < len(num_scores) else 0.0
        q = qual_scores[i] if i < len(qual_scores) else 0.0
        if total_eff <= 0.0:
            combined_0_1.append(0.0)
        else:
            combined_0_1.append((effective_numeric_weight * n + effective_qual_weight * q) / total_eff)

    # Build contributions per material in 0..100 space
    contributions: List[List[Contribution]] = [[] for _ in req.materials]
    # Numeric
    for prop_name, w in numeric_weights.items():
        if w <= 0:
            continue
        norm_map = normalize_property_values(
            materials=numeric_dicts,
            property_name=prop_name,
            higher_is_better=higher_is_better.get(prop_name, True),
        )
        for idx in range(len(req.materials)):
            norm_v = float(norm_map.get(idx, 0.0))
            contributions[idx].append(
                Contribution(
                    name=prop_name,
                    normalized=100.0 * norm_v,
                    weight=w,
                    contribution=100.0 * w * norm_v,
                )
            )
    # Qualitative
    w = qual_weights.get("corrosion", 0.0)
    if w > 0:
        for idx, q in enumerate(qual_dicts):
            val = scale.get(q.get("corrosion", "").lower(), 0.5)
            contributions[idx].append(
                Contribution(
                    name="corrosion",
                    normalized=100.0 * float(val),
                    weight=w,
                    contribution=100.0 * w * float(val),
                )
            )

    # Identify low-contribution features for trade-off reasoning
    low_contrib_feats: List[str] = []
    if contributions and contributions[0]:
        lows = [c.name for c in contributions[0] if c.contribution < 100.0 * (weights_norm.get(c.name, 0.0) * 0.3)]
        low_contrib_feats = lows[:3]

    ranked: List[ApiRankedMaterial] = [
        ApiRankedMaterial(
            id=req.materials[i].id,
            name=req.materials[i].name,
            score=round(100.0 * combined_0_1[i], 1),
            contributions=contributions[i],
            constraints_satisfied=(
                (req.constraints.min_yield_strength is None or req.materials[i].properties.get("yield_strength", 0.0) >= req.constraints.min_yield_strength)
                and (req.constraints.max_density is None or req.materials[i].properties.get("density", 0.0) <= req.constraints.max_density)
                and (req.constraints.max_cost is None or req.materials[i].properties.get("cost", 0.0) <= req.constraints.max_cost)
            ),
            caveats=[],
            provenance=req.materials[i].provenance or [],
        )
        for i in range(len(req.materials))
    ]
    # Stable sort: score desc, then id asc
    ranked.sort(key=lambda r: (-r.score, r.id))

    # Confidence calibration: coverage and margin index
    coverage = min(1.0, max(0.0, total_eff / max(1e-12, sum(weights_norm.values()))))
    top_scores = [r.score for r in ranked[:3]]
    if len(top_scores) < 2:
        margin_index = 0.0
    else:
        top_val = top_scores[0]
        second_val = top_scores[1]
        diffs = [abs(s - median(top_scores)) for s in top_scores]
        mad = median(diffs) if diffs else 0.0
        margin_index = 0.0 if mad == 0 else max(0.0, min(1.0, (top_val - second_val) / mad))
    confidence = max(0.0, min(1.0, 0.3 + 0.5 * coverage + 0.2 * margin_index))
    if len(ranked) == 1:
        confidence = min(confidence, 0.55)

    # Reasoning
    reasoning = _make_reasoning(ranked, low_contrib_feats)

    # Trace and headers
    git = _git_metadata()
    request_hash = req.trace_hash()
    response.headers["x-trace"] = f"{request_hash[:12]}:{git['git_sha']}"

    trace = Trace(
        request_hash=request_hash,
        code_version=f"git:{git['git_sha']}",
        model_config={"scaler": "minmax_v1"},
    )

    assumptions.extend([
        "Per-feature min-max normalization across provided candidates",
        "Lower-is-better features inverted via (1 - normalized)",
        "Qualitative labels matched case-insensitively; unknown labels -> neutral",
    ])

    return MaterialPickResponse(
        schema_version=SCHEMA_VERSION,
        result={"ranked": ranked},
        assumptions=assumptions,
        confidence=confidence,
        abstain=False,
        trace=trace,
    )


