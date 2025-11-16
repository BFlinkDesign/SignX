from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request, Response

from ..common.models import make_envelope
from ..deps import get_code_version, get_model_config, settings
from ..metrics import (
    ABSTAIN_TOTAL,
    MATERIALS_IMPUTED_QUALITATIVE_TOTAL,
    MATERIALS_NORMALIZED_WEIGHTS_TOTAL,
    MATERIALS_REQUESTS_TOTAL,
)
from ..schemas import ResponseEnvelope


router = APIRouter()


MATERIALS_URL = "http://materials-service:8080/pick"


def _result_shape(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "result": payload.get("result"),
        "assumptions": payload.get("assumptions", []),
        "confidence": float(payload.get("confidence", 0.0)),
    }


@router.post("/v1/materials/pick", response_model=ResponseEnvelope)
async def materials_pick(request: Request, resp: Response) -> ResponseEnvelope:  # type: ignore[no-untyped-def]
    # Body size guard
    body_bytes = await request.body()
    if len(body_bytes) > settings.MAX_BODY_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="request body too large")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(MATERIALS_URL, json=body)

    if r.status_code >= 500:
        MATERIALS_REQUESTS_TOTAL.labels(status="5xx").inc()
        raise HTTPException(status_code=502, detail="materials backend error")

    # surface canonical x-trace to callers
    if "x-trace" in r.headers:
        resp.headers["x-trace"] = r.headers["x-trace"]

    # 4xx passthrough
    if 400 <= r.status_code < 500 and r.status_code != 429:
        MATERIALS_REQUESTS_TOTAL.labels(status="4xx").inc()
        raise HTTPException(status_code=r.status_code, detail=r.text)

    payload = r.json()

    # metrics: abstain (if present)
    if isinstance(payload, dict) and payload.get("abstain"):
        ABSTAIN_TOTAL.inc()
    # metrics: normalized weights & imputation by assumptions text
    assumptions = payload.get("assumptions", []) if isinstance(payload, dict) else []
    if any("Normalized weights" in a for a in assumptions):
        MATERIALS_NORMALIZED_WEIGHTS_TOTAL.inc()
    if any("Imputed 'corrosion=neutral'" in a for a in assumptions):
        MATERIALS_IMPUTED_QUALITATIVE_TOTAL.inc()
    MATERIALS_REQUESTS_TOTAL.labels(status="2xx").inc()

    # Build envelope
    out = _result_shape(payload)
    return make_envelope(
        result=out["result"],
        assumptions=out["assumptions"],
        confidence=out["confidence"],
        inputs={"gateway": "materials.pick"},
        intermediates={},
        outputs={"status": r.status_code},
        code_version=get_code_version(),
        model_config=get_model_config(),
    )


