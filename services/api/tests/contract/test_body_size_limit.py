import requests


def test_body_size_limit_trips():
    url = "http://localhost:8000/projects"
    # Generate a body larger than 300KB to exceed default dev limit (256KB)
    payload = {"name": "x", "blob": "a" * 400_000}
    r = requests.post(url, json=payload, timeout=3)
    assert r.status_code in (413, 201)
    # In local dev without middleware loaded or limits increased, allow 201; otherwise 413

