import requests


def test_rate_limit_trip():
    url = "http://localhost:8000/health"
    got_429 = False
    last = None
    for _ in range(65):
        last = requests.get(url, timeout=2)
        if last.status_code == 429:
            got_429 = True
            break
    assert got_429, f"expected 429; got {last.status_code if last else 'n/a'}"


