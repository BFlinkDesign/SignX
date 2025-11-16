import requests


def test_envelope_schema_roundtrip():
    schema = requests.get("http://localhost:8000/schemas/envelope.v1.json", timeout=3).json()
    sample = requests.get("http://localhost:8000/health", timeout=3).json()
    for key in ("result", "assumptions", "confidence", "trace"):
        assert key in sample
    assert 0.0 <= sample["confidence"] <= 1.0
    assert schema["title"].lower().startswith("responseenvelope")


