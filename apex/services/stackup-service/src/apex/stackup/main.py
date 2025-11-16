from __future__ import annotations

from fastapi import FastAPI
from packages.schemas import ResponseEnvelope, TraceDataModel, TraceModel, CodeVersionModel, ModelConfigModel

app = FastAPI(title="APEX Stackup Service")

@app.get("/health")
async def health():
    """Health check endpoint using shared envelope schema."""
    return ResponseEnvelope(
        result={"status": "ok"},
        assumptions=[],
        confidence=1.0,
        trace=TraceModel(
            data=TraceDataModel(inputs={}, intermediates={}, outputs={}),
            code_version=CodeVersionModel(),
            model_config=ModelConfigModel(),
        ),
    )

